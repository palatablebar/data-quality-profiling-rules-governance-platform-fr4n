"""Approved-exception domain: business-key registration, snapshot validation and
scan-time suppression.

The engine stays thin — it calls :func:`classify_violation` for every sampled
violating row and lets this service decide whether an Issue is raised or an
ExceptionHit is recorded instead.
"""
from datetime import date, datetime

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.constants.error_codes import AppError, ErrorCode
from app.constants.exception_status import ExceptionStatus, is_within_window
from app.models import (
    Dataset,
    DatasetKeyConfig,
    ExceptionHit,
    Issue,
    QualityRule,
    RuleException,
    RuleRun,
    User,
)
from app.utils.logger import log_event
from app.utils.pagination import paginate_query

KEY_SEPARATOR = "|"


# --------------------------------------------------------------------------- #
# business key helpers
# --------------------------------------------------------------------------- #
def render_business_key(row, key_columns: list[str]) -> str | None:
    """Join the key columns of one row into a stable string.

    Returns ``None`` when any key cell is blank — such rows cannot be matched
    against a registered exception and must fall through to normal Issue flow.
    """
    values = [str(row.get(col, "")) for col in key_columns]
    if any(value.strip() == "" for value in values):
        return None
    return KEY_SEPARATOR.join(values)


def row_snapshot(df: pd.DataFrame, row_index: int) -> dict[str, str]:
    """Full business-field snapshot (column -> raw cell text) at scan time."""
    snapshot: dict[str, str] = {}
    for column in df.columns:
        value = df.loc[row_index, column]
        snapshot[str(column)] = "" if pd.isna(value) else str(value)
    return snapshot


def get_key_config(db: Session, dataset_id: int) -> DatasetKeyConfig | None:
    return (
        db.query(DatasetKeyConfig)
        .filter(DatasetKeyConfig.dataset_id == dataset_id)
        .first()
    )


def upsert_key_config(db: Session, dataset: Dataset, key_columns: list[str], actor: User) -> DatasetKeyConfig:
    columns = [str(col).strip() for col in (key_columns or []) if str(col).strip()]
    if not columns:
        raise AppError(
            ErrorCode.KEY_CONFIG_INVALID,
            message="业务主键至少选择一列",
            detail={"dataset_id": dataset.id},
        )
    if len(columns) != len(set(columns)):
        raise AppError(
            ErrorCode.KEY_CONFIG_INVALID,
            message="业务主键列不能重复",
            detail={"key_columns": columns},
        )
    # cheap structural validation against the file on disk
    from app.profiling.loader import load_frame

    loaded = load_frame(dataset.file_path, dataset.source_format)
    missing = [col for col in columns if col not in loaded.columns]
    if missing:
        raise AppError(
            ErrorCode.KEY_CONFIG_INVALID,
            message="业务主键列在数据集中不存在",
            detail={"missing": missing, "columns": list(loaded.columns)[:30]},
        )

    config = get_key_config(db, dataset.id)
    before_columns = list(config.key_columns_json) if config else []
    if config is None:
        config = DatasetKeyConfig(
            dataset_id=dataset.id,
            key_columns_json=columns,
            created_by=actor.id,
        )
        db.add(config)
    else:
        config.key_columns_json = columns
        config.created_by = actor.id

    # changing the identity axis invalidates every exception registered on the old key
    if before_columns and before_columns != columns:
        updated = (
            db.query(RuleException)
            .filter(
                RuleException.dataset_id == dataset.id,
                RuleException.status == ExceptionStatus.ACTIVE.value,
            )
            .all()
        )
        for exc in updated:
            _close(
                exc,
                ExceptionStatus.INVALIDATED.value,
                f"业务主键配置变更（{','.join(before_columns)} → {','.join(columns)}）",
            )
        log_event(
            "EXCEPTION_KEY_CONFIG_CHANGED",
            dataset_id=dataset.id,
            old_columns=",".join(before_columns),
            new_columns=",".join(columns),
            invalidated=len(updated),
        )
    db.commit()
    db.refresh(config)
    log_event(
        "EXCEPTION_KEY_CONFIG_SET",
        dataset_id=dataset.id,
        key_columns=",".join(columns),
        actor_id=actor.id,
    )
    return config


