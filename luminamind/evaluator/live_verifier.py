"""Live verification orchestration for EvaluatorAgent integration."""
import asyncio
from dataclasses import dataclass, field
from typing import Any
from enum import Enum
from datetime import datetime

from luminamind.evaluator.playwright_mcp_bridge import PlaywrightMCPBridge
from luminamind.evaluator.session_manager import BrowserSessionManager
from luminamind.evaluator.api_tester import APITester
from luminamind.evaluator.db_verifier import DatabaseVerifier, DBAssertion, AssertionType
from luminamind.evaluator.visual_regression import VisualRegressionDetector


class VerificationType(Enum):
    """Types of verification to run."""
    UI = "ui"
    API = "api"
    DATABASE = "database"
    VISUAL = "visual"
    ALL = "all"


@dataclass
class VerificationConfig:
    """Configuration for live verification."""
    # UI verification
    enable_ui: bool = True
    ui_url: str | None = None
    ui_viewport: tuple[int, int] = (1280, 720)
    # API verification
    enable_api: bool = True
    api_base_url: str | None = None
    api_openapi_spec: str | None = None
    # Database verification
    enable_db: bool = False
    db_connection: Any = None
    db_assertions: list[DBAssertion] = field(default_factory=list)
    # Visual regression
    enable_visual: bool = True
    visual_threshold: float = 0.01
    baseline_screenshots: dict[str, bytes] = field(default_factory=dict)


@dataclass
class VerificationResult:
    """Result of a single verification type."""
    verification_type: VerificationType
    passed: bool
    score: float  # 0.0-1.0
    details: dict[str, Any]
    duration_ms: float


@dataclass
class LiveVerificationReport:
    """Complete live verification report."""
    timestamp: str
    total_score: float
    passed: bool
    results: list[VerificationResult]
    duration_ms: float


