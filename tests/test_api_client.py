"""
Unit tests for Gong API client.

Tests API client functionality including request handling, rate limiting,
error handling, and endpoint methods with comprehensive mock scenarios.
"""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import requests
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api_client import (
    GongAPIClient,
    GongAPIError,
    GongRateLimitError
)
from authentication import GongAuthenticationManager, GongAuthenticationError
from data_models import GongSession, GongAuthenticationToken, GongJWTPayload


class TestGongAPIClientInitialization:
    """Test GongAPIClient initialization"""
    
    def test_initialization_default(self):
        """Test default initialization"""
        client = GongAPIClient()
        
        assert client.auth_manager is not None
        assert client.session is not None
        assert client.timeout == 30
        assert client.min_request_interval == 0.1
        assert client.rate_limit_remaining == 1000
    
    def test_initialization_with_auth_manager(self):
        """Test initialization with custom auth manager"""
        auth_manager = GongAuthenticationManager()
        client = GongAPIClient(auth_manager)
        
        assert client.auth_manager == auth_manager
    
    def test_retry_strategy_configuration(self):
        """Test retry strategy is properly configured"""
        client = GongAPIClient()
        
        # Check that adapters are mounted
        assert 'http://' in client.session.adapters
        assert 'https://' in client.session.adapters


class TestSessionManagement:
    """Test session management in API client"""
    
    def create_valid_session(self):
        """Create a valid session for testing"""
        jwt_payload = GongJWTPayload(
            gp="Okta",
            exp=int((datetime.now().timestamp() + 3600)),
            iat=int(datetime.now().timestamp()),
            jti="test_jti",
            gu="test@example.com",
            cell="us-14496"
        )
        
        auth_token = GongAuthenticationToken(
            token_type="last_login_jwt",
            raw_token="test_token",
            payload=jwt_payload,
            expires_at=datetime.fromtimestamp(jwt_payload.exp),
            issued_at=datetime.fromtimestamp(jwt_payload.iat),
            is_expired=False,
            cell_id="us-14496",
            user_email="test@example.com"
        )
        
        return GongSession(
            session_id="test_session",
            user_email="test@example.com",
            cell_id="us-14496",
            authentication_tokens=[auth_token],
            session_cookies={"g-session": "test_value"}
        )
    
    def test_set_session_valid(self):
        """Test setting valid session"""
        client = GongAPIClient()
        session = self.create_valid_session()
        
        with patch.object(client.auth_manager, 'is_session_valid', return_value=True):
            client.set_session(session)
            assert client.auth_manager.current_session == session
    
    def test_set_session_invalid(self):
        """Test setting invalid session"""
        client = GongAPIClient()
        session = self.create_valid_session()
        
        with patch.object(client.auth_manager, 'is_session_valid', return_value=False):
            with pytest.raises(GongAuthenticationError, match="Invalid session"):
                client.set_session(session)


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_rate_limiting_interval(self):
        """Test rate limiting interval enforcement"""
        client = GongAPIClient()

        # Mock time to control timing
        with patch('time.time') as mock_time:
            # Both calls will need sleep because they're too close together
            mock_time.side_effect = [0, 0, 0.05, 0.05]

            with patch('time.sleep') as mock_sleep:
                client._handle_rate_limiting()
                client._handle_rate_limiting()

                # Should have slept twice since both calls are within the interval
                assert mock_sleep.call_count == 2
    
    def test_rate_limit_status(self):
        """Test rate limit status reporting"""
        client = GongAPIClient()
        
        status = client.get_rate_limit_status()
        
        assert 'remaining' in status
        assert 'reset_time' in status
        assert 'seconds_until_reset' in status
        assert isinstance(status['remaining'], int)
    
    def test_update_rate_limit_info(self):
        """Test updating rate limit info from response headers"""
        client = GongAPIClient()
        
        # Mock response with rate limit headers
        mock_response = Mock()
        mock_response.headers = {
            'X-RateLimit-Remaining': '500',
            'X-RateLimit-Reset': str(int(datetime.now().timestamp()) + 3600)
        }
        
        client._update_rate_limit_info(mock_response)
        
        assert client.rate_limit_remaining == 500


