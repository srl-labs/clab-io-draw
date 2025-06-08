# ruff: noqa: B008
import logging
import os
from pathlib import Path

import typer

from clab_io_draw.core.drawio.converter import Drawio2ClabConverter
from clab_io_draw.core.drawio.drawio_parser import DrawioParser
from clab_io_draw.core.logging_config import configure_logging
from clab_io_draw.core.utils.yaml_processor import YAMLProcessor

logger = logging.getLogger(__name__)


app = typer.Typer(help="Convert a .drawio file to a Containerlab YAML file")


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


@app.command(name="drawio2clab")
def cli(  # noqa: B008
    input: Path = typer.Option(..., "-i", "--input", help="Input .drawio XML file"),  # noqa: B008
    output: Path | None = typer.Option(None, "-o", "--output", help="Output YAML file"),  # noqa: B008
    style: str = typer.Option("flow", "--style", help="YAML style"),  # noqa: B008
    diagram_name: str | None = typer.Option(
        None, "--diagram-name", help="Diagram name"
    ),  # noqa: B008
    default_kind: str = typer.Option(
        "nokia_srlinux", "--default-kind", help="Default node kind"
    ),  # noqa: B008
) -> None:
    """Convert a .drawio diagram to a Containerlab YAML file."""

    if output is None:
        output = Path(os.path.splitext(input)[0] + ".yaml")

    configure_logging(level=logging.DEBUG if style == "block" else logging.INFO)
    main(
        str(input),
        str(output),
        style=style,
        diagram_name=diagram_name,
        default_kind=default_kind,
    )


def main_cli() -> None:
    app()


if __name__ == "__main__":
    main_cli()
