# gunshi/ui_battle.py
# -*- coding: utf-8 -*-
import json
import re
from io import BytesIO

import streamlit as st
from PIL import Image

from .constants import TERA_TYPES, STATUS_PRESET, TEAM_FILE
from .ui_style import TacticalTranslator
from .ui_speed import render_speed_ui

from .pokemon_db import DEFAULT_POKEMON_LIST, normalize_detected_names
from .image_utils import enhance_for_switch_selection, auto_crop_switch_selection, crop_ratio

from .enemy import (
    get_enemy_mem,
    get_enemy_state,
    ensure_enemy_profile,
    set_profile_field,
    set_item_locked,
    clear_item,
    add_move,
    replace_move,
)

from .storage import (
    save_enemy_memory,
    save_enemy_state,
    load_enemy_memory,
    load_enemy_state,
)

from .move4 import get_move4, set_move4, load_move4_db, save_move4_db
from .extraction import auto_extract_enemy_info, auto_update_target_from_text
from .ai_client import get_gunshi_advice, get_strict_json
from .warroom import set_warroom_draft, apply_move_set_only
from .move_dict import load_move_dict
import os


# =========================================================
# war_room_input 安全同期（A案）
# =========================================================
def _sync_warroom_input_before_widget():
    """
    st.text_input(key="war_room_input") の「前」にだけ呼ぶこと。
    draft/clear を war_room_input に反映する唯一の場所。
    """
    if "war_room_input" not in st.session_state:
        st.session_state.war_room_input = ""

    if st.session_state.get("war_room_clear", False):
        st.session_state.war_room_input = ""
        st.session_state.war_room_clear = False

    draft = (st.session_state.get("war_room_draft") or "").strip()
    if draft:
        st.session_state.war_room_input = draft
        st.session_state.war_room_draft = ""


def _ensure_session_defaults():
    st.session_state.setdefault("enemy_party", [])
    st.session_state.setdefault("target_mon", "(なし)")
    st.session_state.setdefault("mem_target_mon", "(未選択)")

    st.session_state.setdefault("chat_history", [])
    st.session_state.setdefault("battle_log", [])
    st.session_state.setdefault("turn_no", 0)
    st.session_state.setdefault("turn_log", [])

    st.session_state.setdefault("pending_ai_prompt", "")
    st.session_state.setdefault("pending_ai_image_bytes", None)

    st.session_state.setdefault("war_room_draft", "")
    st.session_state.setdefault("war_room_clear", False)


def _get_party_slots() -> list[str]:
    party = st.session_state.enemy_party[:] if st.session_state.enemy_party else []
    cur = st.session_state.get("target_mon", "(なし)")

    ordered = []
    if cur and cur != "(なし)" and cur in party:
        ordered.append(cur)
    for m in party:
        if m not in ordered:
            ordered.append(m)

    return (ordered[:6] + [""] * 6)[:6]


def _build_move_candidates() -> list[str]:
    """技の予測変換候補（重くしない範囲で）"""
    cand = set()

    # enemy_memory の既知技
    for info in (st.session_state.get("enemy_memory") or {}).values():
        if isinstance(info, dict):
            for m in (info.get("moves") or [])[:4]:
                if isinstance(m, str) and m.strip():
                    cand.add(m.strip())

    # My Team の技（保存済み）※I/Oをキャッシュして軽量化
    mtime = os.path.getmtime(TEAM_FILE) if os.path.exists(TEAM_FILE) else 0
    for m in _load_team_moves_cached(mtime):
        cand.add(m)

    common = [
        "まもる", "ステルスロック", "とんぼがえり", "ボルトチェンジ", "おにび", "あくび", "アンコール",
        "りゅうのまい", "わるだくみ", "ムーンフォース", "インファイト", "ハイドロポンプ",
        "シャドーボール", "10まんボルト",
    ]
    for m in common:
        cand.add(m)

    # 4) 辞書（data/moves_ja.json）
    for m in load_move_dict():
        cand.add(m)

    return ["-"] + sorted(cand)


