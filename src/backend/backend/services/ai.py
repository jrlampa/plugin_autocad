"""Legacy compatibility layer for `backend.services.ai`.

Canonical implementation: backend.application.ai
"""

from groq import Groq  # noqa: F401
from backend.application.ai import *  # noqa: F401,F403
