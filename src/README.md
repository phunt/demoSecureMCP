# Source Code Structure

This directory contains the main application source code for the Secure MCP Server.

## Directory Overview

```
src/
├── app/           # FastAPI application and API endpoints
├── config/        # Configuration management and settings
└── core/          # Core utilities, middleware, and shared components
```

## Architecture Principles

### 1. **Separation of Concerns**
- `app/`: Business logic and API endpoints
- `config/`: Environment and configuration management
- `core/`: Cross-cutting concerns (logging, middleware, utilities)

### 2. **Dependency Direction**
```
app → core
 ↓      ↑
config ─┘
```
- App layer depends on core utilities and config
- Config is accessible from all layers
- Core has no dependencies on app layer

### 3. **Security First**
- All endpoints require authentication by default
- Scope-based authorization enforced at the dependency level
- Security context propagated through middleware

## Module Descriptions

### `app/` - Application Layer
The FastAPI application with all API endpoints, authentication, and business logic.

Key components:
- `main.py`: Application entry point and endpoint registration
- `auth/`: JWT validation and authorization dependencies
- `tools/`: FastMCP tool implementations (using the FastMCP framework)
- `api/`: Additional API endpoints (if needed)

### `config/` - Configuration Layer
Centralized configuration management using Pydantic Settings.

Key components:
- `settings.py`: Application settings with validation
- `validation.py`: Runtime configuration validation

### `core/` - Core Utilities Layer
Shared utilities and middleware used across the application.

Key components:
- `logging.py`: Structured logging configuration
- `middleware.py`: Request tracking and security middleware

## Key Design Patterns

### 1. **Dependency Injection**
FastAPI's dependency injection is used extensively for:
- Authentication (`get_current_user`)
- Authorization (`RequireMcpRead`, `RequireMcpWrite`)
- Configuration access
- Database connections (if applicable)

### 2. **Request/Response Models**
All API endpoints use Pydantic models for:
- Request validation
- Response serialization
- OpenAPI documentation generation

### 3. **Async/Await**
The application is fully asynchronous for:
- Better performance under load
- Non-blocking I/O operations
- Efficient resource utilization

## Adding New Features

### Creating a New Endpoint
1. Define Pydantic models in appropriate module
2. Implement business logic
3. Add FastAPI route with proper dependencies
4. Include scope requirements
5. Add tests

Example:
```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.app.auth.dependencies import RequireMcpRead

router = APIRouter()

class MyResponse(BaseModel):
    data: str

@router.get("/my-endpoint", response_model=MyResponse)
async def my_endpoint(
    user: Annotated[TokenPayload, RequireMcpRead]
) -> MyResponse:
    return MyResponse(data="Hello")
```

### Adding a New Tool
See `app/tools/README.md` for detailed instructions on creating MCP tools.

## Environment Variables

The application uses environment variables for configuration. See:
- `config/settings.py` for available settings
- `docs/ENVIRONMENT.md` for full documentation
- `.env.example` for template

## Testing

All code should include tests. Test files mirror the source structure:
```
tests/
├── test_app/
├── test_config/
└── test_core/
```

## Code Style

- Follow PEP 8
- Use type hints
- Add docstrings to all public functions
- Keep functions focused and testable
- Prefer composition over inheritance 