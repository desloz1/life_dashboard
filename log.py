import logging
import os
from logging.handlers import RotatingFileHandler

_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(_DIR, "app.log")

_configured = False


def _ensure_config():
    global _configured
    if _configured:
        return
    _configured = True
    logger = logging.getLogger("life_dashboard")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(handler)


def get_logger(name="life_dashboard"):
    _ensure_config()
    return logging.getLogger(name)
