import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Tuple, Optional, Dict, Any, List
from game_engine import GameState, Team, Position
import random


class FreeRangeChessEnv(gym.Env):
    metadata = {'render_modes': ['human', 'ansi'], 'render_fps': 1}
    
    def __init__(self, board_width: int = 10, board_height: int = 10, 
                 max_moves_per_turn: int = 16, max_turns: int = 200,
                 opponent='random'):
        super().__init__()
        
        self.board_width = board_width
        self.board_height = board_height
        self.max_moves_per_turn = max_moves_per_turn
        self.max_turns = max_turns
        self.opponent = opponent
        
        self.observation_space = spaces.Box(
            low=0, high=1, 
            shape=(14, board_height, board_width), 
            dtype=np.float32
        )
        
        max_actions = board_width * board_height * board_width * board_height
        self.action_space = spaces.Discrete(max_actions + 1)
        
        self.game_state: Optional[GameState] = None
        self.agent_team = Team.WHITE
        self.moves_this_turn = 0
        
    def _encode_action(self, from_pos: Position, to_pos: Position) -> int:
        from_x, from_y = from_pos
        to_x, to_y = to_pos
        action = (from_y * self.board_width + from_x) * (self.board_width * self.board_height) + (to_y * self.board_width + to_x)
        return action
    
    def _decode_action(self, action: int) -> Tuple[Optional[Position], Optional[Position]]:
        if action == self.action_space.n - 1:
            return None, None
        
        total_squares = self.board_width * self.board_height
        from_square = action // total_squares
        to_square = action % total_squares
        
        from_x = from_square % self.board_width
        from_y = from_square // self.board_width
        to_x = to_square % self.board_width
        to_y = to_square // self.board_width
        
        return (from_x, from_y), (to_x, to_y)
    
    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        
        self.game_state = GameState(self.board_width, self.board_height)
        self.agent_team = Team.WHITE
        self.moves_this_turn = 0
        
        obs = self.game_state.to_numpy()
        info = self._get_info()
        
        return obs, info
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        if self.game_state is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")
        
        reward = 0.0
        terminated = False
        truncated = False
        
        from_pos, to_pos = self._decode_action(action)
        
        if from_pos is None or to_pos is None:
            if len(self.game_state.pieces_moved) == 0:
                reward = -0.1
            else:
                if not self.game_state.switch_turn():
                    reward = -0.1
                else:
                    self.moves_this_turn = 0
                    
                    if self.game_state.is_game_over():
                        if self.game_state.winner == self.agent_team:
                            reward = 1.0
                            terminated = True
                        else:
                            reward = -1.0
                            terminated = True
                    else:
                        self._opponent_move()
                        
                        if self.game_state.is_game_over():
                            if self.game_state.winner == self.agent_team:
                                reward = 1.0
                                terminated = True
                            else:
                                reward = -1.0
                                terminated = True
        else:
            if self.game_state.current_turn != self.agent_team:
                reward = -0.1
            else:
                target_piece = self.game_state.get_piece(to_pos)
                
                if self.game_state.make_move(from_pos, to_pos):
                    self.moves_this_turn += 1
                    
                    if target_piece:
                        piece_values = {'p': 0.01, 'n': 0.03, 'b': 0.03, 'r': 0.05, 'q': 0.09, 'k': 1.0}
                        reward = piece_values.get(target_piece.piece_type.value, 0.01)
                    else:
                        reward = 0.0
                    
                    if self.game_state.is_game_over():
                        if self.game_state.winner == self.agent_team:
                            reward = 1.0
                            terminated = True
                else:
                    reward = -0.05
        
        if self.game_state.move_count >= self.max_turns:
            truncated = True
        
        obs = self.game_state.to_numpy()
        info = self._get_info()
        
        return obs, reward, terminated, truncated, info
    
    def _opponent_move(self):
        if self.opponent == 'random':
            self._random_opponent_move()
        elif self.opponent == 'greedy':
            self._greedy_opponent_move()
    
    def _random_opponent_move(self):
        max_attempts = 100
        attempts = 0
        while attempts < max_attempts:
            actions = self.game_state.get_all_legal_actions()
            if not actions:
                break
            
            from_pos, to_pos = random.choice(actions)
            self.game_state.make_move(from_pos, to_pos)
            attempts += 1
        
        self.game_state.switch_turn()
    
    def _greedy_opponent_move(self):
        piece_values = {'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9, 'k': 100}
        
        actions = self.game_state.get_all_legal_actions()
        capture_moves = []
        other_moves = []
        
        for from_pos, to_pos in actions:
            target = self.game_state.get_piece(to_pos)
            if target:
                value = piece_values.get(target.piece_type.value, 0)
                capture_moves.append((from_pos, to_pos, value))
            else:
                other_moves.append((from_pos, to_pos))
        
        capture_moves.sort(key=lambda x: x[2], reverse=True)
        
        for from_pos, to_pos, _ in capture_moves:
            self.game_state.make_move(from_pos, to_pos)
        
        remaining_actions = self.game_state.get_all_legal_actions()
        for from_pos, to_pos in remaining_actions:
            self.game_state.make_move(from_pos, to_pos)
        
        self.game_state.switch_turn()
    
    def _get_info(self) -> Dict[str, Any]:
        return {
            'current_turn': self.game_state.current_turn.value if self.game_state else 'w',
            'move_count': self.game_state.move_count if self.game_state else 0,
            'is_game_over': self.game_state.is_game_over() if self.game_state else False,
            'winner': self.game_state.winner.value if (self.game_state and self.game_state.winner) else None,
            'moves_this_turn': self.moves_this_turn,
        }
    
    def render(self):
        if self.game_state is None:
            return
        
        symbols = {
            ('w', 'p'): '♙', ('w', 'n'): '♘', ('w', 'b'): '♗',
            ('w', 'r'): '♖', ('w', 'q'): '♕', ('w', 'k'): '♔',
            ('b', 'p'): '♟', ('b', 'n'): '♞', ('b', 'b'): '♝',
            ('b', 'r'): '♜', ('b', 'q'): '♛', ('b', 'k'): '♚',
        }
        
        print("\n  " + " ".join(chr(97 + i) for i in range(self.board_width)))
        for y in range(self.board_height - 1, -1, -1):
            row_str = f"{y + 1} "
            for x in range(self.board_width):
                piece = self.game_state.board[y][x]
                if piece:
                    symbol = symbols.get((piece.team.value, piece.piece_type.value), '?')
                    row_str += symbol + " "
                else:
                    row_str += ". "
            print(row_str + f"{y + 1}")
        print("  " + " ".join(chr(97 + i) for i in range(self.board_width)))
        print(f"\nTurn: {self.game_state.current_turn.value}, Move: {self.game_state.move_count}")
        
    def close(self):
        pass


class FreeRangeChessMultiActionEnv(FreeRangeChessEnv):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.action_space = spaces.Tuple((
            spaces.Discrete(self.board_width * self.board_height + 1),
            spaces.Discrete(self.board_width * self.board_height + 1),
        ))
        
    def _decode_action(self, action: Tuple[int, int]) -> Tuple[Optional[Position], Optional[Position]]:
        from_action, to_action = action
        
        max_square = self.board_width * self.board_height
        if from_action == max_square or to_action == max_square:
            return None, None
        
        from_x = from_action % self.board_width
        from_y = from_action // self.board_width
        to_x = to_action % self.board_width
        to_y = to_action // self.board_width
        
        return (from_x, from_y), (to_x, to_y)
