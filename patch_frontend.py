import os
import re

api_dir = 'frontend/src/app/api'

for root, dirs, files in os.walk(api_dir):
    if 'auth' in root: continue
    for file in files:
        if file == 'route.js':
            filepath = os.path.join(root, file)
            with open(filepath, 'r') as f:
                content = f.read()

            if 'knx_token' in content:
                continue

            # Add imports
            content = content.replace('import { NextResponse } from \'next/server\';', 'import { NextResponse } from \'next/server\';\nimport { cookies } from \'next/headers\';')
            content = content.replace('import { NextResponse } from "next/server";', 'import { NextResponse } from "next/server";\nimport { cookies } from \'next/headers\';')

            # Inject the authHeaders logic at the beginning of GET, POST, DELETE, PUT
            auth_logic = '\n    const token = cookies().get(\'knx_token\')?.value;\n    const authHeaders = token ? { \'Authorization\': `Bearer ${token}` } : {};'
            content = re.sub(r'(export async function (GET|POST|PUT|DELETE)\([^\)]*\)\s*\{)', r'\1' + auth_logic, content)

            # Replace headers: { ... } with headers: { ...authHeaders, ... }
            content = re.sub(r'headers:\s*\{', r'headers: { ...authHeaders, ', content)

            # For fetch calls that don't have headers but have options { cache: ... }
            def fix_fetch_options(match):
                options = match.group(2)
                if 'headers:' not in options:
                    return match.group(1) + '{ headers: authHeaders, ' + options[1:]
                return match.group(0)
            
            content = re.sub(r'(fetch\([^,]+,\s*)(\{[^\}]+\})', fix_fetch_options, content)

            # For fetch calls with no options at all (just 1 argument)
            content = re.sub(r'(fetch\([^,]+)\)', r'\1, { headers: authHeaders })', content)

            with open(filepath, 'w') as f:
                f.write(content)

print('Patching complete')
