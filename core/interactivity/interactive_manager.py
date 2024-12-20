import logging
from prompt_toolkit.shortcuts import checkboxlist_dialog, yes_no_dialog

logger = logging.getLogger(__name__)

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
        Run dialogs to set graph-levels and icons interactively.

        :return: Summary dictionary of the chosen configuration.
        """
        logger.debug("Starting interactive mode for node configuration...")
        previous_summary = {"Levels": {}, "Icons": {}}
        for node_name, node in nodes.items():
                level = node.graph_level
                previous_summary["Levels"].setdefault(level, []).append(node_name)
                icon = node.graph_icon
                previous_summary["Icons"].setdefault(icon, []).append(node_name)

        while True:
            summary = {"Levels": {}, "Icons": {}}
            tmp_nodes = list(nodes.keys())
            level = 0

            # Assign levels
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
                    logger.debug("User canceled interactive mode.")
                    return

                if len(level_nodes) == 0:
                    continue

                for node_name in level_nodes:
                    nodes[node_name].graph_level = level
                    summary["Levels"].setdefault(level, []).append(node_name)
                    tmp_nodes.remove(node_name)

                    unformatted_node_name = node_name.replace(f"{prefix}-{lab_name}-", "")
                    if "labels" not in containerlab_data["topology"]["nodes"][unformatted_node_name]:
                        containerlab_data["topology"]["nodes"][unformatted_node_name]["labels"] = {}
                    containerlab_data["topology"]["nodes"][unformatted_node_name]["labels"]["graph-level"] = level

            # Assign icons
            tmp_nodes = list(nodes.keys())
            icons = list(icon_to_group_mapping.keys())
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
                    logger.debug("User canceled interactive icon assignment.")
                    return

                if not icon_nodes:
                    continue

                for node_name in icon_nodes:
                    nodes[node_name].graph_icon = icon
                    summary["Icons"].setdefault(icon, []).append(node_name)
                    tmp_nodes.remove(node_name)

                    unformatted_node_name = node_name.replace(f"{prefix}-{lab_name}-", "")
                    if "labels" not in containerlab_data["topology"]["nodes"][unformatted_node_name]:
                        containerlab_data["topology"]["nodes"][unformatted_node_name]["labels"] = {}
                    containerlab_data["topology"]["nodes"][unformatted_node_name]["labels"]["graph-icon"] = icon

            summary_tree = ""
            for lvl, node_list in summary["Levels"].items():
                summary_tree += f"Level {lvl}: "
                node_items = []
                indent = " " * (len(f"Level {lvl}: "))
                for i, node in enumerate(node_list, start=1):
                    icon = nodes[node].graph_icon
                    node_items.append(f"{node} ({icon})")
                    if i % 3 == 0 and i < len(node_list):
                        node_items.append("\n" + indent)
                summary_tree += ", ".join(node_items).replace(indent + ", ", indent) + "\n"
            summary_tree += "\nDo you want to keep it like this? Select < No > to edit your configuration."

            result = yes_no_dialog(title="SUMMARY", text=summary_tree).run()

            if result is None:
                logger.debug("User canceled at summary.")
                return
            elif result:
                break

        update_file = yes_no_dialog(
            title="Update ContainerLab File",
            text="Do you want to save a new ContainerLab file with the new configuration?",
        ).run()

        if update_file:
            modified_output_file = output_file.rsplit('.', 1)[0] + ".mod.yml"
            processor.save_yaml(containerlab_data, modified_output_file)
            print(f"ContainerLab file has been updated: {modified_output_file}")
        else:
            print("ContainerLab file has not been updated.")

        return summary
