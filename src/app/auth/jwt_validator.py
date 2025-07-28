"""JWT validation module for OAuth 2.0 token verification

This module implements JWT token validation with JWKS caching using Redis.
It supports dynamic key rotation and validates tokens according to OAuth 2.1 standards.
"""

from typing import Dict, Any, Optional, List
import time
import json
from functools import lru_cache

import jwt
from jwt import PyJWKClient, InvalidTokenError, InvalidKeyError
import httpx
import redis.asyncio as redis
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from fastapi import HTTPException, status
from pydantic import BaseModel

from src.config.settings import get_settings
from src.core.logging import security_logger, get_logger

logger = get_logger(__name__)


class TokenPayload(BaseModel):
    """Validated JWT token payload"""
    sub: str  # Subject (user ID)
    exp: int  # Expiration time
    iat: int  # Issued at
    jti: Optional[str] = None  # JWT ID
    iss: str  # Issuer
    aud: Optional[str] = None  # Audience
    azp: Optional[str] = None  # Authorized party (client ID)
    typ: Optional[str] = None  # Token type
    scope: Optional[str] = None  # OAuth scopes
    email: Optional[str] = None
    email_verified: Optional[bool] = None
    preferred_username: Optional[str] = None
    client_id: Optional[str] = None  # Client ID from azp or client_id claim
    realm_access: Optional[Dict[str, List[str]]] = None
    resource_access: Optional[Dict[str, Any]] = None


class JWTValidator:
    """JWT validator with JWKS caching support"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client: Optional[redis.Redis] = None
        self.jwks_client: Optional[PyJWKClient] = None
        self._jwks_cache_key = f"jwks:{self.settings.keycloak_realm}"
        self._openid_config_cache_key = f"openid_config:{self.settings.keycloak_realm}"
        
    async def initialize(self):
        """Initialize Redis connection and JWKS client"""
        try:
            self.redis_client = await redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Redis connection established for JWKS caching")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Continuing without cache.")
            self.redis_client = None
            
        # Initialize JWKS client with computed URI
        jwks_uri = self.settings.oauth_jwks_uri
        self.jwks_client = PyJWKClient(jwks_uri, cache_jwk_set=True, lifespan=3600)
        logger.info(f"JWKS client initialized with URI: {jwks_uri}")
            
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            
    async def validate_token(self, token: str) -> TokenPayload:
        """
        Validate JWT token and return payload
        
        Args:
            token: JWT token string
            
        Returns:
            TokenPayload: Validated token payload
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Use PyJWKClient to get the signing key
            if not self.jwks_client:
                raise InvalidTokenError("JWKS client not initialized")
            
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Decode without verification to check audience claim
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            
            # Determine the audience to validate
            # Keycloak uses 'azp' for client credentials flow
            audience = self.settings.oauth_audience
            if 'aud' not in unverified_payload and 'azp' in unverified_payload:
                # For client credentials flow, validate against azp
                audience = None  # Skip aud validation, we'll check azp separately
            
            # Validate the token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=self.settings.jwt_algorithms,
                issuer=str(self.settings.oauth_issuer),
                audience=audience,
                leeway=self.settings.jwt_leeway,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": audience is not None,  # Only verify if we have an audience
                    "verify_iss": True,
                }
            )
            
            # For client credentials, validate azp
            if 'azp' in payload and audience is None:
                if payload['azp'] != self.settings.oauth_audience:
                    raise InvalidTokenError(f"Invalid authorized party (azp): expected {self.settings.oauth_audience}, got {payload['azp']}")
            
            # Extract client_id (prefer azp over client_id claim)
            client_id = payload.get('azp') or payload.get('client_id')
            
            # Create TokenPayload
            token_payload = TokenPayload(
                sub=payload["sub"],
                exp=payload["exp"],
                iat=payload["iat"],
                jti=payload.get("jti"),
                iss=payload["iss"],
                aud=payload.get("aud"),
                azp=payload.get("azp"),
                typ=payload.get("typ"),
                scope=payload.get("scope", ""),
                email=payload.get("email"),
                email_verified=payload.get("email_verified"),
                preferred_username=payload.get("preferred_username"),
                client_id=client_id,
                realm_access=payload.get("realm_access"),
                resource_access=payload.get("resource_access")
            )
            
            # Log successful validation
            security_logger.log_auth_attempt(
                success=True,
                user_id=token_payload.sub,
                client_id=client_id
            )
            
            return token_payload
            
        except jwt.ExpiredSignatureError:
            security_logger.log_auth_attempt(
                success=False,
                reason="Token expired"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidTokenError as e:
            security_logger.log_auth_attempt(
                success=False,
                reason=str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {str(e)}")
            security_logger.log_auth_attempt(
                success=False,
                reason=str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed",
                headers={"WWW-Authenticate": "Bearer"}
            )
            
    def extract_scopes(self, token_payload: TokenPayload) -> List[str]:
        """Extract scopes from token payload"""
        # OAuth scopes in the 'scope' claim
        if token_payload.scope:
            return token_payload.scope.split()
            
        # Keycloak realm roles
        if token_payload.realm_access and "roles" in token_payload.realm_access:
            return token_payload.realm_access["roles"]
            
        return []


# Create a singleton instance
jwt_validator = JWTValidator() 