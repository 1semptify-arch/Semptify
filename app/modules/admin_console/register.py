"""Admin Console module registration helper - FunctionGroupContracts.

The admin console provides system maintenance, user management, module
flags, and AI tools for authorized admin/manager roles.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

# Preserve the existing module manifest registration.
from app.modules.admin_console.module_admin_console import register_admin_console_module  # noqa: F401

# The contracts in router.py and module_flags.py are wrapped in try/try blocks
# to avoid circular imports at router load time. Importing them here at startup
# (after module_contracts is available) registers the contracts in the canonical
# registry.
from app.modules.admin_console import router  # noqa: F401
from app.modules.admin_console import module_flags  # noqa: F401
