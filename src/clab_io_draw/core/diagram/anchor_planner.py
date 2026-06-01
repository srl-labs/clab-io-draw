from dataclasses import dataclass

InterfaceSide = str


@dataclass
class EndpointAssignment:
    link: object
    side: InterfaceSide
    sort_key: float
    label_radius: float


def compact_interface_name(intf_name: str, styles: dict | None = None) -> str:
    """Return a readable, compact interface label without losing the endpoint."""
    if intf_name is None:
        return ""

    label = str(intf_name).strip()
    if not label:
        return ""

    styles = styles or {}
    if not styles.get("compact_interface_names", True):
        return label

    lower = label.lower()
    if lower.startswith("ethernet-"):
        label = "e" + label[9:]
    elif lower.startswith("ethernet"):
        label = "e" + label[8:]

    max_chars = max(4, int(styles.get("label_max_chars", 14)))
    if len(label) > max_chars:
        return label[: max_chars - 3] + "..."
    return label


def label_dimensions(label: str, styles: dict) -> tuple[float, float]:
    font_size = float(styles.get("label_font_size", 9))
    min_width = float(styles.get("label_min_width", styles.get("label_width", 20)))
    max_width = float(styles.get("label_max_width", 96))
    padding_x = float(styles.get("label_padding_x", 6))
    height = float(styles.get("label_height", 12))
    width = len(label) * font_size * 0.58 + padding_x * 2
    return min(max(min_width, width), max_width), height


class AnchorPlanner:
    """
    Assign deterministic node-edge anchors for both visible ports and label bubbles.

    The side selection mirrors clab-ui's SVG export: top/bottom are preferred, with
    left/right used only for near-horizontal links.
    """

    horizontal_slope_threshold = 0.25

    def __init__(self, styles: dict):
        self.styles = styles

    def assign(self, diagram) -> None:
        self._assign_parallel_offsets(diagram)

        buckets_by_node = {
            node.name: {"top": [], "right": [], "bottom": [], "left": []}
            for node in diagram.nodes.values()
        }

        for node in diagram.nodes.values():
            for link in node.get_all_links():
                side = self._classify_side(link)
                vector = self._vector(link)
                label = compact_interface_name(link.source_intf, self.styles)
                radius = self._label_radius(label)
                buckets_by_node[node.name][side].append(
                    EndpointAssignment(
                        link=link,
                        side=side,
                        sort_key=self._sort_key(side, vector),
                        label_radius=radius,
                    )
                )

        for node in diagram.nodes.values():
            for side, assignments in buckets_by_node[node.name].items():
                assignments.sort(
                    key=lambda item: (
                        item.sort_key,
                        item.link.source_intf or "",
                        item.link.target.name,
                        item.link.target_intf or "",
                    )
                )
                for index, assignment in enumerate(assignments):
                    self._place_assignment(
                        assignment,
                        side=side,
                        index=index,
                        total=len(assignments),
                    )

    def _assign_parallel_offsets(self, diagram) -> None:
        groups: dict[tuple[str, str], list[object]] = {}
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
                key = tuple(sorted((link.source.name, link.target.name)))
                groups.setdefault(key, []).append(link)

        step = float(self.styles.get("parallel_edge_spacing", 28))
        for links in groups.values():
            links.sort(
                key=lambda link: (
                    link.source.name,
                    link.source_intf or "",
                    link.target.name,
                    link.target_intf or "",
                )
            )
            total = len(links)
            for index, link in enumerate(links):
                offset = (index - (total - 1) / 2) * step
                link.parallel_offset = offset
                target_link = diagram.get_target_link(link)
                if target_link is not None:
                    target_link.parallel_offset = offset

    def _classify_side(self, link) -> InterfaceSide:
        dx, dy = self._vector(link)
        abs_dx = abs(dx)
        abs_dy = abs(dy)

        if abs_dx > 0.001 and abs_dy <= abs_dx * self.horizontal_slope_threshold:
            return "right" if dx >= 0 else "left"
        return "bottom" if dy >= 0 else "top"

    def _vector(self, link) -> tuple[float, float]:
        source_center = self._center(link.source)
        target_center = self._center(link.target)
        return target_center[0] - source_center[0], target_center[1] - source_center[1]

    def _sort_key(self, side: InterfaceSide, vector: tuple[float, float]) -> float:
        dx, dy = vector
        return dx if side in ("top", "bottom") else dy

    def _center(self, node) -> tuple[float, float]:
        return (
            float(node.pos_x) + float(node.width) / 2,
            float(node.pos_y) + float(node.height) / 2,
        )

    def _label_radius(self, label: str) -> float:
        width, height = label_dimensions(label, self.styles)
        return max(width, height) / 2

    def _place_assignment(
        self,
        assignment: EndpointAssignment,
        side: InterfaceSide,
        index: int,
        total: int,
    ) -> None:
        link = assignment.link
        node = link.source
        slot = (index + 1) / (total + 1)

        node_x = float(node.pos_x)
        node_y = float(node.pos_y)
        node_w = float(node.width)
        node_h = float(node.height)
        port_w = float(self.styles.get("port_width", 10))
        port_h = float(self.styles.get("port_height", 10))
        gap = float(self.styles.get("label_anchor_gap", 2))
        label_out = max(port_w, port_h, assignment.label_radius * 2) / 2 + gap
        port_gap = float(self.styles.get("port_anchor_gap", 0))
        port_out = max(port_w, port_h) / 2 + port_gap

        if side == "top":
            edge_x = node_x + node_w * slot
            edge_y = node_y
            label_x = edge_x
            label_y = node_y - label_out
            port_x = edge_x
            port_y = node_y - port_out
        elif side == "right":
            edge_x = node_x + node_w
            edge_y = node_y + node_h * slot
            label_x = node_x + node_w + label_out
            label_y = edge_y
            port_x = node_x + node_w + port_out
            port_y = edge_y
        elif side == "bottom":
            edge_x = node_x + node_w * slot
            edge_y = node_y + node_h
            label_x = edge_x
            label_y = node_y + node_h + label_out
            port_x = edge_x
            port_y = node_y + node_h + port_out
        else:
            edge_x = node_x
            edge_y = node_y + node_h * slot
            label_x = node_x - label_out
            label_y = edge_y
            port_x = node_x - port_out
            port_y = edge_y

        link.anchor_side = side
        link.edge_exit = (
            min(1.0, max(0.0, (edge_x - node_x) / node_w)),
            min(1.0, max(0.0, (edge_y - node_y) / node_h)),
        )
        link.label_center = (label_x, label_y)
        link.port_pos = (port_x - port_w / 2, port_y - port_h / 2)
