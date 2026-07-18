import sys
import json
import subprocess
import os

# Add knx-bridge to path so it can import local_memory
sys.path.append("/home/an/knx-bridge")

try:
    from local_memory.db import MemoryStore
except ImportError:
    MemoryStore = None

def main():
    if not sys.stdin.isatty():
        input_data = sys.stdin.read()
        args = json.loads(input_data) if input_data else {}
    else:
        args = {}
    
    url = args.get("url", "")
    
    if not url:
        print("Lỗi: Thiếu tham số 'url'. Vui lòng cung cấp link hoặc đường dẫn file.")
        return

    print(f"Đang phân tích tài liệu từ: {url}")
    print("Vui lòng đợi vài giây để AI bóc tách thông tin...\n")

    # Call the original script
    original_script = "/home/an/knx-bridge/tools/document_to_knx_skill.py"
    
    try:
        result = subprocess.run(
            ["/home/an/knx-bridge/.venv/bin/python", original_script, url],
            cwd="/home/an/knx-bridge",
            capture_output=True,
            text=True,
            timeout=180
        )
        
        output = result.stdout
        
        # Save to local memory
        if MemoryStore and result.returncode == 0:
            try:
                store = MemoryStore("/home/an/knx-bridge/data/agent_memory.sqlite3")
                store.add_memory(
                    wing="System",
                    hall="documents",
                    project="KNX",
                    topic="document_parsing",
                    raw_text=f"Đã đọc và tạo bản nháp (proposal) từ tài liệu: {url}",
                    importance=3,
                    tags="document, proposal"
                )
            except Exception as e:
                pass
                
        print(output)
        if result.stderr:
            print("\nCảnh báo/Lỗi hệ thống:\n", result.stderr)

    except Exception as e:
        print(f"Lỗi khi chạy bộ phân tích: {e}")

if __name__ == "__main__":
    main()
