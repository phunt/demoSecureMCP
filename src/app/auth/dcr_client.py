"""Dynamic Client Registration (DCR) client for OAuth 2.0"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

import httpx
from pydantic import BaseModel, Field

from src.core.logging import get_logger
from src.config.settings import Settings


logger = get_logger(__name__)


class ClientMetadata(BaseModel):
    """OAuth 2.0 Dynamic Client Registration metadata"""
    client_name: str = Field(..., description="Human-readable client name")
    redirect_uris: list[str] = Field(default_factory=list, description="Redirect URIs")
    grant_types: list[str] = Field(default=["client_credentials"], description="Grant types")
    response_types: list[str] = Field(default=["none"], description="Response types")
    token_endpoint_auth_method: str = Field(default="client_secret_basic", description="Auth method")
    scope: str = Field(default="", description="Space-separated list of scopes")
    client_uri: Optional[str] = Field(None, description="Client information URI")
    logo_uri: Optional[str] = Field(None, description="Client logo URI")
    contacts: list[str] = Field(default_factory=list, description="Client contacts")
    policy_uri: Optional[str] = Field(None, description="Client policy URI")
    tos_uri: Optional[str] = Field(None, description="Terms of service URI")


class RegisteredClient(BaseModel):
    """Response from successful client registration"""
    client_id: str
    client_secret: Optional[str] = None
    client_secret_expires_at: Optional[int] = None
    registration_access_token: Optional[str] = None
    registration_client_uri: Optional[str] = None
    client_id_issued_at: Optional[int] = None
    # Echo back the metadata
    client_name: Optional[str] = None
    redirect_uris: Optional[list[str]] = None
    grant_types: Optional[list[str]] = None
    response_types: Optional[list[str]] = None
    token_endpoint_auth_method: Optional[str] = None
    scope: Optional[str] = None


class DCRClient:
    """Dynamic Client Registration client"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.registration_endpoint = None
        self.registered_client: Optional[RegisteredClient] = None
        self.client_config_file = Path(".dcr_client.json")
        
    async def discover_registration_endpoint(self) -> str:
        """Discover the DCR endpoint from OAuth metadata"""
        try:
            # Get OAuth metadata
            metadata_url = f"{self.settings.oauth_issuer}/.well-known/openid-configuration"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(metadata_url)
                response.raise_for_status()
                metadata = response.json()
                
            # Extract registration endpoint
            registration_endpoint = metadata.get("registration_endpoint")
            if not registration_endpoint:
                raise ValueError("No registration_endpoint in OAuth metadata")
                
            self.registration_endpoint = registration_endpoint
            logger.info(f"Discovered DCR endpoint: {registration_endpoint}")
            return registration_endpoint
            
        except Exception as e:
            logger.error(f"Failed to discover DCR endpoint: {e}")
            raise
            
    async def register_client(self, initial_access_token: Optional[str] = None) -> RegisteredClient:
        """Register this MCP server as an OAuth client"""
        try:
            # Ensure we have the registration endpoint
            if not self.registration_endpoint:
                await self.discover_registration_endpoint()
                
            # Strip whitespace from token (Docker Compose adds newlines)
            if initial_access_token:
                logger.debug(f"Token before strip - length: {len(initial_access_token)}, repr: {repr(initial_access_token[-5:])}")
                initial_access_token = initial_access_token.strip()
                logger.debug(f"Token after strip - length: {len(initial_access_token)}, repr: {repr(initial_access_token[-5:])}")
                
            # Prepare client metadata
            metadata = ClientMetadata(
                client_name=f"MCP Server ({self.settings.app_name})",
                redirect_uris=[],  # Not needed for client_credentials
                grant_types=["client_credentials"],
                response_types=["none"],
                token_endpoint_auth_method="client_secret_basic",
                # Remove scope to avoid "insufficient_scope" error
                client_uri=self.settings.mcp_resource_identifier,
                contacts=[f"admin@{self.settings.mcp_resource_identifier}"]
            )
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Add initial access token if provided
            if initial_access_token:
                headers["Authorization"] = f"Bearer {initial_access_token}"
                logger.debug(f"Using initial access token (length: {len(initial_access_token)})")
                logger.debug(f"Token preview: {initial_access_token[:20]}...{initial_access_token[-20:]}")
                logger.debug(f"Authorization header length: {len(headers['Authorization'])}")
                logger.debug(f"Authorization header preview: {headers['Authorization'][:30]}...{headers['Authorization'][-30:]}")
            else:
                logger.warning("No initial access token provided for DCR")
                
            # Register the client
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.registration_endpoint,
                    json=metadata.model_dump(exclude_none=True),
                    headers=headers
                )
                
                # Log response details if it fails
                if response.status_code == 401:
                    logger.error(f"DCR registration failed with 401. Response: {response.text}")
                    
                response.raise_for_status()
                
            # Parse response
            data = response.json()
            self.registered_client = RegisteredClient(**data)
            
            # Save registration info for future use
            await self.save_registration()
            
            logger.info(f"Successfully registered client: {self.registered_client.client_id}")
            return self.registered_client
            
        except Exception as e:
            logger.error(f"Failed to register client: {e}")
            raise
            
    async def save_registration(self) -> None:
        """Save registration info to file"""
        if not self.registered_client:
            return
            
        try:
            data = self.registered_client.model_dump(exclude_none=True)
            # Add timestamp
            data["registered_at"] = os.environ.get("HOSTNAME", "unknown")
            
            with open(self.client_config_file, "w") as f:
                json.dump(data, f, indent=2)
                
            # Protect the file
            os.chmod(self.client_config_file, 0o600)
            logger.info(f"Saved registration to {self.client_config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save registration: {e}")
            
    async def load_registration(self) -> Optional[RegisteredClient]:
        """Load registration info from file"""
        try:
            if not self.client_config_file.exists():
                return None
                
            with open(self.client_config_file, "r") as f:
                data = json.load(f)
                
            # Remove our added fields
            data.pop("registered_at", None)
            
            self.registered_client = RegisteredClient(**data)
            logger.info(f"Loaded registration for client: {self.registered_client.client_id}")
            return self.registered_client
            
        except Exception as e:
            logger.error(f"Failed to load registration: {e}")
            return None
            
    async def get_or_register_client(self, initial_access_token: Optional[str] = None) -> RegisteredClient:
        """Get existing registration or register new client"""
        # Try to load existing registration
        existing = await self.load_registration()
        if existing:
            return existing
            
        # Register new client
        return await self.register_client(initial_access_token)
        
    async def update_registration(self, updates: Dict[str, Any]) -> RegisteredClient:
        """Update client registration"""
        if not self.registered_client or not self.registered_client.registration_client_uri:
            raise ValueError("No registered client or registration URI")
            
        try:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Use registration access token if available
            if self.registered_client.registration_access_token:
                headers["Authorization"] = f"Bearer {self.registered_client.registration_access_token}"
                
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    self.registered_client.registration_client_uri,
                    json=updates,
                    headers=headers
                )
                response.raise_for_status()
                
            # Update our stored client
            data = response.json()
            self.registered_client = RegisteredClient(**data)
            await self.save_registration()
            
            logger.info("Successfully updated client registration")
            return self.registered_client
            
        except Exception as e:
            logger.error(f"Failed to update registration: {e}")
            raise
            
    async def delete_registration(self) -> None:
        """Delete client registration"""
        if not self.registered_client or not self.registered_client.registration_client_uri:
            logger.warning("No registered client to delete")
            return
            
        try:
            headers = {}
            
            # Use registration access token if available
            if self.registered_client.registration_access_token:
                headers["Authorization"] = f"Bearer {self.registered_client.registration_access_token}"
                
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    self.registered_client.registration_client_uri,
                    headers=headers
                )
                response.raise_for_status()
                
            # Clean up local storage
            if self.client_config_file.exists():
                self.client_config_file.unlink()
                
            self.registered_client = None
            logger.info("Successfully deleted client registration")
            
        except Exception as e:
            logger.error(f"Failed to delete registration: {e}") 