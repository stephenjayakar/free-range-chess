#!/usr/bin/env python3
"""
AlphaZero-style self-play training for Free Range Chess.

Training loop:
1. Self-play: Two copies of the network play against each other using MCTS
2. Collect training data: (state, MCTS policy, game outcome)
3. Train network on collected data
4. Repeat

The key insight: the network learns from MCTS's improved policy (which looks
ahead), so each iteration the network gets stronger, which makes MCTS stronger,
which produces better training data.

Supports graceful stop (Ctrl+C / SIGINT) — saves checkpoint before exiting.
Resume with --resume <checkpoint.pt>
"""

import os
import sys
import json
import time
import signal
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import deque
from tqdm import tqdm

from game_engine import GameState, Team
from neural_network import ChessNet, create_model, count_parameters, NUM_ACTIONS
from mcts import MCTSPlayer, MCTS, get_legal_action_mask, END_TURN_ACTION, encode_action

# ================================================================
# Graceful shutdown
# ================================================================

_STOP_REQUESTED = False

def _signal_handler(signum, frame):
    global _STOP_REQUESTED
    if _STOP_REQUESTED:
        print("\n  Force quit!")
        sys.exit(1)
    _STOP_REQUESTED = True
    print("\n  ⏹ Stop requested — will save checkpoint after current phase completes...")
    print("  (Press Ctrl+C again to force quit)")

signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

# ================================================================
# Configuration
# ================================================================

class Config:
    # Board
    board_width = 10
    board_height = 10

    # Neural network
    num_res_blocks = 6
    channels = 128

    # MCTS
    num_simulations = 50       # simulations per move during self-play
    c_puct = 1.5
    dirichlet_alpha = 0.3
    dirichlet_epsilon = 0.25

    # Training
    num_iterations = 100       # total training iterations
    num_self_play_games = 20   # games per iteration
    num_epochs = 10            # training epochs per iteration
    batch_size = 128
    learning_rate = 0.001
    lr_decay = 0.1
    lr_decay_steps = [50, 75]
    weight_decay = 1e-4
    max_replay_buffer = 50000  # max training examples to keep
    temperature_threshold = 15 # after this many moves, use temp=0

    # Game limits
    max_turns = 150            # max turns before draw

    # Evaluation
    eval_games = 10            # games to evaluate new model vs old
    eval_simulations = 50      # MCTS sims during evaluation
    win_threshold = 0.55       # new model must win > this fraction

    # Saving
    save_dir = "./models/alphazero"
    log_dir = "./logs/alphazero"
    save_every = 1             # save checkpoint every N iterations (default: every iteration)

    # Device
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"


# ================================================================
# Self-play
# ================================================================

def self_play_game(network: ChessNet, config: Config, game_idx: int = 0) -> List[Dict]:
    """Play one self-play game and collect training data.

    Both sides use the same network + MCTS.
    Returns list of training examples.
    """
    state = GameState(config.board_width, config.board_height)
    training_data = []
    turn_count = 0

    while not state.is_game_over() and turn_count < config.max_turns:
        # Use temperature 1.0 early for exploration, 0 later for quality
        temp = 1.0 if turn_count < config.temperature_threshold else 0.1

        player = MCTSPlayer(
            network,
            num_simulations=config.num_simulations,
            c_puct=config.c_puct,
            temperature=temp,
        )

        turn_data = player.play_turn(state, collect_data=True)
        training_data.extend(turn_data)
        turn_count += 1

        if state.is_game_over():
            break

    # Assign game outcome to all training examples
    if state.winner is not None:
        winner = state.winner
    else:
        winner = None  # draw

    examples = []
    for td in training_data:
        if winner is None:
            value = 0.0
        elif td['turn'] == winner:
            value = 1.0
        else:
            value = -1.0

        examples.append({
            'state': td['state'],
            'policy': td['policy'],
            'value': value,
        })

    return examples


def run_self_play(network: ChessNet, config: Config, iteration: int) -> List[Dict]:
    """Run multiple self-play games and collect training data."""
    global _STOP_REQUESTED
    all_examples = []

    network.eval()

    print(f"  Self-play: {config.num_self_play_games} games, {config.num_simulations} MCTS sims each...")

    for game_idx in tqdm(range(config.num_self_play_games), desc="  Games"):
        if _STOP_REQUESTED:
            print(f"  Stop requested — played {game_idx}/{config.num_self_play_games} games")
            break
        examples = self_play_game(network, config, game_idx)
        all_examples.extend(examples)

    wins_w = sum(1 for e in all_examples if e['value'] == 1.0)
    wins_b = sum(1 for e in all_examples if e['value'] == -1.0)
    draws = sum(1 for e in all_examples if e['value'] == 0.0)
    print(f"  Collected {len(all_examples)} examples "
          f"(value>0: {wins_w}, value<0: {wins_b}, draw: {draws})")

    return all_examples


