"""
Module: test_agent
Type: Test

Purpose:
Gong data extraction agent that implements the IServiceAdapter interface for unified platform integration.

Data Flow:
- Input: Configuration parameters, Authentication credentials
- Processing: Input validation, Data extraction, API interaction
- Output: List of extracted data, Dictionary responses, Error states and exceptions

Critical Because:
Central integration point for Gong - without this, no Gong data can be accessed.

Dependencies:
- Requires: pytest, tempfile, unittest.mock, agent, authentication, api_client, data_models
- Used By: app_backend.ingestion.orchestrator, app_backend.api_bridge.server

Author: Julia Evans
Date: 2025-06-20
"""
import pytest
import time
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import GongAgent, GongAgentError
from authentication import GongAuthenticationManager, GongAuthenticationError
from api_client import GongAPIClient, GongAPIError
from data_models import GongSession, GongAuthenticationToken, GongJWTPayload


class TestGongAgentInitialization:
    """Test GongAgent initialization"""
    
    def test_initialization_default(self):
        """Test default initialization"""
        agent = GongAgent()
        
        assert agent.auth_manager is not None
        assert agent.api_client is not None
        assert agent.session is None
        assert agent.performance_target_seconds == 30
        assert agent.success_rate_target == 0.95
        assert agent.extraction_stats['total_extractions'] == 0
    
    def test_initialization_with_session_object(self):
        """Test initialization with session object"""
        session = Mock(spec=GongSession)
        session.user_email = "test@example.com"
        session.cell_id = "us-14496"
        
        with patch.object(GongAgent, 'set_session') as mock_set_session:
            agent = GongAgent(session)
            mock_set_session.assert_called_once_with(session)
    
    def test_initialization_with_file_path(self):
        """Test initialization with file path"""
        with patch.object(GongAgent, 'set_session') as mock_set_session:
            agent = GongAgent("test_file.json")
            mock_set_session.assert_called_once_with("test_file.json")


class TestSessionManagement:
    """Test session management in agent"""
    
    def create_mock_session(self):
        """Create mock session for testing"""
        # Create a mock token that appears valid
        mock_token = Mock()
        mock_token.is_expired = False
        mock_token.token_type = "last_login_jwt"
        mock_token.user_email = "test@example.com"
        mock_token.cell_id = "us-14496"

        session = Mock(spec=GongSession)
        session.user_email = "test@example.com"
        session.cell_id = "us-14496"
        session.session_id = "test_session"
        session.created_at = datetime.now()
        session.last_activity = datetime.now()
        session.authentication_tokens = [mock_token]  # Add valid token
        session.session_cookies = {}
        session.is_active = True
        return session
    
    def test_set_session_with_object(self):
        """Test setting session with GongSession object"""
        agent = GongAgent()
        session = self.create_mock_session()
        
        agent.set_session(session)
        
        assert agent.session == session
        assert agent.auth_manager.current_session == session
    
    @patch('pathlib.Path.exists')
    @patch.object(GongAuthenticationManager, 'extract_session_from_har')
    def test_set_session_with_har_file(self, mock_extract_har, mock_exists):
        """Test setting session with HAR file"""
        mock_exists.return_value = True
        session = self.create_mock_session()
        mock_extract_har.return_value = session
        
        agent = GongAgent()
        agent.set_session("test_file.har")
        
        assert agent.session == session
        mock_extract_har.assert_called_once()
    
    @patch('pathlib.Path.exists')
    @patch.object(GongAuthenticationManager, 'extract_session_from_analysis')
    def test_set_session_with_json_file(self, mock_extract_json, mock_exists):
        """Test setting session with JSON analysis file"""
        mock_exists.return_value = True
        session = self.create_mock_session()
        mock_extract_json.return_value = session
        
        agent = GongAgent()
        agent.set_session("test_file.json")
        
        assert agent.session == session
        mock_extract_json.assert_called_once()
    
    def test_set_session_file_not_found(self):
        """Test setting session with non-existent file"""
        agent = GongAgent()
        
        with pytest.raises(GongAgentError, match="Session source file not found"):
            agent.set_session("non_existent_file.json")
    
    def test_set_session_unsupported_file_type(self):
        """Test setting session with unsupported file type"""
        agent = GongAgent()
        
        with tempfile.NamedTemporaryFile(suffix='.txt') as temp_file:
            with pytest.raises(GongAgentError, match="Unsupported session source file type"):
                agent.set_session(temp_file.name)
    
    def test_set_session_invalid_type(self):
        """Test setting session with invalid type"""
        agent = GongAgent()
        
        with pytest.raises(GongAgentError, match="Invalid session source type"):
            agent.set_session(123)  # Invalid type
    
    def test_get_session_info_no_session(self):
        """Test getting session info without session"""
        agent = GongAgent()
        
        info = agent.get_session_info()
        assert info["status"] == "no_session"
    
    def test_get_session_info_with_session(self):
        """Test getting session info with active session"""
        agent = GongAgent()
        session = self.create_mock_session()
        agent.session = session
        
        with patch.object(agent.auth_manager, 'is_session_valid', return_value=True):
            info = agent.get_session_info()
            
            assert info["status"] == "active"
            assert info["user_email"] == "test@example.com"
            assert info["cell_id"] == "us-14496"


