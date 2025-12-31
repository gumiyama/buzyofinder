"""
URLファイルから物件データを一括取得するスクリプト
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scrapers.suumo_scraper import SuumoScraper
from src.models.database import init_db, get_session, Property
from datetime import datetime
import re


def main():
    if len(sys.argv) < 2:
        print("使い方: python scripts/fetch_from_url_file.py <URLファイル>")
        print("例: python scripts/fetch_from_url_file.py collected_property_urls.txt")
        return
    
    url_file = sys.argv[1]
    
    if not os.path.exists(url_file):
        print(f"⚠ ファイルが見つかりません: {url_file}")
        return
    
    # URLを読み込み
    with open(url_file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    print("=" * 60)
    print(f"物件データ一括取得")
    print(f"対象: {len(urls)}件")
    print("=" * 60)
    
    # データベース初期化
    print("\n[1/2] データベース初期化中...")
    engine = init_db()
    session = get_session(engine)
    print("✓ 完了")
    
    # スクレイパー初期化
    print(f"\n[2/2] {len(urls)}件の物件データを取得中...")
    scraper = SuumoScraper(interval=3.0)
    
    saved_count = 0
    skipped_count = 0
    error_count = 0
    
    for idx, url in enumerate(urls, 1):
        print(f"\n--- {idx}/{len(urls)} ---")
        
        # URLから物件IDを抽出
        match = re.search(r'/nc_(\d+)/', url)
        if not match:
            print(f"⚠ URL形式が不正: {url}")
            error_count += 1
            continue
        
        property_id = match.group(1)
        
        # 既存チェック
        existing = session.query(Property).filter_by(
            source='SUUMO',
            source_id=property_id
        ).first()
        
        if existing:
            print(f"  スキップ（既存）: {existing.title or property_id}")
            skipped_count += 1
            continue
        
        # データ取得
        detail = scraper.get_property_detail(url)
        
        if not detail or not detail.get('price'):
            print(f"  ⚠ 取得失敗: {url}")
            error_count += 1
            continue
        
        # titleフォールバック
        if not detail.get('title'):
            detail['title'] = f"物件 {property_id}"
        
        # 保存
        try:
            new_property = Property(
                source=detail['source'],
                source_id=property_id,
                url=detail['url'],
                title=detail['title'],
                price=detail['price'],
                area=detail['area'],
                price_per_sqm=detail['price_per_sqm'],
                building_age=detail['building_age'],
                floor=detail['floor'],
                direction=detail['direction'],
                layout=detail['layout'],
                address=detail['address'],
                prefecture=detail['prefecture'],
                city=detail['city'],
                station_name=detail['station_name'],
                station_distance=detail['station_distance'],
                management_fee=detail['management_fee'],
                repair_reserve=detail['repair_reserve'],
                features=detail['features'],
                first_seen=datetime.now(),
                last_updated=datetime.now(),
                is_active=True
            )
            
            session.add(new_property)
            session.commit()
            saved_count += 1
            
            print(f"  ✓ 保存: {detail['title']}")
            print(f"     {detail['price']:,}万円 / {detail['area']}㎡")
            
        except Exception as e:
            print(f"  ⚠ 保存エラー: {e}")
            error_count += 1
            session.rollback()
    
    # 結果表示
    print("\n" + "=" * 60)
    print("完了！")
    print(f"新規保存: {saved_count}件")
    print(f"スキップ: {skipped_count}件")
    print(f"エラー: {error_count}件")
    print(f"総物件数: {session.query(Property).filter_by(is_active=True).count()}件")
    print("\nStreamlitアプリで確認: http://localhost:8501")
    print("=" * 60)
    
    session.close()


if __name__ == '__main__':
    main()