# --------------------------------------------------------------------------- #
# exception CRUD
# --------------------------------------------------------------------------- #
def _base_query(db: Session):
    return db.query(RuleException).options(
        joinedload(RuleException.rule),
        joinedload(RuleException.dataset),
        joinedload(RuleException.creator),
    )


def list_exceptions(
    db: Session,
    dataset_id: int | None = None,
    rule_id: int | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    sync_expired(db, dataset_id=dataset_id)
    query = _base_query(db)
    if dataset_id is not None:
        query = query.filter(RuleException.dataset_id == dataset_id)
    if rule_id is not None:
        query = query.filter(RuleException.rule_id == rule_id)
    if status:
        query = query.filter(RuleException.status == status)
    result = paginate_query(query.order_by(RuleException.id.desc()), page, page_size)
    return result


def get_exception(db: Session, exception_id: int) -> RuleException:
    exc = _base_query(db).filter(RuleException.id == exception_id).first()
    if exc is None:
        raise AppError(
            ErrorCode.EXCEPTION_NOT_FOUND,
            message="例外不存在",
            status_code=404,
            detail={"exception_id": exception_id},
        )
    return exc


def register_exception(
    db: Session,
    *,
    rule: QualityRule,
    row_index: int,
    approval_basis: str,
    approver: str,
    expire_date: date | None,
    actor: User,
) -> tuple[RuleException, bool]:
    """Register (or idempotently re-open) one exception.

    Returns ``(exception, created)``. Re-registering the same ``(rule, key)``
    never inserts a second row: an active row is returned untouched, while a
    lapsed row is revived with a fresh snapshot and approval evidence.
    """
    dataset = db.get(Dataset, rule.dataset_id)
    config = get_key_config(db, dataset.id)
    if config is None:
        raise AppError(
            ErrorCode.EXCEPTION_KEY_MISSING,
            message="该数据集尚未指定业务主键，无法登记例外",
            detail={"dataset_id": dataset.id},
        )
    from app.profiling.loader import load_frame

    loaded = load_frame(dataset.file_path, dataset.source_format)
    df = loaded.df
    if row_index not in df.index:
        raise AppError(
            ErrorCode.EXCEPTION_ROW_INVALID,
            message="row_index 在当前数据中不存在（数据可能已重排）",
            detail={"row_index": row_index, "row_count": loaded.row_count},
        )
    row = df.loc[row_index]
    business_key = render_business_key(row, list(config.key_columns_json))
    if business_key is None:
        raise AppError(
            ErrorCode.EXCEPTION_ROW_INVALID,
            message="该行的业务主键存在空值，不能登记例外",
            detail={"row_index": row_index, "key_columns": config.key_columns_json},
        )
    snapshot = row_snapshot(df, row_index)

    existing = (
        db.query(RuleException)
        .filter(RuleException.rule_id == rule.id, RuleException.business_key == business_key)
        .first()
    )
    if existing is not None:
        if existing.status == ExceptionStatus.ACTIVE.value and is_within_window(existing.expire_date):
            log_event(
                "EXCEPTION_DEDUPED",
                exception_id=existing.id,
                rule_id=rule.id,
                business_key=business_key,
            )
            return existing, False
        # lapsed row (expired / invalidated / revoked): revive the same identity
        existing.key_columns_json = list(config.key_columns_json)
        existing.snapshot_json = snapshot
        existing.approval_basis = approval_basis
        existing.approver = approver
        existing.expire_date = expire_date
        existing.status = ExceptionStatus.ACTIVE.value
        existing.close_reason = None
        existing.closed_at = None
        existing.created_by = actor.id
        db.commit()
        db.refresh(existing)
        log_event(
            "EXCEPTION_REOPENED",
            exception_id=existing.id,
            rule_id=rule.id,
            business_key=business_key,
        )
        return existing, False

    exc = RuleException(
        rule_id=rule.id,
        dataset_id=dataset.id,
        business_key=business_key,
        key_columns_json=list(config.key_columns_json),
        snapshot_json=snapshot,
        approval_basis=approval_basis,
        approver=approver,
        expire_date=expire_date,
        status=ExceptionStatus.ACTIVE.value,
        created_by=actor.id,
    )
    db.add(exc)
    db.commit()
    db.refresh(exc)
    log_event(
        "EXCEPTION_REGISTERED",
        exception_id=exc.id,
        rule_id=rule.id,
        dataset_id=dataset.id,
        business_key=business_key,
        expire_date=expire_date.isoformat() if expire_date else None,
    )
    return exc, True


def revoke_exception(db: Session, exc: RuleException, actor: User, reason: str | None) -> RuleException:
    if exc.status != ExceptionStatus.ACTIVE.value:
        raise AppError(
            ErrorCode.EXCEPTION_NOT_ACTIVE,
            message=f"例外当前状态为 {exc.status}，不能撤销",
            detail={"exception_id": exc.id, "status": exc.status},
        )
    _close(exc, ExceptionStatus.REVOKED.value, (reason or "人工撤销审批")[:300])
    db.commit()
    db.refresh(exc)
    log_event("EXCEPTION_REVOKED", exception_id=exc.id, actor_id=actor.id, reason=exc.close_reason)
    return exc


def list_hits(db: Session, exception_id: int, limit: int = 100) -> list[ExceptionHit]:
    return (
        db.query(ExceptionHit)
        .options(joinedload(ExceptionHit.run))
        .filter(ExceptionHit.exception_id == exception_id)
        .order_by(ExceptionHit.id.desc())
        .limit(min(limit, 200))
        .all()
    )


# --------------------------------------------------------------------------- #
# scan-time classification
# --------------------------------------------------------------------------- #
def build_exception_index(db: Session, rule_ids: list[int]) -> dict[tuple[int, str], RuleException]:
    if not rule_ids:
        return {}
    rows = db.query(RuleException).filter(RuleException.rule_id.in_(rule_ids)).all()
    return {(exc.rule_id, exc.business_key): exc for exc in rows}


def build_dataset_key_map(df: pd.DataFrame, key_columns: list[str]) -> dict[str, int]:
    """First row_index for each rendered business key — key columns are dataset-level,
    so one map serves every rule's recheck."""
    mapping: dict[str, int] = {}
    for idx in df.index:
        key = render_business_key(df.loc[idx], key_columns)
        if key is not None and key not in mapping:
            mapping[key] = int(idx)
    return mapping


def _close(exc: RuleException, status: str, reason: str) -> None:
    exc.status = status
    exc.close_reason = reason[:300]
    exc.closed_at = datetime.now()


def classify_violation(
    db: Session,
    *,
    df: pd.DataFrame,
    rule: QualityRule,
    run: RuleRun,
    row_index: int,
    observed: str,
    key_config: DatasetKeyConfig,
    exception_index: dict[tuple[int, str], RuleException],
    today: date | None = None,
) -> dict:
    """Decide what one sampled violating row becomes.

    Returns a dict:
      * ``{"kind": "issue", "business_key": ..., "exception": None | RuleException}``
      * ``{"kind": "suppressed", "business_key": ..., "exception": RuleException}``
    Side effects: flips lapsed exceptions, appends ExceptionHit rows.
    """
    today = today or date.today()
    key_columns = list(key_config.key_columns_json)
    row = df.loc[row_index]
    business_key = render_business_key(row, key_columns)
    if business_key is None:
        return {"kind": "issue", "business_key": None, "exception": None}

    exc = exception_index.get((rule.id, business_key))
    if exc is None:
        return {"kind": "issue", "business_key": business_key, "exception": None}

    # 1) expiry window
    if exc.status == ExceptionStatus.ACTIVE.value and not is_within_window(exc.expire_date, today):
        _close(exc, ExceptionStatus.EXPIRED.value, f"超过截止日期 {exc.expire_date.isoformat()}")
        log_event("EXCEPTION_EXPIRED", exception_id=exc.id, run_id=run.id, business_key=business_key)

    # 2) business-field drift against the registration snapshot
    drifted = False
    if exc.status == ExceptionStatus.ACTIVE.value:
        current = row_snapshot(df, row_index)
        if current != dict(exc.snapshot_json or {}):
            changed = [
                col
                for col in current
                if str(current.get(col, "")) != str((exc.snapshot_json or {}).get(col, ""))
            ]
            _close(exc, ExceptionStatus.INVALIDATED.value, f"业务字段变化：{', '.join(changed[:8])}")
            drifted = True
            log_event(
                "EXCEPTION_INVALIDATED",
                exception_id=exc.id,
                run_id=run.id,
                business_key=business_key,
                changed=",".join(changed[:8]),
            )

    if exc.status == ExceptionStatus.ACTIVE.value:
        db.add(
            ExceptionHit(
                exception_id=exc.id,
                run_id=run.id,
                rule_id=rule.id,
                dataset_id=rule.dataset_id,
                row_index=row_index,
                business_key=business_key,
                observed_value=(observed or "")[:2000],
                suppressed=True,
                exception_status=exc.status,
                detail="有效例外命中，问题暂缓",
            )
        )
        return {"kind": "suppressed", "business_key": business_key, "exception": exc}

    db.add(
        ExceptionHit(
            exception_id=exc.id,
            run_id=run.id,
            rule_id=rule.id,
            dataset_id=rule.dataset_id,
            row_index=row_index,
            business_key=business_key,
            observed_value=(observed or "")[:2000],
            suppressed=False,
            exception_status=exc.status,
            detail=exc.close_reason,
        )
    )
    log_event(
        "EXCEPTION_RESUMED",
        exception_id=exc.id,
        run_id=run.id,
        rule_id=rule.id,
        business_key=business_key,
        status=exc.status,
        drifted=drifted,
    )
    return {"kind": "issue", "business_key": business_key, "exception": exc}


def sync_expired(db: Session, dataset_id: int | None = None) -> int:
    """Flip active exceptions past their expire_date even without a new scan,
    so list/summary counts never overstate the active backlog."""
    today = date.today()
    query = db.query(RuleException).filter(RuleException.status == ExceptionStatus.ACTIVE.value)
    if dataset_id is not None:
        query = query.filter(RuleException.dataset_id == dataset_id)
    flipped = 0
    for exc in query.all():
        if exc.expire_date is not None and exc.expire_date < today:
            _close(exc, ExceptionStatus.EXPIRED.value, f"超过截止日期 {exc.expire_date.isoformat()}")
            flipped += 1
    if flipped:
        db.commit()
        log_event("EXCEPTION_EXPIRY_SYNC", flipped=flipped, dataset_id=dataset_id)
    return flipped


# --------------------------------------------------------------------------- #
# dashboard summary
# --------------------------------------------------------------------------- #
def summary(db: Session, dataset_id: int | None = None) -> dict:
    sync_expired(db, dataset_id=dataset_id)
    query = db.query(RuleException)
    if dataset_id is not None:
        query = query.filter(RuleException.dataset_id == dataset_id)
    rows = query.all()

    by_status = {status.value: 0 for status in ExceptionStatus}
    for exc in rows:
        by_status[exc.status] = by_status.get(exc.status, 0) + 1

    issue_query = (
        db.query(Issue)
        .join(RuleRun, Issue.rule_run_id == RuleRun.id)
        .filter(Issue.status.in_(["open", "triaged"]))
    )
    if dataset_id is not None:
        issue_query = issue_query.filter(RuleRun.dataset_id == dataset_id)
    pending_issues = issue_query.count()

    resumed_query = (
        db.query(func.count(func.distinct(Issue.id)))
        .join(RuleRun, Issue.rule_run_id == RuleRun.id)
        .filter(Issue.exception_id.isnot(None), Issue.status.in_(["open", "triaged"]))
    )
    if dataset_id is not None:
        resumed_query = resumed_query.filter(RuleRun.dataset_id == dataset_id)
    resumed_issues = int(resumed_query.scalar() or 0)

    return {
        "dataset_id": dataset_id,
        # 暂缓 = active exceptions currently holding issues back
        "suppressed": by_status.get(ExceptionStatus.ACTIVE.value, 0),
        # 到期恢复 = open issues re-raised because an exception lapsed
        "resumed": resumed_issues,
        # 待处理 = whole open/triaged todo board (resumed included)
        "pending": pending_issues,
        "by_status": by_status,
        "total": len(rows),
    }
