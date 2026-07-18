import os, sys, json, subprocess, datetime, yaml

def main():
    if 'OPENCLAW_SKILL_ARGS' in os.environ:
        args_str = os.environ['OPENCLAW_SKILL_ARGS']
    elif len(sys.argv) > 1:
        args_str = sys.argv[1]
    else:
        args_str = sys.stdin.read()
    
    try:
        args = json.loads(args_str)
    except Exception as e:
        print(f'Lỗi đọc tham số: {e}')
        return
        
    skill_name = args.get('skill_name')
    py_code = args.get('python_code')
    desc = args.get('description', '')
    
    if not skill_name or not py_code:
        print('Thiếu tên skill hoặc mã nguồn Python.')
        return
        
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    draft_id = f'{skill_name}_{stamp}'
    draft_path = f'/home/an/knx-bridge/skills/drafts/{draft_id}'
    
    os.makedirs(draft_path, exist_ok=True)
    main_py_path = f'{draft_path}/main.py'
    
    with open(main_py_path, 'w', encoding='utf-8') as f:
        f.write(py_code)
        
    # Syntax check
    try:
        subprocess.run(['python3', '-m', 'py_compile', main_py_path], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f'Lỗi cú pháp Python trong mã nguồn: {e.stderr.decode()}')
        return
        
    # Tạo SKILL.md
    with open(f'{draft_path}/SKILL.md', 'w', encoding='utf-8') as f:
        f.write(f'# {skill_name}\n\n{desc}\n')
        
    # Tạo skill.json (Optional but good for OpenClaw native run)
    skill_json = {
        'schema_version': 2, 'name': skill_name, 'description': desc,
        'run': f'python3 /home/an/knx-bridge/skills/official/{skill_name}/main.py',
        'input': { 'type': 'object', 'properties': {} }
    }
    with open(f'{draft_path}/skill.json', 'w', encoding='utf-8') as f:
        json.dump(skill_json, f, ensure_ascii=False, indent=2)
        
    # Tạo metadata.yaml
    meta = {
        'name': skill_name,
        'author': 'AI',
        'generator': {
            'provider': '9router',
            'model': 'deepseek-v4'
        },
        'status': 'draft',
        'created_at': datetime.datetime.now().isoformat(),
        'risk': 'medium',
        'files': {
            'create': [f'{skill_name}/main.py', f'{skill_name}/SKILL.md', f'{skill_name}/metadata.yaml'],
            'modify': []
        },
        'commands': [f'openclaw skills install /home/an/knx-bridge/skills/official/{skill_name}'],
        'restart': False
    }
    with open(f'{draft_path}/metadata.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(meta, f, default_flow_style=False, allow_unicode=True)
        
    print(f'Thành công! Đã tạo Draft: {draft_id}')
    print(f'Mã nguồn đã qua kiểm tra cú pháp và được lưu tại: {draft_path}')

if __name__ == '__main__':
    main()
