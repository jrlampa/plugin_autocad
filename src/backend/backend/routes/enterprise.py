"""Legacy compatibility layer for `backend.routes.enterprise`.

Canonical implementation: backend.infrastructure.routes.enterprise
"""

import types
import backend.infrastructure.routes.enterprise as _ent

router = _ent.router  # noqa: F401

# Legacy tests access these module-level objects directly
_norma_lock = _ent._norma_lock  # noqa: F401
_norma_config = _ent._norma_config  # noqa: F401
threading = types.SimpleNamespace(Thread=_ent.threading.Thread)  # noqa: F401

# Legacy tests call these handlers/helpers directly
set_norma_config = _ent.set_norma_config  # noqa: F401
_get_local_stats = _ent._get_local_stats  # noqa: F401
