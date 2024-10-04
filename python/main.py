# Import statements
import copy
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

BOARD_SIZE = 10  # Change the board size to 10x10

# Enums for teams and piece types
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

@dataclass
class Piece:
    team: Team
    piece_type: PieceType

# Type aliases
Board = List[List[Optional[Piece]]]
Position = Tuple[int, int]  # (row, col)
Move = Tuple[Position, Position]  # (from_pos, to_pos)

def initialize_board() -> Board:
    board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    # Place pieces for both teams
    # Black pieces (right aligned)
    for col in range(0, 8):
        board[1][BOARD_SIZE - col - 1] = Piece(Team.BLACK, PieceType.PAWN)
    board[0][2] = board[0][9] = Piece(Team.BLACK, PieceType.ROOK)
    board[0][3] = board[0][8] = Piece(Team.BLACK, PieceType.KNIGHT)
    board[0][4] = board[0][7] = Piece(Team.BLACK, PieceType.BISHOP)
    board[0][6] = Piece(Team.BLACK, PieceType.QUEEN)
    board[0][5] = Piece(Team.BLACK, PieceType.KING)

    # White pieces (left aligned)
    for col in range(0, 8):
        board[8][col] = Piece(Team.WHITE, PieceType.PAWN)
    board[9][0] = board[9][7] = Piece(Team.WHITE, PieceType.ROOK)
    board[9][1] = board[9][6] = Piece(Team.WHITE, PieceType.KNIGHT)
    board[9][2] = board[9][5] = Piece(Team.WHITE, PieceType.BISHOP)
    board[9][3] = Piece(Team.WHITE, PieceType.QUEEN)
    board[9][4] = Piece(Team.WHITE, PieceType.KING)

    return board

class GameState:
    def __init__(self):
        self.board = initialize_board()
        self.current_turn = Team.WHITE
        self.pieces_moved = set()  # Positions of pieces moved this turn
        self.winner: Optional[Team] = None

    def switch_turn(self):
        self.current_turn = self.current_turn.opposite()
        self.pieces_moved.clear()

    def is_game_over(self) -> bool:
        return self.winner is not None

    def clone(self):
        return copy.deepcopy(self)

def is_in_bounds(position: Position) -> bool:
    row, col = position
    return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE

def get_piece_at(board: Board, position: Position) -> Optional[Piece]:
    row, col = position
    return board[row][col]

def is_opponent_piece(piece: Piece, team: Team) -> bool:
    return piece.team != team

def add_move_if_valid(moves: List[Position], board: Board, team: Team, position: Position):
    if is_in_bounds(position):
        target_piece = get_piece_at(board, position)
        if target_piece is None or is_opponent_piece(target_piece, team):
            moves.append(position)

def get_pawn_moves(board: Board, position: Position, team: Team) -> List[Position]:
    moves = []
    row, col = position
    # Pawns can move in any direction
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    for dr, dc in directions:
        new_pos = (row + dr, col + dc)
        if is_in_bounds(new_pos):
            target_piece = get_piece_at(board, new_pos)
            if target_piece is None or is_opponent_piece(target_piece, team):
                moves.append(new_pos)
    return moves

def get_knight_moves(board: Board, position: Position, team: Team) -> List[Position]:
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
        add_move_if_valid(moves, board, team, new_pos)
    return moves

def get_straight_line_moves(board: Board, position: Position, team: Team, directions: List[Tuple[int, int]], max_distance: int) -> List[Position]:
    moves = []
    for dr, dc in directions:
        new_row, new_col = position
        for _ in range(max_distance):
            new_row += dr
            new_col += dc
            new_pos = (new_row, new_col)
            if not is_in_bounds(new_pos):
                break
            target_piece = get_piece_at(board, new_pos)
            if target_piece is None:
                moves.append(new_pos)
            else:
                if is_opponent_piece(target_piece, team):
                    moves.append(new_pos)
                break
    return moves

def get_bishop_moves(board: Board, position: Position, team: Team) -> List[Position]:
    directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    return get_straight_line_moves(board, position, team, directions, max_distance=8)

def get_rook_moves(board: Board, position: Position, team: Team) -> List[Position]:
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    return get_straight_line_moves(board, position, team, directions, max_distance=8)

def get_queen_moves(board: Board, position: Position, team: Team) -> List[Position]:
    directions = [
        (-1, -1), (-1, 1), (1, -1), (1, 1),
        (-1, 0), (1, 0), (0, -1), (0, 1)
    ]
    return get_straight_line_moves(board, position, team, directions, max_distance=8)

def get_king_moves(board: Board, position: Position, team: Team) -> List[Position]:
    moves = []
    row, col = position
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            if dr == 0 and dc == 0:
                continue
            new_pos = (row + dr, col + dc)
            add_move_if_valid(moves, board, team, new_pos)
    return moves

