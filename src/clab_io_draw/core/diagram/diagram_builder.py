import logging
import math
import re

from clab_io_draw.core.diagram.anchor_planner import (
    AnchorPlanner,
    compact_interface_name,
    label_dimensions,
)

logger = logging.getLogger(__name__)


class DiagramBuilder:
    """
    Builds diagram elements such as nodes, ports, and links into the Draw.io diagram.
    """

    def get_intf_digit(self, intf_name, styles):
        interface_selector = styles.get("grafana_interface_selector")
        if interface_selector:
            regex_pattern = interface_selector.replace("{x}", r"(\d+)")

            try:
                match = re.match(f"^{regex_pattern}$", intf_name)
                if match:
                    return match.group(1)
            except re.error as e:
                logger.warning(f"Invalid pattern for grafana_interface_selector: {e}")

        # fallback to default
        digits = re.findall(r"\d+", intf_name)
        return digits[-1] if digits else "0"

    def add_ports(self, diagram, styles, _verbose=True):
        """
        Add ports and their connections to the diagram.

        :param diagram: CustomDrawioDiagram instance.
        :param styles: Styles dictionary.
        :param verbose: Enable verbose output.
        """
        logger.debug("Adding ports to nodes...")
        nodes = diagram.nodes
        AnchorPlanner(styles).assign(diagram)

        # Create connectors and midpoint connectors
        connector_dict = {}
        processed_connections = set()
        for node in nodes.values():
            downstream_links = node.get_downstream_links()
            lateral_links = node.get_lateral_links()
            node_links = downstream_links + lateral_links

            for link in node_links:
                connection_id = frozenset(
                    {
                        (link.source.name, link.source_intf),
                        (link.target.name, link.target_intf),
                    }
                )
                if connection_id not in processed_connections:
                    processed_connections.add(connection_id)
                    source_cID = (
                        f"{link.source.name}:{link.source_intf}:"
                        f"{link.target.name}:{link.target_intf}"
                    )
                    source_label = self.get_intf_digit(link.source_intf, styles)
                    source_connector_pos = link.port_pos
                    port_width = styles["port_width"]
                    port_height = styles["port_height"]

                    if link.source.name not in connector_dict:
                        connector_dict[link.source.name] = []
                    connector_dict[link.source.name].append(source_cID)

                    target_cID = (
                        f"{link.target.name}:{link.target_intf}:"
                        f"{link.source.name}:{link.source_intf}"
                    )
                    target_link = diagram.get_target_link(link)
                    target_connector_pos = target_link.port_pos
                    target_label = self.get_intf_digit(target_link.source_intf, styles)

                    if link.target.name not in connector_dict:
                        connector_dict[link.target.name] = []
                    connector_dict[link.target.name].append(target_cID)

                    # Adjust port positions if mismatch
                    source_downstream_links = link.source.get_downstream_links()
                    target_upstream_links = link.target.get_upstream_links()
                    if (
                        diagram.layout == "vertical"
                        and link.source.pos_x == link.target.pos_x
                        and len(source_downstream_links) != len(target_upstream_links)
                    ):
                        if len(source_downstream_links) < len(target_upstream_links):
                            adjusted_x = target_connector_pos[0]
                            source_connector_pos = (adjusted_x, source_connector_pos[1])
                        else:
                            adjusted_x = source_connector_pos[0]
                            target_connector_pos = (adjusted_x, target_connector_pos[1])
                    elif (
                        diagram.layout == "horizontal"
                        and link.source.pos_y == link.target.pos_y
                        and len(source_downstream_links) != len(target_upstream_links)
                    ):
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

                    dx = target_center[0] - source_center[0]
                    dy = target_center[1] - source_center[1]
                    magnitude = (dx**2 + dy**2) ** 0.5
                    if magnitude != 0:
                        normal_dx = -dy / magnitude
                        normal_dy = dx / magnitude
                    else:
                        normal_dx = 0
                        normal_dy = 0

                    parallel_offset = getattr(link, "parallel_offset", 0)
                    midpoint_center_x += normal_dx * parallel_offset
                    midpoint_center_y += normal_dy * parallel_offset

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
        AnchorPlanner(styles).assign(diagram)

        def format_interface_name(intf_name):
            return compact_interface_name(intf_name, styles)

        # Configure font size for labels
        src_label_style = styles.get("src_label_style", "")
        trgt_label_style = styles.get("trgt_label_style", "")
        labels_by_node: dict[str, list[str]] = {}

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
                tgt = link.target
                target_groups.setdefault(tgt, []).append(link)

            for _tgt, group in target_groups.items():
                for link in group:
                    target_link = diagram.get_target_link(link)
                    entryX, entryY, exitX, exitY = (
                        self._calculate_entry_exit_for_fixed_layout(link)
                    )
                    if hasattr(link, "edge_exit"):
                        exitX, exitY = link.edge_exit

                    if target_link is not None and hasattr(target_link, "edge_exit"):
                        entryX, entryY = target_link.edge_exit

                    style = f"{styles['link_style']}entryY={entryY};exitY={exitY};entryX={entryX};exitX={exitX};"

                    link_id = f"link:{link.source.name}:{link.source_intf}:{link.target.name}:{link.target_intf}"
                    source_label_id = f"label:{link_id}:src"
                    target_label_id = f"label:{link_id}:trgt"

                    if not styles.get("default_labels", False):
                        source_label = format_interface_name(link.source_intf)
                        target_label = format_interface_name(link.target_intf)
                        source_label_w, source_label_h = label_dimensions(
                            source_label, styles
                        )
                        target_label_w, target_label_h = label_dimensions(
                            target_label, styles
                        )

                        (
                            (source_label_x, source_label_y),
                            (target_label_x, target_label_y),
                        ) = self._calculate_link_label_positions(
                            link=link,
                            entryX=entryX,
                            entryY=entryY,
                            exitX=exitX,
                            exitY=exitY,
                            source_size=(source_label_w, source_label_h),
                            target_size=(target_label_w, target_label_h),
                            styles=styles,
                        )

                        diagram.add_link(
                            link_id=link_id,
                            source=link.source.name,
                            target=link.target.name,
                            style=style,
                        )

                        diagram.add_node(
                            id=source_label_id,
                            label=source_label,
                            x_pos=source_label_x,
                            y_pos=source_label_y,
                            width=source_label_w,
                            height=source_label_h,
                            style=src_label_style,
                        )

                        diagram.add_node(
                            id=target_label_id,
                            label=target_label,
                            x_pos=target_label_x,
                            y_pos=target_label_y,
                            width=target_label_w,
                            height=target_label_h,
                            style=trgt_label_style,
                        )
                        labels_by_node.setdefault(link.source.name, []).append(
                            source_label_id
                        )
                        labels_by_node.setdefault(link.target.name, []).append(
                            target_label_id
                        )
                    else:
                        diagram.add_link(
                            link_id=link_id,
                            source=link.source.name,
                            target=link.target.name,
                            src_label=format_interface_name(link.source_intf),
                            trgt_label=format_interface_name(link.target_intf),
                            src_label_style=src_label_style,
                            trgt_label_style=trgt_label_style,
                            style=style,
                        )

        for node_name, label_ids in labels_by_node.items():
            diagram.parent_labels_to_node(node_name, label_ids)

    def _calculate_link_label_positions(
        self,
        link,
        entryX,
        entryY,
        exitX,
        exitY,
        source_size,
        target_size,
        styles,
    ):
        source_x, source_y = self._anchor_point(link.source, exitX, exitY)
        target_x, target_y = self._anchor_point(link.target, entryX, entryY)

        dx = target_x - source_x
        dy = target_y - source_y
        magnitude = math.hypot(dx, dy)
        if magnitude == 0:
            return link.get_label_positions(entryX, entryY, exitX, exitY, styles)

        normal_x = -dy / magnitude
        normal_y = dx / magnitude
        line_offset = float(styles.get("label_line_offset", 0))
        source_t = float(styles.get("source_label_position", 0.32))
        target_t = float(styles.get("target_label_position", 0.68))

        source_center = (
            source_x + dx * source_t + normal_x * line_offset,
            source_y + dy * source_t + normal_y * line_offset,
        )
        target_center = (
            source_x + dx * target_t + normal_x * line_offset,
            source_y + dy * target_t + normal_y * line_offset,
        )

        return (
            (
                source_center[0] - source_size[0] / 2,
                source_center[1] - source_size[1] / 2,
            ),
            (
                target_center[0] - target_size[0] / 2,
                target_center[1] - target_size[1] / 2,
            ),
        )

    def _anchor_point(self, node, rel_x, rel_y):
        return (
            float(node.pos_x) + float(node.width) * float(rel_x),
            float(node.pos_y) + float(node.height) * float(rel_y),
        )

    def _calculate_entry_exit_for_fixed_layout(self, link):
        """
        Calculate appropriate entry and exit points for links between nodes with fixed positions.
        Returns (entryX, entryY, exitX, exitY) tuple.
        """
        source = link.source
        target = link.target

        # Calculate center points of nodes
        source_center_x = source.pos_x + source.width / 2
        source_center_y = source.pos_y + source.height / 2
        target_center_x = target.pos_x + target.width / 2
        target_center_y = target.pos_y + target.height / 2

        # Calculate angle between centers
        dx = target_center_x - source_center_x
        dy = target_center_y - source_center_y
        angle_source_to_target = math.atan2(dy, dx)
        angle_target_to_source = math.atan2(-dy, -dx)

        # Determine exit point from source based on angle
        if -math.pi / 4 <= angle_source_to_target <= math.pi / 4:
            # Exit from right of source
            exitX, exitY = 1, 0.5
        elif math.pi / 4 <= angle_source_to_target <= 3 * math.pi / 4:
            # Exit from bottom of source
            exitX, exitY = 0.5, 1
        elif (
            angle_source_to_target >= 3 * math.pi / 4
            or angle_source_to_target <= -3 * math.pi / 4
        ):
            # Exit from left of source
            exitX, exitY = 0, 0.5
        else:
            # Exit from top of source
            exitX, exitY = 0.5, 0

        # Determine entry point to target based on angle
        if -math.pi / 4 <= angle_target_to_source <= math.pi / 4:
            # Enter from right of target
            entryX, entryY = 1, 0.5
        elif math.pi / 4 <= angle_target_to_source <= 3 * math.pi / 4:
            # Enter from bottom of target
            entryX, entryY = 0.5, 1
        elif (
            angle_target_to_source >= 3 * math.pi / 4
            or angle_target_to_source <= -3 * math.pi / 4
        ):
            # Enter from left of target
            entryX, entryY = 0, 0.5
        else:
            # Enter from top of target
            entryX, entryY = 0.5, 0

        return entryX, entryY, exitX, exitY

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

            style = self._apply_node_label_position(
                custom_styles.get(group, base_style),
                node.label_position,
            )
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

    def _apply_node_label_position(self, style, label_position):
        position = str(label_position or "").strip().lower()
        if not position:
            return style

        position_styles = {
            "top": {
                "labelPosition": "center",
                "align": "center",
                "verticalLabelPosition": "top",
                "verticalAlign": "bottom",
            },
            "bottom": {
                "labelPosition": "center",
                "align": "center",
                "verticalLabelPosition": "bottom",
                "verticalAlign": "top",
            },
            "left": {
                "labelPosition": "left",
                "align": "right",
                "verticalLabelPosition": "middle",
                "verticalAlign": "middle",
            },
            "right": {
                "labelPosition": "right",
                "align": "left",
                "verticalLabelPosition": "middle",
                "verticalAlign": "middle",
            },
        }
        overrides = position_styles.get(position)
        if overrides is None:
            return style

        style_dict = self._style_to_dict(style)
        style_dict.update(overrides)
        return self._dict_to_style(style_dict)

    def _style_to_dict(self, style):
        style_dict = {}
        for segment in style.split(";"):
            segment = segment.strip()
            if not segment or "=" not in segment:
                continue
            key, value = segment.split("=", 1)
            style_dict[key] = value
        return style_dict

    def _dict_to_style(self, style_dict):
        return "".join(f"{key}={value};" for key, value in style_dict.items())
