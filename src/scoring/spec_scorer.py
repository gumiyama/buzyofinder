"""
物件スペックスコア算出モジュール
"""

import logging
import json
from typing import Dict

logger = logging.getLogger(__name__)


class SpecScorer:
    """物件スペックスコアを算出（25点満点）"""
    
    MAX_SCORE = 25.0
    
    def calculate(self, property_data: Dict) -> Dict[str, float]:
        """
        物件スペックスコアを算出
        
        Args:
            property_data: 物件データ
            
        Returns:
            スコア詳細
        """
        scores = {
            'age_score': 0.0,        # 築年数スコア（8点）
            'area_score': 0.0,       # 専有面積スコア（5点）
            'floor_score': 0.0,      # 階数・向きスコア（5点）
            'equipment_score': 0.0,  # 設備スコア（7点）
            'score': 0.0             # 合計
        }
        
        try:
            # 1. 築年数スコア（8点）
            scores['age_score'] = self._calculate_age_score(property_data.get('building_age'))
            
            # 2. 専有面積スコア（5点）
            scores['area_score'] = self._calculate_area_score(
                property_data.get('area'),
                property_data.get('layout')
            )
            
            # 3. 階数・向きスコア（5点）
            scores['floor_score'] = self._calculate_floor_score(
                property_data.get('floor'),
                property_data.get('direction')
            )
            
            # 4. 設備スコア（7点）
            scores['equipment_score'] = self._calculate_equipment_score(
                property_data.get('features')
            )
            
            # 合計
            scores['score'] = min(
                scores['age_score'] + scores['area_score'] + 
                scores['floor_score'] + scores['equipment_score'],
                self.MAX_SCORE
            )
            
        except Exception as e:
            logger.error(f"Error calculating spec score: {e}")
        
        return scores
    
    def _calculate_age_score(self, building_age: int) -> float:
        """
        築年数スコア算出（8点満点）
        """
        if building_age is None:
            return 4.0
        
        if building_age <= 5:
            return 8.0
        elif building_age <= 15:
            return 7.0  # 10->15
        elif building_age <= 25:
            return 5.0  # 15->25
        elif building_age <= 35:
            return 3.0  # 20->35
        else:
            return max(1.0, 3.0 - (building_age - 35) * 0.1)
    
    def _calculate_area_score(self, area: float, layout: str) -> float:
        """
        専有面積スコア算出（5点満点）
        """
        if area is None:
            return 2.5
        
        if 50 <= area <= 100:  # 上限80->100
            return 5.0
        elif 40 <= area < 50 or 100 < area <= 120:
            return 4.0  # 3.5->4.0
        elif area > 120:
            return 3.0
        else:
            return 2.0
    
    def _calculate_floor_score(self, floor: int, direction: str) -> float:
        """
        階数・向きスコア算出（5点満点）
        """
        score = 0.0
        
        # 階数スコア（3点）
        if floor is not None:
            if floor >= 10:
                score += 3.0
            elif floor >= 3:
                score += 2.5
            elif floor >= 2:
                score += 2.0
            else:
                score += 1.0
        else:
            score += 1.5
        
        # 向きスコア（2点）
        if direction:
            d = direction.lower()
            if '南' in d:
                score += 2.0
            elif '東' in d or '西' in d:
                score += 2.0  # 東西も南と同じく高評価
            elif '北' in d:
                score += 1.0  # 北も少し底上げ
        else:
            score += 1.0
        
        return min(5.0, score)
    
    def _calculate_equipment_score(self, features: str) -> float:
        """
        設備スコア算出（7点満点）
        """
        score = 2.0  # 基礎点
        
        equipment = {}
        if features:
            try:
                equipment = json.loads(features) if isinstance(features, str) else features
            except:
                equipment = {}
        
        # 加点幅を増やす
        if equipment.get('auto_lock'): score += 1.5
        if equipment.get('delivery_box'): score += 1.5
        if equipment.get('pet_ok'): score += 2.0
        if equipment.get('floor_heating'): score += 2.0
        if equipment.get('disposer'): score += 1.0
        if equipment.get('renovation'): score += 1.0
        
        return min(7.0, score)
