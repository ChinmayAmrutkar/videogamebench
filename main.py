"""Evaluator for running LLM game interactions on VideoGameBench."""
from __future__ import annotations

from typing import Dict, Any, Optional, List, Callable, Tuple
import asyncio
import io
import time
import inspect
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
        if hasattr(h, "hash"):  # imagehash.ImageHash
            arr = h.hash
            return arr.astype(bool) if hasattr(arr, "astype") else np.array(arr, dtype=bool)
        if isinstance(h, np.ndarray):
            return h.astype(bool)
        if isinstance(h, (list, tuple)):
            arr = np.array(h)
            return arr.astype(bool)
    except Exception:
        pass
    return None


def _bit_diff(a: np.ndarray, b: np.ndarray) -> int:
    a = a.astype(bool).ravel()
    b = b.astype(bool).ravel()
    if a.size != b.size:
        n = min(a.size, b.size)
        a = a[:n]
        b = b[:n]
    return int(np.count_nonzero(a ^ b))


def _safe_is_same_hash(a_bool: np.ndarray, b_bool: np.ndarray, threshold_bits: float) -> bool:
    try:
        return bool(is_same_hash(a_bool, b_bool, threshold=threshold_bits, verbose=False))  # type: ignore
    except Exception:
        pass
    return _bit_diff(a_bool, b_bool) <= int(threshold_bits)


def _safe_dist_hash(a_bool: np.ndarray, b_bool: np.ndarray) -> float:
    try:
        return float(dist_hash(a_bool, b_bool))  # type: ignore
    except Exception:
        bits = max(1, a_bool.size, b_bool.size)
        return _bit_diff(a_bool, b_bool) / float(bits)