class TestConnectionTesting:
    """Test connection testing functionality"""
    
    def test_test_connection_no_session(self):
        """Test connection test without session"""
        agent = GongAgent()

        result = agent.test_connection()
        assert isinstance(result, dict)
        assert result['connected'] is False
        assert 'No session available' in result['error_message']
    
    def test_test_connection_success(self):
        """Test successful connection test"""
        agent = GongAgent()
        agent.session = Mock()
        
        with patch.object(agent.api_client, 'test_connection', return_value=True):
            result = agent.test_connection()
            assert result is True
    
    def test_test_connection_failure(self):
        """Test failed connection test"""
        agent = GongAgent()
        agent.session = Mock()

        with patch.object(agent.api_client, 'test_connection', side_effect=Exception("Connection failed")):
            result = agent.test_connection()
            assert isinstance(result, dict)
            assert result['connected'] is False
            assert 'Connection failed' in result['error_message']


class TestDataExtractionMethods:
    """Test individual data extraction methods"""
    
    def setup_method(self):
        """Setup for extraction tests"""
        self.agent = GongAgent()
        self.agent.session = Mock()
        self.agent.session.user_email = "test@example.com"
    
    def test_extract_calls_success(self):
        """Test successful calls extraction"""
        mock_calls = [{'id': '1', 'title': 'Test Call'}]
        
        with patch.object(self.agent.api_client, 'get_my_calls', return_value=mock_calls):
            calls = self.agent.extract_calls(limit=50)
            
            assert calls == mock_calls
            self.agent.api_client.get_my_calls.assert_called_once_with(limit=50)
    
    def test_extract_calls_no_session(self):
        """Test calls extraction without session"""
        agent = GongAgent()
        
        with pytest.raises(GongAgentError, match="No session available"):
            agent.extract_calls()
    
    def test_extract_calls_api_error(self):
        """Test calls extraction with API error"""
        with patch.object(self.agent.api_client, 'get_my_calls', side_effect=Exception("API Error")):
            with pytest.raises(GongAgentError, match="extract_calls failed after .* attempts"):
                self.agent.extract_calls()
    
    def test_extract_users_success(self):
        """Test successful users extraction"""
        mock_users = [{'id': '1', 'name': 'Test User'}]
        
        with patch.object(self.agent.api_client, 'get_users', return_value=mock_users):
            users = self.agent.extract_users()
            
            assert users == mock_users
            self.agent.api_client.get_users.assert_called_once()
    
    def test_extract_deals_success(self):
        """Test successful deals extraction"""
        mock_deals = [{'id': '1', 'name': 'Test Deal'}]
        
        with patch.object(self.agent.api_client, 'get_deals', return_value=mock_deals):
            deals = self.agent.extract_deals(limit=75)
            
            assert deals == mock_deals
            self.agent.api_client.get_deals.assert_called_once_with(limit=75)
    
    def test_extract_conversations_success(self):
        """Test successful conversations extraction"""
        mock_conversations = [{'id': '1', 'title': 'Test Conversation'}]
        
        with patch.object(self.agent.api_client, 'get_conversations', return_value=mock_conversations):
            conversations = self.agent.extract_conversations(limit=25)
            
            assert conversations == mock_conversations
            self.agent.api_client.get_conversations.assert_called_once_with(limit=25)
    
    def test_extract_library_success(self):
        """Test successful library extraction"""
        mock_library = {'folders': [], 'items': []}
        
        with patch.object(self.agent.api_client, 'get_library_data', return_value=mock_library):
            library = self.agent.extract_library()
            
            assert library == mock_library
            self.agent.api_client.get_library_data.assert_called_once()
    
    def test_extract_team_stats_success(self):
        """Test successful team stats extraction"""
        mock_stats = {'avgCallDuration': {'value': 1800}}

        with patch.object(self.agent.api_client, 'get_team_stats', return_value=mock_stats):
            stats = self.agent.extract_team_stats()

            assert isinstance(stats, list)
            assert len(stats) > 0
            # Check that at least one stat has the expected metric
            metric_names = [stat['metric'] for stat in stats]
            assert 'avgCallDuration' in metric_names
            # Should call multiple metrics
            assert self.agent.api_client.get_team_stats.call_count >= 1


