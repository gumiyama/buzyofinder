#!/usr/bin/env python
import os
import sys
import time
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.database import get_session, get_engine
from src.scrapers.suumo_scraper import SuumoScraper
from scripts.collect_tokyo23 import process_area

# 大井町（品川区）を集中的に
# 大井町は品川区の中心的なエリアなので、品川区を深く掘ることで網羅できる
AREAS = {
    'shinagawa': {'pages': 40, 'name': '品川区（大井町中心）'}, # 40ページ分ガッツリ取る
}

def main():
    print("=" * 60)
    print("🚀 大井町（品川区）集中収集モード")
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
