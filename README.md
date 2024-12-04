# DjangoFlow

DjangoFlow is a modern, feature-rich Airflow management system designed to provide data engineers with a unified interface for managing multiple Airflow clusters. Built with Django, Tailwind, and Flowbite, it offers a sleek, responsive UI for monitoring and managing your Airflow deployments.

The Airflow API specification can be found [here](v1.yaml).

## Development Process

The project follows a structured development process with comprehensive documentation:

- **Change Tracking**: All changes are documented in `CHECKPOINT.md`
- **Development Guidelines**: Development instructions and standards are maintained in `cc-prompt.md`
- **Progress Chronicle**: Project evolution and features are tracked in `cc-chronicle.md`

# UX/UI Style Guidelines

**Important:** When being asked to implement a new feature, please consider how the user will interact with the tool.

1. Ensure that the UI is responsive and accessible for all users.
2. Provide clear and concise instructions for users to navigate the tool.
3. Use a color scheme that is visually appealing and easy to distinguish from the background.
4. Use a consistent color scheme across the entire application.
5. Use a consistent font across the entire application.
6. Use a consistent spacing and layout across the entire application.
7. Use a consistent UI theme across the entire application.

## Documentation Guidelines

When documenting the codebase, please ensure that the following guidelines are followed:
- **IMPORTANT:** The single most important piece of information to convey to the user is the purpose of the code.
- Documentation must be written in a clear and concise manner.

- All other documentation must be written in markdown.

## Coding Guidelines

When making changes to the codebase, please ensure that the following guidelines are followed:
- **Important:** Only the minimum necessary changes should be made to the codebase.
- Add semantic `data-kind` attributes to all top-level HTML elements for clarity and testability.
- When making files, please consider the following modern architecture principles:
   1. Split into feature-based modules:
      - Core logic
      - Event handlers
      - Types/interfaces

   2. Implement clean architecture:
      - Separate UI from business logic
      - Use consistent naming

## Features

- **Multi-Cluster Management**
  - View and manage multiple Airflow clusters from a single dashboard
  - Real-time cluster health monitoring
  - Easy endpoint configuration and management

- **DAG Management**
  - View all DAGs across clusters
  - Monitor DAG status and run history
  - Detailed run information with task instance counts
  - Color-coded status indicators for runs and tasks
  - Quick access to run details and logs
  - Pause/unpause DAGs

- **Monitoring & Metrics**
  - Real-time cluster health status
  - DAG processor logs and metrics
  - Task instance metrics
  - Event trigger logs
  - Cluster component logs

- **Modern UI/UX**
  - Clean, intuitive dashboard
  - Real-time updates
  - Responsive design
  - Dark mode support

## Recent Updates

### URL Pattern Standardization (Dec 4, 2024)
- Improved navigation between DAG views with consistent URL pattern naming
- Enhanced cluster filtering and error handling
- Fixed "View all runs" functionality
- Added proper 404 handling for missing DAGs

## Upcoming Features

### Monitoring System Enhancements
1. **Dashboard UI**
   - Create a modern, responsive dashboard layout
   - Add metric visualization using charts and graphs
   - Implement real-time updates using WebSockets
   - Add customizable dashboard widgets

2. **Airflow Integration**
   - Implement Airflow API client for metric collection
   - Add DAG performance monitoring
   - Track task execution statistics
   - Monitor scheduler health

3. **Alert System**
   - Create email notification system for alerts
   - Add Slack/Teams integration for notifications
   - Implement alert escalation policies
   - Add custom alert rules configuration

4. **Metric Visualization**
   - Add time-series graphs for system metrics
   - Create DAG success rate visualizations
   - Add resource usage trend analysis
   - Implement custom metric dashboards

5. **User Features**
   - Add monitoring preferences per user
   - Create custom alert thresholds
   - Implement notification preferences
   - Add dashboard customization options

### Getting Started with Monitoring

1. Ensure Redis is running:
```bash
# Check Redis status (if running in container)
docker ps | grep redis
```

2. Start Celery worker:
```bash
celery -A djangoflow worker -l info
```

3. Start Celery beat for periodic tasks:
```bash
celery -A djangoflow beat -l info
```

4. Access the monitoring endpoints:
- Dashboard: `/monitoring/dashboard/`
- Health Check: `/monitoring/health/`
- Metrics: `/monitoring/metrics/`
- Logs: `/monitoring/logs/`
- Alerts: `/monitoring/alerts/`

API endpoints are available under `/api/`:
- `/api/health/`
- `/api/metrics/`
- `/api/alerts/`
- `/api/logs/`

## Tech Stack

- **Frontend**
  - HTMX
  - Tailwind CSS
  - Flowbite Components
  - Dark mode theming support

- **Backend**
  - Django
  - SQLite database
  - Airflow REST API integration

## URL Pattern Conventions

DjangoFlow follows consistent URL naming conventions across all apps:
- List views: `appname:list`
- Detail views: `appname:detail`
- Edit views: `appname:edit`
- Delete views: `appname:delete`

## Edge Cases and Error Handling

The application is designed to handle various edge cases gracefully:
- Proper validation ensures DAGs are always associated with a cluster
- Debug logging provides clear information about application state
- Comprehensive error handling for API interactions

## Authentication

DjangoFlow supports multiple authentication methods:
- Basic username/password
- LDAP
- SAML
- OIDC

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on contributing to this project.