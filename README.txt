Pokemon SV 軍師AI (Streamlit)

起動:
  1) このzipを「すべて展開」で解凍（zipの中で直接実行しない）
  2) 解凍したフォルダで:
       pip install -r requirements.txt
       streamlit run app.py

データ(JSON)は data/ に統一:
  data/enemy_memory.json, data/enemy_state.json, data/move4_buttons.json, data/my_team.json, data/pokemon_meta_db.json, data/moves_ja.json

注意:
- Gemini APIキーはアプリのサイドバーで入力
- bayesian_engine.py は任意（無くても動く）
