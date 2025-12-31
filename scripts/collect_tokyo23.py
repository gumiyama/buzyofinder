#!/usr/bin/env python
"""
大規模データ収集スクリプト
東京23区すべてから物件データを収集して500件以上を目指す
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.database import get_session, get_engine, Property
from src.scrapers.suumo_scraper import SuumoScraper
import requests

# 東京23区の設定
AREAS = {
    'chiyoda': {'pages': 10, 'name': '千代田区'},
    'chuo': {'pages': 10, 'name': '中央区'},
    'minato': {'pages': 10, 'name': '港区'},
    'shinjuku': {'pages': 10, 'name': '新宿区'},
    'bunkyo': {'pages': 10, 'name': '文京区'},
    'taito': {'pages': 10, 'name': '台東区'},
    'sumida': {'pages': 10, 'name': '墨田区'},
    'koto': {'pages': 10, 'name': '江東区'},
    'shinagawa': {'pages': 10, 'name': '品川区'},
    'meguro': {'pages': 10, 'name': '目黒区'},
    'ota': {'pages': 10, 'name': '大田区'},
    'setagaya': {'pages': 10, 'name': '世田谷区'},
    'shibuya': {'pages': 10, 'name': '渋谷区'},
    'nakano': {'pages': 10, 'name': '中野区'},
    'suginami': {'pages': 10, 'name': '杉並区'},
    'toshima': {'pages': 10, 'name': '豊島区'},
    'kita': {'pages': 10, 'name': '北区'},
    'arakawa': {'pages': 10, 'name': '荒川区'},
    'itabashi': {'pages': 10, 'name': '板橋区'},
    'nerima': {'pages': 10, 'name': '練馬区'},
    'adachi': {'pages': 10, 'name': '足立区'},
    'katsushika': {'pages': 10, 'name': '葛飾区'},
    'edogawa': {'pages': 10, 'name': '江戸川区'},
}

CRAWL_INTERVAL = 3.0  # スクレイピング間隔

def save_property(url, session, scraper):
    """URLから物件情報を取得して保存"""
    try:
        # source_idを抽出
        source_id = url.split('/nc_')[1].split('/')[0] if '/nc_' in url else None
        if not source_id:
            return "skip"
        
        # 既存チェック
        existing = session.query(Property).filter_by(source_id=source_id).first()
        if existing:
            return "exists"
        
        # 詳細取得
        detail = scraper.get_property_detail(url)
        if not detail or not detail.get('price'):
            return "error"
        
        # 新規保存
        property_obj = Property(
            source='SUUMO',
            source_id=source_id,
            url=url,
            title=detail.get('title') or f'物件 {source_id}',
            price=detail.get('price'),
            area=detail.get('area'),
            price_per_sqm=detail.get('price_per_sqm'),
            layout=detail.get('layout'),
            building_age=detail.get('building_age'),
            floor=detail.get('floor'),
            direction=detail.get('direction'),
            address=detail.get('address'),
            prefecture=detail.get('prefecture'),
            city=detail.get('city'),
            station_name=detail.get('station_name'),
            station_distance=detail.get('station_distance'),
            access_info=detail.get('access_info'),
            management_fee=detail.get('management_fee'),
            repair_reserve=detail.get('repair_reserve'),
            features=detail.get('features', '{}'),
            is_active=True
        )
        
        session.add(property_obj)
        session.commit()
        return "saved"
        
    except Exception as e:
        print(f"      ❌ 保存エラー ({url}): {e}")
        session.rollback()
        return "error"

def process_area(area_code, config, session, scraper):
    """区ごとにページを巡回し、見つけ次第保存"""
    base_url = f'https://suumo.jp/ms/chuko/tokyo/sc_{area_code}/'
    pages = config['pages']
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    saved_count = 0
    
    for page in range(1, pages + 1):
        try:
            url = base_url if page == 1 else f"{base_url}?page={page}"
            print(f"  📄 ページ {page}/{pages} をスキャン中...")
            
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                print(f"    ❌ HTTP {response.status_code}")
                continue
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            page_urls = set()
            for link in links:
                href = link['href']
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
                    pass # 冗長なので出力しない
            
            time.sleep(CRAWL_INTERVAL)
            
        except Exception as e:
            print(f"    ⚠️ ページエラー: {e}")
            continue
            
    return saved_count

def main():
    print("=" * 60)
    print("🚀 超高速インクリメンタル収集（目標: 500件以上）")
    print("見つけ次第DBにコミットします。Streamlitでリアルタイムに確認可能")
    print("=" * 60)
    
    engine = get_engine()
    session = get_session(engine)
    scraper = SuumoScraper(interval=1.0) # 加速
    
    total_saved = 0
    
    try:
        for idx, (area_code, config) in enumerate(AREAS.items(), 1):
            print(f"\n[{idx}/23] {config['name']} の処理を開始")
            count = process_area(area_code, config, session, scraper)
            total_saved += count
            print(f"  ✨ {config['name']} 完了: +{count}件 (合計: {total_saved}件)")
            
    except KeyboardInterrupt:
        print("\n🛑 中断されました")
    finally:
        session.close()
        print("\n" + "=" * 60)
        print(f"🏁 終了。今回のセッションでの新規保存: {total_saved}件")
        print("=" * 60)

if __name__ == '__main__':
    main()
