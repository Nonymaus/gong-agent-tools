"""
Module: test_data_models
Type: Test

Purpose:
Data models and validation schemas for Gong platform integration.

Data Flow:
- Input: Authentication credentials
- Processing: API interaction
- Output: List of extracted data, Dictionary responses, Error states and exceptions

Critical Because:
Central integration point for Gong - without this, no Gong data can be accessed.

Dependencies:
- Requires: pytest, data_models
- Used By: app_backend.ingestion.orchestrator, app_backend.api_bridge.server

Author: Julia Evans
Date: 2025-06-20
"""
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_models import (
    GongJWTPayload, GongAuthenticationToken, GongSession,
    GongUser, GongContact, GongCall, GongCallParticipant,
    GongAccount, GongDeal, GongActivity, GongEmailActivity,
    GongCallMetrics, GongTeamStats, GongLibraryItem,
    GongAPIResponse, GongPaginatedResponse,
    CallTypeEnum, DealStageEnum, ActivityTypeEnum
)


class TestGongJWTPayload:
    """Test GongJWTPayload model"""
    
    def test_valid_jwt_payload(self):
        """Test valid JWT payload creation"""
        payload = GongJWTPayload(
            gp="Okta",
            exp=1752677265,
            iat=1750085265,
            jti="5mkml0yWKEay",
            gu="test@example.com",
            cell="us-14496"
        )
        
        assert payload.gp == "Okta"
        assert payload.exp == 1752677265
        assert payload.gu == "test@example.com"
        assert payload.cell == "us-14496"
    
    def test_invalid_timestamp(self):
        """Test invalid timestamp validation"""
        with pytest.raises(ValueError, match="Invalid timestamp"):
            GongJWTPayload(
                exp=123,  # Invalid timestamp
                iat=1750085265,
                jti="test",
                gu="test@example.com"
            )
    
    def test_invalid_email(self):
        """Test invalid email validation"""
        with pytest.raises(ValueError, match="Invalid email format"):
            GongJWTPayload(
                exp=1752677265,
                iat=1750085265,
                jti="test",
                gu="invalid-email"  # No @ symbol
            )


class TestGongAuthenticationToken:
    """Test GongAuthenticationToken model"""
    
    def test_valid_auth_token(self):
        """Test valid authentication token creation"""
        payload = GongJWTPayload(
            gp="Okta",
            exp=1752677265,
            iat=1750085265,
            jti="test",
            gu="test@example.com",
            cell="us-14496"
        )
        
        token = GongAuthenticationToken(
            token_type="last_login_jwt",
            raw_token="eyJhbGciOiJIUzI1NiJ9...",
            payload=payload,
            expires_at=datetime.fromtimestamp(1752677265),
            issued_at=datetime.fromtimestamp(1750085265),
            is_expired=False,
            cell_id="us-14496",
            user_email="test@example.com"
        )
        
        assert token.token_type == "last_login_jwt"
        assert token.user_email == "test@example.com"
        assert token.cell_id == "us-14496"
        assert not token.is_expired


class TestGongSession:
    """Test GongSession model"""
    
    def test_valid_session(self):
        """Test valid session creation"""
        session = GongSession(
            session_id="test_session",
            user_email="test@example.com",
            cell_id="us-14496",
            authentication_tokens=[],
            session_cookies={"test": "value"}
        )
        
        assert session.session_id == "test_session"
        assert session.user_email == "test@example.com"
        assert session.is_active
    
    def test_cell_id_validation(self):
        """Test cell ID validation"""
        with pytest.raises(ValueError, match="Invalid cell ID format"):
            GongSession(
                session_id="test",
                user_email="test@example.com",
                cell_id="x",  # Too short
                authentication_tokens=[],
                session_cookies={}
            )


class TestGongUser:
    """Test GongUser model"""
    
    def test_valid_user(self):
        """Test valid user creation"""
        user = GongUser(
            email="john.doe@example.com",
            first_name="John",
            last_name="Doe",
            title="Sales Manager"
        )
        
        assert user.email == "john.doe@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
    
    def test_email_normalization(self):
        """Test email normalization to lowercase"""
        user = GongUser(email="JOHN.DOE@EXAMPLE.COM")
        assert user.email == "john.doe@example.com"
    
    def test_invalid_email(self):
        """Test invalid email validation"""
        with pytest.raises(ValueError, match="Invalid email format"):
            GongUser(email="invalid-email")


