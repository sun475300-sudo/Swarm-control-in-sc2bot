# -*- coding: utf-8 -*-
"""
게임 성능 최적화 도구

실제 코드를 수정하여 게임 성능을 개선
"""

import re

PROJECT_ROOT = Path(__file__).parent.parent


class GamePerformanceOptimizer:
    """게임 성능 최적화기"""
 
 def optimize_execution_frequency(self, content: str, file_path: Path) -> Tuple[str, int]:
        """실행 주기 최적화"""
 lines = content.splitlines()
 modified_lines = []
 fix_count = 0
 
 for i, line in enumerate(lines):
 # iteration % N == 0 패턴 찾기
 # 너무 자주 실행되는 것들을 줄임
            if re.search(r'iteration\s*%\s*[1-3]\s*==\s*0', line):
 # 1-3프레임마다 실행되는 것을 4-8프레임으로 변경
 new_line = re.sub(
                    r'iteration\s*%\s*([1-3])\s*==\s*0',
                    lambda m: f'iteration % {int(m.group(1)) * 4} == 0',
 line
 )
 if new_line != line:
 modified_lines.append(new_line)
 fix_count += 1
 continue
 
 # 4프레임마다 실행되는 것을 8프레임으로 변경 (비중요 작업)
            if re.search(r'iteration\s*%\s*4\s*==\s*0', line) and 'combat' not in line.lower():
 # CombatManager는 반응성이 중요하므로 제외
 new_line = re.sub(
                    r'iteration\s*%\s*4\s*==\s*0',
                    'iteration % 8 == 0',
 line
 )
 if new_line != line:
 modified_lines.append(new_line)
 fix_count += 1
 continue
 
 modified_lines.append(line)
 
        return '\n'.join(modified_lines), fix_count
 
 def optimize_unit_filtering(self, content: str, file_path: Path) -> Tuple[str, int]:
        """유닛 필터링 최적화"""
 lines = content.splitlines()
 modified_lines = []
 fix_count = 0
 
 for i, line in enumerate(lines):
 # 직접 bot.units() 호출을 캐시 사용으로 변경 제안
            if re.search(r'b\.units\(|bot\.units\(|self\.units\(', line) and 'cached' not in line.lower():
 # 캐시 사용 주석 추가
 indent = len(line) - len(line.lstrip())
                comment = f"{' ' * indent}# PERFORMANCE: Consider using intel.cached_* instead of direct units() call"
 modified_lines.append(line)
 # 다음 줄이 비어있지 않으면 주석 추가
                if i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].strip().startswith('#'):
 modified_lines.append(comment)
 fix_count += 1
 else:
 modified_lines.append(line)
 else:
 modified_lines.append(line)
 
        return '\n'.join(modified_lines), fix_count
 
 def add_lazy_evaluation(self, content: str, file_path: Path) -> Tuple[str, int]:
        """지연 평가 추가"""
 lines = content.splitlines()
 modified_lines = []
 fix_count = 0
 
 for i, line in enumerate(lines):
 # list() 호출 최적화
            if re.search(r'list\(.*\.units|list\(.*\.enemy_units|list\(.*\.structures', line):
 # .exists 체크 추가 제안
 indent = len(line) - len(line.lstrip())
                comment = f"{' ' * indent}# PERFORMANCE: Check .exists before list() to avoid unnecessary conversion"
 modified_lines.append(line)
                if i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].strip().startswith('#'):
 modified_lines.append(comment)
 fix_count += 1
 else:
 modified_lines.append(line)
 else:
 modified_lines.append(line)
 
        return '\n'.join(modified_lines), fix_count


def optimize_game_performance(file_path: Path) -> Dict:
    """게임 성능 최적화"""
 optimizer = GamePerformanceOptimizer()
 
 try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 
 original_content = content
 
 # 실행 주기 최적화
 content, freq_fixes = optimizer.optimize_execution_frequency(content, file_path)
 
 # 유닛 필터링 최적화
 content, filter_fixes = optimizer.optimize_unit_filtering(content, file_path)
 
 # 지연 평가 추가
 content, lazy_fixes = optimizer.add_lazy_evaluation(content, file_path)
 
 total_fixes = freq_fixes + filter_fixes + lazy_fixes
 
 if total_fixes > 0:
 # 백업 생성
            backup_path = file_path.with_suffix(file_path.suffix + '.bak')
            with open(backup_path, 'w', encoding='utf-8') as f:
 f.write(original_content)
 
 # 수정된 내용 저장
            with open(file_path, 'w', encoding='utf-8') as f:
 f.write(content)
 
 return {
                "success": True,
                "freq_fixes": freq_fixes,
                "filter_fixes": filter_fixes,
                "lazy_fixes": lazy_fixes,
                "total_fixes": total_fixes
 }
 else:
 return {
                "success": False,
                "total_fixes": 0
 }
 
 except Exception as e:
 return {
            "success": False,
            "error": str(e)
 }


def main():
    """메인 함수"""
    print("=" * 70)
    print("게임 성능 최적화 도구")
    print("=" * 70)
 print()
 
 # 주요 파일 목록
 main_files = [
        "wicked_zerg_bot_pro.py",
        "production_manager.py",
        "combat_manager.py",
        "economy_manager.py"
 ]
 
 total_freq_fixes = 0
 total_filter_fixes = 0
 total_lazy_fixes = 0
 
    print("게임 성능 최적화 적용 중...")
 for main_file in main_files:
 file_path = PROJECT_ROOT / main_file
 if file_path.exists():
            print(f"  - {main_file}")
 result = optimize_game_performance(file_path)
 
            if result.get("success"):
                print(f"    실행 주기: {result['freq_fixes']}개")
                print(f"    필터링: {result['filter_fixes']}개")
                print(f"    지연 평가: {result['lazy_fixes']}개")
                total_freq_fixes += result['freq_fixes']
                total_filter_fixes += result['filter_fixes']
                total_lazy_fixes += result['lazy_fixes']
            elif result.get("error"):
                print(f"    오류: {result['error']}")
 else:
                print(f"    변경 사항 없음")
 
 print()
    print("=" * 70)
    print("게임 성능 최적화 완료!")
    print(f"  실행 주기: {total_freq_fixes}개")
    print(f"  필터링: {total_filter_fixes}개")
    print(f"  지연 평가: {total_lazy_fixes}개")
    print("=" * 70)


if __name__ == "__main__":
 main()