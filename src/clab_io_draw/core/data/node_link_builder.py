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

    def format_node_name(self, base_name: str) -> str:
        """
        Format node name with given prefix and lab_name.

        :param base_name: Original node name from containerlab data.
        :return: Formatted node name string.
        """
        if self.prefix == "":
            return base_name
        elif self.prefix == "clab" and not self.prefix:
            return f"clab-{self.lab_name}-{base_name}"
        else:
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

            # Extract position from graph-posX and graph-posY labels if available
            pos_x = node_data.get("pos_x", "")
            pos_y = node_data.get("pos_y", "")

            # Check for graph-posX and graph-posY in labels
            labels = node_data.get("labels", {})
            if "graph-posX" in labels:
                pos_x = labels["graph-posX"]
            if "graph-posY" in labels:
                pos_y = labels["graph-posY"]

            node = Node(
                name=formatted_node_name,
                label=node_name,
                kind=node_data.get("kind", ""),
                mgmt_ipv4=node_data.get("mgmt_ipv4", ""),
                graph_level=node_data.get("labels", {}).get("graph-level", None),
                graph_icon=node_data.get("labels", {}).get("graph-icon", None),
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

    def _build_links(self, nodes):
        """
        Internal method to build Link instances and attach them to their respective nodes.

        :param nodes: Dictionary of node_name -> Node
        :return: List of Link objects
        """
        links_from_clab = []
        for link in self.containerlab_data["topology"].get("links", []):
            endpoints = link.get("endpoints")
            if endpoints:
                source_node, source_intf = endpoints[0].split(":")
                target_node, target_intf = endpoints[1].split(":")

                source_node = self.format_node_name(source_node)
                target_node = self.format_node_name(target_node)

                if source_node in nodes and target_node in nodes:
                    links_from_clab.append(
                        {
                            "source": source_node,
                            "target": target_node,
                            "source_intf": source_intf,
                            "target_intf": target_intf,
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
