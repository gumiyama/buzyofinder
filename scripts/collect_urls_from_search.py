"""
SUUMOの検索ページから物件URLを自動収集するスクリプト
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import re
from bs4 import BeautifulSoup
import requests

# 設定
BASE_URL = "https://suumo.jp"
INTERVAL = 3.0  # リクエスト間隔（秒）

# エリア別の検索URL（中古マンション）
# 注: これは仮のURLです実際にはブラウザで検索して正しいURLを確認してください
SEARCH_URLS = {
    'all_tokyo': 'https://suumo.jp/ms/chuko/tokyo/city/',  # 東京都全域
    'chiyoda': 'https://suumo.jp/ms/chuko/tokyo/sc_chiyoda/',  # 千代田区  
    'shibuya': 'https://suumo.jp/ms/chuko/tokyo/sc_shibuya/',  # 渋谷区
    'shinjuku': 'https://suumo.jp/ms/chuko/tokyo/sc_shinjuku/',  # 新宿区
    'minato': 'https://suumo.jp/ms/chuko/tokyo/sc_minato/',  # 港区
    'meguro': 'https://suumo.jp/ms/chuko/tokyo/sc_meguro/',  # 目黒区
}


def collect_urls_from_page(url, max_pages=5):
    """
    検索ページから物件URLを収集
    
    Args:
        url: 検索ページのURL
        max_pages: 最大ページ数
    
    Returns:
        物件URLのリスト
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    
    all_urls = []
    
    for page in range(1, max_pages + 1):
        # ページ番号付きURL
        page_url = f"{url}&page={page}" if page > 1 else url
        
        print(f"📄 ページ {page}/{max_pages} を取得中...")
        
        try:
            response = session.get(page_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # 物件カードから詳細ページURLを抽出
            property_cards = soup.find_all('div', class_='property_unit')
            
            count = 0
            for card in property_cards:
                # h2.property_unit-title a からURLを取得
                title_elem = card.find('h2', class_='property_unit-title')
                if title_elem:
                    link = title_elem.find('a')
                    if link and 'href' in link.attrs:
                        property_url = link['href']
                        
                        # 相対URLを絶対URLに変換
                        if property_url.startswith('/'):
                            property_url = BASE_URL + property_url
                        
                        # /nc_XXXXX/ の形式をチェック
                        if '/nc_' in property_url:
                            all_urls.append(property_url)
                            count += 1
            
            print(f"  ✓ {count}件の物件URLを発見")
            
            if count == 0:
                print(f"  これ以上物件が見つかりません。")
                break
            
            # レート制限
            time.sleep(INTERVAL)
            
        except Exception as e:
            print(f"  ⚠ エラー: {e}")
            break
    
    return all_urls


def main():
    print("=" * 60)
    print("SUUMO物件URL収集スクリプト")
    print("=" * 60)
    
    # エリア選択
    print("\n📍 収集するエリアを選択してください:")
    print("  1. 千代田区")
    print("  2. 渋谷区")
    print("  3. 新宿区")
    print("  4. 港区")
    print("  5. 目黒区")
    print("  6. すべて")
    
    choice = input("\n選択 (1-6): ").strip()
    
    area_map = {
        '1': ['chiyoda'],
        '2': ['shibuya'],
        '3': ['shinjuku'],
        '4': ['minato'],
        '5': ['meguro'],
        '6': ['chiyoda', 'shibuya', 'shinjuku', 'minato', 'meguro']
    }
    
    if choice not in area_map:
        print("⚠ 無効な選択です")
        return
    
    areas = area_map[choice]
    
    # ページ数入力
    max_pages = input("\n各エリアで取得するページ数 (デフォルト: 5): ").strip()
    max_pages = int(max_pages) if max_pages.isdigit() else 5
    
    # URL収集
    all_property_urls = []
    
    for area in areas:
        print(f"\n🏙️ {area} の物件URLを収集中...")
        urls = collect_urls_from_page(SEARCH_URLS[area], max_pages)
        all_property_urls.extend(urls)
        print(f"  合計 {len(urls)}件")
    
    # 重複削除
    unique_urls = list(set(all_property_urls))
    
    print("\n" + "=" * 60)
    print(f"収集完了！合計 {len(unique_urls)}件の物件URL")
    print("=" * 60)
    
    # ファイルに保存
    output_file = 'collected_property_urls.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        for url in unique_urls:
            f.write(url + '\n')
    
    print(f"\n💾 {output_file} に保存しました")
    print("\n次のステップ:")
    print(f"  python scripts/fetch_from_url_file.py {output_file}")


if __name__ == '__main__':
    main()
