"""Evaluator for running LLM game interactions on VideoGameBench."""
from __future__ import annotations

from typing import Dict, Any, Optional, List, Callable, Tuple
import asyncio
import io
import time
from abc import ABC, abstractmethod

import numpy as np
from PIL import Image

# Project imports
from src.llm.vgagent import GameBoyVGAgent, WebBrowsingVGAgent
from src.emulators.gba.interface import GBAInterface
from src.emulators.dos.website_server import DOSGameServer
from src.emulators.dos.interface import DOSGameInterface
from src.utils import is_same_hash, hash_image, dist_hash


# --------------------------- helpers ---------------------------

def _to_bool_array(h) -> Optional[np.ndarray]:
    """
    Coerce ImageHash or ndarray into a boolean ndarray.
    Returns None if coercion fails.
    """
    try:
        # imagehash.ImageHash -> has .hash
        if hasattr(h, "hash"):
            arr = h.hash
            return arr.astype(bool) if hasattr(arr, "astype") else np.array(arr, dtype=bool)
        # numpy array case
        if isinstance(h, np.ndarray):
            return h.astype(bool)
        # list-like of 0/1 or bools
        if isinstance(h, (list, tuple)):
            arr = np.array(h)
            return arr.astype(bool)
    except Exception:
        pass
    return None


def _bit_diff(a: np.ndarray, b: np.ndarray) -> int:
    a = a.astype(bool).ravel()
    b = b.astype(bool).ravel()
    # Align shapes if someone fed us a different hash size by accident
    if a.size != b.size:
        n = min(a.size, b.size)
        a = a[:n]
        b = b[:n]
    return int(np.count_nonzero(a ^ b))


def _safe_is_same_hash(a_bool: np.ndarray, b_bool: np.ndarray, threshold_bits: float) -> bool:
    """
    Try project util is_same_hash first; if that fails, compare bit distance directly.
    """
    try:
        # Many forks accept numpy arrays directly
        return bool(is_same_hash(a_bool, b_bool, threshold=threshold_bits, verbose=False))  # type: ignore
    except Exception:
        pass
    # Fallback on raw Hamming distance in bits
    return _bit_diff(a_bool, b_bool) <= int(threshold_bits)


def _safe_dist_hash(a_bool: np.ndarray, b_bool: np.ndarray) -> float:
    """
    Try project util dist_hash; if it fails, return normalized bit distance [0, 1].
    """
    try:
        return float(dist_hash(a_bool, b_bool))  # type: ignore
    except Exception:
        # Normalized Hamming distance
        bits = max(1, a_bool.size, b_bool.size)
        return _bit_diff(a_bool, b_bool) / float(bits)


# --------------------------- base evaluator ---------------------------

