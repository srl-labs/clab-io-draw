import json
import logging
import os
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


class GrafanaDashboard:
    """
    Manages the creation of a Grafana dashboard and associated panel config from the diagram data.
    """

    def __init__(self, diagram=None, grafana_config_path: Optional[str] = None):
        """
        :param diagram: Diagram object that includes node and link data.
        :param grafana_config_path: Path to the YAML file containing grafana panel config (targets, thresholds, etc.).
        """
        self.diagram = diagram
        self.links = diagram.get_links_from_nodes() if diagram else []
        # The file where the final JSON will be saved
        self.dashboard_filename = (
            diagram.grafana_dashboard_file if diagram else "network_telemetry.json"
        )

        # Determine config path (default or user-provided)
        base_dir = os.getenv("APP_BASE_DIR", "")
        if grafana_config_path is None:
            # default location in core/grafana/config
            grafana_config_path = os.path.join(
                base_dir, "core/grafana/config/default_grafana_panel_config.yml"
            )

        self.grafana_config = self._load_grafana_config(grafana_config_path)

    def _load_grafana_config(self, path: str) -> dict:
        """
        Load the Grafana panel config from a YAML file.

        :param path: Path to the YAML config.
        :return: A dict with 'targets', 'thresholds', 'label_config'.
        """
        logger.debug(f"Loading Grafana config from: {path}")
        if not os.path.exists(path):
            logger.error(f"Grafana config file not found: {path}")
            raise FileNotFoundError(f"Grafana config file not found: {path}")

        with open(path, "r") as f:
            config = yaml.safe_load(f)

        required_keys = ["targets", "thresholds", "label_config"]
        for key in required_keys:
            if key not in config:
                logger.warning(
                    f"Missing key '{key}' in Grafana config '{path}'. Please verify the YAML structure."
                )
                if key == "targets":
                    config["targets"] = []
                elif key == "thresholds":
                    config["thresholds"] = {"operstate": [], "traffic": []}
                elif key == "label_config":
                    config["label_config"] = {}

        return config

    def create_dashboard(self, panel_config: str) -> str:
        """
        Create a Grafana dashboard JSON string by loading a base template (flow_panel_template.json)
        and updating the panel with new targets from the config, plus embedding the panel_config.

        :param panel_config: YAML panel configuration as a string (the result of create_panel_yaml()).
        :return: The final dashboard as a JSON string.
        """
        logger.debug("Creating Grafana dashboard JSON from template...")

        base_dir = os.getenv("APP_BASE_DIR", "")
        template_path = os.path.join(
            base_dir, "core/grafana/templates/flow_panel_template.json"
        )
        if not os.path.exists(template_path):
            logger.error(f"Template not found at {template_path}")
            raise FileNotFoundError(
                f"Grafana template file not found at {template_path}"
            )

        with open(template_path, "r") as file:
            dashboard_json = json.load(file)

        # Update the first panel’s 'targets' from the config
        if "panels" in dashboard_json and len(dashboard_json["panels"]) > 0:
            panel = dashboard_json["panels"][0]

            new_targets = []
            for i, tgt in enumerate(self.grafana_config["targets"]):
                # build target object as per template structure
                datasource_type = tgt.get("datasource", "prometheus")
                expr = tgt.get("expr", "")
                legend_format = tgt.get("legend_format", "")
                new_targets.append(
                    {
                        "datasource": {"type": datasource_type},
                        "editorMode": "code",
                        "expr": expr,
                        "hide": tgt.get("hide", False),
                        "instant": tgt.get("instant", False),
                        "legendFormat": legend_format,
                        "range": tgt.get("range", True),
                        # assign refId A, B, C,... automatically
                        "refId": chr(ord("A") + i),
                    }
                )

            panel["targets"] = new_targets

            # Also inject the newly built panel_yaml into `panelConfig`
            if "options" in panel:
                panel["options"]["panelConfig"] = panel_config

        dashboard_str = json.dumps(dashboard_json, indent=2)
        logger.debug("Grafana dashboard JSON created successfully.")
        return dashboard_str

    def create_panel_yaml(self) -> str:
        """
        Create the flow panel YAML configuration, pulling threshold info, label config, etc.
        from the loaded grafana config, plus adding link data.

        :return: String of the final YAML panel configuration.
        """
        logger.debug("Creating panel YAML from links and grafana config...")

        from ruamel.yaml import YAML, CommentedMap, CommentedSeq

        yaml = YAML()
        yaml.explicit_start = True
        yaml.width = 4096

        root = CommentedMap()

        # Thresholds from config
        thresholds_operstate_config = self.grafana_config["thresholds"].get(
            "operstate", []
        )
        thresholds_traffic_config = self.grafana_config["thresholds"].get("traffic", [])
        label_cfg = self.grafana_config["label_config"]

        # Build the oper-state thresholds
        thresholds_operstate = CommentedSeq()
        for item in thresholds_operstate_config:
            thresholds_operstate.append(
                {"color": item["color"], "level": item["level"]}
            )
        thresholds_operstate.yaml_set_anchor("thresholds-operstate", always_dump=True)

        # Build the traffic thresholds
        thresholds_traffic = CommentedSeq()
        for item in thresholds_traffic_config:
            thresholds_traffic.append({"color": item["color"], "level": item["level"]})
        thresholds_traffic.yaml_set_anchor("thresholds-traffic", always_dump=True)

        label_config_map = CommentedMap()
        label_config_map["separator"] = label_cfg.get("separator", "replace")
        label_config_map["units"] = label_cfg.get("units", "bps")
        label_config_map["decimalPoints"] = label_cfg.get("decimalPoints", 1)
        label_config_map["valueMappings"] = label_cfg.get("valueMappings", [])
        label_config_map.yaml_set_anchor("label-config", always_dump=True)

        root["anchors"] = anchors = CommentedMap()
        anchors["thresholds-operstate"] = thresholds_operstate
        anchors["thresholds-traffic"] = thresholds_traffic
        anchors["label-config"] = label_config_map

        root["cellIdPreamble"] = "cell-"
        cells = CommentedMap()
        root["cells"] = cells

        # Add link data
        for link in self.links:
            source_name = link.source.name
            source_intf = link.source_intf
            target_name = link.target.name
            target_intf = link.target_intf

            # oper-state cell
            cell_id_operstate = (
                f"{source_name}:{source_intf}:{target_name}:{target_intf}"
            )
            dataRef_operstate = f"oper-state:{source_name}:{source_intf}"
            fillColor_operstate = CommentedMap()
            fillColor_operstate["thresholds"] = thresholds_operstate

            cell_operstate = CommentedMap()
            cell_operstate["dataRef"] = dataRef_operstate
            cell_operstate["fillColor"] = fillColor_operstate
            cells[cell_id_operstate] = cell_operstate

            # traffic cell
            cell_id_traffic = (
                f"link_id:{source_name}:{source_intf}:{target_name}:{target_intf}"
            )
            dataRef_traffic = f"{source_name}:{source_intf}:out"

            strokeColor_traffic = CommentedMap()
            strokeColor_traffic["thresholds"] = thresholds_traffic

            cell_traffic = CommentedMap()
            cell_traffic["dataRef"] = dataRef_traffic
            cell_traffic["label"] = label_config_map
            cell_traffic["strokeColor"] = strokeColor_traffic
            cells[cell_id_traffic] = cell_traffic

        import io

        stream = io.StringIO()
        yaml.dump(root, stream)
        panel_yaml = stream.getvalue()
        logger.debug("Panel YAML created successfully.")
        return panel_yaml
