import os, sys, json, subprocess, yaml, shutil, datetime

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
        
    # Thử tìm trong staging trước, nếu không có thì tìm trong drafts (fallback)
    source_path = f'/home/an/knx-bridge/skills/staging/{draft_id}'
    if not os.path.exists(source_path):
        source_path = f'/home/an/knx-bridge/skills/drafts/{draft_id}'
        if not os.path.exists(source_path):
            print('Không tìm thấy draft/staging!')
            return
            
    meta_path = f'{source_path}/metadata.yaml'
    if not os.path.exists(meta_path):
        print('Thiếu metadata.yaml')
        return
        
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = yaml.safe_load(f)
        
    skill_name = meta.get('name')
    if not skill_name:
        print('Metadata thiếu name')
        return
        
    official_path = f'/home/an/knx-bridge/skills/official/{skill_name}'
    
    # Backup bản cũ nếu tồn tại
    if os.path.exists(official_path):
        stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_path = f'/home/an/knx-bridge/skills/archived/{skill_name}_{stamp}'
        shutil.move(official_path, archive_path)
        
    # Di chuyển bản mới vào official
    shutil.move(source_path, official_path)
    
    # Cài đặt
    res = subprocess.run(['openclaw', 'skills', 'install', official_path], capture_output=True, text=True)
    if res.returncode != 0:
        print(f'Lỗi cài đặt: {res.stderr}')
        return
        
    # Restart
    subprocess.run(['systemd-run', '--user', '--on-active=3', 'systemctl', 'restart', 'openclaw-gateway'])
    
    print(f'Commit thành công! Skill {skill_name} đã lên Official. Hệ thống khởi động lại sau 3s.')

if __name__ == '__main__':
    main()
