"""Rent module registration helper — FunctionGroupContracts.

The rent module is the tenant's rent ledger. It tracks rent payments,
payment history, and helps prove payment history in disputes.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
    module="rent",
    group_name="rent_payment_create",
    title="Rent Payment Create (SSOT)",
    description=(
        "CANONICAL create a rent payment record. The tenant logs a payment "
        "with amount, date, method, and optional note."
    ),
    inputs=("user_id", "amount", "payment_date", "method?", "note?"),
    outputs=("payment_id", "payment"),
    dependencies=("app.modules.rent.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="rent",
    group_name="rent_payments_list",
    title="Rent Payments List (SSOT)",
    description=(
        "CANONICAL list of rent payments for the tenant. Returns payments "
        "sorted by date descending. Used by the rent ledger page."
    ),
    inputs=("user_id",),
    outputs=("payments",),
    dependencies=("app.modules.rent.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="rent",
    group_name="rent_payment_get",
    title="Rent Payment Get (SSOT)",
    description=(
        "CANONICAL get a single rent payment by ID. Returns full payment "
        "details including method, note, and receipt info."
    ),
    inputs=("payment_id", "user_id"),
    outputs=("payment",),
    dependencies=("app.modules.rent.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="rent",
    group_name="rent_payment_update",
    title="Rent Payment Update (SSOT)",
    description=(
        "CANONICAL update a rent payment. The tenant can edit amount, date, "
        "method, or note."
    ),
    inputs=("payment_id", "user_id", "updates"),
    outputs=("payment",),
    dependencies=("app.modules.rent.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="rent",
    group_name="rent_payment_delete",
    title="Rent Payment Delete (SSOT)",
    description=(
        "CANONICAL delete a rent payment. Removes the payment record from "
        "the ledger."
    ),
    inputs=("payment_id", "user_id"),
    outputs=("success",),
    dependencies=("app.modules.rent.router",),
    deterministic=False,
))
