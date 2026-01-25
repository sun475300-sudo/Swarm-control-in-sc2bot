"""
자동 리플레이 학습 시스템

기능:
1. 리플레이 자동 다운로드 (Spawning Tool API)
2. 압축 해제 및 파일 이동
3. 리플레이 분석 및 학습 (5회 반복)
4. 학습 완료된 리플레이 아카이브

"""

import os
import sys
import json
import time
import requests
import zipfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class AutoReplayLearner:
    """자동 리플레이 다운로드 및 학습 시스템"""

    def __init__(self,
                 download_dir: str = "data/replays/downloaded",
                 processed_dir: str = "data/replays/processed",
                 archive_dir: str = "data/replays/archive"):
        """
        Args:
            download_dir: 다운로드한 리플레이 저장 경로
            processed_dir: 분석할 리플레이 임시 경로
            archive_dir: 학습 완료된 리플레이 보관 경로
        """
        self.base_dir = Path(__file__).parent.parent
        self.download_dir = self.base_dir / download_dir
        self.processed_dir = self.base_dir / processed_dir
        self.archive_dir = self.base_dir / archive_dir

        # 디렉토리 생성
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        # Spawning Tool API 설정
        self.api_base_url = "https://spawningtool.com/api"

        # 학습 통계
        self.stats = {
            "replays_downloaded": 0,
            "replays_processed": 0,
            "replays_failed": 0,
            "total_learning_runs": 0,
        }

        # 이미 처리한 리플레이 ID 기록
        self.processed_replay_ids = self._load_processed_ids()

    def _load_processed_ids(self) -> set:
        """이미 처리한 리플레이 ID 로드"""
        id_file = self.archive_dir / "processed_ids.json"
        if id_file.exists():
            try:
                with open(id_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get("replay_ids", []))
            except Exception:
                pass
        return set()

    def _save_processed_ids(self):
        """처리한 리플레이 ID 저장"""
        id_file = self.archive_dir / "processed_ids.json"
        try:
            with open(id_file, 'w') as f:
                json.dump({
                    "replay_ids": list(self.processed_replay_ids),
                    "last_updated": datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"[AUTO_REPLAY] Failed to save processed IDs: {e}")

    def search_replays(self,
                      limit: int = 10,
                      race: str = "Zerg",
                      min_mmr: int = 4000) -> List[Dict]:
        """
        Spawning Tool에서 고수 저그 리플레이 검색

        Args:
            limit: 검색할 리플레이 개수
            race: 종족 (Zerg, Terran, Protoss)
            min_mmr: 최소 MMR (4000 = 마스터)

        Returns:
            리플레이 정보 리스트
        """
        print(f"\n[AUTO_REPLAY] Searching for {race} replays (MMR >= {min_mmr})...")

        try:
            # Spawning Tool API로 리플레이 검색
            params = {
                "limit": limit * 2,  # 필터링 후 부족할 수 있으니 2배 요청
                "race": race,
                "after": "2024-01-01",  # 최신 패치 리플레이만
            }

            # 헤더 추가 (User-Agent)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            response = requests.get(
                f"{self.api_base_url}/replays/",
                params=params,
                headers=headers,
                timeout=30,
                verify=False  # SSL 인증서 검증 무시 (인증서 오류 해결)
            )

            if response.status_code != 200:
                print(f"[AUTO_REPLAY] API request failed: {response.status_code}")
                return []

            data = response.json()
            replays = data.get("replays", [])

            # 필터링: 고MMR, 아직 처리 안 한 리플레이만
            filtered_replays = []
            for replay in replays:
                replay_id = replay.get("id")

                # 이미 처리한 리플레이는 스킵
                if replay_id in self.processed_replay_ids:
                    continue

                # MMR 체크 (있으면)
                players = replay.get("players", [])
                avg_mmr = 0
                if players:
                    mmrs = [p.get("mmr", 0) for p in players if p.get("mmr")]
                    if mmrs:
                        avg_mmr = sum(mmrs) / len(mmrs)

                if avg_mmr >= min_mmr or avg_mmr == 0:  # MMR 정보 없으면 일단 포함
                    filtered_replays.append(replay)

                if len(filtered_replays) >= limit:
                    break

            print(f"[AUTO_REPLAY] Found {len(filtered_replays)} suitable replays")
            return filtered_replays[:limit]

        except Exception as e:
            print(f"[AUTO_REPLAY] Search failed: {e}")
            import traceback
            traceback.print_exc()
            return []

    def download_replay(self, replay_info: Dict) -> Optional[Path]:
        """
        리플레이 다운로드

        Args:
            replay_info: 리플레이 정보 딕셔너리

        Returns:
            다운로드한 파일 경로 (실패 시 None)
        """
        replay_id = replay_info.get("id")
        download_url = replay_info.get("download_url")

        if not download_url:
            print(f"[AUTO_REPLAY] No download URL for replay {replay_id}")
            return None

        try:
            print(f"[AUTO_REPLAY] Downloading replay {replay_id}...")

            # 파일명 생성
            filename = f"replay_{replay_id}_{int(time.time())}.SC2Replay"
            filepath = self.download_dir / filename

            # 헤더 추가
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            # 다운로드
            response = requests.get(download_url, headers=headers, timeout=60, verify=False)  # SSL 검증 무시
            if response.status_code != 200:
                print(f"[AUTO_REPLAY] Download failed: {response.status_code}")
                return None

            # 저장
            with open(filepath, 'wb') as f:
                f.write(response.content)

            print(f"[AUTO_REPLAY] [OK] Downloaded: {filepath.name} ({len(response.content)} bytes)")
            self.stats["replays_downloaded"] += 1
            return filepath

        except Exception as e:
            print(f"[AUTO_REPLAY] Download failed: {e}")
            return None

    def extract_and_move_replay(self, replay_path: Path) -> Optional[Path]:
        """
        리플레이 압축 해제 및 이동

        Args:
            replay_path: 다운로드한 리플레이 경로

        Returns:
            처리된 리플레이 경로 (실패 시 None)
        """
        try:
            # .SC2Replay 파일은 압축 파일이 아니므로 그냥 복사
            target_path = self.processed_dir / replay_path.name

            # 기존 파일 있으면 삭제
            if target_path.exists():
                target_path.unlink()

            # 복사
            shutil.copy2(replay_path, target_path)
            print(f"[AUTO_REPLAY] [OK] Moved to processing: {target_path.name}")
            return target_path

        except Exception as e:
            print(f"[AUTO_REPLAY] Failed to move replay: {e}")
            return None

    def learn_from_replay(self, replay_path: Path, iterations: int = 5) -> bool:
        """
        리플레이에서 학습 (여러 번 반복)

        Args:
            replay_path: 리플레이 파일 경로
            iterations: 학습 반복 횟수

        Returns:
            학습 성공 여부
        """
        print(f"\n[AUTO_REPLAY] Learning from {replay_path.name} ({iterations} iterations)...")

        try:
            # ReplayBuildOrderLearner import
            sys.path.insert(0, str(self.base_dir / "local_training" / "scripts"))
            from replay_build_order_learner import ReplayBuildOrderLearner

            learner = ReplayBuildOrderLearner()

            # 여러 번 반복 학습
            for i in range(iterations):
                print(f"\n[AUTO_REPLAY] === Learning iteration {i+1}/{iterations} ===")

                try:
                    # 리플레이 분석 및 학습
                    result = learner.learn_from_replay(str(replay_path))

                    if result:
                        print(f"[AUTO_REPLAY] [OK] Iteration {i+1} successful")
                        self.stats["total_learning_runs"] += 1
                    else:
                        print(f"[AUTO_REPLAY] ✗ Iteration {i+1} failed")
                        # 한 번 실패해도 계속 시도
                        continue

                except Exception as iter_error:
                    print(f"[AUTO_REPLAY] Iteration {i+1} error: {iter_error}")
                    continue

            print(f"[AUTO_REPLAY] [OK] Completed {iterations} learning iterations")
            self.stats["replays_processed"] += 1
            return True

        except Exception as e:
            print(f"[AUTO_REPLAY] Learning failed: {e}")
            import traceback
            traceback.print_exc()
            self.stats["replays_failed"] += 1
            return False

    def archive_replay(self, replay_path: Path, replay_id: str):
        """
        학습 완료된 리플레이 아카이브

        Args:
            replay_path: 리플레이 파일 경로
            replay_id: 리플레이 ID
        """
        try:
            # 아카이브로 이동
            archive_path = self.archive_dir / replay_path.name
            if archive_path.exists():
                archive_path.unlink()

            shutil.move(str(replay_path), str(archive_path))

            # 처리 완료 ID 기록
            self.processed_replay_ids.add(replay_id)
            self._save_processed_ids()

            print(f"[AUTO_REPLAY] [OK] Archived: {archive_path.name}")

        except Exception as e:
            print(f"[AUTO_REPLAY] Failed to archive replay: {e}")

    def run_auto_learning_cycle(self,
                                 num_replays: int = 5,
                                 learning_iterations: int = 5,
                                 min_mmr: int = 4000):
        """
        자동 리플레이 학습 사이클 실행

        Args:
            num_replays: 다운로드할 리플레이 개수
            learning_iterations: 각 리플레이당 학습 반복 횟수
            min_mmr: 최소 MMR
        """
        print("\n" + "="*70)
        print("[REPLAY_LEARNING] [AUTO REPLAY LEARNING CYCLE] STARTING")
        print("="*70)
        print(f"Target replays: {num_replays}")
        print(f"Learning iterations per replay: {learning_iterations}")
        print(f"Minimum MMR: {min_mmr}")
        print("="*70)

        # 1. 리플레이 검색
        replays = self.search_replays(limit=num_replays, min_mmr=min_mmr)

        if not replays:
            print("[AUTO_REPLAY] No replays found. Skipping.")
            return

        # 2. 각 리플레이 처리
        for idx, replay_info in enumerate(replays, 1):
            replay_id = replay_info.get("id")
            print(f"\n[AUTO_REPLAY] Processing replay {idx}/{len(replays)} (ID: {replay_id})")

            # 2.1 다운로드
            downloaded_path = self.download_replay(replay_info)
            if not downloaded_path:
                continue

            # 2.2 이동
            processed_path = self.extract_and_move_replay(downloaded_path)
            if not processed_path:
                continue

            # 2.3 학습 (N회 반복)
            success = self.learn_from_replay(processed_path, iterations=learning_iterations)

            # 2.4 아카이브
            if success:
                self.archive_replay(processed_path, replay_id)
            else:
                # 실패한 리플레이도 아카이브 (재시도 방지)
                self.archive_replay(processed_path, replay_id)

            print(f"[AUTO_REPLAY] Replay {idx}/{len(replays)} complete")

        # 3. 통계 출력
        self.print_stats()

    def print_stats(self):
        """학습 통계 출력"""
        print("\n" + "="*70)
        print("[STATS] [AUTO REPLAY LEARNING] STATISTICS")
        print("="*70)
        print(f"Replays Downloaded:     {self.stats['replays_downloaded']}")
        print(f"Replays Processed:      {self.stats['replays_processed']}")
        print(f"Replays Failed:         {self.stats['replays_failed']}")
        print(f"Total Learning Runs:    {self.stats['total_learning_runs']}")
        print(f"Processed IDs Tracked:  {len(self.processed_replay_ids)}")
        print("="*70)


def main():
    """메인 함수 - 테스트용"""
    learner = AutoReplayLearner()

    # 5개 리플레이 다운로드하여 각 5회씩 학습
    learner.run_auto_learning_cycle(
        num_replays=5,
        learning_iterations=5,
        min_mmr=4000
    )


if __name__ == "__main__":
    main()