def get_piece_moves(board: Board, position: Position, piece: Piece) -> List[Position]:
    if piece.piece_type == PieceType.PAWN:
        return get_pawn_moves(board, position, piece.team)
    elif piece.piece_type == PieceType.KNIGHT:
        return get_knight_moves(board, position, piece.team)
    elif piece.piece_type == PieceType.BISHOP:
        return get_bishop_moves(board, position, piece.team)
    elif piece.piece_type == PieceType.ROOK:
        return get_rook_moves(board, position, piece.team)
    elif piece.piece_type == PieceType.QUEEN:
        return get_queen_moves(board, position, piece.team)
    elif piece.piece_type == PieceType.KING:
        return get_king_moves(board, position, piece.team)
    else:
        return []

def is_valid_move(game_state: GameState, from_pos: Position, to_pos: Position) -> Tuple[bool, str]:
    piece = get_piece_at(game_state.board, from_pos)
    if piece is None:
        return False, "No piece at the starting position."
    if piece.team != game_state.current_turn:
        return False, "It's not your turn."
    if from_pos in game_state.pieces_moved:
        return False, "This piece has already been moved this turn."
    possible_moves = get_piece_moves(game_state.board, from_pos, piece)
    if to_pos not in possible_moves:
        return False, "The move is not valid for this piece."
    return True, ""

def make_move(game_state: GameState, from_pos: Position, to_pos: Position) -> bool:
    valid, message = is_valid_move(game_state, from_pos, to_pos)
    if not valid:
        print(f"Invalid move: {message}")
        return False
    piece = get_piece_at(game_state.board, from_pos)
    target_piece = get_piece_at(game_state.board, to_pos)
    # Move the piece
    game_state.board[to_pos[0]][to_pos[1]] = piece
    game_state.board[from_pos[0]][from_pos[1]] = None
    game_state.pieces_moved.add(to_pos)
    # Check for capturing the opponent's king
    if target_piece and target_piece.piece_type == PieceType.KING:
        game_state.winner = game_state.current_turn
    return True

def get_piece_symbol(piece: Piece) -> str:
    symbols = {
        (Team.BLACK, PieceType.PAWN): '♙',
        (Team.BLACK, PieceType.KNIGHT): '♘',
        (Team.BLACK, PieceType.BISHOP): '♗',
        (Team.BLACK, PieceType.ROOK): '♖',
        (Team.BLACK, PieceType.QUEEN): '♕',
        (Team.BLACK, PieceType.KING): '♔',
        (Team.WHITE, PieceType.PAWN): '♟',
        (Team.WHITE, PieceType.KNIGHT): '♞',
        (Team.WHITE, PieceType.BISHOP): '♝',
        (Team.WHITE, PieceType.ROOK): '♜',
        (Team.WHITE, PieceType.QUEEN): '♛',
        (Team.WHITE, PieceType.KING): '♚',
    }
    return symbols[(piece.team, piece.piece_type)]

def render_board(board: Board):
    cols = 'abcdefghij'  # Adjust column labels for 10x10 board
    print("   " + " ".join(cols))
    for row in range(BOARD_SIZE):
        row_str = f"{BOARD_SIZE - row} "
        row_str = "{:<3}".format(row_str)
        for col in range(BOARD_SIZE):
            piece = board[row][col]
            if piece is None:
                row_str += '. '
            else:
                piece_symbol = get_piece_symbol(piece)
                row_str += piece_symbol + ' '
        print(row_str + f"{BOARD_SIZE - row}")
    print("   " + " ".join(cols) + "\n")

def parse_position(pos_str: str) -> Optional[Position]:
    col_str, row_str = pos_str[0], pos_str[1:]
    cols = 'abcdefghij'
    rows = list(str(i) for i in range(BOARD_SIZE, 0, -1))
    if col_str in cols and row_str in rows:
        col = cols.index(col_str)
        row = rows.index(row_str)
        return (row, col)
    else:
        return None

def get_player_moves(game_state: GameState):
    while True:
        render_board(game_state.board)
        print(f"{game_state.current_turn.name}'s turn.")
        print("Enter your moves in the format 'e2,e4' (from-to).")
        print("Enter 'done' when finished moving your pieces.")

        user_input = input("Your move: ").strip()
        if user_input.lower() == 'done':
            break
        if ',' not in user_input or len(user_input.split(',')) != 2:
            print("Invalid input format. Try again.")
            continue
        from_str, to_str = user_input.split(',')
        from_pos = parse_position(from_str)
        to_pos = parse_position(to_str)
        if from_pos is None or to_pos is None:
            print("Invalid positions. Use format like 'e2,e4'.")
            continue
        if make_move(game_state, from_pos, to_pos):
            print(f"Moved from {from_str} to {to_str}.")
            if game_state.is_game_over():
                print(f"Game over! {game_state.winner.name} wins!")
                break
        else:
            print("Invalid move. Try again.")

def main():
    game_state = GameState()
    while not game_state.is_game_over():
        get_player_moves(game_state)
        if game_state.is_game_over():
            break
        game_state.switch_turn()
    print("Thank you for playing!")

if __name__ == '__main__':
    main()
