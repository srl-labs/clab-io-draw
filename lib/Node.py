class Node:
    def __init__(
        self,
        name,
        label,
        kind,
        mgmt_ipv4=None,
        graph_level=None,
        graph_icon=None,
        **kwargs,
    ):
        self.name = name
        self.label = label
        self.kind = kind
        self.mgmt_ipv4 = mgmt_ipv4
        self.graph_level = graph_level if graph_level is not None else -1
        self.graph_icon = graph_icon
        self.links = []
        self.categories = []
        self.properties = kwargs
        self.base_style = kwargs.get("base_style", "")
        self.custom_style = kwargs.get("custom_style", "")
        self.pos_x = kwargs.get("pos_x", "")
        self.pos_y = kwargs.get("pos_y", "")
        self.width = kwargs.get("width", "")
        self.height = kwargs.get("height", "")
        self.group = kwargs.get("group", "")

    def add_link(self, link):
        self.links.append(link)

    def remove_link(self, link):
        self.upstream_links.remove(link)

    def get_connection_count(self):
        return len(self.links)

    def get_connection_count_within_level(self):
        return len(
            [
                link
                for link in self.links
                if link.source.graph_level == self.graph_level
                or link.target.graph_level == self.graph_level
            ]
        )

    def get_downstream_links(self):
        return [link for link in self.links if link.direction == "downstream"]

    def get_upstream_links(self):
        return [link for link in self.links if link.direction == "upstream"]

    def get_upstream_links_towards_level(self, level):
        return [
            link
            for link in self.links
            if link.direction == "upstream" and link.target.graph_level == level
        ]

    def get_lateral_links(self):
        return [link for link in self.links if link.direction == "lateral"]

    def get_all_links(self):
        return self.links

    def get_neighbors(self):
        neighbors = set()
        for link in self.get_all_links():
            if link.source == self.name:
                neighbors.add(link.target)
            else:
                neighbors.add(link.source)
        return list(neighbors)

    def is_connected_to(self, node):
        for link in self.links:
            if link.source == node or link.target == node:
                return True
        return False

    def set_base_style(self, style):
        self.base_style = style

    def set_custom_style(self, style):
        self.custom_style = style

    def generate_style_string(self):
        style = f"{self.base_style}{self.custom_style}"
        style += f"pos_x={self.pos_x};pos_y={self.pos_y};"
        style += f"width={self.width};height={self.height};"
        return style

    def update_links(self):
        for link in self.links:
            source_level = link.source.graph_level
            target_level = link.target.graph_level
            link.level_diff = target_level - source_level
            if link.level_diff > 0:
                link.direction = "downstream"
            elif link.level_diff < 0:
                link.direction = "upstream"
            else:
                link.direction = "lateral"

    def __repr__(self):
        return f"Node(name='{self.name}', kind='{self.kind}')"
