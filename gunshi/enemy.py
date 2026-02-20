# gunshi/enemy.py
# -*- coding: utf-8 -*-
import streamlit as st
from .constants import ITEM_ALIAS, ENEMY_MEM_FILE, ENEMY_STATE_FILE
from .storage import save_enemy_memory, save_enemy_state

def normalize_item(s: str) -> str:
    s = (s or "").strip()
    return ITEM_ALIAS.get(s, s)

def ensure_enemy_profile(em: dict) -> dict:
    prof = em.setdefault("profile", {})
    prof.setdefault("type", "?")
    prof.setdefault("ability", "-")
    prof.setdefault("nature", "-")
    prof.setdefault("evs", "-")
    prof.setdefault("ivs", "-")
    # 速度メモ（最速/準速/無振り など）
    prof.setdefault("speed_tier", "-")
    prof.setdefault("speed_raw", "-")   # Lv50実数値S
    prof.setdefault("speed_eff", "-")   # 補正込み実効S（任意）
    return prof

def get_enemy_mem(mon: str) -> dict:
    em = st.session_state.enemy_memory.setdefault(mon, {"item": "", "moves": [], "tera": "", "profile": {}})
    moves = em.get("moves") or []
    if isinstance(moves, set):
        moves = list(sorted(moves))
    em["moves"] = (moves or [])[:4]
    em.setdefault("item", "")
    em.setdefault("tera", "")
    ensure_enemy_profile(em)
    return em

def set_profile_field(mon: str, k: str, v: str):
    em = get_enemy_mem(mon)
    prof = ensure_enemy_profile(em)
    prof[k] = (v or "").strip() if v is not None else prof.get(k, "-")

def add_move(mon: str, move: str) -> tuple[bool, str]:
    move = (move or "").strip()
    if not move:
        return False, ""
    em = get_enemy_mem(mon)
    moves = em["moves"]
    if move in moves:
        return False, f"{mon} の技「{move}」は既に登録済み"
    if len(moves) >= 4:
        return False, f"{mon} の技は既に4つ登録済み（上限）"
    moves.append(move)
    em["moves"] = moves[:4]
    return True, f"{mon} に技「{move}」を登録"

def replace_move(mon: str, old_move: str, new_move: str) -> tuple[bool, str]:
    new_move = (new_move or "").strip()
    old_move = (old_move or "").strip()
    if not new_move or not old_move:
        return False, ""
    em = get_enemy_mem(mon)
    moves = em["moves"]
    if new_move in moves:
        return False, f"{mon} の技「{new_move}」は既に登録済み"
    if old_move not in moves:
        return False, f"{mon} の技「{old_move}」が見つからない"
    idx = moves.index(old_move)
    moves[idx] = new_move
    em["moves"] = moves[:4]
    return True, f"{mon} の技「{old_move}」→「{new_move}」に置換"

def set_item_locked(mon: str, item: str) -> tuple[bool, str]:
    item = normalize_item(item)
    if not item:
        return False, ""
    em = get_enemy_mem(mon)
    current = (em.get("item") or "").strip()
    if current and current != item:
        return False, f"{mon} の持ち物は既に「{current}」で確定済み（上書き禁止）"
    em["item"] = item
    return True, f"{mon} の持ち物を「{item}」で確定"

def clear_item(mon: str):
    em = get_enemy_mem(mon)
    em["item"] = ""

def get_enemy_state(mon: str) -> dict:
    stt = st.session_state.enemy_state.setdefault(
        mon, {"hp": 100, "status": "", "alive": True, "tera_used": False, "tera_type": ""}
    )
    stt.setdefault("hp", 100)
    stt.setdefault("status", "")
    stt.setdefault("alive", True)
    stt.setdefault("tera_used", False)
    stt.setdefault("tera_type", "")
    try:
        stt["hp"] = max(0, min(100, int(stt["hp"])))
    except Exception:
        stt["hp"] = 100
    return stt

def log_event(text: str):
    st.session_state.turn_log.append({"t": st.session_state.turn_no, "text": text})
    st.session_state.turn_log = st.session_state.turn_log[-200:]

def reset_battle():
    st.session_state.probs = {}
    st.session_state.prev_probs = {}
    st.session_state.enemy_party = []
    st.session_state.chat_history = []
    st.session_state.battle_log = []
    st.session_state.enemy_memory = {}
    st.session_state.enemy_state = {}
    st.session_state.target_mon = "(なし)"
    st.session_state.mem_target_mon = "(未選択)"
    st.session_state.turn_no = 0
    st.session_state.turn_log = []
    st.session_state.last_uploaded_file = None
    st.session_state.war_room_input = ""
    st.session_state.pending_ai_prompt = ""
    st.session_state.pending_ai_image_bytes = None
    st.toast("🗑️ 戦況をリセットしました", icon="🔥")
