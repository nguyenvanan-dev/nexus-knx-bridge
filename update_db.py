import sqlite3

def init_db():
    conn = sqlite3.connect('smarthome.db')
    c = conn.cursor()
    # ai_conversations table
    c.execute("""
        CREATE TABLE IF NOT EXISTS ai_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Add new columns to ai_conversations (if not exists)
    try: c.execute("ALTER TABLE ai_conversations ADD COLUMN platform TEXT DEFAULT 'unknown'")
    except: pass
    try: c.execute("ALTER TABLE ai_conversations ADD COLUMN user_id TEXT")
    except: pass
    try: c.execute("ALTER TABLE ai_conversations ADD COLUMN message_id TEXT")
    except: pass
    try: c.execute("ALTER TABLE ai_conversations ADD COLUMN reply_to_message_id TEXT")
    except: pass

    # ai_memories table
    c.execute("""
        CREATE TABLE IF NOT EXISTS ai_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            importance INTEGER DEFAULT 1,
            confidence REAL DEFAULT 1.0,
            source TEXT DEFAULT 'system',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Add new columns to ai_memories (if not exists)
    try: c.execute("ALTER TABLE ai_memories ADD COLUMN summary_version INTEGER DEFAULT 1")
    except: pass
    try: c.execute("ALTER TABLE ai_memories ADD COLUMN source_message_start TEXT")
    except: pass
    try: c.execute("ALTER TABLE ai_memories ADD COLUMN source_message_end TEXT")
    except: pass
    try: c.execute("ALTER TABLE ai_memories ADD COLUMN model TEXT")
    except: pass
    try: c.execute("ALTER TABLE ai_memories ADD COLUMN created_by TEXT")
    except: pass

    conn.commit()
    conn.close()
    print("Database updated.")

if __name__ == "__main__":
    init_db()