class BaseVGBenchEvaluator(ABC):
    """Abstract base class for evaluators that coordinate between game emulators and LLMs."""

    def __init__(
        self,
        max_steps: int = 1000,
        step_delay: float = 0.0,
        metrics: Optional[List[Callable]] = None,
        checkpoints: Optional[List[Any]] = None,
        threshold: Optional[float] = None,
    ):
        self.max_steps = max_steps
        self.step_delay = step_delay
        self.metrics = metrics or []

        # Normalize checkpoints to boolean arrays (supports ImageHash or ndarray inputs)
        raw_ckpts = checkpoints or []
        self.checkpoints: List[np.ndarray] = []
        for c in raw_ckpts:
            arr = _to_bool_array(c)
            if arr is not None:
                self.checkpoints.append(arr)
        # Similarity threshold in *bits* (Hamming)
        self.threshold: float = float(threshold if threshold is not None else 10.0)

        # Progress tracking
        self.current_checkpoint_idx: Optional[int] = 0 if self.checkpoints else None
        self.completed_checkpoints: set[int] = set()

        # Keep track of dense distance to the next checkpoint for shaping
        self._prev_dist_to_next: Optional[float] = None

        # Hash bitcount used for logging/normalization (best guess from first ckpt)
        try:
            self._hash_bits = int(self.checkpoints[0].size) if self.checkpoints else 64
        except Exception:
            self._hash_bits = 64

    @abstractmethod
    async def run_episode(self, agent) -> Dict[str, Any]:
        """Run an episode of the game."""
        raise NotImplementedError

    # ---------- hashing & reward utilities ----------

    def _obs_to_hash_bool(self, obs_img_or_dict: Any) -> Optional[np.ndarray]:
        """
        Convert an observation (or dict with 'screen') into a boolean hash array.
        """
        try:
            img = obs_img_or_dict
            if isinstance(obs_img_or_dict, dict) and "screen" in obs_img_or_dict:
                img = obs_img_or_dict["screen"]

            # If already boolean array-like, accept
            if isinstance(img, np.ndarray) and img.dtype == bool:
                return img

            # Convert raw RGB/array to PIL when possible
            if isinstance(img, np.ndarray) and img.ndim in (2, 3):
                pil = Image.fromarray(img)
                h = hash_image(pil)
            elif isinstance(img, Image.Image):
                h = hash_image(img)
            else:
                # Let project util try to hash arbitrary types
                h = hash_image(img)

            return _to_bool_array(h)
        except Exception:
            return None

    def _dense_shaping_reward(self, obs_bool: np.ndarray) -> float:
        """
        Positive reward when you get *closer* (by any amount) to the next checkpoint.
        Uses project dist_hash if available, else normalized Hamming distance.
        """
        if self.current_checkpoint_idx is None:
            return 0.0
        if self.current_checkpoint_idx >= len(self.checkpoints):
            return 0.0

        target = self.checkpoints[self.current_checkpoint_idx]
        d = _safe_dist_hash(obs_bool, target)

        rew = 0.0
        if self._prev_dist_to_next is not None:
            improvement = self._prev_dist_to_next - d
            if improvement > 0:
                # Small positive shaped reward; keep scale gentle
                rew = float(improvement)
        self._prev_dist_to_next = d
        return rew

    def _on_advance_checkpoint(self) -> None:
        """Reset dense shaping tracker when we move to the next checkpoint."""
        self._prev_dist_to_next = None

    def _check_checkpoint_progress(self, obs_img_or_dict: Any, agent: Any) -> Tuple[bool, float]:
        """
        Check if current observation matches (within threshold bits) any checkpoint
        from the current index onward. If so, advance and notify the agent.

        Returns: (hit_checkpoint: bool, shaped_reward: float)
        """
        obs_bool = self._obs_to_hash_bool(obs_img_or_dict)
        if obs_bool is None:
            return False, 0.0

        # Dense shaping wrt *next* checkpoint (before possibly advancing)
        shaped = self._dense_shaping_reward(obs_bool)

        hit = False
        if self.checkpoints and self.current_checkpoint_idx is not None:
            for idx in range(self.current_checkpoint_idx, len(self.checkpoints)):
                ck = self.checkpoints[idx]
                try:
                    same = _safe_is_same_hash(obs_bool, ck, threshold_bits=self.threshold)
                except Exception:
                    same = False

                if same:
                    hit = True
                    self.completed_checkpoints.add(idx)
                    self.current_checkpoint_idx = idx + 1
                    self._on_advance_checkpoint()
                    # Notify agent (best-effort)
                    try:
                        agent.update_checkpoint(idx + 1)
                    except Exception:
                        pass
                    # If we hit, also give a +1 sparse bonus
                    shaped += 1.0
                    break

        return hit, shaped


# --------------------------- GB evaluator ---------------------------

