"""
Module: __init__
Type: Internal Module

Purpose:
Gong integration component handling specific functionality within the CS-Ascension platform.

Data Flow:
- Input: Configuration parameters, Authentication credentials
- Processing: Data extraction, API interaction
- Output: Processed results

Critical Because:
Central integration point for Gong - without this, no Gong data can be accessed.

Dependencies:
- Requires: agent, authentication.auth_manager, api_client.client, data_models.models
- Used By: app_backend.ingestion.orchestrator, app_backend.api_bridge.server

Author: Julia Evans
Date: 2025-06-20
"""
__version__ = "1.0.0"
__author__ = "CS-Ascension Team"

# Import main components for easy access
from .agent import GongAgent
from .authentication.auth_manager import GongAuthenticationManager
from .api_client.client import GongAPIClient
from .data_models.models import (
    GongUser, GongContact, GongDeal, GongCall, GongAccount,
    GongSession, GongAuthenticationToken, GongAPIResponse
)

__all__ = [
    "GongAgent",
    "GongAuthenticationManager",
    "GongAPIClient",
    "GongUser",
    "GongContact",
    "GongDeal",
    "GongCall",
    "GongAccount",
    "GongSession",
    "GongAuthenticationToken",
    "GongAPIResponse"
]
