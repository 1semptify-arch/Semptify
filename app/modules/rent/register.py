"""Rent module registration helper — FunctionGroupContracts.

The rent module is the tenant's rent ledger. It tracks rent payments,
fees, deposits, credits, and running balance to help prove payment
history and resolve disputes.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="rent",
        group_name="rent_ledger_create",
        title="Rent Ledger Create (SSOT)",
        description=(
            "CANONICAL create a rent ledger entry. Supports payments, fees, "
            "deposits, credits, and charges. Amount is in dollars (input), stored "
            "as cents (DB). Computes and returns the running balance after the entry."
        ),
        inputs=(
            "user_id",
            "entry_type",
            "amount",
            "payment_date",
            "due_date?",
            "period_covered?",
            "status?",
            "payment_method?",
            "source?",
            "receipt_document_id?",
            "overlay_link?",
            "notes?",
        ),
        outputs=("payment_id", "payment"),
        dependencies=("app.modules.rent.router", "app.models.models.RentPayment"),
        deterministic=False,
    )
)


register_function_group(
    FunctionGroupContract(
        module="rent",
        group_name="rent_ledger_list",
        title="Rent Ledger List (SSOT)",
        description=(
            "CANONICAL list rent ledger entries for the tenant. Returns entries "
            "sorted newest first with running balance for each. Used by the rent "
            "ledger page."
        ),
        inputs=("user_id",),
        outputs=("payments",),
        dependencies=("app.modules.rent.router",),
        deterministic=True,
    )
)


register_function_group(
    FunctionGroupContract(
        module="rent",
        group_name="rent_ledger_get",
        title="Rent Ledger Get (SSOT)",
        description=(
            "CANONICAL get a single rent ledger entry by ID. Returns full details "
            "including entry type, source, overlay link, and running balance. "
            "Ownership enforced."
        ),
        inputs=("payment_id", "user_id"),
        outputs=("payment",),
        dependencies=("app.modules.rent.router",),
        deterministic=True,
    )
)


register_function_group(
    FunctionGroupContract(
        module="rent",
        group_name="rent_ledger_update",
        title="Rent Ledger Update (SSOT)",
        description=(
            "CANONICAL update a rent ledger entry. The tenant can edit amount, "
            "date, entry type, source, status, method, or overlay link. Running "
            "balance is recomputed on save."
        ),
        inputs=("payment_id", "user_id", "updates"),
        outputs=("payment",),
        dependencies=("app.modules.rent.router",),
        deterministic=False,
    )
)


register_function_group(
    FunctionGroupContract(
        module="rent",
        group_name="rent_ledger_delete",
        title="Rent Ledger Delete (SSOT)",
        description=("CANONICAL delete a rent ledger entry. Ownership enforced."),
        inputs=("payment_id", "user_id"),
        outputs=("deleted",),
        dependencies=("app.modules.rent.router",),
        deterministic=False,
    )
)
