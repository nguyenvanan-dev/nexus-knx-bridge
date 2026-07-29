import sys
import urllib.request
import json


def fail(message: str, code: int = 1) -> None:
    print(f"Lỗi: {message}", file=sys.stderr)
    raise SystemExit(code)


def main():
    url = "https://api.open-meteo.com/v1/forecast?latitude=21.0285&longitude=105.8542&current_weather=true"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())

        current = data.get("current_weather")
        if current is None:
            fail("API trả về dữ liệu không hợp lệ (thiếu current_weather).")

        temp = current.get("temperature", 25.0)
        weather_code = current.get("weathercode", 0)

        # WMO Weather interpretation codes
        condition = "Trời Nắng / Ít mây"
        if weather_code >= 50:
            condition = "Trời Mưa / Có bão"
        elif 3 < weather_code < 50:
            condition = "Trời Nhiều mây / Sương mù"

        print(f"THÔNG TIN THỜI TIẾT HIỆN TẠI (Hà Nội):")
        print(f"- Nhiệt độ: {temp}°C")
        print(f"- Trạng thái: {condition} (Mã WMO: {weather_code})")
        print("\nGỢI Ý CHO BOT:")
        print(
            "Dựa vào thông tin này, bạn hãy tự động suy luận và gọi tool "
            "`scene-creator` để tạo một Kịch bản (Scene) bảo vệ ngôi nhà hoặc "
            "tăng tiện nghi. Ví dụ: Trời mưa thì tự đóng rèm, tắt đèn sân "
            "vườn. Trời nắng thì bật điều hòa, kéo rèm che nắng."
        )

    except SystemExit:
        raise
    except Exception as e:
        fail(f"Lỗi khi lấy thông tin thời tiết: {e}")


if __name__ == "__main__":
    main()
