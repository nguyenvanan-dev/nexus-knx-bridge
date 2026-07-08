import json
import sys
import requests

def main():
    if not sys.stdin.isatty():
        input_data = sys.stdin.read()
        args = json.loads(input_data) if input_data else {}
    else:
        args = {}
    
    command_text = args.get("command_text", "")
    if not command_text:
        print("Lỗi: Không có command_text được truyền vào.")
        return

    try:
        response = requests.post(
            "http://127.0.0.1:5055/agent/command",
            headers={"Content-Type": "application/json", "x-knx-token": "REMOVED_CREDENTIAL"},
            json={"user_id": "zalo_agent", "text": command_text},
            timeout=10
        )
        data = response.json()
        print(data.get("message", json.dumps(data)))
    except Exception as e:
        print(f"Lỗi khi kết nối KNX Bridge: {e}")

if __name__ == "__main__":
    main()
