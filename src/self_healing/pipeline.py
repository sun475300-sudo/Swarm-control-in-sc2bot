"""
Self-Healing Pipeline - End-to-end automated error detection and patching.
"""

from .log_collector import LogCollector
from .analyzer import SimpleLogAnalyzer
from .patch_applier import PatchApplier
from typing import Optional
from .analyzer import AnalysisResult


class SelfHealingPipeline:
    """
    End-to-end pipeline: collect ¡æ analyze ¡æ record patch suggestion.
    
    This pipeline automates the process of:
    1. Collecting error logs
    2. Analyzing them for patterns
    3. Generating patch suggestions
    4. Recording suggestions for review/application
    """

    def __init__(self, log_dir: str = "logs", patch_file: str = "patch_suggestions.txt") -> None:
        """
        Initialize SelfHealingPipeline.
        
        Args:
            log_dir: Directory to collect logs from
            patch_file: File to write patch suggestions to
        """
        self.collector = LogCollector(log_dir=log_dir)
        self.analyzer = SimpleLogAnalyzer()
        self.applier = PatchApplier(out_path=patch_file)

    def run_once(self) -> bool:
        """
        Run one iteration of the self-healing pipeline.
        
        Returns:
            True if an issue was detected and suggestion generated, False otherwise
        """
        # Collect logs
        logs = self.collector.collect()
        if not logs:
            return False

        # Analyze logs
        result = self.analyzer.analyze(logs)
        if not result:
            return False

        # Apply suggestion (record to file)
        msg = f"[{result.error_type}] {result.suggestion}\nConfidence: {result.confidence:.1%}"
        self.applier.apply_suggestion(msg, error_type=result.error_type)
        
        return True

    def run_continuous(self, interval_seconds: int = 60, max_iterations: Optional[int] = None) -> None:
        """
        Run pipeline continuously at specified interval.
        
        Args:
            interval_seconds: Seconds between pipeline runs
            max_iterations: Maximum number of iterations (None for infinite)
        """
        import time
        
        iteration = 0
        while max_iterations is None or iteration < max_iterations:
            self.run_once()
            iteration += 1
            
            if max_iterations is None or iteration < max_iterations:
                time.sleep(interval_seconds)
