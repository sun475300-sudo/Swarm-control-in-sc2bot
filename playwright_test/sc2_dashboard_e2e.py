# playwright_test/sc2_dashboard_e2e.py
# Phase 599: Playwright — SC2 Dashboard End-to-End Testing
#
# Comprehensive E2E test suite for the SC2 Zerg bot web dashboard.
# Covers browser automation, network interception, visual regression,
# performance metrics (Core Web Vitals), and video recording.

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import statistics
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union

try:
    from playwright.sync_api import (
        Browser,
        BrowserContext,
        BrowserType,
        ElementHandle,
        Locator,
        Page,
        Playwright,
        Route,
        sync_playwright,
    )
except ImportError:
    sync_playwright = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "http://localhost:3000"
SCREENSHOTS_DIR = "test_artifacts/screenshots"
VIDEOS_DIR = "test_artifacts/videos"
TRACES_DIR = "test_artifacts/traces"
BASELINES_DIR = "test_artifacts/baselines"
DEFAULT_TIMEOUT_MS = 30_000
DEFAULT_VIEWPORT = {"width": 1920, "height": 1080}

# Mock API data
MOCK_GAME_STATE = {
    "minerals": 1250,
    "vespene": 680,
    "supply_used": 142,
    "supply_cap": 200,
    "workers": 66,
    "army_value": 4800,
    "enemy_army_value": 3200,
    "game_time_seconds": 720,
    "current_phase": "mid_game",
    "win_probability": 0.72,
}

MOCK_UNIT_COMPOSITION = {
    "zergling": 40,
    "baneling": 12,
    "roach": 18,
    "hydralisk": 10,
    "queen": 5,
    "overlord": 8,
    "drone": 66,
}

MOCK_BUILD_ORDER = [
    {"time": "0:00", "action": "Hatchery", "supply": "12/14"},
    {"time": "0:17", "action": "Drone x2", "supply": "12/14"},
    {"time": "0:50", "action": "Spawning Pool", "supply": "14/14"},
    {"time": "1:05", "action": "Extractor", "supply": "14/14"},
    {"time": "1:30", "action": "Hatchery (Natural)", "supply": "16/14"},
    {"time": "2:00", "action": "Queen x2", "supply": "20/22"},
    {"time": "2:30", "action": "Zergling Speed", "supply": "24/30"},
    {"time": "3:00", "action": "Roach Warren", "supply": "30/36"},
    {"time": "3:45", "action": "Lair", "supply": "44/44"},
    {"time": "4:30", "action": "Hydralisk Den", "supply": "60/66"},
]

MOCK_MATCH_HISTORY = [
    {"result": "win", "matchup": "ZvT", "duration": "12:34", "map": "Alcyone"},
    {"result": "win", "matchup": "ZvP", "duration": "15:02", "map": "Amphion"},
    {"result": "loss", "matchup": "ZvZ", "duration": "6:45", "map": "Crimson Court"},
    {"result": "win", "matchup": "ZvT", "duration": "18:20", "map": "Dynasty"},
    {"result": "win", "matchup": "ZvP", "duration": "11:55", "map": "Ghost River"},
]


# ---------------------------------------------------------------------------
# Enums & data classes
# ---------------------------------------------------------------------------


class BrowserKind(Enum):
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


@dataclass
class PerformanceMetrics:
    """Core Web Vitals and custom performance measurements."""

    lcp_ms: Optional[float] = None  # Largest Contentful Paint
    fid_ms: Optional[float] = None  # First Input Delay
    cls_score: Optional[float] = None  # Cumulative Layout Shift
    fcp_ms: Optional[float] = None  # First Contentful Paint
    ttfb_ms: Optional[float] = None  # Time to First Byte
    dom_content_loaded_ms: Optional[float] = None
    load_event_ms: Optional[float] = None
    total_js_heap_mb: Optional[float] = None

    def summary(self) -> str:
        parts = []
        if self.lcp_ms is not None:
            parts.append(f"LCP={self.lcp_ms:.0f}ms")
        if self.fid_ms is not None:
            parts.append(f"FID={self.fid_ms:.0f}ms")
        if self.cls_score is not None:
            parts.append(f"CLS={self.cls_score:.4f}")
        if self.fcp_ms is not None:
            parts.append(f"FCP={self.fcp_ms:.0f}ms")
        if self.ttfb_ms is not None:
            parts.append(f"TTFB={self.ttfb_ms:.0f}ms")
        return " | ".join(parts) if parts else "No metrics collected"

    def passes_thresholds(
        self,
        max_lcp_ms: float = 2500,
        max_fid_ms: float = 100,
        max_cls: float = 0.1,
    ) -> bool:
        """Check Google's Core Web Vitals 'good' thresholds."""
        if self.lcp_ms is not None and self.lcp_ms > max_lcp_ms:
            return False
        if self.fid_ms is not None and self.fid_ms > max_fid_ms:
            return False
        if self.cls_score is not None and self.cls_score > max_cls:
            return False
        return True


