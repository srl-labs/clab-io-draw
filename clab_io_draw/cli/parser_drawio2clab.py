import argparse


def parse_arguments():
    """
    Parse command-line arguments for drawio2clab tool.

    :return: argparse.Namespace object with parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Convert a .drawio file to a Containerlab YAML file."
    )
    parser.add_argument(
        "-i", "--input", required=True, help="The input .drawio XML file."
    )
    parser.add_argument("-o", "--output", required=False, help="The output YAML file.")
    parser.add_argument(
        "--style", choices=["block", "flow"], default="flow", help="YAML style."
    )
    parser.add_argument(
        "--diagram-name", required=False, help="Name of the diagram to parse."
    )
    parser.add_argument(
        "--default-kind", default="nokia_srlinux", help="Default node kind."
    )
    return parser.parse_args()
