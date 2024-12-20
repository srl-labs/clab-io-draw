from prompt_toolkit.shortcuts import checkboxlist_dialog, yes_no_dialog
import os
import re

class InteractiveManager:
    """
    Manages interactive mode for assigning graph-levels and graph-icons via a CLI interface.
    """
    def run_interactive_mode(
        self,
        nodes: dict,
        icon_to_group_mapping: dict,
        containerlab_data: dict,
        output_file: str,
        processor,
        prefix: str,
        lab_name: str,
    ) -> dict:
        """
        Run the interactive mode dialogs to set graph-levels and icons for nodes.

        :param nodes: Dictionary of node_name -> Node instances.
        :param icon_to_group_mapping: Mapping from icon names to style groups.
        :param containerlab_data: Parsed containerlab topology data.
        :param output_file: Path to the output containerlab YAML file.
        :param processor: YAMLProcessor instance for saving updated YAML.
        :param prefix: Node name prefix.
        :param lab_name: Lab name string.
        :return: Summary dictionary of the chosen configuration.
        """
        previous_summary = {"Levels": {}, "Icons": {}}
        for node_name, node in nodes.items():
            try:
                level = node.graph_level
                previous_summary["Levels"].setdefault(level, []).append(node_name)

                icon = node.graph_icon
                previous_summary["Icons"].setdefault(icon, []).append(node_name)
            except AttributeError:
                continue

        while True:
            summary = {"Levels": {}, "Icons": {}}
            tmp_nodes = list(nodes.keys())
            level = 0

            # Assign levels to nodes
            while tmp_nodes:
                level += 1
                valid_nodes = [(node, node) for node in tmp_nodes]
                if valid_nodes:
                    level_nodes = checkboxlist_dialog(
                        title=f"Level {level} nodes",
                        text=f"Choose the nodes for level {level}:",
                        values=valid_nodes,
                        default_values=previous_summary["Levels"].get(level, []),
                    ).run()
                else:
                    break

                if level_nodes is None:
                    return  # Exit if cancel clicked

                if len(level_nodes) == 0:
                    continue

                # Update node labels and summary with assigned levels
                for node_name in level_nodes:
                    nodes[node_name].graph_level = level
                    summary["Levels"].setdefault(level, []).append(node_name)
                    tmp_nodes.remove(node_name)

                    unformatted_node_name = node_name.replace(f"{prefix}-{lab_name}-", "")

                    if (
                        "labels"
                        not in containerlab_data["topology"]["nodes"][unformatted_node_name]
                    ):
                        containerlab_data["topology"]["nodes"][unformatted_node_name]["labels"] = {}

                    containerlab_data["topology"]["nodes"][unformatted_node_name]["labels"][
                        "graph-level"
                    ] = level

            tmp_nodes = list(nodes.keys())
            icons = list(icon_to_group_mapping.keys())

            # Assign icons to nodes
            for icon in icons:
                valid_nodes = [(node, node) for node in tmp_nodes]
                if valid_nodes:
                    icon_nodes = checkboxlist_dialog(
                        title=f"Choose {icon} nodes",
                        text=f"Select the nodes for the {icon} icon:",
                        values=valid_nodes,
                        default_values=previous_summary["Icons"].get(icon, []),
                    ).run()
                else:
                    icon_nodes = []

                if icon_nodes is None:
                    return  # Exit if cancel clicked

                if not icon_nodes:
                    continue

                for node_name in icon_nodes:
                    nodes[node_name].graph_icon = icon
                    summary["Icons"].setdefault(icon, []).append(node_name)
                    tmp_nodes.remove(node_name)

                    unformatted_node_name = node_name.replace(f"{prefix}-{lab_name}-", "")

                    if (
                        "labels"
                        not in containerlab_data["topology"]["nodes"][unformatted_node_name]
                    ):
                        containerlab_data["topology"]["nodes"][unformatted_node_name]["labels"] = {}

                    containerlab_data["topology"]["nodes"][unformatted_node_name]["labels"][
                        "graph-icon"
                    ] = icon

            summary_tree = ""
            for level, node_list in summary["Levels"].items():
                summary_tree += f"Level {level}: "
                node_items = []
                indent = " " * (len(f"Level {level}: "))
                for i, node in enumerate(node_list, start=1):
                    icon = nodes[node].graph_icon
                    node_items.append(f"{node} ({icon})")
                    if i % 3 == 0 and i < len(node_list):
                        node_items.append("\n" + indent)
                summary_tree += ", ".join(node_items).replace(indent + ", ", indent) + "\n"
            summary_tree += "\nDo you want to keep it like this? Select < No > to edit your configuration."

            result = yes_no_dialog(title="SUMMARY", text=summary_tree).run()

            if result is None:
                return
            elif result:
                break

        update_file = yes_no_dialog(
            title="Update ContainerLab File",
            text="Do you want to save a new ContainerLab file with the new configuration?",
        ).run()

        if update_file:
            modified_output_file = os.path.splitext(output_file)[0] + ".mod.yaml"
            processor.save_yaml(containerlab_data, modified_output_file)
            print(f"ContainerLab file has been updated: {modified_output_file}")
        else:
            print("ContainerLab file has not been updated.")

        return summary
