import logging

from app.modules.legal_filing import router as legal_filing_router

logger = logging.getLogger(__name__)

# Thin wrapper that mounts the legal_filing router (app/modules/legal_filing/router.py).


def init_module(app):
    app.include_router(legal_filing_router, tags=["Legal Filing"])
