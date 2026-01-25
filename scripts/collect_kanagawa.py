#!/usr/bin/env python
import os
import sys
import time
from pathlib import Path
import requests

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.database import get_session, get_engine, Property, save_or_update_property
from src.scrapers.suumo_scraper import SuumoScraper

# 神奈川県（武蔵小杉・鷺沼）の設定
AREAS = {
    'kawasakishinakahara': {'pages': 20, 'name': '川崎市中原区（武蔵小杉など）'},
    'kawasakishimiyamae': {'pages': 20, 'name': '川崎市宮前区（鷺沼など）'},
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

def process_area(area_code, config, session, scraper):
    """神奈川県版: 指定エリアを巡回"""
    # ⚠️ ここが重要: URLパターンが神奈川県版 (kanagawa) になっている
    base_url = f'https://suumo.jp/ms/chuko/kanagawa/sc_{area_code}/'
    pages = config['pages']
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    saved_count = 0
    
    for page in range(1, pages + 1):
        try:
            url = base_url if page == 1 else f"{base_url}?page={page}"
            print(f"  📄 ページ {page}/{pages} をスキャン中... ({config['name']})")
            
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                print(f"    ❌ HTTP {response.status_code}")
                # 404ならそのページ以降はない可能性が高いが、念のためcontinue
                continue
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            page_urls = set()
            for link in links:
                href = link['href']
                # 神奈川URLパターンにマッチさせる
                if '/ms/chuko/kanagawa/' in href and '/nc_' in href:
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
            
            time.sleep(CRAWL_INTERVAL)
            
        except Exception as e:
            print(f"    ⚠️ ページエラー: {e}")
            continue
            
    return saved_count

def main():
    print("=" * 60)
    print("🚀 神奈川（武蔵小杉・鷺沼）集中収集")
    print("=" * 60)
    
    engine = get_engine()
    session = get_session(engine)
    scraper = SuumoScraper(interval=1.0)
    
    total_saved = 0
    
    try:
        for area_code, config in AREAS.items():
            print(f"\n{config['name']} の処理を開始")
            count = process_area(area_code, config, session, scraper)
            total_saved += count
            print(f"  ✨ {config['name']} 完了: +{count}件")
            
    except KeyboardInterrupt:
        print("\n🛑 中断されました")
    finally:
        session.close()
        print("\n" + "=" * 60)
        print(f"🏁 終了。新規保存: {total_saved}件")

if __name__ == '__main__':
    main()
