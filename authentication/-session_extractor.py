"""
Module: session_extractor
Type: Internal Module

Purpose:
Gong integration component handling specific functionality within the CS-Ascension platform.

Data Flow:
- Input: Configuration parameters, Authentication credentials
- Processing: Input validation, Data extraction, API interaction
- Output: List of extracted data, Dictionary responses, Error states and exceptions

Critical Because:
Central integration point for Gong - without this, no Gong data can be accessed.

Dependencies:
- Requires: logging
- Used By: app_backend.ingestion.orchestrator, app_backend.api_bridge.server

Author: Julia Evans
Date: 2025-06-20
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class GongSessionConfig:
    """
    Gong-specific session configuration.
    
    Provides platform-specific settings and data structures for Gong authentication.
    """
    
    PLATFORM_NAME = "Gong"
    
    # Gong-specific URLs
    GONG_BASE_URL = "https://app.gong.io"
    GONG_API_BASE = "https://app.gong.io/api"
    
    # Expected token types
    TOKEN_TYPES = ["access", "refresh", "id"]
    
    # Required session fields
    REQUIRED_FIELDS = [
        "user_email",
        "cell_id",
        "workspace_id",
        "authentication_tokens",
        "session_cookies"
    ]
    
    # Cookie names to capture
    IMPORTANT_COOKIES = [
        "gong-auth",
        "gong-session",
        "AWSALB",
        "AWSALBCORS"
    ]
    
    @staticmethod
    def validate_session_data(session_data: Dict[str, Any]) -> bool:
        """
        Validate that session data contains required Gong components.
        
        Args:
            session_data: Session data dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check required fields
            for field in GongSessionConfig.REQUIRED_FIELDS:
                if field not in session_data or not session_data[field]:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            # Check authentication tokens
            tokens = session_data.get('authentication_tokens', [])
            if not isinstance(tokens, list) or len(tokens) == 0:
                logger.error("No authentication tokens found")
                return False
            
            # Check for valid tokens
            valid_tokens = [t for t in tokens if not t.get('is_expired', True)]
            if not valid_tokens:
                logger.error("All authentication tokens are expired")
                return False
            
            logger.info("Session data validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Error validating session data: {e}")
            return False
    
    @staticmethod
    def get_platform_config() -> Dict[str, Any]:
        """Get Gong platform configuration for _godcapture"""
        return {
            "name": GongSessionConfig.PLATFORM_NAME,
            "base_url": GongSessionConfig.GONG_BASE_URL,
            "api_base": GongSessionConfig.GONG_API_BASE,
            "token_types": GongSessionConfig.TOKEN_TYPES,
            "important_cookies": GongSessionConfig.IMPORTANT_COOKIES,
            "validation_func": GongSessionConfig.validate_session_data
        }