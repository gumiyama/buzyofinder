"""
維持コストスコア算出モジュール
"""

import logging
from typing import Dict
import statistics

logger = logging.getLogger(__name__)


class CostScorer:
    """維持コストスコアを算出（15点満点）"""
    
    MAX_SCORE = 15.0
    
    def calculate(self, property_data: Dict, comparable_properties: list = None) -> Dict[str, float]:
        """
        維持コストスコアを算出
        
        Args:
            property_data: 物件データ
            comparable_properties: 比較対象物件のリスト
            
        Returns:
            スコア詳細
        """
        scores = {
            'management_score': 0.0,  # 管理費・修繕積立金スコア（10点）
            'fixed_tax_score': 0.0,   # 固定資産税想定スコア（2点）- 簡易実装
            'total_cost_score': 0.0,  # トータルコスト効率（3点）
            'score': 0.0              # 合計
        }
        
        try:
            # 1. 管理費・修繕積立金スコア（10点）
            scores['management_score'] = self._calculate_management_score(
                property_data,
                comparable_properties
            )
            
            # 2. 固定資産税スコア（2点）- 簡易実装
            scores['fixed_tax_score'] = self._calculate_tax_score(property_data)
            
            # 3. トータルコスト効率（3点）
            scores['total_cost_score'] = self._calculate_total_cost_score(property_data)
            
            # 合計
            scores['score'] = min(
                scores['management_score'] + scores['fixed_tax_score'] + scores['total_cost_score'],
                self.MAX_SCORE
            )
            
        except Exception as e:
            logger.error(f"Error calculating cost score: {e}")
        
        return scores
    
    def _calculate_management_score(self, property_data: Dict, comparable_properties: list = None) -> float:
        """
        管理費・修繕積立金スコア算出（10点満点）
        
        ㎡あたりのコストで評価
        """
        mgmt_fee = property_data.get('management_fee', 0) or 0
        repair_reserve = property_data.get('repair_reserve', 0) or 0
        area = property_data.get('area')
        
        if not area or area <= 0:
            return 5.0  # データなしの場合は中間点
        
        # ㎡あたり月額コスト
        monthly_cost_per_sqm = (mgmt_fee + repair_reserve) / area
        
        # 比較対象がある場合
        if comparable_properties and len(comparable_properties) >= 3:
            costs = []
            for prop in comparable_properties:
                p_mgmt = prop.get('management_fee', 0) or 0
                p_repair = prop.get('repair_reserve', 0) or 0
                p_area = prop.get('area')
                if p_area and p_area > 0:
                    costs.append((p_mgmt + p_repair) / p_area)
            
            if len(costs) >= 3:
                avg_cost = statistics.mean(costs)
                
                # 平均より安いほど高得点（基準を緩和）
                if monthly_cost_per_sqm <= avg_cost * 0.9:
                    return 10.0  # 平均の90%以下
                elif monthly_cost_per_sqm <= avg_cost * 1.05:
                    return 8.0   # 平均ちょい上までOK
                elif monthly_cost_per_sqm <= avg_cost * 1.2:
                    return 6.0   # 平均の1.2倍まで標準
                elif monthly_cost_per_sqm <= avg_cost * 1.4:
                    return 4.0   # 平均の1.4倍まで許容
                else:
                    return 2.0   # それ以上は高い
        
        # 比較対象がない場合は絶対値で評価（基準を緩和）
        # 市場実勢：都心部は400-500円/㎡も普通
        if monthly_cost_per_sqm <= 350:  # 300->350に緩和
            return 10.0
        elif monthly_cost_per_sqm <= 450: # 350->450に緩和
            return 8.0
        elif monthly_cost_per_sqm <= 550: # 400->550に緩和
            return 6.0
        elif monthly_cost_per_sqm <= 650: # 500->650に緩和
            return 4.0
        else:
            return 2.0
    
    def _calculate_tax_score(self, property_data: Dict) -> float:
        """
        固定資産税スコア算出（2点満点）
        
        築年数と価格から推定（簡易実装）
        """
        building_age = property_data.get('building_age')
        price = property_data.get('price')
        
        if building_age is None or price is None:
            return 1.0
        
        # 新しいほど固定資産税が高い傾向
        if building_age >= 20:
            return 2.0  # 築古なら税金安い
        elif building_age >= 15:
            return 1.5
        elif building_age >= 10:
            return 1.0
        else:
            return 0.5
    
    def _calculate_total_cost_score(self, property_data: Dict) -> float:
        """
        トータルコスト効率スコア（3点満点）
        
        購入価格と月額コストのバランス
        """
        price = property_data.get('price')  # 万円
        mgmt_fee = property_data.get('management_fee', 0) or 0
        repair_reserve = property_data.get('repair_reserve', 0) or 0
        
        if not price or price <= 0:
            return 1.5
        
        monthly_cost = mgmt_fee + repair_reserve
        
        # 年間コストの購入価格に対する割合
        annual_cost_ratio = (monthly_cost * 12) / (price * 10000) * 100
        
        # 年間コスト率が低いほど高得点
        # 一般的な目安：0.5-1.0%が標準
        if annual_cost_ratio <= 0.5:
            return 3.0
        elif annual_cost_ratio <= 0.7:
            return 2.5
        elif annual_cost_ratio <= 1.0:
            return 2.0
        elif annual_cost_ratio <= 1.5:
            return 1.0
        else:
            return 0.5
