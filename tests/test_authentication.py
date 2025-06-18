"""
Unit tests for Gong authentication manager.

Tests session extraction, JWT token validation, and authentication workflows
with comprehensive mock data scenarios.
"""

import pytest
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from authentication import (
    GongAuthenticationManager,
    GongAuthenticationError,
    GongSessionExpiredError
)
from data_models import GongSession, GongAuthenticationToken, GongJWTPayload


class TestGongAuthenticationManager:
    """Test GongAuthenticationManager class"""
    
    def test_initialization(self):
        """Test authentication manager initialization"""
        auth_manager = GongAuthenticationManager()
        
        assert auth_manager.jwt_decoder is not None
        assert auth_manager.current_session is None
        assert len(auth_manager.session_cache) == 0
        assert len(auth_manager.gong_domains) > 0
        assert 'gong.io' in auth_manager.gong_domains
        assert 'us-14496.app.gong.io' in auth_manager.gong_domains
    
    def test_gong_domain_patterns(self):
        """Test Gong domain patterns"""
        auth_manager = GongAuthenticationManager()
        
        expected_domains = [
            'gong.io',
            'app.gong.io',
            'us-14496.app.gong.io',
            'api.gong.io',
            'gcell-nam-01.streams.gong.io',
            'resource.gcell-nam-01.app.gong.io'
        ]
        
        for domain in expected_domains:
            assert domain in auth_manager.gong_domains
    
    def test_jwt_cookie_names(self):
        """Test JWT cookie name patterns"""
        auth_manager = GongAuthenticationManager()
        
        expected_jwt_cookies = ['last_login_jwt', 'cell_jwt']
        assert auth_manager.jwt_cookie_names == expected_jwt_cookies
    
    def test_session_cookie_names(self):
        """Test session cookie name patterns"""
        auth_manager = GongAuthenticationManager()
        
        expected_session_cookies = [
            'g-session', 'AWSALB', 'AWSALBTG',
            'ajs_user_id', 'ajs_group_id'
        ]
        
        for cookie in expected_session_cookies:
            assert cookie in auth_manager.session_cookie_names


class TestHARSessionExtraction:
    """Test HAR session extraction functionality"""
    
    def create_mock_har_data(self):
        """Create mock HAR data for testing"""
        return {
            "log": {
                "version": "1.2",
                "entries": [
                    {
                        "request": {
                            "method": "GET",
                            "url": "https://us-14496.app.gong.io/ajax/common/rtkn",
                            "cookies": [
                                {
                                    "name": "last_login_jwt",
                                    "value": "eyJhbGciOiJIUzI1NiJ9.eyJncCI6Ik9rdGEiLCJleHAiOjE3NTI2NzcyNjUsImlhdCI6MTc1MDA4NTI2NSwianRpIjoiNW1rbWwweVdLRWF5IiwiZ3UiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiY2VsbCI6InVzLTE0NDk2In0.test_signature"
                                },
                                {
                                    "name": "g-session",
                                    "value": "test_session_value"
                                }
                            ]
                        },
                        "response": {
                            "status": 200,
                            "cookies": []
                        }
                    }
                ]
            }
        }
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    @patch.object(GongAuthenticationManager, '_process_jwt_cookie')
    def test_extract_session_from_har_success(self, mock_process_jwt, mock_json_load, mock_file):
        """Test successful session extraction from HAR"""
        # Setup mocks
        mock_har_data = self.create_mock_har_data()
        mock_json_load.return_value = mock_har_data
        
        # Mock JWT processing
        mock_jwt_payload = GongJWTPayload(
            gp="Okta",
            exp=1752677265,
            iat=1750085265,
            jti="test_jti",
            gu="test@example.com",
            cell="us-14496"
        )
        
        mock_auth_token = GongAuthenticationToken(
            token_type="last_login_jwt",
            raw_token="test_token",
            payload=mock_jwt_payload,
            expires_at=datetime.fromtimestamp(1752677265),
            issued_at=datetime.fromtimestamp(1750085265),
            is_expired=False,
            cell_id="us-14496",
            user_email="test@example.com"
        )
        
        mock_process_jwt.return_value = mock_auth_token
        
        # Test extraction
        auth_manager = GongAuthenticationManager()
        
        with tempfile.NamedTemporaryFile(suffix='.har') as temp_file:
            temp_path = Path(temp_file.name)
            session = auth_manager.extract_session_from_har(temp_path)
            
            assert session is not None
            assert session.user_email == "test@example.com"
            assert session.cell_id == "us-14496"
            assert len(session.authentication_tokens) > 0
            assert session.is_active
    
    def test_extract_session_from_har_file_not_found(self):
        """Test HAR extraction with non-existent file"""
        auth_manager = GongAuthenticationManager()
        
        with pytest.raises(GongAuthenticationError, match="HAR file not found"):
            auth_manager.extract_session_from_har(Path("non_existent.har"))
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_extract_session_from_har_no_tokens(self, mock_json_load, mock_file):
        """Test HAR extraction with no JWT tokens"""
        # HAR data without JWT tokens
        mock_har_data = {
            "log": {
                "entries": [
                    {
                        "request": {"cookies": []},
                        "response": {"cookies": []}
                    }
                ]
            }
        }
        mock_json_load.return_value = mock_har_data
        
        auth_manager = GongAuthenticationManager()
        
        with tempfile.NamedTemporaryFile(suffix='.har') as temp_file:
            temp_path = Path(temp_file.name)
            
            with pytest.raises(GongAuthenticationError, match="No JWT tokens found"):
                auth_manager.extract_session_from_har(temp_path)


