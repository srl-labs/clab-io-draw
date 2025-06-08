import logging

from rich.logging import RichHandler
from rich.traceback import install


def configure_logging(level: int = logging.INFO) -> None:
    """Configure the logging settings for the application."""

    install(show_locals=False)
    handler = RichHandler(
        show_time=False,
        show_path=False,
        rich_tracebacks=True,
        markup=True,
    )

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[handler],
    )
