# -*- coding: utf-8 -*-
"""
Transformer Decision Model for StarCraft II Bot

AlphaStar 스타일의 트랜스포머 기반 의사결정 모델입니다.
게임 상태를 시퀀스로 변환하여 장기 의존성을 학습합니다.

주요 기능:
1. Multi-head Self-Attention: 게임 상태 간 관계 학습
2. Positional Encoding: 시간적 순서 정보 인코딩
3. Feed-Forward Network: 비선형 변환
"""

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class PositionalEncoding:
    """위치 인코딩 (Positional Encoding)"""

    def __init__(self, d_model: int, max_len: int = 5000):
        """
        Args:
            d_model: 임베딩 차원
            max_len: 최대 시퀀스 길이
        """
        self.d_model = d_model
        self.max_len = max_len
        self.pe = self._create_positional_encoding()

    def _create_positional_encoding(self) -> np.ndarray:
        """위치 인코딩 생성"""
        pe = np.zeros((self.max_len, self.d_model))
        position = np.arange(0, self.max_len).reshape(-1, 1)
        div_term = np.exp(
            np.arange(0, self.d_model, 2) * (-math.log(10000.0) / self.d_model)
        )

        pe[:, 0::2] = np.sin(position * div_term)
        pe[:, 1::2] = np.cos(position * div_term)

        return pe

    def encode(self, x: np.ndarray) -> np.ndarray:
        """위치 인코딩 적용"""
        seq_len = x.shape[0]
        return x + self.pe[:seq_len, : x.shape[1]]