class TestAnalysisSessionExtraction:
    """Test analysis session extraction functionality"""
    
    def create_mock_analysis_data(self):
        """Create mock analysis data for testing"""
        return {
            "artifacts": [
                {
                    "type": "cookie_last_login_jwt",
                    "name": "last_login_jwt",
                    "value": "eyJhbGciOiJIUzI1NiJ9.test_payload.test_signature",
                    "decoded_value": {
                        "header": {"alg": "HS256"},
                        "payload": {
                            "gp": "Okta",
                            "exp": 1752677265,
                            "iat": 1750085265,
                            "jti": "test_jti",
                            "gu": "test@example.com",
                            "cell": "us-14496"
                        }
                    }
                },
                {
                    "type": "cookie_gong_session",
                    "name": "g-session",
                    "value": "test_session_value"
                }
            ]
        }
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_extract_session_from_analysis_success(self, mock_json_load, mock_file):
        """Test successful session extraction from analysis"""
        mock_analysis_data = self.create_mock_analysis_data()
        mock_json_load.return_value = mock_analysis_data
        
        auth_manager = GongAuthenticationManager()
        
        with tempfile.NamedTemporaryFile(suffix='.json') as temp_file:
            temp_path = Path(temp_file.name)
            session = auth_manager.extract_session_from_analysis(temp_path)
            
            assert session is not None
            assert session.user_email == "test@example.com"
            assert session.cell_id == "us-14496"
            assert len(session.authentication_tokens) > 0
            assert len(session.session_cookies) > 0
    
    def test_extract_session_from_analysis_file_not_found(self):
        """Test analysis extraction with non-existent file"""
        auth_manager = GongAuthenticationManager()
        
        with pytest.raises(GongAuthenticationError, match="Analysis file not found"):
            auth_manager.extract_session_from_analysis(Path("non_existent.json"))


class TestJWTProcessing:
    """Test JWT token processing functionality"""
    
    def test_process_jwt_cookie_valid(self):
        """Test processing valid JWT cookie"""
        auth_manager = GongAuthenticationManager()
        
        # Mock JWT decoder
        with patch.object(auth_manager.jwt_decoder, 'decode') as mock_decode:
            mock_decode.return_value = {
                'header': {'alg': 'HS256'},
                'payload': {
                    'gp': 'Okta',
                    'exp': 1752677265,
                    'iat': 1750085265,
                    'jti': 'test_jti',
                    'gu': 'test@example.com',
                    'cell': 'us-14496'
                }
            }
            
            cookie = {
                'name': 'last_login_jwt',
                'value': 'eyJhbGciOiJIUzI1NiJ9.test_payload.test_signature'
            }
            
            token = auth_manager._process_jwt_cookie(cookie)
            
            assert token is not None
            assert token.token_type == 'last_login_jwt'
            assert token.user_email == 'test@example.com'
            assert token.cell_id == 'us-14496'
    
    def test_process_jwt_cookie_invalid(self):
        """Test processing invalid JWT cookie"""
        auth_manager = GongAuthenticationManager()
        
        cookie = {
            'name': 'last_login_jwt',
            'value': 'invalid_token'  # Doesn't start with eyJ
        }
        
        token = auth_manager._process_jwt_cookie(cookie)
        assert token is None
    
    def test_process_jwt_artifact_valid(self):
        """Test processing valid JWT artifact"""
        auth_manager = GongAuthenticationManager()
        
        artifact = {
            'name': 'last_login_jwt',
            'value': 'eyJhbGciOiJIUzI1NiJ9.test_payload.test_signature',
            'decoded_value': {
                'payload': {
                    'gp': 'Okta',
                    'exp': 1752677265,
                    'iat': 1750085265,
                    'jti': 'test_jti',
                    'gu': 'test@example.com',
                    'cell': 'us-14496'
                }
            }
        }
        
        token = auth_manager._process_jwt_artifact(artifact)
        
        assert token is not None
        assert token.token_type == 'last_login_jwt'
        assert token.user_email == 'test@example.com'


