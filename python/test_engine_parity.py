#!/usr/bin/env python3
"""
Test that the Python game engine matches the TypeScript engine exactly.

Verifies:
- Starting position matches
- Move generation for each piece type
- King moves avoid adjacent enemy king
- Cannot capture king
- Check detection
- Switch turn / win condition
- Max slide distance is 7 (not unlimited!)
"""

import sys
import random
from game_engine import GameState, Team, PieceType, Piece, Position
from typing import List, Set, Tuple


def test_starting_position():
    """Verify starting position matches TypeScript startPosition()."""
    gs = GameState(10, 10)
    
    # White pawns at y=1, x=0..7
    for x in range(8):
        p = gs.get_piece((x, 1))
        assert p is not None, f"Expected white pawn at ({x},1)"
        assert p.team == Team.WHITE and p.piece_type == PieceType.PAWN, \
            f"Wrong piece at ({x},1): {p}"
    
    # White back rank y=0
    expected_white = [
        (0, PieceType.ROOK), (1, PieceType.KNIGHT), (2, PieceType.BISHOP),
        (3, PieceType.QUEEN), (4, PieceType.KING), (5, PieceType.BISHOP),
        (6, PieceType.KNIGHT), (7, PieceType.ROOK),
    ]
    for x, pt in expected_white:
        p = gs.get_piece((x, 0))
        assert p is not None, f"Expected white {pt.value} at ({x},0)"
        assert p.team == Team.WHITE and p.piece_type == pt, \
            f"Wrong piece at ({x},0): {p}, expected {pt}"
    
    # Black pawns at y=8, x=2..9
    for x in range(2, 10):
        p = gs.get_piece((x, 8))
        assert p is not None, f"Expected black pawn at ({x},8)"
        assert p.team == Team.BLACK and p.piece_type == PieceType.PAWN, \
            f"Wrong piece at ({x},8): {p}"
    
    # Black back rank y=9
    expected_black = [
        (9, PieceType.ROOK), (8, PieceType.KNIGHT), (7, PieceType.BISHOP),
        (6, PieceType.QUEEN), (5, PieceType.KING), (4, PieceType.BISHOP),
        (3, PieceType.KNIGHT), (2, PieceType.ROOK),
    ]
    for x, pt in expected_black:
        p = gs.get_piece((x, 9))
        assert p is not None, f"Expected black {pt.value} at ({x},9)"
        assert p.team == Team.BLACK and p.piece_type == pt, \
            f"Wrong piece at ({x},9): {p}, expected {pt}"
    
    # Columns 8-9 on rows 0-1 should be empty (only 8 white pieces per row)
    for x in [8, 9]:
        for y in [0, 1]:
            p = gs.get_piece((x, y))
            assert p is None, f"Expected empty at ({x},{y}) but found {p}"
    
    # Columns 0-1 on rows 8-9 should be empty (only 8 black pieces per row)
    for x in [0, 1]:
        for y in [8, 9]:
            p = gs.get_piece((x, y))
            assert p is None, f"Expected empty at ({x},{y}) but found {p}"
    
    print("✓ Starting position matches TypeScript")


def test_pawn_moves():
    """Pawn = pathMarch(1, diag=true, straight=true) — 1 square in all 8 dirs."""
    gs = GameState(10, 10)
    
    # White pawn at (3,1): above is empty, sides have friendly pawns/pieces
    moves = set(gs.get_legal_moves((3, 1)))
    expected = {(2, 2), (3, 2), (4, 2)}
    assert moves == expected, f"Pawn at (3,1) moves: {moves} != {expected}"
    
    # Edge pawn at (0,1)
    moves = set(gs.get_legal_moves((0, 1)))
    expected = {(0, 2), (1, 2)}
    assert moves == expected, f"Pawn at (0,1) moves: {moves} != {expected}"
    
    print("✓ Pawn moves match TypeScript")


def test_rook_moves():
    """Rook slides straight up to 7 squares, blocked by pieces."""
    gs = GameState(10, 10)
    gs.make_move((0, 1), (0, 2))  # move a-pawn forward
    
    moves = set(gs.get_legal_moves((0, 0)))
    expected = {(0, 1)}  # only 1 square up, blocked by pawn at (0,2)
    assert moves == expected, f"Rook at (0,0) moves: {moves} != {expected}"
    
    print("✓ Rook moves match TypeScript")


