"""
Monte Carlo Tree Search with neural network guidance for Free Range Chess.

Key design decisions for this variant:
- A "turn" consists of MULTIPLE actions (move pieces + end_turn)
- Each MCTS node represents a mid-turn state (some pieces already moved)
- Actions are individual piece moves OR end_turn
- The tree search explores sequences of moves within a turn

This is closer to AlphaZero's approach adapted for multi-action turns:
- At each node, the NN evaluates the position
- PUCT selects which action to explore
- When end_turn is selected, the opponent responds
- Leaf evaluation uses the neural network value head
"""

import math
import numpy as np
from typing import Dict, List, Optional, Tuple
from game_engine import GameState, Team, Position, PieceType, PIECE_VALUES
from neural_network import (
    ChessNet, encode_action, decode_action,
    NUM_ACTIONS, END_TURN_ACTION, BOARD_W, BOARD_H
)


class MCTSNode:
    """A node in the MCTS tree."""
    __slots__ = ['state', 'parent', 'action', 'children', 'visit_count',
                 'value_sum', 'prior', 'is_expanded']

    def __init__(self, state: GameState, parent: Optional['MCTSNode'] = None,
                 action: Optional[int] = None, prior: float = 0.0):
        self.state = state
        self.parent = parent
        self.action = action  # action that led to this node
        self.children: Dict[int, 'MCTSNode'] = {}
        self.visit_count = 0
        self.value_sum = 0.0
        self.prior = prior
        self.is_expanded = False

    @property
    def value(self) -> float:
        if self.visit_count == 0:
            return 0.0
        return self.value_sum / self.visit_count

    def ucb_score(self, c_puct: float = 1.5) -> float:
        """Upper Confidence Bound score for selection."""
        if self.parent is None:
            return 0.0
        exploration = c_puct * self.prior * math.sqrt(self.parent.visit_count) / (1 + self.visit_count)
        return self.value + exploration


def get_legal_action_mask(state: GameState) -> np.ndarray:
    """Create a binary mask over all actions indicating which are legal."""
    mask = np.zeros(NUM_ACTIONS, dtype=np.float32)

    # Individual piece moves
    actions = state.get_all_legal_actions()
    for from_pos, to_pos in actions:
        idx = encode_action(from_pos, to_pos)
        mask[idx] = 1.0

    # End turn is legal if at least one piece has moved
    if len(state.pieces_moved) > 0:
        mask[END_TURN_ACTION] = 1.0

    return mask


def apply_action(state: GameState, action: int) -> GameState:
    """Apply an action to a game state and return the new state.
    
    For end_turn: switches turn and lets opponent play a full random turn
    (during MCTS, opponent policy comes from the network on the next expansion).
    """
    new_state = state.clone()

    if action == END_TURN_ACTION:
        new_state.switch_turn()
    else:
        from_pos, to_pos = decode_action(action)
        if from_pos is not None and to_pos is not None:
            new_state.make_move(from_pos, to_pos)

    return new_state


