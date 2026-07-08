with open("app.py", "a") as f:
    f.write("""
from pydantic import BaseModel
from typing import List, Optional, Any

class SceneAction(BaseModel):
    device: str
    action: str
    value: Optional[Any] = None

class ScenePayload(BaseModel):
    name: str
    description: Optional[str] = ""
    actions: List[SceneAction]

@app.get("/api/scenes")
async def get_scenes(current_user: dict = Depends(auth_utils.get_current_user)):
    import sqlite3
    conn = sqlite3.connect('smarthome.db')
    conn.row_factory = sqlite3.Row
    scenes_db = conn.execute("SELECT * FROM scenes").fetchall()
    
    result = {}
    for s in scenes_db:
        scene_id = str(s['id'])
        actions_db = conn.execute("SELECT * FROM scene_actions WHERE scene_id=?", (s['id'],)).fetchall()
        actions = []
        for a in actions_db:
            actions.append({
                "device": a["device_id"],
                "action": a["action"],
                "value": a["value"]
            })
        result[scene_id] = {
            "name": s["name"],
            "description": s["description"],
            "actions": actions
        }
    conn.close()
    return result

@app.post("/api/scenes")
async def create_scene(payload: ScenePayload, current_user: dict = Depends(auth_utils.require_admin)):
    import sqlite3
    conn = sqlite3.connect('smarthome.db')
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO scenes (name, description) VALUES (?, ?)", (payload.name, payload.description))
        scene_id = cursor.lastrowid
        for a in payload.actions:
            val_str = str(a.value) if a.value is not None else None
            cursor.execute("INSERT INTO scene_actions (scene_id, device_id, action, value) VALUES (?, ?, ?, ?)", 
                           (scene_id, a.device, a.action, val_str))
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))
    conn.close()
    return {"status": "success", "id": scene_id}

@app.put("/api/scenes/{scene_id}")
async def update_scene(scene_id: int, payload: ScenePayload, current_user: dict = Depends(auth_utils.require_admin)):
    import sqlite3
    conn = sqlite3.connect('smarthome.db')
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE scenes SET name=?, description=? WHERE id=?", (payload.name, payload.description, scene_id))
        cursor.execute("DELETE FROM scene_actions WHERE scene_id=?", (scene_id,))
        for a in payload.actions:
            val_str = str(a.value) if a.value is not None else None
            cursor.execute("INSERT INTO scene_actions (scene_id, device_id, action, value) VALUES (?, ?, ?, ?)", 
                           (scene_id, a.device, a.action, val_str))
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))
    conn.close()
    return {"status": "success"}

@app.delete("/api/scenes/{scene_id}")
async def delete_scene(scene_id: int, current_user: dict = Depends(auth_utils.require_admin)):
    import sqlite3
    conn = sqlite3.connect('smarthome.db')
    conn.execute("DELETE FROM scenes WHERE id=?", (scene_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}
""")

import os
filepath = "frontend/src/app/api/scenes/route.js"
with open(filepath, "r") as f:
    content = f.read()

content = content.replace("headers: HEADERS,", "headers: { ...HEADERS, ...authHeaders },")
with open(filepath, "w") as f:
    f.write(content)
