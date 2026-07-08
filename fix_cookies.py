import os
import re

api_dir = 'frontend/src/app/api'

for root, dirs, files in os.walk(api_dir):
    for file in files:
        if file == 'route.js':
            filepath = os.path.join(root, file)
            with open(filepath, 'r') as f:
                content = f.read()

            # Fix cookies() call to await cookies()
            content = content.replace("cookies().get('knx_token')", "(await cookies()).get('knx_token')")
            
            with open(filepath, 'w') as f:
                f.write(content)

print('Cookies fixed')
