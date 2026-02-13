"""
Structured Logging Configuration.

Sets up JSON-formatted structured logging for the application.
"""

from __future__ import annotations

import logging
import logging.config
import sys
from pathlib import Path
from typing import Optional

import yaml


def setup_logging(
    config_path: Optional[str] = None,
    default_level: int = logging.INFO,
) -> None:
    """
    Configure logging from a YAML file or fall back to defaults.

    Args:
        config_path: Path to logging.yml. If None, uses configs/logging.yml.
        default_level: Fallback logging level.
    """
    if config_path is None:
        backend_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
        config_path = str(backend_dir / "configs" / "logging.yml")

    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            if config:
                logging.config.dictConfig(config)
                return

    # Fallback: basic structured logging
    logging.basicConfig(
        level=default_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)
