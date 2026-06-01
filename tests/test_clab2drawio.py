import json
import shutil
from pathlib import Path

import pytest
from defusedxml import ElementTree
from typer.testing import CliRunner

from clab_io_draw.clab2drawio import app

LAB_EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "lab-examples"
GRAFANA_CONFIG = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "clab_io_draw"
    / "core"
    / "grafana"
    / "config"
    / "default_grafana_panel_config.yml"
)


def _yaml_files():
    return sorted(LAB_EXAMPLES_DIR.glob("*.clab.yml"))


def _absolute_geometry(root, object_id):
    cell = root.find(f".//object[@id='{object_id}']/mxCell")
    assert cell is not None  # noqa: S101
    geometry = cell.find("mxGeometry")
    assert geometry is not None  # noqa: S101

    x = float(geometry.get("x", "0"))
    y = float(geometry.get("y", "0"))
    parent_id = cell.get("parent")
    if parent_id and parent_id != "1":
        parent_geometry = root.find(f".//mxCell[@id='{parent_id}']/mxGeometry")
        assert parent_geometry is not None  # noqa: S101
        x += float(parent_geometry.get("x", "0"))
        y += float(parent_geometry.get("y", "0"))

    return x, y, geometry


ARG_SETS = [
    (
        [
            "--include-unlinked-nodes",
            "--no-links",
            "--layout",
            "horizontal",
            "--theme",
            "nokia_modern",
            "--log-level",
            "debug",
        ],
        True,
        "nokia_modern_horizontal",
    ),
    (
        [
            "-g",
            "--theme",
            "grafana",
            "--grafana-config",
            str(GRAFANA_CONFIG),
            "--include-unlinked-nodes",
            "--no-links",
            "--layout",
            "horizontal",
            "--log-level",
            "debug",
        ],
        False,
        "grafana_dashboard",
    ),
    (
        [
            "--layout",
            "vertical",
            "--theme",
            "nokia",
            "--include-unlinked-nodes",
            "--log-level",
            "debug",
        ],
        True,
        "nokia_vertical",
    ),
    (
        [
            "--layout",
            "vertical",
            "--theme",
            "nokia_modern",
        ],
        True,
        "nokia_modern_vertical",
    ),
]

IDS = [case[2] for case in ARG_SETS]


@pytest.mark.parametrize("lab_file", _yaml_files(), ids=lambda p: p.stem)
@pytest.mark.parametrize("extra_args,use_output,case_id", ARG_SETS, ids=IDS)
def test_clab2drawio_combinations(tmp_path, lab_file, extra_args, use_output, case_id):
    runner = CliRunner()
    lab_tmp = tmp_path / lab_file.name
    shutil.copy(lab_file, lab_tmp)

    cmd = ["-i", str(lab_tmp)]
    if use_output:
        out_file = tmp_path / f"{lab_file.stem}_{case_id}.drawio"
        cmd.extend(["-o", str(out_file)])
    else:
        out_file = lab_tmp.with_suffix(".drawio")

    cmd.extend(extra_args)
    result = runner.invoke(app, cmd)
    assert result.exit_code == 0, result.output  # noqa: S101
    assert out_file.exists()  # noqa: S101


def test_clab2drawio_accepts_empty_node_definitions(tmp_path):
    runner = CliRunner()
    lab_file = tmp_path / "empty-node-definitions.clab.yml"
    lab_file.write_text(
        """\
name: mtik
prefix: ""
topology:
  defaults:
    kind: ceos
  kinds:
    ceos:
      image: ceos:4.35.0F
  nodes:
    ceos1:
    ceos2:
  links:
    - endpoints: ["ceos1:eth1", "ceos2:eth1"]
""",
        encoding="utf-8",
    )
    out_file = tmp_path / "empty-node-definitions.drawio"

    result = runner.invoke(app, ["-i", str(lab_file), "-o", str(out_file)])

    assert result.exit_code == 0, result.output  # noqa: S101
    assert out_file.exists()  # noqa: S101


def test_default_drawio_output_is_deterministic(tmp_path):
    runner = CliRunner()
    lab_tmp = tmp_path / "clos01.clab.yml"
    shutil.copy(LAB_EXAMPLES_DIR / "clos01.clab.yml", lab_tmp)
    out_a = tmp_path / "clos01-a.drawio"
    out_b = tmp_path / "clos01-b.drawio"

    result_a = runner.invoke(app, ["-i", str(lab_tmp), "-o", str(out_a)])
    result_b = runner.invoke(app, ["-i", str(lab_tmp), "-o", str(out_b)])

    assert result_a.exit_code == 0, result_a.output  # noqa: S101
    assert result_b.exit_code == 0, result_b.output  # noqa: S101
    assert out_a.read_text(encoding="utf-8") == out_b.read_text(encoding="utf-8")  # noqa: S101


