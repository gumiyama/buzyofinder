"""
単一物件のテストスクリプト
"""
import sys
sys.path.insert(0, '/Users/takaakikawabe/.gemini/antigravity/scratch/mansion-scientist')

from src.scrapers.suumo_scraper import SuumoScraper
import json

scraper = SuumoScraper(interval=1.0)
url = 'https://suumo.jp/ms/chuko/tokyo/sc_chiyoda/nc_79091940/'

print(f"テスト: {url}")
result = scraper.get_property_detail(url)

if result:
    print("\n=== 成功 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
else:
    print("\n=== 失敗 ===")
    print("Noneが返されました")
