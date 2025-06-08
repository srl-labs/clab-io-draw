import logging
from collections import defaultdict

from clab_io_draw.core.layout.layout_manager import LayoutManager

logger = logging.getLogger(__name__)


class HorizontalLayout(LayoutManager):
    def apply(self, diagram, verbose=False) -> None:
        logger.debug("Applying iterative barycenter layout (horizontal)...")
        self.diagram = diagram
        self.verbose = verbose

        nodes_by_level = defaultdict(list)
        for n in self.diagram.nodes.values():
            nodes_by_level[n.graph_level].append(n)

        sorted_levels = sorted(nodes_by_level.keys())

        # Initial positioning
        for level in sorted_levels:
            nodes_by_level[level].sort(key=lambda nd: nd.name)
            for i, nd in enumerate(nodes_by_level[level]):
                nd.pos_y = float(100 + i * self.diagram.styles["padding_y"])

        def get_connected_pairs(level_nodes):
            """Get pairs of nodes in the same level that are directly connected."""
            pairs = []
            for i, node1 in enumerate(level_nodes):
                for node2 in level_nodes[i + 1 :]:
                    if node2 in node1.get_neighbors():
                        pairs.append((node1, node2))
            return pairs

        def is_position_between_connected_nodes(pos, node, level_nodes):
            """Check if a position would place the node between connected nodes."""
            connected_pairs = get_connected_pairs(level_nodes)
            for n1, n2 in connected_pairs:
                if n1 != node and n2 != node:
                    min_y, max_y = min(n1.pos_y, n2.pos_y), max(n1.pos_y, n2.pos_y)
                    if min_y < pos < max_y:
                        return True
            return False

        def find_valid_positions(node, level_nodes, barycenter):
            """Find all valid positions, prioritizing those that don't create crossings."""
            positions = []

            connected_nodes = set(node.get_neighbors())
            same_level_connected = [n for n in level_nodes if n in connected_nodes]

            existing_positions = sorted([n.pos_y for n in level_nodes if n != node])
            if not existing_positions:
                return [barycenter]

            # Consider positions before first node
            positions.append(existing_positions[0] - self.diagram.styles["padding_y"])

            # Consider positions after each node
            for pos in existing_positions:
                positions.append(pos + self.diagram.styles["padding_y"])

            # Add positions next to connected nodes
            if same_level_connected:
                for connected_node in same_level_connected:
                    positions.append(
                        connected_node.pos_y + self.diagram.styles["padding_y"]
                    )
                    positions.append(
                        connected_node.pos_y - self.diagram.styles["padding_y"]
                    )

            # Remove invalid positions
            min_spacing = self.diagram.styles["padding_y"] * 0.9
            valid_positions = []
            for pos in sorted(set(positions)):
                if all(
                    abs(pos - other_pos) >= min_spacing
                    for other_pos in existing_positions
                ):
                    valid_positions.append(pos)

            # Sort positions by priority
            return sorted(
                valid_positions,
                key=lambda p: (
                    is_position_between_connected_nodes(p, node, level_nodes),
                    abs(p - barycenter),
                ),
            )

        def compute_barycenter(node):
            """Compute weighted barycenter of all connected nodes."""
            positions = []
            weights = []

            for nbr in node.get_neighbors():
                try:
                    pos = float(nbr.pos_y)
                    # Give higher weight to same-level connections
                    weight = 2.0 if nbr.graph_level == node.graph_level else 1.0
                    positions.append(pos)
                    weights.append(weight)
                except (TypeError, ValueError):
                    continue

            if positions:
                return sum(p * w for p, w in zip(positions, weights)) / sum(weights)
            return node.pos_y

        def reposition_level(level_nodes):
            """Position nodes in a level while avoiding problematic placements."""
            # Sort nodes by number of connections (more connected nodes first)
            nodes_to_position = sorted(
                level_nodes, key=lambda n: len(list(n.get_neighbors())), reverse=True
            )

            positioned = []
            for node in nodes_to_position:
                barycenter = compute_barycenter(node)
                valid_positions = find_valid_positions(node, positioned, barycenter)

                if valid_positions:
                    node.pos_y = valid_positions[0]
                else:
                    if positioned:
                        node.pos_y = (
                            max(n.pos_y for n in positioned)
                            + self.diagram.styles["padding_y"]
                        )
                    else:
                        node.pos_y = barycenter

                positioned.append(node)

        # Main layout iterations
        num_passes = 4
        for _iter in range(num_passes):
            for level in sorted_levels:
                reposition_level(nodes_by_level[level])

            for level in reversed(sorted_levels):
                reposition_level(nodes_by_level[level])

        # Assign X positions
        for level in sorted_levels:
            for node in nodes_by_level[level]:
                node.pos_x = float(100 + level * self.diagram.styles["padding_x"])

        self._center_align_nodes(nodes_by_level)
        self._adjust_intermediary_nodes(diagram)

        logger.debug("Iterative barycenter layout complete (horizontal).")

    def _center_align_nodes(self, nodes_by_level):
        sorted_levels = sorted(nodes_by_level.keys())
        global_center = 300.0

        prev_center = None
        for level in sorted_levels:
            level_nodes = nodes_by_level[level]
            if not level_nodes:
                continue

            min_y = min(nd.pos_y for nd in level_nodes)
            max_y = max(nd.pos_y for nd in level_nodes)
            col_center = (min_y + max_y) / 2.0

            if prev_center is None:
                offset = global_center - col_center
                for nd in level_nodes:
                    nd.pos_y += offset
                min_y = min(nd.pos_y for nd in level_nodes)
                max_y = max(nd.pos_y for nd in level_nodes)
                col_center = (min_y + max_y) / 2.0
                prev_center = col_center
            else:
                offset = prev_center - col_center
                for nd in level_nodes:
                    nd.pos_y += offset
                min_y = min(nd.pos_y for nd in level_nodes)
                max_y = max(nd.pos_y for nd in level_nodes)
                col_center = (min_y + max_y) / 2.0
                prev_center = col_center

    def _adjust_intermediary_nodes(self, diagram, offset=100.0):
        all_links = diagram.get_links_from_nodes()
        nodes = list(diagram.nodes.values())

        for nd in nodes:
            nd.half_w = float(nd.width) / 2.0 if nd.width else 20.0
            nd.half_h = float(nd.height) / 2.0 if nd.height else 20.0

        for link in all_links:
            A = link.source
            B = link.target

            if abs(A.pos_y - B.pos_y) < 1e-5:
                left_x = min(A.pos_x, B.pos_x)
                right_x = max(A.pos_x, B.pos_x)
                for N in nodes:
                    if N not in (A, B):
                        Ny_top = N.pos_y - N.half_h
                        Ny_bot = N.pos_y + N.half_h
                        if Ny_top <= A.pos_y <= Ny_bot:
                            Nx_left = N.pos_x - N.half_w
                            Nx_right = N.pos_x + N.half_w
                            if Nx_left < right_x and Nx_right > left_x:
                                N.pos_y -= offset

            elif abs(A.pos_x - B.pos_x) < 1e-5:
                top_y = min(A.pos_y, B.pos_y)
                bot_y = max(A.pos_y, B.pos_y)
                for N in nodes:
                    if N not in (A, B):
                        Nx_left = N.pos_x - N.half_w
                        Nx_right = N.pos_x + N.half_w
                        if Nx_left <= A.pos_x <= Nx_right:
                            Ny_top = N.pos_y - N.half_h
                            Ny_bot = N.pos_y + N.half_h
                            if Ny_top < bot_y and Ny_bot > top_y:
                                N.pos_x -= offset
