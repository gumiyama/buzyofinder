"""
物件名（タイトル）の修復スクリプト
"""

import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.getcwd())

from sqlalchemy import func
from src.models.database import get_engine, get_session, Property
from src.scrapers.suumo_scraper import SuumoScraper
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def repair_titles():
    engine = get_engine()
    session = get_session(engine)
    scraper = SuumoScraper(interval=1.0)
    
    # 修復対象：
    # 1. タイトルが空、または「物件 」で始まるもの
    # タイトルが「物件...」または向きがNULLのものを対象にする
    properties_to_repair = session.query(Property).filter(
        (Property.title.like('物件 %')) | (Property.direction.is_(None))
    ).filter(Property.is_active == True).all()
    
    logger.info(f"Repair targets: {len(properties_to_repair)} properties (Missing Title or Direction)")
    
    repaired_count = 0
    for prop in properties_to_repair:
        try:
            logger.info(f"Repairing: {prop.source_id} (Current: {prop.title}, Direction: {prop.direction})")
            
            # 再取得
            detail = scraper.get_property_detail(prop.url)
            
            if detail and detail.get('title') and not detail['title'].startswith('物件 '):
                old_title = prop.title
                prop.title = detail['title']
                
                # 他の項目もついでに最新化（特に将来性に関連するブランド名判定に重要）
                if detail.get('management_fee'):
                    prop.management_fee = detail['management_fee']
                if detail.get('repair_reserve'):
                    prop.repair_reserve = detail['repair_reserve']
                if detail.get('access_info'):
                    prop.access_info = detail['access_info']
                if detail.get('direction'):
                    prop.direction = detail['direction']
                if detail.get('floor'):
                    prop.floor = detail['floor']
                if detail.get('station_name'):
                    prop.station_name = detail['station_name']
                
                session.commit()
                logger.info(f"Successfully repaired: {old_title} -> {prop.title}")
                repaired_count += 1
            else:
                logger.warning(f"Could not get clean title for {prop.source_id}. Got: {detail.get('title') if detail else 'None'}")
            
            # サーバー負荷軽減
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error repairing property {prop.id}: {e}")
            session.rollback()
            
    session.close()
    logger.info(f"Title repair completed. Repaired {repaired_count} properties.")

if __name__ == "__main__":
    repair_titles()
