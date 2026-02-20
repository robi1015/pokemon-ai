# gunshi/move4.py
# -*- coding: utf-8 -*-
import os
import json
import streamlit as st

from .constants import BASE_DIR, MOVE4_FILE


def _migrate_move4_from_project_root() -> None:
    """旧: project root 直下 → 新: data/ 配下へ移動（新が無い時だけ）"""
    try:
        old_path = os.path.join(BASE_DIR, "move4_buttons.json")
        if os.path.exists(old_path) and (not os.path.exists(MOVE4_FILE)):
            os.makedirs(os.path.dirname(MOVE4_FILE), exist_ok=True)
            os.replace(old_path, MOVE4_FILE)
    except Exception:
        pass


def _atomic_json_dump(path: str, data, *, ensure_ascii=False, indent=2):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
    os.replace(tmp, path)


def load_move4_db():
    """session_state.move4_db をロード"""
    _migrate_move4_from_project_root()
    if "move4_db" not in st.session_state:
        st.session_state.move4_db = {}

    if os.path.exists(MOVE4_FILE):
        try:
            with open(MOVE4_FILE, "r", encoding="utf-8") as f:
                st.session_state.move4_db = json.load(f) or {}
        except Exception:
            st.session_state.move4_db = {}
    else:
        st.session_state.move4_db = {}


def save_move4_db():
    if "move4_db" not in st.session_state:
        st.session_state.move4_db = {}
    try:
        _atomic_json_dump(MOVE4_FILE, st.session_state.move4_db, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_move4(mon: str) -> list[str]:
    arr = (st.session_state.get("move4_db", {}).get(mon) or [])
    arr = [a.strip() for a in arr if isinstance(a, str) and a.strip()]
    return (arr + [""] * 4)[:4]


def set_move4(mon: str, arr4: list[str]):
    arr4 = [((a or "").strip()) for a in arr4]
    arr4 = [a for a in arr4 if a]
    st.session_state.move4_db[mon] = arr4[:4]
    save_move4_db()
