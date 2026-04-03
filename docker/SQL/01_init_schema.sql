-- ==========================================
-- PostgreSQL Database Schema Initialization
-- AI Music Production Platform
-- ==========================================

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For full-text search support

-- Set timezone
SET timezone = 'UTC';

-- Enable UUID support
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

COMMENT ON DATABASE current_database IS 'AI Music Production Platform Database';