def test_rook_max_distance():
    """Rook max slide distance is 7 (matching TS: pathMarch maxDistance=7)."""
    gs = GameState(10, 10)
    for y in range(10):
        for x in range(10):
            gs.board[y][x] = None
    
    gs.set_piece((0, 0), Piece(Team.WHITE, PieceType.ROOK))
    gs.set_piece((9, 9), Piece(Team.WHITE, PieceType.KING))
    gs.set_piece((9, 0), Piece(Team.BLACK, PieceType.KING))
    gs.current_turn = Team.WHITE
    
    moves = set(gs.get_legal_moves((0, 0)))
    # Rook at (0,0) going right: can reach (1,0)..(7,0) = 7 squares
    # But (9,0) has enemy king which can't be captured
    # Going up: (0,1)..(0,7) = 7 squares  
    assert (0, 7) in moves, "Rook should reach (0,7)"
    assert (0, 8) not in moves, "Rook should NOT reach (0,8) — max distance 7"
    assert (7, 0) in moves, "Rook should reach (7,0)"
    assert (8, 0) not in moves, "Rook should NOT reach (8,0) — max distance 7"
    
    print("✓ Rook max distance = 7 matches TypeScript")


def test_knight_moves():
    """Knight L-shape jumps, can jump over pieces."""
    gs = GameState(10, 10)
    moves = set(gs.get_legal_moves((1, 0)))
    expected = {(0, 2), (2, 2)}
    assert moves == expected, f"Knight at (1,0) moves: {moves} != {expected}"
    
    print("✓ Knight moves match TypeScript")


def test_bishop_moves():
    """Bishop slides diagonally up to 7, blocked by pieces."""
    gs = GameState(10, 10)
    
    # Bishop at (2,0) blocked by pawns
    moves = set(gs.get_legal_moves((2, 0)))
    assert len(moves) == 0, f"Bishop at (2,0) should have no moves"
    
    # Move pawn to open diagonal
    gs.make_move((3, 1), (3, 2))
    moves = set(gs.get_legal_moves((2, 0)))
    
    expected = set()
    for i in range(1, 8):
        pos = (2 + i, 0 + i)
        if not (0 <= pos[0] < 10 and 0 <= pos[1] < 10):
            break
        p = gs.get_piece(pos)
        if p is None:
            expected.add(pos)
        elif p.team != Team.WHITE:
            expected.add(pos)
            break
        else:
            break
    
    assert moves == expected, f"Bishop at (2,0) moves: {moves} != {expected}"
    
    print("✓ Bishop moves match TypeScript")


def test_king_moves():
    """King = pawn moves filtered to avoid adjacent enemy king."""
    gs = GameState(10, 10)
    for y in range(10):
        for x in range(10):
            gs.board[y][x] = None
    
    # Kings far apart
    gs.set_piece((4, 4), Piece(Team.WHITE, PieceType.KING))
    gs.set_piece((4, 7), Piece(Team.BLACK, PieceType.KING))
    gs.current_turn = Team.WHITE
    
    moves = set(gs.get_legal_moves((4, 4)))
    expected = {(3,3),(4,3),(5,3),(3,4),(5,4),(3,5),(4,5),(5,5)}
    assert moves == expected, f"King at (4,4) far: {moves} != {expected}"
    
    # Kings closer — white at (4,5), black at (4,7)
    gs.board[4][4] = None
    gs.set_piece((4, 5), Piece(Team.WHITE, PieceType.KING))
    gs.pieces_moved = set()
    
    moves = set(gs.get_legal_moves((4, 5)))
    # (3,6),(4,6),(5,6) are filtered — their neighbors include (4,7)
    expected = {(3,4),(4,4),(5,4),(3,5),(5,5)}
    assert moves == expected, f"King at (4,5) near enemy: {moves} != {expected}"
    
    print("✓ King moves match TypeScript (avoids adjacent enemy king)")


def test_cannot_capture_king():
    """No piece can capture the king (matches TS validation)."""
    gs = GameState(10, 10)
    for y in range(10):
        for x in range(10):
            gs.board[y][x] = None
    
    gs.set_piece((4, 4), Piece(Team.WHITE, PieceType.QUEEN))
    gs.set_piece((4, 7), Piece(Team.BLACK, PieceType.KING))
    gs.set_piece((0, 0), Piece(Team.WHITE, PieceType.KING))
    gs.current_turn = Team.WHITE
    
    moves = set(gs.get_legal_moves((4, 4)))
    assert (4, 7) not in moves, "Queen should NOT be able to capture king!"
    
    print("✓ Cannot capture king (matches TypeScript)")


