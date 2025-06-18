"""
Gong Validation Module

This module contains validation components for ensuring data quality
and Pydantic model compliance for extracted Gong data.
"""

from .comprehensive_validator import GongValidator

__all__ = [
    "GongValidator",
]