class GBEvaluator(BaseVGBenchEvaluator):
    """Evaluator that coordinates Game Boy emulators and LLMs."""

    def __init__(
        self,
        game_interface: GBAInterface,
        max_steps: int = 1000,
        step_delay: float = 0.1,
        skip_frames: int = 1,
        metrics: Optional[List[Callable]] = None,
        fake_actions: bool = False,
        action_frames: int = 30,
        checkpoints: Optional[List[Any]] = None,
        threshold: float = 10.0,
    ):
        super().__init__(max_steps, step_delay, metrics, checkpoints, threshold)
        self.game = game_interface
        self.fake_actions = fake_actions
        self.skip_frames = skip_frames
        self.action_frames = action_frames

    async def run_episode(self, agent: GameBoyVGAgent, lite: bool = False) -> Dict[str, Any]:
        return await (self.run_episode_lite(agent) if lite else self.run_episode_realtime(agent))

    async def run_episode_lite(self, gba_agent: GameBoyVGAgent) -> Dict[str, Any]:
        """
        Frame-paused loop: the game advances only when we step or no-op.
        Good for cheaper debugging.
        """
        # Let the agent know how many checkpoints exist
        try:
            if self.checkpoints:
                gba_agent.setup_checkpoints(len(self.checkpoints))
        except Exception:
            pass

        try:
            obs = self.game.get_observation()
            gba_agent.store_observation(obs)

            actions_to_run: List[Optional[Dict[str, bool]]] = []

            for step in range(self.max_steps):
                if not actions_to_run:
                    actions_to_run = await gba_agent.get_action()

                # Run one action (or no-op)
                if actions_to_run:
                    action = actions_to_run.pop(0)
                else:
                    action = None

                if action is None:
                    obs, _, _, _ = self.game.no_op(self.action_frames)
                else:
                    obs, _, _, _ = self.game.step(action, self.action_frames)

                gba_agent.store_observation(obs)

                # Checkpoints + reward shaping
                hit, shaped = self._check_checkpoint_progress(
                    obs["screen"] if isinstance(obs, dict) and "screen" in obs else obs,
                    gba_agent,
                )

                # Progress value for logging
                total = len(self.checkpoints)
                current = int(self.current_checkpoint_idx or 0)
                progress = (current / total) if total > 0 else 0.0

                # Send reward/progress to the agent for memento logging
                try:
                    await gba_agent.post_action(action, float(shaped), {"progress": float(progress)})
                except TypeError:
                    # If base is sync
                    try:
                        gba_agent.post_action(action, float(shaped), {"progress": float(progress)})
                    except Exception:
                        pass

                if hit and (self.current_checkpoint_idx is not None) and (self.current_checkpoint_idx >= len(self.checkpoints)):
                    print("Task complete! All checkpoints completed.")
                    break

        except KeyboardInterrupt:
            print("\nEvaluation interrupted by user")
        except Exception as e:
            print(f"Error during evaluation: {e}")
        finally:
            try:
                self.game.close()
            except Exception:
                pass

        return {}

    async def run_episode_realtime(self, gba_agent: GameBoyVGAgent) -> Dict[str, Any]:
        """
        Realtime loop: requests actions asynchronously while the emulator keeps ticking with no-ops.
        """
        try:
            if self.checkpoints:
                gba_agent.setup_checkpoints(len(self.checkpoints))
        except Exception:
            pass

        try:
            obs = self.game.get_observation()
            gba_agent.store_observation(obs)

            actions_to_run: List[Optional[Dict[str, bool]]] = []

            for step in range(self.max_steps):
                if not actions_to_run:
                    action_task = asyncio.create_task(gba_agent.get_action())

                    # While thinking, keep the emulator alive with no-ops
                    while not action_task.done():
                        obs, _, _, _ = self.game.no_op(1)
                        gba_agent.store_observation(obs)

                        hit, shaped = self._check_checkpoint_progress(
                            obs["screen"] if isinstance(obs, dict) and "screen" in obs else obs,
                            gba_agent,
                        )

                        total = len(self.checkpoints)
                        current = int(self.current_checkpoint_idx or 0)
                        progress = (current / total) if total > 0 else 0.0

                        # We didn't actually take a meaningful action yet; pass None
                        try:
                            await gba_agent.post_action(None, float(shaped), {"progress": float(progress)})
                        except TypeError:
                            try:
                                gba_agent.post_action(None, float(shaped), {"progress": float(progress)})
                            except Exception:
                                pass

                        if hit and (self.current_checkpoint_idx is not None) and (self.current_checkpoint_idx >= len(self.checkpoints)):
                            print("Task complete! All checkpoints completed.")
                            break

                        await asyncio.sleep(0.01)

                    if action_task.done():
                        actions_to_run = await action_task

                # If we still failed to parse any action, just no-op for a chunk of frames
                if not actions_to_run:
                    obs, _, _, _ = self.game.no_op(self.action_frames)
                    gba_agent.store_observation(obs)

                    hit, shaped = self._check_checkpoint_progress(
                        obs["screen"] if isinstance(obs, dict) and "screen" in obs else obs,
                        gba_agent,
                    )

                    total = len(self.checkpoints)
                    current = int(self.current_checkpoint_idx or 0)
                    progress = (current / total) if total > 0 else 0.0

                    try:
                        await gba_agent.post_action(None, float(shaped), {"progress": float(progress)})
                    except TypeError:
                        try:
                            gba_agent.post_action(None, float(shaped), {"progress": float(progress)})
                        except Exception:
                            pass

                    if hit and (self.current_checkpoint_idx is not None) and (self.current_checkpoint_idx >= len(self.checkpoints)):
                        print("Task complete! All checkpoints completed.")
                        break

                    continue

                # Execute the next action
                current_action = actions_to_run.pop(0)
                if current_action is not None:
                    obs, _, _, _ = self.game.step(current_action, self.action_frames)
                else:
                    obs, _, _, _ = self.game.no_op(self.action_frames)

                gba_agent.store_observation(obs)

                hit, shaped = self._check_checkpoint_progress(
                    obs["screen"] if isinstance(obs, dict) and "screen" in obs else obs,
                    gba_agent,
                )

                total = len(self.checkpoints)
                current = int(self.current_checkpoint_idx or 0)
                progress = (current / total) if total > 0 else 0.0

                try:
                    await gba_agent.post_action(current_action, float(shaped), {"progress": float(progress)})
                except TypeError:
                    try:
                        gba_agent.post_action(current_action, float(shaped), {"progress": float(progress)})
                    except Exception:
                        pass

                if hit and (self.current_checkpoint_idx is not None) and (self.current_checkpoint_idx >= len(self.checkpoints)):
                    print("Task complete! All checkpoints completed.")
                    break

        except KeyboardInterrupt:
            print("\nEvaluation interrupted by user")
        except Exception as e:
            print(f"Error during realtime evaluation: {e}")

        return {}


