# app.py
# -*- coding: utf-8 -*-
import os
import streamlit as st

from gunshi.ui_style import inject_css
from gunshi.storage import init_session_and_load
from gunshi.ui_battle import render_battle_tab
from gunshi.ui_team import render_team_tab
from gunshi.enemy import reset_battle
from gunshi.constants import APP_TITLE


def get_secret(name: str, default: str = "") -> str:
    # Streamlit Community Cloud: st.secrets
    if hasattr(st, "secrets") and name in st.secrets:
        return str(st.secrets.get(name, default) or default)
    # その他（ローカル等）: 環境変数
    return os.getenv(name, default)


st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
    initial_sidebar_state="collapsed",  # iPad/スマホで最初邪魔にならない
)
inject_css()

# セッション初期化 + ファイル読込
init_session_and_load()

# api_key が未初期化なら secrets から入れる
if "api_key" not in st.session_state or not st.session_state.api_key:
    st.session_state.api_key = get_secret("GEMINI_API_KEY", "")

# Sidebar
with st.sidebar:
    st.title("⚙️ 設定")

    st.session_state.api_key = st.text_input(
        "Gemini APIキー",
        type="password",
        value=st.session_state.api_key,
        placeholder="Secretsに入れると毎回不要",
    )

    st.session_state.vision_model = st.selectbox(
        "モデル（画像はPro推奨）",
        ["gemini-2.5-pro", "gemini-2.5-flash"],
        index=0 if st.session_state.vision_model == "gemini-2.5-pro" else 1,
    )

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ 対戦リセット", type="primary", use_container_width=True):
            reset_battle()
            st.rerun()
    with col2:
        # 将来用の空ボタン枠（必要なら何か入れる）
        st.button(" ", disabled=True, use_container_width=True)

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