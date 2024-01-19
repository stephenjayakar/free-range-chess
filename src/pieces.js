import { Position } from "chessboard/model/Position";

export function getPawnMoves(startCoords, team, board) {
  return pathMarchPotentialMoves(startCoords, team, 1, true, true, board);
}

export function getBishopMoves(startCoords, team, board) {
  return pathMarchPotentialMoves(startCoords, team, 7, true, false, board);
}

export function getRookMoves(startCoords, team, board) {
  return pathMarchPotentialMoves(startCoords, team, 7, false, true, board);
}

export function getQueenMoves(startCoords, team, board) {
  return pathMarchPotentialMoves(startCoords, team, 7, true, true, board);
}

export function getKingMoves(startCoords, team, board) {
  // TODO: add support for checkmate
  return getPawnMoves(startCoords, team, board);
}

export function getKnightMoves(
  startCoords,
  team,
  board,
) {
  const [x, y] = startCoords;
  const potentialMoves = [
    [x + 1, y + 2],
    [x - 1, y + 2],
    [x + 1, y - 2],
    [x - 1, y - 2],
    [x + 2, y + 1],
    [x - 2, y + 1],
    [x + 2, y - 1],
    [x - 2, y - 1],
  ]

  return potentialMoves.filter((m) => {
    if (!moveInBounds(board, m)) {
      return false
    }
    const possibleSquare = Position.coordinatesToSquare(m);
    const possiblePiece = board.getPiece(possibleSquare);
    if (possiblePiece) {
      return getTeam(possiblePiece) !== team;
    } else {
      return true;
    }
  });

}

// TODO(sjayakar): I would like a test
export function pathMarchPotentialMoves(
  startCoords,
  team,
  // 1 -> 7; not a requirement
  maxDistance,
  allowDiagonals,
  allowStraight,
  // TODO(sjayakar): consider passing in all the pieces. something to
  // think about is some pieces _might_ not block movement.
  //
  // So what I need is
  // - board width + height for boundary
  // - location of all the pieces
  board
) {
  const [startX, startY] = startCoords;
  const possibleCoords = [];

  if (allowDiagonals) {
    // If any of the directions get blocked, don't add any more moves
    // in that direction
    let TLBlocked = false;
    let TRBlocked = false;
    let BLBlocked = false;
    let BRBlocked = false;
    for (let i = 1; i <= maxDistance; ++i) {
      TLBlocked = potentiallyAddDirection(
        board,
        team,
        possibleCoords,
        [startX - i, startY + i],
        TLBlocked
      );
      TRBlocked = potentiallyAddDirection(
        board,
        team,
        possibleCoords,
        [startX + i, startY + i],
        TRBlocked
      );
      BLBlocked = potentiallyAddDirection(
        board,
        team,
        possibleCoords,
        [startX - i, startY - i],
        BLBlocked
      );
      BRBlocked = potentiallyAddDirection(
        board,
        team,
        possibleCoords,
        [startX + i, startY - i],
        BRBlocked
      );
    }
  }
  if (allowStraight) {
    // If any of the directions get blocked, don't add any more moves
    // in that direction
    let upBlocked = false;
    let downBlocked = false;
    let leftBlocked = false;
    let rightBlocked = false;
    for (let i = 1; i <= maxDistance; ++i) {
      upBlocked = potentiallyAddDirection(
        board,
        team,
        possibleCoords,
        [startX, startY + i],
        upBlocked
      );
      downBlocked = potentiallyAddDirection(
        board,
        team,
        possibleCoords,
        [startX, startY - i],
        downBlocked
      );
      leftBlocked = potentiallyAddDirection(
        board,
        team,
        possibleCoords,
        [startX - i, startY],
        leftBlocked
      );
      rightBlocked = potentiallyAddDirection(
        board,
        team,
        possibleCoords,
        [startX + i, startY],
        rightBlocked
      );
    }
  }
  return possibleCoords;
}

function moveInBounds(
  board,
  move,
) {
  const [x, y] = move;
  return !(x < 0 || x >= board.props.boardWidth || y < 0 || y >= board.props.boardHeight);
}

// mutates move list, returns blocked
function potentiallyAddDirection(
  board,
  team,
  possibleMoves,
  possibleMove,
  blocked
) {
  if (blocked) {
    return blocked;
  }

  if (!moveInBounds(board, possibleMove)) {
    return blocked;
  }

  const possibleSquare = Position.coordinatesToSquare(possibleMove);

  const possiblePiece = board.getPiece(possibleSquare);
  if (possiblePiece) {
    // Regardless, both of these will block the piece from
    // future moves. However, if it's an enemy piece, we can
    // still move there.
    blocked = true;
    if (getTeam(possiblePiece) !== team) {
      possibleMoves.push(possibleMove);
    }
  } else {
    possibleMoves.push(possibleMove);
  }

  return blocked;
}

export function getTeam(piece) {
  return piece[0];
}
