import base64
import glob
import logging
import os
import re
from typing import Dict, List

import yaml

logger = logging.getLogger(__name__)


class ThemeManagerError(Exception):
    """Raised when loading the theme fails due to invalid style strings or configuration."""

    pass


class ThemeManager:
    """
    ThemeManager is responsible for:
    - Loading a theme configuration from a YAML file.
    - Validating style strings for nodes and links.
    - Optionally modifying embedded SVG images by injecting custom CSS overrides.

    CSS overrides can be specified in the theme YAML and allow changing properties
    of classes defined in the embedded SVG <style> block.
    """

    def __init__(self, config_path: str):
        """
        Initialize the ThemeManager with a path to a theme configuration file.

        :param config_path: Path to the YAML theme configuration file.
        """
        self.config_path = config_path

    def list_available_themes(self) -> List[str]:
        """
        Return a list of all available theme names in the same directory as the current config_path.
        Themes are identified by files ending with .yaml or .yml.

        :return: List of theme names (file names without the .yaml/.yml extension).
        """
        # Identify the directory containing the theme files
        base_dir = os.path.dirname(self.config_path)
        if not base_dir:
            base_dir = "."

        # Gather all .yaml / .yml files
        yaml_files = glob.glob(os.path.join(base_dir, "*.yaml")) + glob.glob(os.path.join(base_dir, "*.yml"))

        # Extract base filenames without extensions
        available_themes = []
        for yf in yaml_files:
            filename = os.path.basename(yf)
            # Remove extension and store just the "name"
            theme_name, _ = os.path.splitext(filename)
            available_themes.append(theme_name)

        return available_themes


    def load_theme(self) -> dict:
        """
        Load and process the theme configuration.

        This method:
        - Reads the YAML file.
        - Validates the 'base_style' string.
        - Merges 'base_style' with each 'custom_styles' entry (custom overrides base).
        - Applies CSS overrides to embedded SVG images in custom styles if defined.

        :return: A dictionary representing the fully processed theme configuration.
        :raises SystemExit: If the file does not exist or another IO error occurs.
        :raises ThemeManagerError: If invalid style strings are encountered.
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
            raise SystemExit(error_message)
        except Exception as e:
            error_message = f"An error occurred while loading the config: {e}"
            logger.error(error_message)
            raise SystemExit(error_message)

        # 1. Read base_style and validate
        base_style = config.get("base_style", "")
        self._validate_style_string(base_style)

        # 2. Read custom_styles, merge with base_style, then validate
        custom_styles = config.get("custom_styles", {})
        merged_custom_styles = {}
        for style_name, style_str in custom_styles.items():
            # Merge base_style with custom_style (custom overrides base)
            merged_style_str = self._merge_style_strings(base_style, style_str)
            # Validate the merged style
            self._validate_style_string(merged_style_str)
            merged_custom_styles[style_name] = merged_style_str

        # 3. Load CSS overrides if any
        css_overrides = config.get("css_overrides", {})

        # 4. Apply CSS overrides to embedded SVGs
        for style_name, final_style_str in merged_custom_styles.items():
            updated_style_str = self._maybe_modify_svg_css(
                style_name, final_style_str, css_overrides
            )
            merged_custom_styles[style_name] = updated_style_str

        config["custom_styles"] = merged_custom_styles

        logger.debug("Theme loaded and processed successfully.")
        return config

    def _merge_style_strings(self, base_style: str, custom_style: str) -> str:
        """
        Merge the base_style and custom_style into a single style string.
        Custom style properties override any conflicts in the base style.

        :param base_style: The global base style string.
        :param custom_style: The per-node custom style string.
        :return: A merged style string with duplicates overridden by custom_style.
        """
        if not base_style:
            # If no base style, just return the custom style
            return custom_style
        if not custom_style:
            # If no custom style, just return the base style
            return base_style

        # Extract any special "points=[]" segments so we can re-append them if needed
        # (some styles rely on "points=[]" but don't parse as "key=value" pairs)
        points_segments = []
        for seg in re.findall(r"(\bpoints=\[.*?\])", base_style + ";" + custom_style):
            points_segments.append(seg)

        # Convert base_style and custom_style to dictionaries
        base_dict = self._style_str_to_dict(base_style)
        custom_dict = self._style_str_to_dict(custom_style)

        # Merge (custom overrides base)
        for k, v in custom_dict.items():
            base_dict[k] = v

        # Convert merged dict back to style string
        merged_str = self._dict_to_style_str(base_dict)

        # Re-append any "points=[]" segments if they aren't already present
        for seg in points_segments:
            if seg not in merged_str:
                merged_str += seg + ";"

        return merged_str

    def _style_str_to_dict(self, style_str: str) -> Dict[str, str]:
        """
        Parse a style string of the form "key1=value1;key2=value2;..." into a dict.
        We skip 'points=[]' segments because they're not strictly "key=value" pairs.

        :param style_str: The style string to parse.
        :return: A dictionary of property->value.
        """
        style_dict = {}
        segments = style_str.split(";")
        for seg in segments:
            seg = seg.strip()
            if not seg or seg.startswith("points=["):
                # Skip or ignore points=[]
                continue
            if "=" in seg:
                k, v = seg.split("=", 1)
                style_dict[k] = v
        return style_dict

    def _dict_to_style_str(self, style_dict: Dict[str, str]) -> str:
        """
        Convert a dictionary of style properties into a "key=value;" style string.

        :param style_dict: Dict of style properties.
        :return: Single string "key1=val1;key2=val2;..."
        """
        segs = []
        for k, v in style_dict.items():
            segs.append(f"{k}={v}")
        return ";".join(segs) + ";" if segs else ""

    def _maybe_modify_svg_css(
        self, style_name: str, style_str: str, css_overrides: Dict[str, Dict[str, str]]
    ) -> str:
        """
        Check if the given style string references an SVG image. If so, and if CSS overrides
        exist for this style, decode the SVG, modify its <style> block, and re-encode it.
        """
        image_match = re.search(r"image=data:([^;]+)", style_str)
        if not image_match:
            return style_str

        image_data = image_match.group(1)
        if not image_data.startswith("image/svg+xml,"):
            return style_str

        base64_part = image_data[len("image/svg+xml,") :]
        try:
            svg_binary = base64.b64decode(base64_part)
        except Exception as e:
            logger.warning(f"Failed to decode base64 SVG for style '{style_name}': {e}")
            return style_str

        svg_str = svg_binary.decode("utf-8", errors="replace")
        style_overrides_for_style = css_overrides.get(style_name, {})

        if not style_overrides_for_style:
            # No overrides for this style
            return style_str

        logger.debug(f"Applying CSS overrides to style '{style_name}'.")
        new_svg_str = self._modify_svg_style_block(svg_str, style_overrides_for_style)
        if new_svg_str == svg_str:
            # No changes were made
            return style_str

        # Re-encode SVG
        new_base64 = base64.b64encode(new_svg_str.encode("utf-8")).decode("utf-8")
        new_image_data = "image/svg+xml," + new_base64
        new_style_str = style_str.replace(image_data, new_image_data, 1)

        logger.debug(f"CSS overrides applied successfully to style '{style_name}'.")
        return new_style_str

    def _modify_svg_style_block(
        self, svg_data: str, style_overrides: Dict[str, str]
    ) -> str:
        """
        Modify or create <style> block in the embedded SVG to apply the given CSS overrides.
        """
        style_start = svg_data.find("<style")
        style_end = -1
        style_content = ""

        if style_start != -1:
            style_close = svg_data.find("</style>", style_start)
            if style_close != -1:
                start_tag_end = svg_data.find(">", style_start)
                if start_tag_end != -1 and start_tag_end < style_close:
                    style_end = style_close + len("</style>")
                    style_content = svg_data[start_tag_end + 1 : style_close]

        # Split by '&#xa;' to preserve formatting of original style lines
        style_lines = style_content.split("&#xa;") if style_content else []

        # Parse existing classes from the style block
        class_rules = {}
        class_line_map = {}
        for i, line in enumerate(style_lines):
            m = re.match(r"(\s*)(\.[A-Za-z0-9_-]+)\{([^}]*)\}", line.strip())
            if m:
                indentation = m.group(1) or ""
                full_cls = m.group(2)
                cls_name = full_cls.lstrip(".")
                props_str = m.group(3)
                props = self._parse_properties(props_str)
                class_rules[cls_name] = props
                class_line_map[cls_name] = (i, indentation)

        # Apply overrides
        changed_classes = set()
        for key, val in style_overrides.items():
            parts = key.split("_", 1)
            if len(parts) != 2:
                logger.debug(
                    f"Skipping invalid override key '{key}'. Expected '<class>_<property>'."
                )
                continue
            class_name, prop_name = parts
            if class_name not in class_rules:
                # If class doesn't exist, create it
                class_rules[class_name] = {}
                class_line_map[class_name] = (None, "        ")
            class_rules[class_name][prop_name] = val
            changed_classes.add(class_name)

        # Rebuild changed or newly added class lines
        for cls_n in changed_classes:
            i, indent = class_line_map[cls_n]
            new_line = self._build_class_line(indent, cls_n, class_rules[cls_n])
            if i is not None:
                # Modify existing line
                style_lines[i] = new_line
            else:
                # Append a new class line
                style_lines.append(new_line)

        new_style_content = "&#xa;".join(style_lines)
        if new_style_content and not new_style_content.endswith("&#xa;"):
            new_style_content += "&#xa;"

        # If there was no style block, create one before </svg>
        if style_start == -1:
            insert_pos = svg_data.rfind("</svg>")
            if insert_pos == -1:
                # No closing svg? Just append the style at the end.
                return svg_data + "<style>" + new_style_content + "</style>"
            else:
                return (
                    svg_data[:insert_pos]
                    + "<style>"
                    + new_style_content
                    + "</style>"
                    + svg_data[insert_pos:]
                )
        else:
            # Replace existing style content
            return self._replace_style_block(
                svg_data, style_start, style_end, new_style_content
            )

    def _replace_style_block(
        self, svg_data: str, style_start: int, style_end: int, new_content: str
    ) -> str:
        """
        Replace the content of the existing <style> block with new_content.
        """
        start_tag_end = svg_data.find(">", style_start)
        if start_tag_end == -1 or style_end == -1:
            logger.debug(
                "Could not properly find the style block boundaries; returning unchanged SVG."
            )
            return svg_data

        style_open_tag = svg_data[style_start : start_tag_end + 1]
        return (
            svg_data[:style_start]
            + style_open_tag
            + new_content
            + "</style>"
            + svg_data[style_end:]
        )

    def _parse_properties(self, props_str: str) -> Dict[str, str]:
        """
        Parse CSS properties from a string like "fill:#001135;stroke:#FFF".
        """
        props = {}
        segments = props_str.split(";")
        for seg in segments:
            seg = seg.strip()
            if "=" in seg:  # skip invalid or unexpected segments
                continue
            if seg:
                kv = seg.split(":", 1)
                if len(kv) == 2:
                    prop = kv[0].strip()
                    val = kv[1].strip()
                    props[prop] = val
        return props

    def _build_class_line(
        self, indent: str, cls_name: str, props: Dict[str, str]
    ) -> str:
        """
        Rebuild a single CSS class line for the style block.
        """
        prop_segs = [f"{p}:{v}" for p, v in props.items()]
        prop_str = ";".join(prop_segs) + ";" if prop_segs else ""
        return f"{indent}.{cls_name}{{{prop_str}}}"

    def _validate_style_string(self, style_str: str):
        """
        Validate that the style string follows "key=value" pairs separated by semicolons.
        Known exception: 'points=[]' patterns are allowed.
        """
        if style_str.strip() == "":
            return
        segments = style_str.split(";")
        segments = [seg for seg in segments if seg.strip() != ""]

        for seg in segments:
            if "=" not in seg:
                if "points=[" in seg:
                    # 'points=[]' is an allowed special case
                    continue
                raise ThemeManagerError(
                    f"Invalid style segment '{seg}' in style string."
                )
            parts = seg.split("=", 1)
            if len(parts) != 2:
                raise ThemeManagerError(
                    f"Invalid style segment '{seg}' in style string."
                )
