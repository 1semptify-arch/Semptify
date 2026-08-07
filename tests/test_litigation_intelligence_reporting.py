"""Tests for the litigation intelligence reporting and PDF export."""

import base64

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.cookie_auth import sign_user_id
from app.main import app
from app.modules.litigation_intelligence.reporting_layer import ReportingLayer, create_reporting_layer


def _client() -> AsyncClient:
    """Return an async test client with a valid signed user cookie."""
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    client.cookies.set("semptify_uid", sign_user_id("GU7x9kM2pQ"))
    return client


@pytest.mark.anyio
async def test_generate_case_summary_report_and_export_pdf():
    """Generate a case summary report and export it as a base64 PDF."""
    async with _client() as client:
        gen_resp = await client.post(
            "/api/litigation-intelligence/report/generate",
            json={"report_type": "case_summary", "time_period": "30_days"},
        )
        assert gen_resp.status_code == 200
        gen_data = gen_resp.json()
        assert gen_data["success"] is True
        report_id = gen_data["report"]["report_id"]

        export_resp = await client.get(
            f"/api/litigation-intelligence/report/{report_id}/export?format=pdf"
        )
        assert export_resp.status_code == 200
        export_data = export_resp.json()
        assert export_data["success"] is True
        assert export_data["format"] == "pdf"
        assert export_data["export_data"].startswith("data:application/pdf;base64,")

        # Verify base64 payload decodes to a valid PDF header.
        b64_payload = export_data["export_data"].split(",")[1]
        pdf_bytes = base64.b64decode(b64_payload)
        assert pdf_bytes.startswith(b"%PDF")


@pytest.mark.anyio
async def test_generate_case_summary_report_returns_zero_metrics_without_storage():
    """Case summary report uses real (zero) metrics when no LIS storage is available."""
    async with _client() as client:
        response = await client.post(
            "/api/litigation-intelligence/report/generate",
            json={"report_type": "case_summary", "time_period": "30_days"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    metric_names = {m["name"] for m in data["report"]["metrics"]}
    assert metric_names == {"total_cases", "active_cases", "success_rate", "avg_case_duration"}


@pytest.mark.anyio
async def test_reporting_layer_pdf_export():
    """ReportingLayer._export_to_pdf returns a base64 PDF data URL."""
    reporting = ReportingLayer()
    report = await reporting.generate_case_summary_report("30_days")
    pdf_data = reporting.export_report_data(report.report_id, "pdf")
    assert pdf_data.startswith("data:application/pdf;base64,")
    b64 = pdf_data.split(",")[1]
    assert base64.b64decode(b64).startswith(b"%PDF")


@pytest.mark.anyio
async def test_create_reporting_layer_accepts_storage_layer():
    """The reporting-layer factory accepts a storage layer reference."""
    from app.modules.litigation_intelligence.storage_layer import create_storage_layer

    storage = create_storage_layer("postgresql://unused")
    reporting = create_reporting_layer(storage)
    assert reporting.storage_layer is storage
