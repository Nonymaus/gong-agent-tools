"""
Gong API Client Package

Provides methods for extracting Gong data using session tokens.
Includes error handling, rate limiting, and comprehensive endpoint coverage.

Key Features:
- Session-based authentication with JWT tokens
- Rate limiting and retry logic
- Comprehensive endpoint coverage (232 API patterns)
- Error handling and timeout management
- Data extraction for all major Gong objects

Usage:
    from gong.api_client import GongAPIClient
    from gong.authentication import GongAuthenticationManager
    
    # Initialize client with authentication
    auth_manager = GongAuthenticationManager()
    session = auth_manager.extract_session_from_analysis(analysis_file)
    
    client = GongAPIClient(auth_manager)
    client.set_session(session)
    
    # Extract data
    calls = client.get_my_calls(limit=50)
    deals = client.get_deals(limit=50)
    users = client.get_users()
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