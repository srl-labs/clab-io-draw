import logging
from collections import defaultdict

from core.layout.layout_manager import LayoutManager

logger = logging.getLogger(__name__)

class VerticalLayout(LayoutManager):
    """
    Applies an iterative "barycenter" layout strategy to arrange nodes vertically.
    Each node's x-position is determined purely from how it connects to other nodes,
    including same-level and cross-level edges.
    """

    def apply(self, diagram, verbose=False) -> None:
        """
        Main entry point: Called by clab2drawio code to apply a vertical layout.
        :param diagram: CustomDrawioDiagram instance with .nodes
        :param verbose: Whether to log extra info
        """
        logger.debug("Applying iterative barycenter layout (vertical)...")
        self.diagram = diagram
        self.verbose = verbose

        # Put nodes into bins by their graph_level
        nodes_by_level = defaultdict(list)
        for n in self.diagram.nodes.values():
            nodes_by_level[n.graph_level].append(n)

        # Initialize: give each level a naive left->right order
        sorted_levels = sorted(nodes_by_level.keys())
        for level in sorted_levels:
            # sort by name
            nodes_by_level[level].sort(key=lambda nd: nd.name)
            # assign an initial x from left->right
            for i, nd in enumerate(nodes_by_level[level]):
                nd.pos_x = float(100 + i * self.diagram.styles["padding_x"])  # or 0.0 + i*...
        
        def compute_barycenters_at_level(level_nodes):
            """
            For each node in level_nodes, compute the average x of all its neighbors,
            ignoring their levels (so it includes same-level edges and multi-level edges).
            Store the result in node._bary (temp).
            """
            for nd in level_nodes:
                # gather x positions of neighbors
                neighbor_x_positions = []
                for nbr in nd.get_neighbors():
                    # skip if neighbor has no numeric pos_x
                    try:
                        nx = float(nbr.pos_x)
                    except (TypeError, ValueError):
                        nx = 0.0
                    neighbor_x_positions.append(nx)

                if neighbor_x_positions:
                    nd._bary = sum(neighbor_x_positions) / len(neighbor_x_positions)
                else:
                    nd._bary = 0.0

        def reorder_by_barycenter(level_nodes):
            """
            Sort the list of nodes by the barycenter we just computed.
            """
            level_nodes.sort(key=lambda nd: nd._bary)

        num_passes = 4  # or more, typically 4~6 is enough
        for _iter in range(num_passes):
            # top->down sweep
            for level in sorted_levels:
                level_nodes = nodes_by_level[level]
                compute_barycenters_at_level(level_nodes)
                reorder_by_barycenter(level_nodes)
                # reassign x after sorting
                for i, nd in enumerate(level_nodes):
                    nd.pos_x = float(100 + i * self.diagram.styles["padding_x"])

            # bottom->up sweep
            for level in reversed(sorted_levels):
                level_nodes = nodes_by_level[level]
                compute_barycenters_at_level(level_nodes)
                reorder_by_barycenter(level_nodes)
                # reassign x
                for i, nd in enumerate(level_nodes):
                    nd.pos_x = float(100 + i * self.diagram.styles["padding_x"])

        # Assign final pos_y from graph_level, keep the pos_x from the last iteration
        for level in sorted_levels:
            for node in nodes_by_level[level]:
                node.pos_y = float(100 + level * self.diagram.styles["padding_y"])

        self._center_align_nodes(nodes_by_level)
        self._adjust_intermediary_nodes(diagram)

        logger.debug("Iterative barycenter layout complete.")

    def _center_align_nodes(self, nodes_by_level):
        """
        Shift each level horizontally so they are centered
        around a consistent "global_center" or around the row above.
        """
        sorted_levels = sorted(nodes_by_level.keys())
        # pick a global center, or compute from the top row
        global_center = 400.0

        prev_center = None
        for level in sorted_levels:
            level_nodes = nodes_by_level[level]
            if not level_nodes:
                continue
            # find min & max x
            min_x = min(nd.pos_x for nd in level_nodes)
            max_x = max(nd.pos_x for nd in level_nodes)
            row_center = (min_x + max_x) / 2.0

            if prev_center is None:
                # for the top row, align it to global_center
                offset = global_center - row_center
                for nd in level_nodes:
                    nd.pos_x += offset
                # update row_center after shift
                min_x = min(nd.pos_x for nd in level_nodes)
                max_x = max(nd.pos_x for nd in level_nodes)
                row_center = (min_x + max_x) / 2.0
                prev_center = row_center
            else:
                # for subsequent rows, line them up with the previous row's center
                offset = prev_center - row_center
                for nd in level_nodes:
                    nd.pos_x += offset
                # update row_center
                min_x = min(nd.pos_x for nd in level_nodes)
                max_x = max(nd.pos_x for nd in level_nodes)
                row_center = (min_x + max_x) / 2.0
                prev_center = row_center

    def _adjust_intermediary_nodes(self, diagram, offset=100.0):
        """
        After the main layout, push nodes out of the way if they lie directly on
        a vertical or horizontal line that connects other nodes.

        :param diagram: The CustomDrawioDiagram with .nodes and .get_links_from_nodes()
        :param offset: How many pixels to shift a node if it is detected "on" a link.
        """
        all_links = diagram.get_links_from_nodes()  # or however you get your link list
        nodes = list(diagram.nodes.values())

        for nd in nodes:
            nd.half_w = float(nd.width) / 2.0 if nd.width else 20.0
            nd.half_h = float(nd.height) / 2.0 if nd.height else 20.0

        for link in all_links:
            A = link.source
            B = link.target

            # If the link is vertical (A.x ~ B.x):
            if abs(A.pos_x - B.pos_x) < 1e-5:
                # figure out top/bot
                top_y = min(A.pos_y, B.pos_y)
                bot_y = max(A.pos_y, B.pos_y)

                # see if any other node is "in line"
                for N in nodes:
                    if N not in (A, B):
                        # Check if N.x is basically same as A.x
                        # and N.y is between top_y and bot_y
                        # We'll do a bounding-box approach:
                        Nx_left  = N.pos_x - N.half_w
                        Nx_right = N.pos_x + N.half_w
                        # "In line" if A.x is within that horizontal range
                        # and N's center is between top_y and bot_y
                        if Nx_left <= A.pos_x <= Nx_right:
                            Ny_top = N.pos_y - N.half_h
                            Ny_bot = N.pos_y + N.half_h
                            # Overlaps vertically?
                            if (Ny_top < bot_y and Ny_bot > top_y):
                                # It's in the vertical corridor
                                # SHIFT N horizontally by offset
                                # (optionally pick left or right based on some logic)
                                # For example, nudge to the left:
                                N.pos_x -= offset

            # If the link is horizontal (A.y ~ B.y):
            elif abs(A.pos_y - B.pos_y) < 1e-5:
                left_x = min(A.pos_x, B.pos_x)
                right_x = max(A.pos_x, B.pos_x)
                for N in nodes:
                    if N not in (A, B):
                        Ny_top = N.pos_y - N.half_h
                        Ny_bot = N.pos_y + N.half_h
                        # "In line" if A.y is within that vertical range
                        if Ny_top <= A.pos_y <= Ny_bot:
                            Nx_left  = N.pos_x - N.half_w
                            Nx_right = N.pos_x + N.half_w
                            # Overlaps horizontally?
                            if (Nx_left < right_x and Nx_right > left_x):
                                # SHIFT N vertically by offset
                                # e.g., nudge upward:
                                N.pos_y -= offset
