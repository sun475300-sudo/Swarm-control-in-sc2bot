"""
Patch Applier - Applies patch suggestions to code.
"""

from pathlib import Path
from datetime import datetime


class PatchApplier:
    """
    실제 코드에 '자동 패치'를 적용하는 대신,
    제안 내용을 patch_suggestions.txt 에 기록하는 안전한 버전.
    
    In production, this would apply actual code patches.
    For safety, this version only records suggestions.
    """

    def __init__(self, out_path: str = "patch_suggestions.txt") -> None:
        """
        Initialize PatchApplier.
        
        Args:
            out_path: Path to output file for patch suggestions
        """
        self.out_path = Path(out_path)

    def apply_suggestion(self, suggestion: str, error_type: str = "unknown") -> None:
        """
        Record patch suggestion to file.
        
        Args:
            suggestion: Patch suggestion text
            error_type: Type of error that triggered the suggestion
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"""
{'='*70}
Timestamp: {timestamp}
Error Type: {error_type}
{'='*70}
{suggestion}
{'='*70}

"""
        
        if self.out_path.exists():
            existing_content = self.out_path.read_text(encoding="utf-8")
            content = existing_content + content
        else:
            # Add header for new file
            header = f"""
# Self-Healing Patch Suggestions
# Generated automatically by SelfHealingPipeline
# Each suggestion represents a potential fix for detected errors

"""
            content = header + content
        
        self.out_path.write_text(content, encoding="utf-8")
