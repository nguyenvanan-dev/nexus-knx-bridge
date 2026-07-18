import sys
import argparse
import json
from pathlib import Path

# Thêm thư mục gốc vào đường dẫn thư viện để Import được module core
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Import thẳng Lõi Động cơ đã làm (ETSParser)
try:
    from core.knxproj_parser import ETSParser
    has_parser = True
except ImportError:
    has_parser = False

def _parse_input():
    # check stdin
    if not sys.stdin.isatty():
        try:
            stdin_data = sys.stdin.read().strip()
            if stdin_data:
                args_dict = json.loads(stdin_data)
                file_path = args_dict.get("file_path")
                password = args_dict.get("password")
                if not file_path:
                    if not has_parser:
                        print("Thưa Quản trị viên, không tìm thấy thư viện Lõi ETSParser hoặc thiếu thư viện dependency xknxproject. Hệ thống chưa sẵn sàng. (NEEDS INPUT: cài đặt xknxproject)")
                    else:
                        print("Thưa Quản trị viên, tôi không nhận được đường dẫn file_path để bóc tách.")
                    sys.exit(0)
                
                # Check parser availability before returning valid path
                if not has_parser:
                    print("Thưa Quản trị viên, không tìm thấy thư viện Lõi ETSParser hoặc thiếu thư viện dependency xknxproject. Hệ thống chưa sẵn sàng. (NEEDS INPUT: cài đặt xknxproject)")
                    sys.exit(0)
                    
                return file_path, password, True
        except SystemExit:
            raise
        except Exception as e:
            if not has_parser:
                print("Thưa Quản trị viên, không tìm thấy thư viện Lõi ETSParser hoặc thiếu thư viện dependency xknxproject. Hệ thống chưa sẵn sàng. (NEEDS INPUT: cài đặt xknxproject)")
            else:
                print(f"Thưa Quản trị viên, tôi không thể đọc đầu vào JSON từ stdin: {e}")
            sys.exit(0)

    # Argparse fallback (CLI)
    if not has_parser:
        print("Thưa Quản trị viên, không tìm thấy thư viện Lõi ETSParser hoặc thiếu thư viện dependency xknxproject. Hệ thống chưa sẵn sàng. (NEEDS INPUT: cài đặt xknxproject)")
        sys.exit(0)

    parser = argparse.ArgumentParser(description="Skill Bot: Đọc và bóc tách thiết bị từ file ETS")
    parser.add_argument("--file_path", required=True, help="Đường dẫn tới file .knxproj tải từ Zalo/Telegram")
    parser.add_argument("--password", default=None, help="Mật khẩu của file ETS (nếu có)")
    args = parser.parse_args()
    return args.file_path, args.password, False

def main():
    file_path, password, _ = _parse_input()

    # has_parser is guaranteed to be True here due to checks in _parse_input()
    ets_parser = ETSParser()
    result = ets_parser.parse_project(file_path, password)

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
    message = (
        f"Thưa Quản trị viên, tôi đã bóc tách thành công {total} thiết bị "
        f"(bao gồm {lights} đèn, {hvacs} điều hòa, {blinds} rèm, {others} khác...). "
        f"Bạn có cho phép tôi nạp danh sách này đè lên Database không? (Yes/No)"
    )
    print(message)

if __name__ == "__main__":
    main()
