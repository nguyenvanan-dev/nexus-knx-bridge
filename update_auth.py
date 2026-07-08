with open('auth_utils.py', 'r') as f:
    content = f.read()

import re

# Remove passlib CryptContext
content = re.sub(r'from passlib.context import CryptContext\n', '', content)
content = re.sub(r'pwd_context = CryptContext\(schemes=\["bcrypt"\], deprecated="auto"\)\n', '', content)

content = content.replace('def verify_password(plain_password: str, hashed_password: str) -> bool:\n    return pwd_context.verify(plain_password, hashed_password)', '''import bcrypt\n\ndef verify_password(plain_password: str, hashed_password: str) -> bool:\n    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))''')

content = content.replace('def get_password_hash(password: str) -> str:\n    return pwd_context.hash(password)', '''def get_password_hash(password: str) -> str:\n    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')''')

with open('auth_utils.py', 'w') as f:
    f.write(content)
