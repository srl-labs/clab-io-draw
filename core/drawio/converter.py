import yaml
import os

class Drawio2ClabConverter:
    def __init__(self, default_kind="nokia_srlinux"):
        self.default_kind = default_kind

    def compile_link_information(self, links_info):
        compiled_links = []
        for link_id, info in links_info.items():
            sorted_labels = sorted(info["labels"], key=lambda label: label["x_position"])

            if len(sorted_labels) < 2:
                print(f"Not enough labels for link {link_id}. At least 2 labels required.")
                continue

            source_label = sorted_labels[0]["value"]
            target_label = sorted_labels[-1]["value"]

            endpoints = [f"{info['source']}:{source_label}", f"{info['target']}:{target_label}"]
            compiled_links.append({"endpoints": endpoints})

        compiled_links.sort(key=lambda x: (x["endpoints"][0].split(":")[0]))
        return compiled_links

    def generate_yaml_structure(self, node_details, compiled_links, input_file):
        base_name = os.path.splitext(os.path.basename(input_file))[0]

        nodes = {}
        kinds = {}

        for node_id, details in node_details.items():
            node_label = details["label"]
            node_kind = details["kind"]

            # Kinds logic from original code
            if node_kind not in kinds:
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
                node_info["mgmt_ipv4"] = details["mgmt_ipv4"]
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
