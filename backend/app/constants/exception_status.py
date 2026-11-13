"""ExceptionStatus — approved exception lifecycle.

Mirrored by frontend/src/constants/exceptionStatus.ts.

* active      审批通过且在有效期内，命中的问题暂缓进待办；
* expired     超过 expire_date，下一次扫描命中即恢复待办；
* invalidated 业务主键仍在但登记时的行快照（业务字段）已变化，例外自动失效；
* revoked     人工撤销（登记有误 / 审批撤回）。
"""
from datetime import date
from enum import Enum


class ExceptionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"
    REVOKED = "revoked"


ALL_EXCEPTION_STATUSES = [s.value for s in ExceptionStatus]

# statuses that keep an exception row from being re-registered as a brand new one
CLOSED_STATUSES = (
    ExceptionStatus.EXPIRED.value,
    ExceptionStatus.INVALIDATED.value,
    ExceptionStatus.REVOKED.value,
)


def is_within_window(expire_date: date | None, today: date | None = None) -> bool:
    """An exception without an expire_date is treated as open-ended (still due)."""
    if expire_date is None:
        return True
    today = today or date.today()
    return expire_date >= today
