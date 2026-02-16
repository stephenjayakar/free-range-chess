# Free Range Chess — AI Training Guide

## Overview

This project includes an **AlphaZero-style reinforcement learning agent** that learns to play Free Range Chess (10×10 board, all pieces move once per turn) through self-play with Monte Carlo Tree Search (MCTS).

### Architecture

| Component | Details |
|-----------|---------|
| **Neural Network** | ResNet: 6 residual blocks, 128 channels, ~33.8M parameters |
| **Input** | 14×10×10 tensor (12 piece channels + moved-tracking + turn indicator) |
| **Policy Head** | 10,001 outputs (100×100 move coordinates + end_turn action) |
| **Value Head** | Single scalar ∈ [-1, 1] (win/loss prediction) |
| **Search** | MCTS with PUCT selection, Dirichlet noise, legal action masking |
| **Device** | MPS (Apple Silicon), CUDA, or CPU |

### Training Progress (24 iterations completed, ~2.4 hours)

```
Iter  1 | PL=4.44  VL=0.11 | 80% vs random
Iter  5 | PL=1.80  VL=0.05 | 100% vs random
Iter 12 | PL=1.03  VL=0.02 | 20% vs random  (win rate noisy with 5 eval games)
Iter 18 | PL=0.91  VL=0.06 | 80% vs random
Iter 24 | PL=0.84  VL=0.16 | 60% vs random
```

Policy loss dropped **81%** (4.44 → 0.84). Win rate vs random is volatile due to small eval sample (5 games).

---

## Quick Start

```bash
cd python

# Set up environment (first time only)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Resume Training

Training stopped at **iteration 24**. To continue from the latest checkpoint:

```bash
cd python && source venv/bin/activate

python3 train_alphazero.py \
  --resume ./models/alphazero/checkpoint_latest.pt \
  --iterations 100 \
  --games 10 \
  --simulations 30 \
  --res-blocks 6 \
  --channels 128 \
  --batch-size 64 \
  --lr 0.001 \
  --epochs 5 \
  --eval-games 5 \
  --max-turns 100 \
  --device mps \
  --save-every 1
```

Or run in the background with logging:

```bash
cd python && source venv/bin/activate

nohup python3 train_alphazero.py \
  --resume ./models/alphazero/checkpoint_latest.pt \
  --iterations 100 \
  --games 10 \
  --simulations 30 \
  --res-blocks 6 \
  --channels 128 \
  --batch-size 64 \
  --lr 0.001 \
  --epochs 5 \
  --eval-games 5 \
  --max-turns 100 \
  --device mps \
  --save-every 1 \
  > logs/training_output.log 2>&1 &

echo "PID: $!"
```

### Key CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--resume PATH` | none | Resume from a checkpoint file |
| `--iterations N` | 100 | Total training iterations |
| `--games N` | 10 | Self-play games per iteration |
| `--simulations N` | 30 | MCTS simulations per move decision |
| `--device DEVICE` | `mps` | `mps` (Apple Silicon), `cuda`, or `cpu` |
| `--save-every N` | 1 | Save checkpoint every N iterations |
| `--eval-games N` | 5 | Games to play vs random for evaluation |
| `--res-blocks N` | 6 | Number of residual blocks in the network |
| `--channels N` | 128 | Channels per residual block |
| `--batch-size N` | 64 | Training batch size |
| `--lr FLOAT` | 0.001 | Learning rate |
| `--epochs N` | 5 | Training epochs per iteration |
| `--max-turns N` | 100 | Max turns per self-play game |

---

## Stop Training

### Graceful stop (saves checkpoint before exiting):

```bash
# Find the PID
ps aux | grep train_alphazero | grep -v grep

# Send SIGINT — triggers graceful shutdown
kill -SIGINT <PID>
```

The script catches SIGINT/SIGTERM, finishes the current phase, saves a checkpoint, and exits cleanly. Press Ctrl+C twice to force quit without saving.

---

## Monitor Training

### Live log output:

```bash
tail -f python/logs/training_output.log
```

### Structured metrics (JSON):

```bash
# Pretty-print all iterations
python3 -c "
import json
d = json.load(open('python/logs/alphazero/training_log.json'))
for e in d:
    print(f\"Iter {e['iteration']:2d} | PL={e['policy_loss']:.4f} VL={e['value_loss']:.4f} | W={e['wins']} L={e['losses']} ({e['win_rate']*100:.0f}%) | {e['total_time']:.0f}s\")
"
```

### Check process health:

```bash
ps aux | grep train_alphazero | grep -v grep
```

---

## Evaluate a Checkpoint

Run a saved model against the random AI:

