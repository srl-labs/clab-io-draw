import shutil
from pathlib import Path

import pytest
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
