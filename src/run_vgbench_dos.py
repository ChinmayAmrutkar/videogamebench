# src/run_vgbench_dos.py
import os
import sys
import asyncio
from typing import Optional
from src.llm.prompts import DOS_PROMPT


def import_dos_modules():
    """
    Import DOS pipeline pieces and return them in the order expected by the caller:
      AgentClass, GAME_URL_MAP, DOSGameServer, DOSEvaluator, DOSGameInterface
    AgentClass will be MementoDOSVGAgent if present, else WebBrowsingVGAgent.
    """
    # Prefer the Memento-enabled DOS agent if you've added it
    try:
        from src.llm.memento_dos_agent import MementoDOSVGAgent as AgentClass  # noqa: F401
        has_memento = True
    except Exception:
        from src.llm.vgagent import WebBrowsingVGAgent as AgentClass  # noqa: F401
        has_memento = False

    # GAME_URL_MAP may live in consts or the website_server module depending on your repo
    GAME_URL_MAP = None
    try:
        from src.consts import GAME_URL_MAP as _URLS  # type: ignore
        GAME_URL_MAP = _URLS
    except Exception:
        pass
    if GAME_URL_MAP is None:
        from src.emulators.dos.website_server import GAME_URL_MAP  # type: ignore

    from src.emulators.dos.website_server import DOSGameServer
    from src.emulators.dos.interface import DOSGameInterface
    from src.vgbench_evaluator import DOSEvaluator

    return AgentClass, GAME_URL_MAP, DOSGameServer, DOSEvaluator, DOSGameInterface


async def run_dos_emulator(args):
    """Run the DOS emulator with the given arguments."""
    # Import required modules (returns AgentClass, not a specific class name)
    AgentClass, GAME_URL_MAP, DOSGameServer, DOSEvaluator, DOSGameInterface = import_dos_modules()

    # CLI / argparsing inputs
    task: str = args.task
    url: Optional[str] = args.url
    model: Optional[str] = args.model
    api_key: Optional[str] = args.api_key

    headless: bool = args.headless
    temperature: float = args.temperature
    max_tokens: int = args.max_tokens
    dos_name: Optional[str] = args.game
    website_only: bool = args.website_only

    if not model:
        print("No model provided, using default model: gpt-4o")
        model = "gpt-4o"

    # Start a local server for DOS games if a game is provided
    server = None
    if dos_name:
        server = DOSGameServer(args.port, lite=args.lite)

        # Use custom HTML if provided, otherwise fall back to GAME_URL_MAP
        if getattr(args, "custom_html", None):
            url = server.start(dos_name, args.custom_html)
        elif dos_name in GAME_URL_MAP:
            dos_game_cfg = GAME_URL_MAP[dos_name]
            url = server.start(dos_game_cfg)
        else:
            print(f"Error: No configuration found for game '{dos_name}'")
            return

    # Default task
    if not task:
        print("No task provided, using default DOS prompt")
        task = DOS_PROMPT

    # Website-only mode: open the page and keep the server running
    if website_only:
        if url and server:
            print(f"Opening {url} in Chromium browser...")
            await server.open_in_chromium(headless=headless)
            print("Press Ctrl+C to stop the server and exit.")
            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                print("\nShutting down server...")
            finally:
                if server:
                    server.stop()
            return
        else:
            print("Error: No URL specified for website-only mode, or server not started.")
            if server:
                server.stop()
            return

    print("Playing VideoGameBench{} on DOS Emulator".format(" Lite" if args.lite else ""))

    # Build agent kwargs common to both base and memento variants
    agent_kwargs = dict(
        model=model,
        api_key=api_key,
        game=dos_name,
        headless=headless,
        temperature=temperature,
        max_tokens=max_tokens,
        context_window=args.max_context_size,
        lite=args.lite,
        enable_ui=args.enable_ui,
        task_prompt=args.task_prompt,
        press_key_delay=args.press_key_delay,
        api_base=args.api_base,
    )

    # If this AgentClass supports a memento config, pass it through
    # (harmless for the base WebBrowsingVGAgent if it just ignores **kwargs)
    if hasattr(args, "memento"):
        agent_kwargs["memento"] = args.memento

    # Create the agent
    agent = AgentClass(**agent_kwargs)

    # Game interface and evaluator
    game_interface = DOSGameInterface(
        game=dos_name,
        lite=args.lite,
        num_screenshots_per_action=args.num_screenshots_per_action,
    )

    evaluator = DOSEvaluator(
        max_steps=args.max_steps,
        step_delay=args.step_delay,
        checkpoints=args.checkpoints,
        game_interface=game_interface,
        threshold=args.threshold,
    )

    # Start and run
    await evaluator.start(url)
    await evaluator.run_episode(agent, task, server)