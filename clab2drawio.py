# from N2G import drawio_diagram
from lib.CustomDrawioDiagram import CustomDrawioDiagram
from lib.Link import Link
from lib.Node import Node
from lib.Grafana import GrafanaDashboard
from lib.Yaml_processor import YAMLProcessor
from collections import defaultdict
from prompt_toolkit.shortcuts import checkboxlist_dialog, yes_no_dialog
import yaml
import argparse
import os
import re
import random


def add_ports(diagram, styles, verbose=True):
    nodes = diagram.nodes

    # Calculate and set port positions for all nodes
    for node in nodes.values():
        links = node.get_all_links()

        # Group links by their direction
        direction_groups = {}
        for link in links:
            direction = link.direction
            if direction not in direction_groups:
                direction_groups[direction] = []
            direction_groups[direction].append(link)

        for direction, group in direction_groups.items():
            if diagram.layout == "vertical":
                if direction == "downstream":
                    # Sort downstream links by x position of source and target
                    sorted_links = sorted(
                        group, key=lambda link: (link.source.pos_x, link.target.pos_x)
                    )
                    num_links = len(sorted_links)
                    spacing = styles["node_width"] / (num_links + 1)
                    for i, link in enumerate(sorted_links):
                        port_x = (
                            node.pos_x
                            + (i + 1) * spacing
                            - styles["connector_width"] / 2
                        )
                        port_y = (
                            node.pos_y
                            + styles["node_height"]
                            - styles["connector_height"] / 2
                        )
                        link.port_pos = (port_x, port_y)
                elif direction == "upstream":
                    # Sort upstream links by x position of source and target
                    sorted_links = sorted(
                        group, key=lambda link: (link.source.pos_x, link.target.pos_x)
                    )
                    num_links = len(sorted_links)
                    spacing = styles["node_width"] / (num_links + 1)
                    for i, link in enumerate(sorted_links):
                        port_x = (
                            node.pos_x
                            + (i + 1) * spacing
                            - styles["connector_width"] / 2
                        )
                        port_y = node.pos_y - styles["connector_height"] / 2
                        link.port_pos = (port_x, port_y)
                else:
                    # Sort lateral links by y position of source and target
                    sorted_links = sorted(
                        group, key=lambda link: (link.source.pos_y, link.target.pos_y)
                    )
                    num_links = len(sorted_links)
                    spacing = styles["node_height"] / (num_links + 1)
                    for i, link in enumerate(sorted_links):
                        if link.target.pos_x > link.source.pos_x:
                            # Lateral link to the right
                            port_x = node.pos_x + styles["node_width"]
                        else:
                            # Lateral link to the left
                            port_x = node.pos_x
                        port_y = node.pos_y + (i + 1) * spacing
                        link.port_pos = (port_x, port_y)
            elif diagram.layout == "horizontal":
                if direction == "downstream":
                    # Sort downstream links by y position of source and target
                    sorted_links = sorted(
                        group, key=lambda link: (link.source.pos_y, link.target.pos_y)
                    )
                    num_links = len(sorted_links)
                    spacing = styles["node_height"] / (num_links + 1)
                    for i, link in enumerate(sorted_links):
                        port_x = node.pos_x + styles["node_width"]
                        port_y = node.pos_y + (i + 1) * spacing
                        link.port_pos = (port_x, port_y)
                elif direction == "upstream":
                    # Sort upstream links by y position of source and target
                    sorted_links = sorted(
                        group, key=lambda link: (link.source.pos_y, link.target.pos_y)
                    )
                    num_links = len(sorted_links)
                    spacing = styles["node_height"] / (num_links + 1)
                    for i, link in enumerate(sorted_links):
                        port_x = node.pos_x
                        port_y = node.pos_y + (i + 1) * spacing
                        link.port_pos = (port_x, port_y)
                else:
                    # Sort lateral links by x position of source and target
                    sorted_links = sorted(
                        group, key=lambda link: (link.source.pos_x, link.target.pos_x)
                    )
                    num_links = len(sorted_links)
                    spacing = styles["node_width"] / (num_links + 1)
                    for i, link in enumerate(sorted_links):
                        if link.target.pos_y > link.source.pos_y:
                            # Lateral link to the bottom
                            port_y = node.pos_y + styles["node_height"]
                        else:
                            # Lateral link to the top
                            port_y = node.pos_y
                        port_x = node.pos_x + (i + 1) * spacing
                        link.port_pos = (port_x, port_y)

    connector_dict = {}
    # Create connectors and links using the calculated port positions
    processed_connections = set()
    for node in nodes.values():
        downstream_links = node.get_downstream_links()
        lateral_links = node.get_lateral_links()

        links = downstream_links + lateral_links

        for link in links:
            connection_id = frozenset(
                {
                    (link.source.name, link.source_intf),
                    (link.target.name, link.target_intf),
                }
            )
            if connection_id not in processed_connections:
                processed_connections.add(connection_id)
                # print(connection_id)
                # source connector
                source_cID = f"{link.source.name}:{link.source_intf}:{link.target.name}:{link.target_intf}"
                source_label = re.findall(r"\d+", link.source_intf)[-1]
                source_connector_pos = link.port_pos
                connector_width = styles["connector_width"]
                connector_height = styles["connector_height"]

                # Add the source connector ID to the source connector dictionary
                if link.source.name not in connector_dict:
                    connector_dict[link.source.name] = []
                connector_dict[link.source.name].append(source_cID)

                # target connector
                target_cID = f"{link.target.name}:{link.target_intf}:{link.source.name}:{link.source_intf}"
                target_link = diagram.get_target_link(link)
                target_connector_pos = target_link.port_pos
                target_label = re.findall(r"\d+", target_link.source_intf)[-1]

                if link.target.name not in connector_dict:
                    connector_dict[link.target.name] = []
                connector_dict[link.target.name].append(target_cID)

                # Adjust port positions if source and target have different numbers of links
                source_downstream_links = link.source.get_downstream_links()
                target_upstream_links = link.target.get_upstream_links()
                if diagram.layout == "vertical":
                    if link.source.pos_x == link.target.pos_x:
                        if len(source_downstream_links) != len(target_upstream_links):
                            if len(source_downstream_links) < len(
                                target_upstream_links
                            ):
                                # Adjust source port position to align with the corresponding target port
                                adjusted_x = target_connector_pos[0]
                                source_connector_pos = (
                                    adjusted_x,
                                    source_connector_pos[1],
                                )
                            else:
                                # Adjust target port position to align with the corresponding source port
                                adjusted_x = source_connector_pos[0]
                                target_connector_pos = (
                                    adjusted_x,
                                    target_connector_pos[1],
                                )
                elif diagram.layout == "horizontal":
                    if link.source.pos_y == link.target.pos_y:
                        # pass
                        if len(source_downstream_links) != len(target_upstream_links):
                            if len(source_downstream_links) < len(
                                target_upstream_links
                            ):
                                # Adjust source port position to align with the corresponding target port
                                adjusted_y = target_connector_pos[1]
                                source_connector_pos = (
                                    source_connector_pos[0],
                                    adjusted_y,
                                )
                            else:
                                # Adjust target port position to align with the corresponding source port
                                adjusted_y = source_connector_pos[1]
                                target_connector_pos = (
                                    target_connector_pos[0],
                                    adjusted_y,
                                )

                diagram.add_node(
                    id=source_cID,
                    label=source_label,
                    x_pos=source_connector_pos[0],
                    y_pos=source_connector_pos[1],
                    width=connector_width,
                    height=connector_height,
                    style=styles["port_style"],
                )

                diagram.add_node(
                    id=target_cID,
                    label=target_label,
                    x_pos=target_connector_pos[0],
                    y_pos=target_connector_pos[1],
                    width=connector_width,
                    height=connector_height,
                    style=styles["port_style"],
                )

                # Calculate center positions
                source_center = (
                    source_connector_pos[0] + connector_width / 2,
                    source_connector_pos[1] + connector_height / 2,
                )
                target_center = (
                    target_connector_pos[0] + connector_width / 2,
                    target_connector_pos[1] + connector_height / 2,
                )

                # Calculate the real middle between the centers for the midpoint connector
                midpoint_center_x = (source_center[0] + target_center[0]) / 2
                midpoint_center_y = (source_center[1] + target_center[1]) / 2

                # Generate a random offset within the range of ±10
                random_offset = random.choice(
                    [random.uniform(-20, -10), random.uniform(10, 20)]
                )

                # Determine the direction of the link
                dx = target_center[0] - source_center[0]
                dy = target_center[1] - source_center[1]

                # Calculate the normalized direction vector for the line
                magnitude = (dx**2 + dy**2) ** 0.5
                if magnitude != 0:
                    direction_dx = dx / magnitude
                    direction_dy = dy / magnitude
                else:
                    # If the magnitude is zero, the source and target are at the same position
                    # In this case, we don't need to move the midpoint
                    direction_dx = 0
                    direction_dy = 0

                # Apply the offset
                midpoint_center_x += direction_dx * random_offset
                midpoint_center_y += direction_dy * random_offset

                midpoint_top_left_x = midpoint_center_x - 2
                midpoint_top_left_y = midpoint_center_y - 2

                # Create midpoint connector between source and target ports
                midpoint_id = f"mid:{link.source.name}:{link.source_intf}:{link.target.name}:{link.target_intf}"
                diagram.add_node(
                    id=midpoint_id,
                    label="\u200b",
                    x_pos=midpoint_top_left_x,
                    y_pos=midpoint_top_left_y,
                    width=4,
                    height=4,
                    style=styles["connector_style"],
                )

                diagram.add_link(
                    source=source_cID,
                    target=midpoint_id,
                    style=styles["link_style"],
                    label="\u200b",
                    link_id=f"{source_cID}",
                )
                diagram.add_link(
                    source=target_cID,
                    target=midpoint_id,
                    style=styles["link_style"],
                    label="\u200b",
                    link_id=f"{target_cID}",
                )

    # Create groups for each node and its connectors
    for node_name, connector_ids in connector_dict.items():
        group_id = f"group-{node_name}"
        member_objects = connector_ids + [node_name]
        diagram.group_nodes(
            member_objects=member_objects, group_id=group_id, style="group"
        )


