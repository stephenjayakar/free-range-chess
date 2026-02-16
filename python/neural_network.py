"""
AlphaZero-style neural network for Free Range Chess.

Architecture:
- Input: 14 x 10 x 10 board state tensor
- Shared ResNet backbone (configurable depth)
- Policy head: outputs probability over all possible (from, to) actions + end_turn
- Value head: outputs scalar value [-1, 1] estimating win probability

Action encoding:
- Actions are (from_square, to_square) pairs
- Total: 10*10 * 10*10 = 10000 move actions + 1 end_turn = 10001
- Action index = from_y * W * H * W + from_x * H * W + to_y * W + to_x
- End turn = 10000
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Tuple

BOARD_W = 10
BOARD_H = 10
NUM_ACTIONS = BOARD_W * BOARD_H * BOARD_W * BOARD_H + 1  # 10001
END_TURN_ACTION = NUM_ACTIONS - 1
INPUT_CHANNELS = 14


def encode_action(from_pos: Tuple[int,int], to_pos: Tuple[int,int]) -> int:
    fx, fy = from_pos
    tx, ty = to_pos
    return fy * BOARD_W * BOARD_H * BOARD_W + fx * BOARD_H * BOARD_W + ty * BOARD_W + tx

def decode_action(action: int) -> Tuple[Tuple[int,int], Tuple[int,int]]:
    if action == END_TURN_ACTION:
        return None, None
    tx = action % BOARD_W
    action //= BOARD_W
    ty = action % BOARD_H
    action //= BOARD_H
    fx = action % BOARD_W
    action //= BOARD_W
    fy = action
    return (fx, fy), (tx, ty)


class ResBlock(nn.Module):
    """Residual block with two conv layers and batch norm."""
    def __init__(self, channels: int):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(channels)

    def forward(self, x):
        residual = x
        x = F.relu(self.bn1(self.conv1(x)))
        x = self.bn2(self.conv2(x))
        x = F.relu(x + residual)
        return x


class ChessNet(nn.Module):
    """AlphaZero-style network for Free Range Chess.
    
    Args:
        num_res_blocks: Number of residual blocks (depth)
        channels: Number of channels in residual tower
    """
    def __init__(self, num_res_blocks: int = 8, channels: int = 128):
        super().__init__()
        
        # Initial convolution
        self.conv_input = nn.Conv2d(INPUT_CHANNELS, channels, 3, padding=1, bias=False)
        self.bn_input = nn.BatchNorm2d(channels)
        
        # Residual tower
        self.res_blocks = nn.ModuleList([
            ResBlock(channels) for _ in range(num_res_blocks)
        ])
        
        # Policy head
        self.policy_conv = nn.Conv2d(channels, 32, 1, bias=False)
        self.policy_bn = nn.BatchNorm2d(32)
        self.policy_fc = nn.Linear(32 * BOARD_H * BOARD_W, NUM_ACTIONS)
        
        # Value head
        self.value_conv = nn.Conv2d(channels, 1, 1, bias=False)
        self.value_bn = nn.BatchNorm2d(1)
        self.value_fc1 = nn.Linear(BOARD_H * BOARD_W, 256)
        self.value_fc2 = nn.Linear(256, 1)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            x: Board state tensor of shape (batch, 14, 10, 10)
        Returns:
            policy_logits: (batch, NUM_ACTIONS) raw logits
            value: (batch, 1) value in [-1, 1]
        """
        # Shared backbone
        x = F.relu(self.bn_input(self.conv_input(x)))
        for block in self.res_blocks:
            x = block(x)
        
        # Policy head
        p = F.relu(self.policy_bn(self.policy_conv(x)))
        p = p.view(p.size(0), -1)
        p = self.policy_fc(p)
        
        # Value head
        v = F.relu(self.value_bn(self.value_conv(x)))
        v = v.view(v.size(0), -1)
        v = F.relu(self.value_fc1(v))
        v = torch.tanh(self.value_fc2(v))
        
        return p, v

    @property
    def device(self) -> torch.device:
        return next(self.parameters()).device

    def predict(self, state_np: np.ndarray) -> Tuple[np.ndarray, float]:
        """Single-state inference for MCTS.
        
        Args:
            state_np: numpy array of shape (14, 10, 10)
        Returns:
            policy: probability distribution over actions (NUM_ACTIONS,)
            value: scalar value estimate
        """
        self.eval()
        with torch.no_grad():
            x = torch.FloatTensor(state_np).unsqueeze(0).to(self.device)
            p_logits, v = self(x)
            policy = F.softmax(p_logits, dim=1).cpu().numpy()[0]
            value = v.cpu().item()
        return policy, value

    def predict_batch(self, states: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Batch inference.
        
        Args:
            states: numpy array of shape (batch, 14, 10, 10)
        Returns:
            policies: (batch, NUM_ACTIONS)
            values: (batch,)
        """
        self.eval()
        with torch.no_grad():
            x = torch.FloatTensor(states).to(self.device)
            p_logits, v = self(x)
            policies = F.softmax(p_logits, dim=1).cpu().numpy()
            values = v.cpu().numpy().flatten()
        return policies, values


def create_model(num_res_blocks: int = 8, channels: int = 128, device: str = 'cpu') -> ChessNet:
    """Create and initialize a ChessNet model."""
    model = ChessNet(num_res_blocks=num_res_blocks, channels=channels)
    model = model.to(device)
    return model


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
