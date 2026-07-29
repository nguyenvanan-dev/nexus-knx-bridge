import sqlite3
import shutil
import time
import os
import argparse

DEFAULT_DB_PATH = 'smarthome.db'

def migrate(db_path=DEFAULT_DB_PATH, dry_run=True, confirm=False):
    if not os.path.exists(db_path):
        print(f"Error: Database '{db_path}' not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(devices)")
    columns = [col[1] for col in cursor.fetchall()]
    conn.close()

    new_columns = {
        'controller': 'TEXT',
        'line_code': 'TEXT',
        'dali_group': 'TEXT',
        'dali_address': 'TEXT',
        'power_feedback_ga': 'TEXT',
        'notes': 'TEXT'
    }

    missing_columns = {k: v for k, v in new_columns.items() if k not in columns}

    if not missing_columns:
        print("No migration needed, schema is up-to-date.")
        return

    print(f"Missing columns: {', '.join(missing_columns.keys())}")

    if dry_run or not confirm:
        print("[DRY-RUN] No changes were made. Pass --confirm to execute migration.")
        return

    backup_path = f"{db_path}.bak.{int(time.time())}"
    print(f"Backing up {db_path} to {backup_path}...")
    shutil.copy2(db_path, backup_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for col_name, col_type in missing_columns.items():
        print(f"Adding column '{col_name}'...")
        cursor.execute(f"ALTER TABLE devices ADD COLUMN {col_name} {col_type}")

    conn.commit()
    conn.close()
    print("Migration executed successfully.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Guarded migration for device metadata columns.")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Path to SQLite database file")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Dry run without modifying database")
    parser.add_argument("--confirm", action="store_true", default=False, help="Confirm execution of database migration")
    args = parser.parse_args()

    is_dry = args.dry_run or not args.confirm
    migrate(db_path=args.db_path, dry_run=is_dry, confirm=args.confirm)
