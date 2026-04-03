"""
Alembic environment configuration for BiometaAgent.
Reads DATABASE_URL from the environment (or .env file) so the same
alembic.ini works in both local dev and Docker without edits.
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Make app importable from backend/ ────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.models import Base          # noqa: E402  import after sys.path fix
from app.core.config import get_settings  # noqa: E402

# ── Alembic Config object ─────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Point autogenerate at our ORM metadata ────────────────────────────────────
target_metadata = Base.metadata

# ── Resolve DB URL: env var wins over alembic.ini placeholder ─────────────────
def _get_url() -> str:
    # 1. Explicit ALEMBIC_DATABASE_URL override (useful in CI)
    url = os.getenv("ALEMBIC_DATABASE_URL")
    if url:
        return url
    # 2. App settings (reads .env file)
    try:
        return get_settings().database_url
    except Exception:
        pass
    # 3. Fall back to whatever is in alembic.ini
    return config.get_main_option("sqlalchemy.url", "")


def run_migrations_offline() -> None:
    """Generate SQL without a live DB connection (useful for review)."""
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations against a live DB connection."""
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _get_url()

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,         # detect column type changes
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
