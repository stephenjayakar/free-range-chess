from gym_env import FreeRangeChessEnv
import numpy as np


def test_basic_game():
    print("Testing Free Range Chess Environment...")
    
    env = FreeRangeChessEnv(opponent='random')
    obs, info = env.reset()
    
    print(f"Observation shape: {obs.shape}")
    print(f"Action space: {env.action_space}")
    print(f"Initial info: {info}")
    
    print("\nInitial board:")
    env.render()
    
    print("\nPlaying a few random moves...")
    for step in range(10):
        legal_actions = env.game_state.get_all_legal_actions()
        if not legal_actions:
            action = env.action_space.n - 1
        else:
            from_pos, to_pos = legal_actions[0]
            action = env._encode_action(from_pos, to_pos)
        
        obs, reward, terminated, truncated, info = env.step(action)
        
        print(f"\nStep {step + 1}:")
        print(f"  Reward: {reward:.3f}")
        print(f"  Info: {info}")
        
        if terminated or truncated:
            print(f"  Game ended! Winner: {info.get('winner', 'None')}")
            break
    
    env.render()
    env.close()
    print("\nTest complete!")


if __name__ == '__main__':
    test_basic_game()
