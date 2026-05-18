"""
Contacts Module Manifest

Self-contained SDK module for managing case-related contacts.
- Landlords, property managers
- Attorneys (opposing and legal aid)
- Witnesses
- Inspectors, agencies, courts
- Any person/organization involved in your case
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="contacts",
    display_name="Contact Manager",
    description="Manage case-related contacts: landlords, attorneys, witnesses, agencies",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.contacts.router",
    tags=("Contact Manager",),
)
