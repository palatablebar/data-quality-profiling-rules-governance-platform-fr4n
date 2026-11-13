from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class RuleException(Base):
    """An approved exception registered for one rule on one business key.

    Identity is ``(rule_id, business_key)`` — re-running the scan over the same
    key never creates a second exception. The ``snapshot_json`` taken at
    registration time is compared on every scan: when the business fields
    change the exception is invalidated and the issue re-enters the todo board.
    """

    __tablename__ = "rule_exceptions"
    __table_args__ = (
        UniqueConstraint("rule_id", "business_key", name="uq_exception_rule_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("quality_rules.id"), nullable=False, index=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), nullable=False, index=True)
    # rendered business primary key value, columns joined by "|"
    business_key: Mapped[str] = mapped_column(String(500), nullable=False)
    key_columns_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # full row snapshot at registration time (column -> raw cell text)
    snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # approval evidence kept for the auditor
    approval_basis: Mapped[str] = mapped_column(Text, nullable=False, default="")
    approver: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    expire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # status: ExceptionStatus (active|expired|invalidated|revoked)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", index=True)
    # why the exception left the active state (expired / snapshot drift / manual revoke)
    close_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    rule = relationship("QualityRule")
    dataset = relationship("Dataset")
    creator = relationship("User", foreign_keys=[created_by])
    hits = relationship(
        "ExceptionHit",
        back_populates="exception",
        cascade="all, delete-orphan",
        order_by="ExceptionHit.id.desc()",
    )
