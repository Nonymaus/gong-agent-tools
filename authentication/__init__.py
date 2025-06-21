"""
Module: __init__
Type: Internal Module

Purpose:
Gong integration component handling specific functionality within the CS-Ascension platform.

Data Flow:
- Input: HTTP requests, Configuration parameters, Authentication credentials
- Processing: Input validation, Data extraction, API interaction
- Output: Processed results

Critical Because:
Central integration point for Gong - without this, no Gong data can be accessed.

Dependencies:
- Requires: auth_manager
- Used By: app_backend.ingestion.orchestrator, app_backend.api_bridge.server

Author: Julia Evans
Date: 2025-06-20
"""
from .auth_manager import (
    GongAuthenticationManager,
    GongAuthenticationError,
    GongSessionExpiredError
)

__version__ = "1.0.0"
__author__ = "CS-Ascension Team"

__all__ = [
    'GongAuthenticationManager',
    'GongAuthenticationError', 
    'GongSessionExpiredError'
]