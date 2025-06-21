"""
Module: __init__
Type: Internal Module

Purpose:
Gong API client implementation for making authenticated requests to Gong services.

Data Flow:
- Input: Configuration parameters, Authentication credentials
- Processing: Data extraction, API interaction
- Output: Processed results

Critical Because:
Central integration point for Gong - without this, no Gong data can be accessed.

Dependencies:
- Requires: client
- Used By: app_backend.ingestion.orchestrator, app_backend.api_bridge.server

Author: Julia Evans
Date: 2025-06-20
"""
from .client import (
    GongAPIClient,
    GongAPIError,
    GongRateLimitError
)

__version__ = "1.0.0"
__author__ = "CS-Ascension Team"

__all__ = [
    'GongAPIClient',
    'GongAPIError',
    'GongRateLimitError'
]