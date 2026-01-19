# -*- coding: utf-8 -*-
"""
Transformer Model for Long-term Causal Relationship Learning

Self-Attention mechanism to understand long-term dependencies in game state.
Based on AlphaStar approach for StarCraft II AI.

Key features:
- Self-Attention: Understands relationships between different game states
- Long-term memory: Can relate "3 minutes ago gas mining rate" to "current enemy army position"
- Causal reasoning: Learns why certain actions lead to outcomes
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple, Any
import math

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


class MultiHeadAttention(nn.Module):
    """
    Multi-Head Self-Attention mechanism.
    
    Allows the model to focus on different aspects of the game state simultaneously.
    """
    
    def __init__(self, d_model: int, num_heads: int = 8, dropout: float = 0.1):
        """
        Initialize multi-head attention.
        
        Args:
            d_model: Model dimension
            num_heads: Number of attention heads
            dropout: Dropout rate
        """
        super().__init__()
        assert d_model % num_heads == 0
        
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads
        
        self.w_q = nn.Linear(d_model, d_model)
        self.w_k = nn.Linear(d_model, d_model)
        self.w_v = nn.Linear(d_model, d_model)
        self.w_o = nn.Linear(d_model, d_model)
        
        self.dropout = nn.Dropout(dropout)
    
    def forward(
        self,
        query: torch.Tensor,
        key: torch.Tensor,
        value: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Forward pass through multi-head attention.
        
        Args:
            query: Query tensor [batch, seq_len, d_model]
            key: Key tensor [batch, seq_len, d_model]
            value: Value tensor [batch, seq_len, d_model]
            mask: Attention mask (optional)
            
        Returns:
            Output tensor [batch, seq_len, d_model]
        """
        batch_size = query.size(0)
        
        # Linear projections and split into heads
        Q = self.w_q(query).view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)
        K = self.w_k(key).view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)
        V = self.w_v(value).view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)
        
        # Scaled dot-product attention
        scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.d_k)
        
        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)
        
        attention_weights = F.softmax(scores, dim=-1)
        attention_weights = self.dropout(attention_weights)
        
        # Apply attention to values
        context = torch.matmul(attention_weights, V)
        
        # Concatenate heads
        context = context.transpose(1, 2).contiguous().view(
            batch_size, -1, self.d_model
        )
        
        # Final linear projection
        output = self.w_o(context)
        
        return output


class TransformerBlock(nn.Module):
    """
    Transformer block with self-attention and feed-forward network.
    """
    
    def __init__(self, d_model: int, num_heads: int = 8, d_ff: int = 2048, dropout: float = 0.1):
        """
        Initialize transformer block.
        
        Args:
            d_model: Model dimension
            num_heads: Number of attention heads
            d_ff: Feed-forward dimension
            dropout: Dropout rate
        """
        super().__init__()
        
        self.attention = MultiHeadAttention(d_model, num_heads, dropout)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        
        self.feed_forward = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout)
        )
    
    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Forward pass through transformer block.
        
        Args:
            x: Input tensor [batch, seq_len, d_model]
            mask: Attention mask (optional)
            
        Returns:
            Output tensor [batch, seq_len, d_model]
        """
        # Self-attention with residual connection
        attn_output = self.attention(x, x, x, mask)
        x = self.norm1(x + attn_output)
        
        # Feed-forward with residual connection
        ff_output = self.feed_forward(x)
        x = self.norm2(x + ff_output)
        
        return x


class GameStateTransformer(nn.Module):
    """
    Transformer model for game state sequence processing.
    
    Understands long-term causal relationships in StarCraft II gameplay.
    """
    
    def __init__(
        self,
        input_dim: int = 128,
        d_model: int = 256,
        num_heads: int = 8,
        num_layers: int = 6,
        d_ff: int = 1024,
        max_seq_len: int = 512,
        dropout: float = 0.1
    ):
        """
        Initialize game state transformer.
        
        Args:
            input_dim: Input feature dimension
            d_model: Model dimension
            num_heads: Number of attention heads
            num_layers: Number of transformer layers
            d_ff: Feed-forward dimension
            max_seq_len: Maximum sequence length
            dropout: Dropout rate
        """
        super().__init__()
        
        self.d_model = d_model
        self.max_seq_len = max_seq_len
        
        # Input projection
        self.input_projection = nn.Linear(input_dim, d_model)
        
        # Positional encoding
        self.pos_encoding = PositionalEncoding(d_model, max_seq_len, dropout)
        
        # Transformer blocks
        self.transformer_blocks = nn.ModuleList([
            TransformerBlock(d_model, num_heads, d_ff, dropout)
            for _ in range(num_layers)
        ])
        
        # Output projection
        self.output_projection = nn.Linear(d_model, input_dim)
    
    def forward(
        self,
        x: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Forward pass through transformer.
        
        Args:
            x: Input sequence [batch, seq_len, input_dim]
            mask: Attention mask (optional)
            
        Returns:
            Output sequence [batch, seq_len, input_dim]
        """
        # Project input
        x = self.input_projection(x) * math.sqrt(self.d_model)
        
        # Add positional encoding
        x = self.pos_encoding(x)
        
        # Pass through transformer blocks
        for block in self.transformer_blocks:
            x = block(x, mask)
        
        # Project output
        x = self.output_projection(x)
        
        return x


class PositionalEncoding(nn.Module):
    """
    Positional encoding for transformer.
    
    Adds positional information to input embeddings.
    """
    
    def __init__(self, d_model: int, max_len: int = 512, dropout: float = 0.1):
        """
        Initialize positional encoding.
        
        Args:
            d_model: Model dimension
            max_len: Maximum sequence length
            dropout: Dropout rate
        """
        super().__init__()
        
        self.dropout = nn.Dropout(dropout)
        
        # Create positional encoding matrix
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        
        pe = pe.unsqueeze(0)  # [1, max_len, d_model]
        self.register_buffer('pe', pe)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Add positional encoding to input.
        
        Args:
            x: Input tensor [batch, seq_len, d_model]
            
        Returns:
            Output tensor with positional encoding
        """
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)


# Usage example (commented)
"""
# Initialize transformer model
model = GameStateTransformer(
    input_dim=128,  # Game state feature dimension
    d_model=256,
    num_heads=8,
    num_layers=6
)

# Process game state sequence
# game_states: [batch, seq_len, input_dim]
output = model(game_states)

# Use output for decision making
# The model has learned long-term causal relationships
"""
