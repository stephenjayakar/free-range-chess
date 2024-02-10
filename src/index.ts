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
  startPosition,
  Piece,
  squaresToPieces,
} from "./pieces";

declare global {
  interface Window {
    board: any;
    switchTurn: () => void;
    toggleValidation: () => void;
    printPieces: () => void;
    setPieces: (pieces: Piece[]) => void;
  }
}

const BOARD_WIDTH = 24;
const BOARD_HEIGHT = 20;

type Team = "w" | "b";

interface State {
  turn: Team;
  pieces: Piece[];
  piecesMoved: string[];
  validationEnabled: boolean;
}

const state: State = {
  turn: "w",
  pieces: startPosition(),
  // TODO: maybe a better name / abstraction.  This stores the
  // destination spaces of pieces. We know that you can't move a piece
  // again if it is the destination of a move.
  piecesMoved: [],
  validationEnabled: true,
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
  state.piecesMoved = [];
  log("switchTurn: " + state.turn);
};

window.toggleValidation = () => {
  state.validationEnabled = !state.validationEnabled;
  log(
    "move validation is now " +
      (state.validationEnabled ? "enabled" : "disabled")
  );
};

window.printPieces = () => {
  console.log(
    squaresToPieces(window.board.state.position.squares, BOARD_WIDTH)
  );
};

window.setPieces = (pieces: Piece[]) => {
  window.board.setPieces(pieces);
};

type InputEvent = any;

function inputHandler(event: InputEvent): boolean | void {
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
      if (state.validationEnabled) {
        log(`validateMoveInput: ${event.squareFrom}-${event.squareTo}`);
        const piece = event.chessboard.getPiece(event.squareFrom);
        const moves: any[] = potentialMoves(
          event.chessboard,
          piece,
          event.squareFrom
        );
        return moves.includes(event.squareTo);
      } else {
        return true;
      }
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
      state.piecesMoved.push(event.squareTo);
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

// TODO: this function uses state. should probably be passed in.
function potentialMoves(
  chessboard: any,
  piece: string,
  squareFrom: string
): any[] {
  console.log(state.piecesMoved, squareFrom);
  if (state.piecesMoved.includes(squareFrom)) {
    return [];
  }

  let retCoords: any[] = [];
  const team: string = getTeam(piece);
  const coords: [number, number] = Position.squareToCoordinates(squareFrom);
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
