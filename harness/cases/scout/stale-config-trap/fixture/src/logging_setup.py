"""Structured logging setup, unrelated to config or validation (noise file)."""

import logging


def configure_logging(level="INFO"):
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")
