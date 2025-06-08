import logging
import sys
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class DrawioParser:
    """
    Parses draw.io XML files to extract node and link information.
    """

    def __init__(self, input_file, diagram_name=None):
        self.input_file = input_file
        self.diagram_name = diagram_name

    def parse_xml(self):
        """
        Parse the input draw.io (XML) file and return the root of mxGraphModel.

        :return: mxGraphModel root element.
        """
        logger.debug(f"Parsing drawio XML from file: {self.input_file}")
        try:
            tree = ET.parse(self.input_file)
            root = tree.getroot()
        except FileNotFoundError:
            logger.error(f"Input file '{self.input_file}' does not exist.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error loading drawio file: {e}")
            sys.exit(1)

        if self.diagram_name:
            for diagram in root.findall("diagram"):
                if diagram.get("name") == self.diagram_name:
                    mxGraphModel_root = diagram.find(".//mxGraphModel/root")
                    if mxGraphModel_root is not None:
                        return mxGraphModel_root
                    logger.error(
                        f"mxGraphModel/root not found in diagram '{self.diagram_name}'."
                    )
                    sys.exit(1)
            logger.error(f"Diagram named '{self.diagram_name}' not found.")
            sys.exit(1)
        else:
            first_diagram = root.find("diagram")
            if first_diagram is not None:
                mxGraphModel_root = first_diagram.find(".//mxGraphModel/root")
                if mxGraphModel_root is not None:
                    return mxGraphModel_root
                logger.error("mxGraphModel/root not found in the first diagram.")
                sys.exit(1)
            logger.error("No diagrams found in the file.")
            sys.exit(1)

    def extract_nodes(self, mxGraphModel):
        """
        Extract node details from mxGraphModel.

        :param mxGraphModel: Root element of mxGraphModel.
        :return: Dict of node_id -> node details.
        """
        logger.debug("Extracting nodes from drawio model...")
        node_details = {}

        # Check 'object' elements
        for obj in mxGraphModel.findall(".//object"):
            node_id = obj.get("id")
            node_label = obj.get("label", "").strip()
            node_type = obj.get("type", None)
            mgmt_ipv4 = obj.get("mgmt-ipv4", None)
            group = obj.get("group", None)
            labels = obj.get("labels", None)
            node_kind = obj.get("kind", "nokia_srlinux")

            if node_label:
                node_details[node_id] = {
                    "label": node_label,
                    "type": node_type,
                    "mgmt-ipv4": mgmt_ipv4,
                    "group": group,
                    "labels": labels,
                    "kind": node_kind,
                }

        # Fallback: check mxCell vertices if not already in node_details
        for mxCell in mxGraphModel.findall(".//mxCell[@vertex='1']"):
            node_id = mxCell.get("id")
            if node_id not in node_details:
                node_label = mxCell.get("value", "").strip()
                style = mxCell.get("style", "")
                if "image=data" in style and node_label:
                    node_details[node_id] = {
                        "label": node_label,
                        "kind": "nokia_srlinux",
                    }

        return node_details

    def extract_links(self, mxGraphModel, node_details):
        """
        Extract link information from mxGraphModel.

        :param mxGraphModel: Root element of mxGraphModel.
        :param node_details: Dict of node_id->node info.
        :return: Dict of link_id->link info.
        """
        logger.debug("Extracting links from drawio model...")
        links_info = {}

        for mxCell in mxGraphModel.findall(".//mxCell[@source][@target][@edge]"):
            link_info = self._extract_link_info(mxCell, node_details)
            if link_info:
                links_info[link_info["id"]] = link_info

        for object_elem in mxGraphModel.findall(".//object"):
            mxCells = object_elem.findall(".//mxCell[@source][@target][@edge]")
            for mxC in mxCells:
                link_info = self._extract_link_info(
                    mxC, node_details, fallback_id=object_elem.get("id")
                )
                if link_info:
                    links_info[link_info["id"]] = link_info

        return links_info

    def _extract_link_info(self, mxCell, node_details, fallback_id=None):
        """
        Extract individual link info from a given mxCell.

        :param mxCell: The mxCell element representing an edge.
        :param node_details: node info dict
        :param fallback_id: fallback link id if mxCell has no id.
        :return: Dict representing link info or None if incomplete.
        """
        source_id, target_id = mxCell.get("source"), mxCell.get("target")
        link_id = mxCell.get("id") or fallback_id
        geometry = mxCell.find("mxGeometry")
        x, y = (
            (float(geometry.get("x", 0)), float(geometry.get("y", 0)))
            if geometry is not None
            else (None, None)
        )

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
        """
        Extract labels for links, used to identify source/target interface names.

        :param mxGraphModel: Root of mxGraphModel.
        :param links_info: Dict of link_id->link info
        """
        logger.debug("Extracting link labels from drawio model...")
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
