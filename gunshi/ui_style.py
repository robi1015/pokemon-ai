# gunshi/ui_style.py
# -*- coding: utf-8 -*-
import streamlit as st


def inject_css():
    st.markdown(
        """
<style>
/* 全体の余白を少し詰める（iPadで表示密度UP） */
.block-container { padding-top: 1.0rem; padding-bottom: 1.5rem; }

/* 見出しの間隔 */
h1, h2, h3 { margin-bottom: .4rem; }

/* サイドバーを少し見やすく */
section[data-testid="stSidebar"] { min-width: 320px; }
@media (max-width: 900px){
  section[data-testid="stSidebar"] { min-width: 260px; }
}

/* ボタンの高さを揃える */
.stButton > button { padding: .6rem .9rem; border-radius: 12px; }

/* タブの見た目を少し強調 */
button[role="tab"] { font-weight: 700; }

/* 画像アップロード枠を見やすく */
div[data-testid="stFileUploader"] section { padding: .8rem; border-radius: 14px; }

/* “カードっぽい”枠（必要なら st.markdown で class を付けて使う） */
.g-card {
  border: 1px solid rgba(49,51,63,.2);
  border-radius: 16px;
  padding: 14px 14px;
  background: rgba(255,255,255,.65);
}
</style>
        """,
        unsafe_allow_html=True,
    )


class TacticalTranslator:
    @staticmethod
    def translate_damage_feeling(dmg_feel_str: str):
        mapping = {
            "無効": ("IMMUNE", "効果なし。起点作成か交代読みへ。", "#7f8c8d", "✖️"),
            "確定耐え": ("TANKABLE", "行動保証あり。強気に動けます。", "#27ae60", "🛡️"),
            "乱数勝負": ("ROLL_DEPENDENT", "運負けのリスクあり。ケアが必要。", "#f39c12", "🎲"),
            "確定1発": ("GUARANTEED_KO", "有利対面。迷わず攻め手。", "#c0392b", "⚔️"),
        }
        return mapping.get(dmg_feel_str, ("UNKNOWN", "状況不明", "gray", "❓"))