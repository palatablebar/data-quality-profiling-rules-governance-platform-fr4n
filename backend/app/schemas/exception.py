from pydantic import BaseModel, Field, field_validator

from app.constants.exception_status import ALL_EXCEPTION_STATUSES
from app.schemas.common import iso


class KeyConfigRequest(BaseModel):
    key_columns: list[str] = Field(min_length=1, max_length=8)

    @field_validator("key_columns")
    @classmethod
    def _strip(cls, values: list[str]) -> list[str]:
        cleaned = [str(v).strip() for v in values if str(v).strip()]
        if not cleaned:
            raise ValueError("业务主键至少选择一列")
        return cleaned


class ExceptionRegisterRequest(BaseModel):
    rule_id: int
    row_index: int = Field(ge=0)
    approval_basis: str = Field(min_length=2, max_length=2000)
    approver: str = Field(min_length=1, max_length=120)
    expire_date: str | None = Field(default=None, description="YYYY-MM-DD；留空表示长期有效")

    @field_validator("expire_date")
    @classmethod
    def _date_format(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        from datetime import date as date_cls

        try:
            date_cls.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("截止日期格式应为 YYYY-MM-DD") from exc
        return value


class ExceptionRevokeRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=300)


def serialize_key_config(config) -> dict:
    return {
        "id": config.id,
        "dataset_id": config.dataset_id,
        "key_columns": list(config.key_columns_json or []),
        "created_by": config.created_by,
        "created_at": iso(config.created_at),
        "updated_at": iso(config.updated_at),
    }


def serialize_exception(exc, include_hits: bool = False) -> dict:
    rule = getattr(exc, "rule", None)
    dataset = getattr(exc, "dataset", None)
    creator = getattr(exc, "creator", None)
    payload = {
        "id": exc.id,
        "rule_id": exc.rule_id,
        "rule_name": rule.name if rule else None,
        "rule_type": rule.rule_type if rule else None,
        "severity": rule.severity if rule else "medium",
        "column_name": rule.column_name if rule else None,
        "dataset_id": exc.dataset_id,
        "dataset_name": dataset.name if dataset else None,
        "business_key": exc.business_key,
        "key_columns": list(exc.key_columns_json or []),
        "snapshot": dict(exc.snapshot_json or {}),
        "approval_basis": exc.approval_basis,
        "approver": exc.approver,
        "expire_date": iso(exc.expire_date),
        "status": exc.status,
        "close_reason": exc.close_reason,
        "created_by": exc.created_by,
        "creator_name": creator.display_name if creator else None,
        "created_at": iso(exc.created_at),
        "updated_at": iso(exc.updated_at),
        "closed_at": iso(exc.closed_at),
    }
    if include_hits:
        payload["hits"] = [serialize_hit(hit) for hit in getattr(exc, "hits", [])]
    return payload


def serialize_hit(hit) -> dict:
    run = getattr(hit, "run", None)
    return {
        "id": hit.id,
        "exception_id": hit.exception_id,
        "run_id": hit.run_id,
        "report_no": run.report_no if run else None,
        "rule_id": hit.rule_id,
        "row_index": hit.row_index,
        "business_key": hit.business_key,
        "observed_value": hit.observed_value,
        "suppressed": hit.suppressed,
        "exception_status": hit.exception_status,
        "detail": hit.detail,
        "issue_id": hit.issue_id,
        "created_at": iso(hit.created_at),
    }


EXCEPTION_STATUS_LITERAL = tuple(ALL_EXCEPTION_STATUSES)