class TestGongCall:
    """Test GongCall model"""
    
    def test_valid_call(self):
        """Test valid call creation"""
        call = GongCall(
            call_id="call_123",
            call_type=CallTypeEnum.VIDEO,
            start_time=datetime.now(),
            duration_seconds=1800
        )
        
        assert call.call_id == "call_123"
        assert call.call_type == CallTypeEnum.VIDEO
        assert call.duration_seconds == 1800
    
    def test_invalid_duration(self):
        """Test invalid duration validation"""
        with pytest.raises(ValueError, match="Invalid call duration"):
            GongCall(
                call_id="test",
                call_type=CallTypeEnum.VIDEO,
                start_time=datetime.now(),
                duration_seconds=100000  # Too long (>24 hours)
            )


class TestGongDeal:
    """Test GongDeal model"""
    
    def test_valid_deal(self):
        """Test valid deal creation"""
        deal = GongDeal(
            deal_id="deal_123",
            name="Test Deal",
            account_id="account_123",
            owner_email="owner@example.com",
            stage=DealStageEnum.PROPOSAL,
            amount=50000.0,
            probability=75.0
        )
        
        assert deal.deal_id == "deal_123"
        assert deal.stage == DealStageEnum.PROPOSAL
        assert deal.probability == 75.0
    
    def test_invalid_probability(self):
        """Test invalid probability validation"""
        with pytest.raises(ValueError, match="Probability must be between 0 and 100"):
            GongDeal(
                deal_id="test",
                name="Test",
                account_id="test",
                owner_email="test@example.com",
                stage=DealStageEnum.PROPOSAL,
                probability=150.0  # Invalid: > 100
            )


class TestGongCallMetrics:
    """Test GongCallMetrics model"""
    
    def test_valid_metrics(self):
        """Test valid call metrics creation"""
        metrics = GongCallMetrics(
            call_id="call_123",
            total_duration_seconds=1800,
            talk_time_seconds=1500,
            silence_time_seconds=300,
            customer_talk_time_seconds=750,
            rep_talk_time_seconds=750,
            sentiment_score=0.8,
            engagement_score=0.9
        )
        
        assert metrics.call_id == "call_123"
        assert metrics.sentiment_score == 0.8
        assert metrics.engagement_score == 0.9
    
    def test_invalid_sentiment_score(self):
        """Test invalid sentiment score validation"""
        with pytest.raises(ValueError, match="Score must be between -1 and 1"):
            GongCallMetrics(
                call_id="test",
                total_duration_seconds=1800,
                talk_time_seconds=1500,
                sentiment_score=2.0  # Invalid: > 1
            )


class TestGongTeamStats:
    """Test GongTeamStats model"""
    
    def test_valid_team_stats(self):
        """Test valid team stats creation"""
        stats = GongTeamStats(
            period_start=datetime.now() - timedelta(days=30),
            period_end=datetime.now(),
            total_calls=100,
            win_rate=85.5
        )
        
        assert stats.total_calls == 100
        assert stats.win_rate == 85.5
    
    def test_invalid_win_rate(self):
        """Test invalid win rate validation"""
        with pytest.raises(ValueError, match="Win rate must be between 0 and 100"):
            GongTeamStats(
                period_start=datetime.now(),
                period_end=datetime.now(),
                win_rate=150.0  # Invalid: > 100
            )


class TestGongAPIResponse:
    """Test GongAPIResponse model"""
    
    def test_valid_api_response(self):
        """Test valid API response creation"""
        response = GongAPIResponse(
            success=True,
            data={"key": "value"},
            timestamp=datetime.now()
        )
        
        assert response.success is True
        assert response.data["key"] == "value"
        assert response.error is None


class TestGongPaginatedResponse:
    """Test GongPaginatedResponse model"""
    
    def test_valid_paginated_response(self):
        """Test valid paginated response creation"""
        response = GongPaginatedResponse(
            items=[{"id": 1}, {"id": 2}],
            total_count=100,
            page=1,
            page_size=50,
            has_more=True
        )
        
        assert len(response.items) == 2
        assert response.total_count == 100
        assert response.has_more is True


