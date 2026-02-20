# gunshi/ui_speed.py
# -*- coding: utf-8 -*-
"""素早さ比較UI（ガチ）

- Lvは敵味方とも 50 固定
- 名前を入れると DB から種族値Sを自動入力
- 自分側は team 管理（data/my_team.json）から選択できる
"""

from __future__ import annotations

import json
import os
import streamlit as st

from .constants import TEAM_FILE
from .speed import calc_speed_stat, apply_modifiers, get_base_speed_from_db


def _load_my_team_names() -> list[str]:
    names: list[str] = []
    try:
        if os.path.exists(TEAM_FILE):
            with open(TEAM_FILE, "r", encoding="utf-8") as f:
                team = json.load(f) or {}
            # 形式: {"1": {"name": "..."}, ...}
            for slot in sorted(team.keys(), key=lambda x: int(x) if str(x).isdigit() else 999):
                p = team.get(slot) or {}
                nm = (p.get("name") or "").strip()
                if nm:
                    names.append(nm)
    except Exception:
        pass
    # 先頭に空選択
    return ["-"] + sorted(dict.fromkeys(names))


def _stat_block(prefix: str, label: str, default_name: str = "") -> dict:
    """1体分の入力UI"""
    st.markdown(f"#### {label}")

    name = st.text_input("ポケモン名（入力するとS種族値を自動）", value=default_name, key=f"{prefix}_name").strip()

    # base speed auto-fill
    base_guess = get_base_speed_from_db(name) or 0
    base_key = f"{prefix}_base"
    if base_guess and st.session_state.get(base_key) in (None, 0, ""):
        # 初回だけ自動で入れる（ユーザーの手入力を上書きしない）
        st.session_state[base_key] = int(base_guess)

    c1, c2, c3 = st.columns(3)
    base = c1.number_input("種族値S", min_value=0, max_value=255, value=int(st.session_state.get(base_key, base_guess or 0)), step=1, key=base_key)
    iv = c2.number_input("IV", min_value=0, max_value=31, value=31, step=1, key=f"{prefix}_iv")
    ev = c3.number_input("EV", min_value=0, max_value=252, value=252, step=4, key=f"{prefix}_ev")

    c4, c5, c6, c7 = st.columns(4)
    nature = c4.selectbox("性格補正", ["-", "↑", "↓"], index=0, key=f"{prefix}_nat")
    scarf = c5.checkbox("スカーフ", value=False, key=f"{prefix}_scarf")
    para = c6.checkbox("まひ", value=False, key=f"{prefix}_para")
    tailwind = c7.checkbox("おいかぜ", value=False, key=f"{prefix}_tail")

    stage = st.slider("Sランク", -6, 6, 0, 1, key=f"{prefix}_stage")

    # Lv固定
    level = 50

    raw = calc_speed_stat(base=base, iv=iv, ev=ev, level=level, nature=nature) if base else 0
    eff = apply_modifiers(raw, scarf=scarf, para=para, tailwind=tailwind, stage=stage) if raw else 0

    return {"name": name, "base": int(base), "raw": int(raw), "eff": int(eff)}


def render_speed_ui(default_my: str = "", default_enemy: str = "") -> None:
    """Speed Compare UI (Lv50固定)"""
    st.caption("Lvは敵味方とも50固定。名前を入れるとDBから種族値Sが自動で入ります。")

    # 自分側は team から選択もできる
    team_names = _load_my_team_names()
    if team_names and team_names != ["-"]:
        pick = st.selectbox("自分のポケモン（team管理から選択）", team_names, index=0, key="speed_my_pick")
        if pick != "-":
            default_my = pick

    colA, colB = st.columns(2)
    with colA:
        me = _stat_block("spd_me", "自分", default_name=default_my)
    with colB:
        en = _stat_block("spd_en", "相手", default_name=default_enemy)

    # 入力した相手名をメモ対象に追従（ユーザー要望）
    if en.get("name"):
        st.session_state.mem_target_mon = en["name"]
        # 対面が未設定なら一緒に更新
        if st.session_state.get("target_mon") in (None, "(なし)"):
            st.session_state.target_mon = en["name"]

    if me["eff"] and en["eff"]:
        if me["eff"] > en["eff"]:
            verdict = "✅ 上を取れる"
        elif me["eff"] < en["eff"]:
            verdict = "❌ 下"
        else:
            verdict = "⚠️ 同速"

        st.success(f"{verdict}（自分 {me['eff']} vs 相手 {en['eff']}）")
    else:
        st.info("両方の種族値Sを入れると比較できます（名前入力で自動補完されます）")
