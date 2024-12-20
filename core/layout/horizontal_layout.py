import logging
from core.layout.layout_manager import LayoutManager
from collections import defaultdict

logger = logging.getLogger(__name__)

class HorizontalLayout(LayoutManager):
    """
    Applies a horizontal layout strategy to arrange nodes.
    """

    def apply(self, diagram, verbose=False) -> None:
        logger.debug("Applying horizontal layout...")
        self.diagram = diagram
        self.verbose = verbose
        self._calculate_positions()

    def _calculate_positions(self):
        nodes = self.diagram.nodes
        nodes = sorted(nodes.values(), key=lambda node: (node.graph_level, node.name))

        # Get padding from styles
        padding_x = self.diagram.styles['padding_x']
        padding_y = self.diagram.styles['padding_y']

        x_start, y_start = 100, 100

        logger.debug("Nodes before calculate_positions:", nodes)

        def prioritize_placement(nodes, level):
            diagram = self.diagram
            if level == diagram.get_max_level():
                ordered_nodes = sorted(nodes, key=lambda node: node.name)
            else:
                multi_connection_nodes = [node for node in nodes if node.get_connection_count_within_level() > 1]
                single_connection_nodes = [node for node in nodes if node.get_connection_count_within_level() == 1]
                zero_connection_nodes = [node for node in nodes if node.get_connection_count_within_level() == 0]

                multi_connection_nodes_with_lateral = []
                multi_connection_nodes_without_lateral = []
                for node in multi_connection_nodes:
                    if any(
                        link.target in multi_connection_nodes
                        for link in node.get_lateral_links()
                    ):
                        multi_connection_nodes_with_lateral.append(node)
                    else:
                        multi_connection_nodes_without_lateral.append(node)

                sorted_multi_connection_nodes_with_lateral = []
                while multi_connection_nodes_with_lateral:
                    node = multi_connection_nodes_with_lateral.pop(0)
                    sorted_multi_connection_nodes_with_lateral.append(node)
                    for link in node.get_lateral_links():
                        if link.target in multi_connection_nodes_with_lateral:
                            multi_connection_nodes_with_lateral.remove(link.target)
                            sorted_multi_connection_nodes_with_lateral.append(link.target)

                multi_connection_nodes_without_lateral = sorted(
                    multi_connection_nodes_without_lateral, key=lambda node: node.name
                )
                sorted_multi_connection_nodes_with_lateral = sorted(
                    sorted_multi_connection_nodes_with_lateral, key=lambda node: node.name
                )
                single_connection_nodes = sorted(single_connection_nodes, key=lambda node: node.name)

                ordered_nodes = (
                    single_connection_nodes[: len(single_connection_nodes) // 2]
                    + multi_connection_nodes_without_lateral
                    + sorted_multi_connection_nodes_with_lateral
                    + single_connection_nodes[len(single_connection_nodes) // 2 :]
                    + zero_connection_nodes
                )

            return ordered_nodes

        nodes_by_graphlevel = defaultdict(list)
        for node in nodes:
            nodes_by_graphlevel[node.graph_level].append(node)

        for graphlevel, graphlevel_nodes in nodes_by_graphlevel.items():
            ordered_nodes = prioritize_placement(graphlevel_nodes, graphlevel)
            for i, node in enumerate(ordered_nodes):
                # horizontal layout
                node.pos_x = x_start + graphlevel * padding_x
                node.pos_y = y_start + i * padding_y

        self._center_align_nodes(nodes_by_graphlevel, layout="horizontal", verbose=self.verbose)
        intermediaries_x, intermediaries_y = self.diagram.get_nodes_between_interconnected()
        self._adjust_intermediary_nodes(intermediaries_y, layout="horizontal", verbose=self.verbose)

    def _adjust_intermediary_nodes(self, intermediaries, layout, verbose=False):
        if not intermediaries:
            return
        intermediaries_by_level = defaultdict(list)
        for node in intermediaries:
            intermediaries_by_level[node.graph_level].append(node)

        selected_level = max(
            intermediaries_by_level.keys(),
            key=lambda lvl: len(intermediaries_by_level[lvl]),
        )
        selected_group = intermediaries_by_level[selected_level]

        if len(selected_group) == 1:
            node = selected_group[0]
            if layout == "vertical":
                node.pos_x = node.pos_x - 100
            else:
                node.pos_y = node.pos_y - 100
        else:
            for i, node in enumerate(selected_group):
                if layout == "vertical":
                    node.pos_x = node.pos_x - 100 + i * 200
                else:
                    node.pos_y = node.pos_y - 100 + i * 200

    def _center_align_nodes(self, nodes_by_graphlevel, layout="horizontal", verbose=False):
        attr_x, attr_y = ("pos_x", "pos_y") if layout == "vertical" else ("pos_y", "pos_x")

        prev_graphlevel_center = None
        for graphlevel, nodes in sorted(nodes_by_graphlevel.items()):
            graphlevel_centers = [getattr(node, attr_x) for node in nodes]

            if prev_graphlevel_center is None:
                prev_graphlevel_center = (min(graphlevel_centers) + max(graphlevel_centers)) / 2
            else:
                graphlevel_center = sum(graphlevel_centers) / len(nodes)
                offset = prev_graphlevel_center - graphlevel_center
                for node in nodes:
                    setattr(node, attr_x, getattr(node, attr_x) + offset)
                prev_graphlevel_center = sum(getattr(node, attr_x) for node in nodes) / len(nodes)
