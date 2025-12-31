"""
物件URLリストから直接データを取得するスクリプト
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scrapers.suumo_scraper import SuumoScraper
from src.models.database import init_db, get_session, get_engine, Property
from src.scoring.property_scorer import PropertyScorer
from datetime import datetime
import json

# 取得したい物件URLのリスト（千代田区の実在物件）
PROPERTY_URLS = [
    'https://suumo.jp/ms/chuko/tokyo/sc_chiyoda/nc_79091940/',  # エクレール平河町
    'https://suumo.jp/ms/chuko/tokyo/sc_chiyoda/nc_78718664/',  # 朝日九段マンション
    'https://suumo.jp/ms/chuko/tokyo/sc_chiyoda/nc_78958225/',  # ダイアパレス水道橋
    'https://suumo.jp/ms/chuko/tokyo/sc_chiyoda/nc_78119138/',  # ライオンズマンション麹町
    'https://suumo.jp/ms/chuko/tokyo/sc_chiyoda/nc_78833444/',  # ドミール五番町１号棟
]

def main():
    print("=" * 60)
    print("SUUMO物件データ取得（URL直接指定方式）")
    print("=" * 60)
    
    if not PROPERTY_URLS:
        print("\n⚠️  取得する物件URLが指定されていません。")
        print("\nscripts/fetch_from_urls.py の PROPERTY_URLS リストに")
        print("SUUMOの物件URLを追加してください。")
        print("\n例:")
        print("PROPERTY_URLS = [")
        print("    'https://suumo.jp/ms/chuko/tokyo/sc_chiyoda/nc_79091940/',")
        print("    'https://suumo.jp/ms/chuko/tokyo/sc_shibuya/nc_12345678/',")
        print("]")
        return
    
    # データベース初期化
    print("\n[1/3] データベース初期化中...")
    engine = init_db()
    session = get_session(engine)
    print("✓ データベース初期化完了")
    
    # スクレイパー初期化
    print(f"\n[2/3] {len(PROPERTY_URLS)}件の物件データを取得中...")
    scraper = SuumoScraper(interval=3.0)
    
    saved_count = 0
    error_count = 0
    
    for idx, url in enumerate(PROPERTY_URLS):
        print(f"\n--- 物件 {idx+1}/{len(PROPERTY_URLS)} ---")
        print(f"URL: {url}")
        
        # URLから物件IDを抽出
        import re
        match = re.search(r'/nc_(\d+)/', url)
        if not match:
            print("⚠ URLが不正です（nc_XXXXX の形式ではありません）")
            error_count += 1
            continue
        
        property_id = match.group(1)
        
        # 既存の物件をチェック
        existing = session.query(Property).filter_by(
            source='SUUMO',
            source_id=property_id
        ).first()
        
        if existing:
            print(f"✓ 既存物件: {existing.title}")
            print(f"  スキップします")
            continue
        
        # 詳細データを取得
        detail = scraper.get_property_detail(url)
        
        if not detail or not detail.get('price'):
            print("⚠ 詳細取得失敗")
            error_count += 1
            continue
        
        # titleがなければURLから物件IDを使用
        if not detail.get('title'):
            detail['title'] = f"物件 {property_id}"
        
        # 新規物件を保存
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
            
            print(f"✓ 保存完了: {detail['title']}")
            print(f"  価格: {detail.get('price', '不明')}万円")
            print(f"  面積: {detail.get('area', '不明')}㎡")
            if detail.get('station_name'):
                print(f"  駅: {detail['station_name']}駅 徒歩{detail.get('station_distance', '?')}分")
            
        except Exception as e:
            print(f"⚠ 保存エラー: {e}")
            error_count += 1
            session.rollback()
    
    # スコアリング
    print(f"\n[3/3] スコアリング実行中...")
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
    print(f"新規保存: {saved_count}件")
    print(f"エラー: {error_count}件")
    print(f"総物件数: {len(all_properties)}件")
    print("\nStreamlitアプリ（http://localhost:8501）で確認してください")
    print("=" * 60)
    
    session.close()


if __name__ == '__main__':
    main()
