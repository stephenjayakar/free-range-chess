import { Position } from "chessboard/model/Position";

export function getPawnMoves(
  startCoords: [number, number],
  team: string,
  board: any
): any[] {
  return pathMarchPotentialMoves(startCoords, team, 1, true, true, board);
}

export function getBishopMoves(
  startCoords: [number, number],
  team: string,
  board: any
): any[] {
  return pathMarchPotentialMoves(startCoords, team, 7, true, false, board);
}

export function getRookMoves(
  startCoords: [number, number],
  team: string,
  board: any
): any[] {
  return pathMarchPotentialMoves(startCoords, team, 7, false, true, board);
}

export function getQueenMoves(
  startCoords: [number, number],
  team: string,
  board: any
): any[] {
  return pathMarchPotentialMoves(startCoords, team, 7, true, true, board);
}

export function getKingMoves(
  startCoords: [number, number],
  team: string,
  board: any
): any[] {
  // TODO: add more king rules
  return getPawnMoves(startCoords, team, board);
}

export function getKnightMoves(
  startCoords: [number, number],
  team: string,
  board: any
): any[] {
  const [x, y] = startCoords;
  const potentialMoves: [number, number][] = [
    [x + 1, y + 2],
    [x - 1, y + 2],
    [x + 1, y - 2],
    [x - 1, y - 2],
    [x + 2, y + 1],
    [x - 2, y + 1],
    [x + 2, y - 1],
    [x - 2, y - 1],
  ];

  return potentialMoves.filter((m) => {
    if (!moveInBounds(board, m)) {
      return false;
    }

    const possibleSquare = Position.coordinatesToSquare(m);
    const possiblePiece = board.getPiece(possibleSquare);
    return !possiblePiece || getTeam(possiblePiece) !== team;
  });
}

// TODO(sjayakar): I would like a test
export function pathMarchPotentialMoves(
  startCoords: [number, number],
  team: string,
  maxDistance: number,
  allowDiagonals: boolean,
  allowStraight: boolean,
  board: any
): any[] {
  const [startX, startY] = startCoords;
  const possibleCoords: [number, number][] = [];

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

function moveInBounds(board: any, move: [number, number]): boolean {
  const [x, y] = move;
  return (
    x >= 0 &&
    x < board.props.boardWidth &&
    y >= 0 &&
    y < board.props.boardHeight
  );
}

// mutates move list, returns blocked
function potentiallyAddDirection(
  board: any,
  team: string,
  possibleMoves: [number, number][],
  possibleMove: [number, number],
  blocked: boolean
): boolean {
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

export function getTeam(piece: string): string {
  return piece[0];
}
