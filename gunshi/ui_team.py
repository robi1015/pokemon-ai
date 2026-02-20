# gunshi/ui_team.py
# -*- coding: utf-8 -*-
import streamlit as st
import time
from .team_parser import parse_showdown_text_robust, save_my_team, load_my_team
from .storage import load_my_team_notes, save_my_team_notes

def render_team_tab():
    st.subheader("📋 チーム一括登録（Showdown/Wiki貼り付け）")
    showdown_text = st.text_area("貼り付け", height=320)
    if st.button("🔄 同期して保存", type="primary"):
        if showdown_text.strip():
            parsed = parse_showdown_text_robust(showdown_text)
            try:
                save_my_team(parsed)
                st.success("保存完了！")
                st.toast("✅ サイドバーを更新しました", icon="✅")
                time.sleep(0.4)
                st.rerun()
            except Exception as e:
                st.error(f"保存失敗: {e}")

    st.divider()
    st.subheader("👀 保存済みチーム確認")
    team = load_my_team()
    if not team:
        st.caption("未登録")
    else:
        for i in range(1, 7):
            p = team.get(str(i), {}) or {}
            if p.get("name"):
                st.markdown(
                    f"- **#{i} {p['name']}** @{p.get('item','--')} / テラ:{p.get('tera','--')} / "
                    f"技:{', '.join([m for m in (p.get('moves') or []) if m])}"
                )

        st.divider()
        st.subheader("🧠 自分のパーティ：役割/立ち回りメモ（AIに渡す）")
        st.caption("ここに書いた内容は、作戦会議のプロンプトに [MY_TEAM_ROLE] として自動で添付されます。")

        notes = load_my_team_notes()
        # チームにいるポケモンだけ並べる
        names = []
        for i in range(1, 7):
            p = team.get(str(i), {}) or {}
            n = (p.get("name") or "").strip()
            if n and n not in names:
                names.append(n)

        # 編集UI
        edited = {}
        for n in names:
            with st.expander(f"✍️ {n} の役割/使い方", expanded=False):
                edited[n] = st.text_area(
                    "メモ",
                    value=(notes.get(n) or ""),
                    height=120,
                    key=f"team_note_{n}",
                    placeholder="例: 初手のステロ要員。終盤は○○で詰める。テラスは基本××…",
                )

        c1, c2 = st.columns([1, 1])
        if c1.button("💾 役割メモを保存", type="primary", use_container_width=True):
            # 既存を維持しつつ、今いるポケモン分だけ更新
            new_notes = dict(notes)
            for n, v in edited.items():
                v = (v or "").strip()
                if v:
                    new_notes[n] = v
                else:
                    new_notes.pop(n, None)
            save_my_team_notes(new_notes)
            st.toast("✅ 役割メモを保存しました", icon="✅")

        if c2.button("🧹 役割メモを全消去", use_container_width=True):
            save_my_team_notes({})
            st.toast("🧹 全消去しました", icon="🧹")
            st.rerun()
