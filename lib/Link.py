class Link:
    def __init__(self, source, target, source_intf=None, target_intf=None, **kwargs):
        self.source = source
        self.target = target
        self.source_intf = source_intf
        self.target_intf = target_intf
        self.direction = kwargs.get('direction', '')
        self.theme = kwargs.get('theme', 'nokia_bright')
        self.base_style = kwargs.get('base_style', '')
        self.link_style = kwargs.get('link_style', '')
        self.src_label_style = kwargs.get('src_label_style', '')
        self.trgt_label_style = kwargs.get('trgt_label_style', '')
        self.entryY = kwargs.get('entryY', 0)
        self.exitY = kwargs.get('exitY', 0)
        self.entryX = kwargs.get('entryX', 0)
        self.exitX = kwargs.get('exitX', 0)

    def set_styles(self, **kwargs):
        self.base_style = kwargs.get('base_style', self.base_style)
        self.link_style = kwargs.get('link_style', self.link_style)
        self.src_label_style = kwargs.get('src_label_style', self.src_label_style)
        self.trgt_label_style = kwargs.get('trgt_label_style', self.trgt_label_style)

    def set_entry_exit_points(self, **kwargs):
        self.entryY = kwargs.get('entryY', self.entryY)
        self.exitY = kwargs.get('exitY', self.exitY)
        self.entryX = kwargs.get('entryX', self.entryX)
        self.exitX = kwargs.get('exitX', self.exitX)

    def generate_style_string(self):
        style = f"{self.base_style}{self.link_style}"
        style += f"entryY={self.entryY};exitY={self.exitY};"
        style += f"entryX={self.entryX};exitX={self.exitX};"
        return style
    
    def __repr__(self):
        return f"Link(source='{self.source}', target='{self.target}')"