import "./css/examples.css";
import "./css/chessboard.css";
import "./css/markers.css";

import { INPUT_EVENT_TYPE, Chessboard } from "chessboard/Chessboard";
import { FEN, Position } from "chessboard/model/Position";
import { Markers, MARKER_TYPE } from "chessboard/extensions/markers/Markers";
import {
  getBishopMoves,
  getPawnMoves,
  getRookMoves,
  getKingMoves,
  getQueenMoves,
  getKnightMoves,
  getTeam,
} from "./pieces";

declare global {
  interface Window {
    board: any;
    switchTurn: () => void;
  }
}

const BOARD_WIDTH = 24;
const BOARD_HEIGHT = 20;

// enum PIECE_TYPE {
//   PAWN,
//   ROOK,
//   KNIGHT,
//   BISHOP,
//   KING,
//   QUEEN,
// }

type Team = "w" | "b";

interface Piece {
  position: [number, number];
  // team: Team;
  type: string;
  // type: PIECE_TYPE;
}

interface State {
  turn: Team;
  pieces: Piece[];
}

const state: State = {
  turn: "w",
  pieces: [
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
      position: [23, 18],
      type: "bp",
    },
    {
      position: [22, 18],
      type: "bp",
    },
    {
      position: [21, 18],
      type: "bp",
    },
    {
      position: [20, 18],
      type: "bp",
    },
    {
      position: [19, 18],
      type: "bp",
    },
    {
      position: [18, 18],
      type: "bp",
    },
    {
      position: [17, 18],
      type: "bp",
    },
    {
      position: [16, 18],
      type: "bp",
    },
    {
      position: [23, 19],
      type: "br",
    },
    {
      position: [22, 19],
      type: "bn",
    },
    {
      position: [21, 19],
      type: "bb",
    },
    {
      position: [16, 19],
      type: "br",
    },
    {
      position: [17, 19],
      type: "bn",
    },
    {
      position: [18, 19],
      type: "bb",
    },
    {
      position: [20, 19],
      type: "bq",
    },
    {
      position: [19, 19],
      type: "bk",
    },
  ],
};

window.board = new Chessboard(document.getElementById("board") as HTMLElement, {
  position: state.pieces,
  assetsUrl: "/assets/",
  style: { pieces: { file: "pieces/staunty.svg" } },
  extensions: [{ class: Markers }],
  boardWidth: BOARD_WIDTH,
  boardHeight: BOARD_HEIGHT,
});

window.board.enableMoveInput(inputHandler);

window.switchTurn = () => {
  state.turn = state.turn === "w" ? "b" : "w";
  log("switchTurn: " + state.turn);
};

type InputEvent = any;

function inputHandler(event: InputEvent): boolean | void {
  console.log(event);
  switch (event.type) {
    case INPUT_EVENT_TYPE.moveInputStarted: {
      log(`moveInputStarted: ${event.squareFrom}`);
      const piece = event.chessboard.getPiece(event.squareFrom);

      const pieceTeam = getTeam(piece);
      if (pieceTeam !== state.turn) {
        return false;
      }

      const moves: any[] = potentialMoves(
        event.chessboard,
        piece,
        event.squareFrom
      );
      moves.forEach((s) => {
        event.chessboard.addMarker(MARKER_TYPE.dot, s);
      });
      return true;
    }
    case INPUT_EVENT_TYPE.validateMoveInput: {
      log(`validateMoveInput: ${event.squareFrom}-${event.squareTo}`);
      const piece = event.chessboard.getPiece(event.squareFrom);
      const moves: any[] = potentialMoves(
        event.chessboard,
        piece,
        event.squareFrom
      );
      return moves.includes(event.squareTo);
    }
    case INPUT_EVENT_TYPE.moveInputCanceled:
      log(`moveInputCanceled`);
      event.chessboard.removeMarkers(MARKER_TYPE.dot);
      event.chessboard.removeMarkers(MARKER_TYPE.bevel);
      break;
    case INPUT_EVENT_TYPE.moveInputFinished:
      log(`moveInputFinished`);
      event.chessboard.removeMarkers(MARKER_TYPE.dot);
      event.chessboard.removeMarkers(MARKER_TYPE.bevel);
      break;
    case INPUT_EVENT_TYPE.movingOverSquare:
      log(`movingOverSquare: ${event.squareTo}`);
      break;
  }
}

const output: HTMLElement = document.getElementById("output") as HTMLElement;

function log(text: string): void {
  const logElement: HTMLDivElement = document.createElement("div");
  logElement.innerText = text;
  output.appendChild(logElement);
}

function potentialMoves(chessboard: any, piece: string, square: string): any[] {
  let retCoords: any[] = [];
  const team: string = getTeam(piece);
  const coords: [number, number] = Position.squareToCoordinates(square);
  if (piece[1] === "p") {
    retCoords = getPawnMoves(coords, team, chessboard);
  } else if (piece[1] === "b") {
    retCoords = getBishopMoves(coords, team, chessboard);
  } else if (piece[1] === "q") {
    retCoords = getQueenMoves(coords, team, chessboard);
  } else if (piece[1] === "k") {
    retCoords = getKingMoves(coords, team, chessboard);
  } else if (piece[1] === "r") {
    retCoords = getRookMoves(coords, team, chessboard);
  } else if (piece[1] === "n") {
    retCoords = getKnightMoves(coords, team, chessboard);
  }

  return retCoords.map((c: [number, number]) =>
    Position.coordinatesToSquare(c)
  );
}
