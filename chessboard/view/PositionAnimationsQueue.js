/**
 * Author and copyright: Stefan Haack (https://shaack.com)
 * Repository: https://github.com/shaack/cm-chessboard
 * License: MIT, see file 'LICENSE'
 */
import { FEN, Position } from "../model/Position.js";
import { Svg } from "../lib/Svg.js";
import { EXTENSION_POINT } from "../model/Extension.js";
import { Utils } from "../lib/Utils.js";

/*
 * Thanks to markosyan for the idea of the PromiseQueue
 * https://medium.com/@karenmarkosyan/how-to-manage-promises-into-dynamic-queue-with-vanilla-javascript-9d0d1f8d4df5
 */

export const ANIMATION_EVENT_TYPE = {
  start: "start",
  frame: "frame",
  end: "end",
};

export class PromiseQueue {
  constructor() {
    this.queue = [];
    this.workingOnPromise = false;
    this.stop = false;
  }

  async enqueue(promise) {
    return new Promise((resolve, reject) => {
      this.queue.push({
        promise,
        resolve,
        reject,
      });
      this.dequeue();
    });
  }

  dequeue() {
    if (this.workingOnPromise) {
      return;
    }
    if (this.stop) {
      this.queue = [];
      this.stop = false;
      return;
    }
    const entry = this.queue.shift();
    if (!entry) {
      return;
    }
    try {
      this.workingOnPromise = true;
      entry
        .promise()
        .then((value) => {
          this.workingOnPromise = false;
          entry.resolve(value);
          this.dequeue();
        })
        .catch((err) => {
          this.workingOnPromise = false;
          entry.reject(err);
          this.dequeue();
        });
    } catch (err) {
      this.workingOnPromise = false;
      entry.reject(err);
      this.dequeue();
    }
    return true;
  }

  destroy() {
    this.stop = true;
  }
}

const CHANGE_TYPE = {
  move: 0,
  appear: 1,
  disappear: 2,
};

export class PositionsAnimation {
  constructor(chessboard, fromPosition, toPosition, duration, callback) {
    // TODO(sjayakar): think about passing this around better
    this.chessboard = chessboard;
    if (fromPosition && toPosition) {
      this.animatedElements = this.createAnimation(
        fromPosition.squares,
        toPosition.squares
      );
      this.duration = duration;
      this.callback = callback;
      this.frameHandle = requestAnimationFrame(this.animationStep.bind(this));
    } else {
      console.error("fromPosition", fromPosition, "toPosition", toPosition);
    }
    chessboard.view.positionsAnimationTask = Utils.createTask();
    chessboard.view.chessboard.state.invokeExtensionPoints(
      EXTENSION_POINT.animation,
      {
        type: ANIMATION_EVENT_TYPE.start,
      }
    );
  }

  static seekChanges(fromSquares, toSquares) {
    const appearedList = [],
      disappearedList = [],
      changes = [];
    for (let i = 0; i < fromSquares.length; i++) {
      const previousSquare = fromSquares[i];
      const newSquare = toSquares[i];
      if (newSquare !== previousSquare) {
        if (newSquare) {
          appearedList.push({ piece: newSquare, index: i });
        }
        if (previousSquare) {
          disappearedList.push({ piece: previousSquare, index: i });
        }
      }
    }
    appearedList.forEach((appeared) => {
      // TODO(SJ): I'm not sure about this one LOL. So it teleports if
      // it exceeds 9.
      let shortestDistance = 9;
      let foundMoved = null;
      disappearedList.forEach((disappeared) => {
        if (appeared.piece === disappeared.piece) {
          const moveDistance = PositionsAnimation.squareDistance(
            appeared.index,
            disappeared.index
          );
          if (moveDistance < shortestDistance) {
            foundMoved = disappeared;
            shortestDistance = moveDistance;
          }
        }
      });
      if (foundMoved) {
        disappearedList.splice(disappearedList.indexOf(foundMoved), 1); // remove from disappearedList, because it is moved now
        changes.push({
          type: CHANGE_TYPE.move,
          piece: appeared.piece,
          atIndex: foundMoved.index,
          toIndex: appeared.index,
        });
      } else {
        changes.push({
          type: CHANGE_TYPE.appear,
          piece: appeared.piece,
          atIndex: appeared.index,
        });
      }
    });
    disappearedList.forEach((disappeared) => {
      changes.push({
        type: CHANGE_TYPE.disappear,
        piece: disappeared.piece,
        atIndex: disappeared.index,
      });
    });
    return changes;
  }

  createAnimation(fromSquares, toSquares) {
    const changes = PositionsAnimation.seekChanges(fromSquares, toSquares);
    const animatedElements = [];
    changes.forEach((change) => {
      const animatedItem = {
        type: change.type,
      };
      switch (change.type) {
        case CHANGE_TYPE.move:
          animatedItem.element = this.chessboard.view.getPieceElement(
            Position.indexToSquare(
              change.atIndex,
              this.chessboard.props.boardWidth
            )
          );
          animatedItem.element.parentNode.appendChild(animatedItem.element); // move element to top layer
          animatedItem.atPoint = this.chessboard.view.indexToPoint(
            change.atIndex
          );
          animatedItem.toPoint = this.chessboard.view.indexToPoint(
            change.toIndex
          );
          break;
        case CHANGE_TYPE.appear:
          animatedItem.element = this.chessboard.view.drawPieceOnSquare(
            Position.indexToSquare(
              change.atIndex,
              this.chessboard.props.boardWidth
            ),
            change.piece
          );
          animatedItem.element.style.opacity = 0;
          break;
        case CHANGE_TYPE.disappear:
          animatedItem.element = this.chessboard.view.getPieceElement(
            Position.indexToSquare(
              change.atIndex,
              this.chessboard.props.boardWidth
            )
          );
          break;
      }
      animatedElements.push(animatedItem);
    });
    return animatedElements;
  }

