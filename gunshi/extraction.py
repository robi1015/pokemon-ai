# gunshi/extraction.py
# -*- coding: utf-8 -*-
import re
from typing import Optional
from .constants import AMBIG, ITEM_ALIAS
from .enemy import add_move, normalize_item

def auto_extract_enemy_info(text: str, known_mons: list[str]) -> list[str]:
    logs = []
    if not text or not known_mons:
        return logs

    is_ambig = any(w in text for w in AMBIG)
    mons_in_text = [m for m in sorted(known_mons, key=len, reverse=True) if m in text]
    if not mons_in_text:
        return logs

    for mon in mons_in_text:
        # item hint only
        item_candidates = []
        m = re.search(rf"{re.escape(mon)}\s*[@＠]\s*([^\s、。！!？\n]+)", text)
        if m: item_candidates.append(m.group(1))
        m = re.search(r"(持ち物|アイテム)\s*[:：=＝]\s*([^\s、。！!？\n]+)", text)
        if m: item_candidates.append(m.group(2))

        item_candidates = [(c or "").strip() for c in item_candidates if (c or "").strip()]
        item_hint = None
        for raw in item_candidates:
            if (raw in ITEM_ALIAS) or any(k in raw for k in ITEM_ALIAS.keys()):
                item_hint = normalize_item(raw)
                break
        if item_hint and (not is_ambig):
            logs.append(f"📝 {mon} の持ち物候補: 「{item_hint}」(未確定)  ※ボタンで確定してね")

        # move only explicit
        move = None
        m = re.search(
            rf"{re.escape(mon)}\s*が\s*([^\s、。！!？\n]+)\s*(を)?\s*(見せた|使った|うった|撃った|してきた|した)",
            text
        )
        if m:
            move = m.group(1).strip()

        if move:
            ok, msg = add_move(mon, move)
            if msg:
                logs.append(("✅ " if ok else "⚠️ ") + msg)

    return logs

def auto_update_target_from_text(text: str, known_mons: list[str]) -> Optional[str]:
    if not text or not known_mons:
        return None
    trigger = any(w in text for w in ["出てきた", "繰り出された", "対面", "着地", "降臨", "登場", "相手は"])
    mons = [m for m in sorted(known_mons, key=len, reverse=True) if m in text]
    if not mons:
        return None
    return mons[0] if trigger else None
