"""Generate Semptify Technical Overview PDF for sharing with tech people."""
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    ListFlowable,
    ListItem,
    Preformatted,
    HRFlowable,
)

OUTPUT = Path(__file__).resolve().parent.parent / "Semptify_Technical_Overview.pdf"


def build_styles() -> dict:
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "Tagline",
            parent=styles["Normal"],
            fontSize=11,
            textColor=colors.HexColor("#555555"),
            spaceAfter=14,
            italic=True,
        )
    )
    styles.add(
        ParagraphStyle(
            "CodeBlock",
            parent=styles["Code"],
            fontSize=9,
            leading=12,
            backColor=colors.HexColor("#f4f4f4"),
            borderPadding=6,
            spaceBefore=6,
            spaceAfter=10,
        )
    )
    return styles


def bullet(items, styles, style_name="Normal"):
    return ListFlowable(
        [ListItem(Paragraph(t, styles[style_name]), leftIndent=12) for t in items],
        bulletType="bullet",
        leftIndent=14,
        spaceBefore=2,
        spaceAfter=6,
    )


def main() -> None:
    styles = build_styles()
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=LETTER,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.8 * inch,
        bottomMargin=0.8 * inch,
        title="Semptify — Technical Overview",
        author="Semptify",
    )
    story = []

    story.append(Paragraph("Semptify — Technical Overview", styles["Heading1"]))
    story.append(
        Paragraph(
            "A tenant-rights platform built on FastAPI with a storage-as-identity auth model.",
            styles["Tagline"],
        )
    )
    story.append(HRFlowable(width="100%", color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 10))

    # What it is
    story.append(Paragraph("What it is", styles["Heading2"]))
    story.append(
        Paragraph(
            "Semptify is a tenant-rights platform that helps renters document landlord "
            "interactions, organize evidence, and access verified housing-rights info. "
            "Free, no ads, privacy-first.",
            styles["Normal"],
        )
    )

    # Stack
    story.append(Paragraph("Stack", styles["Heading2"]))
    story.append(
        bullet(
            [
                "<b>Backend:</b> Python 3.11.9 (hard-pinned), FastAPI, async-first (all I/O is async/await)",
                "<b>DB:</b> PostgreSQL + Redis, async SQLAlchemy, Alembic migrations",
                "<b>Validation:</b> Pydantic everywhere",
                "<b>Storage:</b> User-owned cloud (Google Drive, Dropbox, OneDrive) + Cloudflare R2 for system-only indexes",
                "<b>Deploy:</b> Render (render.yaml), Docker, Cloudflare in front",
                "<b>AI:</b> Pluggable — OpenAI / Azure / Ollama / none",
            ],
            styles,
        )
    )

    # Storage = Identity
    story.append(Paragraph("The Unusual Architectural Choice: Storage = Identity", styles["Heading2"]))
    story.append(
        Paragraph(
            "There are no passwords and no email verification. Auth is delegated to the user's cloud storage provider:",
            styles["Normal"],
        )
    )
    story.append(
        bullet(
            [
                "User clicks \"Connect with Google Drive\" (or Dropbox/OneDrive)",
                "OAuth2 flow → Semptify gets a token scoped to a private app folder",
                "Encrypted auth token is stored in the user's own storage (.semptify/auth_token.enc)",
                "HMAC-signed session cookie issued: &lt;user_id&gt;.&lt;hmac_signature&gt;",
            ],
            styles,
        )
    )
    story.append(
        Paragraph(
            "User IDs are structured: &lt;provider_code&gt;&lt;role_code&gt;&lt;8-char-random&gt; "
            "(e.g. GUabc12345 = Google-User). Provider codes: G/D/O. "
            "Roles: U/Tenant, A/Admin, M/Manager, V/Advocate, L/Legal.",
            styles["Normal"],
        )
    )
    story.append(Paragraph("<b>Why this matters technically:</b>", styles["Normal"]))
    story.append(
        bullet(
            [
                "Server holds no user data — documents live in the user's cloud",
                "Self-custody: deleting the app folder revokes access",
                "Portable identity tied to data ownership, not a silo'd account DB",
            ],
            styles,
        )
    )

    # Onboarding
    story.append(Paragraph("Onboarding as a Gate Machine", styles["Heading2"]))
    story.append(
        Paragraph(
            "Onboarding is gate-driven, not flag-driven. Two gates only:",
            styles["Normal"],
        )
    )
    story.append(
        Preformatted(
            "[nothing] -> storage_connected -> vault_initialized -> [done]",
            styles["CodeBlock"],
        )
    )
    story.append(
        Paragraph(
            "Each gate is checked server-side and unlocks the next stage. Routing is SSOT — "
            "<font face='Courier'>navigation.get_stage(...)</font> returns paths, no hardcoded URL "
            "strings anywhere (enforced via <font face='Courier'>app/core/ssot_guard.py</font>).",
            styles["Normal"],
        )
    )

    # Vault
    story.append(Paragraph("Vault System", styles["Heading2"]))
    story.append(
        Paragraph(
            "On completion, Semptify creates a canonical folder tree in the user's cloud storage "
            "(.Semptify5.0/...). The VaultClient SDK (app/sdk/vault/) handles folder creation, "
            "health checks, and repair across providers. Pre-built specs per role: "
            "TENANT_VAULT, ADVOCATE_VAULT, LEGAL_VAULT, RESEARCH_VAULT.",
            styles["Normal"],
        )
    )

    # Forge
    story.append(Paragraph("Module System (\"The Forge\")", styles["Heading2"]))
    story.append(Paragraph("Not a monolith — it's a lifecycle-pipelined module system:", styles["Normal"]))
    story.append(
        bullet(
            [
                "Modules register in <font face='Courier'>app/core/product_manifest.py</font> (never main.py directly)",
                "Lifecycle stages: dev_only -> preview -> experimental -> beta -> stable",
                "<font face='Courier'>module_resolver.py</font> decides what each user sees based on role + lifecycle",
                "Admins can override at runtime via PostgreSQL-persisted flags",
                "Contracts registered in <font face='Courier'>app/core/module_contracts.py</font> — SSOT for method names, fields, signatures",
            ],
            styles,
        )
    )

    # GUI
    story.append(Paragraph("Two GUI Pillars", styles["Heading2"]))
    story.append(
        bullet(
            [
                "<b>RECORD</b> — Document capture, vault, timeline, journal. Big \"Add Record\" button everywhere.",
                "<b>KNOW</b> — Library of verified facts, rights guides, context engine. Facts only, no opinions.",
            ],
            styles,
        )
    )
    story.append(
        Paragraph(
            "Everything else (advocate, manager, admin, legal) is secondary. The tenant UI is "
            "intentionally minimal: a timeline of everything that's happened + a library of facts.",
            styles["Normal"],
        )
    )

    # Discipline
    story.append(Paragraph("Enforced Engineering Discipline", styles["Heading2"]))
    story.append(
        Paragraph(
            "The repo has hard rules (in AGENTS.md) that AI agents and contributors must follow — "
            "worth noting because they shape the codebase:",
            styles["Normal"],
        )
    )
    story.append(
        bullet(
            [
                "<b>SSOT routing</b> — no hardcoded URLs; <font face='Courier'>navigation.get_stage()</font> everywhere",
                "<b>UTC only</b> — <font face='Courier'>utc_now()</font> from <font face='Courier'>app.core.utc</font>, never <font face='Courier'>datetime.now()</font>",
                "<b>Specific exceptions</b> — no bare <font face='Courier'>except:</font>",
                "<b>No _v2/_fixed files</b> — use a swap protocol for rewrites",
                "<b>Module contracts</b> — every reusable API registers a FunctionGroupContract",
                "<b>Python 3.11.9 locked</b> — no deps requiring 3.12+",
            ],
            styles,
        )
    )

    # Surface
    story.append(Paragraph("Surface Area", styles["Heading2"]))
    story.append(
        bullet(
            [
                "350+ files, 85+ active modules",
                "Health endpoints: /healthz, /readyz, /metrics (Prometheus)",
                "Auto-generated OpenAPI docs at /api/docs and /api/redoc",
                "Security modes: open (dev) vs enforced (prod) via SECURITY_MODE env var",
            ],
            styles,
        )
    )

    # TL;DR
    story.append(Paragraph("TL;DR for Tech People", styles["Heading2"]))
    story.append(
        Paragraph(
            "Semptify is a FastAPI/Postgres tenant-rights app where <b>your cloud storage is your "
            "identity and your vault</b>. No passwords, no server-side user data — OAuth2 into "
            "Google Drive/Dropbox/OneDrive, encrypted token stored back in the user's storage, "
            "HMAC-signed cookies for sessions. Onboarding is a 2-gate state machine. Modules "
            "progress through a lifecycle pipeline (dev_only -> stable) with admin runtime "
            "overrides. Routing is SSOT-enforced. Python 3.11.9 pinned. Deployed on Render "
            "behind Cloudflare.",
            styles["Normal"],
        )
    )

    doc.build(story)
    print(f"PDF written: {OUTPUT}")


if __name__ == "__main__":
    main()