def test_drawio_output_has_unique_ids_with_endpoint_labels(tmp_path):
    runner = CliRunner()
    lab_tmp = tmp_path / "special_endpoints.clab.yml"
    shutil.copy(LAB_EXAMPLES_DIR / "special_endpoints.clab.yml", lab_tmp)
    out_file = tmp_path / "special_endpoints.drawio"

    result = runner.invoke(app, ["-i", str(lab_tmp), "-o", str(out_file)])

    assert result.exit_code == 0, result.output  # noqa: S101
    root = ElementTree.parse(out_file).getroot()
    ids = [elem.get("id") for elem in root.iter() if elem.get("id")]
    assert len(ids) == len(set(ids))  # noqa: S101

    endpoint_labels = [
        obj
        for obj in root.iter("object")
        if (obj.get("id") or "").startswith("label:link:")
    ]
    assert endpoint_labels  # noqa: S101
    for label in endpoint_labels:
        label_cell = label.find("mxCell")
        assert label_cell is not None  # noqa: S101
        parent_id = label_cell.get("parent")
        assert parent_id and parent_id != "1"  # noqa: S101

        node_cell = root.find(f".//object[@id='{parent_id}']/mxCell")
        assert node_cell is not None  # noqa: S101
        assert label_cell.get("parent") == parent_id  # noqa: S101

    link_cells = [
        obj.find("mxCell")
        for obj in root.iter("object")
        if (obj.get("id") or "").startswith("link_id:link:")
    ]
    assert link_cells  # noqa: S101
    assert all(cell is not None and cell.get("parent") == "1" for cell in link_cells)  # noqa: S101


def test_fixed_positions_are_preserved_without_scaling(tmp_path):
    runner = CliRunner()
    lab_file = tmp_path / "fixed.clab.yml"
    lab_file.write_text(
        """\
name: fixed
prefix: ""
topology:
  nodes:
    left:
      kind: linux
      labels:
        graph-posX: 10
        graph-posY: 20
    right:
      kind: linux
      labels:
        graph-posX: 110
        graph-posY: 20
  links:
    - endpoints: ["left:eth1", "right:eth1"]
""",
        encoding="utf-8",
    )
    out_file = tmp_path / "fixed.drawio"

    result = runner.invoke(app, ["-i", str(lab_file), "-o", str(out_file)])

    assert result.exit_code == 0, result.output  # noqa: S101
    root = ElementTree.parse(out_file).getroot()
    left_x, left_y, _ = _absolute_geometry(root, "left")
    right_x, right_y, _ = _absolute_geometry(root, "right")
    assert left_x == 10  # noqa: S101
    assert left_y == 20  # noqa: S101
    assert right_x == 110  # noqa: S101
    assert right_y == 20  # noqa: S101
    assert right_x - left_x == 100  # noqa: S101
    assert right_y - left_y == 0  # noqa: S101


def test_partial_fixed_positions_keep_anchor_and_layout_free_nodes(tmp_path):
    runner = CliRunner()
    lab_file = tmp_path / "partial-fixed.clab.yml"
    lab_file.write_text(
        """\
name: partial-fixed
prefix: ""
topology:
  nodes:
    fixed:
      kind: linux
      labels:
        graph-posX: 250
        graph-posY: 90
    middle:
      kind: linux
    free:
      kind: linux
  links:
    - endpoints: ["fixed:eth1", "middle:eth1"]
    - endpoints: ["middle:eth2", "free:eth1"]
""",
        encoding="utf-8",
    )
    out_file = tmp_path / "partial-fixed.drawio"

    result = runner.invoke(app, ["-i", str(lab_file), "-o", str(out_file)])

    assert result.exit_code == 0, result.output  # noqa: S101
    root = ElementTree.parse(out_file).getroot()
    fixed_x, fixed_y, _ = _absolute_geometry(root, "fixed")
    middle_x, _, _ = _absolute_geometry(root, "middle")
    free_x, _, _ = _absolute_geometry(root, "free")
    assert fixed_x == 250  # noqa: S101
    assert fixed_y == 90  # noqa: S101
    assert middle_x != 0  # noqa: S101
    assert free_x != 0  # noqa: S101


def test_node_annotation_label_position_overrides_theme_default(tmp_path):
    runner = CliRunner()
    lab_file = tmp_path / "label-position.clab.yml"
    lab_file.write_text(
        """\
name: label-position
prefix: ""
topology:
  nodes:
    srl1:
      kind: nokia_srlinux
    ceos1:
      kind: ceos
  links:
    - endpoints: ["srl1:e1-1", "ceos1:eth1"]
""",
        encoding="utf-8",
    )
    lab_file.with_suffix(lab_file.suffix + ".annotations.json").write_text(
        json.dumps({"nodeAnnotations": [{"id": "srl1", "labelPosition": "top"}]}),
        encoding="utf-8",
    )
    out_file = tmp_path / "label-position.drawio"

    result = runner.invoke(app, ["-i", str(lab_file), "-o", str(out_file)])

    assert result.exit_code == 0, result.output  # noqa: S101
    root = ElementTree.parse(out_file).getroot()
    node_cell = root.find(".//object[@id='srl1']/mxCell")
    assert node_cell is not None  # noqa: S101
    style = node_cell.get("style")
    assert "verticalLabelPosition=top;" in style  # noqa: S101
    assert "verticalAlign=bottom;" in style  # noqa: S101


