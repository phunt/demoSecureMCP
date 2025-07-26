"""JWT validation module with JWKS caching"""

import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

import httpx
import jwt
from jwt import PyJWKClient
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidTokenError,
    InvalidSignatureError,
    InvalidIssuerError,
    InvalidAudienceError,
    InvalidKeyError,
    MissingRequiredClaimError
)
import redis.asyncio as redis
from pydantic import BaseModel

from src.config.settings import settings


class TokenPayload(BaseModel):
    """Validated JWT token payload"""
    sub: str  # Subject (user ID)
    iss: str  # Issuer
    aud: str | List[str]  # Audience
    exp: int  # Expiration time
    iat: int  # Issued at
    scope: Optional[str] = None  # OAuth scopes
    preferred_username: Optional[str] = None
    email: Optional[str] = None
    email_verified: Optional[bool] = None
    realm_access: Optional[Dict[str, List[str]]] = None
    resource_access: Optional[Dict[str, Any]] = None


class JWTValidator:
    """JWT validator with JWKS caching support"""
    
    def __init__(self):
        self.settings = settings
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
            await self.redis_client.ping()
        except Exception as e:
            print(f"Warning: Redis connection failed: {e}. Using in-memory cache.")
            self.redis_client = None
        
        # Initialize JWKS client
        await self._setup_jwks_client()
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def _setup_jwks_client(self):
        """Setup JWKS client with discovered configuration"""
        # Try to get OpenID configuration from cache
        openid_config = await self._get_cached_openid_config()
        
        if not openid_config:
            # Fetch from Keycloak
            async with httpx.AsyncClient() as client:
                response = await client.get(str(self.settings.openid_config_url))
                response.raise_for_status()
                openid_config = response.json()
                
                # Cache the configuration
                await self._cache_openid_config(openid_config)
        
        # Create JWKS client
        jwks_uri = openid_config.get("jwks_uri", str(self.settings.oauth_jwks_uri))
        self.jwks_client = PyJWKClient(jwks_uri)
    
    async def _get_cached_openid_config(self) -> Optional[Dict]:
        """Get cached OpenID configuration"""
        if not self.redis_client:
            return None
            
        try:
            cached = await self.redis_client.get(self._openid_config_cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass
        
        return None
    
    async def _cache_openid_config(self, config: Dict):
        """Cache OpenID configuration"""
        if not self.redis_client:
            return
            
        try:
            await self.redis_client.setex(
                self._openid_config_cache_key,
                self.settings.redis_ttl,
                json.dumps(config)
            )
        except Exception:
            pass
    
    async def _get_signing_key(self, token: str):
        """Get signing key for token verification"""
        if not self.jwks_client:
            raise InvalidKeyError("JWKS client not initialized")
        
        # PyJWKClient handles caching internally
        return self.jwks_client.get_signing_key_from_jwt(token)
    
    async def validate_token(self, token: str) -> TokenPayload:
        """
        Validate JWT token and return payload
        
        Args:
            token: JWT token string
            
        Returns:
            TokenPayload: Validated token payload
            
        Raises:
            InvalidTokenError: If token validation fails
        """
        try:
            # Get signing key
            signing_key = await self._get_signing_key(token)
            
            # First decode without audience validation to check what's in the token
            unverified_payload = jwt.decode(
                token,
                options={"verify_signature": False}
            )
            
            # Check if token has 'aud' or 'azp' claim for audience validation
            audience = None
            if 'aud' in unverified_payload:
                audience = self.settings.oauth_audience
            elif 'azp' in unverified_payload and unverified_payload['azp'] == self.settings.oauth_audience:
                # Keycloak uses 'azp' for client credentials flow
                audience = None  # Skip audience validation, we'll check azp manually
            
            # Decode and validate token
            decode_options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_aud": audience is not None,
                "verify_iss": True,
                "require": ["exp", "iat", "iss", "sub"]
            }
            
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=self.settings.jwt_algorithms,
                issuer=str(self.settings.oauth_issuer),
                audience=audience,
                leeway=self.settings.jwt_leeway,
                options=decode_options
            )
            
            # If using azp, verify it matches our expected audience
            if 'azp' in payload and 'aud' not in payload:
                if payload['azp'] != self.settings.oauth_audience:
                    raise InvalidTokenError(f"Invalid authorized party (azp): expected {self.settings.oauth_audience}, got {payload['azp']}")
            
            # Create validated payload (handle aud as optional)
            if 'aud' not in payload and 'azp' in payload:
                payload['aud'] = payload['azp']
            
            return TokenPayload(**payload)
            
        except ExpiredSignatureError:
            raise InvalidTokenError("Token has expired")
        except InvalidSignatureError:
            raise InvalidTokenError("Invalid token signature")
        except InvalidIssuerError:
            raise InvalidTokenError("Invalid token issuer")
        except InvalidAudienceError:
            raise InvalidTokenError("Invalid token audience")
        except MissingRequiredClaimError as e:
            raise InvalidTokenError(f"Missing required claim: {e}")
        except Exception as e:
            raise InvalidTokenError(f"Token validation failed: {str(e)}")
    
    def extract_scopes(self, payload: TokenPayload) -> List[str]:
        """Extract scopes from token payload"""
        scopes = []
        
        # OAuth2 scopes from 'scope' claim
        if payload.scope:
            scopes.extend(payload.scope.split())
        
        # Keycloak realm roles
        if payload.realm_access and payload.realm_access.get("roles"):
            scopes.extend([f"role:{role}" for role in payload.realm_access["roles"]])
        
        # Keycloak resource roles
        if payload.resource_access:
            for resource, access in payload.resource_access.items():
                if isinstance(access, dict) and access.get("roles"):
                    scopes.extend([f"{resource}:{role}" for role in access["roles"]])
        
        return scopes
    
    def has_scope(self, payload: TokenPayload, required_scope: str) -> bool:
        """Check if token has required scope"""
        scopes = self.extract_scopes(payload)
        return required_scope in scopes
    
    def has_any_scope(self, payload: TokenPayload, required_scopes: List[str]) -> bool:
        """Check if token has any of the required scopes"""
        scopes = self.extract_scopes(payload)
        return any(scope in scopes for scope in required_scopes)
    
    def has_all_scopes(self, payload: TokenPayload, required_scopes: List[str]) -> bool:
        """Check if token has all required scopes"""
        scopes = self.extract_scopes(payload)
        return all(scope in scopes for scope in required_scopes)


# Global validator instance
jwt_validator = JWTValidator() 