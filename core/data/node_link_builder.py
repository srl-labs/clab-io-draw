from core.models.node import Node
from core.models.link import Link

class NodeLinkBuilder:
    def __init__(self, containerlab_data, styles, prefix, lab_name):
        self.containerlab_data = containerlab_data
        self.styles = styles
        self.prefix = prefix
        self.lab_name = lab_name

    def format_node_name(self, base_name):
        if self.prefix == "":
            return base_name
        elif self.prefix == "clab" and not self.prefix:
            return f"clab-{self.lab_name}-{base_name}"
        else:
            return f"{self.prefix}-{self.lab_name}-{base_name}"

    def build_nodes_and_links(self):
        nodes = self._build_nodes()
        links = self._build_links(nodes)
        return nodes, links

    def _build_nodes(self):
        nodes_from_clab = self.containerlab_data["topology"]["nodes"]

        node_width = self.styles.get("node_width", 75)
        node_height = self.styles.get("node_height", 75)
        base_style = self.styles.get("base_style", "")

        nodes = {}
        for node_name, node_data in nodes_from_clab.items():
            formatted_node_name = self.format_node_name(node_name)
            node = Node(
                name=formatted_node_name,
                label=node_name,
                kind=node_data.get("kind", ""),
                mgmt_ipv4=node_data.get("mgmt_ipv4", ""),
                graph_level=node_data.get("labels", {}).get("graph-level", None),
                graph_icon=node_data.get("labels", {}).get("graph-icon", None),
                base_style=base_style,
                custom_style=self.styles.get(node_data.get("kind", ""), ""),
                pos_x=node_data.get("pos_x", ""),
                pos_y=node_data.get("pos_y", ""),
                width=node_width,
                height=node_height,
                group=node_data.get("group", ""),
            )
            nodes[formatted_node_name] = node

        return nodes

    def _build_links(self, nodes):
        links_from_clab = []
        for link in self.containerlab_data["topology"].get("links", []):
            endpoints = link.get("endpoints")
            if endpoints:
                source_node, source_intf = endpoints[0].split(":")
                target_node, target_intf = endpoints[1].split(":")

                source_node = self.format_node_name(source_node)
                target_node = self.format_node_name(target_node)

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
                    entryY=link_data.get("entryY", 0),
                    exitY=link_data.get("exitY", 0),
                    entryX=link_data.get("entryX", 0),
                    exitX=link_data.get("exitX", 0),
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
                    entryY=link_data.get("entryY", 0),
                    exitY=link_data.get("exitY", 0),
                    entryX=link_data.get("entryX", 0),
                    exitX=link_data.get("exitX", 0),
                    direction="upstream",
                )
                links.append(downstream_link)
                links.append(upstream_link)

                # Add the links to the source and target nodes
                source_node.add_link(downstream_link)
                target_node.add_link(upstream_link)

        return links
