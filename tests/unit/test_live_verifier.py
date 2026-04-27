"""Unit tests for live verifier integration."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestLiveVerifier:
    """Tests for LiveVerifier."""
    
    @pytest.fixture
    def config(self):
        """Create verification config for testing."""
        from luminamind.evaluator.live_verifier import VerificationConfig
        
        return VerificationConfig(
            enable_ui=True,
            ui_url="https://example.com",
            enable_api=True,
            api_base_url="https://api.example.com",
            enable_db=False,
            enable_visual=True,
            visual_threshold=0.01,
        )
    
    @pytest.fixture
    def verifier(self, config):
        """Create live verifier for testing."""
        from luminamind.evaluator.live_verifier import LiveVerifier
        return LiveVerifier(config)
    
    @pytest.mark.asyncio
    async def test_verify_ui_success(self, verifier):
        """Test UI verification success."""
        with patch("luminamind.evaluator.live_verifier.PlaywrightMCPBridge") as MockBridge:
            mock_bridge = AsyncMock()
            mock_bridge.connect = AsyncMock()
            mock_bridge.screenshot = AsyncMock(return_value=b"fake-screenshot")
            mock_bridge.get_dom_state = AsyncMock(return_value="<html>test</html>")
            mock_bridge.disconnect = AsyncMock()
            MockBridge.return_value = mock_bridge
            
            result = await verifier._verify_ui()
            
            assert result.verification_type.value == "ui"
            assert result.passed is True
            assert result.score == 1.0
    
    @pytest.mark.asyncio
    async def test_verify_ui_failure(self, verifier):
        """Test UI verification failure."""
        with patch("luminamind.evaluator.live_verifier.PlaywrightMCPBridge") as MockBridge:
            mock_bridge = AsyncMock()
            mock_bridge.connect = AsyncMock(side_effect=Exception("Connection failed"))
            MockBridge.return_value = mock_bridge
            
            result = await verifier._verify_ui()
            
            assert result.passed is False
            assert result.score == 0.0
            assert "error" in result.details
    
    @pytest.mark.asyncio
    async def test_verify_all_enabled(self, verifier):
        """Test running all verifications when enabled."""
        with patch("luminamind.evaluator.live_verifier.PlaywrightMCPBridge") as MockBridge:
            mock_bridge = AsyncMock()
            mock_bridge.connect = AsyncMock()
            mock_bridge.screenshot = AsyncMock(return_value=b"fake-screenshot")
            mock_bridge.get_dom_state = AsyncMock(return_value="<html>test</html>")
            mock_bridge.disconnect = AsyncMock()
            MockBridge.return_value = mock_bridge
            
            with patch("luminamind.evaluator.live_verifier.APITester") as MockTester:
                mock_tester = AsyncMock()
                mock_tester.__aenter__ = AsyncMock(return_value=mock_tester)
                mock_tester.__aexit__ = AsyncMock()
                mock_tester.discover = AsyncMock(return_value=[])
                MockTester.return_value = mock_tester
                
                # Set up API without spec to skip tests
                verifier.config.enable_api = False
                verifier.config.enable_db = False
                
                report = await verifier.verify()
                
                assert report.total_score >= 0.0
                assert len(report.results) >= 1  # At least UI


class TestVerificationConfig:
    """Tests for VerificationConfig."""
    
    def test_default_config(self):
        """Test default configuration."""
        from luminamind.evaluator.live_verifier import VerificationConfig
        
        config = VerificationConfig()
        
        assert config.enable_ui is True
        assert config.enable_api is True
        assert config.enable_db is False
        assert config.enable_visual is True
        assert config.visual_threshold == 0.01
    
    def test_custom_config(self):
        """Test custom configuration."""
        from luminamind.evaluator.live_verifier import VerificationConfig
        
        config = VerificationConfig(
            enable_db=True,
            db_connection="mock-connection",
            db_assertions=["mock-assertion"],
        )
        
        assert config.enable_db is True
        assert config.db_connection == "mock-connection"


class TestLiveVerificationReport:
    """Tests for report structure."""
    
    def test_report_structure(self):
        """Test report has correct structure."""
        from luminamind.evaluator.live_verifier import (
            LiveVerificationReport,
            VerificationResult,
            VerificationType,
        )
        
        result = VerificationResult(
            verification_type=VerificationType.UI,
            passed=True,
            score=1.0,
            details={},
            duration_ms=100.0,
        )
        
        report = LiveVerificationReport(
            timestamp="2026-04-27T00:00:00",
            total_score=1.0,
            passed=True,
            results=[result],
            duration_ms=100.0,
        )
        
        assert report.total_score == 1.0
        assert report.passed is True
        assert len(report.results) == 1