  animationStep(time) {
    if (!this.chessboard.view || !this.chessboard.state) {
      // board was destroyed
      return;
    }
    if (!this.startTime) {
      this.startTime = time;
    }
    const timeDiff = time - this.startTime;
    if (timeDiff <= this.duration) {
      this.frameHandle = requestAnimationFrame(this.animationStep.bind(this));
    } else {
      cancelAnimationFrame(this.frameHandle);
      this.animatedElements.forEach((animatedItem) => {
        if (animatedItem.type === CHANGE_TYPE.disappear) {
          Svg.removeElement(animatedItem.element);
        }
      });
      this.chessboard.view.positionsAnimationTask.resolve();
      this.chessboard.state.invokeExtensionPoints(EXTENSION_POINT.animation, {
        type: ANIMATION_EVENT_TYPE.end,
      });
      this.callback();
      return;
    }
    const t = Math.min(1, timeDiff / this.duration);
    let progress = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t; // easeInOut
    if (isNaN(progress) || progress > 0.99) {
      progress = 1;
    }
    this.animatedElements.forEach((animatedItem) => {
      if (animatedItem.element) {
        switch (animatedItem.type) {
          case CHANGE_TYPE.move:
            animatedItem.element.transform.baseVal.removeItem(0);
            const transform = this.chessboard.view.svg.createSVGTransform();
            transform.setTranslate(
              animatedItem.atPoint.x +
                (animatedItem.toPoint.x - animatedItem.atPoint.x) * progress,
              animatedItem.atPoint.y +
                (animatedItem.toPoint.y - animatedItem.atPoint.y) * progress
            );
            animatedItem.element.transform.baseVal.appendItem(transform);
            break;
          case CHANGE_TYPE.appear:
            animatedItem.element.style.opacity =
              Math.round(progress * 100) / 100;
            break;
          case CHANGE_TYPE.disappear:
            animatedItem.element.style.opacity =
              Math.round((1 - progress) * 100) / 100;
            break;
        }
      } else {
        console.warn("animatedItem has no element", animatedItem);
      }
    });
    this.chessboard.state.invokeExtensionPoints(EXTENSION_POINT.animation, {
      type: ANIMATION_EVENT_TYPE.frame,
      progress: progress,
    });
  }

  // TODO(sjayakar): rewrite
  static squareDistance(index1, index2) {
    const file1 = index1 % 8;
    const rank1 = Math.floor(index1 / 8);
    const file2 = index2 % 8;
    const rank2 = Math.floor(index2 / 8);
    return Math.max(Math.abs(rank2 - rank1), Math.abs(file2 - file1));
  }
}

export class PositionAnimationsQueue extends PromiseQueue {
  constructor(chessboard) {
    super();
    this.chessboard = chessboard;
  }

  async enqueuePositionChange(positionFrom, positionTo, animated) {
    // TODO(sjayakar) this sucks. used to be FEN. maybe need a new FEN
    if (
      JSON.stringify(positionFrom.squares) ===
      JSON.stringify(positionTo.squares)
    ) {
      return Promise.resolve();
    } else {
      return super.enqueue(
        () =>
          new Promise((resolve) => {
            let duration = animated
              ? this.chessboard.props.style.animationDuration
              : 0;
            if (this.queue.length > 0) {
              duration = duration / (1 + Math.pow(this.queue.length / 5, 2));
            }
            new PositionsAnimation(
              this.chessboard,
              positionFrom,
              positionTo,
              animated ? duration : 0,
              () => {
                if (this.chessboard.view) {
                  // if destroyed, no view anymore
                  this.chessboard.view.redrawPieces(positionTo.squares);
                }
                resolve();
              }
            );
          })
      );
    }
  }

  async enqueueTurnBoard(position, color, animated) {
    return super.enqueue(
      () =>
        new Promise((resolve) => {
          const emptyPosition = new Position(FEN.empty);
          let duration = animated
            ? this.chessboard.props.style.animationDuration
            : 0;
          if (this.queue.length > 0) {
            duration = duration / (1 + Math.pow(this.queue.length / 5, 2));
          }
          new PositionsAnimation(
            this.chessboard,
            position,
            emptyPosition,
            animated ? duration : 0,
            () => {
              this.chessboard.state.orientation = color;
              this.chessboard.view.redrawBoard();
              this.chessboard.view.redrawPieces(emptyPosition.squares);
              new PositionsAnimation(
                this.chessboard,
                emptyPosition,
                position,
                animated ? duration : 0,
                () => {
                  this.chessboard.view.redrawPieces(position.squares);
                  resolve();
                }
              );
            }
          );
        })
    );
  }
}
