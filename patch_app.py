import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# Update get_ai_context to accept session_id and query
old_get_context = """@app.get("/api/ai/context")
async def get_ai_context():
    \"\"\"
    Endpoint dành riêng cho OpenClaw để kéo (pull) ngữ cảnh ngôi nhà 
    (trạng thái thiết bị, lịch sử sự kiện) trước khi trả lời.
    \"\"\"
    if not _context_builder:
        return {"error": "Context Builder not initialized"}
    
    import json
    # build_context() returns a json string, so we load it to return as JSON response
    return json.loads(_context_builder.build_context())"""

new_get_context = """@app.get("/api/ai/context")
async def get_ai_context(session_id: str = "default", query: str = ""):
    \"\"\"
    Endpoint dành riêng cho OpenClaw để kéo (pull) ngữ cảnh ngôi nhà 
    (trạng thái thiết bị, lịch sử sự kiện) trước khi trả lời.
    \"\"\"
    if not _context_builder:
        return {"error": "Context Builder not initialized"}
    
    import json
    return json.loads(_context_builder.build_context(session_id=session_id, query=query))"""

if old_get_context in content:
    content = content.replace(old_get_context, new_get_context)
else:
    print("Could not find get_ai_context to patch")

# Update AskAICommand
old_ask_command = """class AskAICommand(BaseModel):
    text: str"""
new_ask_command = """class AskAICommand(BaseModel):
    text: str
    session_id: str = "default\""""

if old_ask_command in content:
    content = content.replace(old_ask_command, new_ask_command)
else:
    print("Could not find AskAICommand to patch")

# Update ask_ai to save messages
old_ask_ai = """@app.post("/api/ask-ai")
async def ask_ai(request: AskAICommand):
    try:
        # AI will automatically pull context via /api/ai/context endpoint 
        # using the rule defined in IDENTITY.md
        
        # Pass the message to openclaw CLI to use the agent
        cmd = [
            "openclaw", "agent", 
            "--session-key", "agent:main:dashboard_v2", 
            "--message", request.text, 
            "--json"
        ]
        
        # Run process synchronously since openclaw handles its own timeouts
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            return {"reply": f"Lỗi AI: {result.stderr}"}
            
        try:
            # Parse OpenClaw output
            data = json.loads(result.stdout)
            reply = data.get("result", {}).get("meta", {}).get("finalAssistantVisibleText", "AI không trả lời được.")
            return {"reply": reply}
        except json.JSONDecodeError:
            return {"reply": f"Lỗi định dạng AI: {result.stdout}"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))"""

new_ask_ai = """@app.post("/api/ask-ai")
async def ask_ai(request: AskAICommand):
    try:
        if _context_builder:
            _context_builder.save_message(request.session_id, "user", request.text)

        cmd = [
            "openclaw", "agent", 
            "--session-key", request.session_id, 
            "--message", request.text, 
            "--json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            reply_text = f"Lỗi AI: {result.stderr}"
            if _context_builder:
                _context_builder.save_message(request.session_id, "system", reply_text)
            return {"reply": reply_text}
            
        try:
            data = json.loads(result.stdout)
            reply = data.get("result", {}).get("meta", {}).get("finalAssistantVisibleText", "AI không trả lời được.")
            
            # Layer 7: Reason from OpenClaw (if it outputs reason, we log it or parse it, here we assume reply is text)
            # The architecture requires reasoning, OpenClaw may output it as part of JSON.
            # Assuming OpenClaw's custom tool calls output reasoning. We just save the visible text.
            if _context_builder:
                _context_builder.save_message(request.session_id, "assistant", reply)
                
            return {"reply": reply}
        except json.JSONDecodeError:
            return {"reply": f"Lỗi định dạng AI: {result.stdout}"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))"""

if old_ask_ai in content:
    content = content.replace(old_ask_ai, new_ask_ai)
else:
    print("Could not find ask_ai to patch")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)
print("app.py patched")
