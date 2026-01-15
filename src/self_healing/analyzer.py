"""
Log Analyzer - Analyzes error logs and suggests fixes.
"""

from typing import List, Optional
from dataclasses import dataclass


@dataclass
class AnalysisResult:
    """Result of log analysis."""
    error_type: str
    suggestion: str
    confidence: float = 0.5


class SimpleLogAnalyzer:
    """
    매우 단순한 휴리스틱 분석기.
    나중에 LLM/Gemini 연동 시 이 클래스를 교체하거나 확장하면 된다.
    
    This analyzer uses simple pattern matching to detect common errors.
    In production, this would be replaced with an LLM-based analyzer
    (e.g., using Google Gemini API).
    """

    def analyze(self, logs: List[str]) -> Optional[AnalysisResult]:
        """
        Analyze logs and return suggestion if error detected.
        
        Args:
            logs: List of log message lines
            
        Returns:
            AnalysisResult if error detected, None otherwise
        """
        if not logs:
            return None
        
        text = "\n".join(logs).lower()

        # Import errors
        if "modulenotfounderror" in text or "importerror" in text:
            module_match = self._extract_module_name(text)
            return AnalysisResult(
                error_type="import_error",
                suggestion=f"Check imports and ensure the missing module '{module_match}' is installed. "
                          f"Verify PYTHONPATH includes src/ directory.",
                confidence=0.8
            )

        # Key errors
        if "keyerror" in text:
            key_match = self._extract_key_name(text)
            return AnalysisResult(
                error_type="key_error",
                suggestion=f"Guard dict access with dict.get() or ensure the key '{key_match}' exists "
                          f"in observation dictionary.",
                confidence=0.7
            )

        # Index errors
        if "indexerror" in text or "list index out of range" in text:
            return AnalysisResult(
                error_type="index_error",
                suggestion="Check list indices and lengths before indexing. "
                          "Use len() checks or try-except blocks.",
                confidence=0.7
            )

        # Type errors
        if "typeerror" in text:
            return AnalysisResult(
                error_type="type_error",
                suggestion="Check variable types and ensure correct type conversions. "
                          "Add type hints and type checking.",
                confidence=0.6
            )

        # Attribute errors
        if "attributeerror" in text:
            attr_match = self._extract_attribute_name(text)
            return AnalysisResult(
                error_type="attribute_error",
                suggestion=f"Check that object has attribute '{attr_match}'. "
                          f"Use hasattr() before accessing attributes.",
                confidence=0.7
            )

        # Assertion errors
        if "assertionerror" in text:
            return AnalysisResult(
                error_type="assertion_error",
                suggestion="Review test assertions and ensure test data is valid. "
                          "Check preconditions before assertions.",
                confidence=0.6
            )

        # Timeout errors
        if "timeout" in text or "timed out" in text:
            return AnalysisResult(
                error_type="timeout_error",
                suggestion="Increase timeout values or optimize slow operations. "
                          "Consider using async operations or parallel processing.",
                confidence=0.6
            )

        return None

    def _extract_module_name(self, text: str) -> str:
        """Extract module name from error message."""
        import re
        match = re.search(r"no module named ['\"]([^'\"]+)['\"]", text, re.IGNORECASE)
        return match.group(1) if match else "unknown"

    def _extract_key_name(self, text: str) -> str:
        """Extract key name from KeyError message."""
        import re
        match = re.search(r"keyerror: ['\"]([^'\"]+)['\"]", text, re.IGNORECASE)
        return match.group(1) if match else "unknown"

    def _extract_attribute_name(self, text: str) -> str:
        """Extract attribute name from AttributeError message."""
        import re
        match = re.search(r"attributeerror: .* has no attribute ['\"]([^'\"]+)['\"]", text, re.IGNORECASE)
        return match.group(1) if match else "unknown"
