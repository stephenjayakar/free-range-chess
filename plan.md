# Free Range Chess - RL Training Plan

## Project Overview
Building an OpenAI Gym interface and RL training system for a chess variant where players can move all pieces once per turn.

## Key Challenges
1. **Large Search Space**: Much larger than standard chess due to multi-piece moves per turn
2. **Game State Representation**: Need efficient encoding for neural networks
3. **Parallelization**: Training requires simulating many games simultaneously
4. **Visualization**: Need to replay games to understand learning progress

## Architecture

### Phase 1: Game Engine Backend (Python)
Create a headless Python game engine that mirrors the TypeScript logic:

**Files to create:**
- `python/game_engine.py` - Core game logic (board state, move validation, game rules)
- `python/pieces.py` - Piece movement logic (pawn, rook, knight, bishop, queen, king)
- `python/gym_env.py` - OpenAI Gym environment wrapper
- `python/server.py` - FastAPI server to bridge Python engine with browser visualization (optional)

**Key Components:**
- Board representation: 10x10 grid
- State tracking: pieces, turn, pieces moved this turn, check status, winner
- Move validation: legal moves for each piece type
- Action space: all possible piece movements for current player
- Observation space: board state as tensor

### Phase 2: OpenAI Gym Environment
**Environment Specifications:**
- **Observation Space**: Multi-channel tensor representing:
  - 6 channels for white pieces (pawn, rook, knight, bishop, queen, king)
  - 6 channels for black pieces
  - 1 channel for pieces that already moved this turn
  - 1 channel for current player indicator
  - Total: 14 x 10 x 10 tensor
  
- **Action Space**: 
  - Option A: Discrete (all from_square, to_square combinations) ~10,000 actions
  - Option B: Multi-discrete (from_square selector + to_square selector)
  - Option C: Sequential action selection per turn with "end turn" action
  
- **Reward Structure**:
  - Win: +1
  - Lose: -1
  - Piece capture: +0.01 to +0.09 (based on piece value)
  - King threatened (check): -0.05
  - Draw/timeout: 0
  - Small negative per step to encourage faster wins: -0.001

### Phase 3: RL Agent Implementation
**Multiple Approaches:**

1. **Deep Q-Network (DQN)** - Start simple
   - Good for learning basic tactics
   - Can use prioritized experience replay
   
2. **Proximal Policy Optimization (PPO)** - Recommended
   - Better for complex action spaces
   - More stable training
   - Good for self-play
   
3. **AlphaZero-style MCTS + Neural Network** - Advanced
   - Combines search with learning
   - Best performance but more complex
   - Use for later iterations

**Files to create:**
- `python/agents/dqn_agent.py` - DQN implementation
- `python/agents/ppo_agent.py` - PPO implementation
- `python/agents/mcts_agent.py` - MCTS with neural network guidance (future)
- `python/agents/network.py` - Neural network architectures (CNN + MLP)
- `python/training/self_play.py` - Self-play training loop
- `python/training/parallel_env.py` - Parallel environment wrapper for vectorized training

### Phase 4: Parallelization & Training
**Parallel Training Strategy:**
- Use `stable-baselines3` with `SubprocVecEnv` for parallel environments
- Run 8-16 parallel game environments simultaneously
- Each environment runs independent games
- Centralized agent collects experiences and updates policy

**Files to create:**
- `python/training/train.py` - Main training script
- `python/training/config.py` - Hyperparameters and configuration
- `python/utils/replay_buffer.py` - Experience replay buffer
- `python/utils/metrics.py` - Training metrics and logging

### Phase 5: Visualization & Analysis
**Game Replay System:**
- Save game states as JSON files during training
- Create web-based replay viewer using existing TypeScript board
- Show move-by-move progression with AI decision explanations

**Files to create:**
- `python/utils/game_recorder.py` - Record games during training
- `src/replay_viewer.html` - Web interface for replay
- `src/replay_viewer.ts` - TypeScript logic to load and display saved games
- `python/analysis/elo_rating.py` - Elo rating system to track improvement
- `python/analysis/visualize_training.py` - Plot training metrics

### Phase 6: Integration & API Server (Optional)
If we want browser-based training visualization:

**Files to create:**
- `python/server.py` - FastAPI server exposing:
  - `/api/step` - Take action in game
  - `/api/reset` - Reset game
  - `/api/state` - Get current state
  - `/api/legal_moves` - Get legal moves
  - `/ws/training` - WebSocket for live training updates
  
- `src/ai_interface.ts` - TypeScript client to communicate with Python backend

### Phase 7: Advanced AI with Difficulty Levels
**Difficulty Implementation:**
- **Easy**: Random legal moves
- **Medium**: Greedy heuristic (piece value + position)
- **Hard**: Minimax search with alpha-beta pruning (depth 2-3)
- **Expert**: MCTS with neural network guidance
- **Master**: Trained RL agent

**Files to create:**
- `python/ai/difficulty_levels.py` - Different AI implementations
- `python/ai/heuristics.py` - Evaluation functions
- `python/ai/minimax.py` - Minimax search with alpha-beta pruning
- `python/ai/mcts.py` - Monte Carlo Tree Search

## Implementation Order

### Step 1: Core Game Engine (High Priority)
1. Port TypeScript game logic to Python
2. Implement all piece movement rules
3. Add game state management
4. Add tests to verify correctness against TypeScript version

### Step 2: Gym Environment (High Priority)
1. Create Gym environment wrapper
2. Define observation and action spaces
3. Implement reward function
4. Test environment with random agents

### Step 3: Basic RL Agent (High Priority)
1. Implement PPO agent using stable-baselines3
2. Create training loop with self-play
3. Add basic logging and checkpointing
4. Train initial model

### Step 4: Parallelization (Medium Priority)
1. Implement vectorized environments
2. Scale to 8-16 parallel environments
3. Optimize for throughput

### Step 5: Visualization (Medium Priority)
1. Implement game recording
2. Create replay viewer
3. Add training metrics dashboard

### Step 6: Advanced Agents (Lower Priority)
1. Implement difficulty levels
2. Add MCTS with neural network
3. Implement Elo rating system
4. Tournament between different agents

### Step 7: API Server (Optional)
1. Create FastAPI server
2. Add WebSocket support
3. Integrate with TypeScript frontend

## Technologies & Libraries
- **Game Engine**: Python 3.10+, NumPy
- **Gym Environment**: gymnasium (OpenAI Gym fork)
- **RL Framework**: stable-baselines3, PyTorch
- **Parallelization**: multiprocessing, stable-baselines3 SubprocVecEnv
- **Server** (optional): FastAPI, uvicorn, websockets
- **Visualization**: matplotlib, tensorboard
- **Testing**: pytest

## Expected Outcomes
1. Functional Gym environment for the chess variant
2. Trained RL agent that can play the game competently
3. Parallel training system for efficient learning
4. Game replay and analysis tools
5. Multiple AI difficulty levels
6. Insights into how the agent learns strategy

## Performance Targets
- **Training**: 1000+ games per minute (with parallelization)
- **Model Size**: < 50MB for neural network
- **Inference**: < 50ms per action selection
- **Training Time**: Reasonable agent in 6-12 hours on modern CPU/GPU

## Next Steps
1. Create Python game engine with unit tests
2. Build and test Gym environment
3. Implement PPO agent and start training
4. Add parallelization for faster learning
5. Create visualization tools
6. Experiment with advanced techniques