class TestComprehensiveExtraction:
    """Test comprehensive data extraction"""
    
    def setup_method(self):
        """Setup for comprehensive extraction tests"""
        self.agent = GongAgent()
        self.agent.session = Mock()
        self.agent.session.user_email = "test@example.com"
        self.agent.session.cell_id = "us-14496"
        
        # Mock all extraction methods
        self.agent.extract_calls = Mock(return_value=[{'id': '1'}])
        self.agent.extract_users = Mock(return_value=[{'id': '2'}])
        self.agent.extract_deals = Mock(return_value=[{'id': '3'}])
        self.agent.extract_conversations = Mock(return_value=[{'id': '4'}])
        self.agent.extract_library = Mock(return_value={'folders': []})
        self.agent.extract_team_stats = Mock(return_value={'metric': 'value'})
    
    def test_extract_all_data_success(self):
        """Test successful comprehensive extraction"""
        result = self.agent.extract_all_data()
        
        # Check metadata
        assert 'metadata' in result
        assert 'data' in result
        
        metadata = result['metadata']
        assert metadata['target_objects'] == 6
        assert metadata['successful_objects'] == 6
        assert metadata['failed_objects'] == 0
        assert metadata['duration_seconds'] >= 0
        assert metadata['user_email'] == "test@example.com"
        assert metadata['cell_id'] == "us-14496"
        
        # Check data
        data = result['data']
        assert 'calls' in data
        assert 'users' in data
        assert 'deals' in data
        assert 'conversations' in data
        assert 'library' in data
        assert 'team_stats' in data
        
        # Verify all methods were called
        self.agent.extract_calls.assert_called_once()
        self.agent.extract_users.assert_called_once()
        self.agent.extract_deals.assert_called_once()
        self.agent.extract_conversations.assert_called_once()
        self.agent.extract_library.assert_called_once()
        self.agent.extract_team_stats.assert_called_once()
    
    def test_extract_all_data_selective(self):
        """Test selective data extraction"""
        result = self.agent.extract_all_data(
            include_calls=True,
            include_users=False,
            include_deals=True,
            include_conversations=False,
            include_library=False,
            include_stats=False
        )
        
        metadata = result['metadata']
        assert metadata['target_objects'] == 2
        assert metadata['successful_objects'] == 2
        
        data = result['data']
        assert 'calls' in data
        assert 'users' not in data
        assert 'deals' in data
        assert 'conversations' not in data
        
        self.agent.extract_calls.assert_called_once()
        self.agent.extract_users.assert_not_called()
        self.agent.extract_deals.assert_called_once()
    
    def test_extract_all_data_with_failures(self):
        """Test extraction with partial failures"""
        # Make some methods fail
        self.agent.extract_calls.side_effect = Exception("Calls failed")
        self.agent.extract_deals.side_effect = Exception("Deals failed")
        
        result = self.agent.extract_all_data()
        
        metadata = result['metadata']
        assert metadata['target_objects'] == 6
        assert metadata['successful_objects'] == 4  # 2 failed
        assert metadata['failed_objects'] == 2
        assert len(metadata['errors']) == 2
        
        # Should still have successful extractions
        data = result['data']
        assert 'users' in data
        assert 'conversations' in data
        assert 'library' in data
        assert 'team_stats' in data
    
    def test_extract_all_data_no_session(self):
        """Test extraction without session"""
        agent = GongAgent()
        
        with pytest.raises(GongAgentError, match="No session available"):
            agent.extract_all_data()
    
    def test_extract_all_data_performance_tracking(self):
        """Test performance tracking in extraction"""
        # Mock time to control duration - use side_effect with infinite values
        with patch('time.time') as mock_time:
            # Create an iterator that returns start time, then end time, then repeats end time
            def time_generator():
                yield 0  # start_time
                while True:
                    yield 15.5  # end_time and all other calls

            mock_time.side_effect = time_generator()

            result = self.agent.extract_all_data()

            metadata = result['metadata']
            assert metadata['duration_seconds'] == 15.5
            assert metadata['performance_target_met'] is True  # Under 30 seconds


