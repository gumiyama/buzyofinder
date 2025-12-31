#!/usr/bin/env python
"""
大量データ一括収集スクリプト
複数エリアから物件URLを収集し、データベースに保存
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.scrapers.suumo_scraper import SuumoScraper

# エリア設定
AREAS = {
    'chiyoda': {'pages': 15, 'name': '千代田区', 'url': 'https://suumo.jp/ms/chuko/tokyo/sc_chiyoda/'},
    'shibuya': {'pages': 15, 'name': '渋谷区', 'url': 'https://suumo.jp/ms/chuko/tokyo/sc_shibuya/'},
    'minato': {'pages': 15, 'name': '港区', 'url': 'https://suumo.jp/ms/chuko/tokyo/sc_minato/'},
    'shinjuku': {'pages': 15, 'name': '新宿区', 'url': 'https://suumo.jp/ms/chuko/tokyo/sc_shinjuku/'},
    'meguro': {'pages': 15, 'name': '目黒区', 'url': 'https://suumo.jp/ms/chuko/tokyo/sc_meguro/'},
}

INTERVAL = 3.0  # リクエスト間隔（秒）


def collect_urls_for_area(area_code, area_config):
    """指定エリアから物件URLを収集"""
    scraper = SuumoScraper()
    urls = set()
    
    base_url = area_config['url']
    pages = area_config['pages']
    
    for page in range(1, pages + 1):
        try:
            if page == 1:
                url = base_url
            else:
                url = f"{base_url}?page={page}"
            
            print(f"  ページ {page}/{pages} を取得中... ", end='', flush=True)
            
            # HTMLを取得
            html = scraper._fetch_html(url)
            if not html:
                print("❌ エラー: HTMLの取得に失敗")
                continue
            
            # URLを抽出
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # 物件リンクを探す
            links = soup.find_all('a', href=True)
            page_urls = set()
            
            for link in links:
                href = link['href']
                if '/ms/chuko/tokyo/' in href and '/nc_' in href:
                    # 完全URLに変換
                    if not href.startswith('http'):
                        href = 'https://suumo.jp' + href
                    # bukkengaiyoのURLに変換
                    if 'bukkengaiyo' not in href:
                        href = href.split('?')[0]
                        if not href.endswith('/'):
                            href += '/'
                        href += 'bukkengaiyo/'
                    page_urls.add(href)
            
            urls.update(page_urls)
            print(f"✓ {len(page_urls)}件")
            
            # レート制限
            if page < pages:
                time.sleep(INTERVAL)
                
        except Exception as e:
            print(f"❌ エラー: {e}")
            continue
    
    return urls


def main():
    print("=" * 60)
    print("大量データ一括収集")
    print(f"対象: {len(AREAS)}エリア")
    print("=" * 60)
    
    all_urls = set()
    area_stats = {}
    
    # 各エリアからURL収集
    for area_code, config in AREAS.items():
        print(f"\n📍 [{config['name']}] URL収集中...")
        urls = collect_urls_for_area(area_code, config)
        area_stats[config['name']] = len(urls)
        all_urls.update(urls)
        print(f"  ✓ 合計: {len(urls)}件")
    
    print("\n" + "=" * 60)
    print("URL収集完了")
    print("=" * 60)
    
    # 統計表示
    for area_name, count in area_stats.items():
        print(f"  {area_name}: {count}件")
    
    print(f"\n重複除去後の合計: {len(all_urls)}件")
    
    # ファイルに保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    url_file = f"bulk_urls_{timestamp}.txt"
    
    with open(url_file, 'w') as f:
        for url in sorted(all_urls):
            f.write(url + '\n')
    
    print(f"\n💾 {url_file} に保存しました")
    
    # データ取得確認
    print("\n" + "=" * 60)
    response = input("データ取得を開始しますか？ (y/n): ")
    
    if response.lower() == 'y':
        print("\nデータ取得開始...")
        print("=" * 60)
        os.system(f"PYTHONPATH=. ./venv/bin/python scripts/fetch_from_url_file.py {url_file}")
    else:
        print(f"\n後で以下のコマンドでデータ取得できます:")
        print(f"  PYTHONPATH=. ./venv/bin/python scripts/fetch_from_url_file.py {url_file}")


if __name__ == '__main__':
    main()
