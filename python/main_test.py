import unittest
from main import GameState, parse_position, make_move, get_piece_at, PieceType, Team

class TestChessGame(unittest.TestCase):

    def test_rook_movement(self):
        game_state = GameState()

        from_pos = parse_position('a2')
        to_pos = parse_position('b3')
        self.assertTrue(make_move(game_state, from_pos, to_pos))

        from_pos = parse_position('a1')
        to_pos = parse_position('a9')
        self.assertTrue(make_move(game_state, from_pos, to_pos))

        # Check if the rook is at a9
        a9 = parse_position('a9')
        piece = get_piece_at(game_state.board, a9)
        self.assertIsNotNone(piece)
        self.assertEqual(piece.piece_type, PieceType.ROOK)
        self.assertEqual(piece.team, Team.WHITE)

    def test_rook_limit(self):
        game_state = GameState()

        from_pos = parse_position('a2')
        to_pos = parse_position('b3')
        self.assertTrue(make_move(game_state, from_pos, to_pos))

        from_pos = parse_position('a1')
        to_pos = parse_position('a10')
        self.assertFalse(make_move(game_state, from_pos, to_pos))

        a1 = parse_position('a1')
        piece = get_piece_at(game_state.board, a1)
        self.assertIsNotNone(piece)
        self.assertEqual(piece.piece_type, PieceType.ROOK)
        self.assertEqual(piece.team, Team.WHITE)

if __name__ == '__main__':
    unittest.main()
