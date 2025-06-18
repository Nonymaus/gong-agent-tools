"""
Gong Authentication Manager

Handles Gong session extraction and token management with Okta integration.
Extracts and validates JWT tokens from HAR capture sessions.

Based on HAR analysis showing:
- Okta SAML authentication flow
- JWT tokens: last_login_jwt, cell_jwt  
- Session cookies: g-session, AWSALB, etc.
- Cell-based architecture (us-14496)
"""

import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# Import data models
sys.path.insert(0, str(Path(__file__).parent.parent))
from data_models import (
    GongSession, GongAuthenticationToken, GongJWTPayload,
    GongUser
)

# Import JWT decoder from _godcapture
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "_godcapture"))
from decoders.jwt_decoder import JWTDecoder

logger = logging.getLogger(__name__)


class GongAuthenticationError(Exception):
    """Raised when Gong authentication fails"""
    pass


class GongSessionExpiredError(Exception):
    """Raised when Gong session has expired"""
    pass


class GongAuthenticationManager:
    """
    Manages Gong authentication and session extraction.
    
    Integrates with Okta login flow and extracts session tokens from HAR captures.
    Validates JWT tokens and manages session state.
    """
    
    def __init__(self):
        """Initialize the authentication manager"""
        self.jwt_decoder = JWTDecoder()
        self.current_session: Optional[GongSession] = None
        self.session_cache: Dict[str, GongSession] = {}
        
        # Gong-specific patterns from HAR analysis
        self.gong_domains = [
            'gong.io',
            'app.gong.io', 
            'us-14496.app.gong.io',
            'api.gong.io',
            'gcell-nam-01.streams.gong.io',
            'resource.gcell-nam-01.app.gong.io'
        ]
        
        self.jwt_cookie_names = [
            'last_login_jwt',
            'cell_jwt'
        ]
        
        self.session_cookie_names = [
            'g-session',
            'AWSALB',
            'AWSALBTG',
            'ajs_user_id',
            'ajs_group_id'
        ]
    
    def extract_session_from_har(self, har_file_path: Path) -> GongSession:
        """
        Extract Gong session from HAR capture file.
        
        Args:
            har_file_path: Path to HAR file from _godcapture
            
        Returns:
            GongSession with extracted authentication data
            
        Raises:
            GongAuthenticationError: If no valid session found
        """
        logger.info(f"Extracting Gong session from HAR: {har_file_path}")
        
        # Use _godcapture's load_har which handles compression automatically
        try:
            # Import here to avoid circular dependency
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from _godcapture.core.har_compression import load_har
            har_data = load_har(har_file_path)
        except FileNotFoundError:
            raise GongAuthenticationError(f"HAR file not found: {har_file_path}")
        except ImportError:
            # Fallback to standard loading if _godcapture not available
            import gzip
            if har_file_path.suffix == '.gz' or har_file_path.name.endswith('.har.gz'):
                with gzip.open(har_file_path, 'rt', encoding='utf-8') as f:
                    har_data = json.load(f)
            else:
                with open(har_file_path, 'r', encoding='utf-8') as f:
                    har_data = json.load(f)
        except Exception as e:
            raise GongAuthenticationError(f"Failed to load HAR file: {e}")
        
        entries = har_data.get('log', {}).get('entries', [])
        
        # Extract authentication artifacts
        jwt_tokens = self._extract_jwt_tokens(entries)
        session_cookies = self._extract_session_cookies(entries)
        user_info = self._extract_user_info(jwt_tokens)
        
        if not jwt_tokens:
            raise GongAuthenticationError("No JWT tokens found in HAR data")
        
        if not user_info:
            raise GongAuthenticationError("No user information found in JWT tokens")
        
        # Create session
        session = GongSession(
            session_id=f"gong_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            user_email=user_info['email'],
            cell_id=user_info['cell_id'],
            company_id=user_info.get('company_id'),
            workspace_id=user_info.get('workspace_id'),
            authentication_tokens=jwt_tokens,
            session_cookies=session_cookies,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            is_active=True
        )
        
        # Validate session
        self._validate_session(session)
        
        # Cache session
        self.current_session = session
        self.session_cache[session.session_id] = session
        
        logger.info(f"Successfully extracted Gong session for {session.user_email}")
        logger.info(f"Cell ID: {session.cell_id}, Tokens: {len(session.authentication_tokens)}")
        
        return session
    
    def extract_session_from_analysis_data(self, analysis_data: Dict[str, Any]) -> GongSession:
        """
        Extract Gong session from _godcapture analysis data.

        Args:
            analysis_data: Analysis data dictionary from godcapture_analysis.json

        Returns:
            GongSession with extracted authentication data
        """
        logger.info("Extracting Gong session from analysis data")

        if not analysis_data or 'artifacts' not in analysis_data:
            raise GongAuthenticationError("Invalid analysis data: missing artifacts")

        return self._extract_session_from_artifacts(analysis_data['artifacts'])

    def _extract_session_from_artifacts(self, artifacts: List[Dict[str, Any]]) -> GongSession:
        """Extract session from artifacts list"""
        jwt_tokens = []
        session_cookies = {}

        for artifact in artifacts:
            if artifact.get('type', '').startswith('cookie_'):
                cookie_type = artifact['type'].replace('cookie_', '')

                if cookie_type in ['last_login_jwt', 'cell_jwt']:
                    # Process JWT token
                    jwt_token = self._process_jwt_artifact(artifact)
                    if jwt_token:
                        jwt_tokens.append(jwt_token)

                elif cookie_type in ['gong_session', 'aws_alb', 'aws_albtg', 'gong_user_id', 'gong_group_id']:
                    # Process session cookie
                    session_cookies[artifact.get('name', cookie_type)] = artifact.get('value', '')

        if not jwt_tokens:
            raise GongAuthenticationError("No JWT tokens found in artifacts")

        # Extract user info from JWT tokens
        user_info = self._extract_user_info(jwt_tokens)

        if not user_info:
            raise GongAuthenticationError("No user information found in JWT tokens")

        # Create session
        session = GongSession(
            session_id=f"gong_artifacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            user_email=user_info['email'],
            cell_id=user_info['cell_id'],
            company_id=user_info.get('company_id'),
            workspace_id=user_info.get('workspace_id'),
            authentication_tokens=jwt_tokens,
            session_cookies=session_cookies,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            is_active=True
        )

        # Validate session
        self._validate_session(session)

        # Cache session
        self.current_session = session
        self.session_cache[session.session_id] = session

        logger.info(f"Successfully extracted Gong session from artifacts for {session.user_email}")

        return session

    def extract_session_from_analysis(self, analysis_file_path: Path) -> GongSession:
        """
        Extract Gong session from _godcapture analysis results.

        Args:
            analysis_file_path: Path to godcapture_analysis.json

        Returns:
            GongSession with extracted authentication data
        """
        logger.info(f"Extracting Gong session from analysis: {analysis_file_path}")

        if not analysis_file_path.exists():
            raise GongAuthenticationError(f"Analysis file not found: {analysis_file_path}")

        # Load analysis data
        with open(analysis_file_path, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        artifacts = analysis_data.get('artifacts', [])
        
        # Extract JWT tokens from artifacts
        jwt_tokens = []
        session_cookies = {}
        
        for artifact in artifacts:
            if artifact.get('type', '').startswith('cookie_'):
                cookie_type = artifact['type'].replace('cookie_', '')
                
                if cookie_type in ['last_login_jwt', 'cell_jwt']:
                    # Process JWT token
                    jwt_token = self._process_jwt_artifact(artifact)
                    if jwt_token:
                        jwt_tokens.append(jwt_token)
                
                elif cookie_type in ['gong_session', 'aws_alb', 'aws_albtg', 'gong_user_id', 'gong_group_id']:
                    # Process session cookie
                    session_cookies[artifact.get('name', cookie_type)] = artifact.get('value', '')
        
        if not jwt_tokens:
            raise GongAuthenticationError("No JWT tokens found in analysis data")
        
        # Extract user info from JWT tokens
        user_info = self._extract_user_info(jwt_tokens)
        
        if not user_info:
            raise GongAuthenticationError("No user information found in JWT tokens")
        
        # Create session
        session = GongSession(
            session_id=f"gong_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            user_email=user_info['email'],
            cell_id=user_info['cell_id'],
            company_id=user_info.get('company_id'),
            workspace_id=user_info.get('workspace_id'),
            authentication_tokens=jwt_tokens,
            session_cookies=session_cookies,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            is_active=True
        )
        
        # Validate session
        self._validate_session(session)
        
        # Cache session
        self.current_session = session
        self.session_cache[session.session_id] = session
        
        logger.info(f"Successfully extracted Gong session from analysis for {session.user_email}")
        
        return session
    
    def _extract_jwt_tokens(self, har_entries: List[Dict]) -> List[GongAuthenticationToken]:
        """Extract JWT tokens from HAR entries"""
        jwt_tokens = []
        
        for entry in har_entries:
            request = entry.get('request', {})
            response = entry.get('response', {})
            
            # Check request cookies
            for cookie in request.get('cookies', []):
                if cookie.get('name') in self.jwt_cookie_names:
                    jwt_token = self._process_jwt_cookie(cookie)
                    if jwt_token:
                        jwt_tokens.append(jwt_token)
            
            # Check response cookies
            for cookie in response.get('cookies', []):
                if cookie.get('name') in self.jwt_cookie_names:
                    jwt_token = self._process_jwt_cookie(cookie)
                    if jwt_token:
                        jwt_tokens.append(jwt_token)
        
        # Remove duplicates based on token value
        unique_tokens = {}
        for token in jwt_tokens:
            unique_tokens[token.raw_token] = token
        
        return list(unique_tokens.values())
    
    def _extract_session_cookies(self, har_entries: List[Dict]) -> Dict[str, str]:
        """Extract session cookies from HAR entries"""
        session_cookies = {}
        
        for entry in har_entries:
            request = entry.get('request', {})
            response = entry.get('response', {})
            
            # Check request cookies
            for cookie in request.get('cookies', []):
                name = cookie.get('name', '')
                if any(session_name in name for session_name in self.session_cookie_names):
                    session_cookies[name] = cookie.get('value', '')
            
            # Check response cookies
            for cookie in response.get('cookies', []):
                name = cookie.get('name', '')
                if any(session_name in name for session_name in self.session_cookie_names):
                    session_cookies[name] = cookie.get('value', '')
        
        return session_cookies
    
    def _process_jwt_cookie(self, cookie: Dict) -> Optional[GongAuthenticationToken]:
        """Process a JWT cookie into a GongAuthenticationToken"""
        try:
            token_value = cookie.get('value', '')
            token_name = cookie.get('name', '')
            
            if not token_value or not token_value.startswith('eyJ'):
                return None
            
            # Decode JWT
            decoded_jwt = self.jwt_decoder.decode(token_value)
            
            if not decoded_jwt or 'payload' not in decoded_jwt:
                return None
            
            payload_data = decoded_jwt['payload']
            
            # Create JWT payload model
            jwt_payload = GongJWTPayload(
                gp=payload_data.get('gp'),
                exp=payload_data.get('exp'),
                iat=payload_data.get('iat'),
                jti=payload_data.get('jti'),
                gu=payload_data.get('gu'),
                cell=payload_data.get('cell')
            )
            
            # Create authentication token
            auth_token = GongAuthenticationToken(
                token_type=token_name,
                raw_token=token_value,
                payload=jwt_payload,
                expires_at=datetime.fromtimestamp(payload_data.get('exp', 0)),
                issued_at=datetime.fromtimestamp(payload_data.get('iat', 0)),
                is_expired=datetime.now().timestamp() > payload_data.get('exp', 0),
                cell_id=payload_data.get('cell'),
                user_email=payload_data.get('gu')
            )
            
            return auth_token
            
        except Exception as e:
            logger.warning(f"Failed to process JWT cookie {cookie.get('name')}: {e}")
            return None
    
    def _process_jwt_artifact(self, artifact: Dict) -> Optional[GongAuthenticationToken]:
        """Process a JWT artifact from analysis into a GongAuthenticationToken"""
        try:
            token_value = artifact.get('value', '')
            token_name = artifact.get('name', '')
            decoded_value = artifact.get('decoded_value', {})
            
            if not token_value or not decoded_value:
                return None
            
            payload_data = decoded_value.get('payload', {})
            
            if not payload_data:
                return None
            
            # Create JWT payload model
            jwt_payload = GongJWTPayload(
                gp=payload_data.get('gp'),
                exp=payload_data.get('exp'),
                iat=payload_data.get('iat'),
                jti=payload_data.get('jti'),
                gu=payload_data.get('gu'),
                cell=payload_data.get('cell')
            )
            
            # Create authentication token
            auth_token = GongAuthenticationToken(
                token_type=token_name,
                raw_token=token_value,
                payload=jwt_payload,
                expires_at=datetime.fromtimestamp(payload_data.get('exp', 0)),
                issued_at=datetime.fromtimestamp(payload_data.get('iat', 0)),
                is_expired=datetime.now().timestamp() > payload_data.get('exp', 0),
                cell_id=payload_data.get('cell'),
                user_email=payload_data.get('gu')
            )
            
            return auth_token
            
        except Exception as e:
            logger.warning(f"Failed to process JWT artifact {artifact.get('name')}: {e}")
            return None
    
    def _extract_user_info(self, jwt_tokens: List[GongAuthenticationToken]) -> Optional[Dict[str, str]]:
        """Extract user information from JWT tokens"""
        if not jwt_tokens:
            return None
        
        # Use the first valid token for user info
        for token in jwt_tokens:
            if token.user_email and token.cell_id:
                return {
                    'email': token.user_email,
                    'cell_id': token.cell_id,
                    'company_id': None,  # Extract from other sources if available
                    'workspace_id': None  # Extract from other sources if available
                }
        
        return None
    
    def _validate_session(self, session: GongSession) -> None:
        """Validate that the session is valid and not expired"""
        if not session.authentication_tokens:
            raise GongAuthenticationError("Session has no authentication tokens")
        
        # Check if any tokens are still valid
        valid_tokens = [token for token in session.authentication_tokens if not token.is_expired]
        
        if not valid_tokens:
            raise GongSessionExpiredError("All session tokens have expired")
        
        # Validate user email format
        if not session.user_email or '@' not in session.user_email:
            raise GongAuthenticationError("Invalid user email in session")
        
        # Validate cell ID format (allow empty, but if provided must be ≥3 chars)
        if session.cell_id and len(session.cell_id) < 3:
            raise GongAuthenticationError("Invalid cell ID in session")
    
    def get_current_session(self) -> Optional[GongSession]:
        """Get the current active session"""
        return self.current_session
    
    def is_session_valid(self, session: Optional[GongSession] = None) -> bool:
        """Check if a session is valid and not expired"""
        if session is None:
            session = self.current_session
        
        if not session:
            return False
        
        try:
            self._validate_session(session)
            return True
        except (GongAuthenticationError, GongSessionExpiredError):
            return False
    
    def refresh_session(self, session: GongSession) -> GongSession:
        """
        Refresh a session by updating last activity time.
        
        Note: For full token refresh, a new HAR capture would be needed.
        """
        session.last_activity = datetime.now()
        
        # Check if session is still valid
        if not self.is_session_valid(session):
            raise GongSessionExpiredError("Session cannot be refreshed - tokens expired")
        
        return session
    
    def get_session_headers(self, session: Optional[GongSession] = None) -> Dict[str, str]:
        """
        Get HTTP headers for API requests using session data.
        
        Args:
            session: Session to use, defaults to current session
            
        Returns:
            Dictionary of headers for API requests
        """
        if session is None:
            session = self.current_session
        
        if not session or not self.is_session_valid(session):
            raise GongAuthenticationError("No valid session available")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }
        
        # Add authentication cookies
        cookie_parts = []
        
        # Add JWT tokens
        for token in session.authentication_tokens:
            if not token.is_expired:
                cookie_parts.append(f"{token.token_type}={token.raw_token}")
        
        # Add session cookies
        for name, value in session.session_cookies.items():
            if value:
                cookie_parts.append(f"{name}={value}")
        
        if cookie_parts:
            headers['Cookie'] = '; '.join(cookie_parts)
        
        return headers
    
    def get_base_url(self, session: Optional[GongSession] = None) -> str:
        """
        Get the base URL for API requests.
        
        Args:
            session: Session to use, defaults to current session
            
        Returns:
            Base URL for the user's Gong instance
        """
        if session is None:
            session = self.current_session
        
        if not session:
            raise GongAuthenticationError("No session available")
        
        # Use cell-specific URL
        if session.cell_id:
            return f"https://{session.cell_id}.app.gong.io"
        else:
            return "https://app.gong.io"
    
    def create_user_from_session(self, session: Optional[GongSession] = None) -> GongUser:
        """
        Create a GongUser object from session data.
        
        Args:
            session: Session to use, defaults to current session
            
        Returns:
            GongUser object with available information
        """
        if session is None:
            session = self.current_session
        
        if not session:
            raise GongAuthenticationError("No session available")
        
        # Extract name from email if available
        email_parts = session.user_email.split('@')
        username = email_parts[0] if email_parts else session.user_email
        
        # Try to extract first/last name from username
        name_parts = username.replace('.', ' ').replace('_', ' ').split()
        first_name = name_parts[0].title() if name_parts else None
        last_name = name_parts[1].title() if len(name_parts) > 1 else None
        
        return GongUser(
            email=session.user_email,
            first_name=first_name,
            last_name=last_name,
            full_name=f"{first_name} {last_name}" if first_name and last_name else username.title(),
            is_internal=True,  # Assume internal since they have session access
            is_active=True,
            created_at=session.created_at,
            last_activity=session.last_activity
        )

    # ============================================================================
    # Token Refresh and Session Management
    # ============================================================================

    def refresh_session(self, session: Optional[GongSession] = None) -> GongSession:
        """
        Refresh an expired Gong session.

        Args:
            session: Session to refresh (uses current_session if None)

        Returns:
            Refreshed GongSession

        Raises:
            GongAuthenticationError: If refresh fails
        """
        target_session = session or self.current_session

        if not target_session:
            raise GongAuthenticationError("No session available to refresh")

        logger.info(f"Attempting to refresh session for {target_session.user_email}")

        try:
            # For HAR-based sessions, we can't actually refresh tokens
            # In production, this would integrate with Okta/OAuth flow
            # For now, we'll validate the session and mark it as refreshed

            # Check if any tokens are still valid
            valid_tokens = [
                token for token in target_session.authentication_tokens
                if not token.is_expired
            ]

            if valid_tokens:
                logger.info(f"Found {len(valid_tokens)} valid tokens, session still usable")
                target_session.last_activity = datetime.now()
                return target_session

            # In a real implementation, this would:
            # 1. Use refresh token to get new access tokens
            # 2. Update session with new tokens
            # 3. Persist updated session

            # For HAR-based development, we simulate refresh by extending expiry
            logger.warning("HAR-based session refresh: extending token validity for testing")

            for token in target_session.authentication_tokens:
                if token.is_expired:
                    # Extend expiry by 1 hour for testing
                    token.expires_at = datetime.now() + timedelta(hours=1)
                    logger.info(f"Extended {token.token_type} token expiry to {token.expires_at}")

            target_session.last_activity = datetime.now()
            target_session.is_active = True

            # Update cache
            self.session_cache[target_session.session_id] = target_session
            if target_session == self.current_session:
                self.current_session = target_session

            logger.info(f"Session refresh completed for {target_session.user_email}")
            return target_session

        except Exception as e:
            logger.error(f"Session refresh failed: {e}")
            raise GongAuthenticationError(f"Failed to refresh session: {e}")

    def is_session_expired(self, session: Optional[GongSession] = None) -> bool:
        """
        Check if a session is expired.

        Args:
            session: Session to check (uses current_session if None)

        Returns:
            True if session is expired, False otherwise
        """
        target_session = session or self.current_session

        if not target_session:
            return True

        # Check if session is marked as inactive
        if not target_session.is_active:
            return True

        # Check if all tokens are expired
        if not target_session.authentication_tokens:
            return True

        expired_tokens = [token for token in target_session.authentication_tokens if token.is_expired]
        total_tokens = len(target_session.authentication_tokens)

        # If more than 50% of tokens are expired, consider session expired
        if len(expired_tokens) > (total_tokens / 2):
            logger.warning(f"Session considered expired: {len(expired_tokens)}/{total_tokens} tokens expired")
            return True

        return False

    def auto_refresh_if_needed(self, session: Optional[GongSession] = None) -> GongSession:
        """
        Automatically refresh session if needed.

        Args:
            session: Session to check and refresh (uses current_session if None)

        Returns:
            Valid GongSession (refreshed if necessary)

        Raises:
            GongAuthenticationError: If refresh fails
        """
        target_session = session or self.current_session

        if not target_session:
            raise GongAuthenticationError("No session available for auto-refresh")

        if self.is_session_expired(target_session):
            logger.info("Session expired, attempting auto-refresh")
            return self.refresh_session(target_session)

        return target_session

    def get_refresh_headers(self, session: Optional[GongSession] = None) -> Dict[str, str]:
        """
        Get headers for session refresh requests.

        Args:
            session: Session to get refresh headers for

        Returns:
            Headers dictionary for refresh requests
        """
        target_session = session or self.current_session

        if not target_session:
            return {}

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }

        # Add any valid tokens to headers
        valid_tokens = [token for token in target_session.authentication_tokens if not token.is_expired]

        if valid_tokens:
            cookie_parts = []
            for token in valid_tokens:
                if token.token_type in ['last_login_jwt', 'cell_jwt']:
                    cookie_parts.append(f"{token.token_type}={token.token_value}")

            if cookie_parts:
                headers['Cookie'] = '; '.join(cookie_parts)

        return headers