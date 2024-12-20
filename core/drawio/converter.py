import logging

logger = logging.getLogger(__name__)

class Drawio2ClabConverter:
    """
    Converts parsed draw.io node/link info into Containerlab YAML structure.
    """

    def __init__(self, default_kind="nokia_srlinux"):
        self.default_kind = default_kind

    def compile_link_information(self, links_info):
        """
        Compile raw link info into a structured format expected by Containerlab.

        :param links_info: Dict of link_id -> link details
        :return: List of link dictionaries with endpoints
        """
        logger.debug("Compiling link information from parsed data...")
        compiled_links = []
        for link_id, info in links_info.items():
            sorted_labels = sorted(info["labels"], key=lambda label: label["x_position"])

            if len(sorted_labels) < 2:
                logger.warning(f"Not enough labels for link {link_id}, skipping.")
                continue

            source_label = sorted_labels[0]["value"]
            target_label = sorted_labels[-1]["value"]

            endpoints = [f"{info['source']}:{source_label}", f"{info['target']}:{target_label}"]
            compiled_links.append({"endpoints": endpoints})

        compiled_links.sort(key=lambda x: (x["endpoints"][0].split(":")[0]))
        return compiled_links

    def generate_yaml_structure(self, node_details, compiled_links, input_file):
        """
        Generate the YAML structure for Containerlab from node and link details.

        :param node_details: Dict of node_id -> node attributes
        :param compiled_links: List of compiled link dictionaries
        :param input_file: Original input filename
        :return: Dictionary representing the Containerlab YAML structure
        """
        logger.debug("Generating Containerlab YAML structure...")
        base_name = input_file.split('.')[0]

        nodes = {}
        kinds = {}

        for node_id, details in node_details.items():
            node_label = details["label"]
            node_kind = details["kind"]

            if node_kind not in kinds:
                # simple heuristic
                if node_kind == "nokia_srlinux":
                    kinds[node_kind] = {"image": "ghcr.io/nokia/srlinux", "type": "ixrd3"}
                elif node_kind == "linux":
                    kinds[node_kind] = {"image": "ghcr.io/hellt/network-multitool"}
                elif node_kind == "vr-sros":
                    kinds[node_kind] = {"image": "registry.srlinux.dev/pub/vr-sros:23.10"}
                else:
                    kinds[node_kind] = {"image": None}

            node_info = {"kind": node_kind}
            if details.get("type"):
                node_info["type"] = details["type"]

            if details.get("mgmt-ipv4") is not None:
                node_info["mgmt_ipv4"] = details["mgmt-ipv4"]
            if details.get("group") is not None:
                node_info["group"] = details["group"]
            if details.get("labels") is not None:
                node_info["labels"] = details["labels"]

            nodes[node_label] = node_info

        yaml_data = {
            "name": base_name,
            "topology": {"kinds": kinds, "nodes": nodes, "links": compiled_links},
        }

        return yaml_data
