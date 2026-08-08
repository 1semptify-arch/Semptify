"""Oversight packet generation workflows for agency complaints."""

from typing import Any

from app.core.utc import utc_now


def _build_packet_base(agency: str, tenant_data: dict[str, Any], patterns: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a common packet structure for any oversight agency."""
    return {
        "agency": agency,
        "generated_at": utc_now().isoformat(),
        "tenant": {
            "name": tenant_data.get("name"),
            "address": tenant_data.get("address"),
            "contact": tenant_data.get("contact"),
        },
        "issues": [p.get("description", str(p)) for p in patterns],
        "patterns": patterns,
    }


def build_ag_packet(tenant_data: dict[str, Any], patterns: list[dict[str, Any]]) -> dict[str, Any]:
    """Build an Attorney General consumer protection complaint packet."""
    packet = _build_packet_base("Attorney General", tenant_data, patterns)
    packet["subject"] = "Tenant complaint regarding landlord practices"
    packet["requested_relief"] = "Investigation and enforcement of consumer protection laws"
    return packet


def build_hud_packet(tenant_data: dict[str, Any], patterns: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a HUD fair housing complaint packet."""
    packet = _build_packet_base("HUD", tenant_data, patterns)
    packet["subject"] = "Fair housing complaint"
    packet["requested_relief"] = "HUD investigation of discriminatory housing practices"
    packet["protected_class_basis"] = [p.get("basis") for p in patterns if p.get("basis")]
    return packet


def build_mdhr_packet(tenant_data: dict[str, Any], patterns: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a Minnesota Department of Human Rights complaint packet."""
    packet = _build_packet_base("MDHR", tenant_data, patterns)
    packet["subject"] = "Minnesota human rights complaint"
    packet["requested_relief"] = "Investigation of civil rights violations in housing"
    return packet


def build_cfpb_packet(tenant_data: dict[str, Any], patterns: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a CFPB consumer complaint packet."""
    packet = _build_packet_base("CFPB", tenant_data, patterns)
    packet["subject"] = "Consumer complaint about financial products or services"
    packet["requested_relief"] = "Review of lender, debt collector, or credit reporting practices"
    return packet


def export_packet(packet: dict[str, Any], format: str = "markdown") -> str:
    """Export an oversight packet as plain text or markdown."""
    lines = [
        f"# {packet.get('agency', 'Oversight')} Packet",
        "",
        f"**Subject:** {packet.get('subject', '')}",
        f"**Generated:** {packet.get('generated_at', '')}",
        "",
        "## Tenant Information",
        f"- Name: {packet.get('tenant', {}).get('name', '')}",
        f"- Address: {packet.get('tenant', {}).get('address', '')}",
        f"- Contact: {packet.get('tenant', {}).get('contact', '')}",
        "",
        "## Issues",
    ]
    for issue in packet.get("issues", []):
        lines.append(f"- {issue}")
    lines.append("")
    lines.append("## Requested Relief")
    lines.append(packet.get("requested_relief", ""))
    return "\n".join(lines)
