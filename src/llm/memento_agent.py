from __future__ import annotations

import inspect
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from typing import List, Dict  # ensure this is imported at top


from PIL import Image, ImageOps, ImageFilter
import numpy as np
import io
try:
    import pytesseract
except Exception:
    pytesseract = None
from .vgagent import GameBoyVGAgent  # base agent
from .memento_memory import MementoMemory  # lightweight, vectorless memory


@dataclass
class MementoConfig:
    """Tunable knobs for the memento add-on."""
    # How many past cases to retrieve for the prompt
    top_k: int = 3
    # Store one memory every N environment steps
    write_every_n_steps: int = 1
    # Weighting for retrieval scoring
    recency_decay: float = 0.997
    reward_coef: float = 0.5
    progress_coef: float = 0.5
    # How many cases to keep in RAM (older ones are trimmed)
    capacity: int = 1024
    # Persist memory to disk (jsonl) inside log_dir
    persist: bool = True
    # Whether to save detailed retrieval debug artifacts
    debug_retrieval: bool = True
    use_ocr: bool = True

    @classmethod
    def from_dict(cls, d: Dict[str, Any] | None) -> "MementoConfig":
        if not isinstance(d, dict):
            return cls()
        fields = {
            k: d[k]
            for k in [
                "top_k",
                "write_every_n_steps",
                "recency_decay",
                "reward_coef",
                "progress_coef",
                "capacity",
                "persist",
                "debug_retrieval",
                 "use_ocr" ,
            ]
            if k in d
        }
        return cls(**fields)


