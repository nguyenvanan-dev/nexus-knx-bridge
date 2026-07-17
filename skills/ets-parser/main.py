import sys
import argparse
from pathlib import Path

# Thêm thư mục gốc vào đường dẫn thư viện để Import được module core
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Import thẳng Lõi Động cơ đã làm (ETSParser)
try:
    from core.knxproj_parser import ETSParser
except ImportError:
    print("Thưa Quản trị viên, không tìm thấy thư viện Lõi ETSParser. Hệ thống chưa sẵn sàng.")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Skill Bot: Đọc và bóc tách thiết bị từ file ETS")
    parser.add_argument("--file_path", required=True, help="Đường dẫn tới file .knxproj tải từ Zalo/Telegram")
    parser.add_argument("--password", default=None, help="Mật khẩu của file ETS (nếu có)")
    args = parser.parse_args()

    ets_parser = ETSParser()
    result = ets_parser.parse_project(args.file_path, args.password)

    if result.get("status") == "error":
        print(f"Thưa Quản trị viên, tôi không thể đọc được file này. Lỗi: {result.get('message')}")
        return

    devices = result.get("devices", [])
    total = len(devices)
    
    if total == 0:
        print("Thưa Quản trị viên, tôi đã phân tích file nhưng không tìm thấy thiết bị nào có địa chỉ G.A hợp lệ để nạp.")
        return

    # Phân loại thiết bị
    lights = sum(1 for d in devices if d.get("type") in ["light", "dimmer", "rgbw"])
    hvacs = sum(1 for d in devices if d.get("type") == "hvac")
    blinds = sum(1 for d in devices if d.get("type") == "blind")
    others = total - (lights + hvacs + blinds)

    # TUYỆT ĐỐI KHÔNG INSERT VÀO DATABASE Ở ĐÂY (ANTI-RISK)
    # Thay vào đó, trả ra câu hội thoại để Bot chat với Admin xin phép.
    
    message = (
        f"Thưa Quản trị viên, tôi đã bóc tách thành công {total} thiết bị "
        f"(bao gồm {lights} đèn, {hvacs} điều hòa, {blinds} rèm, {others} khác...). "
        f"Bạn có cho phép tôi nạp danh sách này đè lên Database không? (Yes/No)"
    )
    
    # In ra output để Bot đọc được
    print(message)

if __name__ == "__main__":
    main()
