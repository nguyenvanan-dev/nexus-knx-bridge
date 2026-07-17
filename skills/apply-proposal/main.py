import sys
import json
import subprocess
import os

# Add knx-bridge to path so it can import local_memory
sys.path.append("/home/an/knx-bridge")

try:
    from local_memory.knx_memory import remember_knx_device
except ImportError:
    remember_knx_device = None


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

    proposal_path = args.get("proposal_path", "")

    if not proposal_path:
        fail("Thiếu tham số proposal_path. Bạn phải chỉ định đường dẫn file JSON.", code=2)

    expanded_path = os.path.expanduser(proposal_path)
    if not os.path.isfile(expanded_path):
        fail(f"File proposal không tồn tại: {expanded_path}")

    print(f"Đang duyệt và áp dụng file: {proposal_path} ...\n")

    # Call the canonical implementation in tools/
    original_script = "/home/an/knx-bridge/tools/apply_device_proposal.py"

    if not os.path.isfile(original_script):
        fail(f"Implementation không tồn tại: {original_script}")

    try:
        result = subprocess.run(
            ["/home/an/knx-bridge/.venv/bin/python", original_script, expanded_path, "--confirm"],
            cwd="/home/an/knx-bridge",
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.stdout:
            print(result.stdout, end="")

        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)

        # If applied successfully, inject into Local Memory
        if result.returncode == 0 and remember_knx_device:
            try:
                with open(expanded_path, "r", encoding="utf-8") as f:
                    proposal_data = json.load(f)

                proposed = proposal_data.get("proposed_devices", [])
                ready_devices = [d for d in proposed if d.get("status") == "ready"]

                if ready_devices:
                    print("\n--- Đang lưu cấu hình vào Sổ tay Local Memory ---")
                    count = 0
                    for dev in ready_devices:
                        name = dev.get("name", "Unknown")
                        room = dev.get("room", "Unknown")
                        dev_type = dev.get("type", "Unknown")
                        ga = (
                            dev.get("onoff_ga")
                            or dev.get("brightness_ga")
                            or dev.get("status_ga")
                            or "Unknown"
                        )

                        remember_knx_device(
                            name=name,
                            room=room,
                            device_type=dev_type,
                            group_address=ga,
                            dpt="Auto",
                            direction="N/A",
                            note=f"Được thêm tự động từ proposal: {os.path.basename(proposal_path)}",
                        )
                        count += 1
                    print(f"Đã ghi nhớ vĩnh viễn {count} thiết bị vào Sổ tay AI.")

            except Exception as e:
                print(
                    f"\nCập nhật Sổ tay thất bại (Hệ thống chính vẫn chạy OK): {e}",
                    file=sys.stderr,
                )

        if result.returncode != 0:
            raise SystemExit(result.returncode)

    except SystemExit:
        raise
    except subprocess.TimeoutExpired:
        fail("Quá thời gian chờ (30s) khi duyệt proposal.")
    except Exception as e:
        fail(f"Lỗi khi chạy bộ duyệt proposal: {e}")


if __name__ == "__main__":
    main()
