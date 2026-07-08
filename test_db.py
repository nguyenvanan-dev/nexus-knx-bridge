import sqlite3
import json

db_path = 'smarthome.db'

def get_count():
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]

print(f"Device Count: {get_count()}")

def get_audit():
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        logs = conn.execute("SELECT * FROM command_audit ORDER BY timestamp DESC LIMIT 3").fetchall()
        for log in logs:
            print(dict(log))

print("Recent Audit Logs:")
get_audit()
