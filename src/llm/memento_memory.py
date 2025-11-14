from __future__ import annotations

import time
from typing import Any, Dict, List, Optional


class MementoMemory:
    """
    A super-lightweight, vectorless in-memory case store.

    Each "case" is a dict like:
      {
        "ts": <unix float>,
        "step": <int>,
        "state_card": <str>,   # short textual summary / obs card
        "action": <any>,       # parsed action (tuple/str/etc.)
        "reward": <float>,     # reward signal you compute
        "progress": <float>,   # normalized progress in [0, 1]
      }
    """

    def __init__(self, capacity: int = 1024) -> None:
        self.capacity = int(max(1, capacity))
        self._cases: List[Dict[str, Any]] = []

    def __len__(self) -> int:
        return len(self._cases)

    def add_case(self, case: Dict[str, Any]) -> None:
        """Append a new case; trim to capacity."""
        if "ts" not in case:
            case["ts"] = time.time()
        self._cases.append(case)
        if len(self._cases) > self.capacity:
            # Keep most recent `capacity` cases
            self._cases = self._cases[-self.capacity :]
    
    def retrieve_recent(self, state_card: str, k: int,
                        recency_decay: float, reward_coef: float, progress_coef: float) -> List[Dict[str, Any]]:
        now = time.time()
        scored = []
        for c in self._cases:
            ts = float(c.get("ts", now))
            age_s = max(0.0, now - ts)
            rec = recency_decay ** (age_s / 5.0)  # decay ~ every 5s; tune as needed
            rew = float(c.get("reward", 0.0))
            prog = float(c.get("progress", 0.0))
            score = rec * (reward_coef * rew + progress_coef * prog)
            scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:max(0, k)]]

    # ---- simple retrieval -------------------------------------------------

    @staticmethod
    def _tokenize(s: str) -> List[str]:
        return [t for t in (s or "").lower().replace("\n", " ").split() if t]

    @classmethod
    def _jaccard(cls, a: str, b: str) -> float:
        aa, bb = set(cls._tokenize(a)), set(cls._tokenize(b))
        if not aa or not bb:
            return 0.0
        inter = len(aa & bb)
        union = len(aa | bb)
        return float(inter) / float(union)

    def retrieve_recent(
        self,
        state_card: str,
        k: int = 3,
        recency_decay: float = 0.997,
        reward_coef: float = 0.5,
        progress_coef: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Score = sim_weight * jaccard(state) + recency_weight + reward/progress terms.

        We keep this intentionally simple so it's deterministic and fast.
        """
        n = len(self._cases)
        if n == 0 or k <= 0:
            return []

        # Cheap normalization helpers
        def clip01(x: float) -> float:
            if x != x:  # NaN
                return 0.0
            return 0.0 if x < 0 else (1.0 if x > 1.0 else float(x))

        scored: List[tuple[float, Dict[str, Any]]] = []
        for idx, c in enumerate(self._cases):
            age = n - idx  # 1 for newest, grows older with smaller idx
            rec = recency_decay ** age

            r = clip01(float(c.get("reward", 0.0)))
            p = clip01(float(c.get("progress", 0.0)))

            sim = self._jaccard(state_card or "", str(c.get("state_card", "")))
            # Small weight for similarity so reward/progress still matter
            sim_weight = 0.25
            score = (sim_weight * sim) + rec + (reward_coef * r) + (progress_coef * p)

            scored.append((score, c))

        scored.sort(key=lambda t: t[0], reverse=True)
        return [c for _, c in scored[:k]]
