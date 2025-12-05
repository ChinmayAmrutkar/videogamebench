from typing import List, Dict, Any, Optional, Tuple
import numpy as np

# Optional FAISS: we’ll fall back to NumPy search if it isn’t available
try:
    import faiss  # type: ignore
    _HAS_FAISS = True
except Exception:
    _HAS_FAISS = False

# Sentence-Transformers for embeddings
from sentence_transformers import SentenceTransformer


def _l2norm(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=1, keepdims=True) + 1e-12
    return x / n


class EmbeddingMemory:
    """
    Lightweight vector memory for short text snippets (observations, summaries).
    Provides add(), search(), and loop_detect().
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        max_items: int = 5000,
        use_faiss: bool = False,  # default False for easier setup on macOS
    ):
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()
        self.max_items = max_items
        self.use_faiss = bool(use_faiss and _HAS_FAISS)

        self.texts: List[str] = []
        self.metas: List[Dict[str, Any]] = []
        self.vecs: Optional[np.ndarray] = None
        self.index = faiss.IndexFlatIP(self.dim) if self.use_faiss else None

    # -------------------- core ops --------------------

    def encode(self, texts: List[str]) -> np.ndarray:
        vecs = self.model.encode(texts, normalize_embeddings=True)
        return vecs.astype("float32")

    def add(self, texts: List[str], metas: List[Dict[str, Any]]) -> None:
        assert len(texts) == len(metas)
        new_vecs = self.encode(texts)

        self.texts.extend(texts)
        self.metas.extend(metas)
        self.vecs = new_vecs if self.vecs is None else np.vstack([self.vecs, new_vecs])

        if self.use_faiss:
            self.index.add(new_vecs)

        # cap memory
        if len(self.texts) > self.max_items:
            keep = slice(-self.max_items, None)
            self.texts = self.texts[keep]
            self.metas = self.metas[keep]
            self.vecs = self.vecs[keep, :]
            if self.use_faiss:
                self.index = faiss.IndexFlatIP(self.dim)
                self.index.add(self.vecs)

    def search(self, query: str, k: int = 5) -> List[Tuple[str, Dict[str, Any], float]]:
        if not self.texts:
            return []

        q = self.encode([query])
        if self.use_faiss:
            D, I = self.index.search(q, max(k, 1))
            out: List[Tuple[str, Dict[str, Any], float]] = []
            for j, i in enumerate(I[0]):
                if i != -1:
                    out.append((self.texts[i], self.metas[i], float(D[0][j])))
            return out

        # NumPy fallback
        V = _l2norm(self.vecs)  # type: ignore[arg-type]
        sims = (V @ q.T).ravel()
        idx = np.argsort(-sims)[:k]
        return [(self.texts[i], self.metas[i], float(sims[i])) for i in idx]

    def loop_detect(self, current_text: str, recent: int = 6, thresh: float = 0.985) -> bool:
        """
        True if current state is extremely similar to any of last `recent` states.
        """
        if self.vecs is None or len(self.texts) < 2:
            return False

        q = self.encode([current_text])[0]  # normalized
        V = self.vecs[-recent:, :] if recent > 0 else self.vecs
        sims = (V @ q).ravel()
        return bool((sims >= thresh).any())