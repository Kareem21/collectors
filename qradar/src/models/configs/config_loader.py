"""Configuration Loader for QRadar Collector.

============================================================================
This module loads and combines all configuration settings for the collector:
- OpenAEV/OpenBAS connection settings
- Generic collector settings (ID, name, period, log level)
- QRadar-specific settings (URL, token, SSL verification)

Configuration sources (in order of precedence):
1. Environment variables
2. YAML configuration file (src/config.yml)
3. Default values

The loaded configuration is validated using Pydantic models and provides
a unified interface for the entire collector application.
============================================================================
"""

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pyoaev.daemons.model import DaemonConfig  # type: ignore[import-untyped]

from .qradar_configs import QRadarSettings

LOG_PREFIX = "[ConfigLoader]"


class OpenAEVSettings(BaseSettings):
    """OpenAEV/OpenBAS platform connection settings."""

    model_config = SettingsConfigDict(
        env_prefix="OPENAEV_",
        case_sensitive=False,
        extra="ignore",
    )

    url: str = Field(
        default="https://openbas.example.com",
        description="OpenAEV/OpenBAS platform URL",
    )
    token: SecretStr = Field(
        default=SecretStr("your-openaev-token-here"),
        description="OpenAEV API authentication token",
    )


class CollectorSettings(BaseSettings):
    """Generic collector configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="COLLECTOR_",
        case_sensitive=False,
        extra="ignore",
    )

    id: str = Field(
        default="qradar--00000000-0000-0000-0000-000000000000",
        description="Unique collector ID (UUID format)",
    )
    name: str = Field(
        default="QRadar Collector",
        description="Human-readable collector name",
    )
    period: str = Field(
        default="PT5M",
        description="Collection interval (ISO 8601 duration)",
    )
    log_level: str = Field(
        default="info",
        description="Logging level (debug, info, warn, error)",
    )
    platform: str = Field(
        default="SIEM",
        description="Platform type (SIEM, EDR, XDR, etc.)",
    )


class ConfigLoader:
    """Loads and manages all collector configuration settings."""

    def __init__(self, config_file: str = "src/config.yml") -> None:
        """Initialize configuration loader.

        Args:
            config_file: Path to YAML configuration file

        """
        self.logger = logging.getLogger(__name__)
        self.config_file = Path(config_file)
        self._yaml_config: dict[str, Any] = {}

        if self.config_file.exists():
            self._load_yaml()
        else:
            self.logger.warning(
                f"{LOG_PREFIX} Config file not found: {config_file}, using defaults"
            )

        self.openaev = self._load_openaev_settings()
        self.collector = self._load_collector_settings()
        self.qradar = self._load_qradar_settings()

        self._setup_logging()

    def _load_yaml(self) -> None:
        """Load YAML configuration file."""
        try:
            with open(self.config_file) as f:
                self._yaml_config = yaml.safe_load(f) or {}
            self.logger.info(f"{LOG_PREFIX} Loaded config from {self.config_file}")
        except Exception as e:
            self.logger.error(f"{LOG_PREFIX} Error loading YAML config: {e}")
            self._yaml_config = {}

    def _load_openaev_settings(self) -> OpenAEVSettings:
        """Load OpenAEV settings from YAML or environment."""
        yaml_data = self._yaml_config.get("openaev", {})
        return OpenAEVSettings(**yaml_data)

    def _load_collector_settings(self) -> CollectorSettings:
        """Load collector settings from YAML or environment."""
        yaml_data = self._yaml_config.get("collector", {})
        return CollectorSettings(**yaml_data)

    def _load_qradar_settings(self) -> QRadarSettings:
        """Load QRadar settings from YAML or environment."""
        yaml_data = self._yaml_config.get("qradar", {})
        return QRadarSettings(**yaml_data)

    def _setup_logging(self) -> None:
        """Configure logging based on log_level setting."""
        level_map = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warn": logging.WARNING,
            "error": logging.ERROR,
        }
        level = level_map.get(self.collector.log_level.lower(), logging.INFO)
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    def to_daemon_config(self) -> DaemonConfig:
        """Convert to pyoaev DaemonConfig format.

        Returns:
            DaemonConfig object for pyoaev CollectorDaemon

        """
        return DaemonConfig(
            openaev_url=self.openaev.url,
            openaev_token=self.openaev.token.get_secret_value(),
            collector_id=self.collector.id,
            collector_name=self.collector.name,
            collector_period=self.collector.period,
            collector_log_level=self.collector.log_level,
            collector_platform=self.collector.platform,
        )
