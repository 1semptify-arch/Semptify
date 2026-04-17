# Modular Component System Documentation

## Overview

The Semptify Modular Component System is a comprehensive, stateless, event-driven architecture that transforms the GUI into reusable, maintainable components organized by function groups and roles. This system extends the existing single source of truth foundation while maintaining the project's core values of protecting tenant rights and providing excellent user experiences.

## Architecture

### Core Principles

1. **Stateless Components**: All components receive configuration via data attributes and emit events for integration
2. **Event-Driven Communication**: Components communicate through structured custom events
3. **Role-Based Adaptation**: Components adapt behavior and styling based on user roles
4. **Function Group Organization**: Components are organized by functional purpose (Capture, Understand, Plan)
5. **Single Source of Truth**: All components extend the existing design system and patterns

### System Layers

```
Role Pages (tenant_dashboard.html, advocate_dashboard.html, etc.)
    |
    v
Role-Specific Components (tenant/, advocate/, legal/, admin/)
    |
    v
Function Group Components (capture/, understand/, plan/)
    |
    v
Design System (index.css, index.js)
    |
    v
Backend Integration (components.py API endpoints)
```

## Component Structure

### Function Groups

#### Capture Function Group
Components for information intake and document management:

- **Upload Zone** (`upload-zone.html/.css`): Drag-and-drop file upload with progress tracking
- **Quick Input** (`quick-input.html/.css`): Text input with type selection and suggestions
- **Voice Intake** (`voice-intake.html/.css`): Real-time speech-to-text recording

#### Understand Function Group
Components for analysis and rights understanding:

- **Timeline View** (`timeline-view.html/.css`): Chronological and grouped timeline views
- **Rights Analysis** (`rights-analysis.html/.css`): AI-powered rights detection with confidence scores
- **Risk Detection** (`risk-detection.html/.css`): Risk assessment with priority levels

#### Plan Function Group
Components for action planning and deadline management:

- **Action List** (`action-list.html/.css`): Prioritized action items with progress tracking
- **Deadline Tracker** (`deadline-tracker.html/.css`): Calendar and list views for deadline management
- **Next Step Card** (`next-step-card.html/.css`): AI-recommended next steps with alternatives

### Role-Specific Components

#### Tenant Role (Blue Theme)
- **Dashboard** (`tenant/dashboard.html`): Comprehensive tenant dashboard with emergency actions
- **Case Summary** (`tenant/case-summary.html`): Focused case overview with key metrics
- **Emergency Actions** (`tenant/emergency-actions.html`): Critical action items requiring immediate attention

#### Advocate Role (Purple Theme)
- **Dashboard** (`advocate/dashboard.html`): Client management and case oversight
- **Client Management** (`advocate/client-management.html`): Comprehensive client tracking with handoff capabilities

#### Legal Role (Green Theme)
- **Dashboard** (`legal/dashboard.html`): Legal case review and document analysis
- **Case Review Queue**: Pending legal cases needing review

#### Admin Role (Red Theme)
- **Dashboard** (`admin/dashboard.html`): System oversight and user management
- **System Metrics**: Performance monitoring and health indicators

## Event System

### Event Namespaces

- **Capture Events**: `capture-upload`, `capture-quick-input`, `capture-voice-input`
- **Understand Events**: `understand-timeline-select`, `understand-rights-select`, `understand-risk-select`
- **Plan Events**: `plan-action-select`, `plan-deadline-select`
- **Role Events**: `tenant-emergency-select`, `advocate-handoff-client`, `legal-start-review`, `admin-system-maintenance`

### Event Structure

```javascript
const event = new CustomEvent('capture-upload', {
  detail: {
    component_id: 'upload_zone_123',
    role: 'tenant',
    timestamp: '2026-04-16T20:00:00Z',
    files: [...],
    total_size: 1024
  }
});
```

### Event Handling

Components emit events that are caught by the page-level JavaScript and sent to backend endpoints:

```javascript
document.addEventListener('capture-upload', async (event) => {
  const response = await fetch('/api/components/capture/upload', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(event.detail)
  });
  
  const result = await response.json();
  if (result.success) {
    // Update UI accordingly
  }
});
```

