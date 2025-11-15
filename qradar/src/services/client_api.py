"""QRadar API Client.

============================================================================
This module provides the HTTP client for communicating with IBM QRadar SIEM
via its REST API.

Key responsibilities:
- Authenticate using SEC token
- Fetch offenses from /api/siem/offenses endpoint
- Filter offenses by IP addresses and time ranges
- Handle network errors and retries
- Convert JSON responses to QRadarOffense objects

The client uses the requests library and implements basic error handling
for common QRadar API failure scenarios (auth errors, network issues, etc.).
============================================================================
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from ..models.configs.config_loader import ConfigLoader
from .exception import (
    QRadarAPIError,
    QRadarAuthenticationError,
    QRadarNetworkError,
    QRadarValidationError,
)
from .models import QRadarOffense, QRadarResponse, QRadarSearchCriteria

LOG_PREFIX = "[QRadarClientAPI]"
REQUEST_TIMEOUT_SECONDS = 30


class QRadarClientAPI:
    """QRadar REST API client for fetching offenses."""

    def __init__(self, config: ConfigLoader) -> None:
        """Initialize QRadar API client.

        Args:
            config: Configuration loader with QRadar settings

        Raises:
            QRadarValidationError: If configuration is invalid

        """
        if config is None:
            raise QRadarValidationError("Config is required for API client")

        self.logger = logging.getLogger(__name__)
        self.config = config

        self.base_url = str(self.config.qradar.base_url).rstrip("/")
        self.sec_token = self.config.qradar.sec_token.get_secret_value()
        self.verify_ssl = self.config.qradar.verify_ssl
        self.time_window = self.config.qradar.time_window

        # Disable SSL warnings if verify_ssl is False
        if not self.verify_ssl:
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.session = self._create_session()
        self.logger.info(f"{LOG_PREFIX} QRadar API client initialized successfully")

    def _create_session(self) -> requests.Session:
        """Create HTTP session with QRadar SEC authentication.

        Returns:
            Configured requests.Session

        """
        session = requests.Session()
        session.headers.update(
            {
                "SEC": self.sec_token,
                "Accept": "application/json",
                "Version": "14.0",  # QRadar API version
            }
        )
        session.verify = self.verify_ssl
        return session

    def fetch_offenses(
        self, search_criteria: QRadarSearchCriteria
    ) -> list[QRadarOffense]:
        """Fetch offenses from QRadar based on search criteria.

        Args:
            search_criteria: Search parameters (IPs, time range)

        Returns:
            List of QRadarOffense objects

        Raises:
            QRadarAPIError: If API call fails
            QRadarAuthenticationError: If authentication fails
            QRadarNetworkError: If network connection fails

        """
        try:
            self.logger.debug(
                f"{LOG_PREFIX} Fetching offenses with criteria: {search_criteria}"
            )

            # Build API endpoint and filters
            endpoint = f"{self.base_url}/api/siem/offenses"
            filters = self._build_filters(search_criteria)

            params = {}
            if filters:
                params["filter"] = filters

            self.logger.debug(f"{LOG_PREFIX} Calling QRadar API: {endpoint}")
            self.logger.debug(f"{LOG_PREFIX} Filters: {filters}")

            response = self.session.get(
                endpoint, params=params, timeout=REQUEST_TIMEOUT_SECONDS
            )

            # Handle authentication errors
            if response.status_code == 401:
                raise QRadarAuthenticationError(
                    "Authentication with QRadar failed - check SEC token"
                )

            # Handle other API errors
            if response.status_code != 200:
                raise QRadarAPIError(
                    f"QRadar API returned status {response.status_code}: {response.text}"
                )

            # Parse response
            data = response.json()
            qradar_response = QRadarResponse.from_api_response(data)

            self.logger.info(
                f"{LOG_PREFIX} Retrieved {qradar_response.total_count} offenses from QRadar"
            )

            return qradar_response.offenses

        except QRadarAuthenticationError:
            raise
        except (ConnectionError, Timeout) as e:
            raise QRadarNetworkError(f"Network error connecting to QRadar: {e}") from e
        except RequestException as e:
            raise QRadarAPIError(f"HTTP request to QRadar failed: {e}") from e
        except Exception as e:
            raise QRadarAPIError(f"Unexpected error fetching offenses: {e}") from e

    def _build_filters(self, criteria: QRadarSearchCriteria) -> str:
        """Build QRadar API filter string from search criteria.

        Args:
            criteria: Search criteria with IPs and time range

        Returns:
            QRadar API filter string (e.g., "start_time > 1234567890")

        """
        filters = []

        # Time filter (required for performance)
        if criteria.start_time:
            filters.append(f"start_time > {criteria.start_time}")
        else:
            # Use time_window as default
            cutoff_time = datetime.utcnow() - self.time_window
            cutoff_ms = int(cutoff_time.timestamp() * 1000)
            filters.append(f"start_time > {cutoff_ms}")

        # IP filters - QRadar uses offense_source and local_destination_ip
        ip_filters = []

        if criteria.source_ips:
            for ip in criteria.source_ips:
                ip_filters.append(f"offense_source = '{ip}'")

        if criteria.destination_ips:
            for ip in criteria.destination_ips:
                ip_filters.append(f"local_destination_ip = '{ip}'")

        # Combine IP filters with OR
        if ip_filters:
            filters.append(f"({' or '.join(ip_filters)})")

        # Join all filters with AND
        filter_string = " and ".join(filters) if filters else ""

        self.logger.debug(f"{LOG_PREFIX} Built filter string: {filter_string}")
        return filter_string
