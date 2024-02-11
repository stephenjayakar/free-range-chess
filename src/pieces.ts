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

export interface Piece {
  position: [number, number];
  // team: Team;
  type: string;
  // type: PIECE_TYPE;
}

export function startPosition(
  boardWidth: number,
  boardHeight: number
): Piece[] {
  return [
    {
      position: [0, 1],
      type: "wp",
    },
    {
      position: [1, 1],
      type: "wp",
    },
    {
      position: [2, 1],
      type: "wp",
    },
    {
      position: [3, 1],
      type: "wp",
    },
    {
      position: [4, 1],
      type: "wp",
    },
    {
      position: [5, 1],
      type: "wp",
    },
    {
      position: [6, 1],
      type: "wp",
    },
    {
      position: [7, 1],
      type: "wp",
    },
    {
      position: [0, 0],
      type: "wr",
    },
    {
      position: [1, 0],
      type: "wn",
    },
    {
      position: [2, 0],
      type: "wb",
    },
    {
      position: [7, 0],
      type: "wr",
    },
    {
      position: [6, 0],
      type: "wn",
    },
    {
      position: [5, 0],
      type: "wb",
    },
    {
      position: [3, 0],
      type: "wq",
    },
    {
      position: [4, 0],
      type: "wk",
    },
    {
      position: [boardWidth - 1, boardHeight - 2],
      type: "bp",
    },
    {
      position: [boardWidth - 2, boardHeight - 2],
      type: "bp",
    },
    {
      position: [boardWidth - 3, boardHeight - 2],
      type: "bp",
    },
    {
      position: [boardWidth - 4, boardHeight - 2],
      type: "bp",
    },
    {
      position: [boardWidth - 5, boardHeight - 2],
      type: "bp",
    },
    {
      position: [boardWidth - 6, boardHeight - 2],
      type: "bp",
    },
    {
      position: [boardWidth - 7, boardHeight - 2],
      type: "bp",
    },
    {
      position: [boardWidth - 8, boardHeight - 2],
      type: "bp",
    },
    {
      position: [boardWidth - 1, boardHeight - 1],
      type: "br",
    },
    {
      position: [boardWidth - 2, boardHeight - 1],
      type: "bn",
    },
    {
      position: [boardWidth - 3, boardHeight - 1],
      type: "bb",
    },
    {
      position: [boardWidth - 4, boardHeight - 1],
      type: "bq",
    },
    {
      position: [boardWidth - 5, boardHeight - 1],
      type: "bk",
    },
    {
      position: [boardWidth - 6, boardHeight - 1],
      type: "bb",
    },
    {
      position: [boardWidth - 7, boardHeight - 1],
      type: "bn",
    },
    {
      position: [boardWidth - 8, boardHeight - 1],
      type: "br",
    },
  ];
}

type square = string | null;

// The underlying position format for the board is just a giant array
// of squares and piece monikers. However, we're using the Pieces[]
// object to refer to positions as it's significantly more dense of a
// format, as well as pretty readable.
export function squaresToPieces(
  squares: square[],
  boardWidth: number
): Piece[] {
  const pieces = [];
  for (let i = 0; i < squares.length; ++i) {
    if (squares[i] != null) {
      const square = Position.indexToSquare(i, boardWidth);
      const coords = Position.squareToCoordinates(square);
      pieces.push({
        type: squares[i],
        position: coords,
      });
    }
  }
  return pieces;
}
