-- =============================================================================
-- Multi-Agentic Solution - Database Initialization
-- =============================================================================
-- This script initializes LangGraph checkpoint tables in PostgreSQL
-- Run this BEFORE Alembic migrations to set up LangGraph state persistence
-- =============================================================================

-- Create checkpoints table for LangGraph state persistence
-- This stores the full graph state at each checkpoint
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSON NOT NULL,
    metadata JSON NOT NULL DEFAULT '{}'::json,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

-- Create index on thread_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_checkpoints_thread_id
ON checkpoints(thread_id);

-- Create index on created_at for time-based queries
CREATE INDEX IF NOT EXISTS idx_checkpoints_created_at
ON checkpoints(created_at DESC);

-- Create index on parent_checkpoint_id for traversal
CREATE INDEX IF NOT EXISTS idx_checkpoints_parent
ON checkpoints(parent_checkpoint_id);

-- Create checkpoint_writes table for intermediate state writes
-- This stores individual writes that happen between checkpoints
CREATE TABLE IF NOT EXISTS checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    value JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

-- Create index on thread_id and checkpoint_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_checkpoint_writes_thread_checkpoint
ON checkpoint_writes(thread_id, checkpoint_id);

-- Create index on task_id
CREATE INDEX IF NOT EXISTS idx_checkpoint_writes_task_id
ON checkpoint_writes(task_id);

-- Add foreign key constraint (optional, but good for data integrity)
-- Commented out by default to allow independent table management
-- ALTER TABLE checkpoint_writes
-- ADD CONSTRAINT fk_checkpoint_writes_checkpoints
-- FOREIGN KEY (thread_id, checkpoint_ns, checkpoint_id)
-- REFERENCES checkpoints(thread_id, checkpoint_ns, checkpoint_id)
-- ON DELETE CASCADE;

-- Create Airflow database if it doesn't exist
-- This is needed for Airflow's metadata database
SELECT 'CREATE DATABASE airflow_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow_db')\gexec

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Display success message
DO $$
BEGIN
    RAISE NOTICE '✓ LangGraph checkpoint tables created successfully';
    RAISE NOTICE '✓ Indexes created for optimal query performance';
    RAISE NOTICE '✓ Database initialization complete';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Run Alembic migrations: make db-upgrade';
    RAISE NOTICE '  2. Verify tables: make shell-postgres';
    RAISE NOTICE '  3. Run health checks: make health';
END $$;

-- =============================================================================
-- End of init-db.sql
-- =============================================================================
