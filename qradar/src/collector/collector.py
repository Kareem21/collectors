"""QRadar Collector Core.

============================================================================
This is the main collector class that orchestrates the entire collection
process for IBM QRadar integration with OpenBAS/OpenAEV.

Responsibilities:
- Initialize QRadar services and OpenBAS connection
- Run periodic collection cycles
- Fetch expectations from OpenBAS
- Process expectations through QRadar service
- Update expectation results back to OpenBAS
- Handle errors and logging

The collector extends pyoaev's CollectorDaemon for scheduling and
lifecycle management.
============================================================================
"""

import logging
import os

from pyoaev.daemons import CollectorDaemon  # type: ignore[import-untyped]
from pyoaev.helpers import OpenAEVDetectionHelper  # type: ignore[import-untyped]

from ..models.configs.config_loader import ConfigLoader
from ..services.expectation_service import QRadarExpectationService
from .exception import CollectorConfigError, CollectorProcessingError, CollectorSetupError
from .models import ProcessingSummary

LOG_PREFIX = "[QRadarCollector]"
COLLECTOR_TYPE = "openaev_qradar"


class Collector(CollectorDaemon):  # type: ignore[misc]
    """QRadar Collector using service provider pattern."""

    def __init__(self) -> None:
        """Initialize the collector.

        Raises:
            CollectorConfigError: If initialization fails

        """
        try:
            # Load configuration
            self.config = ConfigLoader()

            # Initialize parent CollectorDaemon
            super().__init__(
                configuration=self.config.to_daemon_config(),
                callback=self._process_callback,
                collector_type=COLLECTOR_TYPE,
            )

            self.logger.info(f"{LOG_PREFIX} QRadar Collector initialized successfully")

        except Exception as err:
            import logging

            logging.basicConfig(level=logging.ERROR)
            self.logger = logging.getLogger(__name__)
            self.logger.error(f"{LOG_PREFIX} Failed to initialize collector: {err}")
            raise CollectorConfigError(
                f"Failed to initialize the collector: {err}"
            ) from err

    def _setup(self) -> None:
        """Set up the collector services.

        Initializes QRadar services and detection helper.

        Raises:
            CollectorSetupError: If setup fails

        """
        try:
            self.logger.info(f"{LOG_PREFIX} Starting collector setup...")

            # Call parent setup (connects to OpenBAS API)
            super()._setup()

            # Initialize QRadar-specific service
            self.logger.debug(f"{LOG_PREFIX} Initializing QRadar services...")
            self.qradar_service = QRadarExpectationService(self.config)

            # Initialize detection helper
            supported_signatures = self.qradar_service.get_supported_signatures()
            self.detection_helper = OpenAEVDetectionHelper(
                logger=self.logger,
                relevant_signatures_types=supported_signatures,
            )

            self.logger.info(f"{LOG_PREFIX} Collector setup completed successfully")
            self.logger.info(
                f"{LOG_PREFIX} Supported signatures: {[sig.value for sig in supported_signatures]}"
            )

        except Exception as err:
            self.logger.error(f"{LOG_PREFIX} Collector setup failed: {err}")
            raise CollectorSetupError(f"Failed to setup the collector: {err}") from err

    def _process_callback(self) -> None:
        """Process callback for expectation processing.

        This method is called periodically by the CollectorDaemon scheduler.
        It fetches expectations from OpenBAS, processes them through QRadar,
        and updates the results back to OpenBAS.

        Raises:
            CollectorProcessingError: If processing fails

        """
        try:
            self.logger.info(f"{LOG_PREFIX} Starting processing cycle...")

            # Fetch expectations from OpenBAS
            self.logger.debug(f"{LOG_PREFIX} Fetching expectations from OpenBAS...")
            expectations = self.api.inject_expectation.expectations_models_for_source(
                source_id=self.get_id()
            )

            if not expectations:
                self.logger.info(f"{LOG_PREFIX} No expectations to process")
                return

            self.logger.info(
                f"{LOG_PREFIX} Found {len(expectations)} expectations to process"
            )

            # Process expectations through QRadar service
            results = self.qradar_service.handle_batch_expectations(
                expectations, self.detection_helper
            )

            # Update OpenBAS with results
            self._update_expectations(results)

            # Log summary
            valid_count = sum(1 for r in results if r.is_valid)
            invalid_count = len(results) - valid_count

            self.logger.info(
                f"{LOG_PREFIX} Processing cycle completed: {len(results)} total, "
                f"{valid_count} valid, {invalid_count} invalid"
            )

        except (KeyboardInterrupt, SystemExit):
            self.logger.info(f"{LOG_PREFIX} Collector stopping...")
            os._exit(0)
        except Exception as e:
            self.logger.error(f"{LOG_PREFIX} Error during processing cycle: {str(e)}")
            raise CollectorProcessingError(f"Processing error: {str(e)}") from e

    def _update_expectations(self, results: list) -> None:
        """Update expectations in OpenBAS with results.

        Args:
            results: List of ExpectationResult objects

        """
        self.logger.debug(f"{LOG_PREFIX} Updating {len(results)} expectations...")

        success_count = 0
        error_count = 0

        for result in results:
            try:
                expectation_id = result.expectation_id
                is_valid = result.is_valid

                # Determine result text
                result_text = "Detected" if is_valid else "Not Detected"

                # Update via OpenBAS API
                self.api.inject_expectation.update(
                    inject_expectation_id=expectation_id,
                    inject_expectation={
                        "collector_id": self.get_id(),
                        "result": result_text,
                        "is_success": is_valid,
                    },
                )

                success_count += 1
                self.logger.debug(
                    f"{LOG_PREFIX} Updated expectation {expectation_id}: {result_text}"
                )

            except Exception as e:
                error_count += 1
                self.logger.error(
                    f"{LOG_PREFIX} Failed to update expectation {result.expectation_id}: {e}"
                )

        self.logger.info(
            f"{LOG_PREFIX} Expectations updated: {success_count} successful, {error_count} failed"
        )
