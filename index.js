import { INPUT_EVENT_TYPE, Chessboard } from "../src/Chessboard.js"
import { FEN } from "../src/model/Position.js"
import { Markers } from "../src/extensions/markers/Markers.js"

window.board = new Chessboard(document.getElementById("board"), {
  position: FEN.start,
  assetsUrl: "../assets/",
  style: { pieces: { file: "pieces/staunty.svg" } },
  extensions: [{ class: Markers }]
})

window.board.enableMoveInput(inputHandler)

function inputHandler(event) {
  console.log(event)
  switch (event.type) {
    case INPUT_EVENT_TYPE.moveInputStarted:
      log(`moveInputStarted: ${event.squareFrom}`)
      return true // false cancels move
    case INPUT_EVENT_TYPE.validateMoveInput:
      log(`validateMoveInput: ${event.squareFrom}-${event.squareTo}`)
      return true // false cancels move
    case INPUT_EVENT_TYPE.moveInputCanceled:
      log(`moveInputCanceled`)
      break
    case INPUT_EVENT_TYPE.moveInputFinished:
      log(`moveInputFinished`)
      break
    case INPUT_EVENT_TYPE.movingOverSquare:
      log(`movingOverSquare: ${event.squareTo}`)
      break
  }
}

const output = document.getElementById("output")

function log(text) {
  const log = document.createElement("div")
  log.innerText = text
  output.appendChild(log)
}
