import { Team, squaresToPieces, getTeam, Piece, Coords, getOtherTeam } from "./pieces";
import { Position } from "chessboard/model/Position";
import { potentialMoves, State } from "./index";

// ============================================================
// Piece values for evaluation
// ============================================================
const PIECE_VALUES: Record<string, number> = {
  p: 1,
  n: 3,
  b: 3,
  r: 5,
  q: 9,
  k: 100,
};

function pieceValue(pieceType: string): number {
  return PIECE_VALUES[pieceType[1]] || 0;
}

// ============================================================
// Positional bonus tables (10x10 board)
// ============================================================
function positionalBonus(pieceType: string, coords: Coords, team: Team): number {
  const [x, y] = coords;
  const centerX = 4.5;
  const centerY = 4.5;
  const distFromCenter = Math.abs(x - centerX) + Math.abs(y - centerY);
  const centerBonus = Math.max(0, (9 - distFromCenter)) * 0.05;

  const type = pieceType[1];

  if (type === "p") {
    const advancement = team === "w" ? y : (9 - y);
    return advancement * 0.1 + centerBonus;
  }
  if (type === "n") return centerBonus * 2;
  if (type === "b") return centerBonus * 1.5;
  if (type === "r") return centerBonus * 0.5;
  if (type === "q") return centerBonus * 0.8;
  if (type === "k") {
    const backRank = team === "w" ? 0 : 9;
    const distFromBack = Math.abs(y - backRank);
    return -distFromBack * 0.15;
  }
  return 0;
}

// ============================================================
// Score a single move for a piece
// ============================================================
interface MoveScore {
  piece: Piece;
  squareFrom: string;
  squareTo: string;
  score: number;
}

function scoreMoveForPiece(
  board: any,
  piece: Piece,
  squareFrom: string,
  squareTo: string,
  team: Team,
  boardWidth: number,
  allPieces: Piece[]
): number {
  let score = 0;
  const otherTeam = getOtherTeam(team);

  // 1. Capture value (MVV-LVA)
  const targetPiece = board.state.position.squares[
    Position.squareToIndex(squareTo, boardWidth)
  ];
  if (targetPiece && getTeam(targetPiece) !== team) {
    const victimValue = pieceValue(targetPiece);
    const attackerValue = pieceValue(piece.type);
    // Strongly reward capturing high-value pieces with low-value pieces
    score += victimValue * 10 + (10 - attackerValue);
    if (targetPiece[1] === "q") score += 50;
    if (piece.type[1] === "p") score += 5;
  }

  // 2. Positional improvement
  const fromCoords = piece.position;
  const toCoords = Position.squareToCoordinates(squareTo) as Coords;
  const posFrom = positionalBonus(piece.type, fromCoords, team);
  const posTo = positionalBonus(piece.type, toCoords, team);
  score += (posTo - posFrom) * 2;

  // 3. Avoid moving valuable pieces into danger
  if (piece.type[1] !== "k") {
    const opponentPieces = allPieces.filter((p) => getTeam(p.type) === otherTeam);
    let isDestAttacked = false;
    for (const op of opponentPieces) {
      const opFrom = Position.coordinatesToSquare(op.position);
      const opMoves = potentialMoves(board, op.type, opFrom);
      if (opMoves.includes(squareTo)) {
        isDestAttacked = true;
        break;
      }
    }
    if (isDestAttacked) {
      score -= pieceValue(piece.type) * 3;
    }
  }

  // 4. Developing pieces off the back rank
  const backRank = team === "w" ? 0 : 9;
  if (fromCoords[1] === backRank && piece.type[1] !== "k") {
    score += 1.5;
  }

  // 5. Threatening opponent pieces from destination
  const destMoves = potentialMoves(board, piece.type, squareTo);
  for (const threatSquare of destMoves) {
    const idx = Position.squareToIndex(threatSquare, boardWidth);
    if (idx >= 0 && idx < board.state.position.squares.length) {
      const threatened = board.state.position.squares[idx];
      if (threatened && getTeam(threatened) !== team) {
        score += pieceValue(threatened) * 0.3;
        if (threatened[1] === "k") score += 15;
      }
    }
  }

  // 6. Pawn promotion proximity
  if (piece.type[1] === "p") {
    const promoRank = team === "w" ? 9 : 0;
    const distToPromo = Math.abs(toCoords[1] - promoRank);
    if (distToPromo <= 2) {
      score += (3 - distToPromo) * 5;
    }
  }

  // 7. King safety: keep pieces near our king
  const ourKing = allPieces.find((p) => p.type === team + "k");
  if (ourKing && piece.type[1] !== "k") {
    const distToKingFrom = Math.abs(fromCoords[0] - ourKing.position[0]) + Math.abs(fromCoords[1] - ourKing.position[1]);
    const distToKingTo = Math.abs(toCoords[0] - ourKing.position[0]) + Math.abs(toCoords[1] - ourKing.position[1]);
    if (distToKingTo < distToKingFrom && distToKingTo <= 3) {
      score += 0.5; // Slight bonus for defending near king
    }
  }

  return score;
}

