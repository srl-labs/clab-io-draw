import logging
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

DRAWIO_VERSION = "27.0.9"
DRAWIO_URL = f"https://github.com/jgraph/drawio-desktop/releases/download/v{DRAWIO_VERSION}/drawio-x86_64-{DRAWIO_VERSION}.AppImage"


def _download_drawio(appimage_path: Path) -> None:
    logger.info("Downloading draw.io AppImage...")
    urllib.request.urlretrieve(DRAWIO_URL, appimage_path)
    appimage_path.chmod(0o755)


def _ensure_drawio() -> Path:
    env_bin = os.environ.get("DRAWIO_BIN")
    if env_bin and Path(env_bin).exists():
        return Path(env_bin)

    cache_dir = Path.home() / ".cache" / "clab_io_draw"
    cache_dir.mkdir(parents=True, exist_ok=True)
    appimage_path = cache_dir / "drawio.AppImage"
    if not appimage_path.exists():
        _download_drawio(appimage_path)
    return appimage_path


def _install_plugin() -> None:
    plugin_src = Path(__file__).with_name("svgdata.js")
    plugin_dir = Path.home() / ".config" / "draw.io" / "plugins"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    plugin_dst = plugin_dir / "svgdata.js"
    try:
        shutil.copy(plugin_src, plugin_dst)
    except Exception as exc:
        logger.debug(f"Could not copy plugin: {exc}")


def export_svg_with_metadata(drawio_file: str, svg_file: str) -> None:
    """Use draw.io CLI to export a diagram to SVG with metadata."""
    drawio_bin = _ensure_drawio()
    _install_plugin()

    cmd = [
        "xvfb-run",
        str(drawio_bin),
        "--appimage-extract-and-run",
        "--no-sandbox",
        "--export",
        "--format",
        "svg",
        "--enable-plugins",
        "--output",
        svg_file,
        drawio_file,
    ]
    logger.debug("Running: %s", " ".join(cmd))
    subprocess.run(cmd, check=True)
