"""
Module: conftest
Type: Test

Purpose:
Unit tests for Gong functionality ensuring reliability and correctness.

Data Flow:
- Input: HTTP requests, Configuration parameters, Authentication credentials
- Processing: Data extraction, API interaction
- Output: Processed results

Critical Because:
Central integration point for Gong - without this, no Gong data can be accessed.

Dependencies:
- Requires: pytest, tempfile, unittest.mock, data_models, authentication, api_client, agent
- Used By: app_backend.ingestion.orchestrator, app_backend.api_bridge.server

Author: Julia Evans
Date: 2025-06-20
"""
import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_models import GongSession, GongAuthenticationToken, GongJWTPayload
from authentication import GongAuthenticationManager
from api_client import GongAPIClient
from agent import GongAgent


@pytest.fixture
def mock_jwt_payload():
    """Mock JWT payload fixture"""
    return GongJWTPayload(
        gp="Okta",
        exp=int((datetime.now().timestamp() + 3600)),  # Expires in 1 hour
        iat=int(datetime.now().timestamp()),
        jti="test_jti",
        gu="test@example.com",
        cell="us-14496"
    )


@pytest.fixture
def mock_auth_token(mock_jwt_payload):
    """Mock authentication token fixture"""
    return GongAuthenticationToken(
        token_type="last_login_jwt",
        raw_token="eyJhbGciOiJIUzI1NiJ9.test_payload.test_signature",
        payload=mock_jwt_payload,
        expires_at=datetime.fromtimestamp(mock_jwt_payload.exp),
        issued_at=datetime.fromtimestamp(mock_jwt_payload.iat),
        is_expired=False,
        cell_id="us-14496",
        user_email="test@example.com"
    )


@pytest.fixture
def mock_session(mock_auth_token):
    """Mock session fixture"""
    return GongSession(
        session_id="test_session",
        user_email="test@example.com",
        cell_id="us-14496",
        company_id="test_company",
        workspace_id="test_workspace",
        authentication_tokens=[mock_auth_token],
        session_cookies={
            "g-session": "test_session_value",
            "AWSALB": "test_alb_value"
        },
        created_at=datetime.now(),
        last_activity=datetime.now(),
        is_active=True
    )


@pytest.fixture
def auth_manager():
    """Authentication manager fixture"""
    return GongAuthenticationManager()


@pytest.fixture
def api_client():
    """API client fixture"""
    return GongAPIClient()


@pytest.fixture
def agent():
    """Agent fixture"""
    return GongAgent()


@pytest.fixture
def agent_with_session(mock_session):
    """Agent with session fixture"""
    agent = GongAgent()
    agent.session = mock_session
    agent.auth_manager.current_session = mock_session
    return agent


@pytest.fixture
def temp_har_file():
    """Temporary HAR file fixture"""
    har_content = {
        "log": {
            "version": "1.2",
            "entries": [
                {
                    "request": {
                        "method": "GET",
                        "url": "https://us-14496.app.gong.io/test",
                        "cookies": [
                            {
                                "name": "last_login_jwt",
                                "value": "eyJhbGciOiJIUzI1NiJ9.test_payload.test_signature"
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
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.har', delete=False) as f:
        import json
        json.dump(har_content, f)
        yield Path(f.name)
    
    # Cleanup
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def temp_analysis_file():
    """Temporary analysis file fixture"""
    analysis_content = {
        "artifacts": [
            {
                "type": "cookie_last_login_jwt",
                "name": "last_login_jwt",
                "value": "eyJhbGciOiJIUzI1NiJ9.test_payload.test_signature",
                "decoded_value": {
                    "header": {"alg": "HS256"},
                    "payload": {
                        "gp": "Okta",
                        "exp": int((datetime.now().timestamp() + 3600)),
                        "iat": int(datetime.now().timestamp()),
                        "jti": "test_jti",
                        "gu": "test@example.com",
                        "cell": "us-14496"
                    }
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        import json
        json.dump(analysis_content, f)
        yield Path(f.name)
    
    # Cleanup
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def mock_api_responses():
    """Mock API responses fixture"""
    return {
        'calls': [
            {'id': 'call_1', 'title': 'Test Call 1', 'duration': 1800},
            {'id': 'call_2', 'title': 'Test Call 2', 'duration': 2400}
        ],
        'users': [
            {'id': 'user_1', 'name': 'John Doe', 'email': 'john@example.com'},
            {'id': 'user_2', 'name': 'Jane Smith', 'email': 'jane@example.com'}
        ],
        'deals': [
            {'id': 'deal_1', 'name': 'Deal 1', 'amount': 50000},
            {'id': 'deal_2', 'name': 'Deal 2', 'amount': 75000}
        ],
        'conversations': [
            {'id': 'conv_1', 'title': 'Conversation 1'},
            {'id': 'conv_2', 'title': 'Conversation 2'}
        ],
        'library': {
            'folders': [
                {'id': 'folder_1', 'name': 'Sales Calls'},
                {'id': 'folder_2', 'name': 'Training'}
            ]
        },
        'team_stats': {
            'avgCallDuration': {'value': 1800, 'unit': 'seconds'},
            'totalCalls': {'value': 150, 'unit': 'count'}
        }
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers"""
    for item in items:
        # Add unit marker to all tests by default
        if not any(marker.name in ['integration', 'slow'] for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)


# Custom assertions
def assert_valid_session(session):
    """Assert that a session is valid"""
    assert session is not None
    assert hasattr(session, 'user_email')
    assert hasattr(session, 'cell_id')
    assert hasattr(session, 'authentication_tokens')
    assert hasattr(session, 'session_cookies')
    assert session.user_email
    assert session.cell_id


def assert_valid_extraction_result(result):
    """Assert that an extraction result is valid"""
    assert 'metadata' in result
    assert 'data' in result
    
    metadata = result['metadata']
    assert 'extraction_id' in metadata
    assert 'timestamp' in metadata
    assert 'target_objects' in metadata
    assert 'successful_objects' in metadata
    assert 'failed_objects' in metadata
    assert 'duration_seconds' in metadata
    
    assert metadata['target_objects'] >= 0
    assert metadata['successful_objects'] >= 0
    assert metadata['failed_objects'] >= 0
    assert metadata['duration_seconds'] >= 0


# Add custom assertions to pytest namespace
pytest.assert_valid_session = assert_valid_session
pytest.assert_valid_extraction_result = assert_valid_extraction_result