## Backend Integration

### API Endpoints

#### Component Configuration
- `GET /api/components/config/{role}` - Get role-specific component configuration

#### Workspace Stage Integration
- `GET /api/components/workspace-stage` - Get current workspace stage
- `GET /api/components/next-step` - Get recommended next step

#### Capture Function Group
- `POST /api/components/capture/upload` - Handle file uploads
- `POST /api/components/capture/input` - Handle text input
- `POST /api/components/capture/voice` - Handle voice recordings

#### Understand Function Group
- `POST /api/components/understand/timeline` - Handle timeline selections
- `POST /api/components/understand/rights` - Handle rights analysis
- `POST /api/components/understand/risk` - Handle risk assessments

#### Plan Function Group
- `POST /api/components/plan/action` - Handle action selections
- `POST /api/components/plan/deadline` - Handle deadline selections

#### Role-Specific Actions
- `POST /api/components/tenant/emergency-action` - Handle tenant emergency actions
- `POST /api/components/advocate/handoff-client` - Handle client handoffs
- `POST /api/components/legal/start-review` - Start legal reviews
- `POST /api/components/admin/system-maintenance` - Handle admin maintenance

### Backend Integration Points

The component system integrates with existing backend services:

- **Document Storage**: Connects to `app.routers.storage` for file management
- **Timeline System**: Integrates with `app.routers.timeline` for timeline data
- **Legal Analysis**: Connects to `app.routers.legal_analysis` for rights analysis
- **Action System**: Integrates with `app.routers.actions` for action management
- **Calendar System**: Connects to `app.routers.calendar` for deadline tracking

## Workspace Stage Model Integration

### Dynamic Content Adaptation

Components adapt their behavior based on the current workspace stage:

```javascript
// Example: Urgent components highlighted when urgency is high
if (workspaceStage.urgency === 'high') {
  document.querySelectorAll('.deadline-tracker, .emergency-actions')
    .forEach(el => el.classList.add('urgent'));
}

// Example: Document capture prioritized when no documents exist
if (!workspaceStage.has_documents) {
  document.querySelector('.upload-zone').classList.add('priority');
}
```

### Stage-Based Component Visibility

Components can be shown/hidden based on workspace stage:

- **Storage Connected**: Show capture components
- **Documents Available**: Show understand components
- **Timeline Built**: Show plan components
- **High Urgency**: Highlight emergency and deadline components

## Onboarding System

### Unified Onboarding Flow

All roles go through the same 6-step onboarding process:

1. **Welcome**: Introduction to Semptify and mission
2. **Role Selection**: Choose user role (Tenant/Advocate/Legal/Admin)
3. **Capture Demo**: Learn how to add information
4. **Understand Demo**: See rights analysis features
5. **Plan Demo**: Understand action planning
6. **Complete**: Summary and role-specific redirection

### Role-Specific Redirection

After onboarding completion, users are redirected to their role-specific dashboard:

- **Tenant** `/tenant/dashboard`
- **Advocate** `/advocate/dashboard`
- **Legal** `/legal/dashboard`
- **Admin** `/admin/dashboard`

### Progress Tracking

Onboarding progress is tracked in localStorage and includes:

- Current step
- Completed steps
- Step history with timestamps
- Role-specific configuration

## Styling and Theming

### Design System Integration

The component system extends the existing design system:

- **CSS Variables**: Role-specific color variables
- **Component Styles**: Scoped CSS for each component
- **Responsive Design**: Mobile-first approach with breakpoints
- **Accessibility**: ARIA labels, keyboard navigation, screen reader support

### Role-Specific Themes

Each role has its own color theme:

```css
:root {
  --color-tenant-primary: #3b82f6;
  --color-advocate-primary: #7c3aed;
  --color-legal-primary: #10b981;
  --color-admin-primary: #ef4444;
}
```

### Dark Mode Support

All components support dark mode through CSS variable adaptation.

## Testing and Validation

### Test Suite

