from local_memory.db import MemoryStore

store = MemoryStore()

def remember_error(service: str, error_text: str, cause: str = None, solution: str = None, severity: int = 3):
    raw_text = f"Lỗi {service}: {error_text}"
    if cause:
        raw_text += f"\nNguyên nhân: {cause}"
    if solution:
        raw_text += f"\nCách xử lý: {solution}"
        
    return store.add_memory(
        wing="System",
        hall="errors",
        project=service,
        topic="error",
        raw_text=raw_text,
        importance=severity,
        tags=f"error, {service}"
    )

def search_errors(query: str):
    return store.search_memory(query)
