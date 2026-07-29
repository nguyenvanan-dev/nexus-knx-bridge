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


def fail(message: str, code: int = 1) -> None:
    print(f"Lỗi: {message}", file=sys.stderr)
    raise SystemExit(code)


def main():
    if not sys.stdin.isatty():
        input_data = sys.stdin.read()
        try:
            args = json.loads(input_data) if input_data.strip() else {}
        except json.JSONDecodeError as e:
            fail(f"Input JSON không hợp lệ: {e}", code=2)
    else:
        args = {}

    url = args.get("url", "")

    if not url:
        fail("Thiếu tham số url. Vui lòng cung cấp link hoặc đường dẫn file.", code=2)

    print(f"Đang phân tích tài liệu từ: {url}")
    print("Vui lòng đợi vài giây để AI bóc tách thông tin...\n")

    # Call the canonical implementation in tools/
    original_script = "/home/an/knx-bridge/tools/document_to_knx_skill.py"

    if not os.path.isfile(original_script):
        fail(f"Implementation không tồn tại: {original_script}")

    try:
        result = subprocess.run(
            ["/home/an/knx-bridge/.venv/bin/python", original_script, url],
            cwd="/home/an/knx-bridge",
            capture_output=True,
            text=True,
            timeout=180,
        )

        if result.stdout:
            print(result.stdout, end="")

        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)

        # Save to local memory on success
        if MemoryStore and result.returncode == 0:
            try:
                store = MemoryStore()
                store.add_memory(
                    wing="System",
                    hall="documents",
                    project="KNX",
                    topic="document_parsing",
                    raw_text=f"Đã đọc và tạo bản nháp (proposal) từ tài liệu: {url}",
                    importance=3,
                    tags="document, proposal",
                )
            except Exception:
                pass

        if result.returncode != 0:
            raise SystemExit(result.returncode)

    except SystemExit:
        raise
    except subprocess.TimeoutExpired:
        fail("Quá thời gian chờ (180s) khi phân tích tài liệu.")
    except Exception as e:
        fail(f"Lỗi khi chạy bộ phân tích: {e}")


if __name__ == "__main__":
    main()
