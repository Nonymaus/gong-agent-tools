"""
Module: client
Type: Internal Module

Purpose:
Gong API client implementation for making authenticated requests to Gong services.

Data Flow:
- Input: HTTP requests, Configuration parameters, Authentication credentials
- Processing: Data extraction, API interaction
- Output: List of extracted data, Dictionary responses, Error states and exceptions

Critical Because:
Central integration point for Gong - without this, no Gong data can be accessed.

Dependencies:
- Requires: logging, requests, requests.adapters, urllib3.util.retry, authentication, data_models
- Used By: app_backend.ingestion.orchestrator, app_backend.api_bridge.server

Author: Julia Evans
Date: 2025-06-20
"""
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import authentication and data models
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from authentication import GongAuthenticationManager, GongAuthenticationError
from data_models import (
    GongSession, GongCall, GongUser, GongContact, GongAccount, 
    GongDeal, GongActivity, GongEmailActivity, GongCallMetrics,
    GongAPIResponse, GongPaginatedResponse
)

logger = logging.getLogger(__name__)


class GongAPIError(Exception):
    """Raised when Gong API request fails"""
    pass


class GongRateLimitError(Exception):
    """Raised when Gong API rate limit is exceeded"""
    pass


class GongAPIClient:
    """
    Gong API client for data extraction using session tokens.
    
    Provides methods for extracting data from all major Gong endpoints
    with proper error handling, rate limiting, and session management.
    """
    
    def __init__(self, auth_manager: Optional[GongAuthenticationManager] = None):
        """
        Initialize the Gong API client.
        
        Args:
            auth_manager: Authentication manager instance
        """
        self.auth_manager = auth_manager or GongAuthenticationManager()
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        self.rate_limit_remaining = 1000
        self.rate_limit_reset = datetime.now()
        
        # Request timeout
        self.timeout = 30

        # Session-related properties (set when session is provided)
        self.base_url = None
        self.user_email = None
        self.cell_id = None
        self.workspace_id = None

        logger.info("Gong API client initialized")
    
    def set_session(self, session: GongSession) -> None:
        """Set the session for API requests"""
        if not self.auth_manager.is_session_valid(session):
            raise GongAuthenticationError("Invalid session provided")

        self.auth_manager.current_session = session

        # Set base URL and other properties from session
        self.base_url = self.auth_manager.get_base_url(session)
        self.user_email = session.user_email
        self.cell_id = session.cell_id
        self.workspace_id = getattr(session, 'workspace_id', None)

        logger.info(f"Session set for user: {session.user_email}")
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Gong API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            data: Form data
            json_data: JSON data
            
        Returns:
            Response data as dictionary
            
        Raises:
            GongAPIError: If request fails
            GongRateLimitError: If rate limited
        """
        # Rate limiting
        self._handle_rate_limiting()
        
        # Get session and headers
        session = self.auth_manager.get_current_session()
        if not session:
            raise GongAuthenticationError("No active session")
        
        headers = self.auth_manager.get_session_headers(session)
        base_url = self.auth_manager.get_base_url(session)
        
        # Build full URL
        if endpoint.startswith('http'):
            url = endpoint
        else:
            url = f"{base_url}{endpoint}"
        
        # Add JSON content type if sending JSON
        if json_data:
            headers['Content-Type'] = 'application/json'
        
        try:
            logger.debug(f"Making {method} request to {url}")
            
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json_data,
                timeout=self.timeout
            )
            
            # Update rate limiting info
            self._update_rate_limit_info(response)
            
            # Handle response
            if response.status_code == 429:
                raise GongRateLimitError("Rate limit exceeded")
            
            if response.status_code == 401:
                raise GongAuthenticationError("Authentication failed - session may be expired")
            
            if not response.ok:
                raise GongAPIError(f"API request failed: {response.status_code} - {response.text}")
            
            # Parse JSON response
            try:
                return response.json()
            except json.JSONDecodeError:
                # Some endpoints return non-JSON responses
                return {"text": response.text, "status_code": response.status_code}
                
        except requests.exceptions.RequestException as e:
            raise GongAPIError(f"Request failed: {e}")
    
    def _handle_rate_limiting(self) -> None:
        """Handle rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _update_rate_limit_info(self, response: requests.Response) -> None:
        """Update rate limiting information from response headers"""
        if 'X-RateLimit-Remaining' in response.headers:
            self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
        
        if 'X-RateLimit-Reset' in response.headers:
            reset_timestamp = int(response.headers['X-RateLimit-Reset'])
            self.rate_limit_reset = datetime.fromtimestamp(reset_timestamp)
    
    # ============================================================================
    # Core Data Extraction Methods
    # ============================================================================
    
    def get_my_calls(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get user's calls from Gong.
        
        Args:
            limit: Maximum number of calls to return
            offset: Offset for pagination
            
        Returns:
            List of call data dictionaries
        """
        logger.info(f"Fetching my calls (limit={limit}, offset={offset})")
        
        params = {
            'limit': limit,
            'offset': offset
        }
        
        response = self._make_request('GET', '/ajax/home/calls/my-calls', params=params)
        
        # Extract calls from response
        calls = response.get('calls', [])
        logger.info(f"Retrieved {len(calls)} calls")
        
        return calls
    
    def get_call_details(self, call_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific call.
        
        Args:
            call_id: Unique call identifier
            
        Returns:
            Call details dictionary
        """
        logger.info(f"Fetching call details for {call_id}")
        
        response = self._make_request('GET', f'/call/{call_id}')
        return response
    
    def get_call_transcript(self, call_id: str) -> Dict[str, Any]:
        """
        Get transcript for a specific call.
        
        Args:
            call_id: Unique call identifier
            
        Returns:
            Transcript data dictionary
        """
        logger.info(f"Fetching transcript for call {call_id}")
        
        response = self._make_request('GET', f'/call/{call_id}/detailed-transcript')
        return response
    
    def search_calls(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search for calls using query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching calls
        """
        logger.info(f"Searching calls with query: {query}")
        
        data = {
            'query': query,
            'limit': limit
        }
        
        response = self._make_request('POST', '/json/call/search', json_data=data)
        
        calls = response.get('results', [])
        logger.info(f"Found {len(calls)} matching calls")
        
        return calls
    
    def get_account_details(self, account_id: str) -> Dict[str, Any]:
        """
        Get detailed information about an account.
        
        Args:
            account_id: Unique account identifier
            
        Returns:
            Account details dictionary
        """
        logger.info(f"Fetching account details for {account_id}")
        
        response = self._make_request('GET', f'/account/{account_id}')
        return response
    
    def get_account_people(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Get people associated with an account.
        
        Args:
            account_id: Unique account identifier
            
        Returns:
            List of people data
        """
        logger.info(f"Fetching people for account {account_id}")
        
        response = self._make_request('GET', f'/ajax/account/{account_id}/people')
        
        people = response.get('people', [])
        logger.info(f"Retrieved {len(people)} people for account")
        
        return people
    
    def get_account_opportunities(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Get opportunities associated with an account.
        
        Args:
            account_id: Unique account identifier
            
        Returns:
            List of opportunity data
        """
        logger.info(f"Fetching opportunities for account {account_id}")
        
        response = self._make_request('GET', f'/ajax/account/{account_id}/opportunities')
        
        opportunities = response.get('opportunities', [])
        logger.info(f"Retrieved {len(opportunities)} opportunities for account")
        
        return opportunities
    
    def get_contact_details(self, contact_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a contact.
        
        Args:
            contact_id: Unique contact identifier
            
        Returns:
            Contact details dictionary
        """
        logger.info(f"Fetching contact details for {contact_id}")
        
        response = self._make_request('GET', '/ajax/contacts/get-single-contact-details', 
                                    params={'contact_id': contact_id})
        return response
    
    def get_contact_engagements(self, contact_id: str) -> List[Dict[str, Any]]:
        """
        Get engagements for a contact.
        
        Args:
            contact_id: Unique contact identifier
            
        Returns:
            List of engagement data
        """
        logger.info(f"Fetching engagements for contact {contact_id}")
        
        response = self._make_request('GET', '/ajax/contacts/get-engagements',
                                    params={'contact_id': contact_id})
        
        engagements = response.get('engagements', [])
        logger.info(f"Retrieved {len(engagements)} engagements for contact")
        
        return engagements
    
    def get_deals(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get deals from Gong.
        
        Args:
            limit: Maximum number of deals to return
            offset: Offset for pagination
            
        Returns:
            List of deal data
        """
        logger.info(f"Fetching deals (limit={limit}, offset={offset})")
        
        data = {
            'limit': limit,
            'offset': offset
        }
        
        response = self._make_request('POST', '/dealswebapi/ajax/deals/get-board-deals', 
                                    json_data=data)
        
        deals = response.get('deals', [])
        logger.info(f"Retrieved {len(deals)} deals")
        
        return deals
    
    def get_users(self) -> List[Dict[str, Any]]:
        """
        Get users from Gong.
        
        Returns:
            List of user data
        """
        logger.info("Fetching users")
        
        response = self._make_request('GET', '/ajax/stats/get-users')
        
        users = response.get('users', [])
        logger.info(f"Retrieved {len(users)} users")
        
        return users
    
    def get_day_activities(self, account_id: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get day activities for an account.
        
        Args:
            account_id: Unique account identifier
            date: Date in YYYY-MM-DD format (defaults to today)
            
        Returns:
            List of activity data
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Fetching day activities for account {account_id} on {date}")
        
        params = {
            'account_id': account_id,
            'date': date
        }
        
        response = self._make_request('GET', '/ajax/account/day-activities', params=params)
        
        activities = response.get('activities', [])
        logger.info(f"Retrieved {len(activities)} activities")
        
        return activities
    
    def get_conversations(self, filters: Optional[Dict] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get conversations with optional filters.
        
        Args:
            filters: Optional filters for conversations
            limit: Maximum number of conversations
            
        Returns:
            List of conversation data
        """
        logger.info(f"Fetching conversations (limit={limit})")
        
        data = {
            'filters': filters or {},
            'limit': limit
        }
        
        response = self._make_request('POST', '/conversations/ajax/results', json_data=data)
        
        conversations = response.get('conversations', [])
        logger.info(f"Retrieved {len(conversations)} conversations")
        
        return conversations
    
    def get_library_data(self, folder_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get library data from Gong.
        
        Args:
            folder_id: Optional folder ID to filter by
            
        Returns:
            Library data dictionary
        """
        logger.info(f"Fetching library data (folder_id={folder_id})")
        
        params = {}
        if folder_id:
            params['folder_id'] = folder_id
        
        response = self._make_request('GET', '/library/get-library-data', params=params)
        return response
    
    # ============================================================================
    # Analytics and Statistics Methods
    # ============================================================================
    
    def get_team_stats(self, metric: str, period: str = 'week') -> Dict[str, Any]:
        """
        Get team statistics for a specific metric.
        
        Args:
            metric: Metric name (e.g., 'avgCallDuration', 'totalCalls')
            period: Time period ('week', 'month', 'quarter')
            
        Returns:
            Statistics data dictionary
        """
        logger.info(f"Fetching team stats for {metric} ({period})")
        
        data = {
            'metric': metric,
            'period': period
        }
        
        response = self._make_request('POST', f'/stats/ajax/v2/team/activity/aggregated/{metric}',
                                    json_data=data)
        return response
    
    def get_user_stats(self, metric: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get user statistics for a specific metric.
        
        Args:
            metric: Metric name
            user_id: Optional user ID (defaults to current user)
            
        Returns:
            User statistics data
        """
        logger.info(f"Fetching user stats for {metric} (user_id={user_id})")
        
        data = {
            'metric': metric
        }
        if user_id:
            data['user_id'] = user_id
        
        response = self._make_request('POST', f'/stats/ajax/v2/team/activity/users/{metric}',
                                    json_data=data)
        return response
    
    # ============================================================================
    # Utility Methods
    # ============================================================================
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get comprehensive connection status information.

        Returns:
            Dictionary with connection status, base URL, workspace ID, and diagnostics
        """
        import time

        start_time = time.time()
        status = {
            'connected': False,
            'base_url': None,
            'workspace_id': None,
            'user_email': None,
            'cell_id': None,
            'response_time_ms': 0,
            'error_message': None,
            'last_tested': datetime.now().isoformat()
        }

        try:
            logger.info("Testing API connection status")

            # Get basic connection info
            current_session = self.auth_manager.get_current_session()
            if current_session:
                status['base_url'] = self.base_url
                status['user_email'] = current_session.user_email
                status['cell_id'] = current_session.cell_id
                status['workspace_id'] = getattr(current_session, 'workspace_id', None)

            # Test lightweight API endpoint
            response = self._make_request('GET', '/ajax/common/rtkn')

            # Calculate response time
            response_time = (time.time() - start_time) * 1000
            status['response_time_ms'] = round(response_time, 2)
            status['connected'] = True

            logger.info(f"API connection status check successful ({status['response_time_ms']}ms)")

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            status['response_time_ms'] = round(response_time, 2)
            status['error_message'] = str(e)
            logger.error(f"API connection status check failed: {e}")

        return status

    def test_connection(self) -> Dict[str, Any]:
        """
        Test the API connection and authentication.

        Returns:
            Dictionary with connection status and diagnostic information
            Maintains backward compatibility with 'connected' key
        """
        try:
            logger.info("Testing API connection")

            # Get comprehensive status
            status = self.get_connection_status()

            if status['connected']:
                logger.info("API connection test successful")
            else:
                logger.error(f"API connection test failed: {status.get('error_message', 'Unknown error')}")

            return status

        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return {
                'connected': False,
                'base_url': self.base_url if hasattr(self, 'base_url') else None,
                'workspace_id': None,
                'error_message': str(e),
                'last_tested': datetime.now().isoformat()
            }
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current rate limit status.
        
        Returns:
            Rate limit information
        """
        return {
            'remaining': self.rate_limit_remaining,
            'reset_time': self.rate_limit_reset.isoformat(),
            'seconds_until_reset': (self.rate_limit_reset - datetime.now()).total_seconds()
        }
    
    def extract_all_data(self, include_calls: bool = True, include_deals: bool = True,
                        include_contacts: bool = True, include_users: bool = True,
                        include_activities: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract all available data from Gong.
        
        Args:
            include_calls: Whether to include calls data
            include_deals: Whether to include deals data
            include_contacts: Whether to include contacts data
            include_users: Whether to include users data
            include_activities: Whether to include activities data
            
        Returns:
            Dictionary with all extracted data
        """
        logger.info("Starting comprehensive data extraction")
        
        extracted_data = {}
        
        try:
            if include_calls:
                logger.info("Extracting calls data...")
                extracted_data['calls'] = self.get_my_calls(limit=100)
            
            if include_deals:
                logger.info("Extracting deals data...")
                extracted_data['deals'] = self.get_deals(limit=100)
            
            if include_users:
                logger.info("Extracting users data...")
                extracted_data['users'] = self.get_users()
            
            if include_contacts:
                logger.info("Extracting contacts data...")
                # Note: Contacts require specific IDs, so this is a placeholder
                extracted_data['contacts'] = []
            
            if include_activities:
                logger.info("Extracting activities data...")
                # Note: Activities require account IDs, so this is a placeholder
                extracted_data['activities'] = []
            
            # Get library data
            logger.info("Extracting library data...")
            extracted_data['library'] = self.get_library_data()
            
            # Get conversations
            logger.info("Extracting conversations data...")
            extracted_data['conversations'] = self.get_conversations(limit=50)
            
            logger.info(f"Data extraction complete. Extracted {len(extracted_data)} data types")
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Data extraction failed: {e}")
            raise GongAPIError(f"Comprehensive data extraction failed: {e}")