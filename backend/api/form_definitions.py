"""FormDefinition 与 PropertyRecord 管理 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend import models
from backend.database import get_db
from backend.security import get_current_admin, get_current_superadmin
from backend.ingest.form_definitions import definition_to_dict
from backend.services import form_definition_service
from backend.ingest.property_modules import PropertyValidationError

router = APIRouter(prefix="/api/form-definitions", tags=["form-definitions"])
admin_router = APIRouter(prefix="/api/admin/form-definitions", tags=["form-definitions-admin"])
promotion_router = APIRouter(prefix="/api/admin/papers", tags=["form-definitions-admin"])


class DefinitionPayload(BaseModel):
    target_kind: str = "property_record"
    module_code: str
    record_type: str | None = None
    method_code: str | None = None
    property_code: str | None = None
    core_schema: dict = Field(default_factory=dict)
    json_schema: dict = Field(default_factory=dict)
    ui_schema: dict = Field(default_factory=dict)


class PromotionPayload(BaseModel):
    operation_id: str = Field(min_length=1, max_length=64)
    target_property_code: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=255)
    description: str | None = None


def _error(exc: PropertyValidationError) -> HTTPException:
    return HTTPException(status_code=400, detail=exc.as_dict())


@router.get("")
def list_definitions(target_kind: str | None = None, module_code: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.FormDefinition).filter(models.FormDefinition.status.in_(["published", "retired"]))
    if target_kind:
        query = query.filter(models.FormDefinition.target_kind == target_kind)
    if module_code:
        query = query.filter(models.FormDefinition.module_code == module_code)
    return [definition_to_dict(item) for item in query.order_by(models.FormDefinition.definition_key, models.FormDefinition.version).all()]


@router.get("/{definition_key:path}/current")
def current_definition(definition_key: str, db: Session = Depends(get_db)):
    item = db.query(models.FormDefinition).filter_by(definition_key=definition_key, status="published").order_by(models.FormDefinition.version.desc()).first()
    if item is None:
        raise HTTPException(status_code=404, detail={"code": "unknown_definition_version", "message": "定义不存在"})
    return definition_to_dict(item)


@router.get("/{definition_key:path}/versions/{version}")
def definition_version(definition_key: str, version: int, db: Session = Depends(get_db)):
    item = db.query(models.FormDefinition).filter_by(definition_key=definition_key, version=version).first()
    if item is None or item.status not in {"published", "retired"}:
        raise HTTPException(status_code=404, detail={"code": "unknown_definition_version", "message": "定义版本不存在"})
    return definition_to_dict(item)


@admin_router.post("/{definition_key:path}/versions", status_code=201)
def create_definition(definition_key: str, payload: DefinitionPayload, user=Depends(get_current_superadmin), db: Session = Depends(get_db)):
    try:
        item = form_definition_service.create_definition(db, {**payload.model_dump(), "definition_key": definition_key}, user.id)
        db.commit()
        return definition_to_dict(item)
    except PropertyValidationError as exc:
        db.rollback()
        raise _error(exc) from exc


@admin_router.post("/{definition_key:path}/versions/{version}/publish")
def publish_definition(definition_key: str, version: int, user=Depends(get_current_superadmin), db: Session = Depends(get_db)):
    item = db.query(models.FormDefinition).filter_by(definition_key=definition_key, version=version).first()
    if item is None:
        raise HTTPException(status_code=404, detail="定义不存在")
    try:
        form_definition_service.publish_definition(db, item, user.id)
        db.commit()
        return definition_to_dict(item)
    except PropertyValidationError as exc:
        db.rollback()
        raise _error(exc) from exc


@admin_router.put("/{definition_key:path}/versions/{version}")
def update_definition(definition_key: str, version: int, payload: DefinitionPayload, user=Depends(get_current_superadmin), db: Session = Depends(get_db)):
    item = db.query(models.FormDefinition).filter_by(definition_key=definition_key, version=version).first()
    if item is None:
        raise HTTPException(status_code=404, detail="定义不存在")
    if item.status != "draft":
        raise HTTPException(status_code=409, detail={"code": "definition_not_available", "message": "已发布定义不可修改"})
    try:
        form_definition_service.validate_definition_payload(payload.model_dump())
        for key, value in payload.model_dump().items():
            setattr(item, key, value)
        item.checksum = form_definition_service.definition_checksum({"definition_key": item.definition_key, "version": item.version, **payload.model_dump()})
        db.commit()
        return definition_to_dict(item)
    except PropertyValidationError as exc:
        db.rollback()
        raise _error(exc) from exc


@admin_router.post("/{definition_key:path}/versions/{version}/retire")
def retire_definition(definition_key: str, version: int, user=Depends(get_current_superadmin), db: Session = Depends(get_db)):
    item = db.query(models.FormDefinition).filter_by(definition_key=definition_key, version=version).first()
    if item is None:
        raise HTTPException(status_code=404, detail="定义不存在")
    try:
        form_definition_service.retire_definition(db, item)
        db.commit()
        return definition_to_dict(item)
    except PropertyValidationError as exc:
        db.rollback()
        raise _error(exc) from exc


router_admin_alias = admin_router


@promotion_router.post("/{paper_id}/property-records/{record_key}/promote-definition", status_code=201)
def promote_definition(paper_id: int, record_key: str, payload: PromotionPayload, user=Depends(get_current_admin), db: Session = Depends(get_db)):
    try:
        result = form_definition_service.promote_custom_property(db, paper_id=paper_id, record_key=record_key, actor_id=user.id, operation_id=payload.operation_id, target_property_code=payload.target_property_code, display_name=payload.display_name, description=payload.description)
        db.commit()
        return result
    except PropertyValidationError as exc:
        db.rollback()
        raise _error(exc) from exc
