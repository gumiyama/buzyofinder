"""
SUUMOから実際のデータを取得してデータベースに保存するスクリプト
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scrapers.suumo_scraper import SuumoScraper
from src.models.database import init_db, get_session, get_engine, Property
from src.scoring.property_scorer import PropertyScorer
from datetime import datetime
import json

def main():
    print("=" * 60)
    print("SUUMOデータ取得スクリプト")
    print("=" * 60)
    
    # データベース初期化
    print("\n[1/4] データベース初期化中...")
    engine = init_db()
    session = get_session(engine)
    print("✓ データベース初期化完了")
    
    # スクレイパー初期化
    print("\n[2/4] SUUMOスクレイピング開始...")
    scraper = SuumoScraper(interval=3.0)
    
    # 東京都の物件を2ページ分取得（テスト）
    print("対象: 東京都の分譲マンション（最大2ページ）")
    properties = scraper.search_properties('tokyo', max_pages=2)
    
    print(f"✓ {len(properties)}件の物件を発見")
    
    # 詳細データを取得してデータベースに保存
    print("\n[3/4] 物件詳細を取得してデータベースに保存中...")
    saved_count = 0
    
    for idx, prop in enumerate(properties[:10]):  # 最初の10件に制限
        print(f"\n--- 物件 {idx+1}/{min(10, len(properties))} ---")
        print(f"URL: {prop['url']}")
        
        # 詳細データを取得
        detail = scraper.get_property_detail(prop['url'])
        
        if not detail:
            print("⚠ 詳細取得失敗、スキップ")
            continue
        
        # 既存の物件をチェック
        existing = session.query(Property).filter_by(
            source='SUUMO',
            source_id=prop['source_id']
        ).first()
        
        if existing:
            print(f"✓ 既存物件: {detail['title']}")
            continue
        
        # 新規物件を保存
        new_property = Property(
            source=detail['source'],
            source_id=prop['source_id'],
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
        
        print(f"✓ 保存完了: {detail['title']}")
        print(f"  価格: {detail['price']}万円")
        print(f"  面積: {detail['area']}㎡")
        print(f"  駅: {detail['station_name']}駅 徒歩{detail['station_distance']}分")
    
    print(f"\n✓ {saved_count}件の新規物件を保存")
    
    # スコアリング
    print("\n[4/4] スコアリング実行中...")
    all_properties = session.query(Property).filter_by(is_active=True).all()
    
    if all_properties:
        scorer = PropertyScorer()
        
        # 比較対象物件のリストを作成
        comparable_data = []
        for p in all_properties:
            comparable_data.append({
                'price': p.price,
                'area': p.area,
                'price_per_sqm': p.price_per_sqm,
                'building_age': p.building_age,
                'management_fee': p.management_fee,
                'repair_reserve': p.repair_reserve
            })
        
        for prop in all_properties:
            # 物件データを辞書に変換
            prop_data = {
                'title': prop.title,
                'price': prop.price,
                'area': prop.area,
                'price_per_sqm': prop.price_per_sqm,
                'building_age': prop.building_age,
                'floor': prop.floor,
                'direction': prop.direction,
                'layout': prop.layout,
                'address': prop.address,
                'prefecture': prop.prefecture,
                'city': prop.city,
                'station_name': prop.station_name,
                'station_distance': prop.station_distance,
                'management_fee': prop.management_fee,
                'repair_reserve': prop.repair_reserve,
                'features': prop.features
            }
            
            # ファミリー向けスコアを計算
            score_result = scorer.calculate_score(prop_data, 'family', comparable_data)
            
            print(f"✓ {prop.title}: {score_result['total_score']}点")
    
    print("\n" + "=" * 60)
    print("完了！")
    print(f"保存済み物件数: {len(all_properties)}件")
    print("Streamlitアプリを起動して確認してください")
    print("=" * 60)
    
    session.close()


if __name__ == '__main__':
    main()
