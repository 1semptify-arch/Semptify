"""Mesh Resource Configuration - Lean Mode Settings

Controls Positronic Mesh intensity to conserve resources while
maintaining core mechanics integrity.
"""

from dataclasses import dataclass
from typing import Set


@dataclass(frozen=True)
class MeshModeConfig:
    """Configuration for mesh operating mode."""
    
    mode: str  # "lean" or "full"
    max_concurrent_workflows: int
    enable_speculative_execution: bool
    enable_action_chaining: bool
    deferred_action_modules: Set[str]
    critical_only: bool
    
    def is_action_allowed(self, module: str, action: str) -> bool:
        """Check if action should execute in current mode."""
        if self.mode == "full":
            return True
        
        # Lean mode: skip deferred modules
        if module in self.deferred_action_modules:
            return False
        
        return True


# Default Lean Mode: Core mechanics only
LEAN_MESH_CONFIG = MeshModeConfig(
    mode="lean",
    max_concurrent_workflows=3,
    enable_speculative_execution=False,
    enable_action_chaining=False,
    deferred_action_modules={
        # Deferred until scale-up triggers met
        "fraud_exposure",
        "public_exposure", 
        "research",
        "legal_trails",
        "adaptive_ui",
        "context_engine",
    },
    critical_only=True,
)

# Full Mode: All registered actions enabled
FULL_MESH_CONFIG = MeshModeConfig(
    mode="full",
    max_concurrent_workflows=10,
    enable_speculative_execution=True,
    enable_action_chaining=True,
    deferred_action_modules=set(),
    critical_only=False,
)

# Active configuration - starts lean
current_mesh_config = LEAN_MESH_CONFIG


def set_mesh_mode(mode: str) -> MeshModeConfig:
    """Switch mesh operating mode."""
    global current_mesh_config
    if mode == "full":
        current_mesh_config = FULL_MESH_CONFIG
    else:
        current_mesh_config = LEAN_MESH_CONFIG
    return current_mesh_config


def get_mesh_config() -> MeshModeConfig:
    """Get current mesh configuration."""
    return current_mesh_config
