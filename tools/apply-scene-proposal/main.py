import json
import sqlite3
import os
from pathlib import Path

db_path = str(Path(__file__).resolve().parent.parent.parent / "smarthome.db")
proposal_file = "/tmp/latest_scene_proposal.json"

def main():
    if not os.path.exists(proposal_file):
        print("Thưa Quản trị viên, không tìm thấy Bản Nháp (Proposal) nào đang chờ duyệt ở /tmp/.")
        return

    try:
        with open(proposal_file, "r") as f:
            proposal_data = json.load(f)
            
        payload = proposal_data.get("payload", {})
        name = payload.get("name")
        description = payload.get("description", "")
        actions = payload.get("actions", [])
        
        if not name or not actions:
            print("Thưa Quản trị viên, Bản Nháp này bị thiếu Tên kịch bản hoặc Danh sách hành động.")
            return

        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("INSERT INTO scenes (name, description) VALUES (?, ?)", (name, description))
        scene_id = c.lastrowid
        
        for a in actions:
            device = a.get("device", "")
            action = a.get("action", "on")
            value = str(a.get("value", ""))
            delay = float(a.get("delay_seconds", 0.0))
            
            c.execute(
                "INSERT INTO scene_actions (scene_id, device_id, action, value, delay_seconds, enabled) VALUES (?, ?, ?, ?, ?, 1)",
                (scene_id, device, action, value, delay)
            )
        
        conn.commit()
        conn.close()
        
        os.remove(proposal_file) # Dọn rác an toàn
        
        print(f"Báo cáo sếp, kịch bản '{name}' đã được LƯU VÀO DATABASE THÀNH CÔNG (ID: {scene_id}). Kính mời sếp F5 lại trang Web để nghiệm thu!")
        
    except Exception as e:
        print(f"Lỗi khi apply kịch bản vào Database: {e}")

if __name__ == "__main__":
    main()
