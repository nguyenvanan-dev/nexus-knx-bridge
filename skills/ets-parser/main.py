import sys
import argparse
import json
import os
import time
import re
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from core.knxproj_parser import ETSParser
    has_parser = True
except ImportError:
    has_parser = False

def _parse_input():
    if not sys.stdin.isatty():
        try:
            stdin_data = sys.stdin.read().strip()
            if stdin_data:
                args_dict = json.loads(stdin_data)
                file_path = args_dict.get("file_path")
                password = args_dict.get("password")
                output_path = args_dict.get("output_path")
                if not file_path:
                    if not has_parser:
                        print("Thưa Quản trị viên, không tìm thấy thư viện Lõi ETSParser hoặc thiếu thư viện dependency xknxproject. Hệ thống chưa sẵn sàng. (NEEDS INPUT: cài đặt xknxproject)")
                    else:
                        print("Thưa Quản trị viên, tôi không nhận được đường dẫn file_path để bóc tách.")
                    sys.exit(0)

                if not has_parser:
                    print("Thưa Quản trị viên, không tìm thấy thư viện Lõi ETSParser hoặc thiếu thư viện dependency xknxproject. Hệ thống chưa sẵn sàng. (NEEDS INPUT: cài đặt xknxproject)")
                    sys.exit(0)

                return file_path, password, output_path, True
        except SystemExit:
            raise
        except Exception as e:
            if not has_parser:
                print("Thưa Quản trị viên, không tìm thấy thư viện Lõi ETSParser hoặc thiếu thư viện dependency xknxproject. Hệ thống chưa sẵn sàng. (NEEDS INPUT: cài đặt xknxproject)")
            else:
                print(f"Thưa Quản trị viên, tôi không thể đọc đầu vào JSON từ stdin: {e}")
            sys.exit(0)

    if not has_parser:
        print("Thưa Quản trị viên, không tìm thấy thư viện Lõi ETSParser hoặc thiếu thư viện dependency xknxproject. Hệ thống chưa sẵn sàng. (NEEDS INPUT: cài đặt xknxproject)")
        sys.exit(0)

    parser = argparse.ArgumentParser(description="Skill Bot: Đọc và bóc tách thiết bị từ file ETS")
    parser.add_argument("--file_path", required=True, help="Đường dẫn tới file .knxproj tải từ Zalo/Telegram")
    parser.add_argument("--password", default=None, help="Mật khẩu của file ETS (nếu có)")
    parser.add_argument("--output_path", default=None, help="Đường dẫn lưu file proposal kết quả")
    args = parser.parse_args()
    return args.file_path, args.password, args.output_path, False

def main():
    file_path, password, output_path, _ = _parse_input()

    expanded_path = os.path.expanduser(file_path)
    if not os.path.isfile(expanded_path):
        print(f"Thưa Quản trị viên, file .knxproj không tồn tại tại: {expanded_path}")
        sys.exit(0)

    ets_parser = ETSParser()
    result = ets_parser.parse_project(expanded_path, password)

    if result.get("status") == "error":
        print(f"Thưa Quản trị viên, tôi không thể đọc được file này. Lỗi: {result.get('message')}")
        return

    if not output_path:
        review_dir = os.path.expanduser("~/.openclaw/workspace/knowledge/review")
        os.makedirs(review_dir, exist_ok=True)
        timestamp = int(time.time())
        stem = Path(expanded_path).name
        # Sanitize name
        stem_clean = re.sub(r"[^a-zA-Z0-9_-]", "_", stem)
        output_path = os.path.join(review_dir, f"knxproj_proposal_{timestamp}_{stem_clean}.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    summary = result.get("summary", {})
    by_type_str = ", ".join([f"{k}: {v}" for k, v in summary.get("by_type", {}).items()]) or "N/A"

    print("Thành công: Đã xử lý dự án KNX!")
    print(f"Tổng số thiết bị tìm thấy: {summary.get('total_devices', 0)}")
    print(f"  - Sẵn sàng (Ready): {summary.get('ready', 0)}")
    print(f"  - Cần xem lại (Needs Review): {summary.get('needs_review', 0)}")
    print(f"  - Thiếu thông tin (Missing Info): {summary.get('missing_info', 0)}")
    print(f"Phân loại loại thiết bị: {by_type_str}")
    print(f"Đường dẫn file proposal: {output_path}")
    print("\nNhắc nhở: Quản trị viên vui lòng duyệt bản nháp này trước khi nạp (apply) vào hệ thống.")

if __name__ == "__main__":
    main()
