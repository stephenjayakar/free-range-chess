import { Team, squaresToPieces, getTeam } from "./pieces";
import { Position } from "chessboard/model/Position";
import { potentialMoves, State } from "./index";

// Does random moves until it can't do any moves anymore
export function randomMoves(board: any, team: Team, state: State) {
  // TODO: copy boardWidth into the top-level of the board
  const boardWidth = board.props.boardWidth;

  let pieceMoved = true;
  while (pieceMoved) {
    // TODO: this is hella wasteful. doing all these conversions over and over :/
    const allPieces = squaresToPieces(
      board.state.position.squares,
      // TODO: can we just get this from the board lol
      boardWidth
    );

    // NOTE: the pieces are in a random order so that we don't just pick the same strategy every time.
    const teamPieces = allPieces
      .filter((p) => getTeam(p.type) === team)
      .sort((a, b) => 0.5 - Math.random());
    pieceMoved = false;
    // TODO: refactor this so that you pick a random piece without replacement.
    for (const p of teamPieces) {
      const squareFrom = Position.coordinatesToSquare(p.position);
      const moves = potentialMoves(board, p.type, squareFrom);
      if (moves.length > 0) {
        const moveIndex = getRandomInt(moves.length - 1);
        const squareTo = moves[moveIndex];

        board.movePiece(squareFrom, squareTo, true);
        pieceMoved = true;
        // TODO: Fuck this
        state.piecesMoved.push(squareTo);
        break;
      }
    }
  }
}

function getRandomInt(maxInc: number): number {
  return Math.floor(Math.random() * maxInc);
}
