import json
import logging
import os

import yaml

from clab_io_draw.core.utils.env_expander import (
    expand_env_vars,
)

logger = logging.getLogger(__name__)


class TopologyLoaderError(Exception):
    """Raised when loading the topology fails."""


class TopologyLoader:
    """
    Loads containerlab topology data from a YAML file, expanding environment variables.
    """

    def load(self, input_file: str) -> dict:
        """
        Load the containerlab YAML topology file, including environment-variable expansion.
        Also loads annotations from .annotations.json file if it exists.

        :param input_file: Path to the containerlab YAML file.
        :return: Parsed containerlab topology data with env variables expanded and annotations.
        :raises TopologyLoaderError: If file not found or parse error occurs.
        """
        logger.debug(f"Loading topology from file: {input_file}")
        try:
            with open(input_file) as file:
                raw_content = file.read()

            # Expand ${VAR:=default} placeholders before parsing
            expanded_content = expand_env_vars(raw_content)

            containerlab_data = yaml.safe_load(expanded_content)

            # Load annotations if .annotations.json file exists
            annotations_file = f"{input_file}.annotations.json"
            if os.path.exists(annotations_file):
                logger.debug(f"Loading annotations from: {annotations_file}")
                with open(annotations_file) as f:
                    annotations = json.load(f)
                containerlab_data["annotations"] = annotations
                logger.debug("Annotations successfully loaded.")
            else:
                logger.debug(f"No annotations file found at: {annotations_file}")
                containerlab_data["annotations"] = None

            logger.debug("Topology successfully loaded.")
            return containerlab_data

        except FileNotFoundError as err:
            error_message = (
                f"Error: The specified clab file '{input_file}' does not exist."
            )
            logger.error(error_message)
            raise TopologyLoaderError(error_message) from err

        except Exception as err:
            error_message = f"An error occurred while loading the config: {err}"
            logger.error(error_message)
            raise TopologyLoaderError(error_message) from err
