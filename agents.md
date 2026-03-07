# AI Agent Guidelines - Backend

## Architecture Rules
- Follow Django REST Framework (DRF) patterns for APIs.
- **[REQUIRED]** Use `StandardizedResponseMixin` for all Admin API views to ensure consistent success/error structures.
- Keep business logic in models or service layers, not in views.
- Use serializers for data validation and transformation.

## Coding Standards
- PEP 8 compliance for Python code.
- Use descriptive variable and function names.
- Document complex logic with docstrings and comments.

## Security Constraints
- Never expose sensitive information in logs or API responses.
- Implement proper authentication and authorization for all endpoints (use `IsAdminUser` for administrative tasks).
- **[AUDIT]** Ensure administrative write operations trigger the `AuditTrailMiddleware`.
- Validate all user inputs to prevent SQL injection and other attacks.

## Safe-Editing Behavior
- Use `python manage.py check` before committing changes.
- Ensure migrations are created and applied correctly for any model changes.
- Avoid deleting existing fields or models without a clear migration path.

## Tool Usage Rules
- Use `run_command` for background tasks, migrations, and tests.
- Use `grep_search` and `find_by_name` for codebase exploration.
- Use `view_file` to understand the context of the files before modification.
