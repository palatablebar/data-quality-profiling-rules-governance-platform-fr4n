"""approved exceptions + per-dataset business key

Revision ID: 20261113_0002
Revises: 20261109_0001
Create Date: 2026-11-13

New tables: dataset_key_configs, rule_exceptions, exception_hits.
New columns: issues.business_key, issues.exception_id,
rule_run_items.suppressed_count, rule_runs.exceptions_suppressed,
rule_runs.exceptions_resumed.

Fresh installs still bootstrap via ``Base.metadata.create_all``; this migration
is written defensively (IF NOT EXISTS / add-if-missing) so it also works on a
database already created by the ORM.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

from app.config.database import Base
import app.models  # noqa: F401

revision = "20261113_0002"
down_revision = "20261109_0001"
branch_labels = None
depends_on = None

NEW_TABLES = ("dataset_key_configs", "rule_exceptions", "exception_hits")


def _existing_tables(bind) -> set[str]:
    return set(inspect(bind).get_table_names())


def _existing_columns(bind, table: str) -> set[str]:
    if table not in _existing_tables(bind):
        return set()
    return {column["name"] for column in inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    metadata = Base.metadata
    for table_name in NEW_TABLES:
        if table_name not in _existing_tables(bind):
            metadata.tables[table_name].create(bind)

    columns = {
        "issues": [
            ("business_key", sa.String(500), True),
            ("exception_id", sa.Integer(), True),
        ],
        "rule_run_items": [
            ("suppressed_count", sa.Integer(), False),
        ],
        "rule_runs": [
            ("exceptions_suppressed", sa.Integer(), False),
            ("exceptions_resumed", sa.Integer(), False),
        ],
    }
    for table_name, specs in columns.items():
        present = _existing_columns(bind, table_name)
        for name, column_type, nullable in specs:
            if name in present:
                continue
            op.add_column(table_name, sa.Column(name, column_type, nullable=nullable))
            if not nullable:
                op.execute(
                    f"UPDATE {table_name} SET {name} = 0 WHERE {name} IS NULL"
                )
    op.create_index(
        "ix_issues_business_key", "issues", ["business_key"], unique=False
    ) if "business_key" not in _existing_columns(bind, "issues") else None
    op.create_index(
        "ix_issues_exception_id", "issues", ["exception_id"], unique=False
    ) if "exception_id" not in _existing_columns(bind, "issues") else None


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index("ix_issues_exception_id", table_name="issues")
    op.drop_index("ix_issues_business_key", table_name="issues")
    op.drop_column("rule_runs", "exceptions_resumed")
    op.drop_column("rule_runs", "exceptions_suppressed")
    op.drop_column("rule_run_items", "suppressed_count")
    op.drop_column("issues", "exception_id")
    op.drop_column("issues", "business_key")
    for table_name in reversed(NEW_TABLES):
        if table_name in _existing_tables(bind):
            op.drop_table(table_name)
