"""Persist normalized upload drafts into the conditioned scientific schema."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
import re
from typing import Any

from sqlalchemy import select

from backend import models
from backend.db_helpers import build_composition_key, build_system_key, normalize_formula
from backend.ingest.prop_names import normalize_prop_name
from backend.services.classification_catalog import (
    MATERIAL_DIMENSIONALITIES,
    count_formula_elements,
)
from backend.services.space_groups import CRYSTAL_SYSTEMS
from backend.services.structure_candidates import validate_structure_text


RESERVED_PROPERTY_CODES = {
    "tc",
    "critical_temperature",
    "electron_phonon_coupling",
    "omega_log",
    "space_group",
}

SUPERCONDUCTOR_KINDS = {"conventional", "unconventional", "unknown"}


@dataclass
class ScientificEvidenceTarget:
    field_path: str
    evidence: dict[str, Any]
    kind: str | None = None
    entity: Any | None = None


def _candidate_state_index(candidate: dict[str, Any]) -> int | None:
    """Return the explicit material-state index assigned by the user."""
    match = re.fullmatch(r"material_states\[(\d+)\]", str(candidate.get("material_state_ref") or ""))
    return int(match.group(1)) if match else None


def _confirmed_candidates_by_state(draft: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for candidate in draft.get("structure_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        if candidate.get("confirmation") != "confirmed" or candidate.get("status") != "confirmed":
            continue
        state_index = _candidate_state_index(candidate)
        if state_index is not None:
            grouped.setdefault(state_index, []).append(candidate)
    return grouped


def _candidate_conventional_representation(candidate: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    representations = candidate.get("representations")
    if not isinstance(representations, dict):
        return None
    conventional = representations.get("conventional")
    if not isinstance(conventional, dict):
        return None
    cif = conventional.get("cif")
    if not isinstance(cif, dict) or not str(cif.get("text") or "").strip():
        return None
    return str(cif["text"]), cif


def _json_number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        value = value.get("value")
    try:
        return float(value)
    except (TypeError, ValueError):
        match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value))
        return float(match.group()) if match else None


def _source_locator(evidence: Any) -> str | None:
    if not isinstance(evidence, dict):
        return None
    values = []
    if evidence.get("section"):
        values.append(str(evidence["section"]))
    if evidence.get("page") or evidence.get("page_start"):
        values.append(f"p. {evidence.get('page') or evidence.get('page_start')}")
    return ", ".join(values) or None


def _fingerprint(field_path: str, payload: dict[str, Any]) -> str:
    serialized = json.dumps(
        {"field_path": field_path, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


async def _get_or_create_superconductor(session, chemical_formula: str):
    normalized, elements, composition, ratios = normalize_formula(chemical_formula)
    composition_key = build_composition_key(composition)
    result = await session.execute(
        select(models.Superconductor).where(
            models.Superconductor.composition_key == composition_key
        )
    )
    superconductor = result.scalar_one_or_none()
    if superconductor is not None:
        return superconductor

    system_key, elements_list = build_system_key(elements)
    result = await session.execute(
        select(models.ChemicalSystem).where(
            models.ChemicalSystem.system_key == system_key
        )
    )
    system = result.scalar_one_or_none()
    if system is None:
        system = models.ChemicalSystem(
            system_key=system_key,
            elements_list=elements_list,
            element_count=len(elements_list),
        )
        session.add(system)
        await session.flush()

    superconductor = models.Superconductor(
        chemical_system_id=system.id,
        chemical_formula=chemical_formula,
        formula_normalized=normalized,
        composition_key=composition_key,
        display_name=chemical_formula,
        elements_list=elements,
        composition={key: _json_number(value) for key, value in composition.items()},
        element_ratio={key: _json_number(value) for key, value in ratios.items()},
    )
    session.add(superconductor)
    await session.flush()
    return superconductor


async def _get_or_create_property_definition(
    session,
    item: dict[str, Any],
    *,
    value_kind: str,
):
    name_raw = str(item.get("name_raw") or item.get("name") or "").strip()
    normalized_name, _matched = normalize_prop_name(str(item.get("name") or name_raw))
    code = re.sub(r"[^a-z0-9]+", "_", normalized_name.lower()).strip("_")
    if not code:
        code = f"custom_{hashlib.sha256(name_raw.encode('utf-8')).hexdigest()[:12]}"
    if code in RESERVED_PROPERTY_CODES:
        raise ValueError(f"{name_raw} 必须写入专用科学字段，不能作为普通物性")
    result = await session.execute(
        select(models.PropertyDefinition).where(models.PropertyDefinition.code == code)
    )
    definition = result.scalar_one_or_none()
    if definition is not None:
        return definition
    definition = models.PropertyDefinition(
        code=code[:100],
        display_name=name_raw[:255],
        canonical_unit=item.get("unit"),
        value_kind=value_kind,
        description="论文上传时自动建立的属性定义",
    )
    session.add(definition)
    await session.flush()
    return definition


async def _create_calculation_context(session, paper, state, structure, calculation_data):
    calculation = models.CalculationContext(
        paper_id=paper.id,
        paper_revision=paper.content_revision,
        material_state_id=state.id,
        structure_id=structure.id if structure is not None else None,
        missing_structure_reason=(
            None if structure is not None
            else calculation_data.get("missing_structure_reason") or "论文未提供或未提取完整结构文本"
        ),
        phonon_nuclear_treatment=calculation_data.get("phonon_nuclear_treatment") or "unknown",
        lambda_ep=_number(calculation_data.get("lambda_ep")),
        omega_log_k=_number(calculation_data.get("omega_log_k")),
        mu_star=_number(calculation_data.get("mu_star")),
        epc_method=calculation_data.get("epc_method"),
        calculation_code=calculation_data.get("calculation_code"),
        parameters_json=calculation_data.get("parameters_json"),
    )
    session.add(calculation)
    await session.flush()
    return calculation


async def persist_scientific_draft(
    session,
    paper: models.Paper,
    draft: dict[str, Any],
) -> list[ScientificEvidenceTarget]:
    """Create the scientific entity graph and return evidence-link targets."""
    targets: list[ScientificEvidenceTarget] = []
    candidates_by_state = _confirmed_candidates_by_state(draft)
    for state_index, state_data in enumerate(draft.get("material_states") or []):
        material = str(state_data.get("material") or "").strip()
        superconductor = await _get_or_create_superconductor(session, material)
        dimensionality = str(state_data.get("material_dimensionality") or "unknown")
        if dimensionality not in MATERIAL_DIMENSIONALITIES:
            raise ValueError("材料维度无效")
        draft_element_count = state_data.get("element_count")
        element_count = (
            draft_element_count
            if isinstance(draft_element_count, int) and not isinstance(draft_element_count, bool)
            else count_formula_elements(material)
        )
        superconductor_kind = state_data.get("superconductor_kind") or "unknown"
        if superconductor_kind not in SUPERCONDUCTOR_KINDS:
            superconductor_kind = "unknown"
        crystal_system = state_data.get("crystal_system") or "unknown"
        if crystal_system not in CRYSTAL_SYSTEMS:
            crystal_system = "unknown"
        state = models.MaterialState(
            paper_id=paper.id,
            paper_revision=paper.content_revision,
            superconductor_id=superconductor.id,
            material_family_id=None,
            element_count=element_count,
            material_dimensionality=dimensionality,
            pressure_value_gpa=_number(state_data.get("pressure_value_gpa")),
            pressure_min_gpa=_number(state_data.get("pressure_min_gpa")),
            pressure_max_gpa=_number(state_data.get("pressure_max_gpa")),
            pressure_raw=state_data.get("pressure_raw"),
            pressure_unit_raw=state_data.get("pressure_unit_raw"),
            reported_space_group_symbol=state_data.get("reported_space_group_symbol"),
            reported_space_group_number=state_data.get("reported_space_group_number"),
            temperature_value_k=_number(state_data.get("temperature_value_k")),
            temperature_raw=state_data.get("temperature_raw"),
            temperature_unit_raw=state_data.get("temperature_unit_raw"),
            magnetic_field_t=_number(state_data.get("magnetic_field_t")),
            state_kind=state_data.get("state_kind") or "unknown",
            superconductor_kind=superconductor_kind,
            crystal_system=crystal_system,
            note=state_data.get("note"),
        )
        session.add(state)
        await session.flush()

        state_path = f"material_states[{state_index}]"
        structure_selections = [
            item for item in state_data.get("structure_families") or []
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        ]
        if sum(bool(item.get("is_primary")) for item in structure_selections) > 1:
            raise ValueError("一个材料状态只能有一个主结构家族")
        space_group_evidence = state_data.get("space_group_evidence")
        if isinstance(space_group_evidence, dict):
            targets.append(ScientificEvidenceTarget(
                f"{state_path}.reported_space_group", space_group_evidence
            ))

        structure = None
        structure_data = state_data.get("structure")
        if isinstance(structure_data, dict) and str(structure_data.get("structure_text") or "").strip():
            structure_text = str(structure_data["structure_text"])
            structure = models.StructureModel(
                paper_id=paper.id,
                paper_revision=paper.content_revision,
                material_state_id=state.id,
                space_group_symbol=structure_data.get("space_group_symbol") or state_data.get("reported_space_group_symbol"),
                space_group_number=structure_data.get("space_group_number") or state_data.get("reported_space_group_number"),
                structure_format=structure_data.get("structure_format") or "unknown",
                structure_text=structure_text,
                structure_hash=hashlib.sha256(structure_text.encode("utf-8")).hexdigest(),
                nuclear_treatment=structure_data.get("nuclear_treatment") or "unknown",
                source_locator=_source_locator(structure_data.get("evidence")),
            )
            session.add(structure)
            await session.flush()
            if isinstance(structure_data.get("evidence"), dict):
                targets.append(ScientificEvidenceTarget(
                    f"{state_path}.structure",
                    structure_data["evidence"],
                    "structure",
                    structure,
                ))

        # Native CIF/POSCAR attachments are only persisted after explicit confirmation.
        # Store the conventional-cell CIF as the canonical representation; the draft
        # retains primitive-cell and POSCAR variants for user export.
        for candidate in candidates_by_state.get(state_index, []):
            representation = _candidate_conventional_representation(candidate)
            if representation is None:
                continue
            structure_text, metadata = representation
            # Never trust validation/hash fields supplied by the browser draft.
            validation = validate_structure_text("cif", structure_text)
            source = next(
                (item for item in candidate.get("sources") or [] if isinstance(item, dict)),
                {},
            )
            source_name = str(source.get("filename") or source.get("file_id") or "structure attachment")
            calculation_data = state_data.get("calculation_context")
            candidate_structure = models.StructureModel(
                paper_id=paper.id,
                paper_revision=paper.content_revision,
                material_state_id=state.id,
                space_group_symbol=state_data.get("reported_space_group_symbol"),
                space_group_number=state_data.get("reported_space_group_number"),
                structure_format="cif",
                structure_text=structure_text,
                structure_hash=(validation or {}).get("structure_hash")
                or hashlib.sha256(structure_text.encode("utf-8")).hexdigest(),
                cell_parameters=(validation or {}).get("cell_parameters"),
                volume_angstrom3=(validation or {}).get("volume"),
                atom_count=(validation or {}).get("atom_count"),
                geometry_method=(metadata or {}).get("standardization_method") or "attachment_conventional",
                nuclear_treatment=(calculation_data or {}).get("phonon_nuclear_treatment")
                if isinstance(calculation_data, dict) else "unknown",
                source_locator=f"attachment: {source_name}",
            )
            session.add(candidate_structure)
            await session.flush()
            for source_evidence in candidate.get("sources") or []:
                if isinstance(source_evidence, dict) and str(source_evidence.get("quote") or "").strip():
                    targets.append(ScientificEvidenceTarget(
                        f"{state_path}.structure_candidates[{candidate.get('candidate_id')}]",
                        source_evidence,
                        "structure",
                        candidate_structure,
                    ))
            if structure is None:
                structure = candidate_structure

        tc_items = [item for item in state_data.get("tc_results") or [] if isinstance(item, dict)]
        calculation_data = state_data.get("calculation_context")
        needs_calculation = isinstance(calculation_data, dict) or any(
            item.get("result_kind") == "theoretical" for item in tc_items
        )
        calculation = None
        if needs_calculation:
            calculation_data = calculation_data if isinstance(calculation_data, dict) else {}
            calculation = await _create_calculation_context(
                session, paper, state, structure, calculation_data
            )
            if isinstance(calculation_data.get("evidence"), dict):
                targets.append(ScientificEvidenceTarget(
                    f"{state_path}.calculation_context", calculation_data["evidence"]
                ))

        experimental_data = state_data.get("experimental_context")
        needs_experiment = isinstance(experimental_data, dict) or any(
            item.get("result_kind") == "experimental" for item in tc_items
        )
        experimental = None
        if needs_experiment:
            experimental_data = experimental_data if isinstance(experimental_data, dict) else {}
            experimental = models.ExperimentalContext(
                paper_id=paper.id,
                paper_revision=paper.content_revision,
                material_state_id=state.id,
                structure_id=structure.id if structure is not None else None,
                sample_label=experimental_data.get("sample_label"),
                measurement_method=experimental_data.get("measurement_method"),
                tc_criterion=experimental_data.get("tc_criterion") or "unknown",
                applied_field_t=_number(experimental_data.get("applied_field_t")),
                pressure_uncertainty_gpa=_number(experimental_data.get("pressure_uncertainty_gpa")),
                parameters_json=experimental_data.get("parameters_json"),
            )
            session.add(experimental)
            await session.flush()

        for tc_index, item in enumerate(tc_items):
            result_kind = item.get("result_kind") or "theoretical"
            value_raw = str(item.get("value_raw") or item.get("tc_value_k") or "").strip()
            tc_method = "experimental" if result_kind == "experimental" else item.get("tc_method") or "unknown"
            field_path = f"{state_path}.tc_results[{tc_index}]"
            item_calculation = None
            item_calculation_data = item.get("calculation_context")
            if result_kind == "theoretical" and isinstance(item_calculation_data, dict) and any(
                _number(item_calculation_data.get(key)) is not None
                for key in ("lambda_ep", "omega_log_k", "mu_star")
            ):
                item_calculation = await _create_calculation_context(
                    session, paper, state, structure, item_calculation_data
                )
                if isinstance(item_calculation_data.get("evidence"), dict):
                    targets.append(ScientificEvidenceTarget(
                        f"{field_path}.calculation_context", item_calculation_data["evidence"]
                    ))
            calculation_context_id = None
            if result_kind == "theoretical":
                context = item_calculation or calculation
                calculation_context_id = context.id if context is not None else None
            tc_result = models.TcResult(
                paper_id=paper.id,
                paper_revision=paper.content_revision,
                material_state_id=state.id,
                calculation_context_id=calculation_context_id,
                experimental_context_id=experimental.id if result_kind == "experimental" and experimental else None,
                result_kind=result_kind,
                tc_method=tc_method,
                tc_method_custom=(item.get("tc_method_custom") or None) if tc_method == "other" else None,
                tc_value_k=_number(item.get("tc_value_k")),
                tc_min_k=_number(item.get("tc_min_k")),
                tc_max_k=_number(item.get("tc_max_k")),
                uncertainty_k=_number(item.get("uncertainty_k")),
                value_raw=value_raw,
                unit_raw=str(item.get("unit_raw") or "K"),
                source_locator=_source_locator(item.get("evidence")),
                source_fingerprint=_fingerprint(field_path, item),
                is_representative=False,
            )
            session.add(tc_result)
            await session.flush()
            if isinstance(item.get("evidence"), dict):
                targets.append(ScientificEvidenceTarget(
                    field_path, item["evidence"], "tc", tc_result
                ))

        for property_index, item in enumerate(state_data.get("properties") or []):
            if not isinstance(item, dict):
                continue
            value_min = _number(item.get("value_min"))
            value_max = _number(item.get("value_max"))
            value_number = _number(item.get("value"))
            value_raw = str(item.get("value_raw") or item.get("value") or "").strip()
            value_kind = "range" if value_min is not None and value_max is not None else "number" if value_number is not None else "text"
            definition = await _get_or_create_property_definition(
                session, item, value_kind=value_kind
            )
            field_path = f"{state_path}.properties[{property_index}]"
            prop = models.SuperconductorProperty(
                paper_id=paper.id,
                paper_revision=paper.content_revision,
                material_state_id=state.id,
                structure_id=structure.id if structure is not None else None,
                calculation_context_id=calculation.id if calculation is not None else None,
                property_definition_id=definition.id,
                material_raw=material,
                name_raw=str(item.get("name_raw") or item.get("name") or "").strip(),
                value_raw=value_raw,
                unit_raw=item.get("unit"),
                value_number=value_number if value_kind == "number" else None,
                value_min=value_min,
                value_max=value_max,
                canonical_unit=item.get("unit"),
                condition_note=item.get("condition_note"),
                source_fingerprint=_fingerprint(field_path, item),
            )
            session.add(prop)
            await session.flush()
            if isinstance(item.get("evidence"), dict):
                targets.append(ScientificEvidenceTarget(
                    field_path, item["evidence"], "property", prop
                ))
    return targets


def add_scientific_evidence_link(
    session,
    target: ScientificEvidenceTarget,
    paper_evidence: models.PaperEvidence,
) -> None:
    common = {
        "paper_evidence_id": paper_evidence.id,
        "paper_id": paper_evidence.paper_id,
        "paper_revision": paper_evidence.paper_revision,
        "evidence_role": "primary",
    }
    if target.kind == "tc":
        session.add(models.TcResultEvidence(tc_result_id=target.entity.id, **common))
    elif target.kind == "structure":
        session.add(models.StructureModelEvidence(structure_id=target.entity.id, **common))
    elif target.kind == "property":
        session.add(models.SuperconductorPropertyEvidence(
            superconductor_property_id=target.entity.id,
            **common,
        ))
