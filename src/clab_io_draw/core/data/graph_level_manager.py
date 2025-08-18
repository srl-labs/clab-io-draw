import logging
from collections import deque

import networkx as nx

logger = logging.getLogger(__name__)


class GraphLevelManager:
    """
    Manages the graph level assignment for nodes in the diagram.
    """

    def assign_graphlevels(
        self, diagram, verbose=False, skip_warnings=False, respect_fixed_positions=False
    ):
        """
        Assign graph levels to nodes in the diagram.

        :param diagram: Diagram object containing nodes and links.
        :param verbose: Enable verbose logging.
        :param skip_warnings: Skip warning messages about missing graph levels.
        :param respect_fixed_positions: Don't override positions of nodes with fixed positions.
        """
        nodes = diagram.nodes
        all_levels_set = all(
            (node.graph_level is not None and node.graph_level != -1)
            for node in nodes.values()
        )

        # More robust fixed position detection
        has_fixed_positions = any(
            node.pos_x is not None
            and node.pos_y is not None
            and str(node.pos_x).strip() != ""
            and str(node.pos_y).strip() != ""
            for node in nodes.values()
        )

        # Show warning only if levels aren't set AND we're not skipping warnings
        # AND we're not using fixed positions
        if not all_levels_set and not skip_warnings and not has_fixed_positions:
            logger.warning(
                "Not all graph levels set in the .clab file. Assigning graph levels based on downstream links. "
                "Expect experimental output. Please consider assigning graph levels to your .clab file, "
                "or use it with -I for interactive mode. Find more information here: "
                "https://github.com/srl-labs/clab-io-draw/blob/main/docs/clab2drawio.md#influencing-node-placement"
            )

        # Extract graph structure for level assignment
        G = nx.DiGraph()
        for node_name in nodes:
            G.add_node(node_name)

        for node in nodes.values():
            for link in node.get_downstream_links():
                G.add_edge(link.source.name, link.target.name)

        # Find roots (nodes with no incoming edges)
        roots = [n for n in G.nodes() if G.in_degree(n) == 0]

        # If no roots identified, use all nodes as potential roots and prune after
        if not roots:
            paths_and_cycles = list(nx.simple_cycles(G))
            if paths_and_cycles:
                # If cycles are detected, use the first node in each cycle as a potential root
                potential_roots = []
                for cycle in paths_and_cycles:
                    potential_roots.append(cycle[0])
                    # Break the cycle by removing the last edge
                    G.remove_edge(cycle[-1], cycle[0])
                roots = potential_roots
            else:
                # If no clear cycles but also no roots, use all nodes as roots
                roots = list(G.nodes())

        # Assign levels using BFS from each root
        levels = {}
        for root in roots:
            bfs_levels = self._bfs_levels(G, root)
            # Update levels dict, keeping the minimum level for each node
            for node, level in bfs_levels.items():
                if node not in levels or level < levels[node]:
                    levels[node] = level

        # Update node levels in the diagram
        for node_name, level in levels.items():
            node = nodes[node_name]
            # Determine if this node has fixed position
            has_fixed_pos = (
                node.pos_x is not None
                and node.pos_y is not None
                and str(node.pos_x).strip() != ""
                and str(node.pos_y).strip() != ""
            )

            # Only update levels if:
            # 1. Level was not specified in YAML (node.graph_level is None)
            # 2. We're not respecting fixed positions OR this specific node doesn't have fixed position
            if node.graph_level is None and (
                not respect_fixed_positions or not has_fixed_pos
            ):
                node.graph_level = level
                if verbose:
                    logger.debug(f"Assigned level {level} to node {node_name}")

        # Calculate link levels
        for node in nodes.values():
            for link in node.get_all_links():
                source_level = link.source.graph_level
                target_level = link.target.graph_level

                # Ensure both levels are integers before subtraction
                if source_level is not None and target_level is not None:
                    try:
                        # Convert to integers if they aren't already
                        if not isinstance(source_level, int):
                            source_level = int(source_level)
                        if not isinstance(target_level, int):
                            target_level = int(target_level)

                        link.level_diff = target_level - source_level
                    except (ValueError, TypeError):
                        # If conversion fails, default to 0
                        link.level_diff = 0
                else:
                    link.level_diff = 0

        # Don't normalize levels if we're respecting fixed positions and have some fixed positions
        if not (respect_fixed_positions and has_fixed_positions):
            self._normalize_levels(nodes)

    def _bfs_levels(self, graph, start_node):
        """
        Perform BFS to assign levels to nodes.

        :param graph: NetworkX DiGraph.
        :param start_node: Root node to start BFS from.
        :return: Dictionary mapping node names to their level.
        """
        visited = {start_node: 0}
        queue = deque([(start_node, 0)])

        while queue:
            node, level = queue.popleft()
            for neighbor in graph.neighbors(node):
                if neighbor not in visited:
                    visited[neighbor] = level + 1
                    queue.append((neighbor, level + 1))

        return visited

    def _normalize_levels(self, nodes):
        """
        Normalize graph levels to start from 0.

        :param nodes: Dictionary of node_name -> Node instances.
        """
        # Find the minimum level
        min_level = float("inf")
        for node in nodes.values():
            if node.graph_level is not None and node.graph_level < min_level:
                min_level = node.graph_level

        # If minimum level is not 0, adjust all levels
        if min_level != 0:
            for node in nodes.values():
                if node.graph_level is not None:
                    node.graph_level -= min_level
