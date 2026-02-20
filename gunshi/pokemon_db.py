# gunshi/pokemon_db.py
# -*- coding: utf-8 -*-
"""ポケモン名リストと、検出名の正規化（ゆるめ）

目的:
- 画像解析/手入力で出てきたポケモン名を DEFAULT_POKEMON_LIST に寄せる
- 「パルデアのすがた」等の表記ゆれを吸収する（最低限）
"""

from __future__ import annotations

import json
import os
import re
from typing import List, Tuple

from .constants import POKEMON_META_DB_FILE


def _load_meta_db() -> dict:
    try:
        if os.path.exists(POKEMON_META_DB_FILE):
            with open(POKEMON_META_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}


_META_DB = _load_meta_db()


def load_pokemon_list() -> list[str]:
    # DBのキーを基本リストにする
    names = [k for k in _META_DB.keys() if isinstance(k, str) and k.strip()]
    names = sorted(set(names))
    return names


DEFAULT_POKEMON_LIST: list[str] = load_pokemon_list()


# ---------------------------------------------------------
# 表記ゆれ吸収（必要に応じて追加してOK）
# ---------------------------------------------------------
_ALIAS: dict[str, str] = {
    # 「ドオー」はパルデア固有。ユーザーが「パルデアドオー」と書いても通す
    "パルデアドオー": "ドオー",
    "パルデアのすがたドオー": "ドオー",
    # 「ウパー」は地域フォーム表記が出やすい（統一してウパーに寄せる）
    "パルデアウパー": "ウパー",
    "パルデアのすがたウパー": "ウパー",
    # 余計な装飾を落とした後に当たるケースが多い
}


def _normalize_raw_name(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    # 全角/半角スペースを除去
    s = re.sub(r"\s+", "", s)
    # よくある接頭辞/接尾辞
    s = s.replace("のすがた", "")
    s = s.replace("（パルデア）", "").replace("(パルデア)", "")
    s = s.replace("（ガラル）", "").replace("(ガラル)", "")
    s = s.replace("（ヒスイ）", "").replace("(ヒスイ)", "")
    # 「パルデアのすがた○○」みたいなのを「パルデア○○」→ alias or prefix除去で扱う
    s = s.replace("パルデアのすがた", "パルデア")
    s = s.replace("ガラルのすがた", "ガラル")
    s = s.replace("ヒスイのすがた", "ヒスイ")
    # 末尾の句読点など
    s = re.sub(r"[！!？?。、．,.・]$", "", s)
    return s


def _try_match(name: str, allowed: list[str]) -> tuple[str | None, str | None]:
    """allowed に寄せる。戻り: (fixed, warning)"""
    if not name:
        return None, None

    # 1) 完全一致
    if name in allowed:
        return name, None

    # 2) alias
    if name in _ALIAS and _ALIAS[name] in allowed:
        return _ALIAS[name], None

    # 3) 「パルデア」「ガラル」「ヒスイ」接頭辞を落として一致させる（DBに地域フォームが無い場合の救済）
    for prefix in ("パルデア", "ガラル", "ヒスイ"):
        if name.startswith(prefix):
            cand = name[len(prefix):]
            if cand in allowed:
                return cand, f"⚠️ {name} → {cand} に寄せました（地域フォームの個別DBが未対応）"
            if cand in _ALIAS and _ALIAS[cand] in allowed:
                return _ALIAS[cand], f"⚠️ {name} → {_ALIAS[cand]} に寄せました（地域フォームの個別DBが未対応）"

    # 4) 近似（部分一致が1件だけなら寄せる）
    hits = [a for a in allowed if a == name or a.startswith(name) or name.startswith(a)]
    hits = list(dict.fromkeys(hits))
    if len(hits) == 1:
        return hits[0], f"⚠️ {name} → {hits[0]} に補正しました"

    return None, f"⚠️ 不明: {name}"


def normalize_detected_names(detected: List[str], allowed: List[str]) -> Tuple[List[str], List[str]]:
    """検出名リストを allowed に寄せる。"""
    fixed: list[str] = []
    warns: list[str] = []

    allowed = allowed or DEFAULT_POKEMON_LIST

    for raw in detected or []:
        n = _normalize_raw_name(raw)
        if not n:
            continue
        f, w = _try_match(n, allowed)
        if f:
            fixed.append(f)
        if w:
            warns.append(w)

    # 重複除去（順序維持）
    out: list[str] = []
    seen = set()
    for x in fixed:
        if x not in seen:
            out.append(x)
            seen.add(x)

    return out, warns