class TestEnums:
    """Test enum values"""
    
    def test_call_type_enum(self):
        """Test CallTypeEnum values"""
        assert CallTypeEnum.VIDEO == "video"
        assert CallTypeEnum.AUDIO == "audio"
        assert CallTypeEnum.PHONE == "phone"
    
    def test_deal_stage_enum(self):
        """Test DealStageEnum values"""
        assert DealStageEnum.PROPOSAL == "proposal"
        assert DealStageEnum.CLOSED_WON == "closed_won"
    
    def test_activity_type_enum(self):
        """Test ActivityTypeEnum values"""
        assert ActivityTypeEnum.CALL == "call"
        assert ActivityTypeEnum.EMAIL == "email"


class TestMockDataValidation:
    """Test models with realistic mock data"""
    
    def test_realistic_jwt_payload(self):
        """Test with realistic JWT payload data"""
        payload = GongJWTPayload(
            gp="Okta",
            exp=1752677265,  # Real timestamp from HAR
            iat=1750085265,
            jti="5mkml0yWKEay",
            gu="jared.boynton@postman.com",
            cell="us-14496"
        )
        
        assert payload.gp == "Okta"
        assert payload.gu == "jared.boynton@postman.com"
    
    def test_realistic_session_data(self):
        """Test with realistic session data"""
        session = GongSession(
            session_id="gong_session_20250616",
            user_email="jared.boynton@postman.com",
            cell_id="us-14496",
            company_id="5273795226998704580",
            workspace_id="5562739194953732039",
            authentication_tokens=[],
            session_cookies={
                "g-session": "abc123",
                "AWSALB": "xyz789",
                "last_login_jwt": "eyJhbGciOiJIUzI1NiJ9..."
            }
        )
        
        assert session.user_email == "jared.boynton@postman.com"
        assert session.cell_id == "us-14496"
        assert len(session.session_cookies) == 3
    
    def test_realistic_call_data(self):
        """Test with realistic call data"""
        participant = GongCallParticipant(
            email="participant@example.com",
            name="John Participant",
            is_host=False,
            talk_time_seconds=900
        )
        
        call = GongCall(
            call_id="call_789456123",
            title="Sales Discovery Call - Acme Corp",
            call_type=CallTypeEnum.VIDEO,
            start_time=datetime(2025, 6, 16, 14, 30),
            end_time=datetime(2025, 6, 16, 15, 15),
            duration_seconds=2700,
            participants=[participant],
            host_email="sales@example.com",
            is_processed=True
        )
        
        assert call.title == "Sales Discovery Call - Acme Corp"
        assert len(call.participants) == 1
        assert call.duration_seconds == 2700
    
    def test_realistic_deal_data(self):
        """Test with realistic deal data"""
        deal = GongDeal(
            deal_id="deal_456789",
            name="Acme Corp - Enterprise License",
            account_id="account_123456",
            owner_email="sales@example.com",
            stage=DealStageEnum.PROPOSAL,
            amount=125000.0,
            currency="USD",
            probability=75.0,
            close_date=datetime(2025, 7, 15),
            source="Inbound Lead",
            type="New Business"
        )
        
        assert deal.name == "Acme Corp - Enterprise License"
        assert deal.amount == 125000.0
        assert deal.probability == 75.0


# Test fixtures for reuse
@pytest.fixture
def sample_jwt_payload():
    """Sample JWT payload for testing"""
    return GongJWTPayload(
        gp="Okta",
        exp=1752677265,
        iat=1750085265,
        jti="test_jti",
        gu="test@example.com",
        cell="us-14496"
    )


@pytest.fixture
def sample_session():
    """Sample session for testing"""
    return GongSession(
        session_id="test_session",
        user_email="test@example.com",
        cell_id="us-14496",
        authentication_tokens=[],
        session_cookies={"test": "value"}
    )


@pytest.fixture
def sample_call():
    """Sample call for testing"""
    return GongCall(
        call_id="test_call",
        call_type=CallTypeEnum.VIDEO,
        start_time=datetime.now()
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])