# --------------------------- DOS evaluator ---------------------------

class DOSEvaluator(BaseVGBenchEvaluator):
    """Evaluator coordinating JS-DOS style web games and LLMs."""

    def __init__(
        self,
        max_steps: int = 10000,
        step_delay: float = 0.1,
        metrics: Optional[List[Callable]] = None,
        checkpoints: Optional[List[Any]] = None,
        game_interface: DOSGameInterface = None,
        threshold: float = 10.0,
    ):
        super().__init__(max_steps, step_delay, metrics, checkpoints, threshold)
        self.game = game_interface

    async def start(self, url: str):
        await self.game.load_game(initial_url=url)

    async def run_episode(
        self,
        dos_agent: WebBrowsingVGAgent,
        task: str,
        server: DOSGameServer
    ) -> Dict[str, Any]:
        if self.checkpoints:
            try:
                dos_agent.setup_checkpoints(len(self.checkpoints))
            except Exception:
                pass

        try:
            # initial screen
            screen = await self.game.get_observation()
            await dos_agent.store_observation([screen])

            task_complete = False
            for step in range(self.max_steps):
                action, action_input = await dos_agent.get_action(task, self.game.browser, step)
                await dos_agent.pre_action(action, action_input, self.game.lite)
                info, frames = await self.game.step(action, action_input)
                await dos_agent.post_action(info, frames, action, action_input)

                # checkpoint checks across frames
                for frame in frames:
                    frame_pil = Image.open(io.BytesIO(frame)).crop((50, 0, 640, 400))
                    hit, _ = self._check_checkpoint_progress(frame_pil, dos_agent)
                    if hit:
                        task_complete = True

                if task_complete:
                    print("Task complete! All checkpoints completed.")
                    break

            if not task_complete and self.max_steps > 0:
                print("Reached maximum number of steps without completing the task.")
        finally:
            try:
                await self.game.close()
            except Exception:
                pass
            try:
                await dos_agent.stop()
            except Exception:
                pass
            try:
                if server:
                    server.stop()
            except Exception:
                pass

        return {}