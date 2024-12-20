import yaml
import sys
import logging

logger = logging.getLogger(__name__)

class ThemeManagerError(Exception):
    """Raised when loading the theme fails."""

class ThemeManager:
    """
    Loads and merges theme configuration from a YAML file.
    """
    def __init__(self, config_path: str):
        """
        :param config_path: Path to the theme configuration file.
        """
        self.config_path = config_path

    def load_theme(self) -> dict:
        """
        Load the theme configuration and return a dictionary of styles.

        :return: Dictionary containing styles and configuration parameters.
        """
        logger.debug(f"Loading theme from: {self.config_path}")
        try:
            with open(self.config_path, "r") as file:
                config = yaml.safe_load(file)
        except FileNotFoundError:
            error_message = (
                f"Error: The specified config file '{self.config_path}' does not exist."
            )
            logger.error(error_message)
            sys.exit(1)
        except Exception as e:
            error_message = f"An error occurred while loading the config: {e}"
            logger.error(error_message)
            sys.exit(1)

        base_style_dict = {
            item.split("=")[0]: item.split("=")[1]
            for item in config.get("base_style", "").split(";")
            if item
        }

        styles = {
            "background": config.get("background", "#FFFFFF"),
            "shadow": config.get("shadow", "1"),
            "grid": config.get("grid", "1"),
            "pagew": config.get("pagew", "827"),
            "pageh": config.get("pageh", "1169"),
            "base_style": config.get("base_style", ""),
            "link_style": config.get("link_style", ""),
            "src_label_style": config.get("src_label_style", ""),
            "trgt_label_style": config.get("trgt_label_style", ""),
            "port_style": config.get("port_style", ""),
            "connector_style": config.get("connector_style", ""),
            "icon_to_group_mapping": config.get("icon_to_group_mapping", {}),
            "custom_styles": {},
        }

        for key, custom_style in config.get("custom_styles", {}).items():
            custom_style_dict = {
                item.split("=")[0]: item.split("=")[1]
                for item in custom_style.split(";")
                if item
            }
            merged_style_dict = {**base_style_dict, **custom_style_dict}
            merged_style = ";".join(f"{k}={v}" for k, v in merged_style_dict.items())
            styles["custom_styles"][key] = merged_style

        for key, value in config.items():
            if key not in styles:
                styles[key] = value

        return styles
