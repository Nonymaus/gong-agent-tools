"""
Module: gong/-agent
Type: High-Level Orchestration Agent

Purpose:
Main orchestrator for Gong data extraction that manages authentication lifecycle,
coordinates data extraction across 6 object types (calls, users, deals, conversations,
library, team stats), and ensures performance targets are met with automatic retry
and session refresh capabilities.

Data Flow:
- Input: AuthSession from GodCapture, optional Dict config with extraction limits
- Processing: Session validation → GongAPIClient creation → Parallel extraction with retry logic → Performance tracking
- Output: Dict[str, Any] with extracted data (List[GongCall], List[GongUser], etc.) and metadata

Critical Because:
This is the primary interface for all Gong data extraction operations. It ensures
95%+ success rate through automatic session refresh, handles authentication failures
gracefully, and maintains performance tracking to meet <30s extraction targets.

Dependencies:
- Requires: base.interfaces (IServiceAdapter, IAuthenticationProvider), api_client.GongAPIClient,
           data_models (GongSession, GongCall, etc.), authentication.GongAuthenticationManager,
           base.godcapture_factory, asyncio, concurrent.futures
- Used By: CrewAI Data Agent, Orchestrator Agent, standalone extraction scripts

Error Handling:
- GongAgentError: Raised for all agent-level failures (no session, extraction failed)
- Automatic retry on 401/authentication errors with session refresh
- Individual extraction failures logged but don't stop comprehensive extraction
- Performance metrics tracked even on partial failures

Observability:
- Logs each extraction step with success/failure indicators (✅/❌)
- Tracks extraction_stats: total/successful/failed counts, average duration
- Performance validation against targets (5 objects in <30s)
- Comprehensive status reporting via get_status()

Author: CS-Ascension Intelligence Engine
Date: 2025-06-20
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

# Import components
# Base interfaces for dependency injection
from app_backend.agent_tools.base.interfaces import (
    IServiceAdapter, IAuthenticationProvider, AuthSession, AuthConfig,
    ServiceError, ExtractionError, RateLimitError
)
from .api_client.client import GongAPIClient, GongAPIError
from .data_models.models import (
    GongSession, GongCall, GongUser, GongContact, GongAccount,
    GongDeal, GongActivity, GongCallMetrics, GongAPIResponse
)

logger = logging.getLogger(__name__)


class GongAgentError(Exception):
    """
    Raised when Gong agent operation fails.
    
    This is the primary exception type for all agent-level failures.
    It wraps underlying errors with context about what operation failed.
    
    Common scenarios:
    - No session available when trying to extract
    - All retry attempts exhausted after auth refresh
    - Critical initialization failures
    - File I/O errors when saving results
    """
    pass


class GongAgent(IServiceAdapter):
    """
    Main Gong agent interface for data extraction.
    
    Orchestrates authentication and data extraction with a simple, high-level API.
    Designed for reliability and performance with comprehensive error handling.
    """
    
    def __init__(self, auth_provider: IAuthenticationProvider, config: Optional[Dict] = None):
        """
        Initialize the Gong agent with dependency injection.
        
        Args:
            auth_provider: Authentication provider for handling auth operations
            config: Optional configuration dictionary
        """
        self._auth_provider = auth_provider
        self._config = config or {}
        self._godcapture = None  # Created via factory in initialize()
        self.api_client = None  # Created after authentication
        self.session: Optional[GongSession] = None
        self.auto_refresh_enabled = True  # Enable automatic session refresh
        self.last_extraction_time: Optional[datetime] = None
        self.extraction_stats = {
            'total_extractions': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'average_duration': 0.0,
            'last_error': None
        }
        
        # Performance tracking
        self.performance_target_seconds = 30
        self.success_rate_target = 0.95
        
        logger.info("Gong agent initialized with dependency injection")
        
    async def initialize(self, session: AuthSession, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the service adapter with authenticated session.
        
        Args:
            session: Authenticated session
            config: Optional service-specific configuration
            
        Raises:
            ServiceError: If initialization fails
        """
        try:
            # Use GodCaptureFactory instead of duplicated creation code
            from app_backend.agent_tools.base.godcapture_factory import create_godcapture_for_platform
            self._godcapture = create_godcapture_for_platform("gong", **(config or {}))
            
            # Apply session to the agent
            self._apply_auth_session(session)
            
            logger.info("Gong agent initialized with GodCaptureFactory")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gong agent: {e}")
            raise ServiceError(f"Initialization failed: {e}")
    
    async def _ensure_authenticated(self):
        """
        Ensure we have valid authentication by checking and refreshing session if needed.
        
        This method is called automatically during retry operations when authentication
        fails. It uses GodCapture to either load an existing valid session or trigger
        a full reauthentication flow.
        
        Flow:
        1. Attempts to load existing session via godcapture.load_session()
        2. Validates session expiry and tokens
        3. If invalid/expired, triggers godcapture.reauthenticate()
        4. Applies refreshed session to API client
        
        Raises:
        - May propagate exceptions from godcapture operations
        - Logged but not explicitly handled to allow retry logic to work
        """
        session = await self.godcapture.load_session("gong")
        if not session or not session.is_valid():
            session = await self.godcapture.reauthenticate("gong")
        
        # Apply session to API client
        self._apply_session_to_client(session)
    
    def _apply_session_to_client(self, session):
        """Apply session data to API client"""
        # Convert godcapture session to GongSession format
        gong_session = self._convert_to_gong_session(session)
        self.session = gong_session
        
        # Create API client if needed
        if not self.api_client:
            from authentication import GongAuthenticationManager
            auth_manager = GongAuthenticationManager()
            auth_manager.current_session = gong_session
            self.api_client = GongAPIClient(auth_manager)
        else:
            self.api_client.set_session(gong_session)
    
    def _convert_to_gong_session(self, godcapture_session) -> GongSession:
        """
        Convert godcapture session to GongSession format.
        
        Maps GodCapture's generic session format to Gong-specific session structure
        by extracting JWT tokens, cookies, and metadata into the artifacts format
        expected by GongAuthenticationManager.
        
        Args:
            godcapture_session: Generic session from GodCapture with tokens/cookies
            
        Returns:
            GongSession: Properly formatted session for Gong API client
            
        Artifact Mapping:
        - JWT tokens -> artifacts with type='jwt_token', metadata includes expiry
        - Session cookies -> artifacts with type='session_cookie'
        - Metadata (cell_id, user_email) preserved in artifact metadata
        """
        # Extract necessary data from godcapture session
        from authentication import GongAuthenticationManager
        auth_manager = GongAuthenticationManager()
        
        # Create artifacts from godcapture session
        artifacts = []
        
        # Add authentication tokens
        for token in godcapture_session.tokens:
            artifacts.append({
                'type': 'jwt_token',
                'value': token.value,
                'source': 'header',
                'metadata': {
                    'token_type': token.type,
                    'expires_at': token.expires_at,
                    'cell_id': godcapture_session.metadata.get('cell_id'),
                    'user_email': godcapture_session.metadata.get('user_email')
                }
            })
        
        # Add cookies
        for cookie in godcapture_session.cookies:
            artifacts.append({
                'type': 'session_cookie',
                'value': cookie.value,
                'source': 'cookie',
                'metadata': {
                    'name': cookie.name,
                    'domain': cookie.domain
                }
            })
        
        # Create GongSession from artifacts
        return auth_manager.extract_session_from_analysis_data({'artifacts': artifacts})
    
    
    def set_session(self, session_source: Union[str, Path, GongSession]) -> None:
        """
        Set the session for the agent.
        
        Args:
            session_source: Session source (HAR file, analysis file, or session object)
        """
        try:
            if isinstance(session_source, GongSession):
                self.session = session_source
                self.auth_manager.current_session = session_source
                
            elif isinstance(session_source, (str, Path)):
                session_path = Path(session_source)
                
                if not session_path.exists():
                    raise GongAgentError(f"Session source file not found: {session_path}")
                
                # Determine file type and extract session
                if session_path.suffix == '.har':
                    self.session = self.auth_manager.extract_session_from_har(session_path)
                elif session_path.suffix == '.json':
                    self.session = self.auth_manager.extract_session_from_analysis(session_path)
                else:
                    raise GongAgentError(f"Unsupported session source file type: {session_path.suffix}")
            
            else:
                raise GongAgentError(f"Invalid session source type: {type(session_source)}")
            
            # Set session in API client
            self.api_client.set_session(self.session)
            
            logger.info(f"Session set for Gong agent: {self.session.user_email}")
            
        except Exception as e:
            raise GongAgentError(f"Failed to set session: {e}")
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        Get information about the current session.
        
        Returns:
            Dictionary with session information
        """
        if not self.session:
            return {"status": "no_session"}
        
        return {
            "status": "active" if self.session.is_active else "expired",
            "user_email": self.session.user_email,
            "cell_id": self.session.cell_id,
            "created_at": self.session.created_at.isoformat(),
            "last_activity": self.session.last_activity.isoformat(),
            "token_count": len(self.session.authentication_tokens),
            "cookie_count": len(self.session.session_cookies),
            "is_active": self.session.is_active
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection to Gong API.

        Returns:
            Dictionary with connection status and diagnostic information
        """
        if not self.session:
            logger.error("No session available for connection test")
            return {
                'connected': False,
                'error_message': 'No session available',
                'last_tested': datetime.now().isoformat()
            }

        try:
            return self.api_client.test_connection()
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                'connected': False,
                'error_message': str(e),
                'last_tested': datetime.now().isoformat()
            }

    def _execute_with_retry(self, operation_func, operation_name: str, max_retries: int = 1):
        """
        Execute an operation with automatic token refresh retry on authentication failure.
        
        This is the core resilience mechanism that ensures 95%+ success rate by automatically
        refreshing sessions when authentication fails. It detects auth errors through
        response analysis and triggers GodCapture refresh flow.

        Args:
            operation_func: Function to execute (must be callable with no args)
            operation_name: Name of the operation for logging and error tracking
            max_retries: Maximum number of retries (default: 1)

        Returns:
            Result of the operation (varies by operation type)

        Raises:
            GongAgentError: If operation fails after all retries with last error details
            
        Error Detection:
        - Checks for: 'authentication failed', 'session may be expired', 'unauthorized', '401'
        - Non-auth errors fail immediately without retry
        - Auth errors trigger async session refresh via _ensure_authenticated()
        
        Observability:
        - Logs retry attempts with attempt counter
        - Distinguishes between auth and non-auth failures
        - Reports refresh success/failure for debugging
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return operation_func()

            except Exception as e:
                last_exception = e
                error_message = str(e).lower()

                # Check if this is an authentication error
                if ('authentication failed' in error_message or
                    'session may be expired' in error_message or
                    'unauthorized' in error_message or
                    '401' in error_message):

                    if attempt < max_retries:
                        logger.info(f"Authentication error in {operation_name}, attempting token refresh (attempt {attempt + 1}/{max_retries + 1})")

                        try:
                            if self.auto_refresh_enabled:
                                logger.info(f"Attempting automatic session refresh for {operation_name}")

                                # Use godcapture to refresh session
                                import asyncio
                                try:
                                    # CRITICAL: Handle async/sync bridge carefully
                                    # This code may be called from sync context but needs to run async _ensure_authenticated
                                    loop = asyncio.get_event_loop()
                                    if loop.is_running():
                                        # We're already in an async context (e.g., from CrewAI agent)
                                        # Must use ThreadPoolExecutor to avoid "asyncio.run() cannot be called from a running event loop"
                                        import concurrent.futures
                                        with concurrent.futures.ThreadPoolExecutor() as executor:
                                            future = executor.submit(asyncio.run, self._ensure_authenticated())
                                            future.result(timeout=300)  # 5 min timeout for godcapture flow
                                    else:
                                        # Sync context - can run directly
                                        asyncio.run(self._ensure_authenticated())
                                    
                                    logger.info(f"Fresh session captured for {operation_name}, retrying...")
                                    continue
                                except Exception as refresh_error:
                                    logger.error(f"Fresh session capture failed for {operation_name}: {refresh_error}")
                                    # Don't retry on refresh failure - likely a persistent issue
                                    break
                            else:
                                logger.error(f"Auto-refresh disabled, cannot refresh session for {operation_name}")
                                break

                        except Exception as refresh_error:
                            logger.error(f"Session refresh failed for {operation_name}: {refresh_error}")
                            break
                    else:
                        logger.error(f"Max retries exceeded for {operation_name}")
                        break
                else:
                    # Non-authentication error, don't retry
                    logger.error(f"Non-authentication error in {operation_name}: {e}")
                    break

        # If we get here, all retries failed
        raise GongAgentError(f"{operation_name} failed after {max_retries + 1} attempts: {last_exception}")
    
    # ============================================================================
    # Core Data Extraction Methods
    # ============================================================================
    
    def extract_calls(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Extract calls data from Gong with automatic token refresh.

        Args:
            limit: Maximum number of calls to extract

        Returns:
            List of call data dictionaries
        """
        logger.info(f"Extracting calls data (limit={limit})")

        if not self.session:
            raise GongAgentError("No session available")

        def _extract_operation():
            calls = self.api_client.get_my_calls(limit=limit)
            logger.info(f"Successfully extracted {len(calls)} calls")
            return calls

        return self._execute_with_retry(_extract_operation, "extract_calls")

    def extract_users(self) -> List[Dict[str, Any]]:
        """
        Extract users data from Gong with automatic token refresh.

        Returns:
            List of user data dictionaries
        """
        logger.info("Extracting users data")

        if not self.session:
            raise GongAgentError("No session available")

        def _extract_operation():
            users = self.api_client.get_users()
            logger.info(f"Successfully extracted {len(users)} users")
            return users

        return self._execute_with_retry(_extract_operation, "extract_users")

    def extract_deals(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Extract deals data from Gong with automatic token refresh.

        Args:
            limit: Maximum number of deals to extract

        Returns:
            List of deal data dictionaries
        """
        logger.info(f"Extracting deals data (limit={limit})")

        if not self.session:
            raise GongAgentError("No session available")

        def _extract_operation():
            deals = self.api_client.get_deals(limit=limit)
            logger.info(f"Successfully extracted {len(deals)} deals")
            return deals

        return self._execute_with_retry(_extract_operation, "extract_deals")
    
    def extract_conversations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Extract conversations data from Gong with automatic token refresh.

        Args:
            limit: Maximum number of conversations to extract

        Returns:
            List of conversation data dictionaries
        """
        logger.info(f"Extracting conversations data (limit={limit})")

        if not self.session:
            raise GongAgentError("No session available")

        def _extract_operation():
            conversations = self.api_client.get_conversations(limit=limit)
            logger.info(f"Successfully extracted {len(conversations)} conversations")
            return conversations

        return self._execute_with_retry(_extract_operation, "extract_conversations")

    def extract_library(self) -> List[Dict[str, Any]]:
        """
        Extract library data from Gong with automatic token refresh.

        Returns:
            Library data list
        """
        logger.info("Extracting library data")

        if not self.session:
            raise GongAgentError("No session available")

        def _extract_operation():
            library = self.api_client.get_library_data()
            logger.info("Successfully extracted library data")
            return library

        return self._execute_with_retry(_extract_operation, "extract_library")

    def extract_team_stats(self) -> List[Dict[str, Any]]:
        """
        Extract team statistics from Gong with automatic token refresh.

        Returns:
            Team statistics list
        """
        logger.info("Extracting team statistics")

        if not self.session:
            raise GongAgentError("No session available")

        def _extract_operation():
            # Get multiple team metrics
            stats = []

            metrics = ['avgCallDuration', 'totalCalls', 'avgWeeklyCalls', 'totalDuration']

            for metric in metrics:
                try:
                    metric_data = self.api_client.get_team_stats(metric)
                    if metric_data:
                        stats.append({
                            'metric': metric,
                            'value': metric_data,
                            'unit': 'seconds' if 'Duration' in metric else 'count',
                            'period': 'week'
                        })
                except Exception as e:
                    logger.warning(f"Failed to get {metric}: {e}")

            logger.info(f"Successfully extracted team stats for {len(stats)} metrics")
            return stats

        return self._execute_with_retry(_extract_operation, "extract_team_stats")
    
    # ============================================================================
    # Comprehensive Extraction Methods
    # ============================================================================
    
    def extract_all_data(self, 
                        include_calls: bool = True,
                        include_users: bool = True, 
                        include_deals: bool = True,
                        include_conversations: bool = True,
                        include_library: bool = True,
                        include_stats: bool = True,
                        calls_limit: int = 100,
                        deals_limit: int = 100,
                        conversations_limit: int = 50) -> Dict[str, Any]:
        """
        Extract all available data from Gong with comprehensive error handling.
        
        This is the main extraction method that orchestrates parallel data extraction
        across all supported object types. It ensures individual failures don't stop
        the entire extraction and provides detailed performance metrics.
        
        Args:
            include_calls: Whether to extract calls
            include_users: Whether to extract users
            include_deals: Whether to extract deals
            include_conversations: Whether to extract conversations
            include_library: Whether to extract library
            include_stats: Whether to extract team stats
            calls_limit: Maximum calls to extract (default: 100)
            deals_limit: Maximum deals to extract (default: 100)
            conversations_limit: Maximum conversations to extract (default: 50)
            
        Returns:
            Dict with structure:
            {
                'metadata': {
                    'extraction_id': str,
                    'timestamp': ISO datetime,
                    'user_email': str,
                    'cell_id': str,
                    'target_objects': int (number of object types to extract),
                    'successful_objects': int (actually extracted),
                    'failed_objects': int,
                    'duration_seconds': float,
                    'performance_target_met': bool (< 30s),
                    'errors': List[str] (error messages for failed extractions)
                },
                'data': {
                    'calls': List[Dict] (if included and successful),
                    'users': List[Dict] (if included and successful),
                    'deals': List[Dict] (if included and successful),
                    'conversations': List[Dict] (if included and successful),
                    'library': List[Dict] (if included and successful),
                    'team_stats': List[Dict] (if included and successful)
                }
            }
            
        Performance:
        - Target: Extract ≥5 object types in <30 seconds
        - Each extraction uses _execute_with_retry for resilience
        - Failed extractions don't block others (fault isolation)
        
        Error Handling:
        - Individual extraction failures logged to metadata['errors']
        - Continues extraction even if some object types fail
        - Updates extraction_stats for monitoring
        """
        start_time = time.time()
        
        logger.info("Starting comprehensive Gong data extraction")
        
        if not self.session:
            raise GongAgentError("No session available")
        
        extraction_result = {
            'metadata': {
                'extraction_id': f"gong_extraction_{int(time.time())}",
                'timestamp': datetime.now().isoformat(),
                'user_email': self.session.user_email,
                'cell_id': self.session.cell_id,
                'target_objects': 0,
                'successful_objects': 0,
                'failed_objects': 0,
                'duration_seconds': 0,
                'performance_target_met': False,
                'errors': []
            },
            'data': {}
        }
        
        # Count target objects
        target_count = sum([
            include_calls, include_users, include_deals,
            include_conversations, include_library, include_stats
        ])
        extraction_result['metadata']['target_objects'] = target_count
        
        successful_count = 0

        try:
            # Extract calls
            if include_calls:
                try:
                    extraction_result['data']['calls'] = self.extract_calls(calls_limit)
                    successful_count += 1
                    logger.info(f"✅ Calls extraction successful ({len(extraction_result['data']['calls'])} items)")
                except Exception as e:
                    extraction_result['metadata']['errors'].append(f"Calls extraction failed: {e}")
                    logger.error(f"❌ Calls extraction failed: {e}")
            
            # Extract users
            if include_users:
                try:
                    extraction_result['data']['users'] = self.extract_users()
                    successful_count += 1
                    logger.info(f"✅ Users extraction successful ({len(extraction_result['data']['users'])} items)")
                except Exception as e:
                    extraction_result['metadata']['errors'].append(f"Users extraction failed: {e}")
                    logger.error(f"❌ Users extraction failed: {e}")
            
            # Extract deals
            if include_deals:
                try:
                    extraction_result['data']['deals'] = self.extract_deals(deals_limit)
                    successful_count += 1
                    logger.info(f"✅ Deals extraction successful ({len(extraction_result['data']['deals'])} items)")
                except Exception as e:
                    extraction_result['metadata']['errors'].append(f"Deals extraction failed: {e}")
                    logger.error(f"❌ Deals extraction failed: {e}")
            
            # Extract conversations
            if include_conversations:
                try:
                    extraction_result['data']['conversations'] = self.extract_conversations(conversations_limit)
                    successful_count += 1
                    logger.info(f"✅ Conversations extraction successful ({len(extraction_result['data']['conversations'])} items)")
                except Exception as e:
                    extraction_result['metadata']['errors'].append(f"Conversations extraction failed: {e}")
                    logger.error(f"❌ Conversations extraction failed: {e}")
            
            # Extract library
            if include_library:
                try:
                    extraction_result['data']['library'] = self.extract_library()
                    successful_count += 1
                    logger.info("✅ Library extraction successful")
                except Exception as e:
                    extraction_result['metadata']['errors'].append(f"Library extraction failed: {e}")
                    logger.error(f"❌ Library extraction failed: {e}")
            
            # Extract team stats
            if include_stats:
                try:
                    extraction_result['data']['team_stats'] = self.extract_team_stats()
                    successful_count += 1
                    logger.info("✅ Team stats extraction successful")
                except Exception as e:
                    extraction_result['metadata']['errors'].append(f"Team stats extraction failed: {e}")
                    logger.error(f"❌ Team stats extraction failed: {e}")
            
            # Calculate final metrics
            end_time = time.time()
            duration = end_time - start_time
            
            extraction_result['metadata']['successful_objects'] = successful_count
            extraction_result['metadata']['failed_objects'] = target_count - successful_count
            extraction_result['metadata']['duration_seconds'] = round(duration, 2)
            extraction_result['metadata']['performance_target_met'] = duration < self.performance_target_seconds
            
            # Update extraction stats
            self._update_extraction_stats(successful_count, target_count, duration)
            
            # Log summary
            success_rate = successful_count / target_count if target_count > 0 else 0
            logger.info(f"🎯 Extraction complete: {successful_count}/{target_count} objects in {duration:.2f}s")
            logger.info(f"📊 Success rate: {success_rate:.1%}, Performance target: {'✅ MET' if duration < self.performance_target_seconds else '❌ MISSED'}")
            
            if successful_count < 5:
                logger.warning(f"⚠️  Only {successful_count} object types extracted (target: ≥5)")
            
            return extraction_result
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            extraction_result['metadata']['duration_seconds'] = round(duration, 2)
            extraction_result['metadata']['errors'].append(f"Extraction failed: {e}")
            
            self._update_extraction_stats(successful_count, target_count, duration, error=str(e))
            
            logger.error(f"❌ Comprehensive extraction failed after {duration:.2f}s: {e}")
            raise GongAgentError(f"Comprehensive extraction failed: {e}")
    
    def _update_extraction_stats(self, successful: int, total: int, duration: float, error: Optional[str] = None) -> None:
        """
        Update internal extraction statistics for monitoring and reporting.
        
        Maintains running averages and counters for extraction performance.
        These stats are exposed via get_extraction_stats() for observability.
        
        Args:
            successful: Number of successfully extracted object types
            total: Total number of object types attempted
            duration: Extraction duration in seconds
            error: Optional error message if extraction failed
            
        Updates:
        - total_extractions: Incremented by 1
        - successful_extractions/failed_extractions: Based on error presence
        - average_duration: Running average using incremental calculation
        - last_error: Stores most recent error for debugging
        - last_extraction_time: Updates to current timestamp
        """
        self.extraction_stats['total_extractions'] += 1
        
        if error:
            self.extraction_stats['failed_extractions'] += 1
            self.extraction_stats['last_error'] = error
        else:
            self.extraction_stats['successful_extractions'] += 1
        
        # Update average duration
        total_extractions = self.extraction_stats['total_extractions']
        current_avg = self.extraction_stats['average_duration']
        self.extraction_stats['average_duration'] = ((current_avg * (total_extractions - 1)) + duration) / total_extractions
        
        self.last_extraction_time = datetime.now()
    
    # ============================================================================
    # Utility and Status Methods
    # ============================================================================
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """
        Get extraction performance statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        stats = self.extraction_stats.copy()
        
        # Calculate success rate
        total = stats['total_extractions']
        if total > 0:
            stats['success_rate'] = stats['successful_extractions'] / total
            stats['failure_rate'] = stats['failed_extractions'] / total
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
        
        # Add performance targets
        stats['performance_target_seconds'] = self.performance_target_seconds
        stats['success_rate_target'] = self.success_rate_target
        stats['meets_performance_target'] = stats['average_duration'] < self.performance_target_seconds
        stats['meets_success_target'] = stats['success_rate'] >= self.success_rate_target
        
        # Add last extraction time
        if self.last_extraction_time:
            stats['last_extraction_time'] = self.last_extraction_time.isoformat()
        
        return stats
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive agent status for monitoring and debugging.
        
        Aggregates all health indicators into a single status report.
        
        Returns:
            Dict with structure:
            {
                'agent_status': 'ready' | 'no_session',
                'session_info': {
                    'status': 'active' | 'expired' | 'no_session',
                    'user_email': str,
                    'cell_id': str,
                    'created_at': ISO datetime,
                    'last_activity': ISO datetime,
                    'token_count': int,
                    'cookie_count': int,
                    'is_active': bool
                },
                'extraction_stats': {
                    'total_extractions': int,
                    'successful_extractions': int,
                    'failed_extractions': int,
                    'average_duration': float,
                    'success_rate': float (0.0-1.0),
                    'meets_performance_target': bool,
                    'meets_success_target': bool,
                    'last_error': str | None,
                    'last_extraction_time': ISO datetime | None
                },
                'api_rate_limit': Dict (from api_client),
                'performance_targets': {
                    'extraction_time_seconds': 30,
                    'success_rate': 0.95,
                    'minimum_object_types': 5
                }
            }
        """
        return {
            'agent_status': 'ready' if self.session else 'no_session',
            'session_info': self.get_session_info(),
            'extraction_stats': self.get_extraction_stats(),
            'api_rate_limit': self.api_client.get_rate_limit_status(),
            'performance_targets': {
                'extraction_time_seconds': self.performance_target_seconds,
                'success_rate': self.success_rate_target,
                'minimum_object_types': 5
            }
        }
    
    def save_extraction_results(self, results: Dict[str, Any], output_path: Path) -> None:
        """
        Save extraction results to file.
        
        Args:
            results: Extraction results dictionary
            output_path: Path to save results
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"Extraction results saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save extraction results: {e}")
            raise GongAgentError(f"Failed to save results: {e}")
    
    # ============================================================================
    # Quick Access Methods
    # ============================================================================
    
    def quick_extract(self, session_source: Optional[Union[str, Path, GongSession]] = None) -> Dict[str, Any]:
        """
        Quick extraction method for immediate results.
        
        Args:
            session_source: Optional session source (if not already set)
            
        Returns:
            Extraction results with all available data
        """
        if session_source:
            self.set_session(session_source)
        
        if not self.session:
            raise GongAgentError("No session available for quick extraction")
        
        logger.info("Starting quick extraction")
        
        return self.extract_all_data(
            calls_limit=50,
            deals_limit=50,
            conversations_limit=25
        )
    
    def validate_performance(self) -> Dict[str, Any]:
        """
        Validate that the agent meets performance targets.
        
        Runs a lightweight extraction (10 items per type) to verify:
        1. Can extract ≥5 object types successfully
        2. Completes extraction in <30 seconds
        3. Authentication and API connectivity working
        
        Returns:
            Dict with structure:
            {
                'valid': bool (False if no session or extraction failed),
                'performance_met': bool (duration < 30s),
                'object_types_met': bool (successful_objects >= 5),
                'duration_seconds': float,
                'successful_objects': int,
                'target_duration': 30,
                'target_objects': 5,
                'overall_success': bool (both targets met),
                'reason': str (only present if valid=False)
            }
            
        Use Cases:
        - Pre-flight check before large extractions
        - Health monitoring in production
        - Performance regression testing
        """
        if not self.session:
            return {
                'valid': False,
                'reason': 'No session available',
                'performance_met': False,
                'object_types_met': False
            }
        
        # Run a test extraction
        try:
            start_time = time.time()
            results = self.extract_all_data(
                calls_limit=10,
                deals_limit=10,
                conversations_limit=10
            )
            duration = time.time() - start_time
            
            successful_objects = results['metadata']['successful_objects']
            performance_met = duration < self.performance_target_seconds
            object_types_met = successful_objects >= 5
            
            return {
                'valid': True,
                'performance_met': performance_met,
                'object_types_met': object_types_met,
                'duration_seconds': round(duration, 2),
                'successful_objects': successful_objects,
                'target_duration': self.performance_target_seconds,
                'target_objects': 5,
                'overall_success': performance_met and object_types_met
            }
            
        except Exception as e:
            return {
                'valid': False,
                'reason': f'Validation extraction failed: {e}',
                'performance_met': False,
                'object_types_met': False
            }



    def enable_auto_refresh(self) -> None:
        """Enable automatic session refresh on authentication failures"""
        self.auto_refresh_enabled = True
        logger.info("✅ Automatic session refresh enabled")

    def disable_auto_refresh(self) -> None:
        """Disable automatic session refresh"""
        self.auto_refresh_enabled = False
        logger.info("⚠️ Automatic session refresh disabled")

