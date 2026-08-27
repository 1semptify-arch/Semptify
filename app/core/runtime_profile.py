"""
Runtime Profile System
=======================

Governs runtime INFRASTRUCTURE services — Positronic Brain integrations,
Mesh Network + Distributed Mesh, Module Hub full registration, the
sentence-transformer embedding model, and performance monitoring — i.e.
what the process loads in the background, independent of product features.

This is a deliberately separate axis from `app/core/product_manifest.py`,
which governs product FEATURE TIERS (what a tenant/attorney/advocate sees:
Briefcase, Case Manager overlay, ADR-0008 narration, OCR Pass 2+, etc.).
Mixing "what does this user get" with "what does this process load" into
one manifest would make both harder to read later, so the two files follow
the same pattern (named, inspectable, single source of truth) without
being merged.

Profile selection
------------------
1. `DEPLOY_TARGET` (existing, unchanged single source of truth for deploy
   context — see `product_manifest.get_deploy_target()`) determines the
   DEFAULT profile:
     - unset, or any value other than "render_mvp"  -> "local_dev"
     - "render_mvp"                                  -> "render_mvp"
   This module does NOT introduce new `DEPLOY_TARGET` values (e.g. a
   literal "local" or "render"). The existing convention only defines
   "render_mvp" as a real value (set in `render.yaml` / `Dockerfile.render`);
   local dev has never set `DEPLOY_TARGET` at all. Inventing new values
   here would require also touching `product_manifest.is_mvp_deploy()`
   and the Render deploy config, which is explicitly out of scope for this
   task ("do not change Render's actual deployed behavior").

2. `LOAD_PROFILE` (new, optional) OVERRIDES the derived default, for when
   "where deployed" and "what should run right now" diverge, e.g.
   `LOAD_PROFILE=local_dev_semantic` to test semantic search locally
   without the full stack, or `LOAD_PROFILE=full` to force everything on
   locally for diagnosis.

3. `ENABLE_HEAVY_SERVICES=false` (legacy) is still honored as a hard
   override that forces every infra flag off regardless of the chosen
   profile. This preserves the original Render emergency-rollback path
   verbatim — it is a well-known, muscle-memory switch, not something to
   remove outright. `ENABLE_HEAVY_SERVICES=true` (or unset) is a no-op;
   it does not force anything on. Use `LOAD_PROFILE=full` for that.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, replace

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoadProfile:
    """A named, inspectable set of runtime infrastructure toggles.

    Each flag corresponds to a startup decision in `app/main.py`. Adding a
    new toggle means adding a field here and a matching flag in every
    profile below — there should never be a scattered `if` check in
    `main.py` that isn't backed by a field on this dataclass.
    """

    name: str
    description: str
    positronic_brain: bool  # Positronic Brain integrations + Location Service
    # (Location Service registers into positronic_mesh, the Brain-adjacent
    # action registry — see app/services/location_service.py:register_with_mesh)
    module_hub: bool  # register_all_modules() / register_all_actions()
    mesh_network: bool  # Mesh Network + Distributed Mesh (mesh_handlers)
    embedding_model: bool  # sentence-transformer (all-MiniLM-L6-v2) for Layer 2 semantic retrieval
    performance_monitoring: bool  # background sampler + per-request middleware

    def flags(self) -> dict[str, bool]:
        return {
            "positronic_brain": self.positronic_brain,
            "module_hub": self.module_hub,
            "mesh_network": self.mesh_network,
            "embedding_model": self.embedding_model,
            "performance_monitoring": self.performance_monitoring,
        }


_PROFILES: dict[str, LoadProfile] = {
    "local_dev": LoadProfile(
        name="local_dev",
        description=(
            "Minimal local dev footprint. Skips Positronic Brain, Mesh "
            "Network, Module Hub full registration, the embedding model, "
            "and performance monitoring, so a single route/feature can be "
            "verified without loading the full production surface area."
        ),
        positronic_brain=False,
        module_hub=False,
        mesh_network=False,
        embedding_model=False,
        performance_monitoring=False,
    ),
    "local_dev_semantic": LoadProfile(
        name="local_dev_semantic",
        description=(
            "Same as local_dev, plus the sentence-transformer embedding "
            "model, for manual semantic-search testing locally."
        ),
        positronic_brain=False,
        module_hub=False,
        mesh_network=False,
        embedding_model=True,
        performance_monitoring=False,
    ),
    "render_mvp": LoadProfile(
        name="render_mvp",
        description=(
            "Current Render-tuned production behavior. All infrastructure "
            "services on except the embedding model, which is loaded on first "
            "request. Preloading all-MiniLM-L6-v2 at startup adds 25-100 MB "
            "of RAM on top of an already-capped free-tier container, so it "
            "is now warmed lazily while the retrieval code still caches it "
            "as a singleton after the first use."
        ),
        positronic_brain=True,
        module_hub=True,
        mesh_network=True,
        embedding_model=False,
        performance_monitoring=True,
    ),
    "full": LoadProfile(
        name="full",
        description=(
            "Complete system running locally, deliberately. Identical "
            "flags to render_mvp; kept as a distinct, explicit name so "
            "startup logs and env vars communicate intent (\"I want "
            "everything on\") rather than implying a Render deploy."
        ),
        positronic_brain=True,
        module_hub=True,
        mesh_network=True,
        embedding_model=True,
        performance_monitoring=True,
    ),
}


def _derive_default_profile_name() -> str:
    """Derive the default profile name from the existing DEPLOY_TARGET value."""
    deploy_target = os.getenv("DEPLOY_TARGET")
    if deploy_target == "render_mvp":
        return "render_mvp"
    return "local_dev"


def get_active_profile() -> LoadProfile:
    """Resolve the active LoadProfile from env vars. Pure/idempotent — safe to
    call multiple times (e.g. once in `create_app()`, once in `lifespan()`)."""
    override = os.getenv("LOAD_PROFILE")
    if override:
        if override in _PROFILES:
            name = override
        else:
            logger.warning(
                "LOAD_PROFILE=%s is not a known profile (%s) - falling back to derived default",
                override,
                ", ".join(_PROFILES),
            )
            name = _derive_default_profile_name()
    else:
        name = _derive_default_profile_name()

    profile = _PROFILES[name]

    # Legacy emergency rollback switch - still honored, not removed.
    # Only fires when it would actually change something, so it doesn't
    # relabel an already-minimal local_dev profile.
    if os.getenv("ENABLE_HEAVY_SERVICES", "true").lower() == "false" and any(profile.flags().values()):
        logger.warning(
            "ENABLE_HEAVY_SERVICES=false overrides profile '%s' -> forcing all infra flags off "
            "(legacy emergency rollback path, preserved for Render OOM incidents)",
            profile.name,
        )
        profile = replace(
            profile,
            name=f"{profile.name}+heavy_disabled",
            description=profile.description + " [forced off by legacy ENABLE_HEAVY_SERVICES=false]",
            positronic_brain=False,
            module_hub=False,
            mesh_network=False,
            embedding_model=False,
            performance_monitoring=False,
        )

    return profile


def log_active_profile() -> LoadProfile:
    """Resolve and log the active profile once at startup. Returns the
    resolved profile so the caller can stash it (e.g. on `app.state`) instead
    of re-deriving it, though re-deriving is also safe."""
    profile = get_active_profile()
    deploy_target = os.getenv("DEPLOY_TARGET") or "(unset - local)"
    load_profile_env = os.getenv("LOAD_PROFILE") or "(unset - derived from DEPLOY_TARGET)"
    logger.info("=" * 60)
    logger.info("Runtime Load Profile: %s", profile.name)
    logger.info("  DEPLOY_TARGET=%s  LOAD_PROFILE=%s", deploy_target, load_profile_env)
    logger.info("  %s", profile.description)
    for flag_name, enabled in profile.flags().items():
        logger.info("  - %-24s %s", flag_name, "ON" if enabled else "off")
    logger.info("=" * 60)
    return profile
