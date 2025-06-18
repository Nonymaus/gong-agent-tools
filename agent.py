"""
Gong Agent - Main Interface

High-level interface for Gong data extraction that orchestrates authentication
and data extraction. Provides simple methods for extracting all major Gong objects.

Performance target: Extract ≥5 object types in <30 seconds.
Success rate target: >95% reliability.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

# Import components
import sys
sys.path.insert(0, str(Path(__file__).parent))
from authentication import GongAuthenticationManager, GongAuthenticationError
from authentication.session_extractor import GongSessionManager
from api_client import GongAPIClient, GongAPIError
from data_models import (
    GongSession, GongCall, GongUser, GongContact, GongAccount,
    GongDeal, GongActivity, GongCallMetrics, GongAPIResponse
)

logger = logging.getLogger(__name__)


class GongAgentError(Exception):
    """Raised when Gong agent operation fails"""
    pass


class GongAgent:
    """
    Main Gong agent interface for data extraction.
    
    Orchestrates authentication and data extraction with a simple, high-level API.
    Designed for reliability and performance with comprehensive error handling.
    """
    
    def __init__(self, session_source: Optional[Union[str, Path, GongSession]] = None):
        """
        Initialize the Gong agent.
        
        Args:
            session_source: Optional session source:
                - Path to HAR file
                - Path to analysis JSON file  
                - GongSession object
                - None (must call set_session later)
        """
        self.auth_manager = GongAuthenticationManager()
        self.session_manager = GongSessionManager()
        self.api_client = GongAPIClient(self.auth_manager)
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
        
        logger.info("Gong agent initialized")
        
        # Set session if provided
        if session_source:
            self.set_session(session_source)
    
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
            "status": "active" if self.auth_manager.is_session_valid(self.session) else "expired",
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

        Args:
            operation_func: Function to execute
            operation_name: Name of the operation for logging
            max_retries: Maximum number of retries (default: 1)

        Returns:
            Result of the operation

        Raises:
            GongAgentError: If operation fails after retries
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

                                # Use session manager to get fresh session (synchronous wrapper)
                                fresh_session_data = self._refresh_session_sync()

                                if fresh_session_data:
                                    # Convert session data to GongSession object
                                    refreshed_session = self.auth_manager.extract_session_from_analysis_data({
                                        'artifacts': self._convert_session_data_to_artifacts(fresh_session_data)
                                    })

                                    self.session = refreshed_session
                                    self.api_client.set_session(refreshed_session)
                                    logger.info(f"Fresh session captured for {operation_name}, retrying...")
                                    continue
                                else:
                                    logger.error(f"Fresh session capture failed for {operation_name}")
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
        Extract all available data from Gong.
        
        Args:
            include_calls: Whether to extract calls
            include_users: Whether to extract users
            include_deals: Whether to extract deals
            include_conversations: Whether to extract conversations
            include_library: Whether to extract library
            include_stats: Whether to extract team stats
            calls_limit: Maximum calls to extract
            deals_limit: Maximum deals to extract
            conversations_limit: Maximum conversations to extract
            
        Returns:
            Dictionary with all extracted data and metadata
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
            # Initialize duration tracking
            extraction_result['metadata']['duration_seconds'] = 0
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
        """Update internal extraction statistics"""
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
        Get comprehensive agent status.
        
        Returns:
            Dictionary with agent status information
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
        
        Returns:
            Validation results dictionary
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