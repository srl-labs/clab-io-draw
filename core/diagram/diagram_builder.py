import re
import random
import logging

logger = logging.getLogger(__name__)

class DiagramBuilder:
    """
    Builds diagram elements such as nodes, ports, and links into the Draw.io diagram.
    """

    def add_ports(self, diagram, styles, verbose=True):
        """
        Add ports and their connections to the diagram.

        :param diagram: CustomDrawioDiagram instance.
        :param styles: Styles dictionary.
        :param verbose: Enable verbose output.
        """
        logger.debug("Adding ports to nodes...")
        nodes = diagram.nodes

        # Calculate port positions
        for node in nodes.values():
            links = node.get_all_links()
            direction_groups = {}
            for link in links:
                direction = link.direction
                direction_groups.setdefault(direction, []).append(link)

            for direction, group in direction_groups.items():
                # Position ports depending on layout and direction
                if diagram.layout == "vertical":
                    if direction == "downstream":
                        sorted_links = sorted(group, key=lambda link: (link.source.pos_x, link.target.pos_x))
                        num_links = len(sorted_links)
                        spacing = styles["node_width"] / (num_links + 1)
                        for i, link in enumerate(sorted_links):
                            port_x = (node.pos_x + (i + 1) * spacing - styles["port_width"] / 2)
                            port_y = (node.pos_y + styles["node_height"] - styles["port_height"] / 2)
                            link.port_pos = (port_x, port_y)
                    elif direction == "upstream":
                        sorted_links = sorted(group, key=lambda link: (link.source.pos_x, link.target.pos_x))
                        num_links = len(sorted_links)
                        spacing = styles["node_width"] / (num_links + 1)
                        for i, link in enumerate(sorted_links):
                            port_x = (node.pos_x + (i + 1) * spacing - styles["port_width"] / 2)
                            port_y = node.pos_y - styles["port_height"] / 2
                            link.port_pos = (port_x, port_y)
                    else: # lateral
                        sorted_links = sorted(group, key=lambda link: (link.source.pos_y, link.target.pos_y))
                        num_links = len(sorted_links)
                        spacing = styles["node_height"] / (num_links + 1)
                        for i, link in enumerate(sorted_links):
                            if link.target.pos_x > link.source.pos_x:
                                port_x = node.pos_x + styles["node_width"] - styles["port_width"] / 2
                            else:
                                port_x = node.pos_x - styles["port_width"] / 2
                            port_y = node.pos_y + (i + 1) * spacing - styles["port_height"] / 2
                            link.port_pos = (port_x, port_y)
                else:
                    # horizontal layout
                    if direction == "downstream":
                        sorted_links = sorted(group, key=lambda link: (link.source.pos_y, link.target.pos_y))
                        num_links = len(sorted_links)
                        spacing = styles["node_height"] / (num_links + 1)
                        for i, link in enumerate(sorted_links):
                            port_x = node.pos_x + styles["node_width"] - styles["port_width"] / 2
                            port_y = node.pos_y + (i + 1) * spacing - styles["port_height"] / 2
                            link.port_pos = (port_x, port_y)

                    elif direction == "upstream":
                        sorted_links = sorted(group, key=lambda link: (link.source.pos_y, link.target.pos_y))
                        num_links = len(sorted_links)
                        spacing = styles["node_height"] / (num_links + 1)
                        for i, link in enumerate(sorted_links):
                            port_x = node.pos_x - styles["port_width"] / 2
                            port_y = node.pos_y + (i + 1) * spacing - styles["port_height"] / 2
                            link.port_pos = (port_x, port_y)
                    else: # lateral
                        sorted_links = sorted(group, key=lambda link: (link.source.pos_x, link.target.pos_x))
                        num_links = len(sorted_links)
                        spacing = styles["node_width"] / (num_links + 1)
                        for i, link in enumerate(sorted_links):
                            if link.target.pos_y > link.source.pos_y:
                                port_y = node.pos_y + styles["node_height"] - styles["port_height"] / 2
                            else:
                                port_y = node.pos_y - styles["port_height"] / 2
                            port_x = node.pos_x + (i + 1) * spacing - styles["port_width"] / 2
                            link.port_pos = (port_x, port_y)

        # Create connectors and midpoint connectors
        connector_dict = {}
        processed_connections = set()
        for node in nodes.values():
            downstream_links = node.get_downstream_links()
            lateral_links = node.get_lateral_links()
            node_links = downstream_links + lateral_links

            for link in node_links:
                connection_id = frozenset({
                    (link.source.name, link.source_intf),
                    (link.target.name, link.target_intf),
                })
                if connection_id not in processed_connections:
                    processed_connections.add(connection_id)
                    source_cID = f"{link.source.name}:{link.source_intf}:{link.target.name}:{link.target_intf}"
                    source_label = re.findall(r"\d+", link.source_intf)[-1]
                    source_connector_pos = link.port_pos
                    port_width = styles["port_width"]
                    port_height = styles["port_height"]

                    if link.source.name not in connector_dict:
                        connector_dict[link.source.name] = []
                    connector_dict[link.source.name].append(source_cID)

                    target_cID = f"{link.target.name}:{link.target_intf}:{link.source.name}:{link.source_intf}"
                    target_link = diagram.get_target_link(link)
                    target_connector_pos = target_link.port_pos
                    target_label = re.findall(r"\d+", target_link.source_intf)[-1]

                    if link.target.name not in connector_dict:
                        connector_dict[link.target.name] = []
                    connector_dict[link.target.name].append(target_cID)

                    # Adjust port positions if mismatch
                    source_downstream_links = link.source.get_downstream_links()
                    target_upstream_links = link.target.get_upstream_links()
                    if diagram.layout == "vertical":
                        if link.source.pos_x == link.target.pos_x:
                            if len(source_downstream_links) != len(target_upstream_links):
                                if len(source_downstream_links) < len(target_upstream_links):
                                    adjusted_x = target_connector_pos[0]
                                    source_connector_pos = (adjusted_x, source_connector_pos[1])
                                else:
                                    adjusted_x = source_connector_pos[0]
                                    target_connector_pos = (adjusted_x, target_connector_pos[1])
                    elif diagram.layout == "horizontal":
                        if link.source.pos_y == link.target.pos_y:
                            if len(source_downstream_links) != len(target_upstream_links):
                                if len(source_downstream_links) < len(target_upstream_links):
                                    adjusted_y = target_connector_pos[1]
                                    source_connector_pos = (source_connector_pos[0], adjusted_y)
                                else:
                                    adjusted_y = source_connector_pos[1]
                                    target_connector_pos = (target_connector_pos[0], adjusted_y)

                    # Add source and target connector nodes
                    diagram.add_node(
                        id=source_cID,
                        label=source_label,
                        x_pos=source_connector_pos[0],
                        y_pos=source_connector_pos[1],
                        width=port_width,
                        height=port_height,
                        style=styles["port_style"],
                    )

                    diagram.add_node(
                        id=target_cID,
                        label=target_label,
                        x_pos=target_connector_pos[0],
                        y_pos=target_connector_pos[1],
                        width=port_width,
                        height=port_height,
                        style=styles["port_style"],
                    )

                    # Create midpoint connector
                    source_center = (
                        source_connector_pos[0] + port_width / 2,
                        source_connector_pos[1] + port_height / 2,
                    )
                    target_center = (
                        target_connector_pos[0] + port_width / 2,
                        target_connector_pos[1] + port_height / 2,
                    )

                    midpoint_center_x = (source_center[0] + target_center[0]) / 2
                    midpoint_center_y = (source_center[1] + target_center[1]) / 2

                    random_offset = random.choice(
                        [random.uniform(-20, -10), random.uniform(10, 20)]
                    )
                    dx = target_center[0] - source_center[0]
                    dy = target_center[1] - source_center[1]
                    magnitude = (dx**2 + dy**2) ** 0.5
                    if magnitude != 0:
                        direction_dx = dx / magnitude
                        direction_dy = dy / magnitude
                    else:
                        direction_dx = 0
                        direction_dy = 0

                    midpoint_center_x += direction_dx * random_offset
                    midpoint_center_y += direction_dy * random_offset

                    midpoint_top_left_x = midpoint_center_x - 2
                    midpoint_top_left_y = midpoint_center_y - 2

                    midpoint_id = f"mid:{link.source.name}:{link.source_intf}:{link.target.name}:{link.target_intf}"
                    diagram.add_node(
                        id=midpoint_id,
                        label="\u200b",
                        x_pos=midpoint_top_left_x,
                        y_pos=midpoint_top_left_y,
                        width=styles["connector_width"],
                        height=styles["connector_height"],
                        style=styles["connector_style"],
                    )

                    diagram.add_link(
                        source=source_cID,
                        target=midpoint_id,
                        style=styles["link_style"],
                        label="rate",
                        link_id=f"{source_cID}",
                    )
                    diagram.add_link(
                        source=target_cID,
                        target=midpoint_id,
                        style=styles["link_style"],
                        label="rate",
                        link_id=f"{target_cID}",
                    )

        # Create groups for each node + connectors
        for node_name, connector_ids in connector_dict.items():
            group_id = f"group-{node_name}"
            member_objects = connector_ids + [node_name]
            diagram.group_nodes(
                member_objects=member_objects, group_id=group_id, style="group"
            )

    def add_links(self, diagram, styles):
        """
        Add links between nodes, with labels if needed.

        :param diagram: CustomDrawioDiagram instance.
        :param styles: Styles dictionary.
        """
        logger.debug("Adding links to diagram...")
        nodes = diagram.nodes
        global_seen_links = set()

        for node in nodes.values():
            downstream_links = node.get_downstream_links()
            lateral_links = node.get_lateral_links()
            all_links = downstream_links + lateral_links

            filtered_links = []
            for link in all_links:
                source_id = f"{link.source.name}:{link.source_intf}"
                target_id = f"{link.target.name}:{link.target_intf}"
                link_pair = tuple(sorted([source_id, target_id]))
                if link_pair not in global_seen_links:
                    global_seen_links.add(link_pair)
                    filtered_links.append(link)

            target_groups = {}
            for link in filtered_links:
                target = link.target
                target_groups.setdefault(target, []).append(link)

            for target, group in target_groups.items():
                for i, link in enumerate(group):
                    source_x, source_y = link.source.pos_x, link.source.pos_y
                    target_x, target_y = link.target.pos_x, link.target.pos_y
                    left_to_right = source_x < target_x
                    above_to_below = source_y < target_y

                    step = 0.5 if len(group) == 1 else 0.25 + 0.5 * (i / (len(group) - 1))

                    if diagram.layout == "horizontal":
                        if link.level_diff > 0:
                            entryX, exitX = (0, 1) if left_to_right else (1, 0)
                            entryY = exitY = step
                        else:
                            if above_to_below:
                                entryY, exitY = (0, 1)
                            else:
                                entryY, exitY = (1, 0)
                            entryX = exitX = step
                    else: # vertical layout
                        if link.level_diff > 0:
                            entryY, exitY = (0, 1) if above_to_below else (1, 0)
                            entryX = exitX = step
                        else:
                            if left_to_right:
                                entryX, exitX = (0, 1)
                            else:
                                entryX, exitX = (1, 0)
                            entryY = exitY = step

                    style = f"{styles['link_style']}entryY={entryY};exitY={exitY};entryX={entryX};exitX={exitX};"

                    source_label_id = f"label:{link.source.name}:{link.source_intf}"
                    target_label_id = f"label:{link.target.name}:{link.target_intf}"

                    if not styles["default_labels"]:
                        ((source_label_x, source_label_y),
                         (target_label_x, target_label_y)) = link.get_label_positions(entryX, entryY, exitX, exitY, styles)

                        diagram.add_link(
                            link_id=f"link:{link.source.name}:{link.source_intf}:{link.target.name}:{link.target_intf}",
                            source=link.source.name,
                            target=link.target.name,
                            style=style,
                        )

                        diagram.add_node(
                            id=source_label_id,
                            label=f"{link.source_intf}",
                            x_pos=source_label_x,
                            y_pos=source_label_y,
                            width=styles["label_width"],
                            height=styles["label_height"],
                            style=styles["src_label_style"],
                        )

                        diagram.add_node(
                            id=target_label_id,
                            label=f"{link.target_intf}",
                            x_pos=target_label_x,
                            y_pos=target_label_y,
                            width=styles["label_width"],
                            height=styles["label_height"],
                            style=styles["trgt_label_style"],
                        )
                    else:
                        diagram.add_link(
                            link_id=f"link:{link.source.name}:{link.source_intf}:{link.target.name}:{link.target_intf}",
                            source=link.source.name,
                            target=link.target.name,
                            src_label=link.source_intf,
                            trgt_label=link.target_intf,
                            src_label_style=styles["src_label_style"],
                            trgt_label_style=styles["trgt_label_style"],
                            style=style,
                        )

    def add_nodes(self, diagram, nodes, styles):
        """
        Add nodes to the diagram.

        :param diagram: CustomDrawioDiagram instance.
        :param nodes: Dictionary of node_name -> Node instances.
        :param styles: Styles dictionary.
        """
        logger.debug("Adding nodes to diagram...")
        base_style = styles["base_style"]
        custom_styles = styles["custom_styles"]
        icon_to_group_mapping = styles["icon_to_group_mapping"]

        for node in nodes.values():
            if node.graph_icon in icon_to_group_mapping:
                group = icon_to_group_mapping[node.graph_icon]
            else:
                # Fallback heuristics
                if "client" in node.name:
                    group = "server"
                elif "leaf" in node.name:
                    group = "leaf"
                elif "spine" in node.name:
                    group = "spine"
                elif "dcgw" in node.name:
                    group = "dcgw"
                else:
                    group = "default"

            style = custom_styles.get(group, base_style)
            x_pos, y_pos = node.pos_x, node.pos_y
            diagram.add_node(
                id=node.name,
                label=node.label,
                x_pos=x_pos,
                y_pos=y_pos,
                style=style,
                width=node.width,
                height=node.height,
            )
