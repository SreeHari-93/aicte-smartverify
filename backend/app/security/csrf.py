import secrets
from fastapi import Request, HTTPException, status


CSRF_COOKIE_NAME = "aicte_csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"


def generate_csrf_token() -> str:
    """Generate cryptographically secure CSRF token"""
    return secrets.token_hex(32)


def verify_csrf_token(request: Request) -> bool:
    """
    Verify double-submit CSRF token.
    Compares cookie value with header value in constant time.
    """
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)

    if not cookie_token or not header_token:
        return False

    return secrets.compare_digest(cookie_token, header_token)


def require_csrf(request: Request):
    """Dependency that enforces CSRF check on state-changing requests"""
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        if not verify_csrf_token(request):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF verification failed. Missing or invalid CSRF token.",
            )

