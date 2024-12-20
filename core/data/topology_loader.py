import yaml
import sys
import logging

logger = logging.getLogger(__name__)

class TopologyLoaderError(Exception):
    """Raised when loading the topology fails."""

class TopologyLoader:
    """
    Loads containerlab topology data from a YAML file.
    """
    def load(self, input_file: str) -> dict:
        """
        Load the containerlab YAML topology file and return its contents as a dictionary.

        :param input_file: Path to the containerlab YAML file.
        :return: Parsed containerlab topology data.
        """
        logger.debug(f"Loading topology from file: {input_file}")
        try:
            with open(input_file, "r") as file:
                containerlab_data = yaml.safe_load(file)
            logger.debug("Topology successfully loaded.")
            return containerlab_data
        except FileNotFoundError:
            error_message = f"Error: The specified clab file '{input_file}' does not exist."
            logger.error(error_message)
            raise TopologyLoaderError(error_message)
        except Exception as e:
            error_message = f"An error occurred while loading the config: {e}"
            logger.error(error_message)
            raise TopologyLoaderError(error_message)
