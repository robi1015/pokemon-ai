# gunshi/ai_client.py
# -*- coding: utf-8 -*-
from typing import Optional
import json
from functools import lru_cache
import streamlit as st
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from PIL import Image

from .constants import GUNSHI_SYSTEM_PROMPT
from .enemy import get_enemy_mem, get_enemy_state, ensure_enemy_profile
from .storage import load_my_team_notes
from .team_parser import load_my_team

@st.cache_resource(show_spinner=False)
def _get_gemini_model_cached(api_key: str, model_name: str, system_instruction: str):
    """Gemini modelの生成は比較的重いのでキャッシュする。"""
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name, system_instruction=system_instruction)


@lru_cache(maxsize=1)
def has_bayes_engine() -> bool:
    try:
        from bayesian_engine import HybridBayesianEngine  # noqa
        return True
    except Exception:
        return False

def format_enemy_memory(enemy_memory: dict) -> str:
    if not enemy_memory:
        return "なし"
    lines = []
    for mon, info in enemy_memory.items():
        if not isinstance(info, dict):
            continue
        prof = (info.get("profile") or {})
        item = (info.get("item") or "不明").strip()
        tera_mem = (info.get("tera") or "不明").strip()
        moves = (info.get("moves") or [])[:4]
        moves = [m for m in moves if isinstance(m, str)]
        moves_str = " / ".join([m for m in moves if m]) if any(moves) else "不明"

        stt = get_enemy_state(mon)
        hp = stt.get("hp", 100)
        status = stt.get("status") or "なし"
        alive = "生存" if stt.get("alive", True) else "瀕死"
        tera_used = "使用済" if stt.get("tera_used") else "未使用"
        tera_type = stt.get("tera_type") or "不明"

        lines.append(
            f"・{mon}: 持ち物[{item}], テラ(メモ)[{tera_mem}], テラタイプ[{tera_type}]({tera_used}), "
            f"技[{moves_str}], 状態[{status}], HP[{hp}%], {alive}, "
            f"タイプ[{(prof.get('type') or '?')}], 特性[{(prof.get('ability') or '-')}]"
            f", 性格[{(prof.get('nature') or '-')}]"
            f", 努力値[{(prof.get('evs') or '-')}]"
            f", 個体値[{(prof.get('ivs') or '-')}]"
            f", 速度[{(prof.get('speed_tier') or '-')}]"
        )
    return "\n".join(lines) if lines else "なし"

def build_action_template(target: str) -> str:
    if not target or target == "(なし)":
        return "なし"
    em = get_enemy_mem(target)
    stt = get_enemy_state(target)
    prof = ensure_enemy_profile(em)

    item = em.get("item") or "不明"
    moves = (em.get("moves") or [])[:4]
    tera_used = "使用済" if stt.get("tera_used") else "未使用"
    tera_type = stt.get("tera_type") or "不明"
    hp = stt.get("hp", 100)
    status = stt.get("status") or "なし"
    alive = "生存" if stt.get("alive", True) else "瀕死"

    return (
        f"【対面要点】相手={target} / 持ち物={item} / 技={moves if any(moves) else '不明'} / "
        f"テラタイプ={tera_type}({tera_used}) / HP={hp}% / 状態={status} / {alive} / "
        f"タイプ={prof.get('type','?')} / 特性={prof.get('ability','-')} / 性格={prof.get('nature','-')} / "
        f"努力値={prof.get('evs','-')} / 個体値={prof.get('ivs','-')} / 速度={prof.get('speed_tier','-')}\n"
        "この要点を前提に、勝ち筋を1本に絞って即断せよ。"
    )

def get_gunshi_advice(user_input: str, image: Optional[Image.Image] = None,
                      probs_context: Optional[dict] = None,
                      tactical_info=None) -> str:
    if not st.session_state.api_key:
        return "⚠️ APIキーを設定してください。"

    genai.configure(api_key=st.session_state.api_key)
    final_prompt = user_input

    enemy_mem_str = format_enemy_memory(st.session_state.get("enemy_memory", {}))
    final_prompt += (
        "\n\n[CONFIRMED INFO]\n"
        "以下は試合中に判明した確定情報。推論ではなく事実として扱え。\n"
        f"{enemy_mem_str}"
    )
    final_prompt += "\n\n[ACTION_TEMPLATE]\n" + build_action_template(st.session_state.get("target_mon", "(なし)"))

    # -------------------------------------------------
    # My Team roles / usage notes (user-written)
    # -------------------------------------------------
    try:
        team = load_my_team() or {}
        notes = load_my_team_notes() or {}
        if isinstance(team, dict) and isinstance(notes, dict) and notes:
            lines = []
            for i in range(1, 7):
                p = team.get(str(i), {}) or {}
                name = (p.get("name") or "").strip()
                if not name:
                    continue
                memo = (notes.get(name) or "").strip()
                if memo:
                    lines.append(f"・{name}: {memo}")
            if lines:
                final_prompt += "\n\n[MY_TEAM_ROLE]\n" + "\n".join(lines)
    except Exception:
        pass

    if tactical_info:
        tag, desc, _, _ = tactical_info
        final_prompt += f"\n\n[TACTICAL_SITUATION]\nSTATUS: {tag}\nMEANING: {desc}"

    if probs_context:
        final_prompt += f"\n\n[BAYESIAN_PROBABILITY]\n{json.dumps(probs_context, ensure_ascii=False)}"

    model_name = st.session_state.get("vision_model", "gemini-2.5-pro")
    model = genai.GenerativeModel(model_name, system_instruction=GUNSHI_SYSTEM_PROMPT)
    proc_image = image.convert("RGB") if image else None

    try:
        response = model.generate_content([final_prompt, proc_image] if proc_image else final_prompt)
        st.session_state.battle_log.insert(0, {"role": "AI", "text": response.text})
        st.session_state.battle_log = st.session_state.battle_log[:120]
        return response.text
    except google_exceptions.Unauthenticated:
        return "⛔ 【認証エラー】APIキーを確認してください。"
    except google_exceptions.ResourceExhausted:
        return "⏳ 【制限エラー】アクセス集中。『再試行』を押してください。"
    except Exception as e:
        return f"❌ 【通信エラー】{str(e)}"


def get_strict_json(prompt: str, image: Optional[Image.Image] = None) -> str:
    """画像解析など『JSONだけ返してほしい』用途。

    軍師用の長い system prompt を使うと、JSON以外が混ざってパース失敗しやすいので、
    ここだけ専用のsystem_instructionで実行する。
    """
    if not st.session_state.api_key:
        return "⚠️ APIキーを設定してください。"

    genai.configure(api_key=st.session_state.api_key)

    system_instruction = (
        "あなたは出力フォーマット厳守の抽出器。\n"
        "- 返答は必ず JSON のみ\n"
        "- 前後に文章、説明、Markdown、コードフェンスを付けない\n"
    )

    model_name = st.session_state.get("vision_model", "gemini-2.5-pro")
    model = genai.GenerativeModel(model_name, system_instruction=system_instruction)
    proc_image = image.convert("RGB") if image else None

    try:
        with st.spinner("解析中..."):
            response = model.generate_content([prompt, proc_image] if proc_image else prompt)
            return response.text
    except google_exceptions.Unauthenticated:
        return "⛔ 【認証エラー】APIキーを確認してください。"
    except google_exceptions.ResourceExhausted:
        return "⏳ 【制限エラー】アクセス集中。『再試行』を押してください。"
    except Exception as e:
        return f"❌ 【通信エラー】{str(e)}"