def _dos_session_started(agent, t0: float, seen_frames: int, min_seconds: float = 5.0) -> bool:
    """
    Consider DOS session 'started' only after:
      (a) at least one non-empty frame has been captured,
      (b) at least one keypress has occurred,
      (c) at least `min_seconds` have elapsed since t0.
    Compatible with WebBrowsingVGAgent; if the agent exposes
    has_seen_first_frame()/keypress_count(), we use those too.
    """
    try:
        if hasattr(agent, "has_seen_first_frame"):
            seen = bool(agent.has_seen_first_frame())
        else:
            seen = seen_frames > 0

        if hasattr(agent, "keypress_count"):
            keys = int(agent.keypress_count())
        else:
            keys = int(getattr(agent, "_keypress_count", 0))

        elapsed = time.time() - float(t0 or 0.0)
        return bool(seen and keys >= 1 and elapsed >= float(min_seconds))
    except Exception:
        return False


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

        raw_ckpts = checkpoints or []
        self.checkpoints: List[np.ndarray] = []
        for c in raw_ckpts:
            arr = _to_bool_array(c)
            if arr is not None:
                self.checkpoints.append(arr)

        self.threshold: float = float(threshold if threshold is not None else 10.0)
        self.current_checkpoint_idx: Optional[int] = 0 if self.checkpoints else None
        self.completed_checkpoints: set[int] = set()
        self._prev_dist_to_next: Optional[float] = None

        try:
            self._hash_bits = int(self.checkpoints[0].size) if self.checkpoints else 64
        except Exception:
            self._hash_bits = 64

    @abstractmethod
    async def run_episode(self, agent) -> Dict[str, Any]:
        raise NotImplementedError

    # ---------- hashing & reward utilities ----------

    def _obs_to_hash_bool(self, obs_img_or_dict: Any) -> Optional[np.ndarray]:
        try:
            img = obs_img_or_dict
            if isinstance(obs_img_or_dict, dict) and "screen" in obs_img_or_dict:
                img = obs_img_or_dict["screen"]

            if isinstance(img, np.ndarray) and img.dtype == bool:
                return img

            if isinstance(img, np.ndarray) and img.ndim in (2, 3):
                pil = Image.fromarray(img)
                h = hash_image(pil)
            elif isinstance(img, Image.Image):
                h = hash_image(img)
            else:
                h = hash_image(img)

            return _to_bool_array(h)
        except Exception:
            return None

    def _dense_shaping_reward(self, obs_bool: np.ndarray) -> float:
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
                rew = float(improvement)
        self._prev_dist_to_next = d
        return rew

    def _on_advance_checkpoint(self) -> None:
        self._prev_dist_to_next = None

    def _check_checkpoint_progress(self, obs_img_or_dict: Any, agent: Any) -> Tuple[bool, float]:
        obs_bool = self._obs_to_hash_bool(obs_img_or_dict)
        if obs_bool is None:
            return False, 0.0

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
                    try:
                        agent.update_checkpoint(idx + 1)
                    except Exception:
                        pass
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
        try:
            if self.checkpoints:
                gba_agent.setup_checkpoints(len(self.checkpoints))
        except Exception:
            pass

        try:
            obs = self.game.get_observation()
            gba_agent.store_observation(obs)

            actions_to_run: List[Optional[Dict[str, bool]]] = []

            for _ in range(self.max_steps):
                if not actions_to_run:
                    actions_to_run = await gba_agent.get_action()

                action = actions_to_run.pop(0) if actions_to_run else None

                if action is None:
                    obs, _, _, _ = self.game.no_op(self.action_frames)
                else:
                    obs, _, _, _ = self.game.step(action, self.action_frames)

                gba_agent.store_observation(obs)

                hit, shaped = self._check_checkpoint_progress(
                    obs["screen"] if isinstance(obs, dict) and "screen" in obs else obs,
                    gba_agent,
                )

                total = len(self.checkpoints)
                current = int(self.current_checkpoint_idx or 0)
                progress = (current / total) if total > 0 else 0.0

                try:
                    await gba_agent.post_action(action, float(shaped), {"progress": float(progress)})
                except TypeError:
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
        try:
            if self.checkpoints:
                gba_agent.setup_checkpoints(len(self.checkpoints))
        except Exception:
            pass

        try:
            obs = self.game.get_observation()
            gba_agent.store_observation(obs)

            actions_to_run: List[Optional[Dict[str, bool]]] = []

            for _ in range(self.max_steps):
                if not actions_to_run:
                    action_task = asyncio.create_task(gba_agent.get_action())

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
                    continue

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
        min_start_seconds: float = 5.0,
    ):
        super().__init__(max_steps, step_delay, metrics, checkpoints, threshold)
        self.game = game_interface
        self.min_start_seconds = float(min_start_seconds)

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

        start_time = time.time()
        seen_frames = 0
        session_started = False
        task_complete = False

        try:
            # initial screen
            screen = await self.game.get_observation()
            # async-safe: await only if the call is awaitable
            res = dos_agent.store_observation([screen])
            if inspect.isawaitable(res):
                await res

            for step in range(self.max_steps):
                action, action_input = await dos_agent.get_action(task, self.game.browser, step)
                # pre_action may be async or sync depending on base class
                try:
                    if inspect.iscoroutinefunction(dos_agent.pre_action):
                        await dos_agent.pre_action(action, action_input, self.game.lite)
                    else:
                        dos_agent.pre_action(action, action_input, self.game.lite)
                except Exception:
                    pass

                info, frames = await self.game.step(action, action_input)

                try:
                    if inspect.iscoroutinefunction(dos_agent.post_action):
                        await dos_agent.post_action(info, frames, action, action_input)
                    else:
                        dos_agent.post_action(info, frames, action, action_input)
                except Exception:
                    pass

                if frames:
                    seen_frames += len(frames)

                if not session_started:
                    session_started = _dos_session_started(
                        dos_agent, start_time, seen_frames, self.min_start_seconds
                    )

                total_ck = len(self.checkpoints)
                current = int(self.current_checkpoint_idx or 0)
                progress = (current / total_ck) if total_ck > 0 else 0.0

                # allow DOS agent to log shaped rewards too
                if hasattr(dos_agent, "post_action_reward"):
                    try:
                        if inspect.iscoroutinefunction(dos_agent.post_action_reward):
                            await dos_agent.post_action_reward(0.0, {"progress": float(progress)})
                        else:
                            dos_agent.post_action_reward(0.0, {"progress": float(progress)})
                    except Exception:
                        pass

                if session_started:
                    for frame in frames:
                        try:
                            pil = Image.open(io.BytesIO(frame)).crop((50, 0, 640, 400))
                        except Exception:
                            continue

                        hit, shaped = self._check_checkpoint_progress(pil, dos_agent)

                        if shaped != 0.0 and hasattr(dos_agent, "post_action_reward"):
                            try:
                                if inspect.iscoroutinefunction(dos_agent.post_action_reward):
                                    await dos_agent.post_action_reward(float(shaped), {"progress": float(progress)})
                                else:
                                    dos_agent.post_action_reward(float(shaped), {"progress": float(progress)})
                            except Exception:
                                pass

                        if hit and (self.current_checkpoint_idx is not None) and (self.current_checkpoint_idx >= len(self.checkpoints)):
                            task_complete = True
                            break

                if task_complete:
                    print("Task complete! All checkpoints completed.")
                    break

            if not task_complete and self.max_steps > 0:
                if not session_started:
                    print("Not started: waiting for first frame + keypress + elapsed time; task not evaluated.")
                else:
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