class MultiHeadAttention:
    """Multi-Head Self-Attention"""

    def __init__(self, d_model: int, num_heads: int = 4):
        """
        Args:
            d_model: 모델 차원
            num_heads: 어텐션 헤드 수
        """
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads

        # 가중치 초기화 (Xavier 초기화)
        scale = np.sqrt(2.0 / (d_model + d_model))
        self.W_q = np.random.randn(d_model, d_model) * scale
        self.W_k = np.random.randn(d_model, d_model) * scale
        self.W_v = np.random.randn(d_model, d_model) * scale
        self.W_o = np.random.randn(d_model, d_model) * scale

    def attention(
        self, Q: np.ndarray, K: np.ndarray, V: np.ndarray, mask: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """Scaled Dot-Product Attention"""
        scores = np.matmul(Q, K.T) / np.sqrt(self.d_k)

        if mask is not None:
            scores = scores + mask * -1e9

        attention_weights = self._softmax(scores)
        return np.matmul(attention_weights, V)

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        """안정적인 소프트맥스"""
        exp_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return exp_x / (np.sum(exp_x, axis=-1, keepdims=True) + 1e-9)

    def forward(self, x: np.ndarray) -> np.ndarray:
        """순전파"""
        # Linear projections
        Q = np.dot(x, self.W_q)
        K = np.dot(x, self.W_k)
        V = np.dot(x, self.W_v)

        # Attention
        attn_output = self.attention(Q, K, V)

        # Output projection
        return np.dot(attn_output, self.W_o)


class FeedForwardNetwork:
    """Feed-Forward Network"""

    def __init__(self, d_model: int, d_ff: int = 256):
        """
        Args:
            d_model: 모델 차원
            d_ff: 피드포워드 숨김 차원
        """
        self.d_model = d_model
        self.d_ff = d_ff

        # 가중치 초기화
        scale1 = np.sqrt(2.0 / (d_model + d_ff))
        scale2 = np.sqrt(2.0 / (d_ff + d_model))
        self.W1 = np.random.randn(d_model, d_ff) * scale1
        self.b1 = np.zeros(d_ff)
        self.W2 = np.random.randn(d_ff, d_model) * scale2
        self.b2 = np.zeros(d_model)

    def forward(self, x: np.ndarray) -> np.ndarray:
        """순전파 (ReLU 활성화)"""
        hidden = np.maximum(0, np.dot(x, self.W1) + self.b1)  # ReLU
        return np.dot(hidden, self.W2) + self.b2


class TransformerBlock:
    """트랜스포머 블록 (Self-Attention + FFN)"""

    def __init__(self, d_model: int, num_heads: int = 4, d_ff: int = 256):
        self.attention = MultiHeadAttention(d_model, num_heads)
        self.ffn = FeedForwardNetwork(d_model, d_ff)

    def forward(self, x: np.ndarray) -> np.ndarray:
        """순전파 (잔차 연결 + Layer Norm 없이 단순화)"""
        # Self-Attention + Residual
        attn_out = self.attention.forward(x)
        x = x + attn_out

        # Feed-Forward + Residual
        ffn_out = self.ffn.forward(x)
        x = x + ffn_out

        return x


class TransformerDecisionModel:
    """
    트랜스포머 기반 의사결정 모델

    게임 상태 시퀀스를 입력받아 최적의 행동을 예측합니다.
    """

    def __init__(
        self,
        input_dim: int = 8,
        d_model: int = 64,
        num_heads: int = 4,
        num_layers: int = 2,
        num_actions: int = 5,
    ):
        """
        Args:
            input_dim: 입력 차원 (게임 상태 피처 수)
            d_model: 모델 차원
            num_heads: 어텐션 헤드 수
            num_layers: 트랜스포머 레이어 수
            num_actions: 출력 행동 수
        """
        self.input_dim = input_dim
        self.d_model = d_model
        self.num_actions = num_actions

        # 입력 임베딩
        scale = np.sqrt(2.0 / (input_dim + d_model))
        self.input_embedding = np.random.randn(input_dim, d_model) * scale

        # 위치 인코딩
        self.pos_encoding = PositionalEncoding(d_model)

        # 트랜스포머 블록들
        self.transformer_blocks = [
            TransformerBlock(d_model, num_heads) for _ in range(num_layers)
        ]

        # 출력 레이어
        scale_out = np.sqrt(2.0 / (d_model + num_actions))
        self.output_layer = np.random.randn(d_model, num_actions) * scale_out

        # 행동 레이블
        self.action_labels = ["ECONOMY", "AGGRESSIVE", "DEFENSIVE", "TECH", "ALL_IN"]

        # 상태 히스토리 (시퀀스 생성용)
        self.state_history: List[np.ndarray] = []
        self.max_history_len = 10

    def _embed_input(self, x: np.ndarray) -> np.ndarray:
        """입력 임베딩"""
        # x: (seq_len, input_dim) -> (seq_len, d_model)
        return np.dot(x, self.input_embedding)

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        """소프트맥스"""
        exp_x = np.exp(x - np.max(x))
        return exp_x / (np.sum(exp_x) + 1e-9)

    def predict(self, game_state: List[float]) -> Dict[str, Any]:
        """
        게임 상태를 입력받아 행동 예측

        Args:
            game_state: 게임 상태 피처 리스트

        Returns:
            예측 결과 딕셔너리
        """
        try:
            # 입력 검증
            if not game_state or len(game_state) < self.input_dim:
                # 부족한 차원을 0으로 채움
                game_state = list(game_state) + [0.0] * (self.input_dim - len(game_state))

            # numpy 배열로 변환
            state = np.array(game_state[: self.input_dim], dtype=np.float32)

            # 히스토리에 추가
            self.state_history.append(state)
            if len(self.state_history) > self.max_history_len:
                self.state_history.pop(0)

            # 시퀀스 생성
            sequence = np.array(self.state_history)  # (seq_len, input_dim)

            # 입력 임베딩
            embedded = self._embed_input(sequence)  # (seq_len, d_model)

            # 위치 인코딩
            encoded = self.pos_encoding.encode(embedded)

            # 트랜스포머 블록 통과
            x = encoded
            for block in self.transformer_blocks:
                x = block.forward(x)

            # 마지막 토큰의 출력 사용
            last_output = x[-1]  # (d_model,)

            # 출력 레이어
            logits = np.dot(last_output, self.output_layer)  # (num_actions,)

            # 소프트맥스로 확률 계산
            probs = self._softmax(logits)

            # 최고 확률 행동 선택
            best_action_idx = np.argmax(probs)
            best_action = self.action_labels[best_action_idx]
            confidence = float(probs[best_action_idx])

            return {
                "action": best_action,
                "confidence": confidence,
                "action_probs": {
                    label: float(probs[i]) for i, label in enumerate(self.action_labels)
                },
                "sequence_length": len(self.state_history),
            }

        except Exception as e:
            return {
                "action": "ECONOMY",
                "confidence": 0.0,
                "error": str(e),
            }

    def get_action_recommendation(self, bot) -> str:
        """
        봇 객체에서 직접 행동 추천

        Args:
            bot: SC2 봇 객체

        Returns:
            추천 행동 문자열
        """
        try:
            # 게임 상태 추출
            game_state = [
                getattr(bot, "minerals", 0) / 1000.0,
                getattr(bot, "vespene", 0) / 1000.0,
                getattr(bot, "supply_used", 0) / 200.0,
                getattr(bot, "supply_cap", 0) / 200.0,
                len(getattr(bot, "units", [])) / 100.0,
                len(getattr(bot, "enemy_units", [])) / 100.0,
                getattr(bot, "time", 0) / 1000.0,
                len(getattr(bot, "townhalls", [])) / 10.0,
            ]

            result = self.predict(game_state)
            return result.get("action", "ECONOMY")

        except Exception:
            return "ECONOMY"

    def reset_history(self):
        """상태 히스토리 초기화"""
        self.state_history.clear()
