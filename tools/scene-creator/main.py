import sys
import argparse
import json
from pathlib import Path

def main():
    # If called with JSON stdin
    if not sys.stdin.isatty():
        try:
            stdin_data = sys.stdin.read().strip()
            if stdin_data:
                args_dict = json.loads(stdin_data)
                name = args_dict.get("name")
                description = args_dict.get("description", "")
                actions = args_dict.get("actions") or args_dict.get("actions_json")
                if not name or not actions:
                    print("Thưa Quản trị viên, thiếu tham số 'name' hoặc 'actions' trong đầu vào JSON.")
                    sys.exit(0)
                
                if isinstance(actions, str):
                    try:
                        actions = json.loads(actions)
                    except Exception:
                        pass
                
                if not isinstance(actions, list):
                    print("Thưa Quản trị viên, kịch bản phải là một mảng JSON các hành động.")
                    sys.exit(0)
                
                total_actions = len(actions)
                message = (
                    f"Thưa Quản trị viên, tôi đã soạn dự thảo kịch bản '{name}' "
                    f"với {total_actions} hành động điều khiển. "
                    f"Bạn có cho phép tôi lưu kịch bản này vào Database không? (Yes/No)"
                )
                print(message)
                
                proposal_data = {
                    "action": "create_scene",
                    "message": message,
                    "payload": {
                        "name": name,
                        "description": description,
                        "actions": actions
                    }
                }
                with open("/tmp/latest_scene_proposal.json", "w") as f:
                    json.dump(proposal_data, f, ensure_ascii=False, indent=2)
                return
        except Exception as e:
            print(f"Thưa Quản trị viên, tôi không thể tạo kịch bản do lỗi định dạng stdin: {e}")
            sys.exit(0)

    # Argparse fallback for CLI
    parser = argparse.ArgumentParser(description="Skill Bot: Tạo kịch bản tự động")
    parser.add_argument("--name", required=True, help="Tên kịch bản (Ví dụ: Kịch bản đi ngủ)")
    parser.add_argument("--description", default="", help="Mô tả kịch bản")
    parser.add_argument("--actions_json", required=True, help="JSON array các hành động. VD: [{'device': 'den_1', 'action': 'on', 'delay_seconds': 0}]")
    args = parser.parse_args()
    
    try:
        actions = json.loads(args.actions_json)
        if not isinstance(actions, list):
            raise ValueError("actions_json must be a JSON array")
    except Exception as e:
        print(f"Thưa Quản trị viên, tôi không thể tạo kịch bản do lỗi định dạng: {e}")
        return
        
    total_actions = len(actions)
    message = (
        f"Thưa Quản trị viên, tôi đã soạn dự thảo kịch bản '{args.name}' "
        f"với {total_actions} hành động điều khiển. "
        f"Bạn có cho phép tôi lưu kịch bản này vào Database không? (Yes/No)"
    )
    print(message)
    
    proposal_data = {
        "action": "create_scene",
        "message": message,
        "payload": {
            "name": args.name,
            "description": args.description,
            "actions": actions
        }
    }
    
    with open("/tmp/latest_scene_proposal.json", "w") as f:
        json.dump(proposal_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
