import os
import json
import sys
import requests
from dotenv import load_dotenv

def main():
    if not sys.stdin.isatty():
        input_data = sys.stdin.read()
        args = json.loads(input_data) if input_data else {}
    else:
        args = {}
    
    question = args.get("question", "")
    if not question:
        print("Lỗi: Không có câu hỏi được truyền vào.")
        return

    # Load from systemd override config or .env
    nvidia_api_key = os.getenv("OPENAI_API_KEY")
    if not nvidia_api_key:
        print("Lỗi: Không tìm thấy NVIDIA_API_KEY (OPENAI_API_KEY).")
        return

    try:
        response = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {nvidia_api_key}"
            },
            json={
                "model": "deepseek-ai/deepseek-v4-pro",
                "messages": [{"role": "user", "content": question}],
                "max_tokens": 1024
            },
            timeout=30
        )
        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            answer = data["choices"][0]["message"]["content"]
            print(f"[DeepSeek V4 Pro trả lời]:\n{answer}")
        else:
            print(f"Lỗi phản hồi từ NVIDIA NIM: {json.dumps(data)}")
    except Exception as e:
        print(f"Lỗi khi gọi Kỹ sư DeepSeek: {e}")

if __name__ == "__main__":
    main()
