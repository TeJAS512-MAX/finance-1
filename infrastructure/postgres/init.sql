-- PostgreSQL initialization script
-- Runs once when the container is first created.

-- Enable pgvector extension for embedding storage
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable pg_trgm for fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable uuid-ossp
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create audit log schema
CREATE SCHEMA IF NOT EXISTS audit;

GRANT ALL PRIVILEGES ON SCHEMA audit TO mi_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO mi_user;
