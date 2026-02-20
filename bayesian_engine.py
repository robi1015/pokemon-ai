# bayesian_engine.py
# -*- coding: utf-8 -*-
"""Hybrid Bayesian engine (pure-Python fallback).

This file replaces the previously broken artifact that contained null bytes.
You can later swap this module with a compiled extension, as long as it
exports `HybridBayesianEngine`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import math
import os

try:
    import google.generativeai as genai  # optional
except Exception:  # pragma: no cover
    genai = None  # type: ignore


def _atomic_json_dump(path: str, data: Any, *, ensure_ascii: bool = False, indent: int = 2) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
    os.replace(tmp, path)


def _normalize(dist: Dict[str, float]) -> Dict[str, float]:
    s = sum(v for v in dist.values() if v > 0)
    if s <= 0:
        n = len(dist) or 1
        return {k: 1.0 / n for k in dist}
    return {k: (max(v, 0.0) / s) for k, v in dist.items()}


@dataclass
class HybridBayesianEngine:
    """A small, pragmatic Bayesian updater.

    - Stores per-key priors in a JSON DB.
    - Can optionally ask an LLM to propose priors (if `api_key` and genai are available).
    """

    api_key: str = ""
    db_path: Optional[str] = None

    def __post_init__(self) -> None:
        base_dir = Path(__file__).resolve().parent
        data_dir = base_dir / "data"
        data_dir.mkdir(exist_ok=True)

        self.db_file = Path(self.db_path) if self.db_path else (data_dir / "bayes_db.json")
        self.db: Dict[str, Any] = {}
        self._load_db()

        if self.api_key and genai is not None:
            try:
                genai.configure(api_key=self.api_key)
            except Exception:
                # Keep working without AI
                pass

    # ---- persistence ----
    def _load_db(self) -> None:
        if self.db_file.exists():
            try:
                self.db = json.loads(self.db_file.read_text(encoding="utf-8")) or {}
                if not isinstance(self.db, dict):
                    self.db = {}
            except Exception:
                self.db = {}
        else:
            self.db = {}

    def _save_db(self) -> None:
        try:
            _atomic_json_dump(str(self.db_file), self.db, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ---- priors ----
    def _ai_generate_priors(self, context: str, candidates: List[str]) -> Dict[str, float]:
        """Ask an LLM for a prior distribution. Falls back to uniform."""
        if not self.api_key or genai is None or not candidates:
            return {c: 1.0 / max(len(candidates), 1) for c in candidates}

        prompt = (
            "You are a Bayesian prior helper for Pokémon SV battles. "
            "Given a context and candidates, output JSON mapping candidate->probability. "
            "Probabilities must be non-negative and sum to 1.\n\n"
            f"Context:\n{context}\n\nCandidates:\n{candidates}\n\n"
            "Return JSON only."
        )
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            resp = model.generate_content(prompt)
            txt = (resp.text or "").strip()
            dist = json.loads(txt)
            if isinstance(dist, dict):
                dist = {str(k): float(v) for k, v in dist.items() if str(k) in candidates}
                if dist:
                    return _normalize(dist)
        except Exception:
            pass
        return {c: 1.0 / max(len(candidates), 1) for c in candidates}

    def get_priors(self, key: str, candidates: List[str], *, context: str = "", use_ai: bool = False) -> Dict[str, float]:
        """Get (and cache) priors for a given key and candidate set."""
        key = str(key)
        candidates = [str(c) for c in candidates if c]
        if not candidates:
            return {}

        entry = self.db.get(key)
        if isinstance(entry, dict) and "priors" in entry and isinstance(entry["priors"], dict):
            pri = {k: float(v) for k, v in entry["priors"].items() if k in candidates}
            if pri:
                return _normalize(pri)

        pri = self._ai_generate_priors(context, candidates) if use_ai else {c: 1.0 / len(candidates) for c in candidates}
        self.db[key] = {"priors": pri}
        self._save_db()
        return _normalize(pri)

    # ---- posterior ----
    def calculate_posterior(self, priors: Dict[str, float], likelihoods: Dict[str, float]) -> Dict[str, float]:
        """Compute posterior proportional to prior * likelihood."""
        post: Dict[str, float] = {}
        for h, p in priors.items():
            l = float(likelihoods.get(h, 1.0))
            # guard
            p = max(float(p), 0.0)
            l = max(l, 0.0)
            post[h] = p * l
        return _normalize(post)