# ================================================================
# Training
# ================================================================

def train_network(network: ChessNet, replay_buffer: deque, config: Config,
                  iteration: int) -> Dict:
    """Train the network on collected self-play data."""
    if len(replay_buffer) < config.batch_size:
        print(f"  Not enough data ({len(replay_buffer)} < {config.batch_size}), skipping training")
        return {'policy_loss': 0, 'value_loss': 0, 'total_loss': 0}

    network.train()

    # Prepare data
    examples = list(replay_buffer)
    random.shuffle(examples)

    states = np.array([e['state'] for e in examples], dtype=np.float32)
    policies = np.array([e['policy'] for e in examples], dtype=np.float32)
    values = np.array([e['value'] for e in examples], dtype=np.float32).reshape(-1, 1)

    dataset = TensorDataset(
        torch.FloatTensor(states),
        torch.FloatTensor(policies),
        torch.FloatTensor(values),
    )
    loader = DataLoader(dataset, batch_size=config.batch_size, shuffle=True,
                       drop_last=True)

    # Learning rate schedule
    lr = config.learning_rate
    for step in config.lr_decay_steps:
        if iteration >= step:
            lr *= config.lr_decay

    optimizer = optim.Adam(network.parameters(), lr=lr,
                          weight_decay=config.weight_decay)

    total_policy_loss = 0
    total_value_loss = 0
    total_loss = 0
    num_batches = 0

    for epoch in range(config.num_epochs):
        for batch_states, batch_policies, batch_values in loader:
            batch_states = batch_states.to(config.device)
            batch_policies = batch_policies.to(config.device)
            batch_values = batch_values.to(config.device)

            # Forward
            pred_policy_logits, pred_values = network(batch_states)

            # Policy loss: cross-entropy with MCTS policy
            policy_loss = -torch.mean(
                torch.sum(batch_policies * torch.log_softmax(pred_policy_logits, dim=1), dim=1)
            )

            # Value loss: MSE
            value_loss = torch.mean((pred_values - batch_values) ** 2)

            # Total loss
            loss = policy_loss + value_loss

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(network.parameters(), 1.0)
            optimizer.step()

            total_policy_loss += policy_loss.item()
            total_value_loss += value_loss.item()
            total_loss += loss.item()
            num_batches += 1

    avg_policy = total_policy_loss / max(num_batches, 1)
    avg_value = total_value_loss / max(num_batches, 1)
    avg_total = total_loss / max(num_batches, 1)

    print(f"  Training: {num_batches} batches, "
          f"policy_loss={avg_policy:.4f}, value_loss={avg_value:.4f}, "
          f"total_loss={avg_total:.4f}")

    return {
        'policy_loss': avg_policy,
        'value_loss': avg_value,
        'total_loss': avg_total,
    }


# ================================================================
# Evaluation
# ================================================================

def evaluate_against_random(network: ChessNet, config: Config,
                            num_games: int = 10) -> Dict:
    """Evaluate network (with MCTS) against a random opponent."""
    network.eval()
    wins = 0
    losses = 0
    draws = 0

    for game_idx in range(num_games):
        state = GameState(config.board_width, config.board_height)
        turn_count = 0

        while not state.is_game_over() and turn_count < config.max_turns:
            if state.current_turn == Team.WHITE:
                # Network plays as white
                player = MCTSPlayer(
                    network,
                    num_simulations=config.eval_simulations,
                    c_puct=config.c_puct,
                    temperature=0.1,
                )
                player.play_turn(state)
            else:
                # Random opponent
                _play_random_turn(state)

            turn_count += 1

        if state.winner == Team.WHITE:
            wins += 1
        elif state.winner == Team.BLACK:
            losses += 1
        else:
            draws += 1

    return {'wins': wins, 'losses': losses, 'draws': draws,
            'win_rate': wins / max(num_games, 1)}


def _play_random_turn(state: GameState):
    """Play a random turn for the current player."""
    max_actions = 50
    for _ in range(max_actions):
        actions = state.get_all_legal_actions()
        if not actions:
            break
        from_pos, to_pos = random.choice(actions)
        state.make_move(from_pos, to_pos)

    if len(state.pieces_moved) > 0:
        state.switch_turn()


def _play_greedy_turn(state: GameState):
    """Play a greedy turn (captures first, then random)."""
    piece_values = {
        'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9, 'k': 100
    }
    max_actions = 50
    for _ in range(max_actions):
        actions = state.get_all_legal_actions()
        if not actions:
            break

        # Sort by capture value
        scored = []
        for from_pos, to_pos in actions:
            target = state.get_piece(to_pos)
            val = piece_values.get(target.piece_type.value, 0) if target else 0
            scored.append((from_pos, to_pos, val))
        scored.sort(key=lambda x: x[2], reverse=True)

        if scored[0][2] > 0:
            # Take best capture
            state.make_move(scored[0][0], scored[0][1])
        else:
            # Random non-capture
            from_pos, to_pos, _ = random.choice(scored)
            state.make_move(from_pos, to_pos)

    if len(state.pieces_moved) > 0:
        state.switch_turn()


# ================================================================
# Checkpoint helpers
# ================================================================

def save_checkpoint(network: ChessNet, config: Config, iteration: int,
                    history: list, tag: str = None):
    """Save a training checkpoint with model weights and training log."""
    os.makedirs(config.save_dir, exist_ok=True)

    if tag:
        ckpt_path = os.path.join(config.save_dir, f"checkpoint_{tag}.pt")
    else:
        ckpt_path = os.path.join(config.save_dir, f"checkpoint_{iteration+1:04d}.pt")

    torch.save({
        'iteration': iteration,
        'model_state_dict': network.state_dict(),
        'config': {
            'num_res_blocks': config.num_res_blocks,
            'channels': config.channels,
        },
    }, ckpt_path)

    # Also save a "latest" copy for easy resume
    latest_path = os.path.join(config.save_dir, "checkpoint_latest.pt")
    torch.save({
        'iteration': iteration,
        'model_state_dict': network.state_dict(),
        'config': {
            'num_res_blocks': config.num_res_blocks,
            'channels': config.channels,
        },
    }, latest_path)

    # Save training log
    if history:
        log_path = os.path.join(config.log_dir, "training_log.json")
        os.makedirs(config.log_dir, exist_ok=True)
        with open(log_path, 'w') as f:
            json.dump(history, f, indent=2)

    print(f"  💾 Saved checkpoint: {ckpt_path}")
    return ckpt_path


# ================================================================
# Main training loop
# ================================================================

