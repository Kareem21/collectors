"""Main Entry Point for QRadar Collector.

============================================================================
This is the main entry point for the QRadar collector application.

When run as a script or module, it:
1. Initializes logging
2. Creates the Collector instance
3. Starts the collection daemon
4. Handles graceful shutdown on Ctrl+C

Usage:
  poetry run python -m src
  or
  QRadarCollector (if installed via pip/poetry)
============================================================================
"""

import logging
import os
import sys

from src.collector.collector import Collector
from src.collector.exception import CollectorConfigError

LOG_PREFIX = "[Main]"


def main() -> None:
    """Define the main function to run the collector."""
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"{LOG_PREFIX} Starting QRadar collector...")
        collector = Collector()
        collector.start()
    except KeyboardInterrupt:
        logger.info(f"{LOG_PREFIX} Collector stopped by user (Ctrl+C)")
        os._exit(0)
    except CollectorConfigError as e:
        logger.error(f"{LOG_PREFIX} Configuration error: {e}")
        sys.exit(2)
    except Exception as e:
        logger.exception(f"{LOG_PREFIX} Fatal error starting collector: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
