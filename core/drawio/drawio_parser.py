import xml.etree.ElementTree as ET
import sys

class DrawioParser:
    def __init__(self, input_file, diagram_name=None):
        self.input_file = input_file
        self.diagram_name = diagram_name

    def parse_xml(self):
        try:
            tree = ET.parse(self.input_file)
            root = tree.getroot()
        except FileNotFoundError:
            print(f"Error: The specified input file '{self.input_file}' does not exist.")
            sys.exit(1)
        except Exception as e:
            print(f"An error occurred while loading the config: {e}")
            sys.exit(1)

        if self.diagram_name:
            for diagram in root.findall("diagram"):
                if diagram.get("name") == self.diagram_name:
                    mxGraphModel_root = diagram.find(".//mxGraphModel/root")
                    if mxGraphModel_root is not None:
                        return mxGraphModel_root
                    else:
                        print(f"mxGraphModel/root not found in diagram '{self.diagram_name}'.")
                        sys.exit(1)
            print(f"Diagram named '{self.diagram_name}' not found.")
            sys.exit(1)
        else:
            first_diagram = root.find("diagram")
            if first_diagram is not None:
                mxGraphModel_root = first_diagram.find(".//mxGraphModel/root")
                if mxGraphModel_root is not None:
                    return mxGraphModel_root
                else:
                    print("mxGraphModel/root not found in the first diagram.")
                    sys.exit(1)
            print("No diagrams found in the file.")
            sys.exit(1)

    def extract_nodes(self, mxGraphModel):
        node_details = {}

        # from the original extract_nodes() logic
        for obj in mxGraphModel.findall(".//object"):
            node_id = obj.get("id")
            node_label = obj.get("label", "").strip()
            node_type = obj.get("type", None)
            mgmt_ipv4 = obj.get("mgmt-ipv4", None)
            group = obj.get("group", None)
            labels = obj.get("labels", None)
            node_kind = obj.get("kind", "nokia_srlinux")

            if not node_label:
                # try child mxCell if needed, but original code tried directly
                pass

            if node_label:
                node_details[node_id] = {
                    "label": node_label,
                    "type": node_type,
                    "mgmt-ipv4": mgmt_ipv4,
                    "group": group,
                    "labels": labels,
                    "kind": node_kind,
                }

        # Also handle mxCell with vertex='1' if needed, original logic included that
        for mxCell in mxGraphModel.findall(".//mxCell[@vertex='1']"):
            node_id = mxCell.get("id")
            # Ensure not descendant of object
            # According to original code, if not already in node_details:
            if node_id not in node_details:
                node_label = mxCell.get("value", "").strip()
                style = mxCell.get("style", "")
                if "image=data" in style and node_label:
                    node_details[node_id] = {"label": node_label, "kind": "nokia_srlinux"}

        return node_details

    def extract_links(self, mxGraphModel, node_details):
        links_info = {}

        # from the original extract_links() logic
        for mxCell in mxGraphModel.findall(".//mxCell[@source][@target][@edge]"):
            link_info = self._extract_link_info(mxCell, node_details)
            if link_info:
                links_info[link_info["id"]] = link_info

        for object_elem in mxGraphModel.findall(".//object"):
            mxCells = object_elem.findall(".//mxCell[@source][@target][@edge]")
            for mxC in mxCells:
                link_info = self._extract_link_info(mxC, node_details, fallback_id=object_elem.get("id"))
                if link_info:
                    links_info[link_info["id"]] = link_info

        return links_info

    def _extract_link_info(self, mxCell, node_details, fallback_id=None):
        source_id, target_id = mxCell.get("source"), mxCell.get("target")
        link_id = mxCell.get("id") or fallback_id
        geometry = mxCell.find("mxGeometry")
        x, y = (float(geometry.get("x", 0)), float(geometry.get("y", 0))) if geometry is not None else (None, None)

        source_label = node_details.get(source_id, {}).get("label", "Unknown")
        target_label = node_details.get(target_id, {}).get("label", "Unknown")

        if link_id:
            return {
                "id": link_id,
                "source": source_label,
                "target": target_label,
                "geometry": {"x": x, "y": y},
                "labels": [],
            }

    def extract_link_labels(self, mxGraphModel, links_info):
        for mxCell in mxGraphModel.findall(".//mxCell[@value]"):
            parent_id = mxCell.get("parent")
            if parent_id in links_info:
                label_value = mxCell.get("value")
                geometry = mxCell.find("mxGeometry")
                if label_value and geometry is not None:
                    x_position = float(geometry.get("x", 0))
                    y_position = float(geometry.get("y", 0))
                    links_info[parent_id]["labels"].append(
                        {
                            "value": label_value,
                            "x_position": x_position,
                            "y_position": y_position,
                        }
                    )