def test_check_detection():
    """Check detection works correctly."""
    gs = GameState(10, 10)
    for y in range(10):
        for x in range(10):
            gs.board[y][x] = None
    
    gs.set_piece((0, 0), Piece(Team.WHITE, PieceType.KING))
    gs.set_piece((0, 5), Piece(Team.BLACK, PieceType.ROOK))
    gs.set_piece((9, 9), Piece(Team.BLACK, PieceType.KING))
    
    assert gs.is_king_threatened(Team.WHITE) == True
    assert gs.is_king_threatened(Team.BLACK) == False
    
    gs.set_piece((0, 0), None)
    gs.set_piece((1, 1), Piece(Team.WHITE, PieceType.KING))
    assert gs.is_king_threatened(Team.WHITE) == False
    
    print("✓ Check detection matches TypeScript")


def test_switch_turn_win():
    """If your king is in check at end of your turn, you lose."""
    gs = GameState(10, 10)
    for y in range(10):
        for x in range(10):
            gs.board[y][x] = None
    
    # White king (0,0), white rook (5,0), black king (9,9)
    gs.set_piece((0, 0), Piece(Team.WHITE, PieceType.KING))
    gs.set_piece((5, 0), Piece(Team.WHITE, PieceType.ROOK))
    gs.set_piece((9, 9), Piece(Team.BLACK, PieceType.KING))
    gs.current_turn = Team.WHITE
    
    # Move rook to (5,7) — within max distance 7
    result = gs.make_move((5, 0), (5, 7))
    assert result == True, "Rook move to (5,7) should succeed"
    
    # White king not in check → switch succeeds
    gs.switch_turn()
    assert gs.current_turn == Team.BLACK, f"Should be black's turn, got {gs.current_turn}"
    assert gs.winner is None
    
    # Black king at (9,9), needs to make a move
    # Black king can move to (8,8),(9,8),(8,9)
    result = gs.make_move((9, 9), (8, 9))
    assert result == True
    
    # Black king at (8,9) — not threatened by rook at (5,7) → safe
    gs.switch_turn()
    assert gs.winner is None
    assert gs.current_turn == Team.WHITE
    
    # Now test a losing scenario: set up position where ending turn = check
    gs2 = GameState(10, 10)
    for y in range(10):
        for x in range(10):
            gs2.board[y][x] = None
    
    gs2.set_piece((0, 0), Piece(Team.WHITE, PieceType.KING))
    gs2.set_piece((9, 9), Piece(Team.BLACK, PieceType.KING))
    gs2.set_piece((1, 5), Piece(Team.BLACK, PieceType.ROOK))  # threatens row 0? No, file 1? No.
    gs2.current_turn = Team.WHITE
    
    # White king moves to (0, 1) — now on file 1 with black rook at (1,5)... not same file
    # Let's make it simpler: black rook on (0,5) threatens file 0
    gs2.set_piece((1, 5), None)
    gs2.set_piece((0, 5), Piece(Team.BLACK, PieceType.ROOK))
    
    # White king at (0,0) is in check from rook at (0,5)!
    assert gs2.is_king_threatened(Team.WHITE) == True
    
    # White moves king to (1,0) — but still on... let's check
    # Actually white needs to move somewhere. Move king to (1,1)
    result = gs2.make_move((0, 0), (1, 1))
    assert result == True
    
    # Now white king at (1,1), rook at (0,5). Is white still in check?
    assert gs2.is_king_threatened(Team.WHITE) == False
    
    # Switch turn — white king safe → black's turn
    gs2.switch_turn()
    assert gs2.winner is None
    assert gs2.current_turn == Team.BLACK
    
    # Now: black rook moves to (1,5) — threatens file 1
    # Then black ends turn. But we need to check BLACK's king status.
    # Black king at (9,9) is not threatened → fine
    gs2.make_move((0, 5), (0, 4))
    gs2.switch_turn()
    assert gs2.winner is None
    
    # Now make white end turn while in check:
    gs3 = GameState(10, 10)
    for y in range(10):
        for x in range(10):
            gs3.board[y][x] = None
    
    gs3.set_piece((4, 0), Piece(Team.WHITE, PieceType.KING))
    gs3.set_piece((8, 0), Piece(Team.WHITE, PieceType.PAWN))
    gs3.set_piece((4, 5), Piece(Team.BLACK, PieceType.ROOK))  # threatens (4,0) via file
    gs3.set_piece((9, 9), Piece(Team.BLACK, PieceType.KING))
    gs3.current_turn = Team.WHITE
    
    # White is in check! White moves pawn instead of king (bad move)
    result = gs3.make_move((8, 0), (8, 1))
    assert result == True
    
    # Now end turn — white king STILL in check → white loses
    gs3.switch_turn()
    assert gs3.winner == Team.BLACK, f"Black should win, got winner={gs3.winner}"
    
    print("✓ Switch turn / win condition matches TypeScript")


