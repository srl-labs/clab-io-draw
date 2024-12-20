import yaml
import sys
import os

class TopologyLoader:
    def load(self, input_file):
        """
        Load the containerlab YAML topology file and return its contents as a dictionary.
        """
        try:
            with open(input_file, "r") as file:
                containerlab_data = yaml.safe_load(file)
            return containerlab_data
        except FileNotFoundError:
            error_message = f"Error: The specified clab file '{input_file}' does not exist."
            print(error_message)
            sys.exit(1)
        except Exception as e:
            error_message = f"An error occurred while loading the config: {e}"
            print(error_message)
            sys.exit(1)
