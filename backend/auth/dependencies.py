"""FastAPI auth dependencies.

Public surface:
  - ``require_auth``      — the canonical dependency for all protected routes,
                            sourced from middleware.auth.  Raises 401 using the
                            canonical error envelope dict.
  - ``get_current_user_id`` — kept for backward compatibility; delegates to
                            ``require_auth``.
"""

from ..middleware.auth import require_auth

# Backward-compatible alias so any code still referencing get_current_user_id
# gets the same canonical behaviour without requiring a rename.
get_current_user_id = require_auth

__all__ = ["require_auth", "get_current_user_id"]
