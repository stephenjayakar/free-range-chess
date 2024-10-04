import unittest
from python.main import GameState, parse_position, make_move, get_piece_at, PieceType, Team

class TestChessGame(unittest.TestCase):

    def test_rook_movement(self):
        game_state = GameState()

        # Move a pawn from a2 to a3
        from_pos = parse_position('a2')
        to_pos = parse_position('a3')
        self.assertTrue(make_move(game_state, from_pos, to_pos))

        # Move a rook from a1 to a9
        from_pos = parse_position('a1')
        to_pos = parse_position('a9')
        self.assertTrue(make_move(game_state, from_pos, to_pos))

        # Check if the rook is at a9
        piece = get_piece_at(game_state.board, to_pos)
        self.assertIsNotNone(piece)
        self.assertEqual(piece.piece_type, PieceType.ROOK)
        self.assertEqual(piece.team, Team.WHITE)

if __name__ == '__main__':
    unittest.main()
