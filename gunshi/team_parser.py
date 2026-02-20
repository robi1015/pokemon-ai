# gunshi/team_parser.py
# -*- coding: utf-8 -*-
import os, json, re
import streamlit as st
from .constants import BASE_DIR, TEAM_FILE


def _migrate_team_from_project_root() -> None:
    try:
        old_path = os.path.join(BASE_DIR, "my_team.json")
        if os.path.exists(old_path) and (not os.path.exists(TEAM_FILE)):
            os.makedirs(os.path.dirname(TEAM_FILE), exist_ok=True)
            os.replace(old_path, TEAM_FILE)
    except Exception:
        pass
from .storage import atomic_json_dump

@st.cache_data(show_spinner=False)
def _load_my_team_cached(_mtime: float) -> dict:
    """my_team.json の読み込みをキャッシュ（更新検知はmtimeで行う）"""
    if os.path.exists(TEAM_FILE):
        with open(TEAM_FILE, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        return data if isinstance(data, dict) else {}
    return {}


def parse_showdown_text_robust(text: str) -> dict:
    team_dict = {}
    lines = text.strip().split("\n")
    current_mon = {}
    mon_count = 0
    skip_prefixes = ("EVs:", "IVs:", "Ability:", "Level:", "Shiny:", "Happiness:", "Nature:")

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "@" in line:
            if current_mon:
                mon_count += 1
                team_dict[str(mon_count)] = current_mon
            parts = line.split("@")
            name = parts[0].strip().replace("(M)", "").replace("(F)", "").strip()
            item = parts[1].strip() if len(parts) > 1 else "なし"
            current_mon = {"name": name, "item": item, "tera": "なし", "moves": []}
        elif current_mon:
            if line.startswith("テラスタイプ:") or line.startswith("Tera Type:"):
                current_mon["tera"] = line.split(":")[1].strip()
            elif line.startswith(skip_prefixes):
                continue
            elif line.startswith("- "):
                current_mon["moves"].append(line[2:].strip())
            elif "/" in line:
                if re.search(r"^\s*\d+\s*(HP|Atk|Def|SpA|SpD|Spe)", line):
                    continue
                for m in line.split("/"):
                    current_mon["moves"].append(m.strip())

    if current_mon:
        mon_count += 1
        team_dict[str(mon_count)] = current_mon

    for key in team_dict:
        while len(team_dict[key]["moves"]) < 4:
            team_dict[key]["moves"].append("")
        team_dict[key]["moves"] = team_dict[key]["moves"][:4]
    return team_dict

def load_my_team() -> dict:
    """自分のチーム定義を読む（更新されても即反映されるようmtimeでキャッシュ制御）"""
    _migrate_team_from_project_root()
    mtime = os.path.getmtime(TEAM_FILE) if os.path.exists(TEAM_FILE) else 0
    try:
        return _load_my_team_cached(mtime)
    except Exception as e:
        st.warning(f"⚠️ my_team読込失敗: {e}")
        return {}
def save_my_team(team: dict):
    atomic_json_dump(TEAM_FILE, team, ensure_ascii=False, indent=4)