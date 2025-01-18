class Link:
    """
    Represents a link between two nodes, including styling and interface labels.
    """

    def __init__(self, source, target, source_intf=None, target_intf=None, **kwargs):
        self.source = source
        self.target = target
        self.source_intf = source_intf
        self.target_intf = target_intf
        self.direction = kwargs.get("direction", "")
        self.theme = kwargs.get("theme", "nokia")
        self.base_style = kwargs.get("base_style", "")
        self.link_style = kwargs.get("link_style", "")
        self.src_label_style = kwargs.get("src_label_style", "")
        self.trgt_label_style = kwargs.get("trgt_label_style", "")
        self.entryY = kwargs.get("entryY", 0)
        self.exitY = kwargs.get("exitY", 0)
        self.entryX = kwargs.get("entryX", 0)
        self.exitX = kwargs.get("exitX", 0)

    def set_styles(self, **kwargs):
        self.base_style = kwargs.get("base_style", self.base_style)
        self.link_style = kwargs.get("link_style", self.link_style)
        self.src_label_style = kwargs.get("src_label_style", self.src_label_style)
        self.trgt_label_style = kwargs.get("trgt_label_style", self.trgt_label_style)

    def set_entry_exit_points(self, **kwargs):
        self.entryY = kwargs.get("entryY", self.entryY)
        self.exitY = kwargs.get("exitY", self.exitY)
        self.entryX = kwargs.get("entryX", self.entryX)
        self.exitX = kwargs.get("exitX", self.exitX)

    def generate_style_string(self):
        style = f"{self.base_style}{self.link_style}"
        style += f"entryY={self.entryY};exitY={self.exitY};"
        style += f"entryX={self.entryX};exitX={self.exitX};"
        return style

    def get_label_positions(self, entryX, entryY, exitX, exitY, styles):
        source_x, source_y = self.source.pos_x, self.source.pos_y
        target_x, target_y = self.target.pos_x, self.target.pos_y
        node_width = styles["node_width"]
        node_height = styles["node_height"]

        source_exit_x = source_x + node_width * exitX
        source_exit_y = source_y + node_height * exitY
        target_entry_x = target_x + node_width * entryX
        target_entry_y = target_y + node_height * entryY

        dx = target_entry_x - source_exit_x
        dy = target_entry_y - source_exit_y
        vector_length = (dx**2 + dy**2) ** 0.5
        unit_dx = dx / vector_length if vector_length != 0 else 0
        unit_dy = dy / vector_length if vector_length != 0 else 0

        label_offset = styles["label_offset"]
        source_label_x = source_exit_x + unit_dx * label_offset
        source_label_y = source_exit_y + unit_dy * label_offset
        target_label_x = target_entry_x - unit_dx * label_offset
        target_label_y = target_entry_y - unit_dy * label_offset

        label_width = styles["label_width"]
        label_height = styles["label_height"]

        if styles["label_alignment"] == "left":
            source_label_x -= label_width + 2
            target_label_x -= label_width + 2
        elif styles["label_alignment"] == "right":
            source_label_x += label_width / 2
            target_label_x += label_width / 2
        elif styles["label_alignment"] == "center":
            source_label_x -= label_width / 2
            target_label_x -= label_width / 2

        source_label_y -= label_height / 2
        target_label_y -= label_height / 2

        return (source_label_x, source_label_y), (target_label_x, target_label_y)

    def __repr__(self):
        return f"Link(source='{self.source.name}', target='{self.target.name}')"
