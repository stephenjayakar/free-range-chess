import { INPUT_EVENT_TYPE, Chessboard } from "../src/Chessboard.js";
import { FEN, Position } from "../src/model/Position.js";
import { Markers, MARKER_TYPE } from "../src/extensions/markers/Markers.js";

window.board = new Chessboard(document.getElementById("board"), {
  position: FEN.start,
  assetsUrl: "../assets/",
  style: { pieces: { file: "pieces/staunty.svg" } },
  extensions: [{ class: Markers }],
  boardWidth: 24,
  boardHeight: 20,
});

window.board.enableMoveInput(inputHandler);

function inputHandler(event) {
  console.log(event);
  switch (event.type) {
    case INPUT_EVENT_TYPE.moveInputStarted:
      log(`moveInputStarted: ${event.squareFrom}`);
      const piece = event.chessboard.getPiece(event.squareFrom);
      const moves = potentialMoves(event.chessboard, piece, event.squareFrom);
      moves.forEach((s) => {
        event.chessboard.addMarker(MARKER_TYPE.dot, s);
      });
      // TODO: I think I would plug in the dot rendering method here.
      return true; // false cancels move
    case INPUT_EVENT_TYPE.validateMoveInput:
      log(`validateMoveInput: ${event.squareFrom}-${event.squareTo}`);
      //       log(`piece: ${window.board.getPiece(event.squareFrom)}`);
      return true; // false cancels move
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
  // TODO: branch on piece. assuming pawn
  // TODO: check for collisions
  // - and if it's allied, it's not a valid move

  if (piece[1] !== "p") {
    return [];
  }

  const [x, y] = Position.squareToCoordinates(square);
  const possibleCoords = [
    [x + 1, y],
    [x - 1, y],
    [x, y + 1],
    [x, y - 1],
    [x - 1, y - 1],
    [x + 1, y + 1],
    [x + 1, y - 1],
    [x - 1, y + 1],
  ];

  const coords = [];
  possibleCoords.forEach((c) => {
    const [cx, cy] = c;
    // Board boundary condition
    if (
      cx < 0 ||
      cy < 0 ||
      cx >= chessboard.props.boardWidth ||
      cy >= chessboard.props.boardHeight
    ) {
      return;
    }

    // Reject if the same team owns a piece in one of the potential move squares
    const s = Position.coordinatesToSquare(c);
    const otherPiece = chessboard.getPiece(s);
    if (otherPiece) {
      if (otherPiece[0] === piece[0]) {
        // same team, reject it
        return;
      }
    } else {
      // TODO: add a bevel somehow...
      // maybe i can add like "move" vs "attack". we can add other types of moves later
    }
    coords.push(c);
  });

  return coords.map((c) => Position.coordinatesToSquare(c));
}
