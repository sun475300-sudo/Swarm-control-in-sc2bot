# -*- coding: utf-8 -*-
"""
Training Pipeline - 모델 버전 관리 + 자동 배포

기능:
1. 학습 체크포인트를 버전별로 저장
2. 새 모델이 기존 모델보다 win_rate 5%+ 향상 시 자동 배포
3. 경험 파일(.npz) 수집 및 아카이브
4. 전체 버전 히스토리 관리

버전 히스토리: local_training/models/versions/version_history.json
"""

import json
import os
import shutil
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ModelVersion:
    """모델 버전 정보"""
    version_id: int
    model_path: str
    metrics: Dict  # {"win_rate": 0.6, "avg_reward": 50, "games": 10}
    created_at: float
    deployed: bool = False


class TrainingPipeline:
    """
    ML 훈련 파이프라인

    - create_checkpoint(): 버전 디렉토리에 모델 저장 + 메트릭 기록
    - deploy_if_better(): 현재 운영 모델 대비 개선 시 자동 배포
    - collect_experience_files(): buffer 디렉토리에서 경험 파일 로드
    - archive_processed_experience(): 처리 완료 파일 이동
    """

    DEPLOY_THRESHOLD = 0.05  # win_rate 5% 이상 향상 시 배포
    MAX_VERSIONS = 50        # 최대 보관 버전 수

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(__file__), "models")
        self.base_dir = Path(base_dir)
        self.versions_dir = self.base_dir / "versions"
        self.buffer_dir = self.base_dir / "buffer"
        self.archive_dir = self.base_dir / "archive"
        self.history_path = self.versions_dir / "version_history.json"
        self.deployed_model_path = self.base_dir / "deployed_model.npz"

        # 디렉토리 생성
        for d in [self.versions_dir, self.buffer_dir, self.archive_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.versions: List[ModelVersion] = []
        self._load_history()

    def _load_history(self) -> None:
        """버전 히스토리 로드"""
        if self.history_path.exists():
            try:
                with open(self.history_path, "r") as f:
                    data = json.load(f)
                self.versions = [
                    ModelVersion(**v) for v in data.get("versions", [])
                ]
            except (json.JSONDecodeError, TypeError):
                self.versions = []

    def _save_history(self) -> None:
        """버전 히스토리 저장"""
        data = {"versions": [asdict(v) for v in self.versions]}
        with open(self.history_path, "w") as f:
            json.dump(data, f, indent=2)

    def create_checkpoint(self, rl_agent, metrics: Dict) -> ModelVersion:
        """
        현재 모델을 새 버전으로 저장.

        Args:
            rl_agent: RLAgent 인스턴스
            metrics: {"win_rate": float, "avg_reward": float, "games": int}

        Returns:
            생성된 ModelVersion
        """
        version_id = len(self.versions) + 1
        model_filename = f"model_v{version_id:04d}.npz"
        model_path = str(self.versions_dir / model_filename)

        # 모델 저장
        rl_agent.save_model(model_path)

        version = ModelVersion(
            version_id=version_id,
            model_path=model_path,
            metrics=metrics,
            created_at=time.time(),
            deployed=False,
        )
        self.versions.append(version)
        self._save_history()

        # 오래된 버전 정리
        self._cleanup_old_versions()

        print(f"[PIPELINE] Checkpoint v{version_id}: {metrics}")
        return version

    def deploy_if_better(self, new_version: ModelVersion) -> bool:
        """
        새 모델이 현재 운영 모델보다 나으면 자동 배포.

        배포 조건: new_win_rate >= current_win_rate + DEPLOY_THRESHOLD
        """
        current_deployed = self._get_deployed_version()

        if current_deployed is None:
            # 첫 배포
            self._deploy(new_version)
            return True

        current_wr = current_deployed.metrics.get("win_rate", 0.0)
        new_wr = new_version.metrics.get("win_rate", 0.0)

        if new_wr >= current_wr + self.DEPLOY_THRESHOLD:
            self._deploy(new_version)
            print(
                f"[PIPELINE] AUTO-DEPLOY v{new_version.version_id}: "
                f"win_rate {current_wr:.1%} → {new_wr:.1%} (+{new_wr - current_wr:.1%})"
            )
            return True

        print(
            f"[PIPELINE] No deploy: v{new_version.version_id} "
            f"({new_wr:.1%}) vs deployed ({current_wr:.1%})"
        )
        return False

    def _deploy(self, version: ModelVersion) -> None:
        """모델 배포 (운영 모델로 복사)"""
        # 기존 배포 해제
        for v in self.versions:
            v.deployed = False

        version.deployed = True

        # 운영 모델 경로로 복사
        if os.path.exists(version.model_path):
            shutil.copy2(version.model_path, str(self.deployed_model_path))

        self._save_history()

    def _get_deployed_version(self) -> Optional[ModelVersion]:
        """현재 배포된 버전 반환"""
        for v in reversed(self.versions):
            if v.deployed:
                return v
        return None

    def collect_experience_files(self) -> list:
        """buffer 디렉토리에서 .npz 경험 파일 수집"""
        files = list(self.buffer_dir.glob("*.npz"))
        return sorted(files, key=lambda f: f.stat().st_mtime)

    def archive_processed_experience(self, files: list) -> None:
        """처리 완료 경험 파일을 archive로 이동"""
        for f in files:
            dest = self.archive_dir / f.name
            try:
                shutil.move(str(f), str(dest))
            except Exception:
                pass

    def _cleanup_old_versions(self) -> None:
        """오래된 버전 정리 (MAX_VERSIONS 초과 시)"""
        if len(self.versions) <= self.MAX_VERSIONS:
            return

        # 배포된 버전은 보존
        to_remove = []
        for v in self.versions[: -self.MAX_VERSIONS]:
            if not v.deployed:
                to_remove.append(v)

        for v in to_remove:
            try:
                if os.path.exists(v.model_path):
                    os.remove(v.model_path)
            except Exception:
                pass
            self.versions.remove(v)

        self._save_history()

    def get_training_summary(self) -> Dict:
        """전체 버전 히스토리 요약"""
        deployed = self._get_deployed_version()
        return {
            "total_versions": len(self.versions),
            "deployed_version": deployed.version_id if deployed else None,
            "deployed_win_rate": deployed.metrics.get("win_rate", 0) if deployed else 0,
            "latest_version": self.versions[-1].version_id if self.versions else 0,
            "buffer_files": len(list(self.buffer_dir.glob("*.npz"))),
        }
