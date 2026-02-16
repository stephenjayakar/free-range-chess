"""
Free Range Chess game engine.
10x10 board, all pieces can move once per turn.
Exactly mirrors the TypeScript pieces.ts / index.ts logic.

Key rules matching TypeScript:
- Pawn: moves 1 square in any direction (all 8 dirs), captures same as move
- Bishop: slides up to 7 diagonally, blocked by pieces, captures enemies
- Rook: slides up to 7 straight, blocked by pieces, captures enemies  
- Queen: slides up to 7 in all 8 dirs, blocked by pieces, captures enemies
- Knight: L-shape jumps (2+1), can jump over pieces, captures enemies
- King: same as pawn but cannot move adjacent to enemy king
- Cannot capture the king directly (TS blocks this in validation)
- Win condition: at end of your turn, if YOUR king is in check, you LOSE
- Each piece can only move once per turn (tracked by destination square)
"""

import copy
from typing import List, Tuple, Optional, Set, Dict
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

Position = Tuple[int, int]

class Team(Enum):
    WHITE = 'w'
    BLACK = 'b'

    def opposite(self):
        return Team.BLACK if self == Team.WHITE else Team.WHITE

class PieceType(Enum):
    PAWN = 'p'
    KNIGHT = 'n'
    BISHOP = 'b'
    ROOK = 'r'
    QUEEN = 'q'
    KING = 'k'

PIECE_VALUES = {
    PieceType.PAWN: 1,
    PieceType.KNIGHT: 3,
    PieceType.BISHOP: 3,
    PieceType.ROOK: 5,
    PieceType.QUEEN: 9,
    PieceType.KING: 100,
}

# Integer encoding for pieces (for fast numpy conversion)
PIECE_TO_INT: Dict[Tuple[str, str], int] = {}
_idx = 1
for t in ['w', 'b']:
    for p in ['p', 'n', 'b', 'r', 'q', 'k']:
        PIECE_TO_INT[(t, p)] = _idx
        _idx += 1

@dataclass
class Piece:
    team: Team
    piece_type: PieceType

    def to_string(self) -> str:
        return self.team.value + self.piece_type.value

    @staticmethod
    def from_string(s: str) -> 'Piece':
        return Piece(Team(s[0]), PieceType(s[1]))

    def __hash__(self):
        return hash((self.team, self.piece_type))

    def __eq__(self, other):
        if not isinstance(other, Piece):
            return False
        return self.team == other.team and self.piece_type == other.piece_type


