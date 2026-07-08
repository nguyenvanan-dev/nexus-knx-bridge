import re

with open('/home/an/knx-bridge/app.py', 'r') as f:
    content = f.read()

# Replace POST /api/users function
new_post_users = """
class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "Member"

@app.post("/api/users")
async def create_user(req: CreateUserRequest, current_user: dict = Depends(auth_utils.require_admin)):
    import sqlite3
    conn = sqlite3.connect('smarthome.db')
    try:
        pw_hash = auth_utils.get_password_hash(req.password)
        conn.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", (req.username, pw_hash, req.role))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
    conn.close()
    return {"status": "success", "message": "User created"}
"""

content = re.sub(
    r'@app\.post\("/api/users"\)\nasync def create_user\(req: LoginRequest, current_user: dict = Depends\(auth_utils\.require_admin\)\):\n.*?return \{"status": "success", "message": "User created"\}',
    new_post_users.strip(),
    content,
    flags=re.DOTALL
)

with open('/home/an/knx-bridge/app.py', 'w') as f:
    f.write(content)
