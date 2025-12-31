#!/usr/bin/env python
import os
import sys
import time
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.database import get_session, get_engine, Property
from src.scrapers.suumo_scraper import SuumoScraper

def repair():
    engine = get_engine()
    session = get_session(engine)
    scraper = SuumoScraper(interval=1.0)
    
    # 修復対象:
    # 1. 駅距離がNULL または アクセス情報が空
    # 2. 維持費が 0 < x < 100 (1万を1と取ってしまっている可能性が高い)
    targets = session.query(Property).filter(
        (Property.station_distance == None) | 
        (Property.access_info == None) |
        ((Property.management_fee > 0) & (Property.management_fee < 100)) |
        ((Property.repair_reserve > 0) & (Property.repair_reserve < 100)),
        Property.is_active == True
    ).all()
    print(f"🔧 修復対象: {len(targets)}件")
    
    for i, prop in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] {prop.title} ({prop.id}) を再取得中...")
        try:
            detail = scraper.get_property_detail(prop.url)
            if detail:
                prop.station_distance = detail.get('station_distance', prop.station_distance)
                prop.station_name = detail.get('station_name', prop.station_name)
                prop.access_info = detail.get('access_info', prop.access_info)
                prop.management_fee = detail.get('management_fee', prop.management_fee)
                prop.repair_reserve = detail.get('repair_reserve', prop.repair_reserve)
                session.commit()
                print(f"  ✅ 修正: 徒歩{prop.station_distance}分 / 管理費{prop.management_fee}円 / 修繕{prop.repair_reserve}円")
            else:
                print(f"  ⚠️ 取得失敗")
        except Exception as e:
            print(f"  ❌ エラー: {e}")
            session.rollback()
        
        time.sleep(1)
    
    session.close()
    print("\n✅ 修復完了")

if __name__ == '__main__':
    repair()
