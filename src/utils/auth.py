"""
JWT Authentication utilities for FastAPI.

Handles JWT token validation and user extraction for LangGraph thread management.
"""
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import Optional
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer()


def decode_jwt_token(token: str) -> dict:
    """
    Decode and validate JWT token.

    Args:
        token: JWT token string

    Returns:
        dict: Decoded JWT payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_user_id_from_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """
    Extract user_id from JWT token for thread_id generation.

    Checks 'sub' (subject) claim first, then falls back to 'user_id'.

    Args:
        credentials: HTTP Bearer credentials containing JWT token

    Returns:
        str: User ID extracted from token

    Raises:
        HTTPException: If token is invalid or user_id not found

    Example:
        >>> # In FastAPI endpoint
        >>> @router.post("/some-endpoint")
        >>> async def endpoint(user_id: str = Depends(get_user_id_from_token)):
        >>>     # user_id is automatically extracted from JWT
        >>>     pass
    """
    token = credentials.credentials
    payload = decode_jwt_token(token)

    # Standard JWT uses 'sub' (subject) for user identifier
    user_id = payload.get("sub") or payload.get("user_id")

    if not user_id:
        logger.error("User ID not found in JWT payload")
        raise HTTPException(status_code=401, detail="User ID not found in token")

    logger.info(f"Authenticated user: {user_id}")
    return user_id


def get_optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[str]:
    """
    Extract user_id from JWT token if provided (optional authentication).

    Useful for endpoints that support both authenticated and anonymous access.

    Args:
        credentials: Optional HTTP Bearer credentials

    Returns:
        Optional[str]: User ID if token provided and valid, None otherwise

    Example:
        >>> @router.get("/some-endpoint")
        >>> async def endpoint(user_id: Optional[str] = Depends(get_optional_user_id)):
        >>>     if user_id:
        >>>         # Authenticated request
        >>>     else:
        >>>         # Anonymous request
    """
    if not credentials:
        return None

    try:
        return get_user_id_from_token(credentials)
    except HTTPException:
        logger.warning("Invalid token provided, treating as anonymous")
        return None


def create_jwt_token(user_id: str, additional_claims: Optional[dict] = None) -> str:
    """
    Create JWT token for testing/development.

    Args:
        user_id: User identifier to encode in token
        additional_claims: Optional additional claims to include

    Returns:
        str: Encoded JWT token

    Example:
        >>> token = create_jwt_token("test_user", {"email": "test@example.com"})
        >>> # Use token in Authorization: Bearer {token}
    """
    from datetime import datetime, timedelta

    claims = {
        "sub": user_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    }

    if additional_claims:
        claims.update(additional_claims)

    token = jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token
