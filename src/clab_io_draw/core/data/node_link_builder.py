import logging

from clab_io_draw.core.models.link import Link
from clab_io_draw.core.models.node import Node

logger = logging.getLogger(__name__)


class NodeLinkBuilder:
    """
    Builds Node and Link objects from containerlab topology data and styling information.
    """

    def __init__(
        self, containerlab_data: dict, styles: dict, prefix: str, lab_name: str
    ):
        """
        :param containerlab_data: Parsed containerlab topology data.
        :param styles: Dictionary of style parameters.
        :param prefix: Prefix used in node names.
        :param lab_name: Name of the lab.
        """
        self.containerlab_data = containerlab_data
        self.styles = styles
        self.prefix = prefix
        self.lab_name = lab_name
        self.annotations = containerlab_data.get("annotations")

        # Pre-build annotation maps for quick lookup later
        self._node_annotations = {}
        self._cloud_annotations = {}
        if self.annotations:
            for ann in self.annotations.get("nodeAnnotations", []):
                self._node_annotations[ann.get("id")] = ann
            for ann in self.annotations.get("cloudNodeAnnotations", []):
                self._cloud_annotations[ann.get("id")] = ann

    def format_node_name(self, base_name: str) -> str:
        """
        Format node name with given prefix and lab_name.

        :param base_name: Original node name from containerlab data.
        :return: Formatted node name string.
        """
        if self.prefix == "":
            return base_name
        if self.prefix == "clab" and not self.prefix:
            return f"clab-{self.lab_name}-{base_name}"
        return f"{self.prefix}-{self.lab_name}-{base_name}"

    def build_nodes_and_links(self):
        """
        Build Node and Link objects from the provided containerlab data.

        :return: A tuple (nodes_dict, links_list)
        """
        logger.debug("Building nodes...")
        nodes = self._build_nodes()
        logger.debug("Building links...")
        links = self._build_links(nodes)
        return nodes, links

    def _build_nodes(self):
        """
        Internal method to build Node instances from containerlab topology data.

        :return: Dictionary of node_name -> Node
        """
        nodes_from_clab = self.containerlab_data["topology"]["nodes"]

        node_width = self.styles.get("node_width", 75)
        node_height = self.styles.get("node_height", 75)
        base_style = self.styles.get("base_style", "")

        nodes = {}
        for node_name, node_data in nodes_from_clab.items():
            formatted_node_name = self.format_node_name(node_name)

            # Initialize default values
            pos_x = node_data.get("pos_x", "")
            pos_y = node_data.get("pos_y", "")
            graph_icon = None
            graph_level = None

            # First check labels (lower priority)
            labels = node_data.get("labels", {})
            if "graph-posX" in labels:
                pos_x = labels["graph-posX"]
            if "graph-posY" in labels:
                pos_y = labels["graph-posY"]
            if "graph-icon" in labels:
                graph_icon = labels["graph-icon"]
            if "graph-level" in labels:
                graph_level = labels["graph-level"]

            # Then check annotations (higher priority - overrides labels)
            if node_name in self._node_annotations:
                annotation = self._node_annotations[node_name]
                if "position" in annotation:
                    pos_x = str(annotation["position"]["x"])
                    pos_y = str(annotation["position"]["y"])
                if "icon" in annotation:
                    graph_icon = annotation["icon"]
                # Note: graph-level could be added to annotations if needed

            node = Node(
                name=formatted_node_name,
                label=node_name,
                kind=node_data.get("kind", ""),
                mgmt_ipv4=node_data.get("mgmt_ipv4", ""),
                graph_level=graph_level,
                graph_icon=graph_icon,
                base_style=base_style,
                custom_style=self.styles.get(node_data.get("kind", ""), ""),
                pos_x=pos_x,
                pos_y=pos_y,
                width=node_width,
                height=node_height,
                group=node_data.get("group", ""),
            )
            nodes[formatted_node_name] = node

        return nodes

    def _parse_endpoint(self, endpoint):
        """Extract node and interface information from an endpoint.

        :param endpoint: Endpoint definition which may be a string in the
            ``node:interface`` format or a dict with ``node`` and ``interface``
            keys.
        :return: Tuple of (node, interface) or (None, None) if parsing fails.
        """
        if isinstance(endpoint, str):
            parts = endpoint.split(":", 1)
            if parts:
                return parts[0], parts[1] if len(parts) > 1 else ""
        elif isinstance(endpoint, dict):
            return endpoint.get("node"), endpoint.get("interface")
        return None, None

    def _create_network_node(self, name: str) -> Node:
        """Create a Node instance representing a network endpoint.

        If annotations include cloud node information for this endpoint, use the
        stored position and label.
        """

        label = name
        pos_x = ""
        pos_y = ""
        annotation = self._cloud_annotations.get(name)
        if annotation:
            label = annotation.get("label", name)
            pos = annotation.get("position")
            if pos:
                pos_x = str(pos.get("x", ""))
                pos_y = str(pos.get("y", ""))

        return Node(
            name=name,
            label=label,
            kind="network",
            graph_icon="network",
            base_style=self.styles.get("base_style", ""),
            custom_style=self.styles.get("custom_styles", {}).get("network", ""),
            width=self.styles.get("node_width", 75),
            height=self.styles.get("node_height", 75),
            pos_x=pos_x,
            pos_y=pos_y,
        )

    def _build_links(self, nodes):
        """
        Internal method to build Link instances and attach them to their respective nodes.

        :param nodes: Dictionary of node_name -> Node
        :return: List of Link objects
        """
        links_from_clab = []
        defined_nodes = set(self.containerlab_data["topology"].get("nodes", {}).keys())
        dummy_count = 0

        for link in self.containerlab_data["topology"].get("links", []):
            endpoints = link.get("endpoints")
            if endpoints and len(endpoints) == 2:
                src_raw, src_intf = self._parse_endpoint(endpoints[0])
                trgt_raw, trgt_intf = self._parse_endpoint(endpoints[1])

                if src_raw and trgt_raw:
                    if src_raw in defined_nodes:
                        src_name = self.format_node_name(src_raw)
                    else:
                        src_name = f"{src_raw}:{src_intf}" if src_intf else src_raw
                        if src_name not in nodes:
                            nodes[src_name] = self._create_network_node(src_name)

                    if trgt_raw in defined_nodes:
                        trgt_name = self.format_node_name(trgt_raw)
                    else:
                        trgt_name = f"{trgt_raw}:{trgt_intf}" if trgt_intf else trgt_raw
                        if trgt_name not in nodes:
                            nodes[trgt_name] = self._create_network_node(trgt_name)

                    links_from_clab.append(
                        {
                            "source": src_name,
                            "target": trgt_name,
                            "source_intf": src_intf or "",
                            "target_intf": trgt_intf or "",
                        }
                    )
            elif link.get("endpoint"):
                # Special link types with a single endpoint
                endpoint = link.get("endpoint")
                src_raw, src_intf = self._parse_endpoint(endpoint)
                if not src_raw:
                    continue

                link_type = link.get("type", "network")
                if link_type == "host":
                    trgt_name = f"host:{link.get('host-interface', '')}"
                elif link_type == "vxlan":
                    trgt_name = f"vxlan:{link.get('remote')}/{link.get('vni')}/{link.get('udp-port')}"
                elif link_type == "vxlan-stitch":
                    trgt_name = f"vxlan-stitch:{link.get('remote')}/{link.get('vni')}/{link.get('udp-port')}"
                elif link_type == "dummy":
                    dummy_count += 1
                    trgt_name = f"dummy{dummy_count}"
                else:
                    trgt_name = link_type

                if src_raw in defined_nodes:
                    src_name = self.format_node_name(src_raw)
                else:
                    src_name = src_raw
                    if src_name not in nodes:
                        nodes[src_name] = self._create_network_node(src_name)

                if trgt_name not in nodes:
                    nodes[trgt_name] = self._create_network_node(trgt_name)

                links_from_clab.append(
                    {
                        "source": src_name,
                        "target": trgt_name,
                        "source_intf": src_intf or "",
                        "target_intf": "",
                    }
                )

        links = []
        for link_data in links_from_clab:
            source_node = nodes.get(link_data["source"])
            target_node = nodes.get(link_data["target"])

            if source_node and target_node:
                downstream_link = Link(
                    source=source_node,
                    target=target_node,
                    source_intf=link_data.get("source_intf", ""),
                    target_intf=link_data.get("target_intf", ""),
                    base_style=self.styles.get("base_style", ""),
                    link_style=self.styles.get("link_style", ""),
                    src_label_style=self.styles.get("src_label_style", ""),
                    trgt_label_style=self.styles.get("trgt_label_style", ""),
                    direction="downstream",
                )
                upstream_link = Link(
                    source=target_node,
                    target=source_node,
                    source_intf=link_data.get("target_intf", ""),
                    target_intf=link_data.get("source_intf", ""),
                    base_style=self.styles.get("base_style", ""),
                    link_style=self.styles.get("link_style", ""),
                    src_label_style=self.styles.get("src_label_style", ""),
                    trgt_label_style=self.styles.get("trgt_label_style", ""),
                    direction="upstream",
                )
                links.append(downstream_link)
                links.append(upstream_link)

                # Attach links to nodes
                source_node.add_link(downstream_link)
                target_node.add_link(upstream_link)

        return links
