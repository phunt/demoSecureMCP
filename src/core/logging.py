"""Logging configuration for the application

Sets up structured JSON logging with correlation IDs and security event tracking.
"""

import logging
import sys
from datetime import datetime
from pythonjsonlogger import jsonlogger

from src.config.settings import get_settings


class CorrelationAdapter(logging.LoggerAdapter):
    """Adds correlation ID to log records"""
    
    def process(self, msg, kwargs):
        """Add correlation ID to the log record"""
        extra = kwargs.get('extra', {})
        if hasattr(self, 'correlation_id'):
            extra['correlation_id'] = self.correlation_id
        kwargs['extra'] = extra
        return msg, kwargs


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""
    
    def add_fields(self, log_record, record, message_dict):
        """Add custom fields to log record"""
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.utcnow().isoformat()
        settings = get_settings()
        log_record['app_name'] = settings.app_name
        log_record['app_version'] = settings.app_version
        log_record['environment'] = 'production' if not settings.debug else 'development'
        
        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_record['correlation_id'] = record.correlation_id


class SecurityLogger:
    """Specialized logger for security events"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        
    def log_auth_attempt(self, success: bool, user_id: str = None, client_id: str = None, reason: str = None):
        """Log authentication attempt"""
        event = {
            'event_type': 'auth_attempt',
            'success': success,
            'user_id': user_id,
            'client_id': client_id,
            'reason': reason
        }
        if success:
            self.logger.info("Authentication successful", extra=event)
        else:
            self.logger.warning("Authentication failed", extra=event)
            
    def log_authorization_check(self, resource: str, action: str, granted: bool, user_id: str = None, required_scope: str = None):
        """Log authorization check"""
        event = {
            'event_type': 'authorization_check',
            'resource': resource,
            'action': action,
            'granted': granted,
            'user_id': user_id,
            'required_scope': required_scope
        }
        self.logger.info("Authorization check", extra=event)


def configure_logging():
    """Configure application logging"""
    settings = get_settings()
    
    # Set log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Create handlers
    handlers = []
    if settings.log_file_path:
        # File handler
        handler = logging.FileHandler(settings.log_file_path)
    else:
        # Console handler
        handler = logging.StreamHandler(sys.stdout)
    
    # Set formatter based on format setting
    if settings.log_format == "json":
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s',
            rename_fields={'level': 'severity', 'name': 'logger'}
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    handlers.append(handler)
    
    # Configure root logger
    logging.root.setLevel(log_level)
    logging.root.handlers = handlers
    
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
    
    # Configure third-party loggers
    configure_third_party_loggers()


def configure_third_party_loggers():
    """Configure logging levels for third-party libraries"""
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    
    # Redis logging
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("redis.asyncio").setLevel(logging.WARNING)
    
    # JWT libraries
    logging.getLogger("jwt").setLevel(logging.WARNING)
    logging.getLogger("jose").setLevel(logging.WARNING)
    
    # Keycloak/OAuth related
    logging.getLogger("oauthlib").setLevel(logging.WARNING)
    logging.getLogger("requests_oauthlib").setLevel(logging.WARNING)
    
    # Set debug level for third-party libs only in debug mode
    settings = get_settings()
    if settings.debug:
        third_party_level = logging.DEBUG
    else:
        third_party_level = logging.WARNING
        
    for logger_name in ["uvicorn", "httpx", "httpcore"]:
        logging.getLogger(logger_name).setLevel(third_party_level)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)


# Create security logger instance
security_logger = SecurityLogger(get_logger("security")) 