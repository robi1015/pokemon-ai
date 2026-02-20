# gunshi/warroom.py
# -*- coding: utf-8 -*-
import streamlit as st
from .enemy import add_move
from .storage import save_enemy_memory


def set_warroom_draft(text: str):
    """入力欄へ入れたい文章を一旦 draft に積み、次のrerunで反映する（安全）"""
    text = (text or "").strip()
    if not text:
        return
    st.session_state.war_room_draft = text
    st.toast("✍️ 入力欄にセットしました（送信は未実行）", icon="✍️")
    st.rerun()


def apply_move_set_only(mon: str, move: str):
    move = (move or "").strip()
    if not mon or mon in ("(未選択)", "(なし)") or not move:
        return

    add_move(mon, move)
    save_enemy_memory()

    st.session_state.target_mon = mon
    st.session_state.mem_target_mon = mon

    set_warroom_draft(f"{mon}が{move}を使った")
