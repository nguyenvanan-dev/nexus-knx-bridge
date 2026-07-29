import os
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

_env_key = os.getenv("API_KEY", "").strip()
WEAK_KEYS = {"knx-secret-key-123", "secret", "change_me", "admin", "123456"}

if _env_key and _env_key not in WEAK_KEYS:
    API_KEY = _env_key
else:
    API_KEY = None

def get_active_api_key():
    key = os.getenv("API_KEY", "").strip()
    return key if key and key not in WEAK_KEYS else None

class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "DELETE"]:
            client_host = request.client.host if request.client else ""
            if client_host not in ("127.0.0.1", "::1", "localhost"):
                active_key = get_active_api_key() or API_KEY
                api_key = request.headers.get("X-API-KEY")
                if not active_key or not api_key or api_key != active_key:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Unauthorized: Invalid or missing X-API-KEY"},
                    )
        response = await call_next(request)
        return response
