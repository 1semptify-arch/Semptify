import pytest
from app.core.role_validation import RoleValidator, RoleVerification, VerificationStatus
from app.core.user_context import UserRole
from app.services.eviction.seed_court_data import RealCourtDataImporter


@pytest.mark.parametrize(
    "bar_number, expected_status",
    [
        ("123456", VerificationStatus.VERIFIED),
        ("654321", VerificationStatus.VERIFIED),
        ("000999", VerificationStatus.PENDING),
    ],
)
def test_verify_bar_number_expected_status(bar_number, expected_status):
    validator = RoleValidator()
    result = validator.validate_for_role(
        user_id="user123",
        requested_role=UserRole.LEGAL,
        bar_number=bar_number,
        email="test@example.com",
    )

    assert isinstance(result, RoleVerification)
    assert result.role == UserRole.LEGAL
    assert result.status == expected_status


@pytest.mark.parametrize(
    "hud_cert, expected_status",
    [
        ("HUD-2025001", VerificationStatus.VERIFIED),
        ("HUD-2025002", VerificationStatus.VERIFIED),
        ("HUD-UNKNOWN", VerificationStatus.PENDING),
    ],
)
def test_verify_hud_cert_expected_status(hud_cert, expected_status):
    validator = RoleValidator()
    result = validator.validate_for_role(
        user_id="user456",
        requested_role=UserRole.ADVOCATE,
        hud_cert_number=hud_cert,
    )

    assert isinstance(result, RoleVerification)
    assert result.role == UserRole.ADVOCATE
    assert result.status == expected_status


def test_import_from_csv(tmp_path):
    csv_file = tmp_path / "seed_cases.csv"
    with csv_file.open("w", encoding="utf-8") as f:
        f.write("case_number,outcome,hearing_date,defenses_used,judge_name\n")
        f.write("C-0001,win,2026-01-10,IMPROPER_NOTICE,Judge A\n")
        f.write("C-0002,loss,2026-01-15,HABITABILITY,Judge B\n")

    result = RealCourtDataImporter.import_from_csv(str(csv_file))

    # handle async signature if added in future
    if hasattr(result, "__await__"):
        import asyncio
        result = asyncio.run(result)

    assert result["source"] == "CSV"
    assert result["cases_imported"] == 2
    assert len(result["imported_cases"]) == 2
    assert result["warnings"] == []

