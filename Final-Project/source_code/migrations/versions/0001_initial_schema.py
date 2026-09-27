"""Initial schema: users, push_tokens, measurements, notifications_log (day 17).

Self-contained on purpose (no import of ``src.db``), so later model changes never rewrite
history. Times are ``timestamptz`` on PostgreSQL. ``test_db.py`` checks that this migration
matches the models exactly (``compare_metadata``) on SQLite and, if configured, PostgreSQL.

Revision ID: 0001
Revises:
Create Date: 2026-09-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ts(name: str, now: bool = True) -> sa.Column:
    """UTC-aware timestamp column (``DEFAULT now()`` when ``now``)."""
    default = sa.func.now() if now else None
    return sa.Column(name, sa.DateTime(timezone=True), server_default=default, nullable=False)


def upgrade() -> None:
    """Create the four tables with their constraints and indexes."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("skin_type", sa.String(length=3), nullable=False),
        sa.Column("province", sa.String(length=64), nullable=True),
        sa.Column("notify_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("alert_threshold", sa.Float(), server_default=sa.text("8"), nullable=False),
        sa.Column("safe_threshold", sa.Float(), server_default=sa.text("6"), nullable=False),
        sa.Column("alert_burn_minutes", sa.Integer(), server_default=sa.text("30"), nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.CheckConstraint(
            "skin_type IN ('I', 'II', 'III', 'IV', 'V', 'VI')", name=op.f("ck_users_skin_type")
        ),
        sa.CheckConstraint(
            "alert_threshold >= 1 AND alert_threshold <= 20", name=op.f("ck_users_alert_threshold")
        ),
        sa.CheckConstraint(
            "safe_threshold >= 0 AND safe_threshold < alert_threshold", name=op.f("ck_users_safe")
        ),
        sa.CheckConstraint(
            "alert_burn_minutes >= 5 AND alert_burn_minutes <= 240", name=op.f("ck_users_burn")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("device_id", name=op.f("uq_users_device_id")),
    )
    op.create_table(
        "push_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=10), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        _ts("created_at"),
        _ts("last_seen_at"),
        sa.CheckConstraint(
            "platform IN ('ios', 'android', 'web')", name=op.f("ck_push_tokens_platform")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_push_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_push_tokens")),
        sa.UniqueConstraint("token", name=op.f("uq_push_tokens_token")),
    )
    op.create_index("ix_push_tokens_user_id", "push_tokens", ["user_id"])
    op.create_table(
        "measurements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        _ts("measured_at", now=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("uvi", sa.Float(), nullable=True),
        sa.Column("uvi_lo", sa.Float(), nullable=True),
        sa.Column("uvi_hi", sa.Float(), nullable=True),
        sa.Column("uva_wm2", sa.Float(), nullable=True),
        sa.Column("uvb_wm2", sa.Float(), nullable=True),
        sa.Column("cmf", sa.Float(), nullable=True),
        sa.Column(
            "interval_adjusted", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("data_imputed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("lux", sa.Float(), nullable=True),
        sa.Column("sky_class", sa.String(length=32), nullable=True),
        sa.Column("sky_confidence", sa.Float(), nullable=True),
        sa.Column("cloud_fraction_rb", sa.Float(), nullable=True),
        sa.Column("openmeteo_uvi", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        _ts("created_at"),
        sa.CheckConstraint(
            "source IN ('api', 'phone_lux', 'sky_image', 'field')",
            name=op.f("ck_measurements_source"),
        ),
        sa.CheckConstraint(
            "lat >= -90 AND lat <= 90 AND lon >= -180 AND lon <= 180",
            name=op.f("ck_measurements_coords"),
        ),
        sa.CheckConstraint(
            "sky_confidence >= 0 AND sky_confidence <= 1",
            name=op.f("ck_measurements_sky_confidence"),
        ),
        sa.CheckConstraint(
            "cloud_fraction_rb >= 0 AND cloud_fraction_rb <= 1",
            name=op.f("ck_measurements_cloud_fraction_rb"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_measurements_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_measurements")),
    )
    op.create_index(
        "ix_measurements_user_id_measured_at", "measurements", ["user_id", "measured_at"]
    )
    op.create_index("ix_measurements_source_measured_at", "measurements", ["source", "measured_at"])
    op.create_table(
        "notifications_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("push_token_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=16), nullable=False),
        _ts("sent_at", now=False),
        sa.Column("uvi", sa.Float(), nullable=True),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("expo_ticket_id", sa.String(length=64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "type IN ('high_uv', 'safe_again', 'burn_time')", name=op.f("ck_notifications_log_type")
        ),
        sa.CheckConstraint("status IN ('sent', 'error')", name=op.f("ck_notifications_log_status")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_notifications_log_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["push_token_id"],
            ["push_tokens.id"],
            name=op.f("fk_notifications_log_push_token_id_push_tokens"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications_log")),
    )
    op.create_index(
        "ix_notifications_log_user_id_type_sent_at",
        "notifications_log",
        ["user_id", "type", "sent_at"],
    )
    op.create_index("ix_notifications_log_sent_at", "notifications_log", ["sent_at"])


def downgrade() -> None:
    """Drop the four tables (indexes go with them)."""
    op.drop_table("notifications_log")
    op.drop_table("measurements")
    op.drop_table("push_tokens")
    op.drop_table("users")