class GameState:
    __slots__ = ['board_width', 'board_height', 'board', 'current_turn',
                 'pieces_moved', 'winner', 'move_count', '_hash']

    def __init__(self, board_width: int = 10, board_height: int = 10):
        self.board_width = board_width
        self.board_height = board_height
        self.board: List[List[Optional[Piece]]] = self._initialize_board()
        self.current_turn = Team.WHITE
        self.pieces_moved: Set[Position] = set()
        self.winner: Optional[Team] = None
        self.move_count = 0
        self._hash: Optional[int] = None

    def _initialize_board(self) -> List[List[Optional[Piece]]]:
        board = [[None for _ in range(self.board_width)] for _ in range(self.board_height)]
        W, B = Team.WHITE, Team.BLACK
        P, N, Bi, R, Q, K = PieceType.PAWN, PieceType.KNIGHT, PieceType.BISHOP, PieceType.ROOK, PieceType.QUEEN, PieceType.KING
        bw, bh = self.board_width, self.board_height

        # White pieces (matching TypeScript startPosition exactly)
        white = [
            (0,1,P),(1,1,P),(2,1,P),(3,1,P),(4,1,P),(5,1,P),(6,1,P),(7,1,P),
            (0,0,R),(1,0,N),(2,0,Bi),(3,0,Q),(4,0,K),(5,0,Bi),(6,0,N),(7,0,R),
        ]
        # Black pieces
        black = [
            (bw-1,bh-2,P),(bw-2,bh-2,P),(bw-3,bh-2,P),(bw-4,bh-2,P),
            (bw-5,bh-2,P),(bw-6,bh-2,P),(bw-7,bh-2,P),(bw-8,bh-2,P),
            (bw-1,bh-1,R),(bw-2,bh-1,N),(bw-3,bh-1,Bi),(bw-4,bh-1,Q),
            (bw-5,bh-1,K),(bw-6,bh-1,Bi),(bw-7,bh-1,N),(bw-8,bh-1,R),
        ]

        for x, y, pt in white:
            board[y][x] = Piece(W, pt)
        for x, y, pt in black:
            board[y][x] = Piece(B, pt)

        return board

    def _is_in_bounds(self, pos: Position) -> bool:
        x, y = pos
        return 0 <= x < self.board_width and 0 <= y < self.board_height

    def get_piece(self, pos: Position) -> Optional[Piece]:
        x, y = pos
        if not self._is_in_bounds(pos):
            return None
        return self.board[y][x]

    def set_piece(self, pos: Position, piece: Optional[Piece]):
        x, y = pos
        self.board[y][x] = piece
        self._hash = None

    # ================================================================
    # Move generation — exactly mirrors TypeScript pieces.ts
    # ================================================================

    def get_piece_moves(self, pos: Position, piece: Piece) -> List[Position]:
        """Get raw moves for a piece (ignoring pieces_moved tracking)."""
        pt = piece.piece_type
        team = piece.team
        if pt == PieceType.PAWN:
            return self._path_march(pos, team, 1, True, True)
        elif pt == PieceType.KNIGHT:
            return self._get_knight_moves(pos, team)
        elif pt == PieceType.BISHOP:
            return self._path_march(pos, team, 7, True, False)
        elif pt == PieceType.ROOK:
            return self._path_march(pos, team, 7, False, True)
        elif pt == PieceType.QUEEN:
            return self._path_march(pos, team, 7, True, True)
        elif pt == PieceType.KING:
            return self._get_king_moves(pos, team)
        return []

    def get_legal_moves(self, pos: Position) -> List[Position]:
        """Get legal moves for a piece at pos, respecting turn and pieces_moved."""
        piece = self.get_piece(pos)
        if piece is None or piece.team != self.current_turn:
            return []
        if pos in self.pieces_moved:
            return []
        moves = self.get_piece_moves(pos, piece)
        # Filter out king captures (matching TS: can't capture king)
        result = []
        for m in moves:
            target = self.get_piece(m)
            if target and target.piece_type == PieceType.KING:
                continue
            result.append(m)
        return result

    def _get_knight_moves(self, pos: Position, team: Team) -> List[Position]:
        x, y = pos
        deltas = [(1,2),(-1,2),(1,-2),(-1,-2),(2,1),(-2,1),(2,-1),(-2,-1)]
        moves = []
        for dx, dy in deltas:
            np_ = (x+dx, y+dy)
            if self._is_in_bounds(np_):
                target = self.get_piece(np_)
                if target is None or target.team != team:
                    moves.append(np_)
        return moves

    def _get_king_moves(self, pos: Position, team: Team) -> List[Position]:
        """King = pawn moves, filtered: can't move adjacent to enemy king."""
        pawn_moves = self._path_march(pos, team, 1, True, True)
        other_king = team.opposite()
        valid = []
        for pm in pawn_moves:
            # Check all neighbors of pm for enemy king
            neighbors = self._path_march(pm, team, 1, True, True)
            has_enemy_king = False
            for nm in neighbors:
                p = self.get_piece(nm)
                if p and p.piece_type == PieceType.KING and p.team == other_king:
                    has_enemy_king = True
                    break
            if not has_enemy_king:
                valid.append(pm)
        return valid

    def _path_march(self, pos: Position, team: Team, max_dist: int,
                    diag: bool, straight: bool) -> List[Position]:
        x, y = pos
        moves = []
        dirs = []
        if diag:
            dirs.extend([(-1,1),(1,1),(-1,-1),(1,-1)])
        if straight:
            dirs.extend([(0,1),(0,-1),(-1,0),(1,0)])

        for dx, dy in dirs:
            for i in range(1, max_dist + 1):
                np_ = (x + dx*i, y + dy*i)
                if not self._is_in_bounds(np_):
                    break
                target = self.get_piece(np_)
                if target is None:
                    moves.append(np_)
                elif target.team != team:
                    moves.append(np_)
                    break  # blocked after capture
                else:
                    break  # blocked by friendly
        return moves

    # ================================================================
    # Game actions
    # ================================================================

    def make_move(self, from_pos: Position, to_pos: Position) -> bool:
        """Execute a move. Returns True if legal."""
        legal = self.get_legal_moves(from_pos)
        if to_pos not in legal:
            return False

        piece = self.get_piece(from_pos)
        self.set_piece(to_pos, piece)
        self.set_piece(from_pos, None)
        self.pieces_moved.add(to_pos)
        self._hash = None
        return True

    def switch_turn(self) -> bool:
        """End the current turn. Returns True if successful.
        If current player's king is in check after their moves, they LOSE.
        (Matches TS: checkIfKingIsThreatened at switchTurn)
        """
        if len(self.pieces_moved) == 0:
            return False

        if self.is_king_threatened(self.current_turn):
            self.winner = self.current_turn.opposite()
            return True

        self.current_turn = self.current_turn.opposite()
        self.pieces_moved = set()
        self.move_count += 1
        self._hash = None
        return True

    def is_king_threatened(self, team: Team) -> bool:
        """Check if team's king is threatened by any enemy piece."""
        king_pos = None
        for y in range(self.board_height):
            for x in range(self.board_width):
                p = self.board[y][x]
                if p and p.team == team and p.piece_type == PieceType.KING:
                    king_pos = (x, y)
                    break
            if king_pos:
                break
        if king_pos is None:
            return True  # king captured/missing = threatened

        other = team.opposite()
        for y in range(self.board_height):
            for x in range(self.board_width):
                p = self.board[y][x]
                if p and p.team == other:
                    moves = self.get_piece_moves((x, y), p)
                    if king_pos in moves:
                        return True
        return False

    def is_game_over(self) -> bool:
        return self.winner is not None

    def get_all_legal_actions(self) -> List[Tuple[Position, Position]]:
        """Get all (from, to) pairs for current player's legal moves."""
        actions = []
        for y in range(self.board_height):
            for x in range(self.board_width):
                pos = (x, y)
                piece = self.get_piece(pos)
                if piece and piece.team == self.current_turn and pos not in self.pieces_moved:
                    for m in self.get_legal_moves(pos):
                        actions.append((pos, m))
        return actions

    def clone(self) -> 'GameState':
        """Fast deep copy."""
        gs = GameState.__new__(GameState)
        gs.board_width = self.board_width
        gs.board_height = self.board_height
        gs.board = [row[:] for row in self.board]  # shallow copy of rows (Piece objects are immutable-ish)
        gs.current_turn = self.current_turn
        gs.pieces_moved = set(self.pieces_moved)
        gs.winner = self.winner
        gs.move_count = self.move_count
        gs._hash = self._hash
        return gs

    # ================================================================
    # Neural network representation
    # ================================================================

    def to_numpy(self) -> np.ndarray:
        """14-channel board representation for neural network.
        Channels 0-5: white P,N,B,R,Q,K
        Channels 6-11: black P,N,B,R,Q,K
        Channel 12: pieces moved this turn
        Channel 13: current turn indicator (1=white, 0=black)
        """
        state = np.zeros((14, self.board_height, self.board_width), dtype=np.float32)

        piece_to_channel = {
            (Team.WHITE, PieceType.PAWN): 0,
            (Team.WHITE, PieceType.KNIGHT): 1,
            (Team.WHITE, PieceType.BISHOP): 2,
            (Team.WHITE, PieceType.ROOK): 3,
            (Team.WHITE, PieceType.QUEEN): 4,
            (Team.WHITE, PieceType.KING): 5,
            (Team.BLACK, PieceType.PAWN): 6,
            (Team.BLACK, PieceType.KNIGHT): 7,
            (Team.BLACK, PieceType.BISHOP): 8,
            (Team.BLACK, PieceType.ROOK): 9,
            (Team.BLACK, PieceType.QUEEN): 10,
            (Team.BLACK, PieceType.KING): 11,
        }

        for y in range(self.board_height):
            for x in range(self.board_width):
                piece = self.board[y][x]
                if piece:
                    ch = piece_to_channel[(piece.team, piece.piece_type)]
                    state[ch, y, x] = 1.0
                if (x, y) in self.pieces_moved:
                    state[12, y, x] = 1.0

        if self.current_turn == Team.WHITE:
            state[13, :, :] = 1.0

        return state

    def __hash__(self):
        if self._hash is None:
            # Hash based on board position + turn + pieces moved
            parts = []
            for y in range(self.board_height):
                for x in range(self.board_width):
                    p = self.board[y][x]
                    if p:
                        parts.append((x, y, p.team.value, p.piece_type.value))
            parts.append(self.current_turn.value)
            parts.append(frozenset(self.pieces_moved))
            self._hash = hash(tuple(parts))
        return self._hash

    def __eq__(self, other):
        if not isinstance(other, GameState):
            return False
        if self.current_turn != other.current_turn:
            return False
        if self.pieces_moved != other.pieces_moved:
            return False
        for y in range(self.board_height):
            for x in range(self.board_width):
                if self.board[y][x] != other.board[y][x]:
                    return False
        return True

    def render(self) -> str:
        symbols = {
            ('w','p'):'♙',('w','n'):'♘',('w','b'):'♗',
            ('w','r'):'♖',('w','q'):'♕',('w','k'):'♔',
            ('b','p'):'♟',('b','n'):'♞',('b','b'):'♝',
            ('b','r'):'♜',('b','q'):'♛',('b','k'):'♚',
        }
        lines = []
        lines.append("  " + " ".join(chr(97+i) for i in range(self.board_width)))
        for y in range(self.board_height - 1, -1, -1):
            row = f"{y+1:2d} "
            for x in range(self.board_width):
                p = self.board[y][x]
                if p:
                    row += symbols.get((p.team.value, p.piece_type.value), '?') + " "
                else:
                    row += ". "
            lines.append(row)
        lines.append("  " + " ".join(chr(97+i) for i in range(self.board_width)))
        lines.append(f"Turn: {'White' if self.current_turn == Team.WHITE else 'Black'}, Move: {self.move_count}")
        text = "\n".join(lines)
        return text
