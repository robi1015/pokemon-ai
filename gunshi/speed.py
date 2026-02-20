# gunshi/speed.py
# -*- coding: utf-8 -*-
"""素早さ計算ユーティリティ（SV想定・Lv50デフォルト）

UIからも呼べるように副作用なしの純関数で実装。
"""

from __future__ import annotations

import json
import os
from functools import lru_cache

from .constants import DB_FILE


def nature_multiplier(nature: str) -> float:
    """性格補正（S）

    nature:
      "↑" 速度↑（おくびょう等）
      "↓" 速度↓（ゆうかん等）
      "-" 変化なし
    """
    if nature == "↑":
        return 1.1
    if nature == "↓":
        return 0.9
    return 1.0


def calc_speed_stat(base: int, iv: int, ev: int, level: int = 50, nature: str = "-") -> int:
    """ポケモンSVの実数値（素早さ）

    stat = floor((floor((2*base + iv + floor(ev/4)) * level/100) + 5) * nature)
    """
    base = int(base)
    iv = max(0, min(31, int(iv)))
    ev = max(0, min(252, int(ev)))
    level = int(level)

    x = (2 * base + iv + (ev // 4))
    y = (x * level) // 100
    stat = y + 5
    stat = int(stat * nature_multiplier(nature))  # floor相当
    return stat


def apply_modifiers(speed: int, scarf: bool = False, para: bool = False, tailwind: bool = False, stage: int = 0) -> int:
    """補正込みの実効Sを返す

    - こだわりスカーフ: *1.5
    - まひ: *0.5 (SV)
    - おいかぜ: *2
    - ランク補正: stage -6..+6
    """
    s = int(speed)

    stage = max(-6, min(6, int(stage)))
    if stage >= 0:
        s = (s * (2 + stage)) // 2
    else:
        s = (s * 2) // (2 + (-stage))

    if scarf:
        s = int(s * 1.5)
    if para:
        s = int(s * 0.5)
    if tailwind:
        s = int(s * 2.0)

    return s


@lru_cache(maxsize=1)
def _load_meta_db(db_path: str) -> dict:
    if not db_path or (not os.path.exists(db_path)):
        return {}
    with open(db_path, "r", encoding="utf-8") as f:
        return json.load(f) or {}


def get_base_speed_from_db(mon: str, db_path: str = DB_FILE) -> int | None:
    """pokemon_meta_db.json から base Speed を引く（なければ None）。

    追加仕様:
    - "パルデアウパー" / "ヒスイ○○" / "ガラル○○" / "アローラ○○" みたいな入力は
      プレフィックス・ノイズを落として再検索する（DBが通常名しかない場合の救済）。
    """
    name = (mon or "").strip()
    if not name:
        return None

    db = _load_meta_db(db_path)

    def _lookup(n: str) -> int | None:
        info = db.get(n)
        if not isinstance(info, dict):
            return None
        bs = info.get("base_stats")
        if not isinstance(bs, dict):
            return None
        spd = bs.get("spe")
        try:
            return int(spd)
        except Exception:
            return None

    hit = _lookup(name)
    if hit is not None:
        return hit

    # regional prefix cleanup
    cleaned = name
    for pref in ("パルデア", "ヒスイ", "ガラル", "アローラ"):
        if cleaned.startswith(pref):
            cleaned = cleaned[len(pref):].lstrip(" -_　")
            break
    cleaned = cleaned.replace("のすがた", "").replace("の姿", "")
    cleaned = cleaned.replace("(パルデア)", "").replace("（パルデア）", "")
    cleaned = cleaned.replace("(ヒスイ)", "").replace("（ヒスイ）", "")
    cleaned = cleaned.replace("(ガラル)", "").replace("（ガラル）", "")
    cleaned = cleaned.replace("(アローラ)", "").replace("（アローラ）", "")
    cleaned = cleaned.strip()

    return _lookup(cleaned)
