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
        board.view.setPieceGreyedOut(squareTo, true);
        pieceMoved = true;
        // TODO: Fuck this
        state.piecesMoved.push(squareTo);
        break;
      }
    }
  }
}

// Aggressive AI that prioritizes capturing opponent pieces or moving towards them
export function aggressiveMoves(board: any, team: Team, state: State) {
  const boardWidth = board.props.boardWidth;

  const allPieces = squaresToPieces(
    board.state.position.squares,
    boardWidth
  );

  const teamPieces = allPieces
    .filter((p) => getTeam(p.type) === team)
    .sort((a, b) => 0.5 - Math.random());

  // First, try to capture opponent pieces
  for (const p of teamPieces) {
    const squareFrom = Position.coordinatesToSquare(p.position);
    const moves = potentialMoves(board, p.type, squareFrom);

    const captureMoves = moves.filter((move) => {
      const targetPiece = board.state.position.squares[Position.squareToIndex(move, boardWidth)];
      return targetPiece && getTeam(targetPiece) !== team;
    });

    for (const squareTo of captureMoves) {
      board.movePiece(squareFrom, squareTo, true);
      board.view.setPieceGreyedOut(squareTo, true);
      state.piecesMoved.push(squareTo);
    }
  }

  // Move remaining pieces towards opponent pieces
  for (const p of teamPieces) {
    const squareFrom = Position.coordinatesToSquare(p.position);
    if (state.piecesMoved.includes(squareFrom)) {
      continue; // Skip pieces that have already moved
    }

    const moves = potentialMoves(board, p.type, squareFrom);

    if (moves.length > 0) {
      const opponentPieces = allPieces.filter((p) => getTeam(p.type) !== team);
      let closestMove = null;
      let minDistance = Infinity;

      for (const move of moves) {
        const moveCoords = Position.squareToCoordinates(move);
        for (const opponent of opponentPieces) {
          const distance = Math.sqrt(
            Math.pow(moveCoords[0] - opponent.position[0], 2) +
            Math.pow(moveCoords[1] - opponent.position[1], 2)
          );
          if (distance < minDistance) {
            minDistance = distance;
            closestMove = move;
          }
        }
      }

      if (closestMove) {
        board.movePiece(squareFrom, closestMove, true);
        board.view.setPieceGreyedOut(closestMove, true);
        state.piecesMoved.push(closestMove);
      }
    }
  }
}

function getRandomInt(maxInc: number): number {
  return Math.floor(Math.random() * maxInc);
}
