"""Logging configuration for TraitorSim."""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(verbose: bool = True, save_to_file: bool = True) -> logging.Logger:
    """
    Configure logging for the application.

    Args:
        verbose: If True, set level to DEBUG, otherwise INFO
        save_to_file: If True, also log to file

    Returns:
        Configured logger
    """
    # Create root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )
    simple_formatter = logging.Formatter("%(message)s")

    # Console handler (simple format for main game events)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)

    # Only show game events in console
    console_handler.addFilter(lambda record: record.name.startswith("traitorsim"))

    logger.addHandler(console_handler)

    # File handler (detailed format) if requested
    if save_to_file:
        try:
            # Create logs directory
            log_dir = Path("data/games")
            log_dir.mkdir(parents=True, exist_ok=True)

            # Create timestamped log file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"game_{timestamp}.log"

            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(detailed_formatter)
            logger.addHandler(file_handler)

            logger.info(f"Logging to file: {log_file}")
        except Exception as e:
            logger.error(f"Failed to create file handler: {e}")

    return logger
