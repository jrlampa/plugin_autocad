"""Legacy compatibility layer for tests importing `backend.services.webhooks`.

Canonical implementation:
- backend.application.webhooks.WebhookService
- backend.application.webhooks.webhook_service
"""

import requests  # noqa: F401

from backend.application.webhooks import WebhookService, webhook_service  # noqa: F401
