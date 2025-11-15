"""QRadar Expectation Service.

============================================================================
This module contains QRadar-specific business logic for handling expectations.

Key responsibilities:
- Define supported signature types (source/target IPs, dates)
- Process detection expectations (prevention not supported for SIEM)
- Fetch relevant offenses from QRadar based on signatures
- Match offenses against expectation criteria
- Return validation results (valid/invalid)

The service acts as a bridge between generic collector logic and
QRadar-specific operations, implementing the service provider pattern.
============================================================================
"""

import logging
from datetime import datetime
from typing import Any

from pyoaev.apis.inject_expectation.model import (  # type: ignore[import-untyped]
    DetectionExpectation,
    PreventionExpectation,
)
from pyoaev.helpers import OpenAEVDetectionHelper  # type: ignore[import-untyped]
from pyoaev.signatures.types import SignatureTypes  # type: ignore[import-untyped]

from ..collector.models import ExpectationResult
from ..models.configs.config_loader import ConfigLoader
from .client_api import QRadarClientAPI
from .converter import Converter
from .exception import QRadarAPIError, QRadarValidationError
from .models import QRadarSearchCriteria

LOG_PREFIX = "[QRadarExpectationService]"


class QRadarExpectationService:
    """QRadar-specific service provider for expectation handling."""

    # Only IP addresses and dates for barebones version
    SUPPORTED_SIGNATURES = [
        SignatureTypes.SIG_TYPE_SOURCE_IPV4_ADDRESS,
        SignatureTypes.SIG_TYPE_TARGET_IPV4_ADDRESS,
        SignatureTypes.SIG_TYPE_START_DATE,
        SignatureTypes.SIG_TYPE_END_DATE,
    ]

    def __init__(self, config: ConfigLoader) -> None:
        """Initialize QRadar expectation service.

        Args:
            config: Configuration loader instance

        Raises:
            QRadarValidationError: If config is None

        """
        if config is None:
            raise QRadarValidationError("Config is required for expectation service")

        self.logger = logging.getLogger(__name__)
        self.config = config

        self.client_api = QRadarClientAPI(config)
        self.converter = Converter()

        self.logger.info(
            f"{LOG_PREFIX} QRadar expectation service initialized successfully"
        )

    def get_supported_signatures(self) -> list[SignatureTypes]:
        """Get signature types this service supports.

        Returns:
            List of supported SignatureTypes

        """
        return self.SUPPORTED_SIGNATURES

    def handle_batch_expectations(
        self,
        expectations: list[DetectionExpectation | PreventionExpectation],
        detection_helper: OpenAEVDetectionHelper,
    ) -> list[ExpectationResult]:
        """Handle batch of expectations.

        Args:
            expectations: List of expectations to process
            detection_helper: OpenBAS detection helper

        Returns:
            List of ExpectationResult objects

        """
        if not expectations:
            self.logger.info(f"{LOG_PREFIX} No expectations to process")
            return []

        self.logger.info(
            f"{LOG_PREFIX} Processing {len(expectations)} expectations"
        )

        results = []
        for i, expectation in enumerate(expectations, 1):
            self.logger.debug(
                f"{LOG_PREFIX} Processing expectation {i}/{len(expectations)}"
            )

            try:
                result = self.process_expectation(expectation, detection_helper)
                results.append(result)
            except Exception as e:
                self.logger.error(
                    f"{LOG_PREFIX} Error processing expectation {expectation.inject_expectation_id}: {e}"
                )
                # Create error result
                results.append(
                    ExpectationResult(
                        expectation_id=str(expectation.inject_expectation_id),
                        is_valid=False,
                        expectation=expectation,
                        error_message=str(e),
                    )
                )

        self.logger.info(
            f"{LOG_PREFIX} Batch processing completed: {len(results)} results"
        )
        return results

    def process_expectation(
        self,
        expectation: DetectionExpectation | PreventionExpectation,
        detection_helper: OpenAEVDetectionHelper,
    ) -> ExpectationResult:
        """Process single expectation.

        Args:
            expectation: Expectation to process
            detection_helper: OpenBAS detection helper

        Returns:
            ExpectationResult with validation outcome

        """
        expectation_id = str(expectation.inject_expectation_id)

        # QRadar only supports detection (SIEM doesn't prevent)
        if isinstance(expectation, PreventionExpectation):
            self.logger.warning(
                f"{LOG_PREFIX} QRadar only supports Detection, not Prevention - marking invalid"
            )
            return ExpectationResult(
                expectation_id=expectation_id,
                is_valid=False,
                expectation=expectation,
                error_message="QRadar only supports DetectionExpectations",
            )

        # Process detection expectation
        try:
            self.logger.debug(
                f"{LOG_PREFIX} Processing detection expectation: {expectation_id}"
            )

            # Extract signatures
            signatures = self._extract_signatures(expectation)

            # Build search criteria
            search_criteria = self._build_search_criteria(signatures)

            # Fetch offenses from QRadar
            offenses = self.client_api.fetch_offenses(search_criteria)

            if not offenses:
                self.logger.info(
                    f"{LOG_PREFIX} No offenses found for expectation {expectation_id}"
                )
                return ExpectationResult(
                    expectation_id=expectation_id,
                    is_valid=False,
                    expectation=expectation,
                    error_message="No matching offenses found in QRadar",
                )

            # Convert to OpenBAS format
            oaev_data = self.converter.convert_data_to_oaev_data(offenses)

            # Match against signatures
            is_valid = self._match_data(oaev_data, signatures, detection_helper)

            return ExpectationResult(
                expectation_id=expectation_id,
                is_valid=is_valid,
                expectation=expectation,
                matched_alerts=oaev_data if is_valid else None,
            )

        except QRadarAPIError as e:
            self.logger.error(f"{LOG_PREFIX} QRadar API error: {e}")
            return ExpectationResult(
                expectation_id=expectation_id,
                is_valid=False,
                expectation=expectation,
                error_message=f"QRadar API error: {e}",
            )
        except Exception as e:
            self.logger.error(f"{LOG_PREFIX} Unexpected error: {e}")
            return ExpectationResult(
                expectation_id=expectation_id,
                is_valid=False,
                expectation=expectation,
                error_message=f"Unexpected error: {e}",
            )

    def _extract_signatures(
        self, expectation: DetectionExpectation
    ) -> list[dict[str, str]]:
        """Extract signatures from expectation.

        Args:
            expectation: Detection expectation

        Returns:
            List of signature dictionaries

        """
        signatures = [
            {"type": sig.type.value, "value": sig.value}
            for sig in expectation.inject_expectation_signatures
            if sig.type in self.SUPPORTED_SIGNATURES
        ]

        self.logger.debug(
            f"{LOG_PREFIX} Extracted {len(signatures)} supported signatures"
        )
        return signatures

    def _build_search_criteria(
        self, signatures: list[dict[str, str]]
    ) -> QRadarSearchCriteria:
        """Build QRadar search criteria from signatures.

        Args:
            signatures: List of signature dictionaries

        Returns:
            QRadarSearchCriteria object

        """
        source_ips = []
        destination_ips = []
        start_time = None
        end_time = None

        for sig in signatures:
            sig_type = sig.get("type")
            sig_value = sig.get("value")

            if sig_type == "source_ipv4_address":
                source_ips.append(sig_value)
            elif sig_type == "target_ipv4_address":
                destination_ips.append(sig_value)
            elif sig_type == "start_date":
                # Convert ISO date to epoch milliseconds
                dt = datetime.fromisoformat(sig_value.replace("Z", "+00:00"))
                start_time = int(dt.timestamp() * 1000)
            elif sig_type == "end_date":
                dt = datetime.fromisoformat(sig_value.replace("Z", "+00:00"))
                end_time = int(dt.timestamp() * 1000)

        criteria = QRadarSearchCriteria(
            source_ips=source_ips,
            destination_ips=destination_ips,
            start_time=start_time,
            end_time=end_time,
        )

        self.logger.debug(f"{LOG_PREFIX} Built search criteria: {criteria}")
        return criteria

    def _match_data(
        self,
        oaev_data: list[dict[str, Any]],
        signatures: list[dict[str, str]],
        detection_helper: OpenAEVDetectionHelper,
    ) -> bool:
        """Match OpenBAS data against signatures.

        Args:
            oaev_data: List of OpenBAS-formatted offense data
            signatures: List of signature dictionaries
            detection_helper: OpenBAS detection helper

        Returns:
            True if match found, False otherwise

        """
        # Filter out date signatures for matching
        date_types = ["start_date", "end_date"]
        matching_signatures = [
            sig for sig in signatures if sig["type"] not in date_types
        ]

        self.logger.debug(
            f"{LOG_PREFIX} Matching {len(oaev_data)} items against {len(matching_signatures)} signatures"
        )

        # Try to match each offense
        for i, data_item in enumerate(oaev_data, 1):
            self.logger.debug(f"{LOG_PREFIX} Testing offense {i}/{len(oaev_data)}")

            # Use detection helper to match
            if detection_helper.match_alert_elements(matching_signatures, data_item):
                self.logger.info(f"{LOG_PREFIX} Match found for offense {i}!")
                return True

        self.logger.info(f"{LOG_PREFIX} No matches found")
        return False

    def get_service_info(self) -> dict[str, Any]:
        """Get service information.

        Returns:
            Dictionary with service metadata

        """
        return {
            "service_name": "QRadar",
            "supported_signatures": [sig.value for sig in self.SUPPORTED_SIGNATURES],
            "supports_detection": True,
            "supports_prevention": False,
        }
