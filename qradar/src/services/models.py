"""QRadar Data Models.

============================================================================
This module defines Pydantic models for QRadar SIEM data structures:

- QRadarOffense: Represents a security offense from QRadar
- QRadarSearchCriteria: Search parameters for querying QRadar API
- QRadarResponse: API response wrapper

These models provide type safety, validation, and easy conversion between
QRadar's REST API JSON responses and Python objects.

Simplified for barebones collector - only includes essential fields needed
for basic IP-based detection matching with OpenBAS expectations.
============================================================================
"""

from typing import Any

from pydantic import BaseModel, Field


class QRadarOffense(BaseModel):
    """QRadar security offense model.

    Represents a single offense/alert from IBM QRadar SIEM.
    Includes only the essential fields needed for OpenBAS integration.
    """

    id: int = Field(..., description="Unique offense ID")
    description: str = Field(default="", description="Offense description")
    offense_source: str | None = Field(
        default=None, description="Source IP address of the offense"
    )
    local_destination_ip: str | None = Field(
        default=None, description="Destination IP address (local network)"
    )
    start_time: int = Field(..., description="Offense start time (epoch milliseconds)")
    last_updated_time: int = Field(
        ..., description="Last update time (epoch milliseconds)"
    )
    magnitude: int = Field(default=0, description="Offense magnitude/severity score")
    offense_type: str | None = Field(default=None, description="Type of offense")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "QRadarOffense":
        """Create QRadarOffense from API JSON response.

        Args:
            data: Raw JSON data from QRadar API

        Returns:
            QRadarOffense instance

        """
        return cls(
            id=data.get("id", 0),
            description=data.get("description", ""),
            offense_source=data.get("offense_source"),
            local_destination_ip=data.get("local_destination_ip"),
            start_time=data.get("start_time", 0),
            last_updated_time=data.get("last_updated_time", 0),
            magnitude=data.get("magnitude", 0),
            offense_type=data.get("offense_type"),
        )


class QRadarSearchCriteria(BaseModel):
    """Search criteria for QRadar API queries.

    Defines parameters for filtering QRadar offenses based on
    IP addresses and time ranges.
    """

    source_ips: list[str] = Field(
        default_factory=list, description="List of source IP addresses to search for"
    )
    destination_ips: list[str] = Field(
        default_factory=list,
        description="List of destination IP addresses to search for",
    )
    start_time: int | None = Field(
        default=None, description="Start time filter (epoch milliseconds)"
    )
    end_time: int | None = Field(
        default=None, description="End time filter (epoch milliseconds)"
    )


class QRadarResponse(BaseModel):
    """QRadar API response wrapper.

    Wraps the API response containing a list of offenses.
    """

    offenses: list[QRadarOffense] = Field(
        default_factory=list, description="List of QRadar offenses"
    )
    total_count: int = Field(default=0, description="Total number of offenses found")

    @classmethod
    def from_api_response(cls, data: list[dict[str, Any]]) -> "QRadarResponse":
        """Create QRadarResponse from API JSON response.

        Args:
            data: List of raw offense dictionaries from QRadar API

        Returns:
            QRadarResponse instance with parsed offenses

        """
        offenses = [QRadarOffense.from_api_response(item) for item in data]
        return cls(offenses=offenses, total_count=len(offenses))
