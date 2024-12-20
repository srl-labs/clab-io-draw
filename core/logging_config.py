import logging

def configure_logging(level=logging.INFO):
    """
    Configure the logging settings for the application.
    Adjust the format and level as desired.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
