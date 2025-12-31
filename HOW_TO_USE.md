# 分譲マンション お得サイエンティスト - 使い方ガイド

## 🎯 データ取得方法

このシステムでは、SUUMOの物件URLから直接データを取得します。

### ステップ1: 気になる物件URLを集める

1. [SUUMO中古マンション](https://suumo.jp/ms/chuko/)で物件を検索
2. 気になる物件の詳細ページを開く
3. URLをコピー（例: `https://suumo.jp/ms/chuko/tokyo/sc_shibuya/nc_12345678/`）

### ステップ2: スクリプトにURLを追加

`scripts/fetch_from_urls.py` を開いて、PROPERTY_URLs リストにURLを追加：

```python
PROPERTY_URLS = [
    'https://suumo.jp/ms/chuko/tokyo/sc_shibuya/nc_12345678/',
    'https://suumo.jp/ms/chuko/tokyo/sc_meguro/nc_87654321/',
    # 気になる物件のURLを追加
]
```

### ステップ3: データを取得

```bash
cd /Users/takaakikawabe/.gemini/antigravity/scratch/mansion-scientist
source venv/bin/activate
PYTHONPATH=. ./venv/bin/python scripts/fetch_from_urls.py
```

### ステップ4: Streamlitで確認

```bash
streamlit run app.py
```

ブラウザで http://localhost:8501 を開いて確認！

## ⚠️ 注意事項

- **個人利用限定**: 商用利用は避けてください
- **適切な間隔**: 物件データ取得は3秒間隔で行われます
- **利用規約**: SUUMOの利用規約を遵守してください

## 💡 ヒント

- 比較したい物件を5-10件程度集めると、スコアリングが効果的になります
- 同じエリア・価格帯の物件を集めると、お得度の判定がより正確になります
- ターゲット層（ファミリー/DINKS）を切り替えてスコアの違いを確認してみましょう

## 🔧 トラブルシューティング

### データが取得できない場合

1. URLが正しいか確認（`/nc_数字/` の形式）
2. インターネット接続を確認
3. SUUMOのサイト構造が変更された可能性（スクレイパーの修正が必要）

### スコアが表示されない場合

1. データベースに物件が保存されているか確認
2. Streamlitアプリを再起動
