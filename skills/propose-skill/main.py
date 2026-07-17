import sys, json, os
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
    desc = args.get('description')
    py_code = args.get('python_code')
    
    if not skill_name or not py_code:
        print('Thiếu tên skill hoặc mã nguồn Python.')
        return
        
    proposal_dir = f'/home/an/knx-bridge/proposals/skills/{skill_name}'
    os.makedirs(proposal_dir, exist_ok=True)
    
    with open(f'{proposal_dir}/main.py', 'w', encoding='utf-8') as f:
        f.write(py_code)
        
    skill_json = {
        'schema_version': 2,
        'name': skill_name,
        'description': desc,
        'run': f'python3 /home/an/knx-bridge/tools/{skill_name}/main.py',
        'input': { 'type': 'object', 'properties': {} }
    }
    
    with open(f'{proposal_dir}/skill.json', 'w', encoding='utf-8') as f:
        json.dump(skill_json, f, ensure_ascii=False, indent=2)
        
    print(f'Thành công! Đã tạo bản nháp (Proposal) cho skill {skill_name} tại {proposal_dir}.')
    print('Vui lòng nói người dùng vào máy chủ đọc file nháp này. Nếu họ duyệt, họ cần copy thư mục này vào /home/an/knx-bridge/tools/ và chạy lệnh openclaw skills install.')
    
if __name__ == '__main__':
    main()
