"""MaterialState 完整 JSON 导出（Issue #90）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload

from backend import models
from backend.database import get_db
from backend.security import get_current_user_optional

router = APIRouter(prefix="/api/papers", tags=["material-state-export"])


def _can_view(paper: models.Paper, user: models.User | None) -> bool:
    if paper.review_status == "approved":
        return True
    return bool(user and (user.role in {"admin", "superadmin"} or paper.uploaded_by_user_id == user.id))


@router.get("/{paper_id}/material-states/{state_key}/export")
def export_material_state(paper_id: int, state_key: str, db: Session = Depends(get_db), user: models.User | None = Depends(get_current_user_optional)):
    state = db.query(models.MaterialState).options(
        joinedload(models.MaterialState.superconductor),
        joinedload(models.MaterialState.property_modules).joinedload(models.PropertyModule.records).joinedload(models.PropertyRecord.definition),
        joinedload(models.MaterialState.property_modules).joinedload(models.PropertyModule.records).joinedload(models.PropertyRecord.evidences),
        joinedload(models.MaterialState.property_modules).joinedload(models.PropertyModule.records),
        joinedload(models.MaterialState.structures),
    ).filter(models.MaterialState.paper_id == paper_id, models.MaterialState.id == int(state_key) if str(state_key).isdigit() else False).first()
    paper = db.query(models.Paper).filter(models.Paper.id == paper_id).first()
    if state is None or paper is None:
        raise HTTPException(status_code=404, detail={"code": "export_incomplete", "message": "材料状态不存在"})
    if not _can_view(paper, user):
        raise HTTPException(status_code=403, detail="无权导出该材料状态")
    modules = []
    definitions = {}
    for module in sorted(state.property_modules, key=lambda item: item.display_order):
        records = []
        for record in module.records:
            if not record.definition:
                raise HTTPException(status_code=409, detail={"code": "export_incomplete", "message": f"记录 {record.record_key} 缺少定义"})
            definitions[f"{record.definition_key}@{record.definition_version}"] = {
                "definition_key": record.definition.definition_key, "version": record.definition.version,
                "module_code": record.definition.module_code, "record_type": record.definition.record_type,
                "property_code": record.definition.property_code, "core_schema": record.definition.core_schema,
                "json_schema": record.definition.json_schema, "ui_schema": record.definition.ui_schema,
                "checksum": record.definition.checksum,
            }
            records.append({
                "record_key": record.record_key, "record_type": record.record_type, "property_code": record.property_code,
                "custom_property_key": record.custom_property_key, "definition_key": record.definition_key,
                "definition_version": record.definition_version, "name_raw": record.name_raw, "value_kind": record.value_kind,
                "value_raw": record.value_raw, "value_number": record.value_number, "value_min": record.value_min,
                "value_max": record.value_max, "value_text": record.value_text, "value_boolean": record.value_boolean,
                "uncertainty": record.uncertainty, "unit_raw": record.unit_raw, "canonical_unit": record.canonical_unit,
                "method_code": record.method_code, "is_representative": record.is_representative,
                "payload": record.payload_json or {}, "evidence_ids": [item.paper_evidence_id for item in record.evidences],
            })
        modules.append({"module_key": module.module_key, "module_code": module.module_code, "display_order": module.display_order, "records": records})
    payload = {
        "export_version": 1, "paper": {"id": paper.id, "revision": paper.content_revision, "doi": paper.doi, "title": paper.title},
        "material": {"id": state.superconductor.id if state.superconductor else None, "formula": state.superconductor.chemical_formula if state.superconductor else None},
        "material_state": {"id": state.id, "paper_id": state.paper_id, "paper_revision": state.paper_revision, "pressure_value_gpa": state.pressure_value_gpa, "temperature_value_k": state.temperature_value_k, "state_kind": state.state_kind, "structures": [{"id": item.id, "format": item.structure_format, "text": item.structure_text, "sha256": item.structure_hash} for item in state.structures]},
        "property_modules": modules, "definitions": list(definitions.values()),
    }
    return JSONResponse(payload)

