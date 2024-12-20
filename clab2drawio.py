from cli.parser_clab2drawio import parse_arguments
from core.diagram.custom_drawio import CustomDrawioDiagram
from core.models.node import Node
from core.models.link import Link
from core.grafana.grafana_manager import GrafanaDashboard
from core.utils.yaml_processor import YAMLProcessor
from core.data.topology_loader import TopologyLoader
from core.data.node_link_builder import NodeLinkBuilder
from core.data.graph_level_manager import GraphLevelManager
from core.layout.vertical_layout import VerticalLayout
from core.layout.horizontal_layout import HorizontalLayout
from core.config.theme_manager import ThemeManager
from core.interactivity.interactive_manager import InteractiveManager
from core.diagram.diagram_builder import DiagramBuilder
from collections import defaultdict
from prompt_toolkit.shortcuts import checkboxlist_dialog, yes_no_dialog
import os


def main(
    input_file,
    output_file,
    grafana,
    theme,
    include_unlinked_nodes=False,
    no_links=False,
    layout="vertical",
    verbose=False,
    interactive=False,
):
    loader = TopologyLoader()
    containerlab_data = loader.load(input_file)

    try:
        if os.path.isabs(theme):
            theme_path = theme
        else:
            theme_path = os.path.join(script_dir, "styles", f"{theme}.yaml")

        # Check if the theme file exists
        if not os.path.exists(theme_path):
            raise FileNotFoundError(
                f"The specified theme file '{theme_path}' does not exist."
            )

    except FileNotFoundError as e:
        error_message = str(e)
        print(error_message)
        exit()
    except Exception as e:
        error_message = f"An error occurred while loading the theme: {e}"
        print(error_message)
        exit()

    # Use ThemeManager to load styles
    theme_manager = ThemeManager(theme_path)
    styles = theme_manager.load_theme()

    diagram = CustomDrawioDiagram()
    diagram.layout = layout

    nodes_from_clab = containerlab_data["topology"]["nodes"]
    # Determine the prefix
    prefix = containerlab_data.get("prefix", "clab")
    lab_name = containerlab_data.get("name", "")

    # Use NodeLinkBuilder to build nodes and links
    builder = NodeLinkBuilder(containerlab_data, styles, prefix, lab_name)
    nodes, links = builder.build_nodes_and_links()    

    diagram.nodes = nodes

    if not include_unlinked_nodes:
        connected_nodes = {name: node for name, node in nodes.items() if node.links}
        diagram.nodes = connected_nodes
        nodes = diagram.nodes
    else:
        diagram.nodes = nodes

    if interactive:
        processor = YAMLProcessor()
        interactor = InteractiveManager()
        interactor.run_interactive_mode(
            diagram.nodes,
            styles["icon_to_group_mapping"],
            containerlab_data,
            input_file,
            processor,
            prefix,
            lab_name,
        )

    graph_manager = GraphLevelManager()
    graph_manager.assign_graphlevels(diagram, verbose=False)

    # Choose layout based on layout argument
    if layout == "vertical":
        layout_manager = VerticalLayout()
    else:
        layout_manager = HorizontalLayout()

    layout_manager.apply(diagram, verbose=verbose)

    # Calculate the diagram size based on the positions of the nodes
    min_x = min(node.pos_x for node in nodes.values())
    min_y = min(node.pos_y for node in nodes.values())
    max_x = max(node.pos_x for node in nodes.values())
    max_y = max(node.pos_y for node in nodes.values())

    # Determine the necessary adjustments
    adjust_x = -min_x + 100  # Adjust so the minimum x is at least 100
    adjust_y = -min_y + 100  # Adjust so the minimum y is at least 100

    # Apply adjustments to each node's position
    for node in nodes.values():
        node.pos_x += adjust_x
        node.pos_y += adjust_y

    # Recalculate diagram size if necessary, after adjustment
    max_x = max(node.pos_x for node in nodes.values())
    max_y = max(node.pos_y for node in nodes.values())

    max_size_x = max_x + 100  # Adding a margin to the right side
    max_size_y = max_y + 100  # Adding a margin to the bottom

    if styles["pagew"] == "auto":
        styles["pagew"] = max_size_x
    if styles["pageh"] == "auto":
        styles["pageh"] = max_size_y

    diagram.update_style(styles)

    diagram.add_diagram("Network Topology")

    diagram_builder = DiagramBuilder()
    diagram_builder.add_nodes(diagram, diagram.nodes, styles)

    if grafana:
        styles["ports"] = True

    if styles["ports"]:
        diagram_builder.add_ports(diagram, styles)
        if not output_file:
            grafana_output_file = os.path.splitext(input_file)[0] + ".grafana.json"
        output_folder = os.path.dirname(grafana_output_file) or "."
        diagram.grafana_dashboard_file = grafana_output_file
        os.makedirs(output_folder, exist_ok=True)
        
        grafana = GrafanaDashboard(diagram)
        panel_config = grafana.create_panel_yaml()

        flow_panel_output_file = os.path.splitext(grafana_output_file)[0] + ".flow_panel.yaml"
        with open(flow_panel_output_file, "w") as f:
            f.write(panel_config)
        print("Saved flow panel YAML to:", flow_panel_output_file)

        grafana_json = grafana.create_dashboard(panel_config)
        with open(grafana_output_file, "w") as f:
            f.write(grafana_json)
        print("Saved Grafana dashboard JSON to:", grafana_output_file)
    else:
        diagram_builder.add_links(diagram, styles)

    if not output_file:
        output_file = os.path.splitext(input_file)[0] + ".drawio"

    output_folder = os.path.dirname(output_file) or "."
    output_filename = os.path.basename(output_file)
    os.makedirs(output_folder, exist_ok=True)

    diagram.dump_file(filename=output_filename, folder=output_folder)

    print("Saved file to:", output_file)

if __name__ == "__main__":
    args = parse_arguments()

    script_dir = os.path.dirname(__file__)

    main(
        args.input,
        args.output,
        args.gf_dashboard,
        args.theme,
        args.include_unlinked_nodes,
        args.no_links,
        args.layout,
        args.verbose,
        args.interactive,
    )
