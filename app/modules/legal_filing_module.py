
from app.routers.legal_filing import router as legal_filing_router

# Placeholder for actual module integration with mesh/network.

def init_module(app):
    app.include_router(legal_filing_router, tags=["Legal Filing"])