class MementoGameBoyVGAgent(GameBoyVGAgent):
    """
    Drop-in replacement for GameBoyVGAgent that adds a lightweight memento memory:

    - Logs (state_card, action, reward, progress) every step (or every N steps)
    - Retrieves top-K relevant past cases and injects them into the prompt
    - Writes rewards to a CSV and appends memories to JSONL
    - Persists retrieval debug artifacts under log_dir/memento_debug
    - Keeps backward compatibility with the base agent method signatures
    """

    # --------------------- Init & filesystem ---------------------

    def __init__(self, *args, **kwargs) -> None:
        # Extract memento-specific config before calling super
        mcfg_raw = kwargs.pop("memento", None)
        super().__init__(*args, **kwargs)

        self.mcfg: MementoConfig = MementoConfig.from_dict(mcfg_raw)
        self.memory = MementoMemory(capacity=self.mcfg.capacity)

        # Runtime scratch
        self._last_obs_card: Optional[str] = None
        self._step_counter: int = 0
        self._prepare_counter: int = 0

        # Files / directories
        base_dir = Path(getattr(self, "log_dir", None) or Path.cwd())
        self._reward_log_path = base_dir / "reward_log.csv"
        self._mem_path = base_dir / "memento_memory.jsonl"
        self._memento_dir = base_dir / "memento_debug"
        self._last_retrieval_block: str = ""
        self._last_retrieval_summary: str = ""          
        self._ocr_enabled = bool(getattr(self.mcfg, "use_ocr", True)) and (pytesseract is not None)
        self._prev_ahash: Optional[int] = None 
        
        try:
            self._memento_dir.mkdir(parents=True, exist_ok=True)
            if not self._reward_log_path.exists():
                self._reward_log_path.parent.mkdir(parents=True, exist_ok=True)
                self._reward_log_path.write_text(
                    "ts,step,reward,progress\n", encoding="utf-8"
                )
        except Exception:
            # Never crash I/O setup
            pass
        
        # Optional visibility
        try:
            lg = getattr(self, "logger", None)
            if lg:
                lg.info(f"Memento debug_retrieval = {self.mcfg.debug_retrieval}")
        except Exception:
            pass
        
    # --------------------- Observation hook ---------------------

    def _build_fallback_card(self, obs: Any) -> str:
        """
        Always produce a non-empty, informative summary even without OCR/metadata.
        """
        try:
            # Prefer a visual signature if we have a screen
            if isinstance(obs, dict) and "screen" in obs:
                img = self._ensure_pil(obs.get("screen"))
                if img is not None:
                    sig = self._visual_signature(img)

                    # (optional) drop an ASCII thumb for quick diffing
                    if getattr(self.mcfg, "debug_retrieval", False):
                        try:
                            step_hint = max(self._step_counter, self._prepare_counter)
                            ascii_map = self._ascii_thumb(img, w=32, h=24)
                            (self._memento_dir / f"ascii_step_{step_hint}.txt").write_text(
                                ascii_map, encoding="utf-8"
                            )
                        except Exception:
                            pass

                    return sig

            # If the emulator stashes any metadata, include that too
            if isinstance(obs, dict):
                parts = []
                for k in ("text", "score", "world", "level", "lives", "time"):
                    if k in obs and obs[k] is not None:
                        parts.append(f"{k}={obs[k]}")
                if parts:
                    return " | ".join(parts)

        except Exception:
            pass

        # Absolute last resort (should be rare now)
        return "sig (no screen available)"


    def store_observation(self, obs: Any) -> None:
        """
        Keep base behavior AND cache a best-effort observation card for memory.
        We try several helper names that commonly exist in different forks.
        """
        try:
            super().store_observation(obs)
        finally:
            card = None
            # Try a variety of helper methods that may exist on the base class
            for attr in (
                "_format_observation_card",
                "_make_observation_card",
                "format_observation_card",
                "_observation_to_card",
                "summarize_observation",
            ):
                fn = getattr(self, attr, None)
                if callable(fn):
                    try:
                        card = fn(obs)  # type: ignore[misc]
                        if card:
                            break
                    except Exception:
                        pass

            if not isinstance(card, str) or not card.strip():
                card = self._build_fallback_card(obs)

            self._last_obs_card = card.strip()

    def _ahash_bits(self, img: Image.Image, n: int = 8) -> int:
        """
        Average-hash as an integer bitfield over an n x n grid.
        """
        g = ImageOps.grayscale(img).resize((n, n), Image.BILINEAR)
        arr = np.asarray(g, dtype=np.float32)
        m = float(arr.mean()) if arr.size else 0.0
        bits = (arr > m).astype(np.uint8)
        # pack bits row-major into an int
        val = 0
        for b in bits.flatten():
            val = (val << 1) | int(b)
        return int(val)

    def _ahash_hex(self, img: Image.Image, n: int = 8) -> str:
        val = self._ahash_bits(img, n=n)
        # width in hex digits: (n*n bits) / 4
        width = (n * n) // 4
        return f"{val:0{width}x}"

    def _ascii_thumb(self, img: Image.Image, w: int = 32, h: int = 24) -> str:
        """
        Tiny ASCII thumbnail to inspect screen structure in logs:
        '#' = dark, '.' = light. Saves to memento_debug when debug_retrieval is on.
        """
        g = ImageOps.grayscale(img).resize((w, h), Image.BILINEAR)
        arr = np.asarray(g, dtype=np.uint8)
        thr = int(arr.mean())  # simple adaptive threshold
        rows = []
        for r in range(h):
            line = "".join("#" if arr[r, c] < thr else "." for c in range(w))
            rows.append(line)
        return "\n".join(rows)

    def _visual_signature(self, img: Image.Image) -> str:
        """
        Build a compact, always-available state_card from image-only cues.
        Includes aHash, brightness, dark ratio, rough player_x, and Δ (changed since last step).
        """
        # average-hash (8x8)
        ah_hex = self._ahash_hex(img, n=8)
        ah_int = int(ah_hex, 16)
        changed = 0 if (self._prev_ahash is not None and self._prev_ahash == ah_int) else 1
        self._prev_ahash = ah_int

        # brightness & dark ratio
        g = ImageOps.grayscale(img)
        arr = np.asarray(g, dtype=np.float32)
        if arr.size == 0:
            return f"sig ah={ah_hex} Δ={changed} (empty frame?)"

        bright = float(arr.mean() / 255.0)
        dark_ratio = float((arr < 80).mean())  # fraction very dark pixels

        # rough player_x: column of max "dark mass"
        # (very crude but stable enough to distinguish left/mid/right)
        darkness = (255.0 - arr).clip(0, 255)
        col_mass = darkness.sum(axis=0)
        idx = int(col_mass.argmax()) if col_mass.size > 0 else 0
        player_x = idx / max(1, (arr.shape[1] - 1))

        return (
            f"sig ah={ah_hex} pos≈{player_x:.2f} bright={bright:.2f} "
            f"dark={dark_ratio:.2f} Δ={changed}"
        )

    
    def _ensure_pil(self, frame):
        if isinstance(frame, Image.Image):
            return frame
        if isinstance(frame, (bytes, bytearray)):
            try: return Image.open(io.BytesIO(frame)).convert("RGB")
            except Exception: return None
        try:
            arr = np.array(frame)
            if arr.ndim == 2:  return Image.fromarray(arr.astype(np.uint8), "L").convert("RGB")
            if arr.ndim == 3 and arr.shape[-1] in (3,4):
                mode = "RGBA" if arr.shape[-1]==4 else "RGB"
                return Image.fromarray(arr.astype(np.uint8), mode).convert("RGB")
        except Exception:
            pass
        return None

    def _extract_on_screen_text(self, img: Image.Image) -> str:
        if not self._ocr_enabled or img is None:
            return ""
        W, H = img.size
        hud = img.crop((0, 0, W, int(0.33 * H)))
        g = ImageOps.grayscale(hud)
        g = ImageOps.autocontrast(g).filter(ImageFilter.SHARPEN)
        g = g.resize((g.width*2, g.height*2), Image.NEAREST)
        try:
            txt = pytesseract.image_to_string(g, config="--psm 6 -l eng")
        except Exception:
            txt = ""
        if not txt or len(txt.strip()) < 4:
            g2 = ImageOps.grayscale(img)
            g2 = ImageOps.autocontrast(g2).filter(ImageFilter.SHARPEN)
            g2 = g2.resize((g2.width*2, g2.height*2), Image.NEAREST)
            try:
                txt2 = pytesseract.image_to_string(g2, config="--psm 6 -l eng")
                if len((txt2 or "").strip()) > len((txt or "").strip()):
                    txt = txt2
            except Exception:
                pass
        txt = " ".join("".join(ch for ch in (txt or "") if 31 < ord(ch) < 127).split())
        # optional: write a debug file
        if getattr(self.mcfg, "debug_retrieval", False):
            try:
                step_hint = max(self._step_counter, self._prepare_counter)
                (self._memento_dir / f"ocr_step_{step_hint}.txt").write_text(txt or "<empty>", encoding="utf-8")
            except Exception:
                pass
        return txt

    def _observation_to_card(self, obs) -> str:
        # 1) Use emulator metadata if available
        if isinstance(obs, dict):
            parts = []
            for k in ("world","level","stage","score","coins","lives","time"):
                if k in obs and obs[k] is not None:
                    parts.append(f"{k}={obs[k]}")
            if parts:
                return " | ".join(parts)

            # Warn if there's no screen to OCR
            if "screen" not in obs:
                if getattr(self.mcfg, "debug_retrieval", False):
                    try:
                        print("[memento][warn] obs has no 'screen' key; OCR disabled for this step")
                    except Exception:
                        pass
                return ""  # fall back; store_observation will fill a generic card

            # 2) OCR from screen
            img = self._ensure_pil(obs.get("screen"))
            text = self._extract_on_screen_text(img) if img is not None else ""
            if text:
                return text[:120]

        # 3) Fallback used by your store_observation
        return ""

