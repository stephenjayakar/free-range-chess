from typing import List, Tuple, Optional
from enum import Enum

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

def get_pawn_moves(board, position: Position, team: Team, board_width: int, board_height: int) -> List[Position]:
    moves = []
    row, col = position
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    for dr, dc in directions:
        new_pos = (row + dr, col + dc)
        if is_in_bounds(new_pos, board_width, board_height):
            target_piece = get_piece_at(board, new_pos)
            if target_piece is None or target_piece.team != team:
                moves.append(new_pos)
    return moves

def get_knight_moves(board, position: Position, team: Team, board_width: int, board_height: int) -> List[Position]:
    moves = []
    row, col = position
    deltas = [
        (-2, -1), (-2, 1),
        (-1, -2), (-1, 2),
        (1, -2),  (1, 2),
        (2, -1),  (2, 1)
    ]
    for dr, dc in deltas:
        new_pos = (row + dr, col + dc)
        if is_in_bounds(new_pos, board_width, board_height):
            target_piece = get_piece_at(board, new_pos)
            if target_piece is None or target_piece.team != team:
                moves.append(new_pos)
    return moves

def get_straight_line_moves(board, position: Position, team: Team, directions: List[Tuple[int, int]], 
                            max_distance: int, board_width: int, board_height: int) -> List[Position]:
    moves = []
    for dr, dc in directions:
        new_row, new_col = position
        for _ in range(max_distance):
            new_row += dr
            new_col += dc
            new_pos = (new_row, new_col)
            if not is_in_bounds(new_pos, board_width, board_height):
                break
            target_piece = get_piece_at(board, new_pos)
            if target_piece is None:
                moves.append(new_pos)
            else:
                if target_piece.team != team:
                    moves.append(new_pos)
                break
    return moves

def get_bishop_moves(board, position: Position, team: Team, board_width: int, board_height: int) -> List[Position]:
    directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    return get_straight_line_moves(board, position, team, directions, max_distance=7, 
                                   board_width=board_width, board_height=board_height)

def get_rook_moves(board, position: Position, team: Team, board_width: int, board_height: int) -> List[Position]:
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    return get_straight_line_moves(board, position, team, directions, max_distance=7, 
                                   board_width=board_width, board_height=board_height)

def get_queen_moves(board, position: Position, team: Team, board_width: int, board_height: int) -> List[Position]:
    directions = [
        (-1, -1), (-1, 1), (1, -1), (1, 1),
        (-1, 0), (1, 0), (0, -1), (0, 1)
    ]
    return get_straight_line_moves(board, position, team, directions, max_distance=7, 
                                   board_width=board_width, board_height=board_height)

def get_king_moves(board, position: Position, team: Team, board_width: int, board_height: int) -> List[Position]:
    moves = []
    row, col = position
    
    pawn_moves = get_pawn_moves(board, position, team, board_width, board_height)
    other_king_type = PieceType.KING
    other_team = team.opposite()
    
    for move in pawn_moves:
        neighboring_moves = get_pawn_moves(board, move, team, board_width, board_height)
        contains_king = False
        for nm in neighboring_moves:
            piece = get_piece_at(board, nm)
            if piece and piece.piece_type == other_king_type and piece.team == other_team:
                contains_king = True
                break
        if not contains_king:
            moves.append(move)
    
    return moves

def is_in_bounds(position: Position, board_width: int, board_height: int) -> bool:
    row, col = position
    return 0 <= row < board_height and 0 <= col < board_width

def get_piece_at(board, position: Position):
    row, col = position
    return board[row][col]
