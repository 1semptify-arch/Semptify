"""Resource Intake & Integrity Engine.

Part 3 of docs/admin/SEMPTIFY_BUILD_CONTRACT.md.

This package does not render any tenant-facing output. It ingests candidate
material, tags it, fact-checks it, routes it for human approval, and releases
verified, human-approved resources into the compiled Information Composer
resource pool (data/composer_resources.json).
"""

from .engine import ResourceIntakeEngine, load_composer_resource_pool
from .schemas import ApprovedResource, ResourceCandidate, ResourcePool

__all__ = [
    "ApprovedResource",
    "ResourceCandidate",
    "ResourcePool",
    "ResourceIntakeEngine",
    "load_composer_resource_pool",
]
