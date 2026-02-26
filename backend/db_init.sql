-- Initial database setup (tables created by SQLAlchemy ORM on startup)
-- This file ensures the database is ready.

-- Enable pgcrypto extension for UUID support
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE biometa_db TO biometa;
