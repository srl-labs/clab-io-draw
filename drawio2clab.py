import os
import logging
from cli.parser_drawio2clab import parse_arguments
from core.utils.yaml_processor import YAMLProcessor
from core.drawio.drawio_parser import DrawioParser
from core.drawio.converter import Drawio2ClabConverter
from core.logging_config import configure_logging

logger = logging.getLogger(__name__)


def main(
    input_file: str,
    output_file: str,
    style: str = "flow",
    diagram_name: str = None,
    default_kind: str = "nokia_srlinux",
) -> None:
    """
    Convert a .drawio file to a Containerlab YAML file.

    :param input_file: Path to the .drawio XML file.
    :param output_file: Output YAML file path.
    :param style: YAML style ("block" or "flow").
    :param diagram_name: Name of the diagram to parse within the .drawio file.
    :param default_kind: Default kind for nodes if not specified.
    """
    logger.debug("Starting drawio2clab conversion...")
    parser = DrawioParser(input_file, diagram_name)
    mxGraphModel_root = parser.parse_xml()

    node_details = parser.extract_nodes(mxGraphModel_root)
    links_info = parser.extract_links(mxGraphModel_root, node_details)
    parser.extract_link_labels(mxGraphModel_root, links_info)

    converter = Drawio2ClabConverter(default_kind=default_kind)
    compiled_links = converter.compile_link_information(links_info)
    yaml_data = converter.generate_yaml_structure(
        node_details, compiled_links, input_file
    )

    processor = YAMLProcessor()
    processor.save_yaml(
        yaml_data, output_file, flow_style="block" if style == "block" else None
    )
    logger.info(f"Conversion completed. Output saved to {output_file}")


if __name__ == "__main__":
    args = parse_arguments()
    if not args.output:
        args.output = os.path.splitext(args.input)[0] + ".yaml"
    configure_logging(level=logging.DEBUG if args.style == "block" else logging.INFO)
    main(
        args.input,
        args.output,
        style=args.style,
        diagram_name=args.diagram_name,
        default_kind=args.default_kind,
    )
