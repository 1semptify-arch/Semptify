"""Legal Share module contracts — SSOT for the case-share API.

Read these before calling any endpoint. If a method or field is not here,
it does not exist. Do not invent signatures.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="legal_share",
        group_name="ls_cases",
        title="Legal Share Case Picker (SSOT)",
        description=(
            "CANONICAL case picker for the share flow. Lists the tenant's INCIDENT overlay "
            "records (same source as Case Builder / Case Review): incident_id, title, status, "
            "incident_type."
        ),
        inputs=("user_id",),
        outputs=("cases",),
        dependencies=("app.modules.legal_share.router", "app.services.incident_store"),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="legal_share",
        group_name="ls_items",
        title="Legal Share Shareable Items (SSOT)",
        description=(
            "CANONICAL item picker for a case: vault documents merged with case tags "
            "(suggested=true when the tag category is filed material — foundational, discovery, "
            "motion, evidence — so filed material is on by default and drafts/misc stay off), "
            "evidence notes, and calendar deadlines. Selection is metadata only; nothing moves "
            "the tenant's actual cloud files."
        ),
        inputs=("user_id", "case_id"),
        outputs=("case_id", "case_title", "documents", "notes", "deadlines"),
        dependencies=(
            "app.modules.legal_share.router",
            "app.modules.case_review.service",
            "app.services.vault_upload_service",
            "app.modules.calendar.service",
        ),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="legal_share",
        group_name="ls_shares",
        title="Legal Share Grants (SSOT)",
        description=(
            "CANONICAL case-share lifecycle. POST creates a CASE_SHARE overlay in the tenant's "
            "vault (reviewer label, selected documents/sections, expiring revocable owner-scoped "
            "token) and sets legal_share_initialized through the Case Review share marker + "
            "capability grant — the flag is never duplicated. GET lists shares with status and "
            "unread question counts; POST /revoke sets revoked_at. The reviewer holds only the "
            "token — no account, no login."
        ),
        inputs=("user_id", "case_id", "reviewer_label", "document_ids", "expires_days", "share_id"),
        outputs=("share", "shares", "ok"),
        dependencies=(
            "app.modules.legal_share.router",
            "app.modules.legal_share.service",
            "app.modules.case_review.service",
            "app.core.capabilities",
        ),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="legal_share",
        group_name="ls_threads",
        title="Legal Share Q&A Threads (SSOT)",
        description=(
            "CANONICAL tenant-side Q&A. GET /shares/{id}/threads lists threads and marks them "
            "tenant-read; POST reply appends the tenant's own words as side=tenant (status → "
            "answered, unread_by_reviewer). GET /questions returns unread reviewer threads "
            "across all active shares. Semptify never generates or suggests legal answers — "
            "both sides' text is verbatim."
        ),
        inputs=("user_id", "share_id", "thread_id", "body"),
        outputs=("threads", "thread", "questions"),
        dependencies=("app.modules.legal_share.router", "app.modules.legal_share.service"),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="legal_share",
        group_name="rs_portal",
        title="Reviewer Portal (SSOT — token-gated, anonymous)",
        description=(
            "CANONICAL anonymous reviewer surface under /api/legal-share/r/{token}. The "
            "owner-scoped token is the entire credential — it resolves the share in the owner's "
            "vault with no server-side index and no reviewer identity. Active shares return the "
            "shared slice: case summary, selected documents (scope-enforced), notes, deadlines, "
            "and this share's Q&A threads. Revoked → share_revoked; expired → share_expired. "
            "Document content streams read-only through shared_document_stream — originals are "
            "never modified."
        ),
        inputs=("token", "document_id", "vault_id", "body"),
        outputs=("status", "summary", "documents", "notes", "deadlines", "threads", "thread"),
        dependencies=(
            "app.modules.legal_share.router",
            "app.modules.legal_share.service",
            "app.services.shared_document_stream",
        ),
        deterministic=False,
    )
)
