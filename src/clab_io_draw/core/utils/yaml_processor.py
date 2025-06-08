import logging
import sys

import yaml

logger = logging.getLogger(__name__)


class YAMLProcessor:
    """
    Handles loading and saving YAML data with custom formatting.
    """

    class CustomDumper(yaml.SafeDumper):
        pass

    def custom_list_representer(self, dumper, data):
        # Check if we are at the specific list under 'links' with 'endpoints'
        if len(data) == 2 and isinstance(data[0], str) and ":" in data[0]:
            return dumper.represent_sequence(
                "tag:yaml.org,2002:seq", data, flow_style=True
            )
        return dumper.represent_sequence(
            "tag:yaml.org,2002:seq", data, flow_style=False
        )

    def custom_dict_representer(self, dumper, data):
        return dumper.represent_dict(data.items())

    def __init__(self):
        self.CustomDumper.add_representer(list, self.custom_list_representer)
        self.CustomDumper.add_representer(dict, self.custom_dict_representer)

    def load_yaml(self, yaml_str):
        try:
            data = yaml.safe_load(yaml_str)
            return data
        except yaml.YAMLError as e:
            logger.error(f"Error loading YAML: {str(e)}")
            sys.exit(1)

    def save_yaml(self, data, output_file, flow_style=None):
        """
        Save the given data as YAML to output_file.

        :param data: Python object to save.
        :param output_file: Path to output file.
        :param flow_style: YAML flow style, if any.
        """
        logger.debug(f"Saving YAML to file: {output_file}")
        try:
            with open(output_file, "w") as file:
                if flow_style is None:
                    yaml.dump(
                        data,
                        file,
                        Dumper=self.CustomDumper,
                        sort_keys=False,
                        default_flow_style=False,
                        indent=2,
                    )
                else:
                    yaml.dump(data, file, default_flow_style=False, sort_keys=False)

            logger.debug("YAML file saved successfully.")
        except OSError as e:
            logger.error(f"Error saving YAML file: {str(e)}")
            sys.exit(1)
