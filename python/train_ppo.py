import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv, VecMonitor
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.logger import configure
import torch
import numpy as np
from gym_env import FreeRangeChessEnv
import os
from datetime import datetime


def make_env(opponent='random', rank=0):
    def _init():
        env = FreeRangeChessEnv(opponent=opponent)
        return env
    return _init


def train_ppo(
    total_timesteps=1_000_000,
    n_envs=8,
    opponent='random',
    log_dir='./logs',
    save_dir='./models',
    learning_rate=3e-4,
    batch_size=256,
    n_steps=2048,
    n_epochs=10,
):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"ppo_chess_{opponent}_{timestamp}"
    
    model_dir = os.path.join(save_dir, run_name)
    log_path = os.path.join(log_dir, run_name)
    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(log_path, exist_ok=True)
    
    print(f"Creating {n_envs} parallel environments...")
    env = make_vec_env(
        lambda: FreeRangeChessEnv(opponent=opponent),
        n_envs=n_envs,
        vec_env_cls=SubprocVecEnv
    )
    env = VecMonitor(env, log_path)
    
    print("Initializing PPO agent...")
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=learning_rate,
        n_steps=n_steps,
        batch_size=batch_size,
        n_epochs=n_epochs,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        vf_coef=0.5,
        max_grad_norm=0.5,
        verbose=1,
        tensorboard_log=log_path,
        device='auto'
    )
    
    checkpoint_callback = CheckpointCallback(
        save_freq=10000,
        save_path=model_dir,
        name_prefix='ppo_chess'
    )
    
    eval_env = FreeRangeChessEnv(opponent=opponent)
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=model_dir,
        log_path=log_path,
        eval_freq=5000,
        n_eval_episodes=10,
        deterministic=True
    )
    
    print(f"Starting training for {total_timesteps} timesteps...")
    print(f"Logs: {log_path}")
    print(f"Models: {model_dir}")
    print(f"View progress with: tensorboard --logdir {log_path}")
    
    model.learn(
        total_timesteps=total_timesteps,
        callback=[checkpoint_callback, eval_callback],
        progress_bar=True
    )
    
    final_model_path = os.path.join(model_dir, 'final_model')
    model.save(final_model_path)
    print(f"Training complete! Final model saved to: {final_model_path}")
    
    env.close()
    eval_env.close()
    
    return model, final_model_path


def evaluate_model(model_path, n_episodes=100, opponent='random', render=False):
    env = FreeRangeChessEnv(opponent=opponent)
    model = PPO.load(model_path)
    
    wins = 0
    losses = 0
    draws = 0
    total_rewards = []
    
    for episode in range(n_episodes):
        obs, info = env.reset()
        episode_reward = 0
        done = False
        
        while not done:
            action, _states = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            episode_reward += reward
            done = terminated or truncated
            
            if render and episode < 5:
                env.render()
        
        total_rewards.append(episode_reward)
        
        if info.get('winner') == 'w':
            wins += 1
        elif info.get('winner') == 'b':
            losses += 1
        else:
            draws += 1
        
        if (episode + 1) % 10 == 0:
            print(f"Episode {episode + 1}/{n_episodes}: W={wins} L={losses} D={draws}, Avg Reward={np.mean(total_rewards):.2f}")
    
    env.close()
    
    print(f"\n=== Evaluation Results ===")
    print(f"Total Episodes: {n_episodes}")
    print(f"Wins: {wins} ({wins/n_episodes*100:.1f}%)")
    print(f"Losses: {losses} ({losses/n_episodes*100:.1f}%)")
    print(f"Draws: {draws} ({draws/n_episodes*100:.1f}%)")
    print(f"Average Reward: {np.mean(total_rewards):.2f}")
    print(f"Std Reward: {np.std(total_rewards):.2f}")
    
    return {
        'wins': wins,
        'losses': losses,
        'draws': draws,
        'avg_reward': np.mean(total_rewards),
        'std_reward': np.std(total_rewards)
    }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Train PPO agent for Free Range Chess')
    parser.add_argument('--mode', type=str, default='train', choices=['train', 'eval', 'play'],
                        help='Mode: train, eval, or play')
    parser.add_argument('--timesteps', type=int, default=1_000_000,
                        help='Total training timesteps')
    parser.add_argument('--n-envs', type=int, default=8,
                        help='Number of parallel environments')
    parser.add_argument('--opponent', type=str, default='random', choices=['random', 'greedy'],
                        help='Opponent type')
    parser.add_argument('--model-path', type=str, default=None,
                        help='Path to model for evaluation or play')
    parser.add_argument('--n-episodes', type=int, default=100,
                        help='Number of episodes for evaluation')
    
    args = parser.parse_args()
    
    if args.mode == 'train':
        train_ppo(
            total_timesteps=args.timesteps,
            n_envs=args.n_envs,
            opponent=args.opponent
        )
    elif args.mode == 'eval':
        if not args.model_path:
            print("Error: --model-path required for evaluation")
            exit(1)
        evaluate_model(args.model_path, n_episodes=args.n_episodes, opponent=args.opponent)
    elif args.mode == 'play':
        if not args.model_path:
            print("Error: --model-path required for play mode")
            exit(1)
        evaluate_model(args.model_path, n_episodes=1, opponent=args.opponent, render=True)
