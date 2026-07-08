import re

with open("app.py", "r") as f:
    code = f.read()

# Add import
if "from core.ai_context import ContextBuilder" not in code:
    code = code.replace(
        "from core.event_bus import EventBus, DomainEvent, EventType",
        "from core.event_bus import EventBus, DomainEvent, EventType\nfrom core.ai_context import ContextBuilder"
    )

# Add global var
if "_context_builder = None" not in code:
    code = code.replace(
        "_notification_engine = None",
        "_notification_engine = None\n_context_builder = None"
    )

# Initialize
if "global _context_builder" not in code:
    init_code = """
    global _notification_engine
    global _context_builder

    _notification_engine = NotificationEngine(_event_bus, _state_manager, ZALO_ACCESS_TOKEN)
    _notification_engine.register()
    
    _context_builder = ContextBuilder(_state_manager, _event_bus, DB_PATH)
"""
    code = re.sub(
        r'global _notification_engine\n\s*_notification_engine = NotificationEngine\(_event_bus, _state_manager, ZALO_ACCESS_TOKEN\)\n\s*_notification_engine\.register\(\)',
        init_code,
        code
    )

# Update /api/ask-ai endpoint
ask_ai_old = """@app.post("/api/ask-ai")
async def ask_ai(request: AskAICommand):
    try:
        # Pass the message to openclaw CLI to use the agent
        cmd = [
            "openclaw", "agent", 
            "--session-key", "agent:main:dashboard_v2", 
            "--message", request.text, 
            "--json"
        ]"""

ask_ai_new = """@app.post("/api/ask-ai")
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

code = code.replace(ask_ai_old, ask_ai_new)

with open("app.py", "w") as f:
    f.write(code)
