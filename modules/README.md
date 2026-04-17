# SEMPTIFY MODULAR ARCHITECTURE

## Overview

Semptify is now organized into a **modular architecture** with clear separation of concerns. Each module represents a functional area of the application, containing all related code, templates, and assets.

## Module Structure

```
modules/
├── core/           # Core application functionality
├── auth/           # Authentication & authorization
├── storage/        # Cloud storage integration
├── client-roles/   # User roles & permissions
├── vault/          # Document vault & security
├── overlay/        # UI overlays & modals
├── documents/      # Document management
├── library/        # Law library & research
├── office/         # Office tools & automation
├── tools/          # General tools & utilities
├── help/           # Help system & tutorials
├── admin/          # Administrative functions
├── timeline/       # Timeline & case management
├── navigation/     # Navigation & routing
└── api/            # API endpoints & services
```

## Module Organization

Each module follows a consistent structure:

```
module-name/
├── __init__.py         # Module initialization
├── routes.py           # FastAPI routes
├── models.py           # Pydantic/SQLAlchemy models
├── services.py         # Business logic
├── templates/          # Jinja2 templates
├── static/             # Module-specific assets
├── tests/              # Unit tests
├── README.md           # Module documentation
└── config.py           # Module configuration
```

## Design System Integration

All modules use the unified design system located in `/design-system/`:

- **Tokens**: Colors, typography, spacing, etc.
- **Components**: Reusable UI components
- **Layouts**: Page layout templates
- **Patterns**: Common interaction patterns
- **Pages**: Complete page templates

## Development Workflow

### 1. Identify the Module
Determine which module your feature belongs to based on functionality.

### 2. Add to Appropriate Module
- Routes go in `routes.py`
- Business logic goes in `services.py`
- Data models go in `models.py`
- Templates go in `templates/`
- Assets go in `static/`

### 3. Use Design System
Import and use design system components in your templates:

```html
<link rel="stylesheet" href="/design-system/index.css">
<script src="/design-system/index.js"></script>
```

### 4. Test & Verify
Run tests and verify the feature works within the module.

### 5. Update Navigation
Add navigation items to the appropriate module's navigation configuration.

## Module Responsibilities

### Core Module
- Application startup & configuration
- Database connections
- Global middleware
- Base templates & layouts

### Auth Module
- User authentication (OAuth, sessions)
- Role-based access control
- Security middleware
- Password management

### Storage Module
- Cloud storage providers (Google Drive, Dropbox, OneDrive)
- File upload/download
- Storage status monitoring
- Provider-specific logic

### Client Roles Module
- User role definitions
- Permission management
- Role-based UI customization
- Access control logic

### Vault Module
- Document encryption/decryption
- Secure file storage
- Access logging
- Document sharing

### Overlay Module
- Modal dialogs
- Toast notifications
- Loading overlays
- Confirmation dialogs

### Documents Module
- Document upload & processing
- OCR & text extraction
- Document metadata
- File type handling

### Library Module
- Legal research tools
- Document templates
- Case law database
- Legal form library

### Office Module
- Document automation
- Letter generation
- Court document preparation
- Office integration

### Tools Module
- General utilities
- Calculators
- Converters
- Helper functions

### Help Module
- User tutorials
- Documentation
- FAQ system
- Support tools

### Admin Module
- User management
- System configuration
- Analytics & reporting
- Administrative tools

### Timeline Module
- Case timeline management
- Event tracking
- Timeline visualization
- Progress tracking

### Navigation Module
- Shared navigation system
- Breadcrumb generation
- Route management
- Menu configuration

### API Module
- REST API endpoints
- GraphQL integration
- API documentation
- External integrations

## Best Practices

### Code Organization
- Keep related functionality together
- Use clear, descriptive names
- Follow Python/FastAPI conventions
- Document all public functions

### Template Structure
- Use design system components
- Follow consistent naming
- Include accessibility features
- Optimize for performance

### Testing
- Write unit tests for each module
- Test API endpoints
- Test UI components
- Include integration tests

### Documentation
- Update module READMEs
- Document API endpoints
- Include code comments
- Maintain change logs

## Migration Guide

### From Old Structure
1. Identify existing functionality
2. Determine appropriate module
3. Move code to module directory
4. Update imports and references
5. Test thoroughly

### Template Migration
1. Update template paths
2. Replace old CSS with design system
3. Update JavaScript imports
4. Test responsive design

### Asset Migration
1. Move module-specific assets
2. Update static file references
3. Optimize asset loading
4. Test asset delivery

## Getting Started

1. Choose the appropriate module for your feature
2. Create the necessary files following the module structure
3. Implement your functionality using the design system
4. Add tests and documentation
5. Submit a pull request

This modular architecture ensures Semptify remains maintainable, scalable, and consistent as it grows.