# --------------------- Prompt preparation (retrieval inject) ---------------------


    async def _prepare_messages(self, *args, **kwargs) -> List[Dict[str, Any]]:
        self._prepare_counter += 1

        # 1) Capture obs_card regardless of signature
        obs_card = kwargs.get("obs_card", None)
        if obs_card is None and args and isinstance(args[0], str):
            obs_card = args[0]
        if obs_card:
            self._last_obs_card = obs_card

        # 2) Call base implementation (handle either signature)
        try:
            messages = await super()._prepare_messages(*args, **kwargs)
        except TypeError:
            messages = await super()._prepare_messages()

        # 3) Retrieve top-K memento cases
        try:
            k = max(0, int(self.mcfg.top_k))
        except Exception:
            k = 0

        cases: List[Dict[str, Any]] = []
        if k > 0:
            try:
                cases = self.memory.retrieve_recent(
                    state_card=self._last_obs_card or "",
                    k=k,
                    recency_decay=float(self.mcfg.recency_decay),
                    reward_coef=float(self.mcfg.reward_coef),
                    progress_coef=float(self.mcfg.progress_coef),
                )
            except Exception:
                cases = []

        # 4) Build injection(s)
        if cases:
            # Build entries with proper comma separation
            entry_lines: List[str] = []
            for i, c in enumerate(cases, 1):
                # state text
                st = (c.get("state_card") or c.get("summary") or "current_screen (no text summary available)")
                st = st.replace("\n", " ")[:360]

                # compact action macro for readability
                act = c.get("action", "")
                if isinstance(act, dict):
                    pressed = [k for k, v in act.items() if v]
                    act_str = "+".join(pressed) if pressed else "NO-OP"
                else:
                    act_str = str(act)[:160]

                rew = float(c.get("reward", 0.0))
                prog = float(c.get("progress", 0.0))
                entry_lines.append(
                    f'  {{"rank": {i}, "reward": {rew:.3f}, "progress": {prog:.3f}, '
                    f'"action": "{act_str}", "state": "{st}"}}'
                )

            # Machine-friendly retrieval block + header
            retrieval_block = (
                "[RETRIEVAL CONTEXT]\n"
                "You are given past action macros and reflections from recent episodes.\n"
                "Use them as hints for the current screen. Decision rule:\n"
                " • Prefer macros with reward>0 or progress ≥ current checkpoint.\n"
                " • If the screen hash does not change for 2 steps, try the fallback sequence.\n"
                " • Output ONLY one actions block in the REQUIRED schema.\n\n"
                "{\n"
                '"PAST_CASES": [\n' + ",\n".join(entry_lines) + "\n]\n}"
            )

            # Human-friendly summary
            summary_text = self._build_cases_summary(cases)

            # Insert both right before the last user message for salience
            last_user_idx = -1
            for idx in range(len(messages) - 1, -1, -1):
                if isinstance(messages[idx], dict) and messages[idx].get("role") == "user":
                    last_user_idx = idx
                    break
            insert_idx = last_user_idx if last_user_idx != -1 else len(messages)

            messages.insert(insert_idx, {"role": "user", "content": retrieval_block})
            messages.insert(insert_idx + 1, {"role": "user", "content": summary_text})

            # Keep for logging/memory
            self._last_retrieval_block = retrieval_block
            self._last_retrieval_summary = summary_text
        else:
            self._last_retrieval_block = ""
            self._last_retrieval_summary = ""

        # 5) Debug artifacts
        if getattr(self.mcfg, "debug_retrieval", False):
            try:
                step_hint = max(self._step_counter, self._prepare_counter)
                if cases:
                    # existing debug bundle
                    self._save_retrieval_debug(cases, self._last_retrieval_block, messages)
                    # summary + readable one-pager
                    (self._memento_dir / f"retrieval_summary_step_{step_hint}.txt").write_text(
                        self._last_retrieval_summary or "[no summary]", encoding="utf-8"
                    )
                    (self._memento_dir / f"readable_retrieval_step_{step_hint}.txt").write_text(
                        "=== OBSERVATION CARD ===\n"
                        f"{self._last_obs_card or '<empty>'}\n\n"
                        "=== PAST_CASES ===\n"
                        f"{self._last_retrieval_block}\n\n"
                        "=== SUMMARY ===\n"
                        f"{self._last_retrieval_summary}\n",
                        encoding="utf-8"
                    )
                else:
                    note = (
                        f"[no retrieval cases] step={self._prepare_counter} "
                        f"obs_card={(self._last_obs_card or '<empty>')!r} "
                        f"mem_size={len(getattr(self.memory, '_cases', []) or [])}"
                    )
                    self._save_retrieval_debug([], note, messages)

                # console breadcrumbs
                try:
                    print("[memento][debug] obs_card:", (self._last_obs_card or "<empty>"))
                    if cases:
                        print("[memento][debug] injected retrieval block and summary.")
                    else:
                        print("[memento][debug] no cases to inject this step")
                except Exception:
                    pass
            except Exception:
                pass

        return messages


    # --------------------- Memory updates & reward logging ---------------------

    async def post_action(self, action: Any, reward: float, info: Dict[str, Any]) -> None:
        """
        Log reward/progress and append a memory case periodically.
        Compatible with both async and sync base post_action.
        """
        # Let the base agent do its bookkeeping
        try:
            base = getattr(super(), "post_action", None)
            if inspect.iscoroutinefunction(base):  # type: ignore[arg-type]
                await base(action, reward, info)  # type: ignore[misc]
            elif callable(base):
                base(action, reward, info)  # type: ignore[misc]
        except Exception:
            pass

        # Steps & signals
        self._step_counter += 1
        try:
            progress_val = float(info.get("progress", 0.0)) if isinstance(info, dict) else 0.0
        except Exception:
            progress_val = 0.0
        reward_val = float(reward or 0.0)

        # Console breadcrumb + CSV append
        try:
            print(f"[memento] step={self._step_counter} reward={reward_val:.6f} progress={progress_val:.6f}")
        except Exception:
            pass
        self._log_step_reward(self._step_counter, reward_val, progress_val)

        # Memory write
        if self.mcfg.write_every_n_steps > 0 and (self._step_counter % self.mcfg.write_every_n_steps == 0):
            case: Dict[str, Any] = {
                "ts": time.time(),
                "step": self._step_counter,
                "state_card": self._last_obs_card or "",
                "action": action,
                "reward": reward_val,
                "progress": progress_val,
                "retrieval_block": self._last_retrieval_block,
                "retrieval_summary": self._last_retrieval_summary,
            }
            try:
                self.memory.add_case(case)
            except Exception:
                pass

            if self.mcfg.persist:
                self._persist_memory_append(case)

    # --------------------- Checkpoint hook (optional) ---------------------

    def update_checkpoint(self, *args: Any, **kwargs: Any) -> None:
        """Forward to base if available. Non-fatal if not implemented."""
        try:
            super().update_checkpoint(*args, **kwargs)  # type: ignore[misc]
        except Exception:
            pass

    # --------------------- Utilities ---------------------

    def _log_step_reward(self, step: int, reward: float, progress: float) -> None:
        try:
            self._reward_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._reward_log_path.open("a", encoding="utf-8") as f:
                f.write(f"{int(time.time())},{step},{reward:.6f},{progress:.6f}\n")
        except Exception:
            pass

    def _persist_memory_append(self, case: Dict[str, Any]) -> None:
        try:
            self._mem_path.parent.mkdir(parents=True, exist_ok=True)
            with self._mem_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(case, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _save_retrieval_debug(
        self,
        cases: List[Dict[str, Any]],
        retrieval_block: str,
        messages: List[Dict[str, Any]],
    ) -> None:
        """Write the retrieval inputs/outputs for offline inspection."""
        try:
            self._memento_dir.mkdir(parents=True, exist_ok=True)
            step_hint = max(self._step_counter, self._prepare_counter)

            # Save raw cases
            (self._memento_dir / f"retrieval_cases_step_{step_hint}.json").write_text(
                json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            # Save the injected (or placeholder) prompt block
            (self._memento_dir / f"retrieval_prompt_step_{step_hint}.txt").write_text(
                retrieval_block, encoding="utf-8"
            )
            # Save the full message payload that will be sent to the LLM
            (self._memento_dir / f"messages_after_injection_step_{step_hint}.json").write_text(
                json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            # Never crash due to I/O
            pass
    
    def _macro_from_action(self, act: Any) -> str:
        """
        Turn an action (dict or str) into a compact macro like 'B+RIGHT' for counting.
        """
        try:
            if isinstance(act, dict):
                pressed = [k for k, v in act.items() if v]
                return "+".join(pressed) if pressed else "NO-OP"
            s = str(act).strip()
            if s.startswith("{") and s.endswith("}"):  # dict-like string
                # very lightweight parse
                pressed = []
                for part in s.strip("{} ").split(","):
                    if ":" in part:
                        k, v = part.split(":", 1)
                        k = k.strip().strip("'\"")
                        v = v.strip().strip(", ").lower()
                        if v in ("true", "1"):
                            pressed.append(k)
                return "+".join(pressed) if pressed else "NO-OP"
            return s or "NO-OP"
        except Exception:
            return "NO-OP"

    def _build_cases_summary(self, cases: List[Dict[str, Any]]) -> str:
        """
        Summarize retrieved cases: best reward, max progress, most common action,
        and a few representative past state lines.
        """
        if not cases:
            return "[RETRIEVAL SUMMARY]\n(no prior cases in memory)\n"

        # stats
        best_reward = max(float(c.get("reward", 0.0)) for c in cases)
        max_progress = max(float(c.get("progress", 0.0)) for c in cases)
        avg_progress = sum(float(c.get("progress", 0.0)) for c in cases) / max(1, len(cases))

        # most common action macro
        counts: Dict[str, int] = {}
        for c in cases:
            macro = self._macro_from_action(c.get("action"))
            counts[macro] = counts.get(macro, 0) + 1
        most_common_action = max(counts.items(), key=lambda kv: kv[1])[0] if counts else "NO-OP"
        most_common_count = counts.get(most_common_action, 0)

        # representative states (unique, short)
        seen = set()
        reps: List[str] = []
        for c in cases:
            st = (c.get("state_card") or c.get("summary") or "").strip()
            if not st:
                st = "current_screen (no text summary available)"
            st = st.replace("\n", " ")
            if st not in seen:
                seen.add(st)
                reps.append(st[:120])
            if len(reps) >= 3:
                break

        lines = [
            "[RETRIEVAL SUMMARY]",
            f"k={len(cases)} | best_reward={best_reward:.3f} | max_progress={max_progress:.3f} | avg_progress={avg_progress:.3f}",
            f"Most common action: {most_common_action} ({most_common_count}×)",
            "Representative past states:",
        ]
        for st in reps:
            lines.append(f" • {st}")
        # small actionable hint if we have a rewarded pattern
        if best_reward > 0.0 and most_common_action != "NO-OP":
            lines.append(f"Hint: try '{most_common_action}' first if stuck; it previously coincided with reward/progress.")
        return "\n".join(lines) + "\n"
