"""QRadar Configuration Settings.

============================================================================
This module defines the configuration settings specific to IBM QRadar SIEM.
It uses Pydantic for validation and supports loading from environment
variables or YAML config files.

Key settings:
- base_url: QRadar Console URL (e.g., https://10.10.0.255)
- sec_token: SEC authentication token for QRadar API
- verify_ssl: Whether to verify SSL certificates (often False for internal)
- time_window: How far back to search for offenses (default: 1 hour)
- max_retry: Number of retry attempts for API calls
- offset: Delay between retries in seconds
============================================================================
"""

from datetime import timedelta
from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class QRadarSettings(BaseSettings):
    """QRadar SIEM configuration settings.

    All settings can be provided via environment variables with QRADAR_ prefix
    or through a YAML configuration file.
    """

    model_config = SettingsConfigDict(
        env_prefix="QRADAR_",
        case_sensitive=False,
        extra="ignore",
    )

    base_url: str = Field(
        default="https://10.10.0.255",
        description="QRadar Console base URL (include https://)",
    )

    sec_token: SecretStr = Field(
        default=SecretStr("your-qradar-sec-token-here"),
        description="QRadar SEC API authentication token",
    )

    verify_ssl: bool = Field(
        default=False,
        description="Verify SSL certificates (often False for internal QRadar)",
    )

    time_window: timedelta = Field(
        default=timedelta(hours=1),
        description="Default time window to search for offenses",
    )

    max_retry: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts for API calls",
    )

    offset: timedelta = Field(
        default=timedelta(seconds=30),
        description="Delay between retry attempts",
    )

    @field_validator("time_window", "offset", mode="before")
    @classmethod
    def parse_timedelta(cls, v: Any) -> timedelta:
        """Parse ISO 8601 duration strings to timedelta.

        Args:
            v: Input value (timedelta, string, or int)

        Returns:
            Parsed timedelta object

        Raises:
            ValueError: If parsing fails

        """
        if isinstance(v, timedelta):
            return v
        if isinstance(v, str):
            return cls._parse_iso8601_duration(v)
        if isinstance(v, (int, float)):
            return timedelta(seconds=v)
        raise ValueError(f"Cannot parse timedelta from {type(v)}")

    @staticmethod
    def _parse_iso8601_duration(duration_str: str) -> timedelta:
        """Parse ISO 8601 duration string (e.g., PT1H, PT30S).

        Args:
            duration_str: ISO 8601 duration string

        Returns:
            Parsed timedelta

        """
        import re

        pattern = r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$"
        match = re.match(pattern, duration_str.upper())
        if not match:
            raise ValueError(f"Invalid ISO 8601 duration: {duration_str}")

        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)

        return timedelta(hours=hours, minutes=minutes, seconds=seconds)
