import "./css/examples.css";
import "./css/chessboard.css";
import "./css/markers.css";

import { INPUT_EVENT_TYPE, Chessboard } from "chessboard/Chessboard";
import { Position } from "chessboard/model/Position";
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
  Coords,
  Team,
  getOtherTeam,
} from "./pieces";

import { randomMoves, aggressiveMoves, strategicMoves } from "./ai";

declare global {
  interface Window {
    board: any;
    switchTurn: () => void;
    toggleValidation: () => void;
    printPieces: () => void;
    setPieces: (pieces: Piece[]) => void;
    checkIfCheck: () => void;
    runAI: () => void;
    aiModel: string;
    newGame: () => void;
  }
}

const BOARD_WIDTH = 10;
const BOARD_HEIGHT = 10;

// Unicode chess piece symbols for captured pieces display
const PIECE_SYMBOLS: Record<string, string> = {
  wk: "♔", wq: "♕", wr: "♖", wb: "♗", wn: "♘", wp: "♙",
  bk: "♚", bq: "♛", br: "♜", bb: "♝", bn: "♞", bp: "♟",
};

const PIECE_NAMES: Record<string, string> = {
  k: "King", q: "Queen", r: "Rook", b: "Bishop", n: "Knight", p: "Pawn",
};

export interface State {
  turn: Team;
  pieces: Piece[];
  piecesMoved: string[];
  validationEnabled: boolean;
  winner: Team | null;
  moveCount: number;
  capturedWhite: string[]; // white pieces captured by black
  capturedBlack: string[]; // black pieces captured by white
}

