with open("app.py", "r") as f:
    code = f.read()

ask_ai_current = """@app.post("/api/ask-ai")
async def ask_ai(request: AskAICommand):
    try:
        # Build Real-time Context
        context_str = _context_builder.build_context() if _context_builder else "{}"
        
        # Inject context directly into the prompt transparently
        # Format it so the LLM clearly distinguishes context from user prompt
        injected_text = f"[[SYSTEM_REALTIME_CONTEXT: {context_str}]]\\n\\nUser Request: {request.text}"
        
        # Pass the message to openclaw CLI to use the agent
        cmd = [
            "openclaw", "agent", 
            "--session-key", "agent:main:dashboard_v2", 
            "--message", injected_text, 
            "--json"
        ]"""

ask_ai_new = """@app.post("/api/ask-ai")
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
        ]"""

code = code.replace(ask_ai_current, ask_ai_new)

with open("app.py", "w") as f:
    f.write(code)