def add_links(diagram, styles):
    nodes = diagram.nodes

    for node in nodes.values():
        downstream_links = node.get_downstream_links()
        lateral_links = node.get_lateral_links()

        links = downstream_links + lateral_links

        # Group links by their target
        target_groups = {}
        for link in links:
            target = link.target
            if target not in target_groups:
                target_groups[target] = []
            target_groups[target].append(link)

        for target, group in target_groups.items():
            for i, link in enumerate(group):
                source_x, source_y = link.source.pos_x, link.source.pos_y
                target_x, target_y = link.target.pos_x, link.target.pos_y

                # Determine directionality
                left_to_right = source_x < target_x
                above_to_below = source_y < target_y

                # Calculate step for multiple links with the same target
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
                elif diagram.layout == "vertical":
                    if link.level_diff > 0:
                        entryY, exitY = (0, 1) if above_to_below else (1, 0)
                        entryX = exitX = step
                    # Same graph level
                    else:
                        if left_to_right:
                            entryX, exitX = (0, 1)
                        else:
                            entryX, exitX = (1, 0)
                        entryY = exitY = step
                style = f"{styles['link_style']}entryY={entryY};exitY={exitY};entryX={entryX};exitX={exitX};"

                diagram.add_link(
                    source=link.source.name,
                    target=link.target.name,
                    src_label=link.source_intf,
                    trgt_label=link.target_intf,
                    src_label_style=styles["src_label_style"],
                    trgt_label_style=styles["trgt_label_style"],
                    style=style,
                )