class MCTS:
    """Monte Carlo Tree Search with neural network guidance."""

    def __init__(self, network: ChessNet, c_puct: float = 1.5,
                 num_simulations: int = 100, dirichlet_alpha: float = 0.3,
                 dirichlet_epsilon: float = 0.25, temperature: float = 1.0):
        self.network = network
        self.c_puct = c_puct
        self.num_simulations = num_simulations
        self.dirichlet_alpha = dirichlet_alpha
        self.dirichlet_epsilon = dirichlet_epsilon
        self.temperature = temperature

    def search(self, state: GameState) -> Tuple[np.ndarray, float]:
        """Run MCTS from the given state.
        
        Returns:
            action_probs: probability distribution over actions
            root_value: estimated value of the root state
        """
        root = MCTSNode(state)
        self._expand(root, add_noise=True)

        for _ in range(self.num_simulations):
            node = root
            search_path = [node]

            # SELECT: traverse tree using UCB
            while node.is_expanded and not node.state.is_game_over():
                action, node = self._select_child(node)
                search_path.append(node)

            # EVALUATE leaf
            if node.state.is_game_over():
                # Terminal node
                value = self._terminal_value(node.state, root.state.current_turn)
            else:
                # Expand and evaluate with neural network
                value = self._expand(node)
                # Value is from the perspective of the node's current player
                # We need it from root's perspective
                if node.state.current_turn != root.state.current_turn:
                    value = -value

            # BACKUP
            self._backup(search_path, value, root.state.current_turn)

        # Build action probability distribution from visit counts
        action_probs = np.zeros(NUM_ACTIONS, dtype=np.float32)
        for action, child in root.children.items():
            action_probs[action] = child.visit_count

        # Apply temperature
        if self.temperature == 0:
            # Greedy
            best = np.argmax(action_probs)
            action_probs = np.zeros(NUM_ACTIONS, dtype=np.float32)
            action_probs[best] = 1.0
        else:
            if action_probs.sum() > 0:
                # Temperature scaling
                action_probs = action_probs ** (1.0 / self.temperature)
                action_probs /= action_probs.sum()

        return action_probs, root.value

    def _expand(self, node: MCTSNode, add_noise: bool = False) -> float:
        """Expand a leaf node using the neural network.
        
        Returns the value estimate for this node.
        """
        state = node.state
        
        if state.is_game_over():
            node.is_expanded = True
            return self._terminal_value(state, state.current_turn)

        # Get NN prediction
        state_np = state.to_numpy()
        policy, value = self.network.predict(state_np)

        # Mask illegal actions
        legal_mask = get_legal_action_mask(state)

        # If no legal actions at all (shouldn't happen if game isn't over,
        # but handle gracefully)
        if legal_mask.sum() == 0:
            node.is_expanded = True
            return value

        # Apply mask and renormalize
        policy = policy * legal_mask
        policy_sum = policy.sum()
        if policy_sum > 0:
            policy /= policy_sum
        else:
            # Uniform over legal actions
            policy = legal_mask / legal_mask.sum()

        # Add Dirichlet noise at root for exploration
        if add_noise:
            noise = np.random.dirichlet([self.dirichlet_alpha] * int(legal_mask.sum()))
            legal_indices = np.where(legal_mask > 0)[0]
            for i, idx in enumerate(legal_indices):
                policy[idx] = (1 - self.dirichlet_epsilon) * policy[idx] +                               self.dirichlet_epsilon * noise[i]

        # Create children for all legal actions
        for action_idx in np.where(legal_mask > 0)[0]:
            action = int(action_idx)
            child_state = apply_action(state, action)
            child = MCTSNode(child_state, parent=node, action=action,
                           prior=policy[action])
            node.children[action] = child

        node.is_expanded = True
        return value

    def _select_child(self, node: MCTSNode) -> Tuple[int, MCTSNode]:
        """Select the child with highest UCB score."""
        best_score = -float('inf')
        best_action = -1
        best_child = None

        for action, child in node.children.items():
            score = child.ucb_score(self.c_puct)
            if score > best_score:
                best_score = score
                best_action = action
                best_child = child

        return best_action, best_child

    def _backup(self, search_path: List[MCTSNode], value: float,
                root_turn: Team):
        """Propagate value back up the search path."""
        for node in reversed(search_path):
            # Value is from root's perspective
            # Flip for nodes where it's the opponent's turn
            if node.state.current_turn == root_turn:
                node.value_sum += value
            else:
                node.value_sum -= value
            node.visit_count += 1

    def _terminal_value(self, state: GameState, perspective: Team) -> float:
        """Get value of a terminal state from perspective's viewpoint."""
        if state.winner == perspective:
            return 1.0
        elif state.winner == perspective.opposite():
            return -1.0
        return 0.0  # draw


class MCTSPlayer:
    """Plays a complete turn using MCTS for each action decision."""

    def __init__(self, network: ChessNet, num_simulations: int = 100,
                 c_puct: float = 1.5, temperature: float = 1.0):
        self.network = network
        self.num_simulations = num_simulations
        self.c_puct = c_puct
        self.temperature = temperature

    def play_turn(self, state: GameState, collect_data: bool = False) -> List[dict]:
        """Play a complete turn (multiple actions until end_turn).
        
        Args:
            state: Current game state (will be modified in place)
            collect_data: If True, collect training data
            
        Returns:
            List of training data dicts if collect_data, else empty list
        """
        training_data = []
        max_actions = 50  # safety limit

        for _ in range(max_actions):
            if state.is_game_over():
                break

            mcts = MCTS(
                self.network,
                c_puct=self.c_puct,
                num_simulations=self.num_simulations,
                temperature=self.temperature,
            )

            action_probs, value = mcts.search(state)

            if collect_data:
                training_data.append({
                    'state': state.to_numpy(),
                    'policy': action_probs,
                    'turn': state.current_turn,
                })

            # Sample action from distribution
            if self.temperature == 0:
                action = int(np.argmax(action_probs))
            else:
                action = int(np.random.choice(NUM_ACTIONS, p=action_probs))

            # Apply action
            if action == END_TURN_ACTION:
                state.switch_turn()
                break
            else:
                from_pos, to_pos = decode_action(action)
                if from_pos is not None and to_pos is not None:
                    if not state.make_move(from_pos, to_pos):
                        # Illegal move selected despite masking — force end turn
                        if len(state.pieces_moved) > 0:
                            state.switch_turn()
                        break

        # If we hit max_actions without ending turn, force it
        if not state.is_game_over() and len(state.pieces_moved) > 0:
            if state.current_turn == state.current_turn:  # still same turn
                state.switch_turn()

        return training_data
