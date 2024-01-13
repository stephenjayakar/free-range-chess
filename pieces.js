import { Position } from "../src/model/Position.js";

export function getBishopMoves(
  startCoords,
  team,
  board,
) {
  return pathMarchPotentialMoves(
    startCoords,
    team,
    7,
    true,
    false,
    board
  )
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
  board,
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
        TLBlocked,
      );
      TRBlocked = potentiallyAddDirection(
        board,
        team,
        possibleCoords,
        [startX + i, startY + i],
        TRBlocked,
      );
      BLBlocked = potentiallyAddDirection(
        board,
        team,
        possibleCoords,
        [startX - i, startY - i],
        BLBlocked,
      );
      BRBlocked = potentiallyAddDirection(
        board,
        team,
        possibleCoords,
        [startX + i, startY - i],
        BRBlocked,
      );
    }
  }
  return possibleCoords;
}

// mutates move list, returns blocked
function potentiallyAddDirection(
  board,
  team,
  possibleMoves,
  possibleMove,
  blocked,
) {
  // TODO: add board boundary condition
  if (blocked) {
    return blocked;
  }

  const possibleSquare = Position.coordinatesToSquare(
    possibleMove,
  );

  const possiblePiece = board.getPiece(possibleSquare)
  if (possiblePiece) {
    // Regardless, both of these will block the piece from
    // future moves. However, if it's an enemy piece, we can
    // still move there.
    blocked = true;
    if (!getTeam(possiblePiece) === team) {
      possibleMoves.push(possibleMove);
    }
  } else {
    possibleMoves.push(possibleMove);
  }

  return blocked;
}

export function getTeam(
  piece,
) {
  return piece[0];
}