@st.cache_data(show_spinner=False)
def _load_team_moves_cached(_mtime: float) -> list[str]:
    """TEAM_FILE から技だけ抽出（UI軽量化のためキャッシュ）。"""
    try:
        if not os.path.exists(TEAM_FILE):
            return []
        with open(TEAM_FILE, "r", encoding="utf-8") as f:
            t = json.load(f) or {}
        out: list[str] = []
        seen = set()
        for p in t.values():
            if isinstance(p, dict):
                for mv in (p.get("moves") or [])[:4]:
                    if isinstance(mv, str):
                        s = mv.strip()
                        if s and s not in seen:
                            out.append(s)
                            seen.add(s)
        return out
    except Exception:
        return []


# =========================================================
# メイン：Battle UI
# =========================================================
def render_battle_tab():
    _ensure_session_defaults()
    load_move4_db()  # move4 が未ロードでも安全に
    _sync_warroom_input_before_widget()

    col_L, col_R = st.columns([1, 1.55])

    # =====================================================
    # LEFT
    # =====================================================
    with col_L:
        st.subheader("👁️ 相手パーティ（6枠）")

        with st.expander("📸 画像解析（Switch選出画面）", expanded=True):
            up = st.file_uploader("画像アップロード", type=["png", "jpg", "jpeg"], label_visibility="collapsed")

            st.caption("推奨：スクショ直 / スマホ写真なら『自動クロップON + Proモデル』")
            use_auto_crop = st.toggle("自動クロップ（推奨）", value=True, key="ui_use_auto_crop")
            use_manual_crop = st.toggle("手動クロップ（ズレ救済）", value=False, key="ui_use_manual_crop")

            if use_manual_crop:
                l = st.slider("left", 0.0, 1.0, 0.08, 0.01, key="ui_crop_l")
                t = st.slider("top", 0.0, 1.0, 0.12, 0.01, key="ui_crop_t")
                r = st.slider("right", 0.0, 1.0, 0.92, 0.01, key="ui_crop_r")
                b = st.slider("bottom", 0.0, 1.0, 0.92, 0.01, key="ui_crop_b")

            if up:
                raw = Image.open(up).convert("RGB")
                work = raw
                if use_auto_crop:
                    work = auto_crop_switch_selection(work)
                if use_manual_crop:
                    work = crop_ratio(work, l, t, r, b)

                work = enhance_for_switch_selection(work, scale=2)
                st.image(work, caption="解析に回す画像（前処理後）", use_container_width=True)

                prompt_img = """
あなたは画像から「相手パーティ6匹の名前」を特定する。
次のルールを厳守せよ。

- 返答は JSON のみ
- 形式は必ずこれ:
{"enemy_party":["ポケモン名1","ポケモン名2","ポケモン名3","ポケモン名4","ポケモン名5","ポケモン名6"]}

- 余計な文章は禁止
- 読めない場合は推測せず、読めない枠は "" を入れる
""".strip()

                if st.button("🔍 画像解析を実行", type="primary", use_container_width=True):
                    buf = BytesIO()
                    work.save(buf, format="JPEG", quality=92)
                    st.session_state.pending_ai_prompt = prompt_img
                    st.session_state.pending_ai_image_bytes = buf.getvalue()
                    st.toast("🧠 pending に保存しました（下の『再試行』で実行）", icon="🧠")

            if st.session_state.pending_ai_prompt:
                colA, colB = st.columns(2)
                if colA.button("🔁 再試行（pendingで実行）", use_container_width=True):
                    img = None
                    if st.session_state.pending_ai_image_bytes:
                        img = Image.open(BytesIO(st.session_state.pending_ai_image_bytes)).convert("RGB")

                    resp = get_strict_json(st.session_state.pending_ai_prompt, image=img)

                    detected = []
                    try:
                        m = re.search(r"\{[\s\S]*\}", resp)
                        if m:
                            obj = json.loads(m.group(0))
                            detected = obj.get("enemy_party", []) or []
                    except Exception:
                        detected = []

                    detected = [d.strip() for d in detected if isinstance(d, str) and d.strip()]
                    if detected:
                        fixed, warns = normalize_detected_names(detected, DEFAULT_POKEMON_LIST)
                        if warns:
                            st.warning("\n".join(warns))
                        if fixed:
                            st.session_state.enemy_party = fixed[:6]
                            st.session_state.target_mon = st.session_state.enemy_party[0] if st.session_state.enemy_party else "(なし)"
                            st.session_state.mem_target_mon = st.session_state.target_mon if st.session_state.target_mon != "(なし)" else "(未選択)"
                            set_warroom_draft(f"相手は{st.session_state.target_mon}を繰り出した")
                            st.toast("✅ 相手パーティを反映しました", icon="✅")
                            st.rerun()
                    else:
                        st.toast("⚠️ 抽出失敗。クロップ調整 or Proモデル推奨", icon="⚠️")

                if colB.button("🧹 pendingを消す", use_container_width=True):
                    st.session_state.pending_ai_prompt = ""
                    st.session_state.pending_ai_image_bytes = None
                    st.rerun()

        st.divider()

        st.caption("🧩 6枠ボタン（タップで対面変更 / メモ対象も追従 / 作戦会議にも注入）")
        slots = _get_party_slots()
        cols = st.columns(6)
        for i in range(6):
            mon = slots[i]
            label = mon if mon else "—"
            is_target = (mon and mon == st.session_state.target_mon)
            btn_text = f"🔥{label}" if is_target else label
            if cols[i].button(btn_text, key=f"party_slot_{i}_{label}"):
                if mon:
                    st.session_state.target_mon = mon
                    st.session_state.mem_target_mon = mon
                    set_warroom_draft(f"相手は{mon}を繰り出した")
                    st.toast(f"🎯 対面: {mon}", icon="🎯")
                else:
                    st.toast("空欄です（下の手動入力で埋めて）", icon="⚠️")
                st.rerun()

        with st.expander("✍️ 相手パーティを手動入力（最大6）", expanded=True):
            cur_party = st.session_state.enemy_party[:] if st.session_state.enemy_party else []
            enemies = st.multiselect("相手パーティ", DEFAULT_POKEMON_LIST, default=cur_party)
            enemies = enemies[:6]
            if enemies != cur_party:
                st.session_state.enemy_party = enemies
                if st.session_state.target_mon not in enemies:
                    st.session_state.target_mon = enemies[0] if enemies else "(なし)"
                if st.session_state.mem_target_mon not in enemies:
                    st.session_state.mem_target_mon = st.session_state.target_mon if st.session_state.target_mon != "(なし)" else "(未選択)"
                st.rerun()

        st.divider()

        dmg_feel = st.select_slider(
            "label", ["無効", "確定耐え", "乱数勝負", "確定1発"],
            value="確定耐え", label_visibility="collapsed"
        )
        tag, desc, _, icon = TacticalTranslator.translate_damage_feeling(dmg_feel)
        st.caption(f"{icon} {tag}：{desc}")

        st.subheader("🧭 AIからの選出指示")
        sel_prompt = st.text_area(
            "選出依頼（必要なら編集）",
            height=120,
            value="【敵チーム】" + str(st.session_state.enemy_party) + "\n"
                  "最強の選出3匹を『結論→理由→裏ケア』で提示せよ。"
        )
        c1, c2 = st.columns(2)
        if c1.button("🧠 選出を依頼（送信）", type="primary", use_container_width=True):
            resp = get_gunshi_advice(sel_prompt, probs_context=st.session_state.get("probs"))
            st.session_state.chat_history.append({"role": "user", "content": "【選出依頼】"})
            st.session_state.chat_history.append({"role": "model", "content": resp})
            st.session_state.chat_history = st.session_state.chat_history[-120:]
            st.rerun()
        if c2.button("✍️ 選出依頼を入力欄へ", use_container_width=True):
            set_warroom_draft("選出相談: " + str(st.session_state.enemy_party))

    # =====================================================
    # RIGHT
    # =====================================================
    with col_R:
        memo_open = st.toggle("🧠 メモを開く", value=True, key="memo_open")

        if memo_open:
            st.subheader("🧠 メモ（敵の確定情報）")

            now_t = st.session_state.target_mon
            if now_t and now_t != "(なし)":
                em = get_enemy_mem(now_t)
                stt = get_enemy_state(now_t)
                prof = ensure_enemy_profile(em)
                st.info(
                    f"🎯 今の対象: {now_t}\n\n"
                    f"- 持ち物: {em.get('item') or '-'}\n"
                    f"- テラ: {stt.get('tera_type') or '-'} ({'済' if stt.get('tera_used') else '未'})\n"
                    f"- HP: {stt.get('hp',100)}% / 状態: {stt.get('status') or '通常'} / {'生存' if stt.get('alive',True) else '瀕死'}\n"
                    f"- 速度: {prof.get('speed_tier','-')}（S{prof.get('speed_raw','-')} / 実効{prof.get('speed_eff','-')}）\n"
                    f"- タイプ: {prof.get('type','?')} / 特性: {prof.get('ability','-')} / 性格: {prof.get('nature','-')}\n"
                    f"- 努力値: {prof.get('evs','-')} / 個体値: {prof.get('ivs','-')}\n"
                    f"- 技: {', '.join([m for m in (em.get('moves') or []) if m]) or '-'}"
                )
            else:
                st.info("🎯 今の対象: 未選択")

            s1, s2, s3 = st.columns(3)
            if s1.button("💾 保存", use_container_width=True):
                save_enemy_memory()
                save_enemy_state()
                save_move4_db()
                st.toast("💾 保存しました", icon="💾")
            if s2.button("📥 読込", use_container_width=True):
                load_enemy_memory()
                load_enemy_state()
                load_move4_db()
                st.toast("📥 読み込みました", icon="📥")
                st.rerun()
            if s3.button("🧹 全消去", use_container_width=True):
                st.session_state.enemy_memory = {}
                st.session_state.enemy_state = {}
                save_enemy_memory()
                save_enemy_state()
                st.toast("🧹 全消去しました", icon="🧹")
                st.rerun()

            st.caption("🎯 メモ対象（左端=対面固定）")
            slots = _get_party_slots()
            cols = st.columns(6)
            for i, mon in enumerate(slots):
                label = mon if mon else "—"
                is_sel = (mon and mon == st.session_state.mem_target_mon)
                base = f"🔥{label}" if (i == 0 and mon and mon == st.session_state.target_mon and st.session_state.target_mon != "(なし)") else label
                btn = f"✅{base}" if is_sel else base
                if cols[i].button(btn, key=f"memslot_{i}_{btn}"):
                    if mon:
                        st.session_state.mem_target_mon = mon
                        set_warroom_draft(f"相手は{mon}（メモ対象変更）")
                        st.toast(f"📝 メモ対象: {mon}", icon="📝")
                    else:
                        st.toast("空欄です", icon="⚠️")
                    st.rerun()

            mem_target = st.session_state.get("mem_target_mon", "(未選択)")
            st.caption(f"対象：{mem_target}")
            with st.expander("🔎 メモ対象を名前で検索", expanded=False):
                pick_list = ["(未選択)"] + DEFAULT_POKEMON_LIST
                cur = st.session_state.get("mem_target_mon", "(未選択)")
                try:
                    idx = pick_list.index(cur) if cur in pick_list else 0
                except Exception:
                    idx = 0
                picked = st.selectbox("ポケモン名", pick_list, index=idx, key="memo_pick_name")
                add_to_party = st.checkbox("相手パーティ6枠にも入れる（任意）", value=False, key="memo_add_to_party")
                if st.button("このポケモンをメモ対象にする", use_container_width=True, key="memo_pick_apply"):
                    st.session_state.mem_target_mon = picked
                    if add_to_party and picked not in ("(未選択)", "(なし)") and picked:
                        party = st.session_state.enemy_party[:] if st.session_state.enemy_party else []
                        if picked not in party and len(party) < 6:
                            party.append(picked)
                            st.session_state.enemy_party = party
                    if picked not in ("(未選択)", "(なし)") and picked:
                        set_warroom_draft("メモ対象を" + picked + "に変更")
                    st.rerun()

            if mem_target != "(未選択)":
                em = get_enemy_mem(mem_target)
                stt = get_enemy_state(mem_target)
                prof = ensure_enemy_profile(em)

                st.divider()
                st.markdown("### 📌 HP / 状態 / テラ")
                a, b, c, d = st.columns(4)
                if a.button("☠️瀕死/生存", use_container_width=True):
                    stt["alive"] = not stt.get("alive", True)
                    save_enemy_state()
                    st.rerun()
                if b.button("HP-25%", use_container_width=True):
                    stt["hp"] = max(0, int(stt.get("hp", 100)) - 25)
                    save_enemy_state()
                    st.rerun()
                if c.button("HP=100%", use_container_width=True):
                    stt["hp"] = 100
                    save_enemy_state()
                    st.rerun()
                if d.button("💎テラ済/未", use_container_width=True):
                    stt["tera_used"] = not stt.get("tera_used", False)
                    save_enemy_state()
                    st.rerun()

                hp_val = st.slider("HP目安", 0, 100, int(stt.get("hp", 100)), 5)
                if hp_val != int(stt.get("hp", 100)):
                    stt["hp"] = int(hp_val)
                    save_enemy_state()

                st.caption("状態")
                st_cols = st.columns(6)
                for i, (lbl, val) in enumerate(STATUS_PRESET):
                    if st_cols[i % 6].button(lbl, key=f"st_{mem_target}_{val}"):
                        stt["status"] = val
                        save_enemy_state()
                        st.rerun()

                st.caption("テラタイプ（記録）")
                tcols = st.columns(6)
                for i, tp in enumerate(TERA_TYPES):
                    if tcols[i % 6].button(tp, key=f"teratype_{mem_target}_{tp}"):
                        stt["tera_type"] = tp
                        save_enemy_state()
                        st.rerun()

                st.divider()
                st.markdown("### 🧩 カード情報（保存）")
                p1, p2 = st.columns(2)
                with p1:
                    p_type = st.text_input("タイプ（例: ゴースト/フェアリー）", value=prof.get("type", "?"), key=f"pf_type_{mem_target}")
                    p_abi = st.text_input("特性", value=prof.get("ability", "-"), key=f"pf_abi_{mem_target}")
                    p_nat = st.text_input("性格", value=prof.get("nature", "-"), key=f"pf_nat_{mem_target}")
                with p2:
                    p_evs = st.text_input("努力値（例: H252 B4 S252）", value=prof.get("evs", "-"), key=f"pf_evs_{mem_target}")
                    p_ivs = st.text_input("個体値（例: A0 など）", value=prof.get("ivs", "-"), key=f"pf_ivs_{mem_target}")

                if st.button("✅ カード情報を保存", use_container_width=True):
                    set_profile_field(mem_target, "type", p_type)
                    set_profile_field(mem_target, "ability", p_abi)
                    set_profile_field(mem_target, "nature", p_nat)
                    set_profile_field(mem_target, "evs", p_evs)
                    set_profile_field(mem_target, "ivs", p_ivs)
                    save_enemy_memory()
                    st.toast("✅ 保存しました", icon="✅")
                    st.rerun()

                st.divider()
                st.markdown("### 📦 持ち物（確定ロック）")
                q1, q2, q3, q4 = st.columns(4)

                def _quick_item(item_name: str):
                    ok, msg = set_item_locked(mem_target, item_name)
                    save_enemy_memory()
                    st.toast(msg if msg else "更新なし", icon=("🧠" if ok else "⚠️"))
                    if ok:
                        set_warroom_draft(f"{mem_target}の持ち物は{item_name}で確定")
                    st.rerun()

                if q1.button("📦 スカーフ"):
                    _quick_item("スカーフ")
                if q2.button("📦 襷"):
                    _quick_item("タスキ")
                if q3.button("📦 メガネ"):
                    _quick_item("メガネ")
                if q4.button("🔓解除"):
                    clear_item(mem_target)
                    save_enemy_memory()
                    st.toast("🔓 持ち物確定を解除", icon="🔓")
                    st.rerun()

                st.divider()
                st.markdown("### ⚔️ 技（メモ：最大4）")
                mv = (em.get("moves") or [])[:4]
                st.caption("登録済み: " + (", ".join([m for m in mv if m]) if any(mv) else "-"))

                # 予測変換
                move_candidates = _build_move_candidates()
                pick = st.selectbox("技候補（検索できる）", move_candidates, index=0, key=f"mv_pick_{mem_target}")

                mcol1, mcol2 = st.columns([2, 1])
                with mcol1:
                    move_input = st.text_input("技を追加（手入力もOK）", key=f"addmv_{mem_target}")
                with mcol2:
                    if st.button("＋追加", use_container_width=True, key=f"addmv_btn_{mem_target}"):
                        chosen = pick if (pick and pick != "-") else move_input
                        ok, msg = add_move(mem_target, chosen)
                        save_enemy_memory()
                        st.toast(msg if msg else "更新なし", icon=("🧠" if ok else "⚠️"))
                        st.rerun()

                with st.expander("🔁 置換（上限時）"):
                    cur_moves = [m for m in (em.get("moves") or []) if m]
                    if not cur_moves:
                        st.caption("対象の技がまだありません")
                    else:
                        old = st.selectbox("置換する技", cur_moves, key=f"rep_old_{mem_target}")
                        new_pick = st.selectbox("新技候補", move_candidates, index=0, key=f"rep_pick_{mem_target}")
                        new = st.text_input("新しい技名（手入力）", key=f"rep_new_{mem_target}")
                        if st.button("🔁 置換実行", use_container_width=True, key=f"rep_btn_{mem_target}"):
                            chosen_new = new_pick if (new_pick and new_pick != "-") else new
                            ok, msg = replace_move(mem_target, old, chosen_new)
                            save_enemy_memory()
                            st.toast(msg if msg else "更新なし", icon=("🧠" if ok else "⚠️"))
                            st.rerun()

                st.divider()
                st.markdown("### 🎛️ 作戦会議に適用される技ボタン（4つ・ポケモン別）")
                cur4 = get_move4(mem_target)
                bcols = st.columns(4)
                for i in range(4):
                    label = cur4[i] if cur4[i] else "—"
                    if bcols[i].button(label, use_container_width=True, key=f"m4btn_{mem_target}_{i}", disabled=(label == "—")):
                        apply_move_set_only(mem_target, label)

                with st.expander("✍️ 4ボタンを手動変更"):
                    e1, e2 = st.columns(2)
                    with e1:
                        t0 = st.text_input("ボタン1", value=cur4[0], key=f"m4e0_{mem_target}")
                        t1 = st.text_input("ボタン2", value=cur4[1], key=f"m4e1_{mem_target}")
                    with e2:
                        t2 = st.text_input("ボタン3", value=cur4[2], key=f"m4e2_{mem_target}")
                        t3 = st.text_input("ボタン4", value=cur4[3], key=f"m4e3_{mem_target}")
                    if st.button("✅ 4ボタン保存", use_container_width=True, key=f"m4save_{mem_target}"):
                        set_move4(mem_target, [t0, t1, t2, t3])
                        save_move4_db()
                        st.toast("✅ 保存しました", icon="✅")
                        st.rerun()

        # ✅ ここがポイント：col_R の中で、メモの外（インデント崩れない）
        with st.expander("⚡ 素早さ比較（ガチ）", expanded=False):
            render_speed_ui(
                default_my="",
                default_enemy=st.session_state.get("target_mon", "")
            )
        # =====================================================
        # 作戦会議（チャット）
        # =====================================================
        st.divider()
        st.subheader("💬 作戦会議")

        chat_container = st.container(height=360)
        with chat_container:
            if not st.session_state.chat_history:
                st.info("履歴なし")
            for chat in st.session_state.chat_history[-120:]:
                role = "assistant" if chat["role"] == "model" else "user"
                content_clean = re.sub(r"```json.*?```", "", chat["content"], flags=re.DOTALL).strip()
                if content_clean:
                    with st.chat_message(role):
                        st.markdown(content_clean)

        st.divider()
        st.markdown("### ✍️ 入力（ボタン注入対応）")
        in_col1, in_col2 = st.columns([4, 1])
        with in_col1:
            st.text_input("質問・報告", key="war_room_input", label_visibility="collapsed")
        with in_col2:
            send_clicked = st.button("送信", type="primary", use_container_width=True)

        if send_clicked:
            user_query = (st.session_state.get("war_room_input") or "").strip()
            if user_query:
                st.session_state.war_room_clear = True
                st.session_state.turn_no += 1

                new_t = auto_update_target_from_text(user_query, st.session_state.enemy_party)
                if new_t and new_t != st.session_state.target_mon:
                    st.session_state.target_mon = new_t
                    st.session_state.mem_target_mon = new_t
                    st.toast(f"🎯 対面を {new_t} に更新", icon="🎯")

                logs = auto_extract_enemy_info(user_query, st.session_state.enemy_party)
                if logs:
                    save_enemy_memory()
                    st.session_state.chat_history.append({"role": "model", "content": "【自動メモ更新】\n" + "\n".join(logs)})

                st.session_state.chat_history.append({"role": "user", "content": user_query})

                resp = get_gunshi_advice(user_query, probs_context=st.session_state.get("probs"))
                st.session_state.chat_history.append({"role": "model", "content": resp})
                st.session_state.chat_history = st.session_state.chat_history[-120:]
                st.rerun()