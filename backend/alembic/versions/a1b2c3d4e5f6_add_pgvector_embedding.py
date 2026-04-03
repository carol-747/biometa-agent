"""add_pgvector_embedding

Revision ID: a1b2c3d4e5f6
Revises: d24496d347d9
Create Date: 2026-04-03 00:00:00.000000

Adds a native vector column to the articles table using the pgvector extension.
The migration is wrapped in a try/except so it degrades gracefully on databases
that do not have the pgvector extension installed (e.g. plain PostgreSQL, SQLite).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "d24496d347d9"
branch_labels = None
depends_on = None

VECTOR_DIM = 384  # matches all-MiniLM-L6-v2 output dimension


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect != "postgresql":
        # SQLite and others: skip silently
        return

    # Enable pgvector extension if not present
    try:
        conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
    except Exception as e:
        print(f"[pgvector migration] Could not create extension: {e}")
        return

    # Add vector column
    try:
        conn.execute(sa.text(
            f"ALTER TABLE articles ADD COLUMN IF NOT EXISTS "
            f"embedding_vector vector({VECTOR_DIM})"
        ))
    except Exception as e:
        print(f"[pgvector migration] Could not add column: {e}")
        return

    # Create approximate nearest-neighbour index (IVFFlat)
    # Requires at least one row with a non-null vector to build — skip if empty.
    try:
        row_count = conn.execute(
            sa.text("SELECT COUNT(*) FROM articles WHERE embedding_vector IS NOT NULL")
        ).scalar()
        if row_count and row_count > 0:
            conn.execute(sa.text(
                "CREATE INDEX IF NOT EXISTS ix_articles_embedding_vector "
                f"ON articles USING ivfflat (embedding_vector vector_cosine_ops) "
                f"WITH (lists = 100)"
            ))
        else:
            # Create a plain index that can be used without data
            conn.execute(sa.text(
                "CREATE INDEX IF NOT EXISTS ix_articles_embedding_vector "
                f"ON articles USING hnsw (embedding_vector vector_cosine_ops)"
            ))
    except Exception as e:
        print(f"[pgvector migration] Index creation skipped: {e}")


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    try:
        conn.execute(sa.text("DROP INDEX IF EXISTS ix_articles_embedding_vector"))
        conn.execute(sa.text("ALTER TABLE articles DROP COLUMN IF EXISTS embedding_vector"))
    except Exception as e:
        print(f"[pgvector downgrade] {e}")
