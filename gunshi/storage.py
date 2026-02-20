# gunshi/storage.py
# -*- coding: utf-8 -*-
import os, json
import streamlit as st
from .constants import (
    BASE_DIR,
    ENEMY_MEM_FILE,
    ENEMY_STATE_FILE,
    MOVE4_FILE,
    MY_TEAM_NOTES_FILE,
)

def atomic_json_dump(path: str, data, *, ensure_ascii=False, indent=2):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
    os.replace(tmp, path)


def _migrate_from_project_root(old_filename: str, new_path: str) -> None:
    """旧: project root 直下 → 新: data/ 配下へ移動（新が無い時だけ）"""
    try:
        old_path = os.path.join(BASE_DIR, old_filename)
        if os.path.exists(old_path) and (not os.path.exists(new_path)):
            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            os.replace(old_path, new_path)
    except Exception:
        pass

def init_session_defaults():
    if "api_key" not in st.session_state: st.session_state.api_key = ""
    if "vision_model" not in st.session_state: st.session_state.vision_model = "gemini-2.5-pro"

    if "probs" not in st.session_state: st.session_state.probs = {}
    if "prev_probs" not in st.session_state: st.session_state.prev_probs = {}

    if "enemy_party" not in st.session_state: st.session_state.enemy_party = []
    if "target_mon" not in st.session_state: st.session_state.target_mon = "(なし)"
    if "mem_target_mon" not in st.session_state: st.session_state.mem_target_mon = "(未選択)"

    if "enemy_memory" not in st.session_state: st.session_state.enemy_memory = {}
    if "enemy_state" not in st.session_state: st.session_state.enemy_state = {}

    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    if "battle_log" not in st.session_state: st.session_state.battle_log = []

    if "turn_no" not in st.session_state: st.session_state.turn_no = 0
    if "turn_log" not in st.session_state: st.session_state.turn_log = []

    if "last_uploaded_file" not in st.session_state: st.session_state.last_uploaded_file = None

    if "move4_db" not in st.session_state: st.session_state.move4_db = {}

    if "war_room_input" not in st.session_state: st.session_state.war_room_input = ""

    if "pending_ai_prompt" not in st.session_state: st.session_state.pending_ai_prompt = ""
    if "pending_ai_image_bytes" not in st.session_state: st.session_state.pending_ai_image_bytes = None

def load_enemy_memory():
    _migrate_from_project_root("enemy_memory.json", ENEMY_MEM_FILE)
    if not os.path.exists(ENEMY_MEM_FILE):
        return
    try:
        with open(ENEMY_MEM_FILE, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        st.session_state.enemy_memory = data if isinstance(data, dict) else {}
    except Exception:
        st.session_state.enemy_memory = {}

def save_enemy_memory():
    try:
        atomic_json_dump(ENEMY_MEM_FILE, st.session_state.enemy_memory, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"⚠️ enemy_memory保存失敗: {e}")

def load_enemy_state():
    _migrate_from_project_root("enemy_state.json", ENEMY_STATE_FILE)
    if not os.path.exists(ENEMY_STATE_FILE):
        return
    try:
        with open(ENEMY_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        st.session_state.enemy_state = data if isinstance(data, dict) else {}
    except Exception:
        st.session_state.enemy_state = {}

def save_enemy_state():
    try:
        atomic_json_dump(ENEMY_STATE_FILE, st.session_state.enemy_state, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"⚠️ enemy_state保存失敗: {e}")

def load_move4_db():
    if not os.path.exists(MOVE4_FILE):
        st.session_state.move4_db = {}
        return
    try:
        with open(MOVE4_FILE, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        st.session_state.move4_db = data if isinstance(data, dict) else {}
    except Exception:
        st.session_state.move4_db = {}

def save_move4_db():
    try:
        atomic_json_dump(MOVE4_FILE, st.session_state.move4_db, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"⚠️ move4保存失敗: {e}")

def init_session_and_load():
    init_session_defaults()
    if "mem_loaded" not in st.session_state:
        st.session_state.mem_loaded = True
        load_enemy_memory()
        load_enemy_state()
        load_move4_db()


# =========================================================
# My Team Notes (roles/usage) for AI
# =========================================================

@st.cache_data(show_spinner=False)
def _load_my_team_notes_cached(_mtime: float) -> dict:
    if not os.path.exists(MY_TEAM_NOTES_FILE):
        return {}
    with open(MY_TEAM_NOTES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f) or {}
    return data if isinstance(data, dict) else {}

def load_my_team_notes() -> dict:
    """自分のパーティの役割/立ち回りメモ（AIへ渡す用）。mtimeでキャッシュ制御。"""
    _migrate_from_project_root("my_team_notes.json", MY_TEAM_NOTES_FILE)
    mtime = os.path.getmtime(MY_TEAM_NOTES_FILE) if os.path.exists(MY_TEAM_NOTES_FILE) else 0
    try:
        return _load_my_team_notes_cached(mtime)
    except Exception:
        return {}
def save_my_team_notes(notes: dict) -> None:
    """notes: {pokemon_name: "text"} を保存"""
    if not isinstance(notes, dict):
        notes = {}
    fixed = {}
    for k, v in notes.items():
        if not isinstance(k, str):
            continue
        s = ("" if v is None else str(v)).strip()
        if s:
            fixed[k.strip()] = s
    try:
        atomic_json_dump(MY_TEAM_NOTES_FILE, fixed, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"⚠️ my_team_notes保存失敗: {e}")