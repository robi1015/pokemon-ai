# gunshi/ui_style.py
# -*- coding: utf-8 -*-
import streamlit as st

def inject_css():
    st.markdown(
        """
<style>
/* 全体の最大幅（ワイドでも読みやすく） */
.block-container{
    max-width: 1200px;
    padding-top: 1.2rem;
    padding-bottom: 2.0rem;
}

/* 見出しの余白を詰める（iPadで縦が伸びすぎるのを抑える） */
h1, h2, h3{
    margin-top: 0.2rem !important;
    margin-bottom: 0.6rem !important;
}

/* セクションっぽいカード（Streamlit標準の白箱を強調） */
div[data-testid="stVerticalBlockBorderWrapper"]{
    border-radius: 14px;
    border: 1px solid rgba(49, 51, 63, 0.12);
    background: rgba(255,255,255,0.92);
}

/* ボタンを少し大きく、押しやすく */
.stButton > button{
    border-radius: 12px;
    padding: 0.55rem 0.9rem;
    font-weight: 600;
}

/* サイドバーを見やすく */
section[data-testid="stSidebar"]{
    padding-top: 0.8rem;
}
section[data-testid="stSidebar"] .block-container{
    padding-top: 0.6rem;
}

/* モバイル/タブレット最適化 */
@media (max-width: 900px){
    .block-container{
        padding-left: 0.9rem;
        padding-right: 0.9rem;
    }
    /* タブの文字が詰まるのを少し緩和 */
    button[role="tab"]{
        padding: 0.35rem 0.6rem !important;
    }
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
            "確定1発": ("GUARANTEED_KO", "有利対面。迷わず攻め手。", "#c0392b", "🔥"),
        }
        return mapping.get(dmg_feel_str, ("UNKNOWN", "状況不明", "gray", "❓"))