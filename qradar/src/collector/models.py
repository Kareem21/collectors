"""Collector Data Models.

============================================================================
This module defines data models used by the collector for processing
expectations and tracking results.

- ExpectationResult: Outcome of processing a single expectation
- ProcessingSummary: Aggregate statistics for a processing cycle

These models are generic and reusable across different collector types.
============================================================================
"""

from typing import Any

from pydantic import BaseModel, Field
from pyoaev.apis.inject_expectation.model import (  # type: ignore[import-untyped]
    DetectionExpectation,
    PreventionExpectation,
)


class ExpectationResult(BaseModel):
    """Result of processing a single expectation."""

    expectation_id: str = Field(..., description="ID of the processed expectation")
    is_valid: bool = Field(..., description="Whether expectation was validated")
    expectation: DetectionExpectation | PreventionExpectation | None = Field(
        default=None, description="Original expectation object"
    )
    matched_alerts: list[dict[str, Any]] | None = Field(
        default=None, description="Alerts that matched the expectation"
    )
    error_message: str | None = Field(
        default=None, description="Error message if processing failed"
    )


class ProcessingSummary(BaseModel):
    """Summary statistics for a processing cycle."""

    processed: int = Field(default=0, description="Total expectations processed")
    valid: int = Field(default=0, description="Number validated as true")
    invalid: int = Field(default=0, description="Number validated as false")
    skipped: int = Field(default=0, description="Number skipped")
