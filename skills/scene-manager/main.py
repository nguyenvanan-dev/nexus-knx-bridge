from pathlib import Path
import sqlite3
import json
import sys
import os

DB_PATH = os.getenv("DB_PATH", str(Path(__file__).resolve().parent.parent.parent / "smarthome.db"))

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def load_scenes():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description FROM scenes")
    rows = cursor.fetchall()
    
    scenes = {}
    for row in rows:
        scene_id = row['id']
        name = row['name']
        description = row['description']
        
        cursor.execute("SELECT device_id, action, value FROM scene_actions WHERE scene_id = ?", (scene_id,))
        actions = []
        for action_row in cursor.fetchall():
            act = {
                "device": action_row['device_id'],
                "action": action_row['action']
            }
            if action_row['value'] is not None:
                # Try to parse numeric values if possible
                try:
                    if '.' in action_row['value']:
                        act['value'] = float(action_row['value'])
                    else:
                        act['value'] = int(action_row['value'])
                except ValueError:
                    act['value'] = action_row['value']
            actions.append(act)
            
        scenes[name] = {
            "description": description,
            "actions": actions
        }
        
    conn.close()
    return scenes

def save_scene(name, data):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("INSERT OR IGNORE INTO scenes (name, description) VALUES (?, ?)", (name, data.get("description", "")))
    cursor.execute("SELECT id FROM scenes WHERE name = ?", (name,))
    scene_id = cursor.fetchone()['id']
    
    # Update description if it changed
    cursor.execute("UPDATE scenes SET description = ? WHERE id = ?", (data.get("description", ""), scene_id))
    
    cursor.execute("DELETE FROM scene_actions WHERE scene_id = ?", (scene_id,))
    
    for action in data.get("actions", []):
        val = action.get("value")
        if val is not None:
            val = str(val)
        cursor.execute("INSERT INTO scene_actions (scene_id, device_id, action, value) VALUES (?, ?, ?, ?)",
                       (scene_id, action.get("device", ""), action.get("action", ""), val))
                       
    conn.commit()
    conn.close()

def delete_scene(name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM scenes WHERE name = ?", (name,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def main():
    if not sys.stdin.isatty():
        input_data = sys.stdin.read()
        args = json.loads(input_data) if input_data else {}
    else:
        args = {}

    action = args.get("action")
    scene_name = args.get("scene_name", "").strip()
    scene_data_raw = args.get("scene_data", "{}")

    if not action:
        print(json.dumps({"error": "Thiếu tham số 'action'."}, ensure_ascii=False))
        return

    if action == "list":
        scenes = load_scenes()
        print(json.dumps({"scenes": list(scenes.keys())}, ensure_ascii=False))
    
    elif action == "get":
        if not scene_name:
            print(json.dumps({"error": "Thiếu 'scene_name'."}, ensure_ascii=False))
            return
        scenes = load_scenes()
        if scene_name in scenes:
            print(json.dumps({"scene_name": scene_name, "data": scenes[scene_name]}, ensure_ascii=False))
        else:
            print(json.dumps({"error": f"Không tìm thấy kịch bản '{scene_name}'."}, ensure_ascii=False))
            
    elif action == "save":
        if not scene_name:
            print(json.dumps({"error": "Thiếu 'scene_name'."}, ensure_ascii=False))
            return
        try:
            scene_data = json.loads(scene_data_raw) if isinstance(scene_data_raw, str) else scene_data_raw
        except Exception:
            print(json.dumps({"error": "Dữ liệu 'scene_data' không phải là JSON hợp lệ."}, ensure_ascii=False))
            return
            
        save_scene(scene_name, scene_data)
        print(json.dumps({"status": "success", "message": f"Đã lưu kịch bản '{scene_name}' vào Database."}, ensure_ascii=False))
        
    elif action == "delete":
        if not scene_name:
            print(json.dumps({"error": "Thiếu 'scene_name'."}, ensure_ascii=False))
            return
        if delete_scene(scene_name):
            print(json.dumps({"status": "success", "message": f"Đã xóa kịch bản '{scene_name}' khỏi Database."}, ensure_ascii=False))
        else:
            print(json.dumps({"error": f"Không tìm thấy kịch bản '{scene_name}'."}, ensure_ascii=False))
    else:
        print(json.dumps({"error": f"Hành động '{action}' không hợp lệ."}, ensure_ascii=False))

if __name__ == "__main__":
    main()
