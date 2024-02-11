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
    checkIfCheck: () => void;
  }
}

const BOARD_WIDTH = 10;
const BOARD_HEIGHT = 10;

type Team = "w" | "b";

type Coords = [number, number];

function getOtherTeam(team: Team): Team {
  return team == "w" ? "b" : "w";
}

interface State {
  turn: Team;
  pieces: Piece[];
  piecesMoved: string[];
  validationEnabled: boolean;
  // TODO: remove this (make it derived from winner)
  gameOver: boolean;
  winner: Team | null;
}

const state: State = {
  turn: "w",
  pieces: startPosition(BOARD_WIDTH, BOARD_HEIGHT),
  // TODO: maybe a better name / abstraction.  This stores the
  // destination spaces of pieces. We know that you can't move a piece
  // again if it is the destination of a move.
  piecesMoved: [],
  validationEnabled: true,
  gameOver: false,
  winner: null,
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

function updateGameStatus(message: string): void {
  const statusElement = document.getElementById("statusMessage") as HTMLElement;
  statusElement.innerText = message;
}

function updateGameOver(winner: Team): void {
  const winnerElement = document.getElementById("winnerMessage") as HTMLElement;
  winnerElement.innerText = `Game Over - Winner: ${winner.toUpperCase()}`;
}

function checkAndDisplayCheck(): void {
  const inCheck = checkIfKingIsThreatened(state.turn, window.board);
  if (inCheck) {
    updateGameStatus(`${state.turn.toUpperCase()} is in check`);
  } else {
    updateGameStatus(""); // Clear status message if not in check
  }
}

window.switchTurn = () => {
  if (state.gameOver) {
    log("The game is over. No more turns allowed.");
    return;
  }

  const inCheck = checkIfKingIsThreatened(state.turn, window.board);
  if (inCheck) {
    state.gameOver = true;
    state.winner = getOtherTeam(state.turn);
    updateGameStatus(`Game Over - ${state.turn.toUpperCase()} lost.`);
  } else {
    state.turn = getOtherTeam(state.turn);
    state.piecesMoved = [];
    log("switchTurn: " + state.turn);
    checkAndDisplayCheck();
  }
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

window.checkIfCheck = (): void => {
  const team = state.turn;
  const isCheck = checkIfKingIsThreatened(team, window.board);
  log(`team ${team} check status: ${isCheck}`);
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

        // Don't allow the king to be taken
        const potentialOtherPiece = event.chessboard.getPiece(event.squareTo);
        if (potentialOtherPiece && potentialOtherPiece[1] == "k") {
          return false;
        }

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
  if (state.piecesMoved.includes(squareFrom)) {
    return [];
  }

  const team: string = getTeam(piece);
  const coords: Coords = Position.squareToCoordinates(squareFrom);
  const retCoords = getPieceMoves(chessboard, piece, team, coords);

  return retCoords.map((c: Coords) => Position.coordinatesToSquare(c));
}

function getPieceMoves(
  chessboard: any,
  // TODO: consider refactoring to use `Piece` as then you don't have to pass in coords separately.
  piece: string,
  team: string,
  coords: Coords
): Coords[] {
  if (piece[1] === "p") {
    return getPawnMoves(coords, team, chessboard);
  } else if (piece[1] === "b") {
    return getBishopMoves(coords, team, chessboard);
  } else if (piece[1] === "q") {
    return getQueenMoves(coords, team, chessboard);
  } else if (piece[1] === "k") {
    return getKingMoves(coords, team, chessboard);
  } else if (piece[1] === "r") {
    return getRookMoves(coords, team, chessboard);
  } else if (piece[1] === "n") {
    return getKnightMoves(coords, team, chessboard);
  } else {
    return [];
  }
}

function coordsEqual(c1: Coords, c2: Coords): boolean {
  return c1[0] === c2[0] && c1[1] === c2[1];
}

// Essentially checks if the king is in check. It's weird to say
// "checkCheck" though LOL.
//
// High level:
// 1. Find the king
// 2. Check all the other pieces on the
// other team, and see if any of their potential moves include the
// king in it.
export function checkIfKingIsThreatened(team: Team, chessboard: any): boolean {
  const pieces = squaresToPieces(
    chessboard.state.position.squares,
    BOARD_WIDTH
  );
  const pieceType = team + "k";

  const king = pieces.find((p) => p.type === pieceType);

  const otherTeam = getOtherTeam(team);
  const otherTeamPieces = pieces.filter((p) => getTeam(p.type) === otherTeam);

  const pieceThreatensKing = otherTeamPieces.some((p) => {
    const moves = getPieceMoves(chessboard, p.type, otherTeam, p.position);
    const moveIncludesKing = moves.some((m) => {
      return coordsEqual(m, king.position);
    });
    return moveIncludesKing;
  });
  return pieceThreatensKing;
}