@dataclass
class VisualRegressionResult:
    page_name: str
    baseline_path: str
    current_path: str
    diff_pixels: int
    total_pixels: int
    diff_percentage: float
    passed: bool
    threshold: float

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (
            f"[{self.page_name}] {status} | "
            f"diff={self.diff_percentage:.2f}% ({self.diff_pixels}/{self.total_pixels} px) "
            f"threshold={self.threshold:.2f}%"
        )


@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: float
    error: Optional[str] = None
    screenshot_path: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSuiteResult:
    suite_name: str
    results: List[TestResult] = field(default_factory=list)
    total_duration_ms: float = 0.0

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def total(self) -> int:
        return len(self.results)

    def summary(self) -> str:
        return (
            f"Suite: {self.suite_name} | "
            f"{self.passed}/{self.total} passed, {self.failed} failed | "
            f"{self.total_duration_ms:.0f}ms"
        )


# ---------------------------------------------------------------------------
# Network interceptor
# ---------------------------------------------------------------------------


class SC2APIInterceptor:
    """Intercepts network requests and serves mock SC2 API responses."""

    def __init__(self) -> None:
        self._routes: Dict[str, Dict[str, Any]] = {}
        self._captured_requests: List[Dict[str, Any]] = []
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Pre-register common SC2 dashboard API endpoints."""
        self.mock_route(
            "/api/game/state",
            json_body=MOCK_GAME_STATE,
        )
        self.mock_route(
            "/api/game/units",
            json_body=MOCK_UNIT_COMPOSITION,
        )
        self.mock_route(
            "/api/game/build-order",
            json_body=MOCK_BUILD_ORDER,
        )
        self.mock_route(
            "/api/matches/history",
            json_body=MOCK_MATCH_HISTORY,
        )
        self.mock_route(
            "/api/bot/config",
            json_body={
                "race": "Zerg",
                "strategy": "adaptive",
                "aggression": 0.6,
                "expansion_priority": 0.8,
            },
        )
        self.mock_route(
            "/api/analytics/winrate",
            json_body={
                "overall": 0.68,
                "ZvT": 0.72,
                "ZvP": 0.65,
                "ZvZ": 0.61,
            },
        )

    def mock_route(
        self,
        url_pattern: str,
        json_body: Any = None,
        status: int = 200,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        delay_ms: int = 0,
    ) -> None:
        """Register a mock response for a URL pattern."""
        self._routes[url_pattern] = {
            "json_body": json_body,
            "body": body,
            "status": status,
            "headers": headers or {"Content-Type": "application/json"},
            "delay_ms": delay_ms,
        }

    def handle_route(self, route: Any) -> None:
        """Playwright route handler — intercepts matching requests."""
        request = route.request
        url = request.url

        self._captured_requests.append(
            {
                "url": url,
                "method": request.method,
                "timestamp": datetime.now().isoformat(),
            }
        )

        for pattern, response_cfg in self._routes.items():
            if pattern in url:
                if response_cfg["delay_ms"] > 0:
                    time.sleep(response_cfg["delay_ms"] / 1000.0)

                body = response_cfg["body"]
                if body is None and response_cfg["json_body"] is not None:
                    body = json.dumps(response_cfg["json_body"])

                route.fulfill(
                    status=response_cfg["status"],
                    headers=response_cfg["headers"],
                    body=body or "",
                )
                return

        # Pass through unmatched requests
        route.continue_()

    @property
    def captured_requests(self) -> List[Dict[str, Any]]:
        return list(self._captured_requests)

    def clear_captured(self) -> None:
        self._captured_requests.clear()


# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------


class DashboardAssertions:
    """Specialised assertion methods for SC2 dashboard elements."""

    def __init__(self, page: Any):
        self.page = page

    def assert_metric_value(
        self,
        selector: str,
        expected_value: str,
        timeout_ms: int = 5000,
    ) -> None:
        """Assert a dashboard metric displays the expected value."""
        locator = self.page.locator(selector)
        locator.wait_for(timeout=timeout_ms)
        actual = locator.text_content()
        assert actual is not None and expected_value in actual, (
            f"Metric mismatch at '{selector}': expected '{expected_value}' "
            f"in '{actual}'"
        )

    def assert_mineral_count(self, expected: int) -> None:
        self.assert_metric_value("[data-testid='minerals']", str(expected))

    def assert_vespene_count(self, expected: int) -> None:
        self.assert_metric_value("[data-testid='vespene']", str(expected))

    def assert_supply(self, used: int, cap: int) -> None:
        self.assert_metric_value("[data-testid='supply']", f"{used}/{cap}")

    def assert_win_probability(self, min_value: float = 0.0) -> None:
        """Assert win probability is rendered and above a minimum."""
        locator = self.page.locator("[data-testid='win-probability']")
        locator.wait_for(timeout=5000)
        text = locator.text_content() or ""
        # Extract numeric value (e.g., "72%" -> 0.72)
        numeric = text.replace("%", "").strip()
        try:
            value = float(numeric) / 100.0 if float(numeric) > 1 else float(numeric)
        except ValueError:
            raise AssertionError(f"Cannot parse win probability: '{text}'")
        assert (
            value >= min_value
        ), f"Win probability {value:.2f} below minimum {min_value:.2f}"

    def assert_unit_count(self, unit_name: str, expected: int) -> None:
        selector = f"[data-testid='unit-{unit_name.lower()}']"
        self.assert_metric_value(selector, str(expected))

    def assert_element_visible(self, selector: str, timeout_ms: int = 5000) -> None:
        locator = self.page.locator(selector)
        locator.wait_for(state="visible", timeout=timeout_ms)

    def assert_element_hidden(self, selector: str, timeout_ms: int = 5000) -> None:
        locator = self.page.locator(selector)
        locator.wait_for(state="hidden", timeout=timeout_ms)

    def assert_table_row_count(self, table_selector: str, expected_rows: int) -> None:
        rows = self.page.locator(f"{table_selector} tbody tr")
        actual = rows.count()
        assert (
            actual == expected_rows
        ), f"Table '{table_selector}' has {actual} rows, expected {expected_rows}"

    def assert_chart_rendered(self, chart_selector: str) -> None:
        """Assert a chart (canvas or SVG) has rendered within its container."""
        container = self.page.locator(chart_selector)
        container.wait_for(state="visible", timeout=5000)
        # Check for canvas or SVG child
        has_canvas = container.locator("canvas").count() > 0
        has_svg = container.locator("svg").count() > 0
        assert (
            has_canvas or has_svg
        ), f"No chart (canvas/svg) found in '{chart_selector}'"

    def assert_no_console_errors(self, errors: List[str]) -> None:
        """Assert no JavaScript errors were logged to console."""
        assert len(errors) == 0, f"Console errors detected: {errors}"


# ---------------------------------------------------------------------------
# SC2DashboardTest
# ---------------------------------------------------------------------------


class SC2DashboardTest:
    """End-to-end test framework for the SC2 Zerg bot web dashboard.

    Provides browser lifecycle management, network interception with
    mock API responses, screenshot comparison for visual regression,
    Core Web Vitals collection, and parallel-ready test execution.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        browser_kind: BrowserKind = BrowserKind.CHROMIUM,
        headless: bool = True,
        viewport: Optional[Dict[str, int]] = None,
        slow_mo: int = 0,
        record_video: bool = False,
        trace: bool = False,
        screenshot_on_failure: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.browser_kind = browser_kind
        self.headless = headless
        self.viewport = viewport or DEFAULT_VIEWPORT
        self.slow_mo = slow_mo
        self.record_video = record_video
        self.trace = trace
        self.screenshot_on_failure = screenshot_on_failure

        self._playwright: Optional[Any] = None
        self._browser: Optional[Any] = None
        self._context: Optional[Any] = None
        self._page: Optional[Any] = None

        self.interceptor = SC2APIInterceptor()
        self._console_errors: List[str] = []
        self._assertions: Optional[DashboardAssertions] = None

        # Ensure artifact directories exist
        for d in (SCREENSHOTS_DIR, VIDEOS_DIR, TRACES_DIR, BASELINES_DIR):
            Path(d).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Lifecycle (setup / teardown)
    # ------------------------------------------------------------------

    def setup(self) -> None:
        """Launch browser and create a fresh context + page."""
        if sync_playwright is None:
            raise RuntimeError(
                "Playwright is not installed. Run: pip install playwright && playwright install"
            )

        self._playwright = sync_playwright().start()
        browser_type: Any = getattr(self._playwright, self.browser_kind.value)

        self._browser = browser_type.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
        )

        context_kwargs: Dict[str, Any] = {
            "viewport": self.viewport,
            "ignore_https_errors": True,
            "user_agent": (
                "Mozilla/5.0 SC2DashboardTest/1.0 " "(Playwright; Zerg Bot QA)"
            ),
        }

        if self.record_video:
            context_kwargs["record_video_dir"] = VIDEOS_DIR
            context_kwargs["record_video_size"] = {
                "width": self.viewport["width"],
                "height": self.viewport["height"],
            }

        self._context = self._browser.new_context(**context_kwargs)

        if self.trace:
            self._context.tracing.start(screenshots=True, snapshots=True)

        self._page = self._context.new_page()
        self._page.set_default_timeout(DEFAULT_TIMEOUT_MS)

        # Capture console errors
        self._console_errors.clear()
        self._page.on(
            "console",
            lambda msg: (
                self._console_errors.append(msg.text) if msg.type == "error" else None
            ),
        )

        # Install network interceptor
        self._page.route("**/api/**", self.interceptor.handle_route)

        self._assertions = DashboardAssertions(self._page)
        logger.info(
            "Browser launched: %s (headless=%s)", self.browser_kind.value, self.headless
        )

    def teardown(self) -> None:
        """Close browser, save trace, and clean up."""
        if self.trace and self._context is not None:
            trace_path = os.path.join(
                TRACES_DIR,
                f"trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            )
            self._context.tracing.stop(path=trace_path)
            logger.info("Trace saved: %s", trace_path)

        if self._context is not None:
            self._context.close()
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()

        logger.info("Browser closed")

    @contextmanager
    def session(self) -> Generator["SC2DashboardTest", None, None]:
        """Context manager for automatic setup/teardown."""
        self.setup()
        try:
            yield self
        finally:
            self.teardown()

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    @property
    def page(self) -> Any:
        if self._page is None:
            raise RuntimeError("No page available. Call setup() first.")
        return self._page

    @property
    def assertions(self) -> DashboardAssertions:
        if self._assertions is None:
            raise RuntimeError("Assertions unavailable. Call setup() first.")
        return self._assertions

    @property
    def console_errors(self) -> List[str]:
        return list(self._console_errors)

    def navigate(self, path: str = "/", wait_until: str = "networkidle") -> None:
        """Navigate to a dashboard page and wait for it to settle."""
        url = f"{self.base_url}{path}"
        self.page.goto(url, wait_until=wait_until)
        logger.info("Navigated to %s", url)

    def navigate_and_wait_for_selector(
        self, path: str, selector: str, timeout_ms: int = DEFAULT_TIMEOUT_MS
    ) -> None:
        """Navigate and wait for a specific element to appear."""
        self.navigate(path, wait_until="domcontentloaded")
        self.page.wait_for_selector(selector, timeout=timeout_ms)

    def wait_for_api_response(
        self, url_pattern: str, timeout_ms: int = DEFAULT_TIMEOUT_MS
    ) -> Any:
        """Wait for a specific API call to complete and return the response."""
        with self.page.expect_response(
            lambda resp: url_pattern in resp.url, timeout=timeout_ms
        ) as response_info:
            pass
        return response_info.value

    # ------------------------------------------------------------------
    # Element interaction
    # ------------------------------------------------------------------

    def click(self, selector: str, **kwargs: Any) -> None:
        self.page.click(selector, **kwargs)

    def fill(self, selector: str, value: str) -> None:
        self.page.fill(selector, value)

    def select_option(self, selector: str, value: str) -> None:
        self.page.select_option(selector, value)

    def check(self, selector: str) -> None:
        self.page.check(selector)

    def uncheck(self, selector: str) -> None:
        self.page.uncheck(selector)

    def get_text(self, selector: str) -> str:
        return self.page.text_content(selector) or ""

    def get_attribute(self, selector: str, attr: str) -> Optional[str]:
        return self.page.get_attribute(selector, attr)

    def is_visible(self, selector: str) -> bool:
        return self.page.is_visible(selector)

    # ------------------------------------------------------------------
    # Selectors (CSS, XPath, text, role)
    # ------------------------------------------------------------------

    def by_css(self, css: str) -> Any:
        return self.page.locator(css)

    def by_xpath(self, xpath: str) -> Any:
        return self.page.locator(f"xpath={xpath}")

    def by_text(self, text: str, exact: bool = False) -> Any:
        return self.page.get_by_text(text, exact=exact)

    def by_role(self, role: str, **kwargs: Any) -> Any:
        return self.page.get_by_role(role, **kwargs)

    def by_test_id(self, test_id: str) -> Any:
        return self.page.get_by_test_id(test_id)

    def by_label(self, label: str) -> Any:
        return self.page.get_by_label(label)

    def by_placeholder(self, placeholder: str) -> Any:
        return self.page.get_by_placeholder(placeholder)

    # ------------------------------------------------------------------
    # Screenshot capture
    # ------------------------------------------------------------------

    def screenshot(
        self,
        name: str,
        full_page: bool = False,
        selector: Optional[str] = None,
    ) -> str:
        """Capture a screenshot and return the file path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = os.path.join(SCREENSHOTS_DIR, filename)

        if selector:
            self.page.locator(selector).screenshot(path=filepath)
        else:
            self.page.screenshot(path=filepath, full_page=full_page)

        logger.info("Screenshot saved: %s", filepath)
        return filepath

    def screenshot_on_fail(self, test_name: str) -> Optional[str]:
        """Capture a failure screenshot if configured to do so."""
        if not self.screenshot_on_failure:
            return None
        return self.screenshot(f"FAIL_{test_name}", full_page=True)

    # ------------------------------------------------------------------
    # Visual regression testing
    # ------------------------------------------------------------------

    def visual_compare(
        self,
        page_name: str,
        threshold_pct: float = 0.5,
        full_page: bool = True,
        selector: Optional[str] = None,
        update_baseline: bool = False,
    ) -> VisualRegressionResult:
        """Compare current page screenshot against a stored baseline.

        Parameters
        ----------
        page_name : str
            Identifier for the baseline image.
        threshold_pct : float
            Maximum allowed pixel difference percentage.
        update_baseline : bool
            When ``True``, save the current screenshot as the new baseline.
        """
        baseline_path = os.path.join(BASELINES_DIR, f"{page_name}.png")
        current_path = os.path.join(
            SCREENSHOTS_DIR,
            f"{page_name}_current_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
        )

        if selector:
            self.page.locator(selector).screenshot(path=current_path)
        else:
            self.page.screenshot(path=current_path, full_page=full_page)

        if update_baseline or not os.path.exists(baseline_path):
            shutil.copy2(current_path, baseline_path)
            logger.info("Baseline updated: %s", baseline_path)
            return VisualRegressionResult(
                page_name=page_name,
                baseline_path=baseline_path,
                current_path=current_path,
                diff_pixels=0,
                total_pixels=0,
                diff_percentage=0.0,
                passed=True,
                threshold=threshold_pct,
            )

        # Pixel-level comparison using raw bytes
        diff_pixels, total_pixels = self._compare_images(baseline_path, current_path)
        diff_pct = (diff_pixels / max(total_pixels, 1)) * 100.0

        result = VisualRegressionResult(
            page_name=page_name,
            baseline_path=baseline_path,
            current_path=current_path,
            diff_pixels=diff_pixels,
            total_pixels=total_pixels,
            diff_percentage=diff_pct,
            passed=diff_pct <= threshold_pct,
            threshold=threshold_pct,
        )
        logger.info("Visual regression: %s", result.summary())
        return result

    @staticmethod
    def _compare_images(path_a: str, path_b: str) -> Tuple[int, int]:
        """Compare two PNG files at the byte level.

        Returns ``(different_pixels, total_pixels)``.
        Uses a simple byte-hash comparison when PIL is unavailable,
        or per-pixel diff when PIL is installed.
        """
        try:
            from PIL import Image
            import numpy as np

            img_a = np.array(Image.open(path_a).convert("RGBA"))
            img_b = np.array(Image.open(path_b).convert("RGBA"))

            if img_a.shape != img_b.shape:
                # Sizes differ — treat everything as a diff
                total = max(
                    img_a.shape[0] * img_a.shape[1], img_b.shape[0] * img_b.shape[1]
                )
                return total, total

            diff = np.any(img_a != img_b, axis=-1)
            total = diff.size
            changed = int(diff.sum())
            return changed, total

        except ImportError:
            # Fallback: hash-based (all-or-nothing)
            hash_a = hashlib.md5(open(path_a, "rb").read()).hexdigest()
            hash_b = hashlib.md5(open(path_b, "rb").read()).hexdigest()
            size = os.path.getsize(path_a)
            if hash_a == hash_b:
                return 0, size
            return size, size

    # ------------------------------------------------------------------
    # Performance metrics (Core Web Vitals)
    # ------------------------------------------------------------------

    def collect_performance_metrics(self) -> PerformanceMetrics:
        """Collect Core Web Vitals and navigation timing from the page.

        Uses the Performance API and PerformanceObserver results injected
        via JavaScript evaluation.
        """
        metrics = PerformanceMetrics()

        # Navigation timing
        nav_timing = self.page.evaluate(
            """() => {
            const nav = performance.getEntriesByType('navigation')[0];
            if (!nav) return null;
            return {
                ttfb: nav.responseStart - nav.requestStart,
                domContentLoaded: nav.domContentLoadedEventEnd - nav.startTime,
                loadEvent: nav.loadEventEnd - nav.startTime,
            };
        }"""
        )
        if nav_timing:
            metrics.ttfb_ms = nav_timing.get("ttfb")
            metrics.dom_content_loaded_ms = nav_timing.get("domContentLoaded")
            metrics.load_event_ms = nav_timing.get("loadEvent")

        # Paint timing (FCP)
        fcp = self.page.evaluate(
            """() => {
            const entries = performance.getEntriesByName('first-contentful-paint');
            return entries.length > 0 ? entries[0].startTime : null;
        }"""
        )
        if fcp is not None:
            metrics.fcp_ms = fcp

        # LCP (via PerformanceObserver — must be injected before navigation
        # for accurate results; here we try post-hoc)
        lcp = self.page.evaluate(
            """() => {
            return new Promise((resolve) => {
                new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    resolve(entries.length > 0
                        ? entries[entries.length - 1].startTime
                        : null);
                }).observe({type: 'largest-contentful-paint', buffered: true});
                setTimeout(() => resolve(null), 3000);
            });
        }"""
        )
        if lcp is not None:
            metrics.lcp_ms = lcp

        # CLS
        cls_score = self.page.evaluate(
            """() => {
            return new Promise((resolve) => {
                let cls = 0;
                new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        if (!entry.hadRecentInput) cls += entry.value;
                    }
                    resolve(cls);
                }).observe({type: 'layout-shift', buffered: true});
                setTimeout(() => resolve(cls), 3000);
            });
        }"""
        )
        if cls_score is not None:
            metrics.cls_score = cls_score

        # JS heap (Chromium only)
        heap = self.page.evaluate(
            """() => {
            if (performance.memory) {
                return performance.memory.totalJSHeapSize / (1024 * 1024);
            }
            return null;
        }"""
        )
        if heap is not None:
            metrics.total_js_heap_mb = heap

        logger.info("Performance: %s", metrics.summary())
        return metrics

    def inject_web_vitals_observer(self) -> None:
        """Inject PerformanceObserver scripts *before* page load for
        accurate LCP/FID/CLS measurement."""
        self.page.add_init_script(
            """
            window.__sc2_vitals = {lcp: 0, fid: 0, cls: 0};

            new PerformanceObserver((list) => {
                const entries = list.getEntries();
                if (entries.length > 0) {
                    window.__sc2_vitals.lcp = entries[entries.length - 1].startTime;
                }
            }).observe({type: 'largest-contentful-paint', buffered: true});

            new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    window.__sc2_vitals.fid = entry.processingStart - entry.startTime;
                    break;
                }
            }).observe({type: 'first-input', buffered: true});

            new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    if (!entry.hadRecentInput) {
                        window.__sc2_vitals.cls += entry.value;
                    }
                }
            }).observe({type: 'layout-shift', buffered: true});
        """
        )

    def read_injected_vitals(self) -> PerformanceMetrics:
        """Read metrics from the pre-injected observer."""
        vitals = self.page.evaluate("() => window.__sc2_vitals || {}")
        return PerformanceMetrics(
            lcp_ms=vitals.get("lcp"),
            fid_ms=vitals.get("fid"),
            cls_score=vitals.get("cls"),
        )

    # ------------------------------------------------------------------
    # Form interaction helpers
    # ------------------------------------------------------------------

    def fill_bot_config_form(
        self,
        strategy: str = "adaptive",
        aggression: float = 0.6,
        expansion_priority: float = 0.8,
    ) -> None:
        """Fill out the bot configuration form on the settings page."""
        self.navigate("/settings")
        self.select_option("[data-testid='strategy-select']", strategy)
        self.fill("[data-testid='aggression-input']", str(aggression))
        self.fill("[data-testid='expansion-input']", str(expansion_priority))
        self.click("[data-testid='save-config-btn']")
        self.page.wait_for_selector("[data-testid='save-success']", timeout=5000)

    def search_replays(self, query: str) -> int:
        """Use the replay search box and return the number of results."""
        self.fill("[data-testid='replay-search']", query)
        self.page.keyboard.press("Enter")
        self.page.wait_for_selector("[data-testid='replay-results']", timeout=5000)
        return self.page.locator("[data-testid='replay-result-row']").count()

    # ------------------------------------------------------------------
    # Test runner
    # ------------------------------------------------------------------

    def run_test(
        self, name: str, test_fn: Callable[["SC2DashboardTest"], None]
    ) -> TestResult:
        """Execute a single test function with timing and error capture."""
        start = time.perf_counter()
        screenshot_path = None
        error = None
        passed = True

        try:
            test_fn(self)
        except Exception as exc:
            passed = False
            error = str(exc)
            logger.error("Test '%s' FAILED: %s", name, exc)
            screenshot_path = self.screenshot_on_fail(name)

        duration = (time.perf_counter() - start) * 1000.0
        result = TestResult(
            name=name,
            passed=passed,
            duration_ms=duration,
            error=error,
            screenshot_path=screenshot_path,
        )
        status = "PASS" if passed else "FAIL"
        logger.info("[%s] %s (%.0f ms)", status, name, duration)
        return result

    def run_suite(
        self,
        suite_name: str,
        tests: List[Tuple[str, Callable[["SC2DashboardTest"], None]]],
    ) -> TestSuiteResult:
        """Run a list of ``(name, fn)`` tests and aggregate results."""
        suite_result = TestSuiteResult(suite_name=suite_name)
        suite_start = time.perf_counter()

        for name, fn in tests:
            result = self.run_test(name, fn)
            suite_result.results.append(result)

        suite_result.total_duration_ms = (time.perf_counter() - suite_start) * 1000.0
        logger.info("Suite complete: %s", suite_result.summary())
        return suite_result

    # ------------------------------------------------------------------
    # Parallel execution helper
    # ------------------------------------------------------------------

    @staticmethod
    def run_parallel(
        tests: List[Tuple[str, Callable[["SC2DashboardTest"], None]]],
        browsers: Optional[List[BrowserKind]] = None,
        base_url: str = DEFAULT_BASE_URL,
        max_workers: int = 4,
    ) -> Dict[str, TestSuiteResult]:
        """Execute test suites in parallel across multiple browsers.

        Each browser kind gets its own process via ``concurrent.futures``.
        """
        from concurrent.futures import ProcessPoolExecutor, as_completed

        if browsers is None:
            browsers = [BrowserKind.CHROMIUM]

        results: Dict[str, TestSuiteResult] = {}

        def _run_in_browser(
            browser_kind: BrowserKind,
        ) -> Tuple[str, TestSuiteResult]:
            tester = SC2DashboardTest(
                base_url=base_url,
                browser_kind=browser_kind,
                headless=True,
            )
            with tester.session():
                suite = tester.run_suite(f"E2E ({browser_kind.value})", tests)
            return browser_kind.value, suite

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_run_in_browser, bk): bk for bk in browsers}
            for future in as_completed(futures):
                try:
                    browser_name, suite = future.result()
                    results[browser_name] = suite
                except Exception as exc:
                    bk = futures[future]
                    logger.error("Parallel run failed for %s: %s", bk.value, exc)

        return results


# ---------------------------------------------------------------------------
# Predefined test cases
# ---------------------------------------------------------------------------


def test_dashboard_loads(t: SC2DashboardTest) -> None:
    """Verify the main dashboard page loads and renders key elements."""
    t.navigate("/")
    t.assertions.assert_element_visible("[data-testid='dashboard-header']")
    t.assertions.assert_element_visible("[data-testid='resource-panel']")
    t.assertions.assert_element_visible("[data-testid='minimap']")


def test_resource_display(t: SC2DashboardTest) -> None:
    """Verify mineral and vespene counts render from mocked API data."""
    t.navigate("/")
    t.assertions.assert_mineral_count(MOCK_GAME_STATE["minerals"])
    t.assertions.assert_vespene_count(MOCK_GAME_STATE["vespene"])
    t.assertions.assert_supply(
        MOCK_GAME_STATE["supply_used"], MOCK_GAME_STATE["supply_cap"]
    )


def test_unit_composition_table(t: SC2DashboardTest) -> None:
    """Verify the unit composition table shows all expected units."""
    t.navigate("/units")
    t.assertions.assert_table_row_count(
        "[data-testid='unit-table']", len(MOCK_UNIT_COMPOSITION)
    )
    for unit, count in MOCK_UNIT_COMPOSITION.items():
        t.assertions.assert_unit_count(unit, count)


def test_build_order_timeline(t: SC2DashboardTest) -> None:
    """Verify the build order timeline renders all entries."""
    t.navigate("/build-order")
    t.assertions.assert_element_visible("[data-testid='build-timeline']")
    entries = t.page.locator("[data-testid='build-entry']")
    assert entries.count() == len(
        MOCK_BUILD_ORDER
    ), f"Expected {len(MOCK_BUILD_ORDER)} build entries, got {entries.count()}"


def test_match_history(t: SC2DashboardTest) -> None:
    """Verify match history page lists all recent games."""
    t.navigate("/matches")
    rows = t.page.locator("[data-testid='match-row']")
    assert rows.count() == len(MOCK_MATCH_HISTORY)


def test_win_probability_widget(t: SC2DashboardTest) -> None:
    """Verify the win probability widget renders and shows a value."""
    t.navigate("/")
    t.assertions.assert_win_probability(min_value=0.5)


def test_settings_form(t: SC2DashboardTest) -> None:
    """Test bot configuration form submission."""
    t.fill_bot_config_form(
        strategy="rush",
        aggression=0.9,
        expansion_priority=0.3,
    )
    # Verify saved confirmation
    t.assertions.assert_element_visible("[data-testid='save-success']")


def test_navigation_links(t: SC2DashboardTest) -> None:
    """Test that all navigation links work correctly."""
    pages = [
        ("/", "[data-testid='dashboard-header']"),
        ("/units", "[data-testid='unit-table']"),
        ("/build-order", "[data-testid='build-timeline']"),
        ("/matches", "[data-testid='match-row']"),
        ("/settings", "[data-testid='strategy-select']"),
        ("/analytics", "[data-testid='winrate-chart']"),
    ]
    for path, selector in pages:
        t.navigate_and_wait_for_selector(path, selector)


def test_api_error_handling(t: SC2DashboardTest) -> None:
    """Verify the dashboard handles API errors gracefully."""
    t.interceptor.mock_route(
        "/api/game/state", json_body={"error": "Service unavailable"}, status=503
    )
    t.navigate("/")
    t.assertions.assert_element_visible("[data-testid='error-banner']")


def test_performance_thresholds(t: SC2DashboardTest) -> None:
    """Verify the dashboard meets Core Web Vitals thresholds."""
    t.inject_web_vitals_observer()
    t.navigate("/")
    # Allow time for layout to stabilise
    t.page.wait_for_timeout(2000)
    metrics = t.collect_performance_metrics()
    assert (
        metrics.passes_thresholds()
    ), f"Performance thresholds not met: {metrics.summary()}"


def test_visual_regression_home(t: SC2DashboardTest) -> None:
    """Visual regression check for the home dashboard."""
    t.navigate("/")
    result = t.visual_compare("home_dashboard", threshold_pct=1.0)
    assert result.passed, f"Visual regression failed: {result.summary()}"


def test_no_console_errors(t: SC2DashboardTest) -> None:
    """Ensure no JavaScript console errors during a full navigation cycle."""
    for path in ("/", "/units", "/build-order", "/matches", "/analytics"):
        t.navigate(path)
        t.page.wait_for_timeout(500)
    t.assertions.assert_no_console_errors(t.console_errors)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

ALL_TESTS: List[Tuple[str, Callable[[SC2DashboardTest], None]]] = [
    ("dashboard_loads", test_dashboard_loads),
    ("resource_display", test_resource_display),
    ("unit_composition_table", test_unit_composition_table),
    ("build_order_timeline", test_build_order_timeline),
    ("match_history", test_match_history),
    ("win_probability_widget", test_win_probability_widget),
    ("settings_form", test_settings_form),
    ("navigation_links", test_navigation_links),
    ("api_error_handling", test_api_error_handling),
    ("performance_thresholds", test_performance_thresholds),
    ("visual_regression_home", test_visual_regression_home),
    ("no_console_errors", test_no_console_errors),
]


def main() -> None:
    """Run the full E2E test suite against the SC2 dashboard."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    import argparse

    parser = argparse.ArgumentParser(description="SC2 Dashboard E2E Tests")
    parser.add_argument(
        "--base-url", default=DEFAULT_BASE_URL, help="Dashboard base URL"
    )
    parser.add_argument(
        "--browser",
        choices=["chromium", "firefox", "webkit"],
        default="chromium",
        help="Browser engine",
    )
    parser.add_argument(
        "--headed", action="store_true", help="Run with visible browser"
    )
    parser.add_argument(
        "--video", action="store_true", help="Record video of test runs"
    )
    parser.add_argument("--trace", action="store_true", help="Capture Playwright trace")
    parser.add_argument("--slow-mo", type=int, default=0, help="Slow down actions (ms)")
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run across all browsers in parallel",
    )
    parser.add_argument(
        "--test",
        type=str,
        default=None,
        help="Run a single test by name",
    )
    parser.add_argument(
        "--update-baselines",
        action="store_true",
        help="Update visual regression baselines",
    )
    args = parser.parse_args()

    browser_kind = BrowserKind(args.browser)

    if args.parallel:
        results = SC2DashboardTest.run_parallel(
            ALL_TESTS,
            browsers=[BrowserKind.CHROMIUM, BrowserKind.FIREFOX, BrowserKind.WEBKIT],
            base_url=args.base_url,
        )
        print("\n=== Parallel Results ===")
        for browser_name, suite in results.items():
            print(f"  {suite.summary()}")
        return

    # Filter tests if --test is specified
    tests_to_run = ALL_TESTS
    if args.test:
        tests_to_run = [(n, f) for n, f in ALL_TESTS if args.test in n]
        if not tests_to_run:
            print(f"No test matching '{args.test}' found.")
            return

    tester = SC2DashboardTest(
        base_url=args.base_url,
        browser_kind=browser_kind,
        headless=not args.headed,
        slow_mo=args.slow_mo,
        record_video=args.video,
        trace=args.trace,
    )

    with tester.session():
        suite = tester.run_suite("SC2 Dashboard E2E", tests_to_run)

    print(f"\n{'=' * 60}")
    print(f"  {suite.summary()}")
    print(f"{'=' * 60}")
    for r in suite.results:
        status = "PASS" if r.passed else "FAIL"
        line = f"  [{status}] {r.name} ({r.duration_ms:.0f}ms)"
        if r.error:
            line += f" -- {r.error[:80]}"
        if r.screenshot_path:
            line += f" [screenshot: {r.screenshot_path}]"
        print(line)
    print()

    # Exit with non-zero if any test failed
    if suite.failed > 0:
        exit(1)


if __name__ == "__main__":
    main()
