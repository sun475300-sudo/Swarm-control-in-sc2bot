"""
Self-healing pipeline tests.
"""

from pathlib import Path
import tempfile
import shutil

from src.self_healing.pipeline import SelfHealingPipeline
from src.self_healing.log_collector import LogCollector
from src.self_healing.analyzer import SimpleLogAnalyzer


def test_self_healing_pipeline_with_error(tmp_path):
    """Test self-healing pipeline with error log."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    
    # Create error log
    log_file = log_dir / "error.log"
    log_file.write_text("ModuleNotFoundError: No module named 'foo'", encoding="utf-8")
    
    # Create pipeline with temp directory
    pipeline = SelfHealingPipeline(log_dir=str(log_dir), patch_file=str(tmp_path / "patches.txt"))
    
    # Run pipeline
    result = pipeline.run_once()
    assert result is True
    
    # Check that patch file was created
    patch_file = tmp_path / "patches.txt"
    assert patch_file.exists()
    
    # Check content
    content = patch_file.read_text(encoding="utf-8")
    assert "import_error" in content.lower()
    assert "foo" in content.lower()


def test_log_collector_empty():
    """Test log collector with no logs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        collector = LogCollector(log_dir=tmpdir)
        logs = collector.collect()
        assert logs == []


def test_log_analyzer_no_error():
    """Test log analyzer with no errors."""
    analyzer = SimpleLogAnalyzer()
    result = analyzer.analyze(["Normal log message", "Another normal message"])
    assert result is None


def test_log_analyzer_key_error():
    """Test log analyzer with KeyError."""
    analyzer = SimpleLogAnalyzer()
    logs = [
        "Traceback (most recent call last):",
        '  File "test.py", line 1, in <module>',
        "    data['missing_key']",
        "KeyError: 'missing_key'"
    ]
    result = analyzer.analyze(logs)
    assert result is not None
    assert result.error_type == "key_error"
    assert "missing_key" in result.suggestion.lower()


def test_log_analyzer_import_error():
    """Test log analyzer with ImportError."""
    analyzer = SimpleLogAnalyzer()
    logs = [
        "ModuleNotFoundError: No module named 'test_module'"
    ]
    result = analyzer.analyze(logs)
    assert result is not None
    assert result.error_type == "import_error"
    assert "test_module" in result.suggestion
