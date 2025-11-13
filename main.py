#!/usr/bin/env python3
import argparse
import yaml
import asyncio
import os
import sys
import webbrowser
import signal
import time
from typing import Optional, Dict, Any
from PIL import Image
from pathlib import Path
from src.llm.prompts import DOS_PROMPT
from src.utils import hash_image

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not installed. Environment variables must be set manually.")

# Global variables for clean shutdown
game_instance = None

def parse_args():
    parser = argparse.ArgumentParser(description="Game Emulation and Evaluation with LLMs")
    
    # VideoGameBench emulator attributes
    parser.add_argument("--emulator", choices=["dos", "gba"],
                       help="Which emulator to use ('dos' or 'gba'). Overwritten if config is specified.")
    parser.add_argument("--game", type=str, 
                       help="Name or URL of a js-dos game bundle to run or GBA game to load")
    parser.add_argument("--lite", action="store_true", 
                       help="Lite-mode, so not real time. Game pauses between actions.")
    parser.add_argument("--max-steps", type=int, default=15000, 
                       help="Maximum number of steps to run")

    # Common arguments
    parser.add_argument("--enable-ui", action="store_true", 
                       help="Enable the UI for the agent")
    parser.add_argument("--threshold", type=float,  
                       help="Threshold for checkpoint progress")
    parser.add_argument("--model", type=str, default="gpt-4o",
                       help="The LLM model to use (for LiteLLM names). Default is gpt-4o")
    parser.add_argument("--headless", action="store_true", 
                       help="Run the emulator without visual display")
    parser.add_argument("--config-folder", type=str, default="configs/",
                       help="Path to the config folder")
    parser.add_argument("--max-tokens", type=int, default=1024, 
                       help="The maximum number of tokens to generate")
    parser.add_argument("--temperature", type=float, default=0.7, 
                       help="The temperature for LLM generation")
    parser.add_argument("--num-screenshots-per-action", type=int, default=0, 
                       help="Number of screenshots to take per action to add in context. 0 has default behavior described in the paper.")
    parser.add_argument("--max-context-size", type=int, default=20, 
                       help="Maximum number of messages in the context window. Default is 20.")

    # LiteLLM + Ollama args
    parser.add_argument("--api-key", type=str, 
                       help="API key for the chosen LLM provider")
    parser.add_argument("--api-base", type=str, default=None,
                       help="API base URL for Ollama or other providers")

    # DOS-specific arguments
    parser.add_argument("--port", type=int, default=8000, 
                       help="Port to run the server on (DOS only)")
    parser.add_argument("--task", type=str, default="",
                       help="The task for the agent to execute (DOS only)")
    parser.add_argument("--url", type=str, default="", 
                       help="The URL to start from (DOS only)")
    parser.add_argument("--website-only", action="store_true", 
                       help="Just open the website without agent interaction (DOS only)")
    
    # GBA-specific arguments
    parser.add_argument("--step-delay", type=float, default=0.0, 
                       help="Delay between steps in seconds (GBA only)")
    parser.add_argument("--skip-frames", type=int, default=1, 
                       help="Number of frames to skip per step (GBA only)")
    parser.add_argument("--fake-actions", action="store_true", 
                       help="Use random actions instead of calling the LLM (GBA only)")
    parser.add_argument("--history-tokens", type=int, default=4000, 
                       help="Maximum tokens in conversation history (GBA only)")
    parser.add_argument("--action-frames", type=int, default=15,
                       help="Number of frames to run each action for (GBA only)")
    
    #Add checkpoints flag
    parser.add_argument("--checkpoints", type=str, default=None,
                    help="Path to a directory of PNG checkpoint screenshots to use for progress detection")

    return parser.parse_args()

