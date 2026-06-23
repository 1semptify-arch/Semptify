"""Contacts module registration helper — FunctionGroupContracts.

The contacts module is the RECORD pillar's people layer. It stores contact
info for landlords, witnesses, neighbors, agencies, and other parties. 
Contacts can be imported from document extraction or added manually.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
    module="contacts",
    group_name="contacts_list",
    title="Contacts List (SSOT)",
    description=(
        "CANONICAL list of contacts for the current user. Supports filtering "
        "by contact_type and role. Returns contact summaries."
    ),
    inputs=("user_id", "contact_type?", "role?"),
    outputs=("contacts", "total"),
    dependencies=("app.modules.contacts.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="contacts",
    group_name="contacts_create",
    title="Contacts Create (SSOT)",
    description=(
        "CANONICAL create a new contact. The tenant adds a landlord, "
        "witness, neighbor, or other party with contact info."
    ),
    inputs=("user_id", "name", "contact_type", "phone?", "email?", "address?"),
    outputs=("contact_id", "contact"),
    dependencies=("app.modules.contacts.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="contacts",
    group_name="contacts_get",
    title="Contacts Get (SSOT)",
    description=(
        "CANONICAL get a single contact by ID. Returns full contact info "
        "including interactions log."
    ),
    inputs=("contact_id", "user_id"),
    outputs=("contact",),
    dependencies=("app.modules.contacts.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="contacts",
    group_name="contacts_update",
    title="Contacts Update (SSOT)",
    description=(
        "CANONICAL update a contact. The tenant can edit name, phone, "
        "email, address, or notes."
    ),
    inputs=("contact_id", "user_id", "updates"),
    outputs=("contact",),
    dependencies=("app.modules.contacts.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="contacts",
    group_name="contacts_delete",
    title="Contacts Delete (SSOT)",
    description=(
        "CANONICAL delete a contact. Removes the contact and all "
        "associated interactions."
    ),
    inputs=("contact_id", "user_id"),
    outputs=("status",),
    dependencies=("app.modules.contacts.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="contacts",
    group_name="contacts_toggle_star",
    title="Contacts Toggle Star (SSOT)",
    description=(
        "CANONICAL star or unstar a contact. Starred contacts appear at "
        "the top of the contacts list."
    ),
    inputs=("contact_id", "user_id"),
    outputs=("starred",),
    dependencies=("app.modules.contacts.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="contacts",
    group_name="contacts_list_interactions",
    title="Contacts List Interactions (SSOT)",
    description=(
        "CANONICAL list of interactions with a contact. Returns logged "
        "calls, emails, meetings, and other interactions."
    ),
    inputs=("contact_id", "user_id"),
    outputs=("interactions",),
    dependencies=("app.modules.contacts.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="contacts",
    group_name="contacts_log_interaction",
    title="Contacts Log Interaction (SSOT)",
    description=(
        "CANONICAL log an interaction with a contact. The tenant records "
        "a call, email, meeting, or other interaction with the contact."
    ),
    inputs=("contact_id", "user_id", "interaction_type", "description?", "date?"),
    outputs=("interaction_id",),
    dependencies=("app.modules.contacts.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="contacts",
    group_name="contacts_import_from_extraction",
    title="Contacts Import From Extraction (SSOT)",
    description=(
        "CANONICAL import contacts from document extraction results. "
        "Takes parties extracted from a document and creates contacts "
        "from them. Avoids manual entry."
    ),
    inputs=("user_id", "extracted_contacts"),
    outputs=("imported", "total"),
    dependencies=("app.modules.contacts.router", "app.modules.documents.router"),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="contacts",
    group_name="contacts_quick_add_landlord",
    title="Contacts Quick Add Landlord (SSOT)",
    description=(
        "CANONICAL quick-add a landlord contact. Simplified form with "
        "just name, phone, and email. Used by the tenant dashboard's "
        "quick-add feature."
    ),
    inputs=("user_id", "name", "phone?", "email?"),
    outputs=("contact_id",),
    dependencies=("app.modules.contacts.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="contacts",
    group_name="contacts_quick_add_witness",
    title="Contacts Quick Add Witness (SSOT)",
    description=(
        "CANONICAL quick-add a witness contact. Simplified form with "
        "name and relationship. Used by the tenant dashboard's quick-add."
    ),
    inputs=("user_id", "name", "relationship"),
    outputs=("contact_id",),
    dependencies=("app.modules.contacts.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="contacts",
    group_name="contacts_for_forms",
    title="Contacts For Forms (SSOT)",
    description=(
        "CANONICAL list of contacts formatted for form autofill. Returns "
        "contacts in a simplified structure for populating form fields."
    ),
    inputs=("user_id",),
    outputs=("contacts",),
    dependencies=("app.modules.contacts.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="contacts",
    group_name="contacts_types",
    title="Contacts Types Reference (SSOT)",
    description=(
        "CANONICAL list of available contact types and roles. Used by "
        "the frontend to populate contact type dropdowns."
    ),
    inputs=(),
    outputs=("types", "roles"),
    dependencies=("app.modules.contacts.router",),
    deterministic=True,
))
