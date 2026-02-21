# app.py
# -*- coding: utf-8 -*-
import streamlit as st
from gunshi.ui_style import inject_css
from gunshi.storage import init_session_and_load
from gunshi.ui_battle import render_battle_tab
from gunshi.ui_team import render_team_tab
from gunshi.enemy import reset_battle
from gunshi.constants import APP_TITLE

st.set_page_config(page_title=APP_TITLE, layout="wide")
inject_css()

# セッション初期化 + ファイル読込
init_session_and_load()

# Sidebar
with st.sidebar:
    st.title("⚙️ 設定")
    st.session_state.api_key = st.text_input(
        "Gemini APIキー",
        type="password",
        value=st.session_state.api_key,
    )

    st.session_state.vision_model = st.selectbox(
        "モデル（画像はPro推奨）",
        ["gemini-2.5-pro", "gemini-2.5-flash"],
        index=0 if st.session_state.vision_model == "gemini-2.5-pro" else 1,
    )

    st.divider()
    if st.button("🗑️ 対戦リセット", type="primary"):
        reset_battle()
        st.rerun()

    from gunshi.ai_client import has_bayes_engine
    if has_bayes_engine():
        st.success("✅ ベイズエンジン稼働中")
    else:
        st.warning("⚠️ bayesian_engine.py 未検出（なくても動作します）")

    st.divider()
    st.subheader("📋 My Team（保存済み）")
    from gunshi.team_parser import load_my_team
    team = load_my_team()

    if not team:
        st.caption("未登録（📝 チーム管理で貼り付け）")
    else:
        for i in range(1, 7):
            p = team.get(str(i), {}) or {}
            if p.get("name"):
                st.markdown(f"**#{i} {p['name']}**  @{p.get('item','--')}")

tab_battle, tab_team = st.tabs(["⚔️ 実戦ナビ", "📝 チーム管理"])
with tab_battle:
    render_battle_tab()
with tab_team:
    render_team_tab()