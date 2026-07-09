import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ConversationRepository:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _get_connection(self):
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def save_message(self, session_id: str, role: str, content: str, 
                     platform: str = 'unknown', user_id: str = None, 
                     message_id: str = None, reply_to_message_id: str = None) -> int:
        """Saves a message and returns the total messages in the session."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute(
                """INSERT INTO ai_conversations 
                   (session_id, role, content, platform, user_id, message_id, reply_to_message_id) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session_id, role, content, platform, user_id, message_id, reply_to_message_id)
            )
            conn.commit()
            
            c.execute("SELECT count(*) FROM ai_conversations WHERE session_id = ?", (session_id,))
            count = c.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return 0

    def get_recent_messages(self, session_id: str, limit: int = 100, since_minutes: int = 30) -> List[Dict]:
        """Gets recent messages for the thread builder."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            query = '''
                SELECT id, platform, session_id, user_id, message_id, reply_to_message_id, role, content, timestamp 
                FROM ai_conversations 
                WHERE session_id = ?
            '''
            params = [session_id]
            
            if since_minutes > 0:
                from datetime import timedelta
                time_threshold = (datetime.utcnow() - timedelta(minutes=since_minutes)).strftime("%Y-%m-%d %H:%M:%S")
                query += ' AND timestamp >= ?'
                params.append(time_threshold)
                
            query += ' ORDER BY timestamp ASC LIMIT ?'
            params.append(limit)
            
            c.execute(query, tuple(params))
            rows = c.fetchall()
            conn.close()
            
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error fetching recent messages: {e}")
            return []