def load_game_config(args):
    """Load game configuration and prompt from the appropriate config folder."""
    # DOS-specific game defaults
    args.press_key_delay = 100

    if not args.game or not args.config_folder:
        print(f"No game or config folder specified. Exiting.")
        return args

    # Determine config path based on emulator type
    config_base = Path(args.config_folder)
    config_dir = config_base / args.game
    config_file = config_dir / "config.yaml"
    prompt_file = config_dir / "prompt.txt"
    # Try loading checkpoints if they exist
    checkpoint_dir = config_dir / "checkpoints"
    # if os.path.exists(checkpoint_dir):
    #     try:
    #         # Get all image files and sort numerically
    #         checkpoint_files = sorted(
    #             [f for f in checkpoint_dir.glob("*.png")],
    #             key=lambda x: int(x.stem)  # Use stem to get filename without extension
    #         )
    #         print("Checkpoint files:", checkpoint_files)
    #         if checkpoint_files:
    #             checkpoint_hashes = []
    #             for checkpoint in checkpoint_files:
    #                 img = Image.open(checkpoint)
    #                 hash_str = hash_image(img)
    #                 checkpoint_hashes.append(hash_str)
    #             args.checkpoints = checkpoint_hashes
    #         else:
    #             args.checkpoints = None
    #     except:
    #         args.checkpoints = None
    # else:
    #     args.checkpoints = None
    
    # If --checkpoints points to a directory, load and hash all PNGs there
    if args.checkpoints and os.path.isdir(args.checkpoints):
        manual_dir = Path(args.checkpoints)
        # sort using digits anywhere in the filename: screenshot_65.png, screesnhot_77.png, etc.
        def num_key(p):
            digits = "".join(ch for ch in p.stem if ch.isdigit())
            return int(digits) if digits else 0
        pngs = sorted(manual_dir.glob("*.png"), key=num_key)

        if not pngs:
            print(f"No PNGs found in {manual_dir}")
        else:
            checkpoint_hashes = []
            for p in pngs:
                img = Image.open(p)
                checkpoint_hashes.append(hash_image(img))
            args.checkpoints = checkpoint_hashes
            print(f"Loaded {len(checkpoint_hashes)} manual checkpoints from {manual_dir}")


    print(f"Loading config from {config_file}")
    try:
        # Load YAML config
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            
        # Load prompt if it exists
        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                config['task_prompt'] = f.read().strip()
        else:
            print(f"Warning: No prompt file found at {prompt_file}")
            config['task_prompt'] = ""
            
        # Update args with config values, preserving command-line overrides
        for key, value in config.items():
            # Only update if not explicitly set in command line
            if not getattr(args, key, None):
                setattr(args, key, value)
                
        # Special handling for DOS games
        if args.emulator == "dos":
            html_file = config_dir / "game.html"
            if html_file.exists():
                with open(html_file, 'r') as f:
                    args.custom_html = f.read()
            else:
                args.custom_html = None
                
    except FileNotFoundError:
        print(f"No config file found at {config_file}")
        print(f"Using default configuration for {args.game}")
    except Exception as e:
        print(f"Error loading config: {e}")
        
    return args

def handle_shutdown_signal(sig, frame):
    """Handle shutdown signals for clean exit."""
    print("\nShutdown signal received. Cleaning up...")
        
    # Close any active screen recorder
    if hasattr(game_instance, 'monitor') and game_instance.monitor:
        if game_instance.monitor.screen_recorder:
            game_instance.monitor.screen_recorder.close()
    
    sys.exit(0)

async def videogamebench_start():
    """Main async entry point."""
    args = parse_args()
    args = load_game_config(args)

    if args.model == "gpt-4o":
        args.model = "gpt-4o"
    elif args.model == "claude-3.7":
        args.model = "claude-3-7-sonnet-20250219"
    elif args.model == "gemini-2.0-flash":
        args.model = "gemini/gemini-2.0-flash"
    elif args.model == "llama4":
        args.model = "together_ai/meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"

    if args.emulator == "dos":
        from src.run_vgbench_dos import run_dos_emulator
        await run_dos_emulator(args)
    elif args.emulator == "gba":
        from src.run_vgbench_gb import run_gba_emulator
        await run_gba_emulator(args)
    else:
        print("No emulator specified. Exiting.")
        sys.exit(1)

if __name__ == "__main__":
    # Register signal handlers for clean shutdown
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    
    # Run the main function
    try:
        asyncio.run(videogamebench_start())
    except KeyboardInterrupt:
        print("\nProgram interrupted. Cleaning up...")
