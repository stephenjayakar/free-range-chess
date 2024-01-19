/**
 * Author and copyright: Stefan Haack (https://shaack.com)
 * Repository: https://github.com/shaack/cm-chessboard
 * License: MIT, see file 'LICENSE'
 */
import { Position, FEN } from "./Position.js";

export class ChessboardState {
  constructor(boardWidth, boardHeight) {
    this.position = new Position(FEN.empty, boardWidth, boardHeight);
    this.orientation = undefined;
    this.inputWhiteEnabled = false;
    this.inputBlackEnabled = false;
    this.moveInputCallback = null;
    this.extensionPoints = {};
    this.moveInputProcess = Promise.resolve();
  }

  inputEnabled() {
    return this.inputWhiteEnabled || this.inputBlackEnabled;
  }

  invokeExtensionPoints(name, data = {}) {
    const extensionPoints = this.extensionPoints[name];
    const dataCloned = Object.assign({}, data);
    dataCloned.extensionPoint = name;
    let returnValue = true;
    if (extensionPoints) {
      for (const extensionPoint of extensionPoints) {
        if (extensionPoint(dataCloned) === false) {
          returnValue = false;
        }
      }
    }
    return returnValue;
  }
}
