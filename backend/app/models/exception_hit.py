from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class ExceptionHit(Base):
    """Append-only history: one row per scan that observed the registered key
    still violating the rule. ``suppressed=True`` means a valid exception kept
    the issue out of the todo board; ``suppressed=False`` means the exception
    had already lapsed (expired / invalidated / revoked) and an issue was raised.
    """

    __tablename__ = "exception_hits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exception_id: Mapped[int] = mapped_column(
        ForeignKey("rule_exceptions.id"), nullable=False, index=True
    )
    run_id: Mapped[int] = mapped_column(ForeignKey("rule_runs.id"), nullable=False, index=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("quality_rules.id"), nullable=False, index=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), nullable=False, index=True)
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    business_key: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    observed_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    # suppressed -> no Issue created; otherwise the exception had lapsed and an Issue was raised
    suppressed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    # exception status at hit time (active / expired / invalidated / revoked)
    exception_status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    detail: Mapped[str | None] = mapped_column(String(300), nullable=True)
    issue_id: Mapped[int | None] = mapped_column(ForeignKey("issues.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    exception = relationship("RuleException", back_populates="hits")
    run = relationship("RuleRun")
