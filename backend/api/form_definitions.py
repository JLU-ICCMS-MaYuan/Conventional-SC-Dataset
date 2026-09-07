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
from backend.services import property_record_upgrade_service
from backend.ingest.property_modules import PropertyIssue, PropertyValidationError

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
    expected_paper_revision: int = Field(ge=1)
    source_checksum: str = Field(min_length=64, max_length=64)
    module_code: str
    value_kind: str
    canonical_unit: str | None = None
    description: str | None = None


class UpgradePreviewPayload(BaseModel):
    target_version: int = Field(ge=1)
    expected_paper_revision: int = Field(ge=1)
    payload: dict | None = None


class UpgradeApplyPayload(UpgradePreviewPayload):
    expected_record_checksum: str = Field(min_length=64, max_length=64)
    preview_checksum: str = Field(min_length=64, max_length=64)


class UpgradeRollbackPayload(BaseModel):
    event_id: int = Field(ge=1)
    expected_paper_revision: int = Field(ge=1)
    expected_record_checksum: str = Field(min_length=64, max_length=64)


def _error(exc: PropertyValidationError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.as_dict())


@router.get("")
def list_definitions(target_kind: str | None = None, module_code: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.FormDefinition).filter(models.FormDefinition.status == "published")
    if target_kind:
        query = query.filter(models.FormDefinition.target_kind == target_kind)
    if module_code:
        query = query.filter(models.FormDefinition.module_code == module_code)
    latest: dict[str, models.FormDefinition] = {}
    for item in query.order_by(models.FormDefinition.definition_key, models.FormDefinition.version).all():
        latest[item.definition_key] = item
    return [definition_to_dict(item) for item in latest.values()]


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


def _locked_record(db: Session, paper_id: int, record_key: str, expected_revision: int):
    paper = db.query(models.Paper).filter(models.Paper.id == paper_id).with_for_update().first()
    if paper is None:
        raise HTTPException(status_code=404, detail={"code": "paper_not_found", "message": "论文不存在"})
    if paper.content_revision != expected_revision:
        raise _error(PropertyValidationError([
            PropertyIssue("expected_paper_revision", "definition_upgrade_stale", "论文 revision 已变化")
        ]))
    record = db.query(models.PropertyRecord).filter_by(
        paper_id=paper_id, paper_revision=expected_revision, record_key=record_key,
    ).with_for_update().first()
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "record_not_found", "message": "物性记录不存在"})
    return paper, record


@promotion_router.post("/{paper_id}/property-records/{record_key}/definition-upgrade/preview")
def preview_definition_upgrade(paper_id: int, record_key: str, payload: UpgradePreviewPayload, user=Depends(get_current_superadmin), db: Session = Depends(get_db)):
    try:
        _, record = _locked_record(db, paper_id, record_key, payload.expected_paper_revision)
        target = db.query(models.FormDefinition).filter_by(definition_key=record.definition_key, version=payload.target_version).first()
        if target is None:
            raise HTTPException(status_code=404, detail={"code": "unknown_definition_version", "message": "目标定义不存在"})
        return property_record_upgrade_service.preview_upgrade(record, target, payload.payload)
    except PropertyValidationError as exc:
        raise _error(exc) from exc


@promotion_router.post("/{paper_id}/property-records/{record_key}/definition-upgrade/apply")
def apply_definition_upgrade(paper_id: int, record_key: str, payload: UpgradeApplyPayload, user=Depends(get_current_superadmin), db: Session = Depends(get_db)):
    try:
        paper, record = _locked_record(db, paper_id, record_key, payload.expected_paper_revision)
        target = db.query(models.FormDefinition).filter_by(definition_key=record.definition_key, version=payload.target_version).first()
        if target is None:
            raise HTTPException(status_code=404, detail={"code": "unknown_definition_version", "message": "目标定义不存在"})
        event = property_record_upgrade_service.apply_upgrade(db, record, target, user.id, payload.expected_record_checksum, payload.preview_checksum, payload.payload)
        db.commit()
        return {"upgrade_event_id": event.id, "paper_revision": paper.content_revision, "record_checksum": record.record_checksum}
    except PropertyValidationError as exc:
        db.rollback()
        raise _error(exc) from exc


@promotion_router.post("/{paper_id}/property-records/{record_key}/definition-upgrade/rollback")
def rollback_definition_upgrade(paper_id: int, record_key: str, payload: UpgradeRollbackPayload, user=Depends(get_current_superadmin), db: Session = Depends(get_db)):
    try:
        paper, record = _locked_record(db, paper_id, record_key, payload.expected_paper_revision)
        event = db.query(models.PropertyRecordDefinitionEvent).filter_by(id=payload.event_id, record_id=record.id).first()
        if event is None:
            raise HTTPException(status_code=404, detail={"code": "upgrade_event_not_found", "message": "升级事件不存在"})
        reverse = property_record_upgrade_service.rollback(db, record, event, user.id, payload.expected_record_checksum)
        db.commit()
        return {"upgrade_event_id": reverse.id, "paper_revision": paper.content_revision, "record_checksum": record.record_checksum}
    except PropertyValidationError as exc:
        db.rollback()
        raise _error(exc) from exc


@promotion_router.post("/{paper_id}/property-records/{record_key}/promote-definition", status_code=201)
def promote_definition(paper_id: int, record_key: str, payload: PromotionPayload, user=Depends(get_current_admin), db: Session = Depends(get_db)):
    try:
        result = form_definition_service.promote_custom_property(db, paper_id=paper_id, record_key=record_key, actor_id=user.id, **payload.model_dump())
        db.commit()
        return result
    except PropertyValidationError as exc:
        db.rollback()
        raise _error(exc) from exc
