# -*- coding: utf-8 -*-
"""
Extract and Train from Training Data

게임 훈련 종료 후 데이터를 추출하고 학습하는 스크립트입니다.
- training_stats.json에서 게임 결과 추출
- build_order_comparison_history.json에서 빌드 오더 추출
- 추출된 데이터를 기반으로 학습 파라미터 업데이트
"""

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import statistics

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
 sys.path.insert(0, str(script_dir))

try:
except ImportError as e:
    print(f"[WARNING] Failed to import required modules: {e}")
 BuildOrderComparator = None
 TrainingSessionManager = None


class TrainingDataExtractor:
    """훈련 데이터 추출 및 학습 클래스"""
 
 def __init__(self, base_dir: Optional[Path] = None):
        """
 Initialize TrainingDataExtractor
 
 Args:
 base_dir: Base directory for training data (default: auto-detect)
        """
 if base_dir is None:
 base_dir = Path(__file__).parent.parent
 
 self.base_dir = base_dir
 
 # Training data paths
        self.training_stats_path = base_dir / "data" / "training_stats.json"
 if not self.training_stats_path.exists():
            self.training_stats_path = base_dir / "training_stats.json"
 
        self.comparison_history_path = base_dir / "local_training" / "scripts" / "build_order_comparison_history.json"
        self.session_stats_path = base_dir / "local_training" / "scripts" / "training_session_stats.json"
        self.learned_build_orders_path = base_dir / "local_training" / "scripts" / "learned_build_orders.json"
 
 # Output directory for extracted data
        self.output_dir = base_dir / "local_training" / "extracted_data"
 self.output_dir.mkdir(parents=True, exist_ok=True)
 
        print(f"[EXTRACTOR] Initialized")
        print(f"[EXTRACTOR] Base directory: {self.base_dir}")
        print(f"[EXTRACTOR] Output directory: {self.output_dir}")
 
 def extract_training_stats(self) -> List[Dict[str, Any]]:
        """Extract training statistics from training_stats.json"""
 if not self.training_stats_path.exists():
            print(f"[WARNING] Training stats file not found: {self.training_stats_path}")
 return []
 
 training_data = []
 try:
 # training_stats.json is in JSONL format (one JSON object per line)
            with open(self.training_stats_path, 'r', encoding='utf-8', errors='ignore') as f:
 for line_num, line in enumerate(f, 1):
 line = line.strip()
 if not line:
 continue
 try:
 obj = json.loads(line)
 training_data.append(obj)
 except json.JSONDecodeError as e:
                        print(f"[WARNING] Failed to parse line {line_num}: {e}")
 continue
 
            print(f"[EXTRACTOR] Extracted {len(training_data)} training records")
 return training_data
 except Exception as e:
            print(f"[ERROR] Failed to extract training stats: {e}")
 return []
 
 def extract_build_order_comparisons(self) -> List[Dict[str, Any]]:
        """Extract build order comparisons from comparison history"""
 if not self.comparison_history_path.exists():
            print(f"[WARNING] Comparison history file not found: {self.comparison_history_path}")
 return []
 
 try:
            with open(self.comparison_history_path, 'r', encoding='utf-8') as f:
 data = json.load(f)
 
            comparisons = data.get("comparisons", [])
            print(f"[EXTRACTOR] Extracted {len(comparisons)} build order comparisons")
 return comparisons
 except Exception as e:
            print(f"[ERROR] Failed to extract build order comparisons: {e}")
 return []
 
 def extract_session_stats(self) -> Optional[Dict[str, Any]]:
        """Extract session statistics"""
 if not self.session_stats_path.exists():
            print(f"[WARNING] Session stats file not found: {self.session_stats_path}")
 return None
 
 try:
            with open(self.session_stats_path, 'r', encoding='utf-8') as f:
 data = json.load(f)
 
            print(f"[EXTRACTOR] Extracted session statistics")
 return data
 except Exception as e:
            print(f"[ERROR] Failed to extract session stats: {e}")
 return None
 
 def analyze_training_data(self, training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze extracted training data"""
 if not training_data:
 return {}
 
 analysis = {
            "total_games": len(training_data),
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "avg_game_time": 0.0,
            "build_order_scores": [],
            "loss_reasons": defaultdict(int),
            "by_opponent_race": defaultdict(lambda: {"wins": 0, "losses": 0}),
            "by_personality": defaultdict(lambda: {"wins": 0, "losses": 0}),
            "build_order_timings": defaultdict(list)
 }
 
 total_time = 0.0
 
 for record in training_data:
            result = record.get("result", "").lower()
            if "victory" in result:
                analysis["wins"] += 1
 else:
                analysis["losses"] += 1
 
            game_time = record.get("game_time", 0)
 total_time += game_time
 
 # Build order score
            if "build_order_score" in record:
                score = record.get("build_order_score")
 if score is not None:
                    analysis["build_order_scores"].append(score)
 
 # Loss reasons
            loss_reason = record.get("loss_reason", "UNKNOWN")
 if loss_reason:
                analysis["loss_reasons"][loss_reason] += 1
 
 # By opponent race
            opponent_race = record.get("opponent_race", "Unknown")
            if "victory" in result:
                analysis["by_opponent_race"][opponent_race]["wins"] += 1
 else:
                analysis["by_opponent_race"][opponent_race]["losses"] += 1
 
 # By personality
            personality = record.get("personality", "unknown")
            if "victory" in result:
                analysis["by_personality"][personality]["wins"] += 1
 else:
                analysis["by_personality"][personality]["losses"] += 1
 
 # Calculate statistics
        analysis["win_rate"] = (analysis["wins"] / analysis["total_games"] * 100) if analysis["total_games"] > 0 else 0.0
        analysis["avg_game_time"] = total_time / analysis["total_games"] if analysis["total_games"] > 0 else 0.0
 
        if analysis["build_order_scores"]:
            analysis["avg_build_order_score"] = statistics.mean(analysis["build_order_scores"])
            analysis["median_build_order_score"] = statistics.median(analysis["build_order_scores"])
 else:
            analysis["avg_build_order_score"] = 0.0
            analysis["median_build_order_score"] = 0.0
 
 return analysis
 
 def extract_build_order_timings(self, comparisons: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        """Extract build order timings from comparisons"""
 timings = defaultdict(list)
 
 for comp in comparisons:
            if "comparisons" not in comp:
 continue
 
            for param_comp in comp.get("comparisons", []):
                param_name = param_comp.get("parameter_name")
                training_supply = param_comp.get("training_supply")
 
 if param_name and training_supply is not None:
 timings[param_name].append(training_supply)
 
 return dict(timings)
 
 def learn_from_training_data(
 self,
 training_data: List[Dict[str, Any]],
 comparisons: List[Dict[str, Any]],
 learning_rate: float = 0.1
 ) -> Dict[str, float]:
        """
 Learn optimal parameters from training data
 
 Args:
 training_data: Extracted training statistics
 comparisons: Build order comparisons
 learning_rate: Learning rate for parameter updates
 
 Returns:
 Updated learned parameters
        """
 if not self.learned_build_orders_path.exists():
            print(f"[WARNING] Learned build orders file not found: {self.learned_build_orders_path}")
 return {}
 
 # Load current learned parameters
 try:
            with open(self.learned_build_orders_path, 'r', encoding='utf-8') as f:
 current_params = json.load(f)
 except Exception as e:
            print(f"[WARNING] Failed to load current parameters: {e}")
 current_params = {}
 
 # Extract successful build order timings (victories only)
 victory_timings = defaultdict(list)
 
 for comp in comparisons:
            game_result = comp.get("game_result", "").lower()
            if "victory" not in game_result:
 continue
 
            if "comparisons" not in comp:
 continue
 
            for param_comp in comp.get("comparisons", []):
                param_name = param_comp.get("parameter_name")
                training_supply = param_comp.get("training_supply")
 
 if param_name and training_supply is not None:
 # Only include if timing is reasonable (within 2 supply of pro baseline)
                    pro_supply = param_comp.get("pro_supply")
 if pro_supply is not None:
 diff = abs(training_supply - pro_supply)
 if diff <= 2:
 victory_timings[param_name].append(training_supply)
 else:
 victory_timings[param_name].append(training_supply)
 
 # Update parameters based on successful timings
 updated_params = current_params.copy()
 
 for param_name, timings in victory_timings.items():
 if not timings:
 continue
 
 # Use median of successful timings
 median_timing = statistics.median(timings)
 current_value = current_params.get(param_name, median_timing)
 
 # Update with learning rate
 new_value = current_value + (median_timing - current_value) * learning_rate
 updated_params[param_name] = max(6.0, new_value) # Minimum supply 6
 
 return updated_params
 
 def save_extracted_data(
 self,
 training_data: List[Dict[str, Any]],
 comparisons: List[Dict[str, Any]],
 analysis: Dict[str, Any],
 learned_params: Dict[str, float]
 ) -> None:
        """Save extracted data to output directory"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
 
 # Save training data
        training_data_file = self.output_dir / f"training_data_{timestamp}.json"
        with open(training_data_file, 'w', encoding='utf-8') as f:
 json.dump(training_data, f, indent=2, ensure_ascii=False)
        print(f"[SAVED] Training data: {training_data_file}")
 
 # Save comparisons
        comparisons_file = self.output_dir / f"comparisons_{timestamp}.json"
        with open(comparisons_file, 'w', encoding='utf-8') as f:
 json.dump(comparisons, f, indent=2, ensure_ascii=False)
        print(f"[SAVED] Comparisons: {comparisons_file}")
 
 # Save analysis
        analysis_file = self.output_dir / f"analysis_{timestamp}.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
 json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"[SAVED] Analysis: {analysis_file}")
 
 # Save learned parameters
 if learned_params:
            learned_params_file = self.output_dir / f"learned_params_{timestamp}.json"
            with open(learned_params_file, 'w', encoding='utf-8') as f:
 json.dump(learned_params, f, indent=2, ensure_ascii=False)
            print(f"[SAVED] Learned parameters: {learned_params_file}")
 
 def generate_report(
 self,
 analysis: Dict[str, Any],
 learned_params: Dict[str, float]
 ) -> str:
        """Generate human-readable report"""
 report_parts = []
 
        report_parts.append("=" * 70)
        report_parts.append("TRAINING DATA EXTRACTION AND LEARNING REPORT")
        report_parts.append("=" * 70)
        report_parts.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_parts.append("")
 
 # Training statistics
        report_parts.append("TRAINING STATISTICS:")
        report_parts.append("-" * 70)
        report_parts.append(f"Total Games: {analysis.get('total_games', 0)}")
        report_parts.append(f"Wins: {analysis.get('wins', 0)}")
        report_parts.append(f"Losses: {analysis.get('losses', 0)}")
        report_parts.append(f"Win Rate: {analysis.get('win_rate', 0.0):.2f}%")
        report_parts.append(f"Average Game Time: {analysis.get('avg_game_time', 0.0):.1f}s")
 
        if analysis.get('build_order_scores'):
            report_parts.append(f"Average Build Order Score: {analysis.get('avg_build_order_score', 0.0):.2%}")
            report_parts.append(f"Median Build Order Score: {analysis.get('median_build_order_score', 0.0):.2%}")
 
        report_parts.append("")
 
 # Top loss reasons
        loss_reasons = analysis.get('loss_reasons', {})
 if loss_reasons:
            report_parts.append("TOP LOSS REASONS:")
            report_parts.append("-" * 70)
 for reason, count in sorted(loss_reasons.items(), key=lambda x: x[1], reverse=True)[:10]:
                report_parts.append(f"  {reason}: {count}")
            report_parts.append("")
 
 # By opponent race
        by_race = analysis.get('by_opponent_race', {})
 if by_race:
            report_parts.append("PERFORMANCE BY OPPONENT RACE:")
            report_parts.append("-" * 70)
 for race, stats in sorted(by_race.items()):
                wins = stats.get('wins', 0)
                losses = stats.get('losses', 0)
 total = wins + losses
 win_rate = (wins / total * 100) if total > 0 else 0.0
                report_parts.append(f"  {race}: {wins}W / {losses}L ({win_rate:.1f}%)")
            report_parts.append("")
 
 # Learned parameters
 if learned_params:
            report_parts.append("LEARNED PARAMETERS:")
            report_parts.append("-" * 70)
 for param_name, value in sorted(learned_params.items()):
                report_parts.append(f"  {param_name}: {value:.1f} supply")
            report_parts.append("")
 
        report_parts.append("=" * 70)
 
        return "\n".join(report_parts)


