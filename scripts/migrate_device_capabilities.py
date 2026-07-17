import sqlite3
import shutil
import time
import os
import argparse

DB_PATH = '/home/an/knx-bridge/smarthome.db'
if not os.path.exists(DB_PATH):
    DB_PATH = 'smarthome.db'

def migrate(dry_run=False):
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return False

    print(f"Target Database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check existing columns
    cursor.execute("PRAGMA table_info(devices)")
    columns = [col[1] for col in cursor.fetchall()]

    col_name = 'knx_config_payload'
    col_type = 'TEXT'

    if col_name not in columns:
        if dry_run:
            print("[Dry Run] Checking if migration is needed...")
            print(f"[Dry Run] Column '{col_name}' is missing. Migration IS needed.")
        else:
            # Only backup when running real migration
            backup_path = f'{DB_PATH}.bak.capabilities.{int(time.time())}'
            print(f"Backing up {DB_PATH} to {backup_path}...")
            shutil.copy2(DB_PATH, backup_path)

            print(f"Adding column '{col_name}'...")
            cursor.execute(f"ALTER TABLE devices ADD COLUMN {col_name} {col_type}")
            conn.commit()
            print("Migration successful.")
    else:
        if dry_run:
            print("[Dry Run] Checking if migration is needed...")
            print(f"Column '{col_name}' already exists. No migration needed.")
        else:
            print(f"Column '{col_name}' already exists. No migration needed.")

    conn.close()
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Migrate devices table to support knx_config_payload.")
    parser.add_argument("--dry-run", action="store_true", help="Check column status without applying any changes.")
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)
