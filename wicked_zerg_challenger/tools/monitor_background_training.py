# -*- coding: utf-8 -*-
"""
Background Training Live Monitor
백그라운드 학습 실시간 모니터링 스크립트

실시간으로 백그라운드 학습 상태를 모니터링하고 대시보드 형식으로 표시합니다.
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 프로젝트 루트 추가
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class BackgroundTrainingMonitor:
    """백그라운드 학습 실시간 모니터"""

    def __init__(self):
        self.buffer_dir = project_root / "wicked_zerg_challenger" / "local_training" / "data" / "buffer"
        self.archive_dir = project_root / "wicked_zerg_challenger" / "local_training" / "data" / "archive"
        self.model_path = project_root / "wicked_zerg_challenger" / "local_training" / "models" / "rl_agent_model.npz"
        self.log_file = project_root / "wicked_zerg_challenger" / "local_training" / "logs" / "background_training.log"

        self.last_buffer_count = 0
        self.last_archive_count = 0
        self.last_model_mtime = 0.0
        self.start_time = time.time()

    def clear_screen(self):
        """화면 지우기 (OS별 처리)"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def get_directory_info(self, directory: Path) -> Dict:
        """디렉토리 정보 수집"""
        if not directory.exists():
            return {
                "count": 0,
                "total_size": 0,
                "files": []
            }

        files = list(directory.glob("*.npz"))
        total_size = sum(f.stat().st_size for f in files)

        return {
            "count": len(files),
            "total_size": total_size,
            "files": sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)[:5]
        }

    def get_model_info(self) -> Dict:
        """모델 정보 수집"""
        if not self.model_path.exists():
            return {
                "exists": False,
                "size": 0,
                "modified": None
            }

        stat = self.model_path.stat()
        return {
            "exists": True,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime)
        }

    def get_log_tail(self, lines: int = 10) -> List[str]:
        """로그 파일의 마지막 N 줄 읽기"""
        if not self.log_file.exists():
            return []

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return all_lines[-lines:] if all_lines else []
        except Exception:
            return []

    def format_size(self, size_bytes: int) -> str:
        """파일 크기를 읽기 좋은 형식으로 변환"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def format_time_delta(self, seconds: float) -> str:
        """시간 차이를 읽기 좋은 형식으로 변환"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    def print_dashboard(self):
        """대시보드 출력"""
        self.clear_screen()

        # 헤더
        print("="*80)
        print(" " * 20 + "? BACKGROUND TRAINING LIVE MONITOR")
        print("="*80)
        print(f"Monitoring Started: {datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Current Time:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Uptime:             {self.format_time_delta(time.time() - self.start_time)}")
        print("="*80)

        # 버퍼 디렉토리 상태
        buffer_info = self.get_directory_info(self.buffer_dir)
        print("\n? BUFFER DIRECTORY (Pending Training)")
        print("-"*80)
        print(f"Path:        {self.buffer_dir}")
        print(f"File Count:  {buffer_info['count']} files")
        print(f"Total Size:  {self.format_size(buffer_info['total_size'])}")

        # 버퍼 변화 감지
        buffer_delta = buffer_info['count'] - self.last_buffer_count
        if buffer_delta > 0:
            print(f"Status:      ? +{buffer_delta} new files detected!")
        elif buffer_delta < 0:
            print(f"Status:      ✓ {abs(buffer_delta)} files processed")
        else:
            print(f"Status:      ○ No change")

        if buffer_info['files']:
            print("\nRecent Files:")
            for f in buffer_info['files'][:3]:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                size = self.format_size(f.stat().st_size)
                print(f"  - {f.name} ({size}, {mtime.strftime('%H:%M:%S')})")

        self.last_buffer_count = buffer_info['count']

        # 아카이브 디렉토리 상태
        archive_info = self.get_directory_info(self.archive_dir)
        print("\n? ARCHIVE DIRECTORY (Processed)")
        print("-"*80)
        print(f"Path:        {self.archive_dir}")
        print(f"File Count:  {archive_info['count']} files")
        print(f"Total Size:  {self.format_size(archive_info['total_size'])}")

        # 아카이브 변화 감지
        archive_delta = archive_info['count'] - self.last_archive_count
        if archive_delta > 0:
            print(f"Status:      ✓ +{archive_delta} files archived (training completed)")
        else:
            print(f"Status:      ○ No change")

        if archive_info['files']:
            print("\nRecently Archived:")
            for f in archive_info['files'][:3]:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                size = self.format_size(f.stat().st_size)
                print(f"  - {f.name} ({size}, {mtime.strftime('%H:%M:%S')})")

        self.last_archive_count = archive_info['count']

        # 모델 정보
        model_info = self.get_model_info()
        print("\n? MODEL STATUS")
        print("-"*80)
        print(f"Path:        {self.model_path}")

        if model_info['exists']:
            print(f"Status:      ✓ Model exists")
            print(f"Size:        {self.format_size(model_info['size'])}")
            print(f"Modified:    {model_info['modified'].strftime('%Y-%m-%d %H:%M:%S')}")

            # 모델 업데이트 감지
            current_mtime = model_info['modified'].timestamp()
            if self.last_model_mtime > 0 and current_mtime > self.last_model_mtime:
                time_since_update = time.time() - current_mtime
                print(f"Update:      ? Model updated {self.format_time_delta(time_since_update)} ago!")

            self.last_model_mtime = current_mtime
        else:
            print(f"Status:      ✗ Model not found")

        # 학습 로그
        print("\n? TRAINING LOG (Last 10 lines)")
        print("-"*80)
        log_lines = self.get_log_tail(10)
        if log_lines:
            for line in log_lines:
                print(line.rstrip())
        else:
            print("(No log entries)")

        # 푸터
        print("\n" + "="*80)
        print("Refresh Rate: 2 seconds | Press Ctrl+C to stop monitoring")
        print("="*80)

    def run(self):
        """모니터링 실행"""
        print("Starting Background Training Monitor...")
        print("Press Ctrl+C to stop")
        time.sleep(2)

        try:
            while True:
                self.print_dashboard()
                time.sleep(2)
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user.")
            print(f"Total monitoring time: {self.format_time_delta(time.time() - self.start_time)}")


def main():
    """메인 진입점"""
    monitor = BackgroundTrainingMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