def add_nodes(diagram, nodes, styles):
    base_style = styles["base_style"]
    custom_styles = styles["custom_styles"]
    icon_to_group_mapping = styles["icon_to_group_mapping"]

    for node in nodes.values():
        # Check for 'graph_icon' attribute and map it to the corresponding group
        if node.graph_icon in icon_to_group_mapping:
            group = icon_to_group_mapping[node.graph_icon]
        else:
            # Determine the group based on the node's name if 'graph_icon' is not specified
            if "client" in node.name:
                group = "server"
            elif "leaf" in node.name:
                group = "leaf"
            elif "spine" in node.name:
                group = "spine"
            elif "dcgw" in node.name:
                group = "dcgw"
            else:
                group = (
                    "default"  # Fallback to 'default' if none of the conditions are met
                )

        style = custom_styles.get(group, base_style)
        x_pos, y_pos = node.pos_x, node.pos_y
        # Add each node to the diagram with the given x and y position.
        diagram.add_node(
            id=node.name,
            label=node.label,
            x_pos=x_pos,
            y_pos=y_pos,
            style=style,
            width=node.width,
            height=node.height,
        )


def adjust_intermediary_nodes(intermediaries, layout, verbose=False):
    if not intermediaries:
        return

    # group the intermediaries by their graph level
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

    pass


def center_align_nodes(nodes_by_graphlevel, layout="vertical", verbose=False):
    """
    Center align nodes within each graphlevel based on the layout layout and ensure
    they are nicely distributed to align with the graphlevel above.
    """

    attr_x, attr_y = ("pos_x", "pos_y") if layout == "vertical" else ("pos_y", "pos_x")

    prev_graphlevel_center = None
    for graphlevel, nodes in sorted(nodes_by_graphlevel.items()):
        graphlevel_centers = [getattr(node, attr_x) for node in nodes]

        if prev_graphlevel_center is None:
            # For the first graphlevel, calculate its center and use it as the previous center for the next level
            prev_graphlevel_center = (
                min(graphlevel_centers) + max(graphlevel_centers)
            ) / 2
        else:
            # Calculate current graphlevel's center
            graphlevel_center = sum(graphlevel_centers) / len(nodes)

            # Calculate offset to align current graphlevel's center with the previous graphlevel's center
            offset = prev_graphlevel_center - graphlevel_center

            # Apply offset to each node in the current graphlevel
            for node in nodes:
                setattr(node, attr_x, getattr(node, attr_x) + offset)

            # Update prev_graphlevel_center for the next level
            prev_graphlevel_center = sum(getattr(node, attr_x) for node in nodes) / len(
                nodes
            )


