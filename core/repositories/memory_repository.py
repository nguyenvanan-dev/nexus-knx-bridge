import sqlite3
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class MemoryRepository:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _get_connection(self):
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_user_memory(self, user_id: str) -> List[Dict]:
        """Gets user preferences."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute('''
                SELECT key, value, importance, confidence, source, updated_at 
                FROM ai_memories 
                WHERE user_id = ? AND type = 'preference'
                ORDER BY confidence DESC, importance DESC
            ''', (user_id,))
            rows = c.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error fetching user memory: {e}")
            return []

    def get_latest_summary(self, session_id: str) -> Optional[Dict]:
        """Gets the most recent conversation summary."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute('''
                SELECT value, summary_version, source_message_start, source_message_end, model, updated_at 
                FROM ai_memories 
                WHERE user_id = ? AND type = 'session_summary' 
                ORDER BY id DESC LIMIT 1
            ''', (session_id,))
            row = c.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching summary: {e}")
            return None

    def save_summary(self, session_id: str, summary_text: str, version: int, 
                     start_msg: str, end_msg: str, model: str, created_by: str):
        """Saves a new conversation summary version."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute(
                """INSERT INTO ai_memories 
                   (user_id, type, key, value, summary_version, source_message_start, source_message_end, model, created_by) 
                   VALUES (?, 'session_summary', 'summary', ?, ?, ?, ?, ?, ?)""",
                (session_id, summary_text, version, start_msg, end_msg, model, created_by)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving summary: {e}")

    def save_preference(self, user_id: str, key: str, value: str, 
                        importance: int = 1, confidence: float = 1.0, source: str = 'system'):
        """Upserts a user preference."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            # Try to update existing first
            c.execute('''
                UPDATE ai_memories 
                SET value = ?, importance = ?, confidence = ?, source = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND type = 'preference' AND key = ?
            ''', (value, importance, confidence, source, user_id, key))
            
            if c.rowcount == 0:
                c.execute('''
                    INSERT INTO ai_memories (user_id, type, key, value, importance, confidence, source)
                    VALUES (?, 'preference', ?, ?, ?, ?, ?)
                ''', (user_id, key, value, importance, confidence, source))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving preference: {e}")

    def save_summaries_batch(self, summaries: List[Dict]):
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.executemany(
                """INSERT INTO ai_memories 
                   (user_id, type, key, value, summary_version, source_message_start, source_message_end, model, created_by) 
                   VALUES (?, 'session_summary', 'summary', ?, ?, ?, ?, ?, ?)""",
                [(s['session_id'], s['summary_text'], s['version'], s['start_msg'], s['end_msg'], s['model'], s['created_by']) for s in summaries]
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving summaries batch: {e}")

    def save_preferences_batch(self, preferences: List[Dict]):
        try:
            conn = self._get_connection()
            c = conn.cursor()
            for p in preferences:
                c.execute('''
                    UPDATE ai_memories 
                    SET value = ?, importance = ?, confidence = ?, source = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND type = 'preference' AND key = ?
                ''', (p['value'], p['importance'], p['confidence'], p['source'], p['user_id'], p['key']))
                if c.rowcount == 0:
                    c.execute('''
                        INSERT INTO ai_memories (user_id, type, key, value, importance, confidence, source)
                        VALUES (?, 'preference', ?, ?, ?, ?, ?)
                    ''', (p['user_id'], p['key'], p['value'], p['importance'], p['confidence'], p['source']))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving preferences batch: {e}")