def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("TRAINING DATA EXTRACTION AND LEARNING")
    print("=" * 70)
 print()
 
 extractor = TrainingDataExtractor()
 
 # Extract data
    print("[STEP 1] Extracting training data...")
 training_data = extractor.extract_training_stats()
 comparisons = extractor.extract_build_order_comparisons()
 session_stats = extractor.extract_session_stats()
 
 if not training_data and not comparisons:
        print("[ERROR] No training data found. Please run training first.")
 return
 
 # Analyze data
    print("\n[STEP 2] Analyzing training data...")
 analysis = extractor.analyze_training_data(training_data)
 
 # Learn from data
    print("\n[STEP 3] Learning from training data...")
 learned_params = extractor.learn_from_training_data(
 training_data,
 comparisons,
 learning_rate=0.1
 )
 
 # Save extracted data
    print("\n[STEP 4] Saving extracted data...")
 extractor.save_extracted_data(
 training_data,
 comparisons,
 analysis,
 learned_params
 )
 
 # Generate and print report
    print("\n[STEP 5] Generating report...")
 report = extractor.generate_report(analysis, learned_params)
    print("\n" + report)
 
 # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = extractor.output_dir / f"report_{timestamp}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
 f.write(report)
    print(f"\n[SAVED] Report: {report_file}")
 
    print("\n" + "=" * 70)
    print("EXTRACTION AND LEARNING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
 main()