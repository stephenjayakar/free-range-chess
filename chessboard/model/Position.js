/**
 * Author and copyright: Stefan Haack (https://shaack.com)
 * Repository: https://github.com/shaack/cm-chessboard
 * License: MIT, see file 'LICENSE'
 */
export const FEN = {
  start: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  empty: "8/8/8/8/8/8/8/8",
};

export class Position {
  constructor(fen = FEN.empty, boardWidth, boardHeight) {
    this.squares = new Array(boardWidth * boardHeight).fill(null);
    this.setFen(fen);
    this.boardWidth = boardWidth;
    this.boardHeight = boardHeight;
  }

  // TODO(sjayakar): this doesn't work
  setFen(fen = FEN.empty) {
    const parts = fen.replace(/^\s*/, "").replace(/\s*$/, "").split(/\/|\s/);
    for (let part = 0; part < 8; part++) {
      const row = parts[7 - part].replace(/\d/g, (str) => {
        const numSpaces = parseInt(str);
        let ret = "";
        for (let i = 0; i < numSpaces; i++) {
          ret += "-";
        }
        return ret;
      });
      for (let c = 0; c < 8; c++) {
        const char = row.substring(c, c + 1);
        let piece = null;
        if (char !== "-") {
          if (char.toUpperCase() === char) {
            piece = `w${char.toLowerCase()}`;
          } else {
            piece = `b${char}`;
          }
        }
        this.squares[part * 8 + c] = piece;
      }
    }
  }

  // TODO(sjayakar): this doesn't work
  getFen() {
    let parts = new Array(8).fill("");
    for (let part = 0; part < 8; part++) {
      let spaceCounter = 0;
      for (let i = 0; i < 8; i++) {
        const piece = this.squares[part * 8 + i];
        if (!piece) {
          spaceCounter++;
        } else {
          if (spaceCounter > 0) {
            parts[7 - part] += spaceCounter;
            spaceCounter = 0;
          }
          const color = piece.substring(0, 1);
          const name = piece.substring(1, 2);
          if (color === "w") {
            parts[7 - part] += name.toUpperCase();
          } else {
            parts[7 - part] += name;
          }
        }
      }
      if (spaceCounter > 0) {
        parts[7 - part] += spaceCounter;
        spaceCounter = 0;
      }
    }
    return parts.join("/");
  }

  getPieces(sortBy = ["k", "q", "r", "b", "n", "p"], boardWidth) {
    const pieces = [];
    const sort = (a, b) => {
      return sortBy.indexOf(a.name) - sortBy.indexOf(b.name);
    };
    for (let i = 0; i < 64; i++) {
      const piece = this.squares[i];
      if (piece) {
        pieces.push({
          name: piece.charAt(1),
          color: piece.charAt(0),
          position: Position.indexToSquare(i, boardWidth),
        });
      }
    }
    if (sortBy) {
      pieces.sort(sort);
    }
    return pieces;
  }

  movePiece(squareFrom, squareTo, boardWidth) {
    if (!this.squares[Position.squareToIndex(squareFrom, boardWidth)]) {
      console.warn("no piece on", squareFrom);
      return;
    }
    this.squares[Position.squareToIndex(squareTo, boardWidth)] =
      this.squares[Position.squareToIndex(squareFrom, boardWidth)];
    this.squares[Position.squareToIndex(squareFrom, boardWidth)] = null;
  }

  setPiece(square, piece, boardWidth) {
    this.squares[Position.squareToIndex(square, boardWidth)] = piece;
  }

  getPiece(square, boardWidth) {
    return this.squares[Position.squareToIndex(square, boardWidth)];
  }

  static squareToIndex(square, boardWidth) {
    const coordinates = Position.squareToCoordinates(square);
    return coordinates[0] + coordinates[1] * boardWidth;
  }

  static indexToSquare(index, boardWidth) {
    return this.coordinatesToSquare([Math.floor(index % boardWidth), Math.floor(index / boardWidth)]);
  }

  // This is chess square ("a1") -> 0, 0
  // I've converted the notation to `"X,Y"` where X, Y are 0 -> boarddim - 1
  static squareToCoordinates(square) {
    const [file, rank] = square.split(',');
    return [parseInt(file), parseInt(rank)];
  }

  static coordinatesToSquare(coordinates) {
    return coordinates[0].toString() + ',' + coordinates[1].toString()
  }

  clone() {
    const cloned = new Position(FEN.empty, this.boardWidth, this.boardHeight);
    cloned.squares = this.squares.slice(0);
    return cloned;
  }
}
