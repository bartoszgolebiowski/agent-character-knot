from __future__ import annotations

import logging
from typing import Optional


def get_agent_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a configured logger for the agent.

    Args:
        name: Optional name for the logger. Defaults to 'agent'.

    Returns:
        A configured logging.Logger instance.
    """
    logger_name = name or "agent"
    logger = logging.getLogger(logger_name)

    # Only add handler if not already added
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger
