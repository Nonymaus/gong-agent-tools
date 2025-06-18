"""
Gong Platform Toolkit

This module provides comprehensive data extraction capabilities for the Gong platform,
including authentication, API client, data models, and validation components.

The toolkit follows the established pattern from the Salesforce implementation,
providing a consistent interface for data extraction across platforms.
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
