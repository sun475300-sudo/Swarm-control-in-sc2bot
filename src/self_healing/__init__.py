"""
Self-Healing DevOps module.
Provides automated error detection, analysis, and patching capabilities.
"""

from .pipeline import SelfHealingPipeline
from .log_collector import LogCollector
from .analyzer import SimpleLogAnalyzer, AnalysisResult
from .patch_applier import PatchApplier

__all__ = [
    "SelfHealingPipeline",
    "LogCollector",
    "SimpleLogAnalyzer",
    "AnalysisResult",
    "PatchApplier",
]