class TestRequestHandling:
    """Test HTTP request handling"""
    
    def create_mock_session_and_client(self):
        """Create mock session and client for testing"""
        client = GongAPIClient()
        session = Mock()
        session.user_email = "test@example.com"
        session.cell_id = "us-14496"
        
        # Mock auth manager methods
        client.auth_manager.get_current_session = Mock(return_value=session)
        client.auth_manager.get_session_headers = Mock(return_value={
            'Cookie': 'test=value',
            'User-Agent': 'test-agent'
        })
        client.auth_manager.get_base_url = Mock(return_value="https://us-14496.app.gong.io")
        
        return client, session
    
    @patch('requests.Session.request')
    def test_make_request_success(self, mock_request):
        """Test successful API request"""
        client, session = self.create_mock_session_and_client()
        
        # Mock successful response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {"success": True, "data": []}
        mock_request.return_value = mock_response
        
        result = client._make_request('GET', '/test/endpoint')
        
        assert result == {"success": True, "data": []}
        mock_request.assert_called_once()
    
    @patch('requests.Session.request')
    def test_make_request_rate_limit_error(self, mock_request):
        """Test rate limit error handling"""
        client, session = self.create_mock_session_and_client()
        
        # Mock rate limit response
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 429
        mock_response.headers = {}
        mock_request.return_value = mock_response
        
        with pytest.raises(GongRateLimitError, match="Rate limit exceeded"):
            client._make_request('GET', '/test/endpoint')
    
    @patch('requests.Session.request')
    def test_make_request_auth_error(self, mock_request):
        """Test authentication error handling"""
        client, session = self.create_mock_session_and_client()
        
        # Mock auth error response
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.headers = {}
        mock_request.return_value = mock_response
        
        with pytest.raises(GongAuthenticationError, match="Authentication failed"):
            client._make_request('GET', '/test/endpoint')
    
    @patch('requests.Session.request')
    def test_make_request_api_error(self, mock_request):
        """Test general API error handling"""
        client, session = self.create_mock_session_and_client()
        
        # Mock API error response
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.headers = {}
        mock_request.return_value = mock_response
        
        with pytest.raises(GongAPIError, match="API request failed: 500"):
            client._make_request('GET', '/test/endpoint')
    
    def test_make_request_no_session(self):
        """Test request without active session"""
        client = GongAPIClient()
        client.auth_manager.get_current_session = Mock(return_value=None)
        
        with pytest.raises(GongAuthenticationError, match="No active session"):
            client._make_request('GET', '/test/endpoint')
    
    @patch('requests.Session.request')
    def test_make_request_json_decode_error(self, mock_request):
        """Test handling of non-JSON responses"""
        client, session = self.create_mock_session_and_client()
        
        # Mock response with non-JSON content
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.headers = {}
        import json
        mock_response.json.side_effect = json.JSONDecodeError("No JSON object could be decoded", "", 0)
        mock_response.text = "Plain text response"
        mock_request.return_value = mock_response
        
        result = client._make_request('GET', '/test/endpoint')
        
        assert result == {"text": "Plain text response", "status_code": 200}