```bash
cd python && source venv/bin/activate

python3 -c "
import torch
from neural_network import ChessNet
from mcts import MCTS, MCTSPlayer
from game_engine import GameState

# Load model
net = ChessNet(res_blocks=6, channels=128)
ckpt = torch.load('models/alphazero/checkpoint_latest.pt', map_location='mps')
net.load_state_dict(ckpt['model_state_dict'])
net.eval()
net.to('mps')

# Create MCTS player
mcts = MCTS(net, num_simulations=50, device='mps')
player = MCTSPlayer(mcts, temperature=0.1)  # low temp = greedy

# Play a game vs random
import random
state = GameState()
turn = 0
while turn < 200:
    if state.current_player == 1:  # White = MCTS
        actions = player.play_turn(state)
        print(f'Turn {turn}: MCTS played {len(actions)} actions')
    else:  # Black = random
        moves = state.get_all_legal_moves()
        if moves:
            piece_idx = random.randint(0, len(moves)-1)
            piece_moves = moves[piece_idx]
            if piece_moves:
                move = random.choice(piece_moves)
                state.make_move(move[0], move[1], move[2], move[3])
        state.end_turn()
    turn += 1
    if state.is_game_over():
        winner = 'White (MCTS)' if state.winner == 1 else 'Black (Random)'
        print(f'Game over! Winner: {winner}')
        break
else:
    print('Draw (max turns)')
"
```

### Batch evaluation (N games):

```bash
cd python && source venv/bin/activate

python3 -c "
import torch, random
from neural_network import ChessNet
from mcts import MCTS, MCTSPlayer
from game_engine import GameState

net = ChessNet(res_blocks=6, channels=128)
ckpt = torch.load('models/alphazero/checkpoint_latest.pt', map_location='mps')
net.load_state_dict(ckpt['model_state_dict'])
net.eval(); net.to('mps')

mcts = MCTS(net, num_simulations=50, device='mps')
player = MCTSPlayer(mcts, temperature=0.1)

wins, losses, draws = 0, 0, 0
N = 20
for g in range(N):
    state = GameState()
    for turn in range(200):
        if state.current_player == 1:
            player.play_turn(state)
        else:
            moves = state.get_all_legal_moves()
            if moves:
                pm = moves[random.randint(0, len(moves)-1)]
                if pm:
                    m = random.choice(pm)
                    state.make_move(m[0], m[1], m[2], m[3])
            state.end_turn()
        if state.is_game_over():
            break
    if state.winner == 1: wins += 1
    elif state.winner == -1: losses += 1
    else: draws += 1
    print(f'Game {g+1}/{N}: {\"W\" if state.winner==1 else \"L\" if state.winner==-1 else \"D\"}  (Running: {wins}W-{losses}L-{draws}D)')
print(f'Final: {wins}/{N} wins ({wins/N*100:.0f}%)')
"
```

---

## Files

| File | Description |
|------|-------------|
| `python/train_alphazero.py` | Self-play training loop with MCTS |
| `python/game_engine.py` | Python game engine (mirrors TypeScript exactly) |
| `python/neural_network.py` | AlphaZero ResNet (policy + value heads) |
| `python/mcts.py` | Monte Carlo Tree Search with neural network guidance |
| `python/test_engine_parity.py` | 14 tests verifying Python↔TypeScript engine parity |
| `python/requirements.txt` | Dependencies: numpy, torch, gymnasium, tqdm, tensorboard |
| `python/logs/alphazero/training_log.json` | Structured training metrics (JSON) |
| `python/logs/training_output.log` | Raw training console output |
| `python/models/alphazero/` | Saved checkpoints (`checkpoint_NNNN.pt` + `checkpoint_latest.pt`) |

---

## Checkpoints

Each checkpoint (129MB) contains:
- `model_state_dict`: Neural network weights
- `iteration`: Training iteration number

Checkpoints are saved every iteration (configurable via `--save-every`). The `checkpoint_latest.pt` symlink always points to the most recent save.

**Disk management**: Each checkpoint is ~129MB. To keep only the last N:

```bash
cd python/models/alphazero
ls -1 checkpoint_0*.pt | sort | head -n -5 | xargs rm -v
```

---

## Tips

- **Win rate noise**: With only 5 eval games, win rate swings wildly (0-100%). The **policy loss** is the reliable signal — it should trend downward.
- **More MCTS sims = stronger but slower**: 30 sims is fast for training; use 50-100 for evaluation/play.
- **Temperature**: During training, temperature=1.0 (exploration). For evaluation/play, use 0.1 (greedy).
- **Training speed**: ~4-6 min/iteration on Apple M-series with MPS. ~100 iterations ≈ 8-10 hours.
- **Resume is safe**: The `--resume` flag loads weights and iteration count. The replay buffer restarts empty but refills quickly.
