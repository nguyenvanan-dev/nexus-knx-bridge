import sys
import json
import os

# Add knx-bridge to path so it can import local_memory
sys.path.append("/home/an/knx-bridge")

try:
    from local_memory.db import MemoryStore
except ImportError as e:
    print(f"Lỗi: Không thể import local_memory. {e}")
    sys.exit(1)

def main():
    if not sys.stdin.isatty():
        input_data = sys.stdin.read()
        args = json.loads(input_data) if input_data else {}
    else:
        args = {}
    
    action = args.get("action", "")
    
    if not action:
        print("Lỗi: Thiếu tham số 'action'.")
        return

    store = MemoryStore("/home/an/knx-bridge/data/agent_memory.sqlite3")

    if action == "search":
        query = args.get("query", "")
        if not query:
            print("Lỗi: Thiếu tham số 'query' để tìm kiếm.")
            return
            
        results = store.search_memory(query, limit=5)
        if not results:
            print(f"Không tìm thấy thông tin nào trong Memory về: {query}")
        else:
            lines = []
            for r in results:
                location = f"[{r.get('wing', 'System')} -> {r.get('hall', 'notes')} -> {r.get('room', 'general')}]"
                lines.append(f"- {location} [Topic: {r.get('topic', 'general')}]: {r.get('raw_text', '')}")
            print(f"Kết quả tra cứu Memory cho '{query}':\n" + "\n".join(lines))
            
    elif action == "remember":
        content = args.get("content", "")
        topic = args.get("topic", "general")
        wing = args.get("wing", "System")
        hall = args.get("hall", "notes")
        room = args.get("room", "general")
        tags = args.get("tags", f"note, {topic}")
        importance = args.get("importance", 3)
        
        if not content:
            print("Lỗi: Thiếu tham số 'content' để ghi nhớ.")
            return
            
        mem_id = store.add_memory(
            wing=wing,
            hall=hall,
            room=room,
            project="General",
            topic=topic,
            raw_text=content,
            importance=importance,
            tags=tags
        )
        print(f"Đã lưu thành công vào Memory (ID: {mem_id}).")
        
    else:
        print(f"Lỗi: Hành động '{action}' không hợp lệ. Chỉ dùng 'search' hoặc 'remember'.")

if __name__ == "__main__":
    main()
