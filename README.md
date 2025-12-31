# 分譲マンション お得サイエンティスト

一都三県の分譲マンション物件を科学的に分析し、「お得度」を100点満点でスコアリングするシステムです。

## 🎯 主な機能

- **5カテゴリ評価**: 価格適正性・立地・スペック・維持コスト・将来性
- **ターゲット層別分析**: ファミリー向け / DINKS向けで重み付け調整
- **実データ連携**: SUUMOから実在物件データを取得
- **可視化**: Streamlit UIでスコア・レーダーチャート表示

## 🚀 クイックスタート

### 1. セットアップ

```bash
cd /Users/takaakikawabe/.gemini/antigravity/scratch/mansion-scientist

# 仮想環境作成
python3.14 -m venv venv
source venv/bin/activate

# 依存パッケージインストール
pip install -r requirements.txt
```

### 2. データ取得（3つの方法）

#### 方法A: 手動URLリスト（少量）

`scripts/fetch_from_urls.py` を編集:

```python
PROPERTY_URLS = [
    'https://suumo.jp/ms/chuko/tokyo/sc_chiyoda/nc_79091940/',
    # URLを追加...
]
```

実行:
```bash
PYTHONPATH=. ./venv/bin/python scripts/fetch_from_urls.py
```

#### 方法B: 自動URL収集（大量推奨 🔥）

```bash
# 1. URLを収集
python scripts/collect_urls_from_search.py
# → collected_property_urls.txt に保存される

# 2. 収集したURLから詳細データ取得
python scripts/fetch_from_url_file.py collected_property_urls.txt
```

**メリット**:
- 一度に100件以上の物件URLを収集可能
- エリア別に選択可能（千代田区・渋谷区・新宿区・港区・目黒区）
- 既存物件は自動スキップ

#### 方法C: エリアを追加して再実行

同じスクリプトを別エリアで実行するだけ:

```bash
python scripts/collect_urls_from_search.py
# → 別のエリアを選択
python scripts/fetch_from_url_file.py collected_property_urls.txt
```

### 3. UI起動

```bash
streamlit run app.py
```

ブラウザで http://localhost:8501 を開く

## 📊 スコアリング基準

### 価格適正性 (30点)
- ㎡単価偏差値
- 総額偏差値
- エリア相場との比較

### 立地スコア (25点)
- 駅距離
- エリアブランド
- 周辺施設充実度

### 物件スペック (25点)
- 築年数
- 専有面積
- 階数・向き

### 管理・維持コスト (15点)
- 管理費
- 修繕積立金
- コストパフォーマンス

### 将来性・流動性 (5点)
- 流動性
- 人気度

## 💡 使い方のコツ

### データ蓄積のベストプラクティス

1. **初回**: 複数エリアを一括収集
```bash
python scripts/collect_urls_from_search.py
# → 「すべて」を選択
# → ページ数: 10
```

2. **定期更新**: 週1回程度で新規物件を追加
```bash
python scripts/collect_urls_from_search.py
# → 特定エリアを選択
python scripts/fetch_from_url_file.py collected_property_urls.txt
```

3. **比較対象を増やす**: 最低20件以上あると相対評価が正確に

### エラーが出た場合

- **TypeError: NoneType**: 修正済み。最新版を使用してください
- **物件が見つからない**: 検索URLが古い可能性。別エリアを試してください
- **データベース**: `data/properties.db` を削除して再実行

## 📁 プロジェクト構造

```
mansion-scientist/
├── app.py                          # Streamlit UI
├── scripts/
│   ├── fetch_from_urls.py          # 手動URLリスト取得
│   ├── collect_urls_from_search.py # URL自動収集 🆕
│   └── fetch_from_url_file.py      # ファイルから一括取得 🆕
├── src/
│   ├── scrapers/
│   │   └── suumo_scraper.py        # SUUMOスクレイパー
│   ├── scoring/
│   │   ├── property_scorer.py      # 総合スコアリング
│   │   └── ...                     # カテゴリ別スコアラー
│   └── models/
│       └── database.py             # データベース定義
├── data/
│   └── properties.db               # SQLite DB
└── collected_property_urls.txt     # 収集したURL 🆕
```

## ⚠️ 注意事項

- **個人利用限定**: 商用利用は避けてください
- **スクレイピング間隔**: 3秒間隔を守ってください
- **利用規約**: SUUMOの利用規約を遵守してください
- **データ量**: 一度に1,000件以上の取得は避けてください

## 🛠️ トラブルシューティング

### Streamlitでエラーが出る

```bash
# キャッシュクリア
rm -rf .streamlit/cache
streamlit run app.py
```

### データベースをリセット

```bash
rm data/properties.db
PYTHONPATH=. python scripts/fetch_from_url_file.py collected_property_urls.txt
```

### URLが収集できない

検索ページの構造が変わった可能性があります。`collect_urls_from_search.py` のセレクタを確認してください。

## 📈 今後の拡張案

- [ ] 定期実行の自動化（cron）
- [ ] 物件名の取得改善
- [ ] 価格推移の記録
- [ ] エクスポート機能（CSV）
- [ ] より詳細なフィルタリング

---

作成: 2025-12-27  
更新: 2025-12-27