class TestEndpointMethods:
    """Test individual endpoint methods"""
    
    def setup_method(self):
        """Setup for endpoint tests"""
        self.client = GongAPIClient()
        self.session = Mock()
        self.session.user_email = "test@example.com"
        self.session.cell_id = "us-14496"
        
        # Mock auth manager
        self.client.auth_manager.get_current_session = Mock(return_value=self.session)
        self.client.auth_manager.get_session_headers = Mock(return_value={'Cookie': 'test=value'})
        self.client.auth_manager.get_base_url = Mock(return_value="https://us-14496.app.gong.io")
    
    @patch.object(GongAPIClient, '_make_request')
    def test_get_my_calls(self, mock_request):
        """Test get_my_calls method"""
        mock_request.return_value = {
            'calls': [
                {'id': '1', 'title': 'Test Call 1'},
                {'id': '2', 'title': 'Test Call 2'}
            ]
        }
        
        calls = self.client.get_my_calls(limit=10, offset=0)
        
        assert len(calls) == 2
        assert calls[0]['id'] == '1'
        mock_request.assert_called_once_with('GET', '/ajax/home/calls/my-calls', params={'limit': 10, 'offset': 0})
    
    @patch.object(GongAPIClient, '_make_request')
    def test_get_call_details(self, mock_request):
        """Test get_call_details method"""
        mock_request.return_value = {'id': 'call_123', 'title': 'Test Call'}
        
        call = self.client.get_call_details('call_123')
        
        assert call['id'] == 'call_123'
        mock_request.assert_called_once_with('GET', '/call/call_123')
    
    @patch.object(GongAPIClient, '_make_request')
    def test_search_calls(self, mock_request):
        """Test search_calls method"""
        mock_request.return_value = {
            'results': [
                {'id': '1', 'title': 'Matching Call'}
            ]
        }
        
        calls = self.client.search_calls('test query', limit=25)
        
        assert len(calls) == 1
        assert calls[0]['title'] == 'Matching Call'
        mock_request.assert_called_once_with('POST', '/json/call/search', json_data={'query': 'test query', 'limit': 25})
    
    @patch.object(GongAPIClient, '_make_request')
    def test_get_users(self, mock_request):
        """Test get_users method"""
        mock_request.return_value = {
            'users': [
                {'id': '1', 'name': 'User 1'},
                {'id': '2', 'name': 'User 2'}
            ]
        }
        
        users = self.client.get_users()
        
        assert len(users) == 2
        mock_request.assert_called_once_with('GET', '/ajax/stats/get-users')
    
    @patch.object(GongAPIClient, '_make_request')
    def test_get_deals(self, mock_request):
        """Test get_deals method"""
        mock_request.return_value = {
            'deals': [
                {'id': '1', 'name': 'Deal 1'},
                {'id': '2', 'name': 'Deal 2'}
            ]
        }
        
        deals = self.client.get_deals(limit=50, offset=0)
        
        assert len(deals) == 2
        mock_request.assert_called_once_with('POST', '/dealswebapi/ajax/deals/get-board-deals', 
                                           json_data={'limit': 50, 'offset': 0})
    
    @patch.object(GongAPIClient, '_make_request')
    def test_get_conversations(self, mock_request):
        """Test get_conversations method"""
        mock_request.return_value = {
            'conversations': [
                {'id': '1', 'title': 'Conversation 1'}
            ]
        }
        
        conversations = self.client.get_conversations(limit=25)
        
        assert len(conversations) == 1
        mock_request.assert_called_once_with('POST', '/conversations/ajax/results', 
                                           json_data={'filters': {}, 'limit': 25})
    
    @patch.object(GongAPIClient, '_make_request')
    def test_get_library_data(self, mock_request):
        """Test get_library_data method"""
        mock_request.return_value = {'folders': [], 'items': []}
        
        library = self.client.get_library_data()
        
        assert 'folders' in library
        mock_request.assert_called_once_with('GET', '/library/get-library-data', params={})
    
    @patch.object(GongAPIClient, '_make_request')
    def test_get_team_stats(self, mock_request):
        """Test get_team_stats method"""
        mock_request.return_value = {'metric': 'avgCallDuration', 'value': 1800}
        
        stats = self.client.get_team_stats('avgCallDuration', 'week')
        
        assert stats['metric'] == 'avgCallDuration'
        mock_request.assert_called_once_with('POST', '/stats/ajax/v2/team/activity/aggregated/avgCallDuration',
                                           json_data={'metric': 'avgCallDuration', 'period': 'week'})


class TestConnectionTesting:
    """Test connection testing functionality"""
    
    @patch.object(GongAPIClient, '_make_request')
    def test_test_connection_success(self, mock_request):
        """Test successful connection test"""
        client = GongAPIClient()
        mock_request.return_value = {'success': True}

        result = client.test_connection()

        assert isinstance(result, dict)
        assert result['connected'] is True
        mock_request.assert_called_once_with('GET', '/ajax/common/rtkn')
    
    @patch.object(GongAPIClient, '_make_request')
    def test_test_connection_failure(self, mock_request):
        """Test failed connection test"""
        client = GongAPIClient()
        mock_request.side_effect = GongAPIError("Connection failed")

        result = client.test_connection()

        assert isinstance(result, dict)
        assert result['connected'] is False
        assert 'Connection failed' in result['error_message']


