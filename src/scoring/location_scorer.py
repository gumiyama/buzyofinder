"""
立地スコア算出モジュール
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class LocationScorer:
    """立地スコアを算出（25点満点）"""
    
    MAX_SCORE = 25.0
    
    def calculate(self, property_data: Dict) -> Dict[str, float]:
        """
        立地スコアを算出
        
        Args:
            property_data: 物件データ
            
        Returns:
            スコア詳細
        """
        scores = {
            'station_score': 0.0,    # 駅距離スコア（10点）
            'facility_score': 0.0,   # 周辺施設スコア（8点）
            'area_score': 0.0,       # エリアブランドスコア（7点）
            'score': 0.0             # 合計
        }
        
        try:
            # 1. 駅距離スコア（10点）
            scores['station_score'] = self._calculate_station_score(
                property_data.get('station_distance')
            )
            
            # 2. 周辺施設スコア（8点）- 現時点では簡易実装
            scores['facility_score'] = self._calculate_facility_score(
                property_data
            )
            
            # 3. エリアブランドスコア（7点）- 現時点では簡易実装
            scores['area_score'] = self._calculate_area_score(property_data)
            
            # 合計
            scores['score'] = min(
                scores['station_score'] + scores['facility_score'] + scores['area_score'],
                self.MAX_SCORE
            )
            
        except Exception as e:
            logger.error(f"Error calculating location score: {e}")
        
        return scores
    
    def _calculate_station_score(self, station_distance: int) -> float:
        """
        駅距離スコア算出（10点満点）
        
        利便性の高い駅近（10分以内）を重視
        """
        if station_distance is None:
            return 5.0  # データなしの場合は中間点
        
        # 基本スコア
        if station_distance <= 5:
            base_score = 10.0
        elif station_distance <= 10:
            base_score = 7.0
        elif station_distance <= 15:
            base_score = 4.0
        elif station_distance <= 20:
            base_score = 2.0
        else:
            base_score = max(0.0, 10.0 - (station_distance - 20) * 0.5)
        
        # 駅近（10分以内）は利便性を評価し1.1倍ボーナス
        if station_distance <= 10:
            base_score = min(10.0, base_score * 1.1)
        
        return base_score
    
    def _calculate_facility_score(self, property_data: Dict) -> float:
        """
        周辺施設スコア算出（8点満点）
        """
        # 簡易実装：主要エリアにボーナス
        address = property_data.get('address', '')
        city = property_data.get('city', '')
        
        score = 4.0  # ベーススコア
        
        # 主要ターミナル駅周辺にボーナス
        major_terminal_areas = ['渋谷', '新宿', '池袋', '品川', '横浜', '大宮']
        if any(area in address or area in city for area in major_terminal_areas):
            score += 2.0
        
        # 文教・生活利便・商業エリアの統合判定
        high_potential_areas = [
            '文京区', '目黒区', '世田谷区', '杉並区', '武蔵野市', # 生活・文教
            '港区', '中央区', '千代田区' # 商業・中心地
        ]
        if any(area in address for area in high_potential_areas):
            score += 2.0
        
        return min(8.0, score)
    
    def _calculate_area_score(self, property_data: Dict) -> float:
        """
        エリアブランドスコア算出（7点満点）
        
        現時点では簡易実装（人気エリアの判定）
        """
        address = property_data.get('address', '')
        prefecture = property_data.get('prefecture', '')
        city = property_data.get('city', '')
        
        score = 3.5  # ベーススコア
        
        # 人気エリア判定（ティア1）
        tier1_areas = [
            '港区', '渋谷区', '目黒区', '世田谷区', '文京区',
            'みなとみらい', '武蔵小杉'
        ]
        
        # 人気エリア判定（ティア2）
        tier2_areas = [
            '品川区', '新宿区', '中野区', '杉並区', '大田区',
            '横浜市西区', '横浜市中区', '川崎市中原区',
            'さいたま市浦和区', '千葉市中央区'
        ]
        
        for area in tier1_areas:
            if area in address or area in city:
                score = 7.0
                break
        
        if score == 3.5:  # ティア1でない場合
            for area in tier2_areas:
                if area in address or area in city:
                    score = 5.5
                    break
        
        return score
