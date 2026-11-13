from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class DatasetKeyConfig(Base):
    """Business primary key chosen per dataset (one or several columns).

    Exceptions are keyed by the rendered value of these columns, so a data
    re-shuffle that changes ``row_index`` keeps the same exception as long as
    the business key value and the registered row snapshot stay unchanged.
    """

    __tablename__ = "dataset_key_configs"
    __table_args__ = (UniqueConstraint("dataset_id", name="uq_key_config_dataset"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), nullable=False, index=True)
    # ordered column names forming the business primary key, e.g. ["account_no"]
    key_columns_json: Mapped[list] = mapped_column(JSON, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    dataset = relationship("Dataset", back_populates="key_config")