def calculate_positions(diagram, layout="vertical", verbose=False):
    """
    Calculates and assigns positions to nodes for graph visualization based on their hierarchical levels and connectivity.
    Organizes nodes by graph level, applies prioritization within levels based on connectivity, and adjusts positions to enhance readability.
    Aligns and adjusts intermediary nodes to address alignment issues and improve visual clarity.
    """

    nodes = diagram.nodes
    nodes = sorted(nodes.values(), key=lambda node: (node.graph_level, node.name))

    x_start, y_start = 100, 100
    padding_x, padding_y = 150, 175
    min_margin = 150

    if verbose:
        print("Nodes before calculate_positions:", nodes)

    def prioritize_placement(nodes, level, verbose=False):
        if level == diagram.get_max_level():
            # If it's the maximum level, simply sort nodes by name
            ordered_nodes = sorted(nodes, key=lambda node: node.name)
        else:
            # Separate nodes by their connection count within the level
            multi_connection_nodes = [
                node for node in nodes if node.get_connection_count_within_level() > 1
            ]
            single_connection_nodes = [
                node for node in nodes if node.get_connection_count_within_level() == 1
            ]
            zero_connection_nodes = [
                node for node in nodes if node.get_connection_count_within_level() == 0
            ]

            # Separate multi-connection nodes with lateral links
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

            # Sort multi-connection nodes with lateral links wisely
            sorted_multi_connection_nodes_with_lateral = []
            while multi_connection_nodes_with_lateral:
                node = multi_connection_nodes_with_lateral.pop(0)
                sorted_multi_connection_nodes_with_lateral.append(node)
                for link in node.get_lateral_links():
                    if link.target in multi_connection_nodes_with_lateral:
                        multi_connection_nodes_with_lateral.remove(link.target)
                        sorted_multi_connection_nodes_with_lateral.append(link.target)

            # sort by name
            multi_connection_nodes_without_lateral = sorted(
                multi_connection_nodes_without_lateral, key=lambda node: node.name
            )
            sorted_multi_connection_nodes_with_lateral = sorted(
                sorted_multi_connection_nodes_with_lateral, key=lambda node: node.name
            )
            single_connection_nodes = sorted(
                single_connection_nodes, key=lambda node: node.name
            )

            # Merge single, multi-connection (with and without lateral), and zero-connection nodes
            ordered_nodes = (
                single_connection_nodes[: len(single_connection_nodes) // 2]
                + multi_connection_nodes_without_lateral
                + sorted_multi_connection_nodes_with_lateral
                + single_connection_nodes[len(single_connection_nodes) // 2 :]
                + zero_connection_nodes
            )

        return ordered_nodes

    # Organize nodes by graphlevel and order within each graphlevel
    nodes_by_graphlevel = defaultdict(list)
    for node in nodes:
        nodes_by_graphlevel[node.graph_level].append(node)

    for graphlevel, graphlevel_nodes in nodes_by_graphlevel.items():
        ordered_nodes = prioritize_placement(
            graphlevel_nodes, graphlevel, verbose=verbose
        )

        for i, node in enumerate(ordered_nodes):
            if layout == "vertical":
                node.pos_x = x_start + i * padding_x
                node.pos_y = y_start + graphlevel * padding_y
            else:
                node.pos_x = x_start + graphlevel * padding_x
                node.pos_y = y_start + i * padding_y

    center_align_nodes(nodes_by_graphlevel, layout=layout, verbose=verbose)

    intermediaries_x, intermediaries_y = diagram.get_nodes_between_interconnected()

    if diagram.layout == "vertical":
        adjust_intermediary_nodes(
            intermediaries_x, layout=diagram.layout, verbose=verbose
        )
    else:
        adjust_intermediary_nodes(
            intermediaries_y, layout=diagram.layout, verbose=verbose
        )


def adjust_node_levels(diagram):
    used_levels = diagram.get_used_levels()
    max_level = diagram.get_max_level()
    min_level = diagram.get_min_level()
    # print(f"Initial used levels: {used_levels}")
    if len(used_levels) <= 1:
        # print("Only one level present, no adjustment needed.")
        return  # Only one level present, no adjustment needed

    current_level = min_level
    while current_level < max_level + 1:
        # if level is the first used level or the last used level, skip it
        if current_level == min_level:
            # print(f"Skip Level: {current_level} because it is the first or last level")
            current_level += 1
            continue

        nodes_at_current_level = diagram.get_nodes_by_level(current_level)
        nodes_at_next_level = diagram.get_nodes_by_level(current_level + 1)
        # print(f"Processing level {current_level}:")
        # print(f"Nodes at current level: {{current_level}} {[node.name for node in nodes_at_current_level.values()]}")
        next_level = current_level + 1
        before_level = current_level - 1
        nodes_to_move = []
        # if nodes_at_next_level:

        if len(nodes_at_current_level.items()) == 1:
            # print(f"Only one node found at level {current_level}. No adjustment needed.")
            current_level += 1
            continue
        for node_name, node in nodes_at_current_level.items():
            has_upstream_connection = any(
                node.get_upstream_links_towards_level(before_level)
            )

            if not has_upstream_connection:
                nodes_to_move.append(node)
            # else:
            # print(f"Node {node_name} has {len(node.get_upstream_links_towards_level(before_level))} upstream links against Level {before_level} No adjustment needed.")

        if len(nodes_to_move) == len(nodes_at_current_level):
            # print(f"Nothing to move here")
            current_level += 1
            continue
        # else:
        # for node in nodes_to_move:
        # print(f"!Node {node.name} does not have an upstream connection to level {before_level}. Marked for movement.")

        if nodes_to_move:
            # print(f"Because we need to move, we are increasing all node_graphlevels from the next Levels Nodes by one level")

            for level in range(max_level, current_level, -1):
                nodes_at_level = diagram.get_nodes_by_level(level)
                for node in nodes_at_level.values():
                    node.graph_level += 1
                    # print(f"  Moving node {node.name} from level {level} to level {level + 1}.")

            # Move the nodes marked for movement to the next level
            for node in nodes_to_move:
                node.graph_level += 1
                # print(f"  Moving node {node.name} from level {current_level} to level {next_level}")

            # print(f"Moved nodes at level {current_level} to level {next_level}.")
            update_links(diagram.get_links_from_nodes())
            max_level = diagram.get_max_level()

        max_level = diagram.get_max_level()
        current_level += 1

    # Check all levels starting from the last level
    for level in range(max_level, min_level - 1, -1):
        nodes_at_level = diagram.get_nodes_by_level(level)
        for node in nodes_at_level.values():
            upstream_links = node.get_upstream_links()
            can_move = True
            for link in upstream_links:
                level_diff = node.graph_level - link.target.graph_level
                if level_diff == 1:
                    can_move = False
                    break  # Stop checking if any upstream link has a level difference of 1

            if can_move:
                for link in upstream_links:
                    level_diff = node.graph_level - link.target.graph_level
                    if level_diff > 1:
                        node.graph_level -= 1
                        # print(f"  Moving node {node.name} from level {level} to level {level - 1} due to upstream link with level difference > 1")
                        update_links(diagram.get_links_from_nodes())
                        max_level = diagram.get_max_level()
                        break  # Stop moving the node after adjusting its level once


def update_links(links):
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


def assign_graphlevels(diagram, verbose=False):
    """
    Assigns hierarchical graph levels to nodes based on connections or optional labels
    Returns a sorted list of nodes and their graph levels.
    """
    nodes = diagram.get_nodes()

    # Check if all nodes already have a graphlevel != -1
    if all(node.graph_level != -1 for node in nodes.values()):
        already_set = True
    else:
        already_set = False
        print(
            "Not all graph levels set in the .clab file. Assigning graph levels based on downstream links. Expect experimental output. Please consider assigning graph levels to your .clab file, or use it with -I for interactive mode. Find more information here: https://github.com/srl-labs/clab-io-draw/blob/grafana_style/docs/clab2drawio.md#influencing-node-placement"
        )

    # Helper function to assign graphlevel by recursively checking connections
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

    # Start by setting the graphlevel to -1 if they don't already have a graphlevel
    for node in nodes.values():
        if node.graph_level != -1:
            continue
        # Setting the graphlevel of nodes with no upstream connections
        elif not node.get_upstream_links():
            set_graphlevel(node, 0)
        else:
            set_graphlevel(node, node.graph_level)

    # Update the links of each node
    for node in nodes.values():
        node.update_links()

    if not already_set:
        adjust_node_levels(diagram)
        for node in nodes.values():
            node.update_links()

    sorted_nodes = sorted(
        nodes.values(), key=lambda node: (node.graph_level, node.name)
    )
    return sorted_nodes


def load_styles_from_config(config_path):
    try:
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        error_message = (
            f"Error: The specified config file '{config_path}' does not exist."
        )
        print(error_message)
        exit()
    except Exception as e:
        error_message = f"An error occurred while loading the config: {e}"
        print(error_message)
        exit()

    # Parse the base style into a dictionary
    base_style_dict = {
        item.split("=")[0]: item.split("=")[1]
        for item in config.get("base_style", "").split(";")
        if item
    }

    # Initialize styles dictionary with configuration values
    styles = {
        "background": config.get("background", "#FFFFFF"),
        "shadow": config.get("shadow", "1"),
        "grid": config.get("grid", "1"),
        "pagew": config.get("pagew", "827"),
        "pageh": config.get("pageh", "1169"),
        "base_style": config.get("base_style", ""),
        "link_style": config.get("link_style", ""),
        "src_label_style": config.get("src_label_style", ""),
        "trgt_label_style": config.get("trgt_label_style", ""),
        "port_style": config.get("port_style", ""),
        "connector_style": config.get("connector_style", ""),
        "icon_to_group_mapping": config.get("icon_to_group_mapping", {}),
        "custom_styles": {},
    }

    # Merge base style with custom styles
    for key, custom_style in config.get("custom_styles", {}).items():
        custom_style_dict = {
            item.split("=")[0]: item.split("=")[1]
            for item in custom_style.split(";")
            if item
        }
        merged_style_dict = {
            **base_style_dict,
            **custom_style_dict,
        }  # custom style overrides base style
        merged_style = ";".join(f"{k}={v}" for k, v in merged_style_dict.items())
        styles["custom_styles"][key] = merged_style

    # Read all other configuration values
    for key, value in config.items():
        if key not in styles:
            styles[key] = value

    return styles


def interactive_mode(
    nodes, icon_to_group_mapping, containerlab_data, output_file, processor
):
    # Initialize previous summary with existing node labels
    previous_summary = {"Levels": {}, "Icons": {}}
    for node_name, node in nodes.items():
        try:
            level = node.graph_level
            previous_summary["Levels"].setdefault(level, []).append(node_name)

            icon = node.graph_icon
            previous_summary["Icons"].setdefault(icon, []).append(node_name)
        except AttributeError:
            continue

    while True:
        summary = {"Levels": {}, "Icons": {}}
        tmp_nodes = list(nodes.keys())
        level = 0

        # Assign levels to nodes
        while tmp_nodes:
            level += 1
            valid_nodes = [(node, node) for node in tmp_nodes]
            if valid_nodes:
                level_nodes = checkboxlist_dialog(
                    title=f"Level {level} nodes",
                    text=f"Choose the nodes for level {level}:",
                    values=valid_nodes,
                    default_values=previous_summary["Levels"].get(level, []),
                ).run()
            else:
                break

            if level_nodes is None:
                return  # Exit the function if cancel button is clicked

            if len(level_nodes) == 0:
                continue

            # Update node labels and summary with assigned levels
            for node_name in level_nodes:
                nodes[node_name].graph_level = level
                summary["Levels"].setdefault(level, []).append(node_name)
                tmp_nodes.remove(node_name)

                # Check if 'labels' section exists, create it if necessary
                if "labels" not in containerlab_data["topology"]["nodes"][node_name]:
                    containerlab_data["topology"]["nodes"][node_name]["labels"] = {}

                # Update containerlab_data with graph-level
                containerlab_data["topology"]["nodes"][node_name]["labels"][
                    "graph-level"
                ] = level

        tmp_nodes = list(nodes.keys())
        icons = list(icon_to_group_mapping.keys())

        # Assign icons to nodes
        for icon in icons:
            valid_nodes = [(node, node) for node in tmp_nodes]
            if valid_nodes:
                icon_nodes = checkboxlist_dialog(
                    title=f"Choose {icon} nodes",
                    text=f"Select the nodes for the {icon} icon:",
                    values=valid_nodes,
                    default_values=previous_summary["Icons"].get(icon, []),
                ).run()
            else:
                icon_nodes = []

            if icon_nodes is None:
                return  # Exit the function if cancel button is clicked

            if not icon_nodes:
                continue

            # Update node labels and summary with assigned icons
            for node_name in icon_nodes:
                nodes[node_name].graph_icon = icon
                summary["Icons"].setdefault(icon, []).append(node_name)
                tmp_nodes.remove(node_name)

                # Check if 'labels' section exists, create it if necessary
                if "labels" not in containerlab_data["topology"]["nodes"][node_name]:
                    containerlab_data["topology"]["nodes"][node_name]["labels"] = {}

                # Update containerlab_data with graph-icon
                containerlab_data["topology"]["nodes"][node_name]["labels"][
                    "graph-icon"
                ] = icon

        # Generate summary tree with combined levels and icons
        summary_tree = ""
        for level, node_list in summary["Levels"].items():
            summary_tree += f"Level {level}: "
            node_items = []
            # Calculate the indentation based on "Level {level}: "
            indent = " " * (len(f"Level {level}: "))
            for i, node in enumerate(node_list, start=1):
                icon = nodes[node].graph_icon
                # Append the node and its icon to the node_items list
                node_items.append(f"{node} ({icon})")
                if i % 3 == 0 and i < len(node_list):
                    node_items.append("\n" + indent)
            # Join the node items, now including the newline and indentation at the correct position
            summary_tree += ", ".join(node_items).replace(indent + ", ", indent) + "\n"
        summary_tree += "\nDo you want to keep it like this? Select < No > to edit your configuration."

        # Prompt user for confirmation
        result = yes_no_dialog(title="SUMMARY", text=summary_tree).run()

        if result is None:
            return  # Exit the function if cancel button is clicked
        elif result:
            break  # Exit the loop if user confirms the summary

    # Prompt user if they want to update the ContainerLab file
    update_file = yes_no_dialog(
        title="Update ContainerLab File",
        text="Do you want to save a new ContainerLab file with the new configuration?",
    ).run()

    if update_file:
        # Save the updated containerlab_data to the output file using processor.save_yaml
        modified_output_file = os.path.splitext(output_file)[0] + ".mod.yaml"
        processor.save_yaml(containerlab_data, modified_output_file)
        print(f"ContainerLab file has been updated: {modified_output_file}")
    else:
        print("ContainerLab file has not been updated.")

    return summary


def format_node_name(base_name, prefix, lab_name):
    if prefix == "":
        return base_name
    elif prefix == "clab" and not prefix:
        return f"clab-{lab_name}-{base_name}"
    else:
        return f"{prefix}-{lab_name}-{base_name}"


def main(
    input_file,
    output_file,
    grafana,
    theme,
    include_unlinked_nodes=False,
    no_links=False,
    layout="vertical",
    verbose=False,
    interactive=False,
):
    """
    Generates a diagram from a given topology definition file, organizing and displaying nodes and links.

    Processes an input YAML file containing node and link definitions, extracts relevant information,
    and applies logic to determine node positions and connectivity. The function supports filtering out unlinked nodes,
    optionally excluding links, choosing the layout orientation, and toggling verbose output for detailed processing logs.
    """
    try:
        with open(input_file, "r") as file:
            containerlab_data = yaml.safe_load(file)
    except FileNotFoundError:
        error_message = f"Error: The specified clab file '{input_file}' does not exist."
        print(error_message)
        exit()
    except Exception as e:
        error_message = f"An error occurred while loading the config: {e}"
        print(error_message)
        exit()

    if theme in ["nokia_bright", "nokia_dark", "grafana_dark"]:
        config_path = os.path.join(script_dir, f"styles/{theme}.yaml")
    else:
        # Assume the user has provided a custom path
        config_path = theme

    # Load styles
    styles = load_styles_from_config(config_path)

    diagram = CustomDrawioDiagram()
    diagram.layout = layout

    nodes_from_clab = containerlab_data["topology"]["nodes"]
    # Determine the prefix
    prefix = containerlab_data.get("prefix", "clab")
    lab_name = containerlab_data.get("name", "")

    nodes = {}
    for node_name, node_data in nodes_from_clab.items():
        formatted_node_name = format_node_name(node_name, prefix, lab_name)

        node = Node(
            name=formatted_node_name,
            label=node_name,
            kind=node_data.get("kind", ""),
            mgmt_ipv4=node_data.get("mgmt_ipv4", ""),
            graph_level=node_data.get("labels", {}).get("graph-level", None),
            graph_icon=node_data.get("labels", {}).get("graph-icon", None),
            base_style=styles.get("base_style", ""),
            custom_style=styles.get(node_data.get("kind", ""), ""),
            pos_x=node_data.get("pos_x", ""),
            pos_y=node_data.get("pos_y", ""),
            width=styles.get("node_width", 75),
            height=styles.get("node_height", 75),
            group=node_data.get("group", ""),
        )
        nodes[formatted_node_name] = node

    diagram.nodes = nodes

    # Prepare the links list by extracting source and target from each link's 'endpoints'
    links_from_clab = []
    for link in containerlab_data["topology"].get("links", []):
        endpoints = link.get("endpoints")
        if endpoints:
            source_node, source_intf = endpoints[0].split(":")
            target_node, target_intf = endpoints[1].split(":")

            source_node = format_node_name(source_node, prefix, lab_name)
            target_node = format_node_name(target_node, prefix, lab_name)

            # Add link only if both source and target nodes exist
            if source_node in nodes and target_node in nodes:
                links_from_clab.append(
                    {
                        "source": source_node,
                        "target": target_node,
                        "source_intf": source_intf,
                        "target_intf": target_intf,
                    }
                )
    # Create Link instances and attach them to nodes
    links = []
    for link_data in links_from_clab:
        source_node = nodes.get(link_data["source"])
        target_node = nodes.get(link_data["target"])

        if source_node and target_node:
            # Create two links, one for downstream and one for upstream
            downstream_link = Link(
                source=source_node,
                target=target_node,
                source_intf=link_data.get("source_intf", ""),
                target_intf=link_data.get("target_intf", ""),
                base_style=styles.get("base_style", ""),
                link_style=styles.get("link_style", ""),
                src_label_style=styles.get("src_label_style", ""),
                trgt_label_style=styles.get("trgt_label_style", ""),
                entryY=link_data.get("entryY", 0),
                exitY=link_data.get("exitY", 0),
                entryX=link_data.get("entryX", 0),
                exitX=link_data.get("exitX", 0),
                direction="downstream",  # Set the direction to downstream
            )
            upstream_link = Link(
                source=target_node,
                target=source_node,
                source_intf=link_data.get("target_intf", ""),
                target_intf=link_data.get("source_intf", ""),
                base_style=styles.get("base_style", ""),
                link_style=styles.get("link_style", ""),
                src_label_style=styles.get("src_label_style", ""),
                trgt_label_style=styles.get("trgt_label_style", ""),
                entryY=link_data.get("entryY", 0),
                exitY=link_data.get("exitY", 0),
                entryX=link_data.get("entryX", 0),
                exitX=link_data.get("exitX", 0),
                direction="upstream",  # Set the direction to upstream
            )
            links.append(downstream_link)
            links.append(upstream_link)

            # Add the links to the source and target nodes
            source_node.add_link(downstream_link)
            target_node.add_link(upstream_link)

    if not include_unlinked_nodes:
        connected_nodes = {name: node for name, node in nodes.items() if node.links}
        diagram.nodes = connected_nodes
        nodes = diagram.nodes
    else:
        diagram.nodes = nodes

    if interactive:
        processor = YAMLProcessor()
        interactive_mode(
            diagram.nodes,
            styles["icon_to_group_mapping"],
            containerlab_data,
            input_file,
            processor,
        )

    assign_graphlevels(diagram, verbose=False)
    calculate_positions(diagram, layout=layout, verbose=verbose)

    # Calculate the diagram size based on the positions of the nodes
    min_x = min(node.pos_x for node in nodes.values())
    min_y = min(node.pos_y for node in nodes.values())
    max_x = max(node.pos_x for node in nodes.values())
    max_y = max(node.pos_y for node in nodes.values())

    # Determine the necessary adjustments
    adjust_x = -min_x + 100  # Adjust so the minimum x is at least 100
    adjust_y = -min_y + 100  # Adjust so the minimum y is at least 100

    # Apply adjustments to each node's position
    for node in nodes.values():
        node.pos_x += adjust_x
        node.pos_y += adjust_y

    # Recalculate diagram size if necessary, after adjustment
    max_x = max(node.pos_x for node in nodes.values())
    max_y = max(node.pos_y for node in nodes.values())

    max_size_x = max_x + 100  # Adding a margin to the right side
    max_size_y = max_y + 100  # Adding a margin to the bottom

    if styles["pagew"] == "auto":
        styles["pagew"] = max_size_x
    if styles["pageh"] == "auto":
        styles["pageh"] = max_size_y

    diagram.update_style(styles)

    diagram.add_diagram("Network Topology")

    add_nodes(diagram, diagram.nodes, styles)

    if grafana:
        add_ports(diagram, styles)
        if not output_file:
            grafana_output_file = os.path.splitext(input_file)[0] + ".grafana.json"
        output_folder = os.path.dirname(grafana_output_file) or "."
        output_filename = os.path.basename(grafana_output_file)
        diagram.grafana_dashboard_file = grafana_output_file
        os.makedirs(output_folder, exist_ok=True)
        grafana = GrafanaDashboard(diagram)
        grafana_json = grafana.create_dashboard()
        # dump the json to the file
        with open(grafana_output_file, "w") as f:
            f.write(grafana_json)
        print("Saved file to:", grafana_output_file)
    else:
        add_links(diagram, styles)

    # If output_file is not provided, generate it from input_file
    if not output_file:
        output_file = os.path.splitext(input_file)[0] + ".drawio"

    output_folder = os.path.dirname(output_file) or "."
    output_filename = os.path.basename(output_file)
    os.makedirs(output_folder, exist_ok=True)

    diagram.dump_file(filename=output_filename, folder=output_folder)

    print("Saved file to:", output_file)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Generate a topology diagram from a containerlab YAML or draw.io XML file."
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="The filename of the input file (containerlab YAML for diagram generation).",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=False,
        help="The output file path for the generated diagram (draw.io format).",
    )
    parser.add_argument(
        "-g",
        "--gf_dashboard",
        action="store_true",
        required=False,
        help="Generate Grafana Dashboard Flag.",
    )
    parser.add_argument(
        "--include-unlinked-nodes",
        action="store_true",
        help="Include nodes without any links in the topology diagram",
    )
    parser.add_argument(
        "--no-links",
        action="store_true",
        help="Do not draw links between nodes in the topology diagram",
    )
    parser.add_argument(
        "--layout",
        type=str,
        default="vertical",
        choices=["vertical", "horizontal"],
        help="Specify the layout of the topology diagram (vertical or horizontal)",
    )
    parser.add_argument(
        "--theme",
        default="nokia_bright",
        help="Specify the theme for the diagram (nokia_bright, nokia_dark, grafana_dark) or the path to a custom style config file.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output for debugging purposes",
    )
    parser.add_argument(
        "-I",
        "--interactive",
        action="store_true",
        required=False,
        help="Define graph-levels and graph-icons in interactive mode",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    script_dir = os.path.dirname(__file__)

    main(
        args.input,
        args.output,
        args.gf_dashboard,
        args.theme,
        args.include_unlinked_nodes,
        args.no_links,
        args.layout,
        args.verbose,
        args.interactive,
    )
