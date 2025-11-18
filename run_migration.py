"""Run database migration directly"""
import asyncio
import asyncpg

async def run_migration():
    """Apply the database migration"""
    conn = await asyncpg.connect(
        host='postgres',
        port=5432,
        user='postgres',
        password='postgres',
        database='agentic_db'
    )

    try:
        # Create alembic_version table if it doesn't exist
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(32) NOT NULL,
                CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
            )
        """)

        # Create metadata_extract table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS metadata_extract (
                id SERIAL PRIMARY KEY,
                metadata_id VARCHAR(64) NOT NULL UNIQUE,
                src_doc_name VARCHAR(512) NOT NULL,
                src_doc_path VARCHAR(512) NOT NULL,
                metadata_json JSON NOT NULL,
                description TEXT,
                status VARCHAR(32) NOT NULL DEFAULT 'uploaded',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_metadata_extract_status
            ON metadata_extract(status)
        """)

        # Create ddl_generated table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ddl_generated (
                id SERIAL PRIMARY KEY,
                metadata_id INTEGER NOT NULL REFERENCES metadata_extract(id),
                thread_id VARCHAR(128) NOT NULL,
                ddl_statement TEXT NOT NULL,
                ddl_file_path VARCHAR(512),
                validation_score FLOAT,
                accuracy_score FLOAT,
                validation_details JSON,
                feedback_iteration INTEGER NOT NULL DEFAULT 0,
                user_feedback TEXT,
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_ddl_generated_metadata_id
            ON ddl_generated(metadata_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_ddl_generated_thread_id
            ON ddl_generated(thread_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_ddl_generated_status
            ON ddl_generated(status)
        """)

        # Create testdata_generated table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS testdata_generated (
                id SERIAL PRIMARY KEY,
                metadata_id INTEGER NOT NULL REFERENCES metadata_extract(id),
                ddl_id INTEGER REFERENCES ddl_generated(id),
                thread_id VARCHAR(128) NOT NULL,
                file_path VARCHAR(512),
                synthetic_json JSON NOT NULL,
                row_count INTEGER,
                data_type VARCHAR(32),
                validation_score FLOAT,
                validation_details JSON,
                feedback_iteration INTEGER NOT NULL DEFAULT 0,
                user_feedback TEXT,
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_testdata_generated_metadata_id
            ON testdata_generated(metadata_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_testdata_generated_ddl_id
            ON testdata_generated(ddl_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_testdata_generated_thread_id
            ON testdata_generated(thread_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_testdata_generated_status
            ON testdata_generated(status)
        """)

        # Update alembic version
        await conn.execute("""
            INSERT INTO alembic_version (version_num) VALUES ('001')
            ON CONFLICT (version_num) DO NOTHING
        """)

        print("✓ Migration completed successfully!")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())
