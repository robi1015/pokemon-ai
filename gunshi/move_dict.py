# -*- coding: utf-8 -*-
"""技の予測変換（辞書）

- data/moves_ja.json を読み込んで候補にする。
- ファイルが無い/壊れている場合は空リストで安全に動作。

フォーマット: JSON配列
  ["まもる", "ステルスロック", ...]
"""

from __future__ import annotations

import json
from typing import List

import streamlit as st

from .constants import MOVES_DICT_FILE


@st.cache_data(show_spinner=False)
def load_move_dict() -> List[str]:
    try:
        with open(MOVES_DICT_FILE, "r", encoding="utf-8") as f:
            arr = json.load(f) or []
        if not isinstance(arr, list):
            return []
        out = []
        seen = set()
        for x in arr:
            if isinstance(x, str):
                s = x.strip()
                if s and s not in seen:
                    out.append(s)
                    seen.add(s)
        return out
    except Exception:
        return []
