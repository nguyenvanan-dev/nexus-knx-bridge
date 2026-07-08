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

def main():
    if not sys.stdin.isatty():
        input_data = sys.stdin.read()
        args = json.loads(input_data) if input_data else {}
    else:
        args = {}
    
    proposal_path = args.get("proposal_path", "")
    
    if not proposal_path:
        print("Lỗi: Thiếu tham số 'proposal_path'. Bạn phải chỉ định đường dẫn file JSON.")
        return

    print(f"Đang duyệt và áp dụng file: {proposal_path} ...\n")

    # Call the original script
    original_script = "/home/an/knx-bridge/tools/apply_device_proposal.py"
    
    try:
        result = subprocess.run(
            ["/home/an/knx-bridge/.venv/bin/python", original_script, proposal_path, "--confirm"],
            cwd="/home/an/knx-bridge",
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout
        print(output)
        
        if result.stderr:
            print("\nCảnh báo/Lỗi hệ thống:\n", result.stderr)

        # If applied successfully, inject into Local Memory
        if result.returncode == 0 and remember_knx_device:
            try:
                with open(os.path.expanduser(proposal_path), "r", encoding="utf-8") as f:
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
                        ga = dev.get("onoff_ga") or dev.get("brightness_ga") or dev.get("status_ga") or "Unknown"
                        
                        remember_knx_device(
                            name=name,
                            room=room,
                            device_type=dev_type,
                            group_address=ga,
                            dpt="Auto",
                            direction="N/A",
                            note=f"Được thêm tự động từ proposal: {os.path.basename(proposal_path)}"
                        )
                        count += 1
                    print(f"✅ Đã ghi nhớ vĩnh viễn {count} thiết bị vào Sổ tay AI.")
                    
            except Exception as e:
                print(f"\n⚠️ Cập nhật Sổ tay thất bại (Hệ thống chính vẫn chạy OK): {e}")

    except Exception as e:
        print(f"Lỗi khi chạy bộ duyệt proposal: {e}")

if __name__ == "__main__":
    main()