def test_grafana_ports_stay_circular_and_close_to_nodes(tmp_path):
    runner = CliRunner()
    lab_file = tmp_path / "grafana-ports.clab.yml"
    lab_file.write_text(
        """\
name: grafana-ports
prefix: ""
topology:
  nodes:
    left:
      kind: linux
    right:
      kind: linux
  links:
    - endpoints: ["left:eth1", "right:eth1"]
""",
        encoding="utf-8",
    )
    out_file = lab_file.with_suffix(".drawio")

    result = runner.invoke(app, ["-i", str(lab_file), "-g"])

    assert result.exit_code == 0, result.output  # noqa: S101
    assert out_file.exists()  # noqa: S101
    root = ElementTree.parse(out_file).getroot()

    source_port = root.find(".//object[@id='left:eth1:right:eth1']")
    target_port = root.find(".//object[@id='right:eth1:left:eth1']")
    assert source_port is not None  # noqa: S101
    assert target_port is not None  # noqa: S101
    assert source_port.get("label") == "1"  # noqa: S101
    assert target_port.get("label") == "1"  # noqa: S101

    source_cell = source_port.find("mxCell")
    target_cell = target_port.find("mxCell")
    assert source_cell is not None  # noqa: S101
    assert target_cell is not None  # noqa: S101
    assert "ellipse" in (source_cell.get("style") or "")  # noqa: S101
    assert "ellipse" in (target_cell.get("style") or "")  # noqa: S101

    def distance_from_node(node_id, port_id):
        node_x, node_y, node_geometry = _absolute_geometry(root, node_id)
        port_x, port_y, port_geometry = _absolute_geometry(root, port_id)
        node_w = float(node_geometry.get("width", "0"))
        node_h = float(node_geometry.get("height", "0"))
        port_w = float(port_geometry.get("width", "0"))
        port_h = float(port_geometry.get("height", "0"))
        port_center_x = port_x + port_w / 2
        port_center_y = port_y + port_h / 2
        outside_x = max(
            node_x - port_center_x,
            port_center_x - (node_x + node_w),
            0,
        )
        outside_y = max(
            node_y - port_center_y,
            port_center_y - (node_y + node_h),
            0,
        )
        return max(outside_x, outside_y)

    assert 5 <= distance_from_node("left", "left:eth1:right:eth1") <= 7  # noqa: S101
    assert 5 <= distance_from_node("right", "right:eth1:left:eth1") <= 7  # noqa: S101

    traffic_edges = [
        obj for obj in root.iter("object") if (obj.get("id") or "").startswith("link_id:")
    ]
    assert traffic_edges  # noqa: S101
    assert all(edge.get("label") == "rate" for edge in traffic_edges)  # noqa: S101

    panel_yaml = lab_file.with_suffix(".grafana.flow_panel.yaml").read_text(
        encoding="utf-8"
    )
    assert "left:eth1:right:eth1" in panel_yaml  # noqa: S101
    assert "link_id:left:eth1:right:eth1" in panel_yaml  # noqa: S101


def test_annotation_positions_are_normalized_to_canvas_margin(tmp_path):
    runner = CliRunner()
    lab_file = tmp_path / "annotated.clab.yml"
    lab_file.write_text(
        """\
name: annotated
prefix: ""
topology:
  nodes:
    ceos1:
      kind: ceos
    ceos2:
      kind: ceos
  links:
    - endpoints: ["ceos1:eth1", "ceos2:eth1"]
""",
        encoding="utf-8",
    )
    lab_file.with_suffix(lab_file.suffix + ".annotations.json").write_text(
        json.dumps(
            {
                "nodeAnnotations": [
                    {"id": "ceos1", "position": {"x": 380, "y": 340}},
                    {"id": "ceos2", "position": {"x": 520, "y": 340}},
                ]
            }
        ),
        encoding="utf-8",
    )
    out_file = tmp_path / "annotated.drawio"

    result = runner.invoke(app, ["-i", str(lab_file), "-o", str(out_file)])

    assert result.exit_code == 0, result.output  # noqa: S101
    root = ElementTree.parse(out_file).getroot()
    model = root.find(".//mxGraphModel")
    assert model is not None  # noqa: S101
    ceos1_x, ceos1_y, _ = _absolute_geometry(root, "ceos1")
    ceos2_x, ceos2_y, _ = _absolute_geometry(root, "ceos2")
    assert ceos1_x == 80  # noqa: S101
    assert ceos1_y == 80  # noqa: S101
    assert ceos2_x == 220  # noqa: S101
    assert ceos2_y == 80  # noqa: S101
    assert float(model.get("pageWidth")) == 364  # noqa: S101
    assert float(model.get("pageHeight")) == 224  # noqa: S101
