"""Structured logging configuration for the MCP server"""

import logging
import sys
from typing import Dict, Any, Optional
from datetime import datetime
import json

from pythonjsonlogger import jsonlogger

from src.config.settings import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to the log record"""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add standard fields
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        
        # Add location info
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Add app context
        log_record['app_name'] = settings.app_name
        log_record['app_version'] = settings.app_version
        log_record['environment'] = 'production' if not settings.debug else 'development'
        
        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_record['correlation_id'] = record.correlation_id
        
        # Add user context if present
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        
        # Add request context if present
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        if hasattr(record, 'method'):
            log_record['method'] = record.method
        if hasattr(record, 'path'):
            log_record['path'] = record.path
        if hasattr(record, 'status_code'):
            log_record['status_code'] = record.status_code
        
        # Add security context if present
        if hasattr(record, 'security_event'):
            log_record['security_event'] = record.security_event
        if hasattr(record, 'client_ip'):
            log_record['client_ip'] = record.client_ip


def configure_logging() -> None:
    """Configure application logging based on settings"""
    
    # Get root logger
    root_logger = logging.getLogger()
    
    # Clear existing handlers
    root_logger.handlers = []
    
    # Set log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Create handler
    if settings.log_file_path:
        # File handler
        handler = logging.FileHandler(settings.log_file_path)
    else:
        # Console handler
        handler = logging.StreamHandler(sys.stdout)
    
    # Set formatter based on format setting
    if settings.log_format == "json":
        # JSON formatter for production
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s',
            rename_fields={
                'levelname': 'level',
                'name': 'logger'
            }
        )
    else:
        # Text formatter for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Configure specific loggers
    configure_app_loggers(log_level)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            'log_level': settings.log_level,
            'log_format': settings.log_format,
            'log_file': settings.log_file_path or 'stdout'
        }
    )


def configure_app_loggers(log_level: int) -> None:
    """Configure application-specific loggers"""
    
    # App loggers
    app_loggers = [
        'src',
        'mcp_server',
        'auth',
        'security',
    ]
    
    for logger_name in app_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
    
    # Third-party loggers (set to WARNING unless in DEBUG mode)
    third_party_loggers = [
        'uvicorn',
        'uvicorn.access',
        'uvicorn.error',
        'httpx',
        'httpcore',
        'redis',
        'urllib3',
    ]
    
    third_party_level = logging.DEBUG if settings.debug else logging.WARNING
    
    for logger_name in third_party_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(third_party_level)


class SecurityLogger:
    """Logger for security-related events"""
    
    def __init__(self):
        self.logger = logging.getLogger('security')
    
    def log_authentication_attempt(
        self,
        success: bool,
        user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        error: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log authentication attempt"""
        log_extra = {
            'security_event': 'authentication',
            'success': success,
            'user_id': user_id,
            'client_ip': client_ip,
            **(extra or {})
        }
        
        if success:
            self.logger.info(
                f"Authentication successful for user {user_id}",
                extra=log_extra
            )
        else:
            log_extra['error'] = error
            self.logger.warning(
                f"Authentication failed: {error}",
                extra=log_extra
            )
    
    def log_authorization_decision(
        self,
        user_id: str,
        resource: str,
        action: str,
        allowed: bool,
        required_scope: Optional[str] = None,
        user_scopes: Optional[list] = None,
        client_ip: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log authorization decision"""
        log_extra = {
            'security_event': 'authorization',
            'user_id': user_id,
            'resource': resource,
            'action': action,
            'allowed': allowed,
            'required_scope': required_scope,
            'user_scopes': user_scopes,
            'client_ip': client_ip,
            **(extra or {})
        }
        
        if allowed:
            self.logger.info(
                f"Access granted to {resource} for user {user_id}",
                extra=log_extra
            )
        else:
            self.logger.warning(
                f"Access denied to {resource} for user {user_id}",
                extra=log_extra
            )
    
    def log_token_validation(
        self,
        success: bool,
        token_type: str = "Bearer",
        error: Optional[str] = None,
        client_ip: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log token validation event"""
        log_extra = {
            'security_event': 'token_validation',
            'success': success,
            'token_type': token_type,
            'client_ip': client_ip,
            **(extra or {})
        }
        
        if success:
            self.logger.info(
                "Token validation successful",
                extra=log_extra
            )
        else:
            log_extra['error'] = error
            self.logger.warning(
                f"Token validation failed: {error}",
                extra=log_extra
            )


# Global security logger instance
security_logger = SecurityLogger()


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    correlation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **kwargs
) -> None:
    """Log a message with additional context"""
    extra = {
        'correlation_id': correlation_id,
        'user_id': user_id,
        **kwargs
    }
    # Remove None values
    extra = {k: v for k, v in extra.items() if v is not None}
    
    logger.log(level, message, extra=extra) 