def test_queen_moves():
    """Queen = pathMarch(7, diag=True, straight=True)."""
    gs = GameState(10, 10)
    for y in range(10):
        for x in range(10):
            gs.board[y][x] = None
    
    gs.set_piece((4, 4), Piece(Team.WHITE, PieceType.QUEEN))
    gs.set_piece((0, 0), Piece(Team.WHITE, PieceType.KING))
    gs.set_piece((9, 9), Piece(Team.BLACK, PieceType.KING))
    gs.current_turn = Team.WHITE
    
    moves = set(gs.get_legal_moves((4, 4)))
    
    # Verify max distance 7 applies
    # From (4,4) going up: (4,5)..(4,9) but (4,9+) OOB. That's only 5 up. Under 7.
    # From (4,4) going right: (5,4)..(9,4) — 5 squares. Under 7.
    # From (4,4) going down: (4,3)..(4,0) — 4 squares. Under 7.
    # From (4,4) going left: (3,4)..(0,4) — 4 squares. Under 7.
    # All within 7 for this board position.
    
    assert (4, 5) in moves
    assert (4, 9) in moves  # 5 squares up, within 7
    assert (9, 4) in moves  # 5 right, within 7
    assert (0, 0) not in moves  # friendly king
    assert (9, 9) not in moves  # can't capture king
    
    # Diagonal: (4,4) -> (9,9) is 5 steps, but can't capture king
    # (4,4) -> (8,8) should be reachable (4 diagonal steps)
    assert (8, 8) in moves
    
    print("✓ Queen moves match TypeScript")


def test_pieces_moved_tracking():
    """Pieces that have moved this turn can't move again."""
    gs = GameState(10, 10)
    
    # Move white pawn
    gs.make_move((0, 1), (0, 2))
    
    # That pawn (now at (0,2)) should have no moves
    assert gs.get_legal_moves((0, 2)) == [], "Moved pawn should have no more moves"
    
    # Other pawns still can move
    assert len(gs.get_legal_moves((1, 1))) > 0, "Unmoved pawn should have moves"
    
    # After switch_turn, pieces_moved resets
    gs.switch_turn()
    # Now it's black's turn — white pieces can't move anyway
    # But pieces_moved should be empty
    assert len(gs.pieces_moved) == 0
    
    print("✓ Pieces moved tracking matches TypeScript")


def test_full_game_no_crash():
    """Play a random full game to verify no crashes."""
    gs = GameState(10, 10)
    turns = 0
    max_turns = 100
    
    while not gs.is_game_over() and turns < max_turns:
        actions = gs.get_all_legal_actions()
        if not actions:
            if len(gs.pieces_moved) > 0:
                gs.switch_turn()
            else:
                break
            turns += 1
            continue
        
        random.shuffle(actions)
        num_moves = min(len(actions), random.randint(1, 5))
        for i in range(num_moves):
            if i < len(actions):
                from_pos, to_pos = actions[i]
                gs.make_move(from_pos, to_pos)
                actions = gs.get_all_legal_actions()
        
        if len(gs.pieces_moved) > 0:
            gs.switch_turn()
        turns += 1
    
    print(f"✓ Full random game completed ({turns} turns, winner={gs.winner})")


def test_to_numpy():
    """Verify numpy representation is correct shape and values."""
    gs = GameState(10, 10)
    arr = gs.to_numpy()
    
    assert arr.shape == (14, 10, 10), f"Wrong shape: {arr.shape}"
    assert arr.dtype == 'float32'
    
    # Channel 13 should be all 1s (white's turn)
    assert arr[13].sum() == 100.0, "Turn channel should be all 1s for white"
    
    # Channel 0 (white pawns) should have 8 ones
    assert arr[0].sum() == 8.0, f"White pawns channel sum: {arr[0].sum()}"
    
    # Channel 5 (white king) should have 1 one at (0, 4) → arr[5, 0, 4]
    assert arr[5, 0, 4] == 1.0, "White king should be at (4,0) → channel[5,0,4]"
    
    print("✓ Numpy representation is correct")


if __name__ == '__main__':
    print("Testing Python engine parity with TypeScript...")
    print()
    
    test_starting_position()
    test_pawn_moves()
    test_rook_moves()
    test_rook_max_distance()
    test_knight_moves()
    test_bishop_moves()
    test_king_moves()
    test_cannot_capture_king()
    test_check_detection()
    test_switch_turn_win()
    test_queen_moves()
    test_pieces_moved_tracking()
    test_to_numpy()
    test_full_game_no_crash()
    
    print()
    print("=" * 40)
    print("All tests passed! ✓")
    print("Python engine matches TypeScript engine.")
    print("=" * 40)
