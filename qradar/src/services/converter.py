"""QRadar Data Converter.

============================================================================
This module converts QRadar offense data into OpenBAS/OpenAEV format.

Conversion process:
1. Takes QRadarOffense objects
2. Extracts relevant fields (source IP, destination IP)
3. Formats them according to OpenBAS data structure expectations
4. Returns dictionaries ready for matching with DetectionHelper

The converter ensures compatibility between QRadar's offense structure
and OpenBAS's expectation signature format.
============================================================================
"""

import logging
from typing import Any

from .exception import QRadarDataConversionError, QRadarValidationError
from .models import QRadarOffense

LOG_PREFIX = "[QRadarConverter]"


class Converter:
    """Converter for QRadar data to OpenBAS format."""

    def __init__(self) -> None:
        """Initialize converter with logger."""
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"{LOG_PREFIX} QRadar data converter initialized")

    def convert_data_to_oaev_data(
        self,
        data: QRadarOffense | list[QRadarOffense] | None,
    ) -> list[dict[str, Any]]:
        """Convert QRadar offenses to OpenBAS format.

        Args:
            data: QRadar offense(s) to convert

        Returns:
            List of OpenBAS-formatted data dictionaries

        Raises:
            QRadarDataConversionError: If conversion fails

        """
        if not data:
            self.logger.debug(
                f"{LOG_PREFIX} No data provided for conversion, returning empty list"
            )
            return []

        # Ensure data is a list
        if not isinstance(data, list):
            data = [data]

        try:
            self.logger.debug(
                f"{LOG_PREFIX} Converting {len(data)} QRadar offenses to OpenBAS format"
            )

            oaev_data = []
            for i, offense in enumerate(data, 1):
                self.logger.debug(
                    f"{LOG_PREFIX} Processing offense {i}/{len(data)}: ID {offense.id}"
                )

                try:
                    converted = self._convert_offense(offense)
                    if converted:
                        oaev_data.append(converted)
                        self.logger.debug(
                            f"{LOG_PREFIX} Successfully converted offense {offense.id}"
                        )
                    else:
                        self.logger.debug(
                            f"{LOG_PREFIX} Offense {offense.id} resulted in empty data - skipping"
                        )
                except Exception as e:
                    raise QRadarDataConversionError(
                        f"Failed to convert offense {offense.id}: {e}"
                    ) from e

            self.logger.info(
                f"{LOG_PREFIX} Conversion completed: {len(data)} offenses -> {len(oaev_data)} OpenBAS items"
            )

            return oaev_data

        except QRadarDataConversionError:
            raise
        except Exception as e:
            raise QRadarDataConversionError(
                f"Unexpected error converting data to OpenBAS format: {e}"
            ) from e

    def _convert_offense(self, offense: QRadarOffense) -> dict[str, Any]:
        """Convert single QRadar offense to OpenBAS format.

        Args:
            offense: QRadar offense object

        Returns:
            OpenBAS-formatted dictionary

        Raises:
            QRadarValidationError: If offense type is invalid

        """
        if not isinstance(offense, QRadarOffense):
            raise QRadarValidationError(
                f"Invalid input type: {type(offense)}, expected QRadarOffense"
            )

        oaev_data = {}

        # Extract source IP
        if offense.offense_source:
            oaev_data["source_ipv4_address"] = {
                "type": "simple",
                "data": [offense.offense_source],
            }
            self.logger.debug(
                f"{LOG_PREFIX} Offense {offense.id} - Source IP: {offense.offense_source}"
            )

        # Extract destination IP
        if offense.local_destination_ip:
            oaev_data["target_ipv4_address"] = {
                "type": "simple",
                "data": [offense.local_destination_ip],
            }
            self.logger.debug(
                f"{LOG_PREFIX} Offense {offense.id} - Dest IP: {offense.local_destination_ip}"
            )

        # Log offense details for debugging
        if offense.description:
            self.logger.debug(
                f"{LOG_PREFIX} Offense {offense.id} - Description: {offense.description}"
            )

        if offense.offense_type:
            self.logger.debug(
                f"{LOG_PREFIX} Offense {offense.id} - Type: {offense.offense_type}"
            )

        self.logger.debug(
            f"{LOG_PREFIX} Converted offense {offense.id} with {len(oaev_data)} fields"
        )

        return oaev_data