class TestSessionValidation:
    """Test session validation functionality"""
    
    def create_valid_session(self):
        """Create a valid session for testing"""
        jwt_payload = GongJWTPayload(
            gp="Okta",
            exp=int((datetime.now().timestamp() + 3600)),  # Expires in 1 hour
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
            session_cookies={"test": "value"}
        )
    
    def test_validate_session_valid(self):
        """Test validation of valid session"""
        auth_manager = GongAuthenticationManager()
        session = self.create_valid_session()
        
        # Should not raise exception
        auth_manager._validate_session(session)
        assert auth_manager.is_session_valid(session)
    
    def test_validate_session_no_tokens(self):
        """Test validation of session without tokens"""
        auth_manager = GongAuthenticationManager()
        
        session = GongSession(
            session_id="test",
            user_email="test@example.com",
            cell_id="us-14496",
            authentication_tokens=[],  # No tokens
            session_cookies={}
        )
        
        with pytest.raises(GongAuthenticationError, match="no authentication tokens"):
            auth_manager._validate_session(session)
    
    def test_validate_session_expired_tokens(self):
        """Test validation of session with expired tokens"""
        auth_manager = GongAuthenticationManager()
        
        # Create expired token
        jwt_payload = GongJWTPayload(
            gp="Okta",
            exp=int((datetime.now().timestamp() - 3600)),  # Expired 1 hour ago
            iat=int((datetime.now().timestamp() - 7200)),
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
            is_expired=True,
            cell_id="us-14496",
            user_email="test@example.com"
        )
        
        session = GongSession(
            session_id="test",
            user_email="test@example.com",
            cell_id="us-14496",
            authentication_tokens=[auth_token],
            session_cookies={}
        )
        
        with pytest.raises(GongSessionExpiredError, match="tokens have expired"):
            auth_manager._validate_session(session)


class TestSessionHeaders:
    """Test session header generation"""
    
    def test_get_session_headers_valid(self):
        """Test getting headers from valid session"""
        auth_manager = GongAuthenticationManager()
        
        # Create session with tokens
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
            raw_token="test_token_value",
            payload=jwt_payload,
            expires_at=datetime.fromtimestamp(jwt_payload.exp),
            issued_at=datetime.fromtimestamp(jwt_payload.iat),
            is_expired=False,
            cell_id="us-14496",
            user_email="test@example.com"
        )
        
        session = GongSession(
            session_id="test",
            user_email="test@example.com",
            cell_id="us-14496",
            authentication_tokens=[auth_token],
            session_cookies={"g-session": "session_value"}
        )
        
        auth_manager.current_session = session
        headers = auth_manager.get_session_headers(session)
        
        assert 'Cookie' in headers
        assert 'User-Agent' in headers
        assert 'Accept' in headers
        assert 'last_login_jwt=test_token_value' in headers['Cookie']
        assert 'g-session=session_value' in headers['Cookie']
    
    def test_get_session_headers_no_session(self):
        """Test getting headers without session"""
        auth_manager = GongAuthenticationManager()
        
        with pytest.raises(GongAuthenticationError, match="No valid session"):
            auth_manager.get_session_headers()


class TestBaseURL:
    """Test base URL generation"""
    
    def test_get_base_url_with_cell(self):
        """Test base URL generation with cell ID"""
        auth_manager = GongAuthenticationManager()
        
        session = GongSession(
            session_id="test",
            user_email="test@example.com",
            cell_id="us-14496",
            authentication_tokens=[],
            session_cookies={}
        )
        
        auth_manager.current_session = session
        base_url = auth_manager.get_base_url(session)
        
        assert base_url == "https://us-14496.app.gong.io"
    
    def test_get_base_url_no_cell(self):
        """Test base URL generation without cell ID"""
        auth_manager = GongAuthenticationManager()
        
        session = GongSession(
            session_id="test",
            user_email="test@example.com",
            cell_id="",  # No cell ID
            authentication_tokens=[],
            session_cookies={}
        )
        
        auth_manager.current_session = session
        base_url = auth_manager.get_base_url(session)
        
        assert base_url == "https://app.gong.io"


class TestUserCreation:
    """Test user creation from session"""
    
    def test_create_user_from_session(self):
        """Test creating user from session data"""
        auth_manager = GongAuthenticationManager()
        
        session = GongSession(
            session_id="test",
            user_email="john.doe@example.com",
            cell_id="us-14496",
            authentication_tokens=[],
            session_cookies={}
        )
        
        auth_manager.current_session = session
        user = auth_manager.create_user_from_session(session)
        
        assert user.email == "john.doe@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.full_name == "John Doe"
        assert user.is_internal is True


# Test fixtures
@pytest.fixture
def auth_manager():
    """Authentication manager fixture"""
    return GongAuthenticationManager()


@pytest.fixture
def valid_session():
    """Valid session fixture"""
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
        session_cookies={"test": "value"}
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])