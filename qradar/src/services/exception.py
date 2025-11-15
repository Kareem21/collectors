"""QRadar Service Exceptions.

============================================================================
This module defines custom exceptions for QRadar service operations.

Exception hierarchy:
- QRadarServiceError (base for all QRadar errors)
  ├─ QRadarValidationError (invalid input/config)
  ├─ QRadarAPIError (API call failures)
  ├─ QRadarAuthenticationError (auth failures)
  ├─ QRadarNetworkError (connection issues)
  └─ QRadarDataConversionError (data transformation errors)

These exceptions provide specific error handling for different failure
scenarios when interacting with QRadar SIEM.
============================================================================
"""


class QRadarServiceError(Exception):
    """Base exception for all QRadar service errors."""

    pass


class QRadarValidationError(QRadarServiceError):
    """Raised when validation of inputs or configuration fails."""

    pass


class QRadarAPIError(QRadarServiceError):
    """Raised when QRadar API calls fail."""

    pass


class QRadarAuthenticationError(QRadarServiceError):
    """Raised when QRadar authentication fails."""

    pass


class QRadarNetworkError(QRadarServiceError):
    """Raised when network connectivity to QRadar fails."""

    pass


class QRadarDataConversionError(QRadarServiceError):
    """Raised when converting QRadar data to OpenBAS format fails."""

    pass
