import secrets

from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import settings

CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


async def csrf_protection(request: Request, call_next):
    if request.method.upper() not in SAFE_METHODS:
        cookie_token = request.cookies.get(CSRF_COOKIE)
        header_token = request.headers.get(CSRF_HEADER)
        if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
            return JSONResponse({"detail": "Token CSRF inválido"}, status_code=403)

    response = await call_next(request)
    if request.method.upper() in SAFE_METHODS and not request.cookies.get(CSRF_COOKIE):
        response.set_cookie(
            key=CSRF_COOKIE,
            value=secrets.token_urlsafe(32),
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            httponly=False,
            secure=settings.APP_ENV == "production",
            samesite="lax",
            path="/",
        )
    return response