class TestPerformanceValidation:
    """Test performance validation functionality"""
    
    def setup_method(self):
        """Setup for performance tests"""
        self.agent = GongAgent()
        self.agent.session = Mock()
        self.agent.session.user_email = "test@example.com"
    
    def test_validate_performance_no_session(self):
        """Test performance validation without session"""
        agent = GongAgent()
        
        result = agent.validate_performance()
        
        assert result['valid'] is False
        assert result['reason'] == 'No session available'
        assert result['performance_met'] is False
        assert result['object_types_met'] is False
    
    def test_validate_performance_success(self):
        """Test successful performance validation"""
        with patch.object(self.agent, 'extract_all_data') as mock_extract:
            mock_extract.return_value = {
                'metadata': {
                    'successful_objects': 6,
                    'duration_seconds': 12.5
                }
            }
            
            with patch('time.time') as mock_time:
                mock_time.side_effect = [0, 12.5]
                
                result = self.agent.validate_performance()
                
                assert result['valid'] is True
                assert result['performance_met'] is True
                assert result['object_types_met'] is True
                assert result['duration_seconds'] == 12.5
                assert result['successful_objects'] == 6
                assert result['overall_success'] is True
    
    def test_validate_performance_failure(self):
        """Test performance validation failure"""
        with patch.object(self.agent, 'extract_all_data', side_effect=Exception("Extraction failed")):
            result = self.agent.validate_performance()
            
            assert result['valid'] is False
            assert 'Validation extraction failed' in result['reason']
            assert result['performance_met'] is False
            assert result['object_types_met'] is False


class TestExtractionStatistics:
    """Test extraction statistics tracking"""
    
    def test_update_extraction_stats_success(self):
        """Test updating stats for successful extraction"""
        agent = GongAgent()
        
        agent._update_extraction_stats(5, 6, 15.5)
        
        stats = agent.extraction_stats
        assert stats['total_extractions'] == 1
        assert stats['successful_extractions'] == 1
        assert stats['failed_extractions'] == 0
        assert stats['average_duration'] == 15.5
        assert stats['last_error'] is None
    
    def test_update_extraction_stats_failure(self):
        """Test updating stats for failed extraction"""
        agent = GongAgent()
        
        agent._update_extraction_stats(3, 6, 25.0, error="Test error")
        
        stats = agent.extraction_stats
        assert stats['total_extractions'] == 1
        assert stats['successful_extractions'] == 0
        assert stats['failed_extractions'] == 1
        assert stats['average_duration'] == 25.0
        assert stats['last_error'] == "Test error"
    
    def test_get_extraction_stats(self):
        """Test getting extraction statistics"""
        agent = GongAgent()
        
        # Add some stats
        agent._update_extraction_stats(5, 6, 15.0)
        agent._update_extraction_stats(4, 6, 20.0, error="Partial failure")
        
        stats = agent.get_extraction_stats()
        
        assert stats['total_extractions'] == 2
        assert stats['successful_extractions'] == 1
        assert stats['failed_extractions'] == 1
        assert stats['success_rate'] == 0.5
        assert stats['failure_rate'] == 0.5
        assert stats['average_duration'] == 17.5
        assert stats['meets_performance_target'] is True  # 17.5 < 30
        assert stats['meets_success_target'] is False  # 0.5 < 0.95


class TestQuickExtract:
    """Test quick extraction functionality"""
    
    def test_quick_extract_with_session_source(self):
        """Test quick extract with session source"""
        agent = GongAgent()

        with patch.object(agent, 'set_session') as mock_set_session:
            with patch.object(agent, 'extract_all_data') as mock_extract:
                # Mock that session is set after set_session call
                agent.session = Mock()  # Set a mock session
                mock_extract.return_value = {'metadata': {'successful_objects': 6}}

                result = agent.quick_extract("test_file.json")

                mock_set_session.assert_called_once_with("test_file.json")
                mock_extract.assert_called_once()
                assert result['metadata']['successful_objects'] == 6
    
    def test_quick_extract_no_session(self):
        """Test quick extract without session"""
        agent = GongAgent()
        
        with pytest.raises(GongAgentError, match="No session available"):
            agent.quick_extract()


class TestStatusReporting:
    """Test comprehensive status reporting"""
    
    def test_get_status_no_session(self):
        """Test status reporting without session"""
        agent = GongAgent()
        
        status = agent.get_status()
        
        assert status['agent_status'] == 'no_session'
        assert 'session_info' in status
        assert 'extraction_stats' in status
        assert 'api_rate_limit' in status
        assert 'performance_targets' in status
        
        targets = status['performance_targets']
        assert targets['extraction_time_seconds'] == 30
        assert targets['success_rate'] == 0.95
        assert targets['minimum_object_types'] == 5
    
    def test_get_status_with_session(self):
        """Test status reporting with session"""
        agent = GongAgent()
        agent.session = Mock()
        
        with patch.object(agent, 'get_session_info', return_value={'status': 'active'}):
            with patch.object(agent.api_client, 'get_rate_limit_status', return_value={'remaining': 1000}):
                status = agent.get_status()
                
                assert status['agent_status'] == 'ready'
                assert status['session_info']['status'] == 'active'


class TestUtilityMethods:
    """Test utility methods"""
    
    def test_save_extraction_results(self):
        """Test saving extraction results"""
        agent = GongAgent()
        results = {'test': 'data'}
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            
            agent.save_extraction_results(results, temp_path)
            
            # Verify file was created
            assert temp_path.exists()
            
            # Clean up
            temp_path.unlink()


# Test fixtures
@pytest.fixture
def agent():
    """Agent fixture"""
    return GongAgent()


@pytest.fixture
def agent_with_session():
    """Agent with mock session fixture"""
    agent = GongAgent()
    session = Mock()
    session.user_email = "test@example.com"
    session.cell_id = "us-14496"
    agent.session = session
    return agent


@pytest.fixture
def mock_extraction_methods():
    """Mock extraction methods fixture"""
    def _mock_methods(agent):
        agent.extract_calls = Mock(return_value=[{'id': '1'}])
        agent.extract_users = Mock(return_value=[{'id': '2'}])
        agent.extract_deals = Mock(return_value=[{'id': '3'}])
        agent.extract_conversations = Mock(return_value=[{'id': '4'}])
        agent.extract_library = Mock(return_value={'folders': []})
        agent.extract_team_stats = Mock(return_value={'metric': 'value'})
        return agent
    return _mock_methods


if __name__ == "__main__":
    pytest.main([__file__, "-v"])