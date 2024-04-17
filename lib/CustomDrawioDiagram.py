from N2G import drawio_diagram
import xml.etree.ElementTree as ET
class CustomDrawioDiagram(drawio_diagram):
    # Overriding the drawio_diagram_xml with shadow=0
    drawio_diagram_xml = """
    <diagram id="{id}" name="{name}">
      <mxGraphModel dx="{width}" dy="{height}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0" background="#000000">
        <root>
          <mxCell id="0"/>   
          <mxCell id="1" parent="0"/>
        </root>
      </mxGraphModel>
    </diagram>
    """
    
    def __init__(self, styles=None, node_duplicates="skip", link_duplicates="skip"):

        if styles:
            background = styles['background']
            shadow = styles['shadow']
            grid = styles['grid']
            pagew = styles['pagew']
            pageh = styles['pageh']

            self.drawio_diagram_xml = f"""
            <diagram id="{{id}}" name="{{name}}">
            <mxGraphModel dx="{{width}}" dy="{{height}}" grid="{grid}" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{pagew}" pageHeight="{pageh}" math="0" shadow="{shadow}" background="{background}">
                <root>
                <mxCell id="0"/>   
                <mxCell id="1" parent="0"/>
                </root>
            </mxGraphModel>
            </diagram>
            """

        super().__init__(node_duplicates, link_duplicates, )

    def calculate_new_group_positions(self, obj_pos_old, group_pos):
        # Adjust object positions relative to the new group's position
        obj_pos_new = (obj_pos_old[0] - group_pos[0], obj_pos_old[1] - group_pos[1])
        return obj_pos_new
    
    def update_style(self, styles):
        background = styles['background']
        shadow = styles['shadow']
        grid = styles['grid']
        pagew = styles['pagew']
        pageh = styles['pageh']

        self.drawio_diagram_xml = f"""
        <diagram id="{{id}}" name="{{name}}">
          <mxGraphModel dx="{{width}}" dy="{{height}}" grid="{grid}" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{pagew}" pageHeight="{pageh}" math="0" shadow="{shadow}" background="{background}">
            <root>
              <mxCell id="0"/>   
              <mxCell id="1" parent="0"/>
            </root>
          </mxGraphModel>
        </diagram>
        """
        self.drawing = ET.fromstring(self.drawio_drawing_xml)

    def group_nodes(self, member_objects, group_id, style=""):
        # Initialize bounding box coordinates
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')

        object_positions = []  # To store all object positions

        # Process each member object to update the bounding box
        for obj_id in member_objects:
            obj_mxcell = self.current_root.find(f".//object[@id='{obj_id}']/mxCell")
            if obj_mxcell is not None:
                geometry = obj_mxcell.find("./mxGeometry")
                if geometry is not None:
                    x, y = float(geometry.get('x', '0')), float(geometry.get('y', '0'))
                    width, height = float(geometry.get('width', '0')), float(geometry.get('height', '0'))

                    # Store object positions and update bounding box
                    object_positions.append((obj_id, x, y, width, height))
                    min_x, min_y = min(min_x, x), min(min_y, y)
                    max_x, max_y = max(max_x, x + width), max(max_y, y + height)

        # Define the group's position and size based on the bounding box
        group_x, group_y = min_x, min_y
        group_width, group_height = max_x - min_x, max_y - min_y

        # Create the group cell in the XML structure
        group_cell_xml = f"""
        <mxCell id="{group_id}" value="" style="{style}" vertex="1" connectable="0" parent="1">
        <mxGeometry x="{group_x}" y="{group_y}" width="{group_width}" height="{group_height}" as="geometry" />
        </mxCell>
        """
        group_cell = ET.fromstring(group_cell_xml)
        self.current_root.append(group_cell)

        # Update positions of all objects within the group
        for obj_id, x, y, _, _ in object_positions:
            obj_pos_old = (x, y)
            obj_pos_new = self.calculate_new_group_positions(obj_pos_old, (group_x, group_y))

            obj_mxcell = self.current_root.find(f".//object[@id='{obj_id}']/mxCell")
            if obj_mxcell is not None:
                geometry = obj_mxcell.find("./mxGeometry")
                if geometry is not None:
                    geometry.set('x', str(obj_pos_new[0]))
                    geometry.set('y', str(obj_pos_new[1]))
                    obj_mxcell.set("parent", group_id)  # Set the object's parent to the new group

    def get_used_levels(self):
        return set([node.graph_level for node in self.nodes.values()])

    def get_max_level(self):
        return max([node.graph_level for node in self.nodes.values()])
    
    def get_min_level(self):
        return min([node.graph_level for node in self.nodes.values()])
    
    def get_links_from_nodes(self):
        links = []
        for node in self.nodes.values():
            links.extend(node.get_all_links())
        return links
    
    def get_upstream_links_from_nodes(self):
        links = []
        for node in self.nodes.values():
            links.extend(node.get_upstream_links())
        return links
    
    def get_downstream_links_from_nodes(self):
        links = []
        for node in self.nodes.values():
            links.extend(node.get_downstream_links())
        return links
    
    def get_lateral_links_from_nodes(self):
        links = []
        for node in self.nodes.values():
            links.extend(node.get_lateral_links())
        return links

    def get_target_link(self, source_link):
        for link in self.get_links_from_nodes():
            if link.source == source_link.target \
            and link.target == source_link.source \
            and (link.direction != 'lateral' or link.direction == source_link.direction) \
            and source_link.source_intf == link.target_intf \
            and source_link.target_intf == link.source_intf:
                return link
        return None



    def get_nodes(self):
        return self.nodes
    

    def get_nodes_with_same_xy(self):
        nodes_with_same_x = {}
        nodes_with_same_y = {}

        for node_id, node in self.nodes.items():
            x, y = node.pos_x, node.pos_y

            # Add node to nodes_with_same_x if x-coordinate matches
            if x in nodes_with_same_x:
                nodes_with_same_x[x].append(node)
            else:
                nodes_with_same_x[x] = [node]

            # Add node to nodes_with_same_y if y-coordinate matches
            if y in nodes_with_same_y:
                nodes_with_same_y[y].append(node)
            else:
                nodes_with_same_y[y] = [node]

        return nodes_with_same_x, nodes_with_same_y

    def get_nodes_between_interconnected(self):
        nodes_with_same_x, nodes_with_same_y = self.get_nodes_with_same_xy()
        nodes_between_interconnected_x = []
        nodes_between_interconnected_y = []

        for coord, nodes in nodes_with_same_x.items():
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    node1 = nodes[i]
                    node2 = nodes[j]
                    if node1.is_connected_to(node2):
                        # Check if there are any nodes between node1 and node2 based on their positions
                        for node_between in nodes:
                            if node_between != node1 and node_between != node2:
                                if (node1.pos_y < node_between.pos_y < node2.pos_y) or (node2.pos_y < node_between.pos_y < node1.pos_y):
                                    if node_between not in nodes_between_interconnected_x:
                                        nodes_between_interconnected_x.append(node_between)
          

        for coord, nodes in nodes_with_same_y.items():
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    node1 = nodes[i]
                    node2 = nodes[j]
                    if node1.is_connected_to(node2):
                        # Check if there are any nodes between node1 and node2 based on their positions
                        for node_between in nodes:
                            if node_between != node1 and node_between != node2:
                                if (node1.pos_x < node_between.pos_x < node2.pos_x) or (node2.pos_x < node_between.pos_x < node1.pos_x):
                                    if node_between not in nodes_between_interconnected_y:
                                        nodes_between_interconnected_y.append(node_between)

        return nodes_between_interconnected_x, nodes_between_interconnected_y


    def get_nodes_by_level(self, level):
        nodes_by_level = {}
        for node in self.nodes.values():
            if node.graph_level == level:
                nodes_by_level[node.name] = node
        return nodes_by_level
