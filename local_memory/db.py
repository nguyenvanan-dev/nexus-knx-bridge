import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

class MemoryStore:
    def __init__(self, db_path: str = "data/agent_memory.sqlite3"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create main table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                wing TEXT,
                hall TEXT,
                room TEXT,
                raw_text TEXT NOT NULL,
                summary TEXT,
                tags TEXT,
                project TEXT,
                topic TEXT,
                device_name TEXT,
                group_address TEXT,
                dpt TEXT,
                importance INTEGER DEFAULT 1
            )
        ''')
        
        # Create FTS5 virtual table
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                raw_text, summary, tags, device_name, group_address, room,
                content='memories', content_rowid='id'
            )
        ''')
        
        # Triggers to keep FTS in sync
        cursor.executescript('''
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, raw_text, summary, tags, device_name, group_address, room)
                VALUES (new.id, new.raw_text, new.summary, new.tags, new.device_name, new.group_address, new.room);
            END;
            
            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, raw_text, summary, tags, device_name, group_address, room)
                VALUES('delete', old.id, old.raw_text, old.summary, old.tags, old.device_name, old.group_address, old.room);
            END;
            
            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, raw_text, summary, tags, device_name, group_address, room)
                VALUES('delete', old.id, old.raw_text, old.summary, old.tags, old.device_name, old.group_address, old.room);
                INSERT INTO memories_fts(rowid, raw_text, summary, tags, device_name, group_address, room)
                VALUES (new.id, new.raw_text, new.summary, new.tags, new.device_name, new.group_address, new.room);
            END;
        ''')
        
        conn.commit()
        conn.close()

    def add_memory(self, **kwargs) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        columns = ', '.join(kwargs.keys())
        placeholders = ', '.join(['?' for _ in kwargs])
        values = tuple(kwargs.values())
        
        cursor.execute(f'''
            INSERT INTO memories ({columns})
            VALUES ({placeholders})
        ''', values)
        
        memory_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return memory_id

    def search_memory(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Escape query for FTS5 to prevent syntax errors with characters like '/'
        safe_query = f'"{query}"'
        
        # FTS5 search
        cursor.execute('''
            SELECT m.* 
            FROM memories m
            JOIN memories_fts fts ON m.id = fts.rowid
            WHERE memories_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        ''', (safe_query, limit))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
        
    def get_important_memories(self, project: str, min_importance: int = 4, limit: int = 20) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM memories 
            WHERE project = ? AND importance >= ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (project, min_importance, limit))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