class TestComprehensiveExtraction:
    """Test comprehensive data extraction"""
    
    def setup_method(self):
        """Setup for extraction tests"""
        self.client = GongAPIClient()
        
        # Mock all individual methods
        self.client.get_my_calls = Mock(return_value=[{'id': '1'}])
        self.client.get_deals = Mock(return_value=[{'id': '2'}])
        self.client.get_users = Mock(return_value=[{'id': '3'}])
        self.client.get_conversations = Mock(return_value=[{'id': '4'}])
        self.client.get_library_data = Mock(return_value={'folders': []})
    
    def test_extract_all_data_success(self):
        """Test successful comprehensive extraction"""
        data = self.client.extract_all_data()
        
        assert 'calls' in data
        assert 'deals' in data
        assert 'users' in data
        assert 'conversations' in data
        assert 'library' in data
        
        # Verify methods were called
        self.client.get_my_calls.assert_called_once_with(limit=100)
        self.client.get_deals.assert_called_once_with(limit=100)
        self.client.get_users.assert_called_once()
        self.client.get_conversations.assert_called_once_with(limit=50)
        self.client.get_library_data.assert_called_once()
    
    def test_extract_all_data_selective(self):
        """Test selective data extraction"""
        data = self.client.extract_all_data(
            include_calls=True,
            include_deals=False,
            include_users=True,
            include_contacts=False,
            include_activities=False
        )
        
        assert 'calls' in data
        assert 'deals' not in data
        assert 'users' in data
        
        self.client.get_my_calls.assert_called_once()
        self.client.get_deals.assert_not_called()
        self.client.get_users.assert_called_once()
    
    def test_extract_all_data_with_error(self):
        """Test extraction with partial failures"""
        # Make one method fail
        self.client.get_deals.side_effect = GongAPIError("Deals API failed")
        
        with pytest.raises(GongAPIError, match="Comprehensive data extraction failed"):
            self.client.extract_all_data()


class TestErrorHandling:
    """Test comprehensive error handling"""
    
    def test_request_timeout(self):
        """Test request timeout handling"""
        client = GongAPIClient()
        
        with patch.object(client.session, 'request') as mock_request:
            mock_request.side_effect = requests.exceptions.Timeout("Request timed out")
            
            client.auth_manager.get_current_session = Mock(return_value=Mock())
            client.auth_manager.get_session_headers = Mock(return_value={})
            client.auth_manager.get_base_url = Mock(return_value="https://test.gong.io")
            
            with pytest.raises(GongAPIError, match="Request failed"):
                client._make_request('GET', '/test')
    
    def test_connection_error(self):
        """Test connection error handling"""
        client = GongAPIClient()
        
        with patch.object(client.session, 'request') as mock_request:
            mock_request.side_effect = requests.exceptions.ConnectionError("Connection failed")
            
            client.auth_manager.get_current_session = Mock(return_value=Mock())
            client.auth_manager.get_session_headers = Mock(return_value={})
            client.auth_manager.get_base_url = Mock(return_value="https://test.gong.io")
            
            with pytest.raises(GongAPIError, match="Request failed"):
                client._make_request('GET', '/test')


# Test fixtures
@pytest.fixture
def api_client():
    """API client fixture"""
    return GongAPIClient()


@pytest.fixture
def mock_session():
    """Mock session fixture"""
    session = Mock()
    session.user_email = "test@example.com"
    session.cell_id = "us-14496"
    return session


@pytest.fixture
def client_with_session(api_client, mock_session):
    """API client with mock session fixture"""
    api_client.auth_manager.get_current_session = Mock(return_value=mock_session)
    api_client.auth_manager.get_session_headers = Mock(return_value={'Cookie': 'test=value'})
    api_client.auth_manager.get_base_url = Mock(return_value="https://us-14496.app.gong.io")
    return api_client


if __name__ == "__main__":
    pytest.main([__file__, "-v"])