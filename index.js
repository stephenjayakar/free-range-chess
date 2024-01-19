import { INPUT_EVENT_TYPE, Chessboard } from "../src/Chessboard.js";
import { FEN, Position } from "../src/model/Position.js";
import { Markers, MARKER_TYPE } from "../src/extensions/markers/Markers.js";
import {
  getBishopMoves,
  getPawnMoves,
  getRookMoves,
  getKingMoves,
  getQueenMoves,
  getKnightMoves,
  getTeam,
} from "./pieces.js";

window.board = new Chessboard(document.getElementById("board"), {
  position: FEN.start,
  assetsUrl: "../assets/",
  style: { pieces: { file: "pieces/staunty.svg" } },
  extensions: [{ class: Markers }],
  boardWidth: 24,
  boardHeight: 20,
});

window.board.enableMoveInput(inputHandler);

const state = {
  turn: "w",
};

window.switchTurn = () => {
  if (state.turn === "w") {
    state.turn = "b";
  } else {
    state.turn = "w";
  }
};

function inputHandler(event) {
  console.log(event);
  switch (event.type) {
    case INPUT_EVENT_TYPE.moveInputStarted: {
      log(`moveInputStarted: ${event.squareFrom}`);
      const piece = event.chessboard.getPiece(event.squareFrom);

      // Make sure it's the team's turn
      const pieceTeam = getTeam(piece);
      if (pieceTeam !== state.turn) {
        return false;
      }

      const moves = potentialMoves(event.chessboard, piece, event.squareFrom);
      moves.forEach((s) => {
        event.chessboard.addMarker(MARKER_TYPE.dot, s);
      });
      // TODO: I think I would plug in the dot rendering method here.
      return true;
    }
    case INPUT_EVENT_TYPE.validateMoveInput: {
      log(`validateMoveInput: ${event.squareFrom}-${event.squareTo}`);
      const piece = event.chessboard.getPiece(event.squareFrom);
      const moves = potentialMoves(event.chessboard, piece, event.squareFrom);
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

const output = document.getElementById("output");

function log(text) {
  const log = document.createElement("div");
  log.innerText = text;
  output.appendChild(log);
}

// returns a list of squares
function potentialMoves(chessboard, piece, square) {
  let retCoords = [];
  const team = getTeam(piece);
  const coords = Position.squareToCoordinates(square);
  if (piece[1] === "p") {
    retCoords = [...getPawnMoves(coords, team, board)];
  } else if (piece[1] === "b") {
    retCoords = [...getBishopMoves(coords, team, board)];
  } else if (piece[1] === "q") {
    retCoords = [...getQueenMoves(coords, team, board)];
  } else if (piece[1] === "k") {
    retCoords = [...getKingMoves(coords, team, board)];
  } else if (piece[1] === "r") {
    retCoords = [...getRookMoves(coords, team, board)];
  } else if (piece[1] === "n") {
    retCoords = [...getKnightMoves(coords, team, board)];
  }

  return retCoords.map((c) => Position.coordinatesToSquare(c));
}
