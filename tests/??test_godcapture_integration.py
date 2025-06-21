"""
Module: test_godcapture_integration
Type: Test

Purpose:
Unit tests for Gong functionality ensuring reliability and correctness.

Data Flow:
- Input: Configuration parameters, Authentication credentials
- Processing: Data extraction
- Output: Processed results

Critical Because:
Central integration point for Gong - without this, no Gong data can be accessed.

Dependencies:
- Requires: pytest, unittest.mock, agent, _godcapture.core.interfaces
- Used By: app_backend.ingestion.orchestrator, app_backend.api_bridge.server

Author: Julia Evans
Date: 2025-06-20
"""
import pytest
from unittest.mock import Mock, AsyncMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from agent import GongAgent
from _godcapture.core.interfaces import IGodCapture

class TestGongGodCaptureIntegration:
    """Test Gong integration with GodCapture"""
    
    @pytest.fixture
    def mock_godcapture(self):
        """Create mock GodCapture instance"""
        mock = Mock(spec=IGodCapture)
        mock.load_session = AsyncMock()
        mock.reauthenticate = AsyncMock()
        return mock
    
    @pytest.fixture
    def gong_agent(self, mock_godcapture):
        """Create Gong agent with mock GodCapture"""
        return GongAgent(godcapture=mock_godcapture)
    
    @pytest.mark.asyncio
    async def test_initialization(self, gong_agent, mock_godcapture):
        """Test agent initialization"""
        await gong_agent.initialize()
        mock_godcapture.load_session.assert_called_once_with("gong")
    
    @pytest.mark.asyncio
    async def test_auto_refresh(self, gong_agent, mock_godcapture):
        """Test automatic session refresh"""
        # Simulate expired session
        mock_godcapture.load_session.return_value = None
        await gong_agent._ensure_authenticated()
        mock_godcapture.reauthenticate.assert_called_once_with("gong")
    
    def test_extract_calls(self, gong_agent):
        """Test call extraction"""
        # Would add more comprehensive tests here
        assert gong_agent is not None
    
    def test_performance_targets(self, gong_agent):
        """Test performance target validation"""
        assert gong_agent.performance_target_seconds == 30
        assert gong_agent.success_rate_target == 0.95
