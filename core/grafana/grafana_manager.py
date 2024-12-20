import json
import os
import xml.etree.ElementTree as ET
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
import yaml

class GrafanaDashboard:
    def __init__(self, diagram=None, panel_config=None):
        self.diagram = diagram
        self.links = self.diagram.get_links_from_nodes()
        self.dashboard_filename = self.diagram.grafana_dashboard_file

    def create_dashboard(self, panel_config):
        # Path to the dashboard JSON template
        base_dir = os.getenv("APP_BASE_DIR", "")
        template_path = os.path.join(base_dir, "core/grafana/templates/flow_panel_template.json")

        # Load the dashboard template from file
        with open(template_path, 'r') as file:
            dashboard_json = json.load(file)

        # Insert the YAML configuration as a string into the panelConfig of the relevant panel
        for panel in dashboard_json['panels']:
            if 'options' in panel:
                panel['options']['panelConfig'] = panel_config

        return json.dumps(dashboard_json, indent=2)

    def create_panel_yaml(self):
        from ruamel.yaml import YAML, CommentedMap, CommentedSeq

        yaml = YAML()
        yaml.explicit_start = True  # To include '---' at the start
        yaml.width = 4096  # prevent line wrapping

        root = CommentedMap()

        # Anchors and Aliases
        thresholds_operstate = CommentedSeq()
        thresholds_operstate.append({'color': 'red', 'level': 0})
        thresholds_operstate.append({'color': 'green', 'level': 1})

        thresholds_operstate.yaml_set_anchor('thresholds-operstate', always_dump=True)

        thresholds_traffic = CommentedSeq()
        thresholds_traffic.append({'color': 'gray', 'level': 0})
        thresholds_traffic.append({'color': 'green', 'level': 199999})
        thresholds_traffic.append({'color': 'yellow', 'level': 500000})
        thresholds_traffic.append({'color': 'orange', 'level': 1000000})
        thresholds_traffic.append({'color': 'red', 'level': 5000000})

        thresholds_traffic.yaml_set_anchor('thresholds-traffic', always_dump=True)

        label_config = CommentedMap()
        label_config['separator'] = "replace"
        label_config['units'] = "bps"
        label_config['decimalPoints'] = 1
        label_config['valueMappings'] = [
            {'valueMax': 199999, 'text': "\u200B"},
            {'valueMin': 200000}
        ]

        label_config.yaml_set_anchor('label-config', always_dump=True)

        # Anchors entry in root
        root['anchors'] = anchors = CommentedMap()

        anchors['thresholds-operstate'] = thresholds_operstate
        anchors['thresholds-traffic'] = thresholds_traffic
        anchors['label-config'] = label_config

        # cellIdPreamble
        root['cellIdPreamble'] = 'cell-'

        # cells
        cells = CommentedMap()
        root['cells'] = cells
        for link in self.links:
            source_name = link.source.name
            source_intf = link.source_intf
            target_name = link.target.name
            target_intf = link.target_intf

            # Operstate cell
            cell_id_operstate = f"{source_name}:{source_intf}:{target_name}:{target_intf}"
            dataRef_operstate = f"oper-state:{source_name}:{source_intf}"

            # fillColor thresholds referencing the anchor
            fillColor_operstate = CommentedMap()
            fillColor_operstate['thresholds'] = thresholds_operstate  # reference anchor

            cell_operstate = CommentedMap()
            cell_operstate['dataRef'] = dataRef_operstate
            cell_operstate['fillColor'] = fillColor_operstate

            cells[cell_id_operstate] = cell_operstate

            # Traffic cell
            cell_id_traffic = f"link_id:{source_name}:{source_intf}:{target_name}:{target_intf}"

            dataRef_traffic = f"{source_name}:{source_intf}:out"

            strokeColor_traffic = CommentedMap()
            strokeColor_traffic['thresholds'] = thresholds_traffic  # reference anchor

            cell_traffic = CommentedMap()
            cell_traffic['dataRef'] = dataRef_traffic
            cell_traffic['label'] = label_config  # reference anchor
            cell_traffic['strokeColor'] = strokeColor_traffic

            cells[cell_id_traffic] = cell_traffic

        import io
        stream = io.StringIO()
        yaml.dump(root, stream)
        panel_yaml = stream.getvalue()
        return panel_yaml
