#!/usr/bin/env python
"""
大井町駅（ek_05130）指定の集中収集スクリプト
"""
import os
import sys
import time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.database import get_session, get_engine, Property, save_or_update_property
from src.scrapers.suumo_scraper import SuumoScraper

# 大井町駅の設定
STATIONS = {
    '05480': {'pages': 20, 'name': '大井町駅'},
}

CRAWL_INTERVAL = 1.0

def save_property(url, session, scraper):
    """URLから物件情報を取得して保存または更新"""
    try:
        source_id = url.split('/nc_')[1].split('/')[0] if '/nc_' in url else None
        if not source_id: return "skip"
        
        detail = scraper.get_property_detail(url)
        if not detail or not detail.get('price'): return "error"
        
        return save_or_update_property(session, detail, source_id)
        
    except Exception as e:
        print(f"      ❌ 処理エラー ({url}): {e}")
        return "error"

def process_station(ek_code, config, session, scraper):
    """駅ごとにページを巡回"""
    base_url = f'https://suumo.jp/ms/chuko/tokyo/ek_{ek_code}/'
    pages = config['pages']
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    saved_count = 0
    
    for page in range(1, pages + 1):
        try:
            url = base_url if page == 1 else f"{base_url}?page={page}"
            print(f"  📄 ページ {page}/{pages} をスキャン中... ({config['name']})")
            
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                print(f"    ❌ HTTP {response.status_code}")
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            # 検索結果メインリストのコンテナを特定（通常 'property_unit' クラスなどを持つ）
            # もしくは、おすすめ物件を除外するために、特定のセクション内のみを探索
            main_content = soup.find('div', id='js-bukkenList') or soup
            links = main_content.find_all('a', href=True)
            
            page_urls = set()
            for link in links:
                href = link['href']
                # 駅近辺の検索結果に限定
                if '/ms/chuko/tokyo/' in href and '/nc_' in href:
                    if not href.startswith('http'):
                        href = 'https://suumo.jp' + href
                    if 'bukkengaiyo' not in href:
                        href = href.split('?')[0].rstrip('/') + '/bukkengaiyo/'
                    page_urls.add(href)
            
            print(f"    🔍 {len(page_urls)}件のURLを発見。保存開始...")
            
            for p_url in page_urls:
                result = save_property(p_url, session, scraper)
                if result == "saved":
                    saved_count += 1
                    print(f"      ✅ 保存成功: {p_url.split('/nc_')[1].split('/')[0]}")
                elif result == "exists":
                    pass
            
            time.sleep(CRAWL_INTERVAL)
            
        except Exception as e:
            print(f"    ⚠️ ページエラー: {e}")
            continue
            
    return saved_count

def main():
    print("=" * 60)
    print("🚀 大井町駅 集中収集（駅指定モード）")
    print("=" * 60)
    
    engine = get_engine()
    session = get_session(engine)
    scraper = SuumoScraper(interval=1.0)
    
    total_saved = 0
    
    try:
        for ek_code, config in STATIONS.items():
            print(f"\n{config['name']} の処理を開始")
            count = process_station(ek_code, config, session, scraper)
            total_saved += count
            print(f"  ✨ {config['name']} 完了: +{count}件")
            
    except KeyboardInterrupt:
        print("\n🛑 中断されました")
    finally:
        session.close()
        print("\n" + "=" * 60)
        print(f"🏁 終了。今回のセッションでの新規保存: {total_saved}件")

if __name__ == '__main__':
    main()
