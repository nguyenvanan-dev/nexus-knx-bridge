import re

with open("app.py", "r") as f:
    code = f.read()

endpoint_code = """
@app.get("/api/ai/context")
async def get_ai_context():
    \"\"\"
    Endpoint dành riêng cho OpenClaw để kéo (pull) ngữ cảnh ngôi nhà 
    (trạng thái thiết bị, lịch sử sự kiện) trước khi trả lời.
    \"\"\"
    if not _context_builder:
        return {"error": "Context Builder not initialized"}
    
    import json
    # build_context() returns a json string, so we load it to return as JSON response
    return json.loads(_context_builder.build_context())

"""

if "@app.get(\"/api/ai/context\")" not in code:
    # Insert it before ask_ai
    code = code.replace("@app.post(\"/api/ask-ai\")", endpoint_code + "@app.post(\"/api/ask-ai\")")
    
with open("app.py", "w") as f:
    f.write(code)
