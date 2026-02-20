# gunshi/ui_style.py
# -*- coding: utf-8 -*-
import streamlit as st


def inject_css():
    st.markdown(
        """
<style>
/* Buttons */
.stButton>button { width: 100%; height: 3rem; font-weight: 700; border-radius: 10px; }
.smallbtn .stButton>button { height: 2.4rem; }

/* Card */
.card {
  border: 2px solid rgba(255,255,255,0.12);
  border-radius: 14px;
  padding: 12px 14px;
  background: rgba(255,255,255,0.03);
  margin-bottom: 10px;
}
.card-title { font-weight: 800; font-size: 14px; margin-bottom: 6px; opacity: 0.95; }
.card-row { font-size: 13px; opacity: 0.9; line-height: 1.5; }
.badge {
  display:inline-block; padding: 2px 8px; border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.18); font-size: 12px; margin-right: 6px;
}
.hl-target { border-color: rgba(255,215,0,0.65) !important; }
.hl-memo   { border-color: rgba(0,200,255,0.65) !important; }
.muted { opacity: 0.72; }
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
            "確定1発": ("GUARANTEED_KO", "有利対面。迷わず攻め手。", "#c0392b", "💀"),
        }
        return mapping.get(dmg_feel_str, ("UNKNOWN", "状況不明", "gray", "❓"))
