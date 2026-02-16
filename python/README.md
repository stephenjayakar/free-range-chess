# Free Range Chess - RL Training System

This directory contains a complete RL training system for the Free Range Chess variant with a web-based training dashboard.

## Overview

Free Range Chess is a chess variant where:
- Board is 10x10
- Players can move ALL their pieces once per turn (instead of just one piece)
- Pieces have a max distance of 7 squares (except knights/pawns)
- Otherwise follows standard chess piece movement rules
- Game ends when a king is captured or put in check at end of turn

## Quick Setup

### Option 1: Automated Setup (Recommended)

```bash
cd python
./setup.sh
```

This will:
- Create a virtual environment
- Install all dependencies
- Give you instructions to get started

### Option 2: Manual Setup

```bash
cd python
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Quick Start

### Method 1: Web Dashboard (Easiest)

Start the web server:
```bash
source venv/bin/activate  # If you created a venv
python server.py
```

Then open http://localhost:8000 in your browser to:
- ✅ Start/stop training with a visual interface
- ✅ Monitor training progress in real-time
- ✅ View system metrics (CPU, memory)
- ✅ See training logs live
- ✅ Browse saved models

### Method 2: Command Line

#### 1. Test the Environment

```bash
python test_env.py
```

This will run a simple test to verify the environment is working.

#### 2. Train a PPO Agent

```bash
# Train with random opponent (easiest)
python train_ppo.py --mode train --timesteps 1000000 --n-envs 8 --opponent random

# Train with greedy opponent (harder)
python train_ppo.py --mode train --timesteps 2000000 --n-envs 8 --opponent greedy
```

Training will create:
- `./logs/` - Tensorboard logs and training output
- `./models/` - Saved model checkpoints

#### 3. Monitor Training (Tensorboard)

```bash
tensorboard --logdir ./logs
```

Open http://localhost:6006 in your browser to view training progress.

#### 4. Evaluate a Trained Model

```bash
python train_ppo.py --mode eval --model-path ./models/ppo_chess_random_TIMESTAMP/final_model --n-episodes 100
```

#### 5. Watch the Agent Play

```bash
python train_ppo.py --mode play --model-path ./models/ppo_chess_random_TIMESTAMP/final_model
```

## Files

### Core System
- `game_engine.py` - Core game logic (board state, move validation, piece movement)
- `gym_env.py` - OpenAI Gym environment wrapper
- `train_ppo.py` - PPO training script with parallel environments
- `test_env.py` - Simple environment test

### Web Dashboard
- `server.py` - FastAPI web server for training management
- `web/index.html` - Training dashboard UI

### Setup
- `requirements.txt` - Python dependencies
- `setup.sh` - Automated setup script
- `start_server.sh` - Quick server startup script

## Architecture

### Game Engine
- **Board**: 10x10 grid with standard chess pieces
- **State**: Numpy tensor (14, 10, 10)
  - 6 channels for white pieces (p, n, b, r, q, k)
  - 6 channels for black pieces
  - 1 channel for pieces that moved this turn
  - 1 channel for current player indicator
  
### RL Environment
- **Observation Space**: Box(0, 1, (14, 10, 10))
- **Action Space**: Discrete(10001)
  - Actions 0-9999: move from (x1,y1) to (x2,y2)
  - Action 10000: end turn
  
### Reward Structure
- Win: +1.0
- Loss: -1.0
- Capture piece: +0.01 to +0.09 (based on piece value)
- King threatened: -0.05
- Invalid move: -0.05
- End turn with no moves: -0.1

### Training
- **Algorithm**: PPO (Proximal Policy Optimization)
- **Parallelization**: 8+ environments running simultaneously
- **Policy Network**: MLP (Multi-Layer Perceptron)
- **Opponent**: Random or greedy baseline

## Parallelization

The training system uses `SubprocVecEnv` from stable-baselines3 to run multiple game environments in parallel. This dramatically speeds up training:

- 1 environment: ~50 games/hour
- 8 environments: ~400 games/hour
- 16 environments: ~800 games/hour

Adjust `--n-envs` based on your CPU cores.

## Performance Expectations

### Training Times (on modern CPU)
- **Random opponent**: 6-12 hours for competent play
- **Greedy opponent**: 24-48 hours for competent play

### Expected Win Rates
After training:
- vs Random: 80-95%
- vs Greedy: 50-70%

## Next Steps

### Implemented:
- ✅ Core game engine
- ✅ Gym environment
- ✅ PPO agent with self-play
- ✅ Parallel training

### TODO:
- [ ] Game recording and replay system
- [ ] Visualization dashboard
- [ ] Advanced opponents (minimax, MCTS)
- [ ] Difficulty levels
- [ ] Tournament system
- [ ] Elo rating tracker
- [ ] Integration with TypeScript frontend

## Advanced Usage

### Custom Training Parameters

```bash
python train_ppo.py \
    --mode train \
    --timesteps 5000000 \
    --n-envs 16 \
    --opponent greedy
```

### Self-Play Training

To train agents that play against themselves (coming soon):

```python
# In train_ppo.py, modify to load previous best model as opponent
opponent_model = PPO.load("./models/best_model")
```

## Troubleshooting

**ImportError: No module named 'gymnasium'**
```bash
pip install -r requirements.txt
```

**Training is slow**
- Increase `--n-envs` (requires more CPU cores)
- Decrease `--n-steps` in the training script
- Use GPU if available (PyTorch will auto-detect)

**Agent not learning**
- Try training longer (more timesteps)
- Start with random opponent first
- Check tensorboard logs for reward progression
- Adjust learning rate or other hyperparameters

## Contributing

See `../plan.md` for the full development roadmap.
