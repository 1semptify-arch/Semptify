"""Litigation Intelligence graph engine.

Lightweight in-memory entity-relationship graph for case analysis. Supports
building from entities, adding typed relationships, shortest-path search,
basic graph statistics, and simple PNG/SVG visualization.
"""

import base64
import io
import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from app.core.utc import utc_now


@dataclass
class GraphNode:
    """A node in the litigation intelligence graph."""

    node_id: str
    name: str
    node_type: str = "entity"
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """A typed relationship between two graph nodes."""

    source: str
    target: str
    edge_type: str = "related_to"
    weight: float = 1.0
    attributes: dict[str, Any] = field(default_factory=dict)


class GraphEngine:
    """Entity-relationship graph engine for litigation intelligence."""

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._outgoing: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
        # Undirected adjacency for path search (relationships may be logically
        # bidirectional even though they are stored with a direction).
        self._adj: dict[str, list[tuple[str, str, float]]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def build_from_entities(self, entities: list[dict[str, Any]]) -> None:
        """Add nodes from a list of entity dictionaries."""
        for entity in entities:
            if not isinstance(entity, dict):
                continue
            node_id = str(entity.get("id", entity.get("name", ""))).strip()
            if not node_id:
                continue
            self._nodes[node_id] = GraphNode(
                node_id=node_id,
                name=str(entity.get("name", node_id)).strip(),
                node_type=str(entity.get("type", "entity")).strip().lower(),
                attributes={k: v for k, v in entity.items() if k not in ("id", "name", "type")},
            )

    def add_relationship(
        self,
        source: str,
        target: str,
        edge_type: str = "related_to",
        weight: float = 1.0,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Add a directed, typed relationship between two entities."""
        if source == target:
            return
        attributes = attributes or {}
        edge = GraphEdge(
            source=str(source).strip(),
            target=str(target).strip(),
            edge_type=str(edge_type).strip().lower() or "related_to",
            weight=float(weight) if weight is not None else 1.0,
            attributes=attributes,
        )
        self._edges.append(edge)
        self._outgoing[edge.source].append((edge.target, edge.edge_type, edge.weight))
        self._adj[edge.source].append((edge.target, edge.edge_type, edge.weight))
        self._adj[edge.target].append((edge.source, edge.edge_type, edge.weight))

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def export_graph_data(self) -> dict[str, Any]:
        """Return a serializable representation of the graph."""
        return {
            "nodes": [
                {
                    "id": node.node_id,
                    "name": node.name,
                    "type": node.node_type,
                    "attributes": node.attributes,
                }
                for node in self._nodes.values()
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "type": edge.edge_type,
                    "weight": edge.weight,
                    "attributes": edge.attributes,
                }
                for edge in self._edges
            ],
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "generated_at": utc_now().isoformat(),
        }

    def find_shortest_path(self, source: str, target: str) -> list[str] | None:
        """Return the shortest path of node IDs between source and target (BFS)."""
        source = str(source).strip()
        target = str(target).strip()
        if source not in self._nodes or target not in self._nodes:
            return None
        if source == target:
            return [source]

        visited = {source}
        queue: deque[tuple[str, list[str]]] = deque([(source, [source])])
        while queue:
            current, path = queue.popleft()
            for neighbor, _edge_type, _weight in self._adj.get(current, []):
                if neighbor in visited:
                    continue
                new_path = path + [neighbor]
                if neighbor == target:
                    return new_path
                visited.add(neighbor)
                queue.append((neighbor, new_path))
        return None

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    def analyze_graph(self) -> dict[str, Any]:
        """Compute basic graph statistics."""
        node_count = len(self._nodes)
        edge_count = len(self._edges)
        density = 0.0
        if node_count > 1:
            # Simple graph density for directed graph without self-loops.
            density = edge_count / (node_count * (node_count - 1))

        degree: dict[str, int] = defaultdict(int)
        for edge in self._edges:
            degree[edge.source] += 1
            degree[edge.target] += 1

        # Connected components (treat graph as undirected)
        visited: set[str] = set()
        components = 0
        for node_id in self._nodes:
            if node_id in visited:
                continue
            components += 1
            queue = deque([node_id])
            visited.add(node_id)
            while queue:
                current = queue.popleft()
                for neighbor, _edge_type, _weight in self._adj.get(current, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

        top_nodes = sorted(degree.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "density": round(density, 4),
            "connected_components": components,
            "top_degree_nodes": [
                {"id": nid, "degree": deg, "name": self._nodes.get(nid, GraphNode(nid, nid)).name}
                for nid, deg in top_nodes
            ],
            "status": "operational",
            "generated_at": utc_now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Visualization
    # ------------------------------------------------------------------
    def generate_visualization(self, output_format: str = "png") -> dict[str, Any]:
        """Generate a simple graph visualization.

        Supports ``png`` (base64-encoded Pillow image) and ``svg`` (XML string).
        """
        fmt = str(output_format).lower().strip()
        if fmt not in ("png", "svg"):
            fmt = "png"

        positions = self._compute_positions()
        if not positions:
            return {"format": fmt, "data": None, "node_count": 0, "edge_count": 0}

        if fmt == "svg":
            svg = self._render_svg(positions)
            return {
                "format": "svg",
                "data": svg,
                "content_type": "image/svg+xml",
                "node_count": len(self._nodes),
                "edge_count": len(self._edges),
                "generated_at": utc_now().isoformat(),
            }

        # PNG fallback
        try:
            png_b64 = self._render_png(positions)
            return {
                "format": "png",
                "data": png_b64,
                "content_type": "image/png",
                "encoding": "base64",
                "node_count": len(self._nodes),
                "edge_count": len(self._edges),
                "generated_at": utc_now().isoformat(),
            }
        except Exception as exc:
            # Pillow may be unavailable in some environments; degrade to SVG.
            svg = self._render_svg(positions)
            return {
                "format": "svg",
                "data": svg,
                "content_type": "image/svg+xml",
                "fallback_reason": str(exc),
                "node_count": len(self._nodes),
                "edge_count": len(self._edges),
                "generated_at": utc_now().isoformat(),
            }

    def _compute_positions(self) -> dict[str, tuple[float, float]]:
        """Assign a deterministic circular layout to nodes."""
        if not self._nodes:
            return {}
        count = len(self._nodes)
        radius = max(120.0, count * 25.0)
        center = (radius + 40, radius + 40)
        positions: dict[str, tuple[float, float]] = {}
        for i, node_id in enumerate(sorted(self._nodes.keys())):
            angle = 2 * math.pi * i / count - math.pi / 2
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            positions[node_id] = (x, y)
        return positions

    def _render_svg(self, positions: dict[str, tuple[float, float]]) -> str:
        """Render the graph as a simple SVG."""
        width = int(max(x for x, y in positions.values()) * 2 + 40) if positions else 400
        height = int(max(y for x, y in positions.values()) * 2 + 40) if positions else 400
        svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            f'<rect width="{width}" height="{height}" fill="#f8fafc"/>',
        ]
        # Edges first so nodes draw on top
        for edge in self._edges:
            src = positions.get(edge.source)
            tgt = positions.get(edge.target)
            if not src or not tgt:
                continue
            svg.append(
                f'<line x1="{src[0]:.1f}" y1="{src[1]:.1f}" x2="{tgt[0]:.1f}" y2="{tgt[1]:.1f}" '
                f'stroke="#94a3b8" stroke-width="2"/>'
            )
        for node_id, (x, y) in positions.items():
            node = self._nodes[node_id]
            color = self._node_color(node.node_type)
            svg.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="{color}" stroke="#334155" stroke-width="2"/>'
            )
            label = self._escape_xml(node.name or node_id)[:30]
            svg.append(
                f'<text x="{x + 16:.1f}" y="{y + 4:.1f}" font-size="12" fill="#334155">{label}</text>'
            )
        svg.append("</svg>")
        return "\n".join(svg)

    def _render_png(self, positions: dict[str, tuple[float, float]]) -> str | None:
        """Render the graph as a PNG and return a base64 data URL."""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            return None

        width = int(max(x for x, y in positions.values()) * 2 + 40)
        height = int(max(y for x, y in positions.values()) * 2 + 40)
        image = Image.new("RGB", (width, height), "#f8fafc")
        draw = ImageDraw.Draw(image)

        for edge in self._edges:
            src = positions.get(edge.source)
            tgt = positions.get(edge.target)
            if not src or not tgt:
                continue
            draw.line([(src[0], src[1]), (tgt[0], tgt[1])], fill="#94a3b8", width=2)

        for node_id, (x, y) in positions.items():
            node = self._nodes[node_id]
            color = self._node_color(node.node_type)
            draw.ellipse([(x - 12, y - 12), (x + 12, y + 12)], fill=color, outline="#334155", width=2)
            draw.text((x + 16, y - 6), (node.name or node_id)[:30], fill="#334155")

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    @staticmethod
    def _node_color(node_type: str) -> str:
        """Return a palette color for a node type."""
        palette = {
            "person": "#3b82f6",
            "organization": "#10b981",
            "case": "#f59e0b",
            "property": "#8b5cf6",
            "document": "#64748b",
        }
        return palette.get(node_type.lower(), "#ef4444")

    @staticmethod
    def _escape_xml(text: str) -> str:
        """Escape XML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )


def create_graph_engine() -> GraphEngine:
    """Factory function for the graph engine."""
    return GraphEngine()
