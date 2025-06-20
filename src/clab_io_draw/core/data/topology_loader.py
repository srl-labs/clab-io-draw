import logging

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

        :param input_file: Path to the containerlab YAML file.
        :return: Parsed containerlab topology data with env variables expanded.
        :raises TopologyLoaderError: If file not found or parse error occurs.
        """
        logger.debug(f"Loading topology from file: {input_file}")
        try:
            with open(input_file) as file:
                raw_content = file.read()

            # Expand ${VAR:=default} placeholders before parsing
            expanded_content = expand_env_vars(raw_content)

            containerlab_data = yaml.safe_load(expanded_content)
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