const state: State = {
  turn: "w",
  pieces: startPosition(BOARD_WIDTH, BOARD_HEIGHT),
  piecesMoved: [],
  validationEnabled: true,
  winner: null,
  moveCount: 1,
  capturedWhite: [],
  capturedBlack: [],
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

// ============================================================
// UI Update Functions
// ============================================================

function updateGameStatus(message: string): void {
  const el = document.getElementById("statusMessage") as HTMLElement;
  el.innerText = message;
  el.className = message ? "status-alert" : "";
}

function updateTurnMessage(): void {
  const el = document.getElementById("turnMessage") as HTMLElement;
  const isWhite = state.turn === "w";
  el.innerHTML = `<span class="turn-badge ${isWhite ? 'turn-white' : 'turn-black'}">${isWhite ? '♔' : '♚'}</span> ${isWhite ? "White" : "Black"}'s Turn`;
}

function updateMoveCount(): void {
  const el = document.getElementById("moveCount") as HTMLElement;
  el.innerText = `Move ${state.moveCount}`;
}

function updateCapturedPieces(): void {
  const whiteEl = document.getElementById("capturedWhite") as HTMLElement;
  const blackEl = document.getElementById("capturedBlack") as HTMLElement;
  
  whiteEl.innerHTML = state.capturedWhite.length > 0
    ? state.capturedWhite.map(p => `<span class="captured-piece" title="${PIECE_NAMES[p[1]] || p}">${PIECE_SYMBOLS[p] || p}</span>`).join("")
    : '<span class="no-captures">—</span>';
    
  blackEl.innerHTML = state.capturedBlack.length > 0
    ? state.capturedBlack.map(p => `<span class="captured-piece" title="${PIECE_NAMES[p[1]] || p}">${PIECE_SYMBOLS[p] || p}</span>`).join("")
    : '<span class="no-captures">—</span>';
}

function showGameOver(winner: Team): void {
  const overlay = document.getElementById("gameOverOverlay") as HTMLElement;
  const msg = document.getElementById("gameOverMessage") as HTMLElement;
  const winnerName = winner === "w" ? "White" : "Black";
  const loserName = winner === "w" ? "Black" : "White";
  msg.innerHTML = `<span class="winner-icon">${winner === 'w' ? '♔' : '♚'}</span><br>${winnerName} Wins!<br><span class="game-over-sub">${loserName}'s king is in check at end of turn</span>`;
  overlay.classList.add("visible");
}

function hideGameOver(): void {
  const overlay = document.getElementById("gameOverOverlay") as HTMLElement;
  overlay.classList.remove("visible");
}

function startTurnChecks(): void {
  const inCheck = checkIfKingIsThreatened(state.turn, window.board);
  if (inCheck) {
    updateGameStatus(`⚠ ${state.turn === "w" ? "White" : "Black"} is in check!`);
  } else {
    updateGameStatus("");
  }
}

// Track captures when a piece moves to a square with an opponent piece
function trackCapture(squareTo: string): void {
  const boardWidth = window.board.props.boardWidth;
  const targetPiece = window.board.state.position.squares[
    Position.squareToIndex(squareTo, boardWidth)
  ];
  if (targetPiece) {
    const targetTeam = getTeam(targetPiece);
    if (targetTeam === "w") {
      state.capturedWhite.push(targetPiece);
    } else {
      state.capturedBlack.push(targetPiece);
    }
    updateCapturedPieces();
  }
}

// ============================================================
// Game Actions
// ============================================================

window.switchTurn = () => {
  if (state.winner) {
    log("The game is over. No more turns allowed.");
    return;
  }
  if (state.piecesMoved.length === 0) {
    return;
  }

  const inCheck = checkIfKingIsThreatened(state.turn, window.board);
  if (inCheck) {
    state.winner = getOtherTeam(state.turn);
    updateGameStatus("");
    showGameOver(state.winner);
  } else {
    state.turn = getOtherTeam(state.turn);
    state.piecesMoved = [];
    state.moveCount++;
    log("switchTurn: " + state.turn);
    updateTurnMessage();
    updateMoveCount();

    window.board.view.clearGreyedPieces();
    window.board.view.redrawPieces();

    startTurnChecks();
  }
};

window.toggleValidation = () => {
  state.validationEnabled = !state.validationEnabled;
  const btn = document.getElementById("toggleValidationBtn") as HTMLElement;
  if (btn) {
    btn.innerText = state.validationEnabled ? "🛡 Validation: ON" : "⚡ Validation: OFF";
    btn.classList.toggle("btn-active", state.validationEnabled);
  }
  log("move validation is now " + (state.validationEnabled ? "enabled" : "disabled"));
};

window.printPieces = () => {
  console.log(squaresToPieces(window.board.state.position.squares, BOARD_WIDTH));
};

window.setPieces = (pieces: Piece[]) => {
  window.board.setPieces(pieces);
};

window.checkIfCheck = (): void => {
  const team = state.turn;
  const isCheck = checkIfKingIsThreatened(team, window.board);
  log(`team ${team} check status: ${isCheck}`);
};

window.aiModel = "alphazero";

const AI_SERVER_URL = "http://localhost:8080";

async function runAlphaZeroAI(board: any, team: Team, gameState: State): Promise<void> {
  const boardWidth = board.props.boardWidth;
  const boardHeight = board.props.boardHeight;
  const squares = board.state.position.squares;

  // Build pieces array in the format the server expects
  const pieces: Array<{square: string, piece: string}> = [];
  for (let i = 0; i < squares.length; i++) {
    if (squares[i]) {
      const x = i % boardWidth;
      const y = Math.floor(i / boardWidth);
      pieces.push({
        square: `${x},${y}`,
        piece: squares[i],
      });
    }
  }

  const body = {
    pieces,
    turn: team,
    pieces_moved: gameState.piecesMoved.map((sq: string) => {
      const coords = Position.squareToCoordinates(sq);
      return `${coords[0]},${coords[1]}`;
    }),
    board_width: boardWidth,
    board_height: boardHeight,
  };

  const btn = document.getElementById("runAIBtn") as HTMLButtonElement;
  btn.disabled = true;
  btn.innerText = "🤔 Thinking...";

  try {
    const resp = await fetch(`${AI_SERVER_URL}/api/play-turn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!resp.ok) {
      const err = await resp.text();
      throw new Error(`Server error ${resp.status}: ${err}`);
    }

    const data = await resp.json();
    log(`AlphaZero thought for ${data.thinking_time_ms}ms (${data.simulations} sims)`);

    // Apply each move the AI returned
    for (const move of data.moves) {
      const fromSquare = Position.coordinatesToSquare(
        move.square_from.split(",").map(Number)
      );
      const toSquare = Position.coordinatesToSquare(
        move.square_to.split(",").map(Number)
      );

      trackCapture(toSquare);
      board.movePiece(fromSquare, toSquare, true);
      board.view.setPieceGreyedOut(toSquare, true);
      gameState.piecesMoved.push(toSquare);
    }

    if (data.moves.length === 0) {
      log("AlphaZero made no moves (may be stuck)");
    } else {
      log(`AlphaZero made ${data.moves.length} move(s)`);
    }
  } catch (e: any) {
    log(`❌ AlphaZero error: ${e.message}`);
    log("Is the AI server running? Start it with:");
    log("  cd python && source venv/bin/activate && python ai_server.py");
  } finally {
    btn.disabled = false;
    btn.innerText = "🤖 Run AI";
  }

  updateCapturedPieces();
}

window.runAI = (): void => {
  const aiSelector = document.getElementById("aiSelector") as HTMLSelectElement;
  window.aiModel = aiSelector.value;
  const team = state.turn;
  log(`Running ${window.aiModel} AI for ${team === "w" ? "White" : "Black"}`);
  
  if (window.aiModel === "alphazero") {
    runAlphaZeroAI(window.board, team, state);
    return; // async — don't call updateCapturedPieces synchronously
  } else if (window.aiModel === "random") {
    randomMoves(window.board, team, state);
  } else if (window.aiModel === "aggressive") {
    aggressiveMoves(window.board, team, state);
  } else if (window.aiModel === "strategic") {
    strategicMoves(window.board, team, state);
  }
  updateCapturedPieces();
};

window.newGame = (): void => {
  state.turn = "w";
  state.pieces = startPosition(BOARD_WIDTH, BOARD_HEIGHT);
  state.piecesMoved = [];
  state.validationEnabled = true;
  state.winner = null;
  state.moveCount = 1;
  state.capturedWhite = [];
  state.capturedBlack = [];
  
  window.board.setPieces(state.pieces);
  window.board.view.clearGreyedPieces();
  window.board.view.redrawPieces();
  
  updateTurnMessage();
  updateMoveCount();
  updateCapturedPieces();
  updateGameStatus("");
  hideGameOver();
  
  const output = document.getElementById("output") as HTMLElement;
  output.innerHTML = "";
  log("New game started!");
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
      const moves: any[] = potentialMoves(event.chessboard, piece, event.squareFrom);
      moves.forEach((s) => {
        event.chessboard.addMarker(MARKER_TYPE.dot, s);
      });
      return true;
    }
    case INPUT_EVENT_TYPE.validateMoveInput: {
      if (state.validationEnabled) {
        log(`validateMoveInput: ${event.squareFrom}-${event.squareTo}`);
        const piece = event.chessboard.getPiece(event.squareFrom);
        const moves: any[] = potentialMoves(event.chessboard, piece, event.squareFrom);
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
      log("moveInputCanceled");
      event.chessboard.removeMarkers(MARKER_TYPE.dot);
      event.chessboard.removeMarkers(MARKER_TYPE.bevel);
      break;
    case INPUT_EVENT_TYPE.moveInputFinished:
      log("moveInputFinished");
      event.chessboard.removeMarkers(MARKER_TYPE.dot);
      event.chessboard.removeMarkers(MARKER_TYPE.bevel);
      trackCapture(event.squareTo);
      state.piecesMoved.push(event.squareTo);
      event.chessboard.view.setPieceGreyedOut(event.squareTo, true);
      break;
    case INPUT_EVENT_TYPE.movingOverSquare:
      break;
  }
}

const output: HTMLElement = document.getElementById("output") as HTMLElement;

function log(text: string): void {
  const logElement: HTMLDivElement = document.createElement("div");
  logElement.className = "log-entry";
  logElement.innerText = text;
  output.appendChild(logElement);
  output.scrollTop = output.scrollHeight;
}

export function potentialMoves(
  chessboard: any,
  piece: string,
  squareFrom: string
): any[] {
  if (state.piecesMoved.includes(squareFrom)) {
    return [];
  }
  const team = getTeam(piece);
  const coords: Coords = Position.squareToCoordinates(squareFrom);
  const retCoords = getPieceMoves(chessboard, piece, team, coords);
  return retCoords.map((c: Coords) => Position.coordinatesToSquare(c));
}

function getPieceMoves(
  chessboard: any,
  piece: string,
  team: Team,
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

// Initialize UI on load
updateTurnMessage();
updateMoveCount();
updateCapturedPieces();
log("Free Range Chess loaded! White moves first.");
