from datetime import date as date_cls

from sqlalchemy.orm import Session

from app.constants.messages import AUDIT_ACTIONS
from app.log_helpers import audit_event
from app.models import QualityRule, User
from app.schemas.exception import (
    serialize_exception,
    serialize_hit,
    serialize_key_config,
)
from app.services import dataset_service, exception_service


# --------------------------------------------------------------------------- #
# business primary key per dataset
# --------------------------------------------------------------------------- #
def get_key_config(db: Session, dataset_id: int) -> dict:
    dataset_service.get_dataset(db, dataset_id)
    config = exception_service.get_key_config(db, dataset_id)
    return {"config": serialize_key_config(config) if config else None}


def set_key_config(request, db: Session, user: User, dataset_id: int, payload) -> dict:
    dataset = dataset_service.get_dataset(db, dataset_id)
    config = exception_service.upsert_key_config(db, dataset, payload.key_columns, user)
    audit_event(
        request,
        AUDIT_ACTIONS["KEY_CONFIG_SET"],
        "DatasetKeyConfig",
        config.id,
        None,
        {"dataset_id": dataset_id, "key_columns": payload.key_columns},
    )
    return {"config": serialize_key_config(config)}


# --------------------------------------------------------------------------- #
# exceptions
# --------------------------------------------------------------------------- #
def list_exceptions(db: Session, **filters) -> dict:
    result = exception_service.list_exceptions(db, **filters)
    result["items"] = [serialize_exception(exc) for exc in result["items"]]
    return result


def summary(db: Session, dataset_id: int | None) -> dict:
    return exception_service.summary(db, dataset_id)


def get_exception(db: Session, exception_id: int) -> dict:
    exc = exception_service.get_exception(db, exception_id)
    return serialize_exception(exc, include_hits=True)


def list_hits(db: Session, exception_id: int) -> dict:
    exc = exception_service.get_exception(db, exception_id)
    hits = exception_service.list_hits(db, exc.id)
    return {"items": [serialize_hit(hit) for hit in hits], "total": len(hits)}


def register_exception(request, db: Session, user: User, payload) -> dict:
    rule = db.get(QualityRule, payload.rule_id)
    if rule is None:
        from app.constants.error_codes import AppError, ErrorCode

        raise AppError(ErrorCode.RULE_PARAMS_INVALID, message="规则不存在", status_code=404)
    expire = date_cls.fromisoformat(payload.expire_date) if payload.expire_date else None
    exc, created = exception_service.register_exception(
        db,
        rule=rule,
        row_index=payload.row_index,
        approval_basis=payload.approval_basis,
        approver=payload.approver,
        expire_date=expire,
        actor=user,
    )
    audit_event(
        request,
        AUDIT_ACTIONS["EXCEPTION_REGISTER"],
        "RuleException",
        exc.id,
        None,
        {
            "rule_id": exc.rule_id,
            "business_key": exc.business_key,
            "approval_basis": exc.approval_basis,
            "approver": exc.approver,
            "expire_date": payload.expire_date,
            "created": created,
        },
    )
    return serialize_exception(exc)


def revoke_exception(request, db: Session, user: User, exception_id: int, payload) -> dict:
    exc = exception_service.get_exception(db, exception_id)
    before = {"status": exc.status}
    exc = exception_service.revoke_exception(db, exc, user, payload.reason)
    audit_event(
        request,
        AUDIT_ACTIONS["EXCEPTION_REVOKE"],
        "RuleException",
        exc.id,
        before,
        {"status": exc.status, "reason": exc.close_reason},
    )
    return serialize_exception(exc)
