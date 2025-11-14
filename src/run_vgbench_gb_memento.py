import argparse, sys
from pathlib import Path

def import_modules():
    from src.emulators.gba.interface import GBAInterface
    from src.llm.memento_agent import MementoGameBoyVGAgent, MementoConfig
    from src.vgbench_evaluator import GBEvaluator
    from src.consts import ROM_FILE_MAP
    return GBAInterface, MementoGameBoyVGAgent, GBEvaluator, ROM_FILE_MAP

async def main():
    GBAInterface, MementoGameBoyVGAgent, GBEvaluator, ROM_FILE_MAP = import_modules()
    parser = argparse.ArgumentParser(description="Run VG-Bench Lite (GBA) with Memento agent.")
    parser.add_argument("--rom", type=str, required=True, help="Game ROM key (per ROM_FILE_MAP).")
    parser.add_argument("--model", type=str, required=True, help="LLM model")
    parser.add_argument("--api_key", type=str, required=True, help="API key")
    parser.add_argument("--api_base", type=str, default=None, help="API base (for Ollama/vLLM)")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max_tokens", type=int, default=1024)
    parser.add_argument("--skip_frames", type=int, default=4)
    parser.add_argument("--action_frames", type=int, default=8)
    parser.add_argument("--fake_actions", action="store_true")
    parser.add_argument("--checkpoints", type=str, default=None, help="Path to checkpoints YAML")
    parser.add_argument("--threshold", type=float, default=0.95)
    parser.add_argument("--lite", action="store_true", help="Use Lite mode (pause while thinking)")
    parser.add_argument("--log_dir", type=str, default="./logs")
    parser.add_argument("--memento_top_k", type=int, default=6)
    parser.add_argument("--memento_max_cases", type=int, default=15000)
    args = parser.parse_args()

    rom_path = ROM_FILE_MAP[args.rom]

    game = GBAInterface(rom_path)
    await game.initialize()

    mcfg = MementoConfig(top_k=args.memento_top_k, max_cases=args.memento_max_cases)
    agent = MementoGameBoyVGAgent(
        model=args.model,
        api_key=args.api_key,
        game_type="gba",
        headless=True,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        realtime=not args.lite,
        log_dir=Path(args.log_dir),
        api_base=args.api_base,
        memento=mcfg
    )

    evaluator = GBEvaluator(
        game=game,
        skip_frames=args.skip_frames,
        action_frames=args.action_frames,
        fake_actions=args.fake_actions,
        checkpoints=args.checkpoints,
        threshold=args.threshold,
    )
    try:
        metrics = await evaluator.run_episode(agent, args.lite)
    except KeyboardInterrupt:
        print("Interrupted")
    finally:
        print("Done.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())