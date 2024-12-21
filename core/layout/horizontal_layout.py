import logging
from collections import defaultdict

from core.layout.layout_manager import LayoutManager

logger = logging.getLogger(__name__)

class HorizontalLayout(LayoutManager):
    """
    Applies an iterative "barycenter" layout strategy to arrange nodes horizontally.
    Each node's y-position is determined purely from how it connects to other nodes,
    including same-level and cross-level edges.
    """

    def apply(self, diagram, verbose=False) -> None:
        """
        Main entry point: Called by clab2drawio code to apply a horizontal layout.
        :param diagram: CustomDrawioDiagram instance with .nodes
        :param verbose: Whether to log extra info
        """
        logger.debug("Applying iterative barycenter layout (horizontal)...")
        self.diagram = diagram
        self.verbose = verbose

        # Put nodes into bins by their graph_level
        nodes_by_level = defaultdict(list)
        for n in self.diagram.nodes.values():
            nodes_by_level[n.graph_level].append(n)

        # Initialize: give each level a naive top->bottom order
        sorted_levels = sorted(nodes_by_level.keys())
        for level in sorted_levels:
            # sort by name 
            nodes_by_level[level].sort(key=lambda nd: nd.name)
            # assign an initial y from top->bottom
            for i, nd in enumerate(nodes_by_level[level]):
                nd.pos_y = float(100 + i * self.diagram.styles["padding_y"])

        # We'll do N passes. Each pass: left->right, then right->left
        # In each pass, we compute barycenter for each node (based on neighbors)
        # and reorder the level by that barycenter.

        def compute_barycenters_at_level(level_nodes):
            """
            For each node in level_nodes, compute the average y of all its neighbors,
            ignoring their levels (so it includes same-level edges and multi-level edges).
            Store the result in node._bary (temp).
            """
            for nd in level_nodes:
                # gather y positions of neighbors
                neighbor_y_positions = []
                for nbr in nd.get_neighbors():
                    # skip if neighbor has no numeric pos_y
                    try:
                        ny = float(nbr.pos_y)
                    except (TypeError, ValueError):
                        ny = 0.0
                    neighbor_y_positions.append(ny)

                if neighbor_y_positions:
                    nd._bary = sum(neighbor_y_positions) / len(neighbor_y_positions)
                else:
                    nd._bary = 0.0

        def reorder_by_barycenter(level_nodes):
            """
            Sort the list of nodes by the barycenter we just computed.
            Keep it stable so that ties won't cause random reordering.
            """
            level_nodes.sort(key=lambda nd: nd._bary)

        num_passes = 4  # or more, typically 4~6 is enough
        for _iter in range(num_passes):
            # left->right sweep
            for level in sorted_levels:
                level_nodes = nodes_by_level[level]
                compute_barycenters_at_level(level_nodes)
                reorder_by_barycenter(level_nodes)
                # reassign y after sorting
                for i, nd in enumerate(level_nodes):
                    nd.pos_y = float(100 + i * self.diagram.styles["padding_y"])

            # right->left sweep
            for level in reversed(sorted_levels):
                level_nodes = nodes_by_level[level]
                compute_barycenters_at_level(level_nodes)
                reorder_by_barycenter(level_nodes)
                # reassign y
                for i, nd in enumerate(level_nodes):
                    nd.pos_y = float(100 + i * self.diagram.styles["padding_y"])

        # Assign final pos_x from graph_level, keep the pos_y from the last iteration
        for level in sorted_levels:
            for node in nodes_by_level[level]:
                node.pos_x = float(100 + level * self.diagram.styles["padding_x"])

        self._center_align_nodes(nodes_by_level)
        self._adjust_intermediary_nodes(diagram)

        logger.debug("Iterative barycenter layout complete (horizontal).")

    def _center_align_nodes(self, nodes_by_level):
        """
        Shift each level vertically so they are centered
        around a consistent "global_center" or around the previous column.
        """
        sorted_levels = sorted(nodes_by_level.keys())
        # pick a global center, or compute from the leftmost column
        global_center = 300.0

        prev_center = None
        for level in sorted_levels:
            level_nodes = nodes_by_level[level]
            if not level_nodes:
                continue
            # find min & max y
            min_y = min(nd.pos_y for nd in level_nodes)
            max_y = max(nd.pos_y for nd in level_nodes)
            col_center = (min_y + max_y) / 2.0

            if prev_center is None:
                # for the leftmost column, align it to global_center
                offset = global_center - col_center
                for nd in level_nodes:
                    nd.pos_y += offset
                # update col_center after shift
                min_y = min(nd.pos_y for nd in level_nodes)
                max_y = max(nd.pos_y for nd in level_nodes)
                col_center = (min_y + max_y) / 2.0
                prev_center = col_center
            else:
                # for subsequent columns, line them up with the previous column's center
                offset = prev_center - col_center
                for nd in level_nodes:
                    nd.pos_y += offset
                # update col_center
                min_y = min(nd.pos_y for nd in level_nodes)
                max_y = max(nd.pos_y for nd in level_nodes)
                col_center = (min_y + max_y) / 2.0
                prev_center = col_center

    def _adjust_intermediary_nodes(self, diagram, offset=100.0):
        """
        After the main layout, push nodes out of the way if they lie directly on
        a horizontal or vertical line that connects other nodes.

        :param diagram: The CustomDrawioDiagram with .nodes and .get_links_from_nodes()
        :param offset: How many pixels to shift a node if it is detected "on" a link.
        """
        all_links = diagram.get_links_from_nodes()
        nodes = list(diagram.nodes.values())

        # minimal bounding-box approach
        for nd in nodes:
            nd.half_w = float(nd.width) / 2.0 if nd.width else 20.0
            nd.half_h = float(nd.height) / 2.0 if nd.height else 20.0

        for link in all_links:
            A = link.source
            B = link.target

            # If the link is horizontal (A.y ~ B.y):
            if abs(A.pos_y - B.pos_y) < 1e-5:
                left_x = min(A.pos_x, B.pos_x)
                right_x = max(A.pos_x, B.pos_x)
                for N in nodes:
                    if N not in (A, B):
                        # bounding box check
                        Ny_top = N.pos_y - N.half_h
                        Ny_bot = N.pos_y + N.half_h
                        # "in line" if A.y in that range
                        if Ny_top <= A.pos_y <= Ny_bot:
                            Nx_left  = N.pos_x - N.half_w
                            Nx_right = N.pos_x + N.half_w
                            # Overlaps horizontally?
                            if (Nx_left < right_x and Nx_right > left_x):
                                # SHIFT N vertically out of the way
                                N.pos_y -= offset

            # If the link is vertical (A.x ~ B.x):
            elif abs(A.pos_x - B.pos_x) < 1e-5:
                top_y = min(A.pos_y, B.pos_y)
                bot_y = max(A.pos_y, B.pos_y)
                for N in nodes:
                    if N not in (A, B):
                        Nx_left  = N.pos_x - N.half_w
                        Nx_right = N.pos_x + N.half_w
                        # "in line" if A.x in that range
                        if Nx_left <= A.pos_x <= Nx_right:
                            Ny_top = N.pos_y - N.half_h
                            Ny_bot = N.pos_y + N.half_h
                            if (Ny_top < bot_y and Ny_bot > top_y):
                                # SHIFT N horizontally out of the way
                                N.pos_x -= offset
