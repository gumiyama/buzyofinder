#!/usr/bin/env python
"""
自動データ収集スクリプト
5分毎に新規物件を収集してデータベースに追加
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
from src.models.database import get_session, get_engine, Property

# エリアのローテーション# エリア設定
AREAS = {
    'chiyoda': {'pages': 5, 'name': '千代田区', 'url': 'https://suumo.jp/ms/chuko/tokyo/sc_chiyoda/'},
    'shibuya': {'pages': 5, 'name': '渋谷区', 'url': 'https://suumo.jp/ms/chuko/tokyo/sc_shibuya/'},
    'minato': {'pages': 5, 'name': '港区', 'url': 'https://suumo.jp/ms/chuko/tokyo/sc_minato/'},
    'shinjuku': {'pages': 5, 'name': '新宿区', 'url': 'https://suumo.jp/ms/chuko/tokyo/sc_shinjuku/'},
    'meguro': {'pages': 5, 'name': '目黒区', 'url': 'https://suumo.jp/ms/chuko/tokyo/sc_meguro/'},
}

INTERVAL = 1 * 60  # 1分（秒単位）
CRAWL_INTERVAL = 3.0  # スクレイピング間隔


def collect_urls_from_area(area_config):
    """エリアから物件URLを収集"""
    scraper = SuumoScraper()
    urls = set()
    
    for page in range(1, area_config['pages'] + 1):
        try:
            if page == 1:
                url = area_config['url']
            else:
                url = f"{area_config['url']}?page={page}"
            
            html = scraper._fetch_html(url)
            if not html:
                continue
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link['href']
                if '/ms/chuko/tokyo/' in href and '/nc_' in href:
                    if not href.startswith('http'):
                        href = 'https://suumo.jp' + href
                    if 'bukkengaiyo' not in href:
                        href = href.split('?')[0]
                        if not href.endswith('/'):
                            href += '/'
                        href += 'bukkengaiyo/'
                    urls.add(href)
            
            time.sleep(CRAWL_INTERVAL)
        except Exception as e:
            print(f"  エラー: {e}")
            continue
    
    return urls


def save_property(url, session):
    """物件データを取得してDBに保存"""
    scraper = SuumoScraper()
    
    try:
        detail = scraper.get_property_detail(url)
        if not detail or not detail.get('price'):
            return False
        
        # source_idを抽出
        source_id = url.split('/nc_')[1].split('/')[0] if '/nc_' in url else None
        if not source_id:
            return False
        
        # 既存チェック
        existing = session.query(Property).filter_by(source_id=source_id).first()
        if existing:
            return False  # スキップ
        
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
            management_fee=detail.get('management_fee'),
            repair_reserve=detail.get('repair_reserve'),
            features=str(detail.get('features', {})),
            is_active=True
        )
        
        session.add(property_obj)
        session.commit()
        return True
        
    except Exception as e:
        print(f"  保存エラー: {e}")
        return False


def auto_collect_cycle():
    """1サイクルの自動収集"""
    print("\n" + "=" * 60)
    print(f"自動収集開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    session = get_session(get_engine())
    total_new = 0
    
    for area in AREAS:
        print(f"\n📍 {area['name']} から収集中...")
        urls = collect_urls_from_area(area)
        print(f"  URL発見: {len(urls)}件")
        
        new_count = 0
        for url in urls:
            if save_property(url, session):
                new_count += 1
                print(f"  ✓ 新規保存 [{new_count}件目]")
            time.sleep(CRAWL_INTERVAL)
        
        total_new += new_count
        print(f"  {area['name']}: {new_count}件追加")
    
    # 現在の総件数
    total_count = session.query(Property).filter_by(is_active=True).count()
    
    print("\n" + "=" * 60)
    print(f"サイクル完了: {total_new}件追加")
    print(f"総物件数: {total_count}件")
    print("=" * 60)
    
    session.close()


def main():
    print("=" * 60)
    print("🤖 自動データ収集システム")
    print("1分毎に新規物件を自動収集")
    print("停止するには Ctrl+C を押してください")
    print("=" * 60)
    
    cycle_count = 0
    
    try:
        while True:
            cycle_count += 1
            print(f"\n【サイクル {cycle_count}】")
            
            auto_collect_cycle()
            
            # 次のサイクルまで待機
            next_time = datetime.now()
            next_time = next_time.replace(second=0, microsecond=0)
            from datetime import timedelta
            next_time += timedelta(minutes=1)
            
            print(f"\n⏰ 次回実行: {next_time.strftime('%H:%M')}")
            print(f"   待機中... (1分)")
            
            time.sleep(INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n停止しました。")
        print(f"実行サイクル数: {cycle_count}")


if __name__ == '__main__':
    main()