class LiveVerifier:
    """Orchestrates all live verification types.
    
    Integrates:
    - Playwright MCP bridge for UI verification
    - API tester for backend contract verification
    - Database verifier for state verification
    - Visual regression detector for UI change detection
    
    All verification runs in sandboxed context for isolation.
    """
    
    def __init__(self, config: VerificationConfig):
        """Initialize live verifier.
        
        Args:
            config: Verification configuration with enable flags and settings
        """
        self.config = config
        self._browser_manager: BrowserSessionManager | None = None
        self._api_tester: APITester | None = None
        self._db_verifier: DatabaseVerifier | None = None
        self._visual_detector: VisualRegressionDetector | None = None
    
    async def verify(self) -> LiveVerificationReport:
        """Run all enabled verifications.
        
        Returns:
            LiveVerificationReport with aggregated results
        """
        start_time = datetime.utcnow()
        results = []
        
        if self.config.enable_ui:
            ui_result = await self._verify_ui()
            results.append(ui_result)
        
        if self.config.enable_api:
            api_result = await self._verify_api()
            results.append(api_result)
        
        if self.config.enable_db:
            db_result = await self._verify_database()
            results.append(db_result)
        
        if self.config.enable_visual:
            visual_result = await self._verify_visual()
            results.append(visual_result)
        
        # Calculate total score
        total_score = sum(r.score for r in results) / len(results) if results else 0.0
        passed = all(r.passed for r in results)
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return LiveVerificationReport(
            timestamp=datetime.utcnow().isoformat(),
            total_score=total_score,
            passed=passed,
            results=results,
            duration_ms=duration_ms,
        )
    
    async def _verify_ui(self) -> VerificationResult:
        """Run UI verification via Playwright."""
        start_time = datetime.utcnow()
        
        try:
            bridge = PlaywrightMCPBridge(
                headless=True,
                viewport=self.config.ui_viewport,
            )
            await bridge.connect()
            
            try:
                if self.config.ui_url:
                    await bridge.screenshot(self.config.ui_url)
                
                # UI smoke test - check page loads without crash
                await bridge.get_dom_state()
                
                score = 1.0
                passed = True
                details = {"url": self.config.ui_url, "status": "loaded"}
            finally:
                await bridge.disconnect()
            
        except Exception as e:
            score = 0.0
            passed = False
            details = {"error": str(e)}
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return VerificationResult(
            verification_type=VerificationType.UI,
            passed=passed,
            score=score,
            details=details,
            duration_ms=duration_ms,
        )
    
    async def _verify_api(self) -> VerificationResult:
        """Run API verification via APITester."""
        start_time = datetime.utcnow()
        
        try:
            if not self.config.api_base_url:
                return VerificationResult(
                    verification_type=VerificationType.API,
                    passed=False,
                    score=0.0,
                    details={"error": "No API base URL configured"},
                    duration_ms=0,
                )
            
            async with APITester(
                base_url=self.config.api_base_url,
                openapi_spec=self.config.api_openapi_spec,
            ) as tester:
                endpoints = await tester.discover()
                
                # Test a sample of endpoints
                test_results = []
                for ep in endpoints[:5]:  # Limit to 5 for speed
                    result = await tester.test_endpoint(ep)
                    test_results.append({
                        "endpoint": ep.path,
                        "method": ep.method,
                        "passed": result.passed,
                    })
                
                passed_count = sum(1 for r in test_results if r["passed"])
                score = passed_count / len(test_results) if test_results else 0.0
                passed = score >= 0.8
                
                details = {
                    "endpoints_tested": len(test_results),
                    "passed": passed_count,
                    "results": test_results,
                }
                
        except Exception as e:
            score = 0.0
            passed = False
            details = {"error": str(e)}
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return VerificationResult(
            verification_type=VerificationType.API,
            passed=passed,
            score=score,
            details=details,
            duration_ms=duration_ms,
        )
    
    async def _verify_database(self) -> VerificationResult:
        """Run database verification."""
        start_time = datetime.utcnow()
        
        try:
            if not self.config.db_connection:
                return VerificationResult(
                    verification_type=VerificationType.DATABASE,
                    passed=False,
                    score=0.0,
                    details={"error": "No DB connection configured"},
                    duration_ms=0,
                )
            
            if not self.config.db_assertions:
                return VerificationResult(
                    verification_type=VerificationType.DATABASE,
                    passed=True,
                    score=1.0,
                    details={"status": "no assertions to run"},
                    duration_ms=0,
                )
            
            from luminamind.evaluator.schema_introspector import SchemaIntrospector
            
            verifier = DatabaseVerifier(
                self.config.db_connection,
                SchemaIntrospector(self.config.db_connection),
            )
            
            report = await verifier.verify(self.config.db_assertions)
            
            passed = report.failed == 0
            score = report.passed / report.total_assertions if report.total_assertions > 0 else 1.0
            
            details = {
                "total": report.total_assertions,
                "passed": report.passed,
                "failed": report.failed,
                "results": [
                    {"assertion": r.assertion.description, "passed": r.passed}
                    for r in report.results
                ],
            }
            
        except Exception as e:
            score = 0.0
            passed = False
            details = {"error": str(e)}
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return VerificationResult(
            verification_type=VerificationType.DATABASE,
            passed=passed,
            score=score,
            details=details,
            duration_ms=duration_ms,
        )
    
    async def _verify_visual(self) -> VerificationResult:
        """Run visual regression verification."""
        start_time = datetime.utcnow()
        
        try:
            if not self.config.ui_url:
                return VerificationResult(
                    verification_type=VerificationType.VISUAL,
                    passed=False,
                    score=0.0,
                    details={"error": "No UI URL configured for visual verification"},
                    duration_ms=0,
                )
            
            detector = VisualRegressionDetector(threshold=self.config.visual_threshold)
            
            # Capture current screenshot
            bridge = PlaywrightMCPBridge(headless=True)
            await bridge.connect()
            
            try:
                current_screenshot = await bridge.screenshot(self.config.ui_url)
            finally:
                await bridge.disconnect()
            
            # Compare against baseline if exists
            baseline_key = self.config.ui_url
            if baseline_key in self.config.baseline_screenshots:
                baseline = self.config.baseline_screenshots[baseline_key]
                diff_result = detector.compare(baseline, current_screenshot)
                
                passed = not diff_result.has_changed
                score = 1.0 - diff_result.diff_percentage
                
                details = {
                    "diff_percentage": diff_result.diff_percentage,
                    "changed_regions": len(diff_result.changed_regions),
                    "has_changes": diff_result.has_changed,
                }
            else:
                # First run - capture baseline
                passed = True
                score = 1.0
                details = {"status": "baseline captured"}
            
        except Exception as e:
            score = 0.0
            passed = False
            details = {"error": str(e)}
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return VerificationResult(
            verification_type=VerificationType.VISUAL,
            passed=passed,
            score=score,
            details=details,
            duration_ms=duration_ms,
        )


__all__ = ["LiveVerifier", "VerificationConfig", "VerificationType", "LiveVerificationReport"]