def train(config: Optional[Config] = None, resume_from: Optional[str] = None):
    """Main AlphaZero training loop."""
    global _STOP_REQUESTED

    if config is None:
        config = Config()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(config.save_dir, exist_ok=True)
    os.makedirs(config.log_dir, exist_ok=True)

    print("=" * 60)
    print("Free Range Chess — AlphaZero Training")
    print("=" * 60)
    print(f"Device: {config.device}")
    print(f"Board: {config.board_width}x{config.board_height}")
    print(f"Network: {config.num_res_blocks} res blocks, {config.channels} channels")
    print(f"MCTS: {config.num_simulations} simulations")
    print(f"Self-play: {config.num_self_play_games} games/iteration")
    print(f"Training: {config.num_epochs} epochs, batch_size={config.batch_size}")
    print(f"Checkpoint: every {config.save_every} iteration(s)")
    print(f"Graceful stop: Ctrl+C saves checkpoint then exits")
    print()

    # Create or load network
    if resume_from:
        print(f"Resuming from {resume_from}")
        network = create_model(config.num_res_blocks, config.channels, config.device)
        checkpoint = torch.load(resume_from, map_location=config.device, weights_only=False)
        network.load_state_dict(checkpoint['model_state_dict'])
        start_iteration = checkpoint.get('iteration', 0) + 1
        # Replay buffer not saved in checkpoint — starts fresh (acceptable)
        replay_buffer = deque(maxlen=config.max_replay_buffer)
        print(f"  Loaded iteration {checkpoint.get('iteration', '?')}, resuming at iteration {start_iteration + 1}")
    else:
        network = create_model(config.num_res_blocks, config.channels, config.device)
        start_iteration = 0
        replay_buffer = deque(maxlen=config.max_replay_buffer)

    print(f"Model parameters: {count_parameters(network):,}")
    print()

    # Load existing training history if resuming
    history = []
    log_path = os.path.join(config.log_dir, "training_log.json")
    if resume_from and os.path.exists(log_path):
        try:
            with open(log_path, 'r') as f:
                history = json.load(f)
            print(f"  Loaded {len(history)} previous log entries")
        except Exception as e:
            print(f"  Warning: Could not load training log: {e}")
    print()

    for iteration in range(start_iteration, config.num_iterations):
        if _STOP_REQUESTED:
            print(f"\n  ⏹ Stop requested before iteration {iteration + 1}")
            save_checkpoint(network, config, iteration - 1, history, tag="interrupted")
            print("  Training stopped gracefully.")
            return network, history

        iter_start = time.time()
        print(f"{'='*60}")
        print(f"Iteration {iteration + 1}/{config.num_iterations}")
        print(f"{'='*60}")

        # 1. Self-play
        sp_start = time.time()
        examples = run_self_play(network, config, iteration)
        replay_buffer.extend(examples)
        sp_time = time.time() - sp_start
        print(f"  Self-play time: {sp_time:.1f}s, buffer size: {len(replay_buffer)}")

        if _STOP_REQUESTED:
            print(f"  ⏹ Stop requested after self-play")
            save_checkpoint(network, config, iteration - 1, history, tag="interrupted")
            print("  Training stopped gracefully (self-play data NOT trained on).")
            return network, history

        # 2. Train
        train_start = time.time()
        train_metrics = train_network(network, replay_buffer, config, iteration)
        train_time = time.time() - train_start
        print(f"  Training time: {train_time:.1f}s")

        # 3. Evaluate against random
        eval_start = time.time()
        eval_results = evaluate_against_random(network, config, num_games=config.eval_games)
        eval_time = time.time() - eval_start
        print(f"  Eval vs Random: W={eval_results['wins']} L={eval_results['losses']} "
              f"D={eval_results['draws']} ({eval_results['win_rate']*100:.0f}% win rate)")
        print(f"  Eval time: {eval_time:.1f}s")

        iter_time = time.time() - iter_start
        print(f"  Total iteration time: {iter_time:.1f}s")

        # Log
        log_entry = {
            'iteration': iteration + 1,
            'self_play_examples': len(examples),
            'replay_buffer_size': len(replay_buffer),
            'self_play_time': sp_time,
            'train_time': train_time,
            'eval_time': eval_time,
            'total_time': iter_time,
            **train_metrics,
            **eval_results,
        }
        history.append(log_entry)

        # Save checkpoint every N iterations
        if (iteration + 1) % config.save_every == 0 or iteration == config.num_iterations - 1:
            save_checkpoint(network, config, iteration, history)

        print()

    print("=" * 60)
    print("Training complete!")
    print("=" * 60)

    # Save final model
    save_checkpoint(network, config, config.num_iterations - 1, history, tag="final")

    return network, history


# ================================================================
# CLI
# ================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='AlphaZero training for Free Range Chess')
    parser.add_argument('--iterations', type=int, default=100, help='Training iterations')
    parser.add_argument('--games', type=int, default=20, help='Self-play games per iteration')
    parser.add_argument('--simulations', type=int, default=50, help='MCTS simulations per move')
    parser.add_argument('--res-blocks', type=int, default=6, help='ResNet blocks')
    parser.add_argument('--channels', type=int, default=128, help='ResNet channels')
    parser.add_argument('--batch-size', type=int, default=128, help='Training batch size')
    parser.add_argument('--lr', type=float, default=0.001, help='Learning rate')
    parser.add_argument('--epochs', type=int, default=10, help='Training epochs per iteration')
    parser.add_argument('--resume', type=str, default=None, help='Resume from checkpoint path')
    parser.add_argument('--eval-games', type=int, default=10, help='Evaluation games per iteration')
    parser.add_argument('--max-turns', type=int, default=150, help='Max turns per game')
    parser.add_argument('--device', type=str, default=None, help='Device (cuda/mps/cpu)')
    parser.add_argument('--save-every', type=int, default=1, help='Save checkpoint every N iterations')

    args = parser.parse_args()

    config = Config()
    config.num_iterations = args.iterations
    config.num_self_play_games = args.games
    config.num_simulations = args.simulations
    config.num_res_blocks = args.res_blocks
    config.channels = args.channels
    config.batch_size = args.batch_size
    config.learning_rate = args.lr
    config.num_epochs = args.epochs
    config.eval_games = args.eval_games
    config.max_turns = args.max_turns
    config.save_every = args.save_every

    if args.device:
        config.device = args.device

    train(config, resume_from=args.resume)
