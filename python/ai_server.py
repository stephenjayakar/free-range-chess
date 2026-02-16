#!/usr/bin/env python3
"""
Inference server for Free Range Chess AlphaZero model.

Exposes a single endpoint that accepts a board state and returns
the AI's moves for a complete turn using MCTS + trained neural network.

Usage:
    cd python && source venv/bin/activate
    python ai_server.py                                    # uses checkpoint_latest.pt
    python ai_server.py --checkpoint models/alphazero/checkpoint_0024.pt
    python ai_server.py --simulations 100 --port 8080
"""

import os
import argparse
import time
import torch
import numpy as np
from typing import List, Dict, Optional, Tuple
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from game_engine import GameState, Team, Piece, PieceType, Position
from neural_network import ChessNet, create_model, NUM_ACTIONS, END_TURN_ACTION, decode_action
from mcts import MCTS, MCTSPlayer

# ================================================================
# Request / Response models
# ================================================================

class SquarePiece(BaseModel):
    """A piece on a square. Matches the browser's format."""
    square: str       # e.g. "0,0", "4,1" — the board uses "x,y" notation
    piece: str        # e.g. "wp", "bk", "br"

class PlayTurnRequest(BaseModel):
    """Board state sent from the browser."""
    pieces: List[SquarePiece]
    turn: str                          # "w" or "b"
    pieces_moved: List[str] = []       # squares already moved this turn ("x,y" format)
    board_width: int = 10
    board_height: int = 10

class MoveAction(BaseModel):
    square_from: str   # e.g. "0,0"
    square_to: str     # e.g. "0,2"

class PlayTurnResponse(BaseModel):
    moves: List[MoveAction]
    thinking_time_ms: int
    simulations: int

# ================================================================
# Coordinate conversion (browser "x,y" square notation ↔ engine tuples)
# ================================================================

def square_to_xy(square: str, board_width: int = 10) -> Tuple[int, int]:
    """Convert square notation "x,y" to (x, y) tuple.
    
    The browser/chessboard uses "x,y" format: e.g. "0,0" = bottom-left, "9,9" = top-right.
    """
    parts = square.split(',')
    return (int(parts[0]), int(parts[1]))

def xy_to_square(x: int, y: int) -> str:
    """Convert (x, y) tuple to "x,y" square notation."""
    return f"{x},{y}"

# ================================================================
# Build GameState from browser data
# ================================================================

def build_game_state(req: PlayTurnRequest) -> GameState:
    """Reconstruct a GameState from the browser's piece list."""
    gs = GameState.__new__(GameState)
    gs.board_width = req.board_width
    gs.board_height = req.board_height
    gs.board = [[None for _ in range(req.board_width)] for _ in range(req.board_height)]
    gs.current_turn = Team.WHITE if req.turn == "w" else Team.BLACK
    gs.winner = None
    gs.move_count = 0
    gs._hash = None

    # Place pieces
    for sp in req.pieces:
        x, y = square_to_xy(sp.square, req.board_width)
        piece = Piece.from_string(sp.piece)
        gs.board[y][x] = piece

    # Track already-moved pieces
    gs.pieces_moved = set()
    for sq in req.pieces_moved:
        gs.pieces_moved.add(square_to_xy(sq, req.board_width))

    return gs

# ================================================================
# App setup
# ================================================================

app = FastAPI(title="Free Range Chess AI Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model state (loaded on startup)
model_state = {
    "network": None,
    "device": None,
    "simulations": 50,
    "checkpoint_path": None,
}

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model_loaded": model_state["network"] is not None,
        "checkpoint": model_state["checkpoint_path"],
        "device": model_state["device"],
        "simulations": model_state["simulations"],
    }

@app.post("/api/play-turn", response_model=PlayTurnResponse)
def play_turn(req: PlayTurnRequest):
    """Accept a board state, run MCTS, return the AI's moves for a full turn."""
    network = model_state["network"]
    if network is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    t0 = time.time()

    # Rebuild game state from browser data
    state = build_game_state(req)

    # Run MCTS to play a full turn
    moves_made: List[MoveAction] = []
    max_actions = 50

    network.eval()
    with torch.no_grad():
        for _ in range(max_actions):
            if state.is_game_over():
                break

            actions = state.get_all_legal_actions()
            if not actions:
                break

            mcts = MCTS(
                network,
                c_puct=1.5,
                num_simulations=model_state["simulations"],
                temperature=0.1,  # near-greedy for play
            )

            action_probs, value = mcts.search(state)

            # Pick best action
            action = int(np.argmax(action_probs))

            if action == END_TURN_ACTION:
                break

            from_pos, to_pos = decode_action(action)
            if from_pos is None or to_pos is None:
                break

            if not state.make_move(from_pos, to_pos):
                break

            moves_made.append(MoveAction(
                square_from=xy_to_square(*from_pos),
                square_to=xy_to_square(*to_pos),
            ))

    elapsed_ms = int((time.time() - t0) * 1000)

    return PlayTurnResponse(
        moves=moves_made,
        thinking_time_ms=elapsed_ms,
        simulations=model_state["simulations"],
    )

# ================================================================
# Model loading
# ================================================================

def load_model(checkpoint_path: str, device: str, simulations: int):
    """Load the AlphaZero model from a checkpoint."""
    print(f"Loading model from {checkpoint_path} on {device}...")

    if not os.path.exists(checkpoint_path):
        print(f"ERROR: Checkpoint not found: {checkpoint_path}")
        return

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)

    cfg = checkpoint.get("config", {})
    res_blocks = cfg.get("num_res_blocks", 6)
    channels = cfg.get("channels", 128)

    network = create_model(res_blocks, channels, device)
    network.load_state_dict(checkpoint["model_state_dict"])
    network.eval()

    iteration = checkpoint.get("iteration", "?")
    print(f"  Loaded iteration {iteration} ({res_blocks} res blocks, {channels} channels)")
    print(f"  MCTS simulations: {simulations}")
    print(f"  Device: {device}")

    model_state["network"] = network
    model_state["device"] = device
    model_state["simulations"] = simulations
    model_state["checkpoint_path"] = checkpoint_path


# ================================================================
# CLI
# ================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Free Range Chess AI inference server")
    parser.add_argument("--checkpoint", type=str,
                        default="./models/alphazero/checkpoint_latest.pt",
                        help="Path to model checkpoint")
    parser.add_argument("--device", type=str, default=None,
                        help="Device (cuda/mps/cpu). Auto-detects if not set.")
    parser.add_argument("--simulations", type=int, default=50,
                        help="MCTS simulations per move decision")
    parser.add_argument("--port", type=int, default=8080,
                        help="Server port")
    parser.add_argument("--res-blocks", type=int, default=6)
    parser.add_argument("--channels", type=int, default=128)

    args = parser.parse_args()

    if args.device is None:
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
    else:
        device = args.device

    load_model(args.checkpoint, device, args.simulations)

    print(f"\nStarting AI server on http://localhost:{args.port}")
    print(f"  POST /api/play-turn  — send board state, get AI moves")
    print(f"  GET  /api/health     — check server status\n")

    uvicorn.run(app, host="0.0.0.0", port=args.port)
