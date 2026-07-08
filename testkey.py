#!/usr/bin/env python3
import os
import time
import json
import requests

BASE_URL = "https://integrate.api.nvidia.com/v1"

# Các keyword model muốn lọc
KEYWORDS = [
    "deepseek",
    "minimax",
    "qwen",
    "llama",
    "nemotron",
    "glm",
    "kimi",
    "mistral",
]

def get_api_key() -> str:
    api_key = "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"
    if not api_key:
        raise SystemExit(
            "Thiếu NVIDIA_API_KEY.\n"
            "Chạy: export NVIDIA_API_KEY='nvapi-...'\n"
            "Không hard-code key vào file."
        )
    return api_key

def headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

def list_models(api_key: str) -> list[str]:
    url = f"{BASE_URL}/models"
    resp = requests.get(url, headers=headers(api_key), timeout=60)

    if resp.status_code != 200:
        print("Lỗi khi lấy danh sách model:")
        print("HTTP:", resp.status_code)
        print(resp.text[:1000])
        raise SystemExit(1)

    data = resp.json()
    models = []

    for item in data.get("data", []):
        model_id = item.get("id")
        if model_id:
            models.append(model_id)

    return sorted(models)

def filter_models(models: list[str]) -> list[str]:
    result = []
    for model in models:
        lower = model.lower()
        if any(k in lower for k in KEYWORDS):
            result.append(model)
    return result

def test_chat_model(api_key: str, model: str) -> dict:
    url = f"{BASE_URL}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Bạn là bot test API. Chỉ trả lời cực ngắn."
            },
            {
                "role": "user",
                "content": "Trả lời đúng một từ: OK"
            }
        ],
        "max_tokens": 20,
        "temperature": 0.1,
    }

    start = time.time()

    try:
        resp = requests.post(
            url,
            headers=headers(api_key),
            json=payload,
            timeout=90,
        )
        elapsed = round(time.time() - start, 2)

        if resp.status_code != 200:
            return {
                "model": model,
                "ok": False,
                "status": resp.status_code,
                "time_sec": elapsed,
                "error": resp.text[:300],
            }

        data = resp.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

        return {
            "model": model,
            "ok": True,
            "status": resp.status_code,
            "time_sec": elapsed,
            "reply": content.strip(),
        }

    except Exception as e:
        elapsed = round(time.time() - start, 2)
        return {
            "model": model,
            "ok": False,
            "status": "exception",
            "time_sec": elapsed,
            "error": str(e),
        }

def main():
    api_key = get_api_key()

    print("=== NVIDIA NIM MODEL CHECK ===")
    print("Base URL:", BASE_URL)
    print()

    models = list_models(api_key)
    print(f"Tổng model key thấy được: {len(models)}")
    print()

    interesting = filter_models(models)

    print("=== Model đáng chú ý ===")
    for model in interesting:
        print(model)

    print()
    print("=== Test nhanh từng model đáng chú ý ===")

    results = []
    for model in interesting:
        print(f"Testing: {model}")
        result = test_chat_model(api_key, model)
        results.append(result)

        if result["ok"]:
            print(f"  OK | {result['time_sec']}s | {result.get('reply')}")
        else:
            print(f"  FAIL | {result['status']} | {result['time_sec']}s | {result.get('error')}")
        print()

    ok_models = [r for r in results if r["ok"]]
    ok_models = sorted(ok_models, key=lambda x: x["time_sec"])

    print("=== Model chạy được, xếp theo tốc độ ===")
    for r in ok_models:
        print(f"{r['time_sec']}s | {r['model']} | reply={r.get('reply')}")

    with open("nvidia_model_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print()
    print("Đã lưu kết quả vào: nvidia_model_test_results.json")
    print()
    print("Gợi ý thêm vào 9Router:")
    for r in ok_models[:8]:
        print(r["model"])

if __name__ == "__main__":
    main()