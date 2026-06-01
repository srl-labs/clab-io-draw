from __future__ import annotations

import itertools
import math
from dataclasses import dataclass

from clab_io_draw.core.layout.horizontal_layout import HorizontalLayout
from clab_io_draw.core.layout.vertical_layout import VerticalLayout


@dataclass(frozen=True)
class LayoutResult:
    name: str
    score: float


class AdaptiveLayout:
    """Apply and score deterministic pure-Python layout candidates."""

    def __init__(self, styles: dict):
        self.styles = styles

    def apply(self, diagram, requested_layout: str, verbose: bool = False) -> LayoutResult:
        layout = (requested_layout or "auto").lower()
        if layout in ("vertical", "horizontal"):
            return self._apply_one(diagram, layout, verbose=verbose)

        candidates = []
        original = self._snapshot(diagram)
        for candidate in ("vertical", "horizontal"):
            self._restore(diagram, original)
            result = self._apply_one(diagram, candidate, verbose=verbose)
            candidates.append((result, self._snapshot(diagram)))

        best_result, best_positions = min(candidates, key=lambda item: item[0].score)
        self._restore(diagram, best_positions)
        diagram.layout = best_result.name
        return best_result

    def _apply_one(self, diagram, layout: str, verbose: bool = False) -> LayoutResult:
        diagram.layout = layout
        if layout == "vertical":
            VerticalLayout().apply(diagram, verbose=verbose)
        else:
            HorizontalLayout().apply(diagram, verbose=verbose)
        self._normalize_component_offsets(diagram, layout)
        return LayoutResult(name=layout, score=self._score(diagram))

    def _snapshot(self, diagram) -> dict[str, tuple[float | None, float | None]]:
        return {name: (node.pos_x, node.pos_y) for name, node in diagram.nodes.items()}

    def _restore(
        self,
        diagram,
        positions: dict[str, tuple[float | None, float | None]],
    ) -> None:
        for name, (x, y) in positions.items():
            if name in diagram.nodes:
                diagram.nodes[name].pos_x = x
                diagram.nodes[name].pos_y = y

    def _normalize_component_offsets(self, diagram, layout: str) -> None:
        """Pack disconnected level components without changing their order."""
        nodes_by_level: dict[int, list[object]] = {}
        for node in diagram.nodes.values():
            nodes_by_level.setdefault(int(node.graph_level or 0), []).append(node)

        primary_padding = float(
            self.styles.get("padding_x" if layout == "horizontal" else "padding_y", 150)
        )
        for level, nodes in nodes_by_level.items():
            for node in nodes:
                if layout == "horizontal":
                    node.pos_x = 100 + level * primary_padding
                else:
                    node.pos_y = 100 + level * primary_padding

    def _score(self, diagram) -> float:
        nodes = list(diagram.nodes.values())
        links = self._unique_links(diagram)
        if not nodes:
            return 0

        crossings = self._count_crossings(links)
        overlap = self._node_overlap(nodes)
        edge_length = sum(self._edge_length(link) for link in links)
        same_rank = sum(
            1
            for link in links
            if (link.source.graph_level is not None)
            and link.source.graph_level == link.target.graph_level
        )
        width, height = self._bounds(nodes)
        aspect_penalty = abs(math.log(max(width, 1) / max(height, 1))) * 80

        return (
            crossings * 1200
            + overlap * 900
            + same_rank * 120
            + edge_length * 0.06
            + aspect_penalty
            + (width + height) * 0.03
        )

    def _unique_links(self, diagram) -> list[object]:
        links = []
        seen = set()
        for node in diagram.nodes.values():
            for link in node.get_all_links():
                connection_id = frozenset(
                    {
                        (link.source.name, link.source_intf),
                        (link.target.name, link.target_intf),
                    }
                )
                if connection_id in seen:
                    continue
                seen.add(connection_id)
                links.append(link)
        return links

    def _edge_length(self, link) -> float:
        sx, sy = self._center(link.source)
        tx, ty = self._center(link.target)
        return math.hypot(tx - sx, ty - sy)

    def _center(self, node) -> tuple[float, float]:
        return (
            float(node.pos_x) + float(node.width) / 2,
            float(node.pos_y) + float(node.height) / 2,
        )

    def _bounds(self, nodes: list[object]) -> tuple[float, float]:
        min_x = min(float(node.pos_x) for node in nodes)
        min_y = min(float(node.pos_y) for node in nodes)
        max_x = max(float(node.pos_x) + float(node.width) for node in nodes)
        max_y = max(float(node.pos_y) + float(node.height) for node in nodes)
        return max_x - min_x, max_y - min_y

    def _node_overlap(self, nodes: list[object]) -> float:
        margin = float(self.styles.get("node_margin", 18))
        overlap = 0.0
        for left, right in itertools.combinations(nodes, 2):
            left_box = self._box(left, margin)
            right_box = self._box(right, margin)
            x_overlap = min(left_box[2], right_box[2]) - max(left_box[0], right_box[0])
            y_overlap = min(left_box[3], right_box[3]) - max(left_box[1], right_box[1])
            if x_overlap > 0 and y_overlap > 0:
                overlap += x_overlap * y_overlap
        return overlap

    def _box(self, node, margin: float) -> tuple[float, float, float, float]:
        return (
            float(node.pos_x) - margin,
            float(node.pos_y) - margin,
            float(node.pos_x) + float(node.width) + margin,
            float(node.pos_y) + float(node.height) + margin,
        )

    def _count_crossings(self, links: list[object]) -> int:
        crossings = 0
        for left, right in itertools.combinations(links, 2):
            if {left.source.name, left.target.name} & {right.source.name, right.target.name}:
                continue
            if self._segments_cross(
                self._center(left.source),
                self._center(left.target),
                self._center(right.source),
                self._center(right.target),
            ):
                crossings += 1
        return crossings

    def _segments_cross(
        self,
        a: tuple[float, float],
        b: tuple[float, float],
        c: tuple[float, float],
        d: tuple[float, float],
    ) -> bool:
        def orient(p, q, r):
            return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

        o1 = orient(a, b, c)
        o2 = orient(a, b, d)
        o3 = orient(c, d, a)
        o4 = orient(c, d, b)
        return (o1 * o2 < 0) and (o3 * o4 < 0)
