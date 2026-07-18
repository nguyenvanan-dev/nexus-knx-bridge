import sys
import argparse
import json
from pathlib import Path

def main():
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
        
    # ANTI-RISK COMPLIANCE: Tuyệt đối không Insert trực tiếp vào Database.
    # Tạo Bản Nháp (Proposal) và hỏi ý kiến Quản trị viên.
    
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
