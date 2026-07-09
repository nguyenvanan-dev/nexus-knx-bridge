import os
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

API_KEY = os.getenv("API_KEY", "knx-secret-key-123")

class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "DELETE"]:
            api_key = request.headers.get("X-API-KEY")
            if api_key != API_KEY:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Unauthorized: Invalid or missing X-API-KEY"},
                )
        response = await call_next(request)
        return response
