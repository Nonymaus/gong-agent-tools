"""
Gong Authentication Package

Handles Gong session extraction and token management with Okta integration.
Extracts and validates JWT tokens from HAR capture sessions.

Key Features:
- JWT token extraction and validation
- Session management with expiration checking
- Okta SAML integration support
- HAR capture session extraction
- Cell-based architecture support (us-14496)

Usage:
    from gong.authentication import GongAuthenticationManager
    
    # Extract session from HAR capture
    auth_manager = GongAuthenticationManager()
    session = auth_manager.extract_session_from_har(har_file_path)
    
    # Get headers for API requests
    headers = auth_manager.get_session_headers(session)
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