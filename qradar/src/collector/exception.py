"""Collector Exceptions.

============================================================================
This module defines custom exceptions for collector-level operations.

Exception hierarchy:
- CollectorError (base)
  ├─ CollectorConfigError (configuration issues)
  ├─ CollectorSetupError (initialization failures)
  └─ CollectorProcessingError (runtime processing errors)

These are high-level exceptions for the main collector orchestration,
separate from QRadar-specific service exceptions.
============================================================================
"""


class CollectorError(Exception):
    """Base exception for collector errors."""

    pass


class CollectorConfigError(CollectorError):
    """Raised when collector configuration is invalid."""

    pass


class CollectorSetupError(CollectorError):
    """Raised when collector setup/initialization fails."""

    pass


class CollectorProcessingError(CollectorError):
    """Raised when collector processing cycle fails."""

    pass
