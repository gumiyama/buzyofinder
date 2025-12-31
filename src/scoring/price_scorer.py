"""
価格適正性スコア算出モジュール
"""

import logging
from typing import Dict, Optional
import statistics

logger = logging.getLogger(__name__)


class PriceScorer:
    """価格適正性スコアを算出（30点満点）"""
    
    MAX_SCORE = 30.0
    
    def __init__(self, area_stats: Optional[Dict] = None):
        """
        Args:
            area_stats: エリア統計データ {area_code: {'avg_price_per_sqm': float, 'std': float}}
        """
        self.area_stats = area_stats or {}
    
    def calculate(self, property_data: Dict, comparable_properties: list = None) -> Dict[str, float]:
        """
        価格適正性スコアを算出
        
        Args:
            property_data: 物件データ
            comparable_properties: 比較対象物件のリスト（同エリア・同築年数帯）
            
        Returns:
            スコア詳細 {'score': float, 'sqm_score': float, 'total_score': float, 'discount_score': float}
        """
        scores = {
            'sqm_score': 0.0,      # ㎡単価偏差値スコア（15点）
            'total_score': 0.0,    # 総額偏差値スコア（10点）
            'discount_score': 0.0, # 値下げスコア（5点）
            'score': 0.0           # 合計
        }
        
        try:
            # 1. ㎡単価偏差値スコア（15点）
            scores['sqm_score'] = self._calculate_sqm_score(property_data, comparable_properties)
            
            # 2. 総額偏差値スコア（10点）
            scores['total_score'] = self._calculate_total_price_score(property_data, comparable_properties)
            
            # 3. 値下げスコア（5点）- 現時点では実装スキップ
            scores['discount_score'] = 0.0
            
            # 合計
            scores['score'] = min(
                scores['sqm_score'] + scores['total_score'] + scores['discount_score'],
                self.MAX_SCORE
            )
            
        except Exception as e:
            logger.error(f"Error calculating price score: {e}")
        
        return scores
    
    def _calculate_sqm_score(self, property_data: Dict, comparable_properties: list = None) -> float:
        """
        ㎡単価偏差値スコア算出（15点満点）
        
        同エリア・同築年数帯の平均と比較して、安いほど高得点
        """
        if not property_data.get('price_per_sqm'):
            return 0.0
        
        property_sqm = property_data['price_per_sqm']
        
        # 比較対象物件がある場合
        if comparable_properties and len(comparable_properties) >= 3:
            sqm_prices = [p.get('price_per_sqm') for p in comparable_properties if p.get('price_per_sqm')]
            
            if len(sqm_prices) >= 3:
                avg_sqm = statistics.mean(sqm_prices)
                std_sqm = statistics.stdev(sqm_prices) if len(sqm_prices) > 1 else avg_sqm * 0.15
                
                # 偏差値的なスコア算出
                # 平均より安いほど高得点、高いほど低得点
                deviation = (avg_sqm - property_sqm) / std_sqm if std_sqm > 0 else 0
                
                # deviation:
                # +2.0 = かなり安い -> 15点
                # +1.0 = やや安い -> 11点
                # 0.0 = 平均 -> 7.5点
                # -1.0 = やや高い -> 4点
                # -2.0 = かなり高い -> 0点
                
                score = 7.5 + (deviation * 3.75)  # 7.5点を中心に±7.5点
                return max(0.0, min(15.0, score))
        
        # 比較対象がない場合は中間点
        return 7.5
    
    def _calculate_total_price_score(self, property_data: Dict, comparable_properties: list = None) -> float:
        """
        総額偏差値スコア算出（10点満点）
        
        同条件物件の総額と比較
        """
        if not property_data.get('price'):
            return 0.0
        
        property_price = property_data['price']
        
        # 比較対象物件がある場合
        if comparable_properties and len(comparable_properties) >= 3:
            prices = [p.get('price') for p in comparable_properties if p.get('price')]
            
            if len(prices) >= 3:
                avg_price = statistics.mean(prices)
                std_price = statistics.stdev(prices) if len(prices) > 1 else avg_price * 0.15
                
                deviation = (avg_price - property_price) / std_price if std_price > 0 else 0
                
                # deviation範囲を10点満点でスコアリング
                score = 5.0 + (deviation * 2.5)
                return max(0.0, min(10.0, score))
        
        # 比較対象がない場合は中間点
        return 5.0
