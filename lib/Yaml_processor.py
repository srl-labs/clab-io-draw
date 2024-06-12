import yaml
import sys


class YAMLProcessor:
    class CustomDumper(yaml.SafeDumper):
        """
        Custom YAML dumper that adjusts the indentation for lists and maintains certain lists in inline format.
        """

        pass

    def custom_list_representer(self, dumper, data):
        # Check if we are at the specific list under 'links' with 'endpoints'
        if len(data) == 2 and isinstance(data[0], str) and ":" in data[0]:
            return dumper.represent_sequence(
                "tag:yaml.org,2002:seq", data, flow_style=True
            )
        else:
            return dumper.represent_sequence(
                "tag:yaml.org,2002:seq", data, flow_style=False
            )

    def custom_dict_representer(self, dumper, data):
        return dumper.represent_dict(data.items())

    def __init__(self):
        # Assign custom representers to the CustomDumper class
        self.CustomDumper.add_representer(list, self.custom_list_representer)
        self.CustomDumper.add_representer(dict, self.custom_dict_representer)

    def load_yaml(self, yaml_str):
        try:
            # Load YAML data
            data = yaml.safe_load(yaml_str)
            return data

        except yaml.YAMLError as e:
            print(f"Error loading YAML: {str(e)}")
            sys.exit(1)

    def save_yaml(self, data, output_file, flow_style=None):
        try:
            # Save YAML data
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

            print(f"YAML file saved as '{output_file}'.")

        except IOError as e:
            print(f"Error saving YAML file: {str(e)}")
            sys.exit(1)
