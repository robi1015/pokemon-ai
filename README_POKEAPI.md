# PokeAPI でDBを作る（最初に1回だけ）

このプロジェクトは **実行中に毎回PokeAPIを叩きません**。
代わりに、PCで最初に一度だけ取得して **`data/pokemon_meta_db.json`** に保存し、それをアプリが参照します。

## 1) 依存を入れる

```bash
pip install -r requirements.txt
```

## 2) DB生成（全件）

```bash
python tools/build_pokeapi_cache.py
```

- 完了すると `data/pokemon_meta_db.json` が更新されます。

## 3) 動作確認用（先頭50体だけ）

```bash
python tools/build_pokeapi_cache.py --max 50
```

## 生成されるDBの中身

各ポケモン（日本語名キー）に、最低限これが入ります。

- `types`: タイプ（日本語）
- `base_stats`: 種族値（hp/atk/def/spa/spd/spe）
- `abilities`: 特性（日本語）

> ※ 取得件数が多いので、初回は時間がかかります。
