from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.core.config import settings
import logging

logger = logging.getLogger("api.auth")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not settings.X_API_KEY:
        logger.warning("X_API_KEY not configured - API authentication is disabled")
        return None
    
    if not api_key:
        logger.warning("Missing X-API-Key header in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header"
        )
    
    print(api_key, "API KEY ACCEPTED")
    print(settings.X_API_KEY, "API KEY EXPECTED")
    
    if api_key != settings.X_API_KEY:
        logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid X-API-Key"
        )
    
    return api_key