"""
SUUMO scraper for mansion properties - 修正版
"""

import time
import logging
import re
import json
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/suumo_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SuumoScraper:
    """SUUMOから分譲マンション物件情報をスクレイピング"""
    
    BASE_URL = "https://suumo.jp"
    
    def __init__(self, interval: float = 3.0):
        self.interval = interval
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def get_property_detail(self, property_url: str) -> Optional[Dict]:
        """物件詳細ページから詳細情報を取得"""
        try:
            logger.info(f"Fetching property detail: {property_url}")
            
            # 物件概要ページのURLを構築（二重付与防止）
            if 'bukkengaiyo' in property_url:
                bukkengaiyo_url = property_url
            else:
                bukkengaiyo_url = property_url.rstrip('/') + '/bukkengaiyo/'
            
            response = self.session.get(bukkengaiyo_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            detail = self._parse_bukkengaiyo(soup, property_url)
            
            time.sleep(self.interval)
            return detail
            
        except Exception as e:
            logger.error(f"Error fetching property detail: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _parse_bukkengaiyo(self, soup: BeautifulSoup, url: str) -> Dict:
        """物件概要ページから情報を抽出"""
        data = {
            'source': 'SUUMO',
            'url': url,
            'title': '',
            'price': None,
            'area': None,
            'price_per_sqm': None,
            'building_age': None,
            'floor': None,
            'direction': None,
            'layout': None,
            'address': '',
            'prefecture': '',
            'city': '',
            'station_name': '',
            'station_distance': None,
            'management_fee': None,
            'repair_reserve': None,
            'features': {}
        }
        
    def _parse_yen_value(self, value_text: str) -> Optional[int]:
        """「1億2345万円」や「1万4000円」といった形式を数値（円または万円）に変換"""
        if not value_text or value_text == '-':
            return None
            
        # 全角を半角に、カンマを除去、不要な記号を除去
        text = value_text.translate(str.maketrans('０１２３４５６７８９（）／', '0123456789()/'))
        text = text.replace(',', '')
        # 括弧内の除去（「(巡回)」などを消して数値抽出を助ける）
        text = re.sub(r'\(.*?\)', '', text)
        text = re.sub(r'（.*?）', '', text)
        
        total_yen = 0
        
        # 億の処理
        oku_match = re.search(r'(\d+)億', text)
        if oku_match:
            total_yen += int(oku_match.group(1)) * 100000000
        
        # 万の処理
        man_match = re.search(r'(\d+)万', text)
        if man_match:
            total_yen += int(man_match.group(1)) * 10000
            
        # 円の処理（「万」の後に続く数字も含む）
        # 例：「1万4000円」の「4000」
        leftover_match = re.search(r'(?:万|億|^)(\d+)円', text)
        if leftover_match:
            total_yen += int(leftover_match.group(1))
        elif not oku_match and not man_match:
            # 「万」も「億」も「円」もないが数字だけある場合
            num_match = re.search(r'(\d+)', text)
            if num_match:
                total_yen = int(num_match.group(1))
                
        return total_yen if total_yen > 0 else None

    def _parse_bukkengaiyo(self, soup: BeautifulSoup, url: str) -> Dict:
        """物件概要ページから情報を抽出"""
        data = {
            'source': 'SUUMO',
            'url': url,
            'title': '',
            'price': None,
            'area': None,
            'price_per_sqm': None,
            'building_age': None,
            'floor': None,
            'direction': None,
            'layout': None,
            'address': '',
            'prefecture': '',
            'city': '',
            'station_name': '',
            'station_distance': None,
            'management_fee': None,
            'repair_reserve': None,
            'features': {}
        }
        
        try:
            # 物件名の抽出（最新のHTML構造に対応）
            
            # 1. パンくずリストから取得（最もクリーンな名称が取れることが多い）
            breadcrumb_link = soup.select_one('.breadcrumb_item a[href*="/nc_"]') or \
                              soup.select_one('.p-breadcrumb-item a[href*="/nc_"]')
            if breadcrumb_link:
                data['title'] = breadcrumb_link.get_text(strip=True)
            
            # 2. H1から取得（パンくずで取れなかった場合や補完用）
            if not data['title']:
                h1 = soup.select_one('h1.section_h1-header-title') or \
                     soup.select_one('h1.secTitle') or \
                     soup.find('h1')
                if h1:
                    h1_text = h1.get_text(strip=True)
                    # ノイズ除去
                    # 1. 冒頭の宣伝文句（【...】や「...！」）を除去
                    h1_text = re.sub(r'^.*?(!|！|】)\s*', '', h1_text)
                    # 2. 価格情報（...万円/億円/億）以降を、全角スペース含めて除去
                    h1_text = re.sub(r'[\s\u3000]*[\d,]+[万億]円?.*$', '', h1_text)
                    # 3. カッコ内の詳細情報や「（物件概要）」を除去
                    h1_text = re.sub(r'[\(（].*?[\)）]$', '', h1_text)
                    data['title'] = h1_text.strip()
            
            # 3. H2（セクション見出し）から取得
            if not data['title'] or data['title'].isdigit():
                h2 = soup.select_one('h2.section_h2-header-title')
                if h2:
                    t = h2.get_text(strip=True).replace('【マンション】', '').strip()
                    # 宣伝文句の除去
                    data['title'] = re.sub(r'^【.*?】\s*', '', t).strip()

            # テーブル (class="mt10") から情報を抽出
            # ... (中略、以降のテーブルループ内でのタイトル抽出も強化)
            tables = soup.find_all('table', class_='mt10')
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['th', 'td'])
                    
                    i = 0
                    while i < len(cells) - 1:
                        if cells[i].name == 'th' and cells[i+1].name == 'td':
                            label_raw = cells[i].get_text(strip=True)
                            value_raw = cells[i+1].get_text(strip=True)
                            
                            # ノイズ除去
                            label = label_raw.replace('ヒント', '').strip()
                            value = re.sub(r'\[.*?\]', '', value_raw).strip()
                            
                            # 物件名（テーブル内にあれば最優先）
                            if ('物件名' in label or 'マンション名' in label) and (not data['title'] or '物件' in data['title']):
                                data['title'] = value
                            
                            # 価格（億・万円対応）
                            elif '価格' in label:
                                price_yen = self._parse_yen_value(value)
                                if price_yen:
                                    # DBには万円単位で保存
                                    data['price'] = price_yen // 10000
                            
                            # 専有面積
                            elif '専有面積' in label:
                                m = re.search(r'([\d.]+)', value)
                                if m:
                                    data['area'] = float(m.group(1))
                            
                            # 間取り
                            elif '間取り' in label:
                                data['layout'] = value
                            
                            # 築年月 / 完成時期
                            elif '築年月' in label or '完成時期' in label:
                                m = re.search(r'(\d{4})年', value)
                                if m:
                                    age = datetime.now().year - int(m.group(1))
                                    data['building_age'] = max(0, age)  # 0年（築1年未満）も許容
                            
                            # 所在階
                            elif '所在階' in label:
                                m = re.search(r'(\d+)階', value)
                                if m:
                                    data['floor'] = int(m.group(1))
                            
                            # 向き
                            elif any(k in label for k in ['向き', '方角', 'バルコニー']):
                                for d in ['南', '東', '西', '北', '南東', '南西', '北東', '北西']:
                                    if d in value:
                                        data['direction'] = d
                                        break
                            
                            # 所在地
                            elif '所在地' in label:
                                data['address'] = value
                                for pref in ['東京都', '神奈川県', '埼玉県', '千葉県']:
                                    if pref in value:
                                        data['prefecture'] = pref
                                        break
                                m = re.search(r'[都県](.+?区|.+?市)', value)
                                if m:
                                    data['city'] = m.group(1)
                            
                            # 交通
                            elif '交通' in label:
                                # brタグなどを改行として取得
                                value_lines = cells[i+1].get_text(separator='\n').split('\n')
                                
                                best_distance = float('inf')
                                best_station = ""
                                access_info_list = []
                                
                                for line in value_lines:
                                    # 不要な記号と空白を極力排除
                                    line_clean = re.sub(r'[\s\]\[「」]+', ' ', line).strip()
                                    if not line_clean or '乗り換え案内' in line_clean or '地図' in line_clean:
                                        continue
                                    
                                    # 駅名と路線のパターンを再構成して保存
                                    # 例: 東京メトロ千代田線「代々木公園」歩3分 -> 東京メトロ千代田線 代々木公園 歩3分
                                    m_all = re.search(r'(.+?)\s*(?:歩|徒歩)(\d+)分', line_clean)
                                    if m_all:
                                        info_str = f"{m_all.group(1)} 徒歩{m_all.group(2)}分"
                                        access_info_list.append(info_str)
                                        
                                        # 最小距離の更新用
                                        dist = int(m_all.group(2))
                                        if dist < best_distance:
                                            best_distance = dist
                                            # 駅名だけを抽出（あれば）
                                            m_name = re.search(r'」*(.+?)$', m_all.group(1))
                                            best_station = m_name.group(1).split()[-1] if m_name else m_all.group(1)
                                
                                if best_distance != float('inf'):
                                    data['station_name'] = best_station
                                    data['station_distance'] = best_distance
                                
                                if access_info_list:
                                    data['access_info'] = '\n'.join(access_info_list)
                            
                            # 管理費
                            elif '管理費' in label:
                                data['management_fee'] = self._parse_yen_value(value)
                            
                            # 修繕積立金
                            elif '修繕積立金' in label:
                                data['repair_reserve'] = self._parse_yen_value(value)
                            
                            i += 2
                        else:
                            i += 1
            
            # ㎡単価を計算
            if data['price'] and data['area']:
                data['price_per_sqm'] = (data['price'] * 10000) / data['area']
            
            # 設備情報
            page_text = soup.get_text()
            features = {}
            if 'オートロック' in page_text:
                features['auto_lock'] = True
            if 'ペット' in page_text and '可' in page_text:
                features['pet_ok'] = True
            if '宅配ボックス' in page_text or '宅配BOX' in page_text:
                features['delivery_box'] = True
            
            data['features'] = json.dumps(features, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Parse error: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return data
