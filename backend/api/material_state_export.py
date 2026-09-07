"""MaterialState 完整 JSON 导出（Issue #90）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from backend import models
from backend.database import get_db
from backend.security import get_current_user_optional

router = APIRouter(prefix="/api/papers", tags=["material-state-export"])


def _can_view(paper: models.Paper, user: models.User | None) -> bool:
    if paper.review_status == "approved" and paper.approved_revision == paper.content_revision:
        return True
    return bool(user and (user.role in {"admin", "superadmin"} or paper.uploaded_by_user_id == user.id))


def _incomplete(message: str) -> HTTPException:
    return HTTPException(status_code=409, detail={"code": "export_incomplete", "message": message})


def build_material_state_export(db: Session, *, paper_id: int, state_key: str, user: models.User | None) -> dict:
    paper = db.query(models.Paper).filter(models.Paper.id == paper_id).first()
    if paper is None:
        raise HTTPException(status_code=404, detail={"code": "export_incomplete", "message": "论文不存在"})
    if not _can_view(paper, user):
        raise HTTPException(status_code=403, detail={"code": "export_forbidden", "message": "无权导出该材料状态"})
    revision = paper.content_revision
    state = db.query(models.MaterialState).filter_by(state_key=state_key, paper_id=paper_id, paper_revision=revision).first()
    if state is None:
        raise HTTPException(status_code=404, detail={"code": "export_incomplete", "message": "材料状态不存在"})
    material = db.query(models.Superconductor).filter_by(id=state.superconductor_id, paper_id=paper_id, paper_revision=revision).first()
    if material is None:
        raise _incomplete("材料状态所属材料不存在")
    chemical_system = db.query(models.ChemicalSystem).filter_by(id=material.chemical_system_id, paper_id=paper_id, paper_revision=revision).first()
    if chemical_system is None:
        raise _incomplete("材料所属化学体系不存在")

    structures = db.query(models.StructureModel).filter_by(material_state_id=state.id, paper_id=paper_id, paper_revision=revision).order_by(models.StructureModel.id).all()
    modules = db.query(models.PropertyModule).filter_by(material_state_id=state.id, paper_id=paper_id, paper_revision=revision).order_by(models.PropertyModule.display_order, models.PropertyModule.id).all()
    module_ids = [item.id for item in modules]
    records = [] if not module_ids else db.query(models.PropertyRecord).filter(
        models.PropertyRecord.module_id.in_(module_ids), models.PropertyRecord.paper_id == paper_id,
        models.PropertyRecord.paper_revision == revision,
    ).order_by(models.PropertyRecord.id).all()
    records_by_module: dict[int, list[models.PropertyRecord]] = {item.id: [] for item in modules}
    for record in records:
        records_by_module[record.module_id].append(record)

    definition_keys = {(item.definition_key, item.definition_version) for item in modules}
    definition_keys.update((item.definition_key, item.definition_version) for item in records)
    definitions = {}
    for key, version in definition_keys:
        definition = db.query(models.FormDefinition).filter_by(definition_key=key, version=version).first()
        if definition is None:
            raise _incomplete(f"定义 {key}@{version} 不存在")
        definitions[(key, version)] = definition

    record_ids = [item.id for item in records]
    links = [] if not record_ids else db.query(models.PropertyRecordEvidence).filter(
        models.PropertyRecordEvidence.record_id.in_(record_ids), models.PropertyRecordEvidence.paper_id == paper_id,
        models.PropertyRecordEvidence.paper_revision == revision,
    ).all()
    evidence_ids = {item.paper_evidence_id for item in links}
    evidence_rows = [] if not evidence_ids else db.query(models.PaperEvidence).filter(
        models.PaperEvidence.id.in_(evidence_ids), models.PaperEvidence.paper_id == paper_id,
        models.PaperEvidence.paper_revision == revision,
    ).all()
    evidence_by_id = {item.id: item for item in evidence_rows}
    if evidence_ids != set(evidence_by_id):
        missing = min(evidence_ids - set(evidence_by_id))
        raise _incomplete(f"Evidence {missing} 无法解析")
    links_by_record: dict[int, list[models.PropertyRecordEvidence]] = {item.id: [] for item in records}
    for link in links:
        links_by_record[link.record_id].append(link)

    structure_ids = {str(item.id) for item in structures}
    for record in records:
        if record.structure_key and record.structure_key not in structure_ids:
            raise _incomplete(f"记录 {record.record_key} 引用的结构不存在")

    module_payloads = []
    for module in modules:
        record_payloads = []
        for record in records_by_module[module.id]:
            references = []
            for link in links_by_record[record.id]:
                evidence = evidence_by_id[link.paper_evidence_id]
                references.append({
                    "paper_evidence_id": evidence.id, "field_path": link.field_path,
                    "evidence_role": link.evidence_role, "source_field_path": evidence.field_path,
                    "section": evidence.section, "page_start": evidence.page_start,
                    "page_end": evidence.page_end, "quote": evidence.quote,
                })
            record_payloads.append({
                "record_key": record.record_key, "record_type": record.record_type,
                "property_code": record.property_code, "custom_property_key": record.custom_property_key,
                "definition_key": record.definition_key, "definition_version": record.definition_version,
                "name_raw": record.name_raw, "value_kind": record.value_kind, "value_raw": record.value_raw,
                "value_number": record.value_number, "value_min": record.value_min, "value_max": record.value_max,
                "value_text": record.value_text, "value_boolean": record.value_boolean,
                "uncertainty": record.uncertainty, "unit_raw": record.unit_raw,
                "canonical_unit": record.canonical_unit, "method_code": record.method_code,
                "method_raw": record.method_raw, "criterion_code": record.criterion_code,
                "criterion_raw": record.criterion_raw, "is_representative": record.is_representative,
                "structure_key": record.structure_key, "payload": record.payload_json or {},
                "record_checksum": record.record_checksum, "evidences": references,
            })
        module_payloads.append({
            "module_key": module.module_key, "module_code": module.module_code,
            "definition_key": module.definition_key, "definition_version": module.definition_version,
            "display_order": module.display_order, "metadata": module.metadata_json or {}, "records": record_payloads,
        })

    end_revision = db.query(models.Paper.content_revision).filter(models.Paper.id == paper_id).scalar()
    if end_revision != revision:
        raise HTTPException(status_code=409, detail={"code": "export_revision_conflict", "message": "导出期间论文 revision 已变化"})

    payload = {
        "export_version": 1,
        "paper": {"id": paper.id, "revision": revision, "doi": paper.doi, "title": paper.title, "journal": paper.journal, "year": paper.year},
        "chemical_system": {"system_key": chemical_system.system_key, "elements_list": chemical_system.elements_list, "element_count": chemical_system.element_count},
        "material": {"chemical_formula": material.chemical_formula, "formula_normalized": material.formula_normalized, "composition_key": material.composition_key, "isotope_signature": material.isotope_signature, "display_name": material.display_name, "elements_list": material.elements_list, "composition": material.composition, "element_ratio": material.element_ratio},
        "material_state": {
            "id": state.id, "paper_id": state.paper_id, "paper_revision": state.paper_revision,
            "element_count": state.element_count, "material_dimensionality": state.material_dimensionality,
            "pressure_value_gpa": state.pressure_value_gpa, "pressure_min_gpa": state.pressure_min_gpa,
            "pressure_max_gpa": state.pressure_max_gpa, "pressure_raw": state.pressure_raw,
            "pressure_unit_raw": state.pressure_unit_raw, "reported_space_group_symbol": state.reported_space_group_symbol,
            "reported_space_group_number": state.reported_space_group_number, "temperature_value_k": state.temperature_value_k,
            "temperature_raw": state.temperature_raw, "temperature_unit_raw": state.temperature_unit_raw,
            "magnetic_field_t": state.magnetic_field_t, "state_kind": state.state_kind,
            "crystal_system": state.crystal_system, "note": state.note,
            "structures": [{
                "id": item.id, "format": item.structure_format, "filename": item.source_locator,
                "media_type": "chemical/x-cif" if item.structure_format == "cif" else "chemical/x-poscar",
                "content": item.structure_text, "sha256": item.structure_hash,
                "space_group_symbol": item.space_group_symbol, "space_group_number": item.space_group_number,
                "cell_parameters": item.cell_parameters, "source_locator": item.source_locator,
            } for item in structures],
        },
        "property_modules": module_payloads,
        "definitions": [{
            "definition_key": item.definition_key, "version": item.version, "target_kind": item.target_kind,
            "module_code": item.module_code, "record_type": item.record_type, "method_code": item.method_code,
            "property_code": item.property_code, "core_schema": item.core_schema, "json_schema": item.json_schema,
            "ui_schema": item.ui_schema, "status": item.status, "checksum": item.checksum,
        } for _, item in sorted(definitions.items())],
    }
    return jsonable_encoder(payload)


@router.get("/{paper_id}/material-states/{state_key}/export")
def export_material_state(paper_id: int, state_key: str, db: Session = Depends(get_db), user: models.User | None = Depends(get_current_user_optional)):
    return build_material_state_export(db, paper_id=paper_id, state_key=state_key, user=user)
