"""Part 3B guardrail: verify context_fact consumer filter and gatherer attestation."""

from pathlib import Path

try:
    from tools.checks.common import CheckResult  # type: ignore
except Exception:
    # Fallback for when the guardrail engine loads this directly.
    from dataclasses import dataclass

    @dataclass
    class CheckResult:
        name: str
        passed: bool
        summary: str
        details: str = ""


def run(repo_root: Path) -> CheckResult:
    cache_path = repo_root / "app" / "modules" / "context_engine" / "cache.py"
    gatherer_path = repo_root / "app" / "modules" / "context_engine" / "gatherer.py"
    model_path = repo_root / "app" / "modules" / "context_engine" / "models.py"

    failures = []

    if not model_path.exists():
        failures.append("ContextFact model not found")
    else:
        model_text = model_path.read_text(encoding="utf-8")
        required_fields = [
            "fact_id",
            "resolution_status",
            "ai_generated",
            "fabrication_check",
            "source_authority",
            "last_verified_date",
        ]
        for field in required_fields:
            if field not in model_text:
                failures.append(f"ContextFact model missing field: {field}")

    if not cache_path.exists():
        failures.append("context_engine/cache.py not found")
    else:
        cache_text = cache_path.read_text(encoding="utf-8")
        for token in (
            "resolution_status == \"Resolved\"",
            "ai_generated.is_(False)",
            "fabrication_check.is_(True)",
        ):
            if token not in cache_text:
                failures.append(f"get_facts() missing Part 3B consumer filter: {token}")

    if not gatherer_path.exists():
        failures.append("context_engine/gatherer.py not found")
    else:
        gatherer_text = gatherer_path.read_text(encoding="utf-8")
        law_block = "gather_law_library_facts"
        if law_block not in gatherer_text:
            failures.append("gather_law_library_facts not found")
        else:
            for token in (
                'ai_generated=False',
                'resolution_status="Resolved"',
                'fabrication_check=True',
            ):
                if token not in gatherer_text:
                    failures.append(f"Law Library gatherer missing Part 3B attestation: {token}")

    if failures:
        return CheckResult(
            name="context_fact_check",
            passed=False,
            summary="Part 3B context_fact guardrail failed",
            details="\n".join(failures),
        )

    return CheckResult(
        name="context_fact_check",
        passed=True,
        summary="Part 3B context_fact schema, consumer filter, and gatherer attestation verified",
    )
