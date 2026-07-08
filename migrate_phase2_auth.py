import sqlite3
import os
import argparse
import bcrypt

DB_PATH = 'smarthome.db'

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def migrate(db_path=DB_PATH):
    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Member',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("Ensured 'users' table exists.")

    # Check if admin user exists
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        print("Creating default 'admin' user...")
        default_pw_hash = hash_password('admin123')
        cursor.execute('''
            INSERT INTO users (username, password_hash, role)
            VALUES (?, ?, ?)
        ''', ('admin', default_pw_hash, 'Admin'))
        print("Default 'admin' user created with password 'admin123'.")
    else:
        print("'admin' user already exists.")

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate DB to add auth tables")
    parser.add_argument("--db", type=str, default=DB_PATH, help="Path to sqlite db file")
    args = parser.parse_args()
    
    if not os.path.exists(args.db):
        print(f"Warning: Database {args.db} does not exist. It will be created.")
    
    migrate(args.db)