// ============================================================
// Strategic AI: The main export
// ============================================================
export function strategicMoves(board: any, team: Team, state: State) {
  const boardWidth = board.props.boardWidth;

  let madeAMove = true;
  while (madeAMove) {
    madeAMove = false;

    const allPieces = squaresToPieces(board.state.position.squares, boardWidth);
    const teamPieces = allPieces.filter((p) => getTeam(p.type) === team);
    const allMoveScores: MoveScore[] = [];

    for (const p of teamPieces) {
      const squareFrom = Position.coordinatesToSquare(p.position);
      const moves = potentialMoves(board, p.type, squareFrom);

      for (const squareTo of moves) {
        const targetPiece = board.state.position.squares[
          Position.squareToIndex(squareTo, boardWidth)
        ];
        if (targetPiece && targetPiece[1] === "k") continue;

        const score = scoreMoveForPiece(board, p, squareFrom, squareTo, team, boardWidth, allPieces);
        allMoveScores.push({ piece: p, squareFrom, squareTo, score });
      }
    }

    if (allMoveScores.length === 0) break;

    // Sort descending by score, pick the best move
    allMoveScores.sort((a, b) => b.score - a.score);
    const best = allMoveScores[0];

    board.movePiece(best.squareFrom, best.squareTo, true);
    board.view.setPieceGreyedOut(best.squareTo, true);
    state.piecesMoved.push(best.squareTo);
    madeAMove = true;
  }
}

// ============================================================
// Original AI functions (kept for backward compatibility)
// ============================================================

export function randomMoves(board: any, team: Team, state: State) {
  const boardWidth = board.props.boardWidth;

  let pieceMoved = true;
  while (pieceMoved) {
    const allPieces = squaresToPieces(
      board.state.position.squares,
      boardWidth
    );
    const teamPieces = allPieces
      .filter((p) => getTeam(p.type) === team)
      .sort((a, b) => 0.5 - Math.random());
    pieceMoved = false;
    for (const p of teamPieces) {
      const squareFrom = Position.coordinatesToSquare(p.position);
      const moves = potentialMoves(board, p.type, squareFrom);
      if (moves.length > 0) {
        const moveIndex = getRandomInt(moves.length - 1);
        const squareTo = moves[moveIndex];
        board.movePiece(squareFrom, squareTo, true);
        board.view.setPieceGreyedOut(squareTo, true);
        pieceMoved = true;
        state.piecesMoved.push(squareTo);
        break;
      }
    }
  }
}

export function aggressiveMoves(board: any, team: Team, state: State) {
  const boardWidth = board.props.boardWidth;

  const allPieces = squaresToPieces(
    board.state.position.squares,
    boardWidth
  );
  const teamPieces = allPieces
    .filter((p) => getTeam(p.type) === team)
    .sort((a, b) => 0.5 - Math.random());

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

  for (const p of teamPieces) {
    const squareFrom = Position.coordinatesToSquare(p.position);
    if (state.piecesMoved.includes(squareFrom)) continue;
    const moves = potentialMoves(board, p.type, squareFrom);
    if (moves.length > 0) {
      const opponentPieces = allPieces.filter((p) => getTeam(p.type) !== team);
      let closestMove: string | null = null;
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