Comprehensive test suite covers:

- **Component Rendering**: HTML structure and CSS classes
- **Event Handling**: Event emission and processing
- **API Integration**: Backend endpoint connectivity
- **Role Functionality**: Role-specific behavior
- **Performance**: Response times and loading
- **Accessibility**: ARIA compliance and keyboard navigation

### Validation Script

Run the validation script to test the complete system:

```bash
python scripts/validate_modular_system.py
```

The validation script checks:

- File structure completeness
- CSS integration and imports
- HTML template structure
- API endpoint accessibility
- Event system functionality
- Role-specific features
- Performance metrics

## Usage Examples

### Including Components in Pages

```html
<!-- Include design system -->
<link rel="stylesheet" href="/design-system/index.css">

<!-- Include component -->
{% include "design-system/components/function-groups/capture/upload-zone.html" %}

<!-- Or include role-specific dashboard -->
{% include "design-system/components/function-groups/role-specific/tenant/dashboard.html" %}
```

### Component Configuration

```html
<div class="upload-zone" 
     data-component-id="upload_zone_123"
     data-role="tenant"
     data-auto-upload="true"
     data-max-file-size="10485760">
</div>
```

### JavaScript Integration

```javascript
// Listen for component events
document.addEventListener('capture-upload', (event) => {
  console.log('Files uploaded:', event.detail.files);
});

// Configure component
const component = document.getElementById('upload_zone_123');
component.dataset.autoUpload = 'true';
```

## Performance Optimization

### Loading Strategies

- **Lazy Loading**: Components load when needed
- **Code Splitting**: Function groups loaded independently
- **Caching**: CSS and JavaScript cached aggressively
- **Minification**: Production assets minified

### Optimization Techniques

- **Event Delegation**: Efficient event handling
- **Virtual Scrolling**: For large lists
- **Image Optimization**: Responsive images and lazy loading
- **Bundle Splitting**: Separate bundles per role

## Maintenance and Extensibility

### Adding New Components

1. Create HTML template in appropriate function group
2. Create CSS file with component styles
3. Add component to function group index.css
4. Create event handlers for component interactions
5. Add backend endpoints if needed
6. Update documentation and tests

### Adding New Roles

1. Create role-specific directory
2. Define role color theme
3. Create role-specific components
4. Add role configuration to components.py
5. Create role dashboard page
6. Update onboarding redirection

### Updating Existing Components

1. Modify HTML template
2. Update CSS styles
3. Update event handlers
4. Update backend endpoints if needed
5. Run tests and validation

## Troubleshooting

### Common Issues

1. **Components Not Loading**: Check CSS imports and file paths
2. **Events Not Firing**: Verify event listeners and component IDs
3. **Backend Integration**: Check API endpoints and CORS settings
4. **Role Styling**: Verify CSS variables and theme application
5. **Workspace Stage**: Check stage model integration

### Debug Tools

- **Browser DevTools**: Inspect components and events
- **Network Tab**: Monitor API calls and responses
- **Console**: Check for JavaScript errors
- **Validation Script**: Run comprehensive system check

## Future Enhancements

### Planned Features

- **Additional Function Groups**: Act, Track, Collaborate components
- **Advanced Analytics**: Component usage tracking
- **AI Integration**: Enhanced AI-powered features
- **Mobile Apps**: Native mobile component support
- **Real-time Collaboration**: Multi-user component interactions

### Extension Points

- **Custom Components**: Plugin architecture for custom components
- **Third-party Integration**: External service integration
- **Advanced Theming**: Custom theme system
- **Component Marketplace**: Share and reuse components

## Conclusion

The Modular Component System provides a solid foundation for Semptify's GUI that is:

- **Maintainable**: Clear structure and separation of concerns
- **Scalable**: Easy to add new components and features
- **Accessible**: Full accessibility support
- **Performant**: Optimized loading and rendering
- **User-Centric**: Designed around user needs and workflows

This system enables rapid development of new features while maintaining consistency and quality across the application, ultimately helping to better protect tenant rights through improved user experiences.
