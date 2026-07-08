from local_memory.db import MemoryStore

store = MemoryStore()

def build_wakeup_context(project: str = "KNX", max_tokens: int = 800) -> str:
    """
    Builds a summary of important information for the agent at the start of a session.
    """
    memories = store.get_important_memories(project=project, min_importance=4, limit=20)
    
    if not memories:
        return f"Không có dữ liệu quan trọng nào được ghi nhận cho dự án {project}."
        
    context = f"=== WAKEUP CONTEXT: {project} ===\n"
    context += "Những thông tin quan trọng nhất mà Agent cần nhớ:\n\n"
    
    current_length = len(context)
    # Rough estimation: 1 word ~ 1.3 tokens. 
    # Max length in chars approx: max_tokens * 4
    max_chars = max_tokens * 4
    
    for mem in memories:
        hall = mem.get("hall", "general")
        raw_text = mem.get("raw_text", "")
        
        entry = f"[{hall.upper()}] {raw_text}\n"
        if current_length + len(entry) > max_chars:
            context += "... (truncated due to token limit)\n"
            break
            
        context += entry
        current_length += len(entry)
        
    return context
