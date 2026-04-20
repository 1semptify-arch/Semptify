"""
Semptify Modules Package
========================

Place new module files in this directory.
Each module should follow the SDK pattern - see example_payment_tracking.py
"""

# Import modules here for easy access
# from app.modules.example_payment_tracking import initialize as init_payment_tracking
from app.modules.free_api_pack import api as free_api_registry

__all__ = ["free_api_registry"]
