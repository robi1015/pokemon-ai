"""Project-wide constants.

（A案）JSONファイルはすべて project_root/data/ に統一します。
"""

# gunshi/constants.py
# -*- coding: utf-8 -*-

import os

APP_TITLE = "軍師Pro - Modular Final"

# project root = gunshi/ の1つ上
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DATA_DIR = os.path.join(BASE_DIR, "data")

# data/ が無い場合でも落ちないように作る
os.makedirs(DATA_DIR, exist_ok=True)

# JSON paths（すべて data/ 配下）
TEAM_FILE = os.path.join(DATA_DIR, "my_team.json")
MY_TEAM_NOTES_FILE = os.path.join(DATA_DIR, "my_team_notes.json")
DB_FILE = os.path.join(DATA_DIR, "pokemon_meta_db.json")

# Backward-compat alias (some modules import this name)
POKEMON_META_DB_FILE = DB_FILE

ENEMY_MEM_FILE = os.path.join(DATA_DIR, "enemy_memory.json")
ENEMY_STATE_FILE = os.path.join(DATA_DIR, "enemy_state.json")
MOVE4_FILE = os.path.join(DATA_DIR, "move4_buttons.json")

# 技候補辞書（予測変換用）
MOVES_DICT_FILE = os.path.join(DATA_DIR, "moves_ja.json")

TERA_TYPES = [
    "ノーマル","ほのお","みず","でんき","くさ","こおり","かくとう","どく","じめん",
    "ひこう","エスパー","むし","いわ","ゴースト","ドラゴン","あく","はがね","フェアリー"
]

STATUS_PRESET = [
    ("✅通常", ""), ("🔥やけど", "やけど"), ("☠️どく", "どく"), ("😵まひ", "まひ"),
    ("🧊こおり", "こおり"), ("😴ねむり", "ねむり")
]

AMBIG = ("かも", "っぽい", "らしい", "みたい", "たぶん", "多分")

ITEM_ALIAS = {
    "スカーフ": "こだわりスカーフ",
    "メガネ": "こだわりメガネ",
    "ハチマキ": "こだわりハチマキ",
    "タスキ": "きあいのタスキ",
    "チョッキ": "とつげきチョッキ",
    "オボン": "オボンのみ",
    "残飯": "たべのこし",
    "ゴツメ": "ゴツゴツメット",
    "ブースト": "ブーストエナジー",
    "パンチ": "パンチグローブ",
    "マント": "おんみつマント",
}

GUNSHI_SYSTEM_PROMPT = r"""
[ROLE]
あなたはポケモンSVの最上位レート帯プレイヤー兼、対戦軍師AI。
目的は「勝率最大の一手を即断し、勝ち筋を1本に固定すること」。

[CORE RULES]
- 結論ファースト。必ず次の順番で出力:
  ① 推奨行動（技名/交代先/テラ有無まで明記）
  ② 理由（確率/盤面/相手の確定情報を根拠に断定）
  ③ 裏ケア（最大2個まで。優先度順。）
- 分岐を増やさない。勝ち筋を一本に絞る。
- 「確定情報」は推論ではなく事実。絶対に優先。

[INPUT DATA HANDLING]
- [CONFIRMED INFO] は事実として扱え（持ち物確定なら上書きせず前提固定）。
- [ACTION_TEMPLATE] は今の対面に対する要点。必ずそこから考えろ。
- [BAYESIAN_PROBABILITY] があれば絶対的な事実として用いろ。

[MANDATORY OUTPUT FORMAT]
【推奨行動】
○○
【理由】
○○
【裏ケア】
○○
"""
