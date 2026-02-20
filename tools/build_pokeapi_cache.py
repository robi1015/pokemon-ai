# -*- coding: utf-8 -*-
"""PokeAPI からメタDB(JSON)を生成するツール。

目的:
- 実行時に毎回APIを叩かず、最初に一度だけ取得して data/pokemon_meta_db.json に保存する。
- speed比較UIの『種族値S自動入力』や、タイプ/特性などの補助に使う。

使い方（例）:
  python tools/build_pokeapi_cache.py
  python tools/build_pokeapi_cache.py --max 50   # 動作確認用に先頭50体だけ

注意:
- 全ポケモン取得は時間がかかります（ネット回線/サーバ負荷に依存）。
- 途中で止まっても data/pokemon_meta_db.json は原子的に保存します。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

import requests


TYPE_JA = {
    "normal": "ノーマル",
    "fire": "ほのお",
    "water": "みず",
    "electric": "でんき",
    "grass": "くさ",
    "ice": "こおり",
    "fighting": "かくとう",
    "poison": "どく",
    "ground": "じめん",
    "flying": "ひこう",
    "psychic": "エスパー",
    "bug": "むし",
    "rock": "いわ",
    "ghost": "ゴースト",
    "dragon": "ドラゴン",
    "dark": "あく",
    "steel": "はがね",
    "fairy": "フェアリー",
}

STAT_KEY = {
    "hp": "hp",
    "attack": "atk",
    "defense": "def",
    "special-attack": "spa",
    "special-defense": "spd",
    "speed": "spe",
}


def atomic_json_dump(path: str, data: Any, *, ensure_ascii: bool = False, indent: int = 2) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
    os.replace(tmp, path)


def get_json(url: str, *, timeout: int = 30) -> Dict[str, Any]:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()


def pick_ja_name(species_json: Dict[str, Any]) -> Optional[str]:
    # species.names から ja-Hrkt を優先、なければ ja
    for lang in ("ja-Hrkt", "ja"):
        for n in species_json.get("names", []) or []:
            if (n.get("language") or {}).get("name") == lang:
                name = (n.get("name") or "").strip()
                if name:
                    return name
    return None


def pick_ability_ja(ability_json: Dict[str, Any]) -> Optional[str]:
    for lang in ("ja-Hrkt", "ja"):
        for n in ability_json.get("names", []) or []:
            if (n.get("language") or {}).get("name") == lang:
                name = (n.get("name") or "").strip()
                if name:
                    return name
    return None


def build_one(pokemon_url: str, sleep: float = 0.08) -> Optional[Dict[str, Any]]:
    # pokemon -> species -> names
    p = get_json(pokemon_url)
    species_url = (p.get("species") or {}).get("url")
    if not species_url:
        return None
    sp = get_json(species_url)

    ja_name = pick_ja_name(sp)
    if not ja_name:
        return None

    # types
    types_en = [((t.get("type") or {}).get("name") or "") for t in (p.get("types") or [])]
    types_ja = [TYPE_JA.get(x, x) for x in types_en if x]

    # base stats
    base_stats: Dict[str, int] = {}
    for s in (p.get("stats") or []):
        k = ((s.get("stat") or {}).get("name") or "")
        v = s.get("base_stat")
        if k in STAT_KEY:
            try:
                base_stats[STAT_KEY[k]] = int(v)
            except Exception:
                pass

    # abilities (日本語名を取りに行くので少し重い)
    abilities_ja: List[str] = []
    for a in (p.get("abilities") or []):
        url = ((a.get("ability") or {}).get("url") or "")
        if not url:
            continue
        try:
            aj = get_json(url)
            name_ja = pick_ability_ja(aj)
            if name_ja:
                abilities_ja.append(name_ja)
        except Exception:
            continue
        time.sleep(sleep)

    out = {
        "id": p.get("id"),
        "types": types_ja,
        "base_stats": base_stats,
        "abilities": abilities_ja,
    }
    return {ja_name: out}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=0, help="取得数を制限（0=全件）")
    ap.add_argument("--out", type=str, default="data/pokemon_meta_db.json", help="出力パス")
    ap.add_argument("--sleep", type=float, default=0.08, help="API間スリープ秒")
    args = ap.parse_args()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = os.path.join(base_dir, args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    index = get_json("https://pokeapi.co/api/v2/pokemon?limit=2000")
    results = index.get("results") or []
    if args.max and args.max > 0:
        results = results[: args.max]

    db: Dict[str, Any] = {}
    total = len(results)
    for i, row in enumerate(results, 1):
        url = row.get("url")
        if not url:
            continue
        try:
            one = build_one(url, sleep=args.sleep)
            if one:
                db.update(one)
        except requests.HTTPError as e:
            print(f"[WARN] HTTPError {e} ({url})", file=sys.stderr)
        except Exception as e:
            print(f"[WARN] {e} ({url})", file=sys.stderr)

        if i % 25 == 0:
            print(f"{i}/{total} ...")
        time.sleep(args.sleep)

    atomic_json_dump(out_path, db, ensure_ascii=False, indent=2)
    print(f"OK: wrote {len(db)} mons -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
