import json
import os
import xml.etree.ElementTree as ET

class GrafanaDashboard:
    def __init__(self, diagram=None):
        self.diagram = diagram
        self.links = self.diagram.get_links_from_nodes()
        self.dashboard_filename = self.diagram.grafana_dashboard_file


    def create_dashboard(self):
        # We just need the subtree objects from mxGraphModel.Single page drawings only
        xmlTree = ET.fromstring(self.diagram.dump_xml())
        subXmlTree = xmlTree.findall('.//mxGraphModel')[0]

        # Define Query rules for the Panel, rule_expr needs to match the collector metric name
        # Legend format needs to match the format expected by the metric
        panelQueryList = {
            "IngressTraffic": {
                "rule_expr": "gnmic_in_bps",
                "legend_format": '{{source}}:{{interface_name}}:in',
            },
            "EgressTraffic": {
                "rule_expr": "gnmic_out_bps",
                "legend_format": '{{source}}:{{interface_name}}:out',
            },
            "ItfOperState": {
                "rule_expr": "gnmic_oper_state",
                "legend_format": 'oper_state:{{source}}:{{interface_name}}',
            },
        }
        # Create a targets list to embed in the JSON object, we add all the other default JSON attributes to the list
        targetsList = []
        for query in panelQueryList:
            targetsList.append(
                self.gf_dashboard_datasource_target(
                    rule_expr=panelQueryList[query]["rule_expr"],
                    legend_format=panelQueryList[query]["legend_format"],
                    refId=query,
                )
            )

        # Create the Rules Data
        rulesData = []
        i = 0
        for link in self.links:
            link_id =  f"{link.source.name}:{link.source_intf}:{link.target.name}:{link.target_intf}"

            # Traffic in
            rulesData.append(
                self.gf_flowchart_rule_traffic(
                    ruleName=f"{link.source.name}:{link.source_intf}:in",
                    metric=f"{link.source.name}:{link.source_intf}:in",
                    link_id=link_id,
                    order=i,
                )
            )
             
            i = i + 2
            

            # Port State:
            rulesData.append(
                self.gf_flowchart_rule_operstate(
                    ruleName=f"oper_state:{link.source.name}:{link.source_intf}",
                    metric=f"oper_state:{link.source.name}:{link.source_intf}",
                    link_id=link_id,
                    order=i + 3,
                )
            )
            i = i + 2

        # Create the Panel
        flowchart_panel = self.gf_flowchart_panel_template(
            xml=ET.tostring(subXmlTree, encoding="unicode"),
            rulesData=rulesData,
            panelTitle="Network Telemetry",
            targetsList=targetsList,
        )
        # Create a dashboard from the panel
        dashboard_json = json.dumps(
            self.gf_dashboard_template(
                panels=flowchart_panel,
                dashboard_name=os.path.splitext(self.dashboard_filename)[0],
            ),
            indent=4,
        )
        with open(self.dashboard_filename, 'w') as f:
            f.write(dashboard_json)
            print("Saved Grafana dashboard file to:", self.dashboard_filename)

    def gf_dashboard_datasource_target(self, rule_expr="promql_query", legend_format=None, refId="Query1"):
        """
        Dictionary containing information relevant to the Targets queried
        """
        target = {
            "datasource": {
                "type": "prometheus",
                "uid": "${DS_PROMETHEUS}"
            },
            "editorMode": "code",
            "expr": rule_expr,
            "instant": False,
            "legendFormat": legend_format,
            "range": True,
            "refId": refId,
        }
        return target

    def gf_flowchart_rule_traffic(self, ruleName="traffic:inOrOut", metric=None, link_id=None, order=1):
        """
        Dictionary containing information relevant to the traffic Rules
        """
        # Load the traffic rule template from file
        with open("lib/templates/traffic_rule_template.json") as f:
            rule = json.load(f)

        rule["alias"] = ruleName
        rule["pattern"] = metric
        rule["mapsDat"]["shapes"]["dataList"][0]["pattern"] = link_id
        rule["mapsDat"]["texts"]["dataList"][0]["pattern"] = link_id
        rule["order"] = order

        return rule

    def gf_flowchart_rule_operstate(self, ruleName="oper_state", metric=None, link_id=None, order=1):
        """
        Dictionary containing information relevant to the Operational State Rules
        """
        # Load the operstate rule template from file
        with open("lib/templates/operstate_rule_template.json") as f:
            rule = json.load(f)

        rule["alias"] = ruleName
        rule["pattern"] = metric
        rule["mapsDat"]["shapes"]["dataList"][0]["pattern"] = link_id
        rule["order"] = order

        return rule

    def gf_flowchart_panel_template(self, xml=None, rulesData=None, targetsList=None, panelTitle="Network Topology"):
        """
        Dictionary containing information relevant to the Panels Section in the JSON Dashboard
        Embedding of the XML diagram, the Rules and the Targets
        """
        # Load the panel template from file
        with open("lib/templates/panel_template.json") as f:
            panel = json.load(f)

        panel[0]["flowchartsData"]["flowcharts"][0]["xml"] = xml
        panel[0]["rulesData"]["rulesData"] = rulesData
        panel[0]["targets"] = targetsList
        panel[0]["title"] = panelTitle

        return panel

    def gf_dashboard_template(self, panels=None, dashboard_name="lab-telemetry"):
        """
        Dictionary containing information relevant to the Grafana Dashboard Root JSON object
        """
        # Load the dashboard template from file
        with open("lib/templates/dashboard_template.json") as f:
            dashboard = json.load(f)

        dashboard["panels"] = panels
        dashboard["title"] = dashboard_name

        return dashboard