import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def optimize_database(db_path: str):
    """
    Apply SQLite performance optimizations and ensure necessary indices exist.
    """
    logger.info(f"Optimizing database: {db_path}")
    if not Path(db_path).exists():
        logger.warning(f"Database {db_path} does not exist yet. Skipping optimization.")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. Enable WAL mode for concurrency and performance
        cursor.execute("PRAGMA journal_mode=WAL;")
        wal_result = cursor.fetchone()
        logger.info(f"Database journal_mode is now: {wal_result[0] if wal_result else 'unknown'}")

        # 2. Relax synchronous mode since WAL handles corruption better
        cursor.execute("PRAGMA synchronous=NORMAL;")

        # 3. Increase cache size
        cursor.execute("PRAGMA cache_size=-64000;") # 64MB

        # 4. Create missing indices
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_user_type ON ai_memories(user_id, type)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_session ON ai_conversations(session_id)"
        )
        
        conn.commit()
        conn.close()
        logger.info("Database optimization completed successfully.")
    except Exception as e:
        logger.error(f"Failed to optimize database: {e}")
