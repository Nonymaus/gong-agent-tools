"""
Gong Session Extractor with _godcapture Integration

This module provides automated Gong session capture using the _godcapture tools.
Integrates with the stealth browser automation to capture fresh Gong sessions
with all required authentication artifacts.

Features:
- Automated browser navigation to Gong
- HAR capture with authentication artifact extraction
- JWT token and session cookie extraction
- Integration with Okta WebAuthn authentication
- Session validation and persistence
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add _godcapture to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "_godcapture"))

from scripts.stealth_godcapture_launcher import StealthGodCaptureSession
from core.analyzer import UniversalHARAnalyzer
from core.models import AuthenticationArtifact

# Import Gong authentication manager
from .auth_manager import GongAuthenticationManager, GongAuthenticationError

logger = logging.getLogger(__name__)


class GongSessionExtractor:
    """
    Automated Gong session extraction using _godcapture integration.
    
    This class provides automated session capture for Gong by:
    1. Launching stealth browser with WebAuthn credentials
    2. Navigating through Okta authentication to Gong
    3. Capturing network traffic and authentication artifacts
    4. Extracting and validating session data
    5. Returning ready-to-use Gong session
    """
    
    def __init__(self, headless: bool = True, session_timeout: int = 300,
                 minimal_mode: bool = False, collect_js_variables: bool = True,
                 collect_response_bodies: bool = True, early_exit_on_navigation: bool = False):
        """
        Initialize the Gong session extractor.

        Args:
            headless: Whether to run browser in headless mode
            session_timeout: Timeout for session capture in seconds
            minimal_mode: Enable minimal data collection for test suites
            collect_js_variables: Whether to collect JavaScript variables (slow)
            collect_response_bodies: Whether to analyze response bodies (slow)
            early_exit_on_navigation: Exit immediately after navigation success
        """
        self.headless = headless
        self.session_timeout = session_timeout
        self.minimal_mode = minimal_mode
        self.collect_js_variables = collect_js_variables
        self.collect_response_bodies = collect_response_bodies
        self.early_exit_on_navigation = early_exit_on_navigation
        self.auth_manager = GongAuthenticationManager()
        
        # Session capture state
        self.capture_session: Optional[StealthGodCaptureSession] = None
        self.session_dir: Optional[Path] = None
        self.captured_artifacts: List[AuthenticationArtifact] = []
        
        logger.info("🔧 Gong Session Extractor initialized")
        logger.info(f"🎯 Target: Gong platform authentication")
        logger.info(f"⚙️ Headless: {headless}, Timeout: {session_timeout}s")
        logger.info("🗜️ HAR compression: enabled (via _godcapture core)")
    
    async def capture_fresh_session(self, target_app: str = "Gong") -> Optional[Dict[str, Any]]:
        """
        Capture a fresh Gong session using automated browser navigation.
        
        Args:
            target_app: Name of the target app in Okta (default: "Gong")
            
        Returns:
            Dictionary containing session data and authentication artifacts
            
        Raises:
            GongAuthenticationError: If session capture fails
        """
        logger.info("🚀 Starting fresh Gong session capture")
        
        try:
            # Create session name with timestamp
            session_name = f"gong_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Initialize capture session with optimization parameters and credential monitoring
            self.capture_session = StealthGodCaptureSession(
                session_name=session_name,
                okta_session=True,
                headless=self.headless,
                minimal_mode=self.minimal_mode,
                collect_js_variables=self.collect_js_variables,
                collect_response_bodies=self.collect_response_bodies,
                early_exit_on_navigation=self.early_exit_on_navigation
            )

            # Enable credential monitoring for smart early exit
            try:
                from app_backend.agent_tools._godcapture.tests.universal_platform_credential_test import CredentialMonitor, PLATFORM_CONFIGS
                if "Gong" in PLATFORM_CONFIGS:
                    gong_config = PLATFORM_CONFIGS["Gong"]
                    self.capture_session.credential_monitor = CredentialMonitor(gong_config)
                    logger.info("✅ Credential monitoring enabled for Gong")
            except ImportError:
                logger.warning("⚠️ Credential monitoring not available, using standard capture")
            
            self.session_dir = self.capture_session.session_dir
            logger.info(f"📂 Session directory: {self.session_dir}")
            
            # Launch browser and capture session
            session_data = await self._run_capture_session(target_app)
            
            if not session_data:
                raise GongAuthenticationError("Failed to capture session data")
            
            logger.info("✅ Fresh Gong session captured successfully")
            return session_data
            
        except Exception as e:
            logger.error(f"❌ Failed to capture fresh session: {e}")
            raise GongAuthenticationError(f"Session capture failed: {e}")
    
    async def _run_capture_session(self, target_app: str) -> Optional[Dict[str, Any]]:
        """Run the actual session capture process"""
        try:
            logger.info("🌐 Launching stealth browser for session capture")

            # Run the capture session with target platform in programmatic mode
            session_data = await self.capture_session.launch_stealth_session(
                target_platform=target_app,
                programmatic_mode=True
            )

            if session_data:
                logger.info(f"✅ Session capture successful: {len(session_data.get('authentication_tokens', []))} tokens")
                return session_data
            else:
                logger.error("❌ Session capture failed - no data returned")
                return None
            
        except Exception as e:
            logger.error(f"❌ Error during capture session: {e}")
            return None
    
    async def _analyze_captured_data(self) -> Optional[Dict[str, Any]]:
        """Analyze captured HAR data and extract session information"""
        try:
            logger.info("🔍 Analyzing captured session data")
            
            # Find HAR file in session directory
            har_files = list(self.session_dir.glob("*.har"))
            if not har_files:
                logger.error("❌ No HAR file found in session directory")
                return None
            
            har_file = har_files[0]  # Use the first HAR file
            logger.info(f"📄 Analyzing HAR file: {har_file}")
            
            # Use UniversalHARAnalyzer to extract artifacts
            analyzer = UniversalHARAnalyzer()
            analysis_results = analyzer.analyze_har_file(str(har_file))
            
            if not analysis_results or 'artifacts' not in analysis_results:
                logger.error("❌ No artifacts found in HAR analysis")
                return None
            
            # Extract Gong session using authentication manager
            gong_session = self.auth_manager.extract_session_from_analysis_data(analysis_results)
            
            # Prepare session data for return
            session_data = {
                'session_id': gong_session.session_id,
                'user_email': gong_session.user_email,
                'cell_id': gong_session.cell_id,
                'workspace_id': gong_session.workspace_id,
                'company_id': gong_session.company_id,
                'authentication_tokens': [
                    {
                        'token_type': token.token_type,
                        'raw_token': token.raw_token,
                        'expires_at': token.expires_at.isoformat(),
                        'is_expired': token.is_expired,
                        'cell_id': token.cell_id,
                        'user_email': token.user_email
                    }
                    for token in gong_session.authentication_tokens
                ],
                'session_cookies': gong_session.session_cookies,
                'created_at': gong_session.created_at.isoformat(),
                'is_active': gong_session.is_active,
                'har_file_path': str(har_file),
                'session_dir': str(self.session_dir)
            }
            
            # Validate session has required components
            if not self._validate_session_data(session_data):
                logger.error("❌ Captured session data failed validation")
                return None
            
            logger.info("✅ Session data analysis completed successfully")
            logger.info(f"👤 User: {session_data['user_email']}")
            logger.info(f"🏢 Cell: {session_data['cell_id']}")
            logger.info(f"🔑 Tokens: {len(session_data['authentication_tokens'])}")
            
            # The HAR file is already compressed by StealthGodCaptureSession
            
            return session_data
            
        except Exception as e:
            logger.error(f"❌ Error analyzing captured data: {e}")
            return None
    
    def _validate_session_data(self, session_data: Dict[str, Any]) -> bool:
        """Validate that session data contains required components"""
        try:
            # Check required fields
            required_fields = ['user_email', 'authentication_tokens', 'session_cookies']
            for field in required_fields:
                if field not in session_data or not session_data[field]:
                    logger.error(f"❌ Missing required field: {field}")
                    return False
            
            # Check authentication tokens
            tokens = session_data['authentication_tokens']
            if not isinstance(tokens, list) or len(tokens) == 0:
                logger.error("❌ No authentication tokens found")
                return False
            
            # Check for valid JWT tokens
            valid_tokens = [t for t in tokens if not t.get('is_expired', True)]
            if not valid_tokens:
                logger.error("❌ All authentication tokens are expired")
                return False
            
            # Check user email format
            email = session_data['user_email']
            if not email or '@' not in email:
                logger.error("❌ Invalid user email format")
                return False
            
            logger.info("✅ Session data validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error validating session data: {e}")
            return False
    
    def get_session_file_path(self) -> Optional[Path]:
        """Get the path to the captured session HAR file"""
        if not self.session_dir:
            return None
        
        har_files = list(self.session_dir.glob("*.har"))
        return har_files[0] if har_files else None
    
    def cleanup_session_data(self) -> None:
        """Clean up temporary session data"""
        try:
            if self.capture_session:
                # The StealthGodCaptureSession handles its own cleanup
                pass
            
            logger.info("🧹 Session data cleanup completed")
            
        except Exception as e:
            logger.warning(f"⚠️ Error during cleanup: {e}")


class GongSessionManager:
    """
    High-level manager for Gong session lifecycle.
    
    Provides convenient methods for session capture, validation, and refresh.
    """
    
    def __init__(self):
        """Initialize the session manager"""
        self.auth_manager = GongAuthenticationManager()
        self.session_extractor = GongSessionExtractor()
        self.current_session_data: Optional[Dict[str, Any]] = None
        
        logger.info("🔧 Gong Session Manager initialized")
    
    async def get_fresh_session(self, target_app: str = "Gong") -> Dict[str, Any]:
        """
        Get a fresh Gong session, capturing if necessary.
        
        Args:
            target_app: Name of the target app in Okta
            
        Returns:
            Dictionary containing session data
            
        Raises:
            GongAuthenticationError: If session capture fails
        """
        logger.info("🔄 Getting fresh Gong session")
        
        # Capture fresh session
        session_data = await self.session_extractor.capture_fresh_session(target_app)
        
        if not session_data:
            raise GongAuthenticationError("Failed to capture fresh session")
        
        # Store current session
        self.current_session_data = session_data
        
        logger.info("✅ Fresh session ready for use")
        return session_data
    
    def get_current_session(self) -> Optional[Dict[str, Any]]:
        """Get the current session data"""
        return self.current_session_data
    
    def is_session_valid(self, session_data: Optional[Dict[str, Any]] = None) -> bool:
        """Check if session data is valid and not expired"""
        if session_data is None:
            session_data = self.current_session_data
        
        if not session_data:
            return False
        
        try:
            # Check authentication tokens
            tokens = session_data.get('authentication_tokens', [])
            valid_tokens = [t for t in tokens if not t.get('is_expired', True)]
            
            return len(valid_tokens) > 0
            
        except Exception as e:
            logger.error(f"❌ Error checking session validity: {e}")
            return False
    
    async def refresh_session_if_needed(self, target_app: str = "Gong") -> Dict[str, Any]:
        """
        Refresh session if current session is invalid or expired.
        
        Args:
            target_app: Name of the target app in Okta
            
        Returns:
            Dictionary containing valid session data
        """
        if self.is_session_valid():
            logger.info("✅ Current session is still valid")
            return self.current_session_data
        
        logger.info("🔄 Current session invalid, capturing fresh session")
        return await self.get_fresh_session(target_app)
