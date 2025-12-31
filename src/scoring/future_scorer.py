"""
将来性・流動性スコア算出モジュール
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class FutureScorer:
    """将来性・流動性スコアを算出（5点満点）"""
    
    MAX_SCORE = 5.0
    
    # 大手ブランドマップ
    BRAND_MAP = {
        '三井不動産': ['パークホームズ', 'パークタワー', 'パークコート', 'パークマンション'],
        '三菱地所': ['パークハウス', 'ザ・パークハウス'],
        '住友不動産': ['シティハウス', 'シティタワー', 'グランドヒルズ', 'シティテラス'],
        '野村不動産': ['プラウド', 'PROUD'],
        '東急不動産': ['ブランズ', 'BRANZ'],
        '東京建物': ['ブリリア', 'Brillia'],
        '旭化成': ['アトラス', 'ATLAS']
    }
    
    def calculate(self, property_data: Dict) -> Dict[str, float]:
        """将来性・流動性スコアを算出"""
        scores = {
            'location_asset_score': 0.0,  # 立地資産性 (2.0)
            'brand_score': 0.0,           # ブランド価値 (1.0)
            'management_score': 0.0,      # 管理健全性 (1.0)
            'area_score': 0.0,            # エリア再開発期待 (1.0)
            'score': 0.0
        }
        
        try:
            # 1. 立地資産性 (2.0点)
            scores['location_asset_score'] = self._calculate_location_asset_score(property_data)
            
            # 2. ブランド価値 (1.0点)
            scores['brand_score'] = self._calculate_brand_score(property_data)
            
            # 3. 管理健全性 (1.0点)
            scores['management_score'] = self._calculate_management_score(property_data)
            
            # 4. エリア・再開発 (1.0点)
            scores['area_score'] = self._calculate_area_score(property_data)
            
            # 合計
            total = (
                scores['location_asset_score'] + 
                scores['brand_score'] + 
                scores['management_score'] + 
                scores['area_score']
            )
            scores['score'] = min(total, self.MAX_SCORE)
            
        except Exception as e:
            logger.error(f"Error calculating future score: {e}")
        
        return scores
    
    def _calculate_location_asset_score(self, property_data: Dict) -> float:
        """立地資産性算出 (2.0点満点)"""
        score = 0.0
        dist = property_data.get('station_distance')
        
        # 駅距離の希少性 (1.5点)
        if dist is not None:
            if dist <= 1: score += 1.5
            elif dist <= 3: score += 1.3
            elif dist <= 5: score += 1.0
            elif dist <= 7: score += 0.7
            elif dist <= 10: score += 0.4
        else:
            score += 0.5
            
        # 都心5区ボーナス (0.5点)
        address = property_data.get('address', '')
        central_wards = ['千代田区', '中央区', '港区', '新宿区', '渋谷区']
        if any(ward in address for ward in central_wards):
            score += 0.5
            
        return min(2.0, score)
    
    def _calculate_brand_score(self, property_data: Dict) -> float:
        """ブランド価値算出 (1.0点満点)"""
        title = property_data.get('title', '')
        
        # タイトルから大手ブランドを検索
        for developer, series in self.BRAND_MAP.items():
            if any(s in title for s in series):
                return 1.0
                
        # 準大手・その他優良デベロッパー（簡易）
        sub_brands = ['クレヴィア', 'ライオンズ', 'ピアース', 'ディアナ']
        if any(sb in title for sb in sub_brands):
            return 0.7
            
        return 0.3
        
    def _calculate_management_score(self, property_data: Dict) -> float:
        """管理健全性算出 (1.0点満点)"""
        m_fee = property_data.get('management_fee')
        r_fee = property_data.get('repair_reserve')
        
        if not m_fee or not r_fee:
            return 0.5 # 不明な場合は標準点
            
        # 修繕積立金と管理費の比率を評価
        # 一般的に修繕積立金が管理費の0.8倍〜1.5倍程度だと健全
        ratio = r_fee / m_fee if m_fee > 0 else 0
        
        if 0.8 <= ratio <= 1.5:
            return 1.0
        elif 0.5 <= ratio <= 2.0:
            return 0.8
        elif ratio < 0.3:
            return 0.3 # 少なすぎて将来の不安
        else:
            return 0.6 # 比率が歪
            
    def _calculate_area_score(self, property_data: Dict) -> float:
        """エリア・再開発期待算出 (1.0点満点)"""
        address = property_data.get('address', '')
        
        # 再開発重点エリア
        dev_map = {
            '品川': 1.0, '高輪': 1.0, '虎ノ門': 1.0, '麻布台': 1.0,
            '渋谷': 1.0, '日本橋': 0.9, '八重洲': 0.9, '中野': 0.8,
            '下北沢': 0.8, '池袋': 0.7, '晴海': 0.7, '勝どき': 0.7
        }
        
        for area, point in dev_map.items():
            if area in address:
                return point
        
        # 23区内であれば基礎点
        if '区' in address:
            return 0.5
            
        return 0.3
