class GraphLevelManager:
    def __init__(self):
        pass

    def update_links(self, links):
        # Same logic as before
        for link in links:
            source_level = link.source.graph_level
            target_level = link.target.graph_level
            link.level_diff = target_level - source_level
            if link.level_diff > 0:
                link.direction = "downstream"
            elif link.level_diff < 0:
                link.direction = "upstream"
            else:
                link.direction = "lateral"

    def adjust_node_levels(self, diagram):
        used_levels = diagram.get_used_levels()
        max_level = diagram.get_max_level()
        min_level = diagram.get_min_level()

        if len(used_levels) <= 1:
            return  # Only one level present, no adjustment needed

        current_level = min_level
        while current_level < max_level + 1:
            if current_level == min_level:
                current_level += 1
                continue

            nodes_at_current_level = diagram.get_nodes_by_level(current_level)
            before_level = current_level - 1
            nodes_to_move = []

            if len(nodes_at_current_level.items()) == 1:
                current_level += 1
                continue
            for node_name, node in nodes_at_current_level.items():
                has_upstream_connection = any(
                    node.get_upstream_links_towards_level(before_level)
                )

                if not has_upstream_connection:
                    nodes_to_move.append(node)

            if len(nodes_to_move) == len(nodes_at_current_level):
                current_level += 1
                continue

            if nodes_to_move:
                for level in range(max_level, current_level, -1):
                    nodes_at_level = diagram.get_nodes_by_level(level)
                    for node in nodes_at_level.values():
                        node.graph_level += 1

                for node in nodes_to_move:
                    node.graph_level += 1

                self.update_links(diagram.get_links_from_nodes())
                max_level = diagram.get_max_level()

            max_level = diagram.get_max_level()
            current_level += 1

        for level in range(max_level, min_level - 1, -1):
            nodes_at_level = diagram.get_nodes_by_level(level)
            for node in nodes_at_level.values():
                upstream_links = node.get_upstream_links()
                can_move = True
                for link in upstream_links:
                    level_diff = node.graph_level - link.target.graph_level
                    if level_diff == 1:
                        can_move = False
                        break

                if can_move:
                    for link in upstream_links:
                        level_diff = node.graph_level - link.target.graph_level
                        if level_diff > 1:
                            node.graph_level -= 1
                            self.update_links(diagram.get_links_from_nodes())
                            max_level = diagram.get_max_level()
                            break

    def assign_graphlevels(self, diagram, verbose=False):
        nodes = diagram.get_nodes()

        # Check if all nodes already have a graphlevel != -1
        if all(node.graph_level != -1 for node in nodes.values()):
            already_set = True
        else:
            already_set = False
            print(
                "Not all graph levels set in the .clab file. Assigning graph levels based on downstream links. Expect experimental output. Please consider assigning graph levels to your .clab file, or use it with -I for interactive mode. Find more information here: https://github.com/srl-labs/clab-io-draw/blob/grafana_style/docs/clab2drawio.md#influencing-node-placement"
            )

        def set_graphlevel(node, current_graphlevel, visited=None):
            if visited is None:
                visited = set()
            if node.name in visited:
                return
            visited.add(node.name)

            if node.graph_level < current_graphlevel:
                node.graph_level = current_graphlevel
            for link in node.get_downstream_links():
                target_node = nodes[link.target.name]
                set_graphlevel(target_node, current_graphlevel + 1, visited)

        for node in nodes.values():
            if node.graph_level != -1:
                continue
            elif not node.get_upstream_links():
                set_graphlevel(node, 0)
            else:
                set_graphlevel(node, node.graph_level)

        for node in nodes.values():
            node.update_links()

        if not already_set:
            self.adjust_node_levels(diagram)
            for node in nodes.values():
                node.update_links()

        sorted_nodes = sorted(
            nodes.values(), key=lambda node: (node.graph_level, node.name)
        )
        return sorted_nodes
