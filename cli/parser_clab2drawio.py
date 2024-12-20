import argparse

def parse_arguments():
    """
    Parse command-line arguments for clab2drawio tool.

    :return: argparse.Namespace object with parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Generate a topology diagram from a containerlab YAML or draw.io XML file."
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="The filename of the input file (containerlab YAML for diagram generation).",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=False,
        help="The output file path for the generated diagram (draw.io format).",
    )
    parser.add_argument(
        "-g",
        "--gf_dashboard",
        action="store_true",
        required=False,
        help="Generate Grafana Dashboard Flag.",
    )
    parser.add_argument(
        "--include-unlinked-nodes",
        action="store_true",
        help="Include nodes without any links in the topology diagram",
    )
    parser.add_argument(
        "--no-links",
        action="store_true",
        help="Do not draw links between nodes in the topology diagram",
    )
    parser.add_argument(
        "--layout",
        type=str,
        default="vertical",
        choices=["vertical", "horizontal"],
        help="Specify the layout of the topology diagram (vertical or horizontal)",
    )
    parser.add_argument(
        "--theme",
        default="nokia_bright",
        help="Specify the theme for the diagram or path to a custom style config file.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output for debugging purposes",
    )
    parser.add_argument(
        "-I",
        "--interactive",
        action="store_true",
        required=False,
        help="Define graph-levels and graph-icons in interactive mode",
    )
    return parser.parse_args()
