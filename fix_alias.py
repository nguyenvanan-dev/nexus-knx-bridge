import sqlite3
import json

db_path = "/home/an/knx-bridge/smarthome.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT metadata FROM devices WHERE id = 'g1_den_tran'")
row = cursor.fetchone()
if row:
    meta = json.loads(row[0])
    if "đèn dali" not in meta.get("aliases", []):
        meta.setdefault("aliases", []).append("đèn dali")
        cursor.execute("UPDATE devices SET metadata = ? WHERE id = 'g1_den_tran'", (json.dumps(meta, ensure_ascii=False),))
        conn.commit()
        print("Updated metadata.")
    else:
        print("Already has alias.")
conn.close()
