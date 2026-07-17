import os, sys, json, subprocess

def main():
    if 'OPENCLAW_SKILL_ARGS' in os.environ:
        args_str = os.environ['OPENCLAW_SKILL_ARGS']
    elif len(sys.argv) > 1:
        args_str = sys.argv[1]
    else:
        args_str = sys.stdin.read()
    
    try:
        args = json.loads(args_str)
    except:
        print('Lỗi tham số')
        return
        
    draft_id = args.get('draft_id')
    if not draft_id:
        print('Thiếu draft_id')
        return
        
    draft_path = f'/home/an/knx-bridge/skills/drafts/{draft_id}'
    staging_path = f'/home/an/knx-bridge/skills/staging/{draft_id}'
    
    if not os.path.exists(draft_path):
        print('Không tìm thấy bản draft')
        return
        
    subprocess.run(['mv', draft_path, staging_path])
    print(f'Thành công! Đã chuyển {draft_id} sang môi trường Staging.')

if __name__ == '__main__':
    main()
