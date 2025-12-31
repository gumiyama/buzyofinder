"""
総合スコアリングエンジン
"""

import logging
from typing import Dict, List
from .price_scorer import PriceScorer
from .location_scorer import LocationScorer
from .spec_scorer import SpecScorer
from .cost_scorer import CostScorer
from .future_scorer import FutureScorer

logger = logging.getLogger(__name__)


class PropertyScorer:
    """物件の総合お得度スコアを算出"""
    
    # 標準の重み係数（資産性と居住性のバランス重視）
    WEIGHTS = {
        'price': 1.0,      # 価格適正性: 30点
        'location': 1.1,   # 立地: 27.5点（利便性重視）
        'spec': 1.0,       # 物件スペック: 25.0点
        'cost': 1.0,       # 維持コスト: 15.0点
        'future': 1.1      # 将来性: 5.5点 (資産価値重視)
    }
    
    def __init__(self):
        self.price_scorer = PriceScorer()
        self.location_scorer = LocationScorer()
        self.spec_scorer = SpecScorer()
        self.cost_scorer = CostScorer()
        self.future_scorer = FutureScorer()
    
    def calculate_score(
        self,
        property_data: Dict,
        comparable_properties: List[Dict] = None
    ) -> Dict:
        """
        物件の総合お得度スコアを算出
        
        Args:
            property_data: 物件データ
            comparable_properties: 比較対象物件のリスト
            
        Returns:
            スコア詳細
        """
        # 各カテゴリのスコア算出
        price_detail = self.price_scorer.calculate(property_data, comparable_properties)
        location_detail = self.location_scorer.calculate(property_data)
        spec_detail = self.spec_scorer.calculate(property_data)
        cost_detail = self.cost_scorer.calculate(property_data, comparable_properties)
        future_detail = self.future_scorer.calculate(property_data)

        # 各カテゴリの分母（満点）を計算
        w = self.WEIGHTS
        
        # 型チェック
        if not isinstance(w, dict):
            logger.error(f"FATAL: WEIGHTS is not a dict! type: {type(w)}")
            raise TypeError(f"WEIGHTS is {type(w)}, expected dict")

        # 重み付けを適用（一行ずつ実行してエラー箇所を特定）
        weighted_scores = {}
        sub_details = [
            ('price_score', price_detail, 'price'),
            ('location_score', location_detail, 'location'),
            ('spec_score', spec_detail, 'spec'),
            ('cost_score', cost_detail, 'cost'),
            ('future_score', future_detail, 'future')
        ]
        
        for key, detail, weight_key in sub_details:
            try:
                if not isinstance(detail, dict):
                    logger.error(f"Detail for {weight_key} is not a dict! type: {type(detail)}")
                
                score_val = detail.get('score', 0.0)
                weight_val = w.get(weight_key, 1.0)
                
                # ここで TypeError が発生する可能性が高いのでチェック
                if not isinstance(score_val, (int, float)):
                    logger.error(f"Score for {weight_key} is not numeric! value: {score_val} (type: {type(score_val)})")
                if not isinstance(weight_val, (int, float)):
                    logger.error(f"Weight for {weight_key} is not numeric! value: {weight_val} (type: {type(weight_val)})")
                
                weighted_scores[key] = score_val * weight_val
                
            except Exception as e:
                logger.error(f"FAILED calculation for {key}: {e}")
                logger.error(f"Detail: {detail}")
                logger.error(f"Weight key: {weight_key}, Weight: {w.get(weight_key)}")
                raise e
        
        # 総合スコアを100点満点に正規化
        try:
            total_max = 0.0
            max_defs = [
                (PriceScorer.MAX_SCORE, 'price'),
                (LocationScorer.MAX_SCORE, 'location'),
                (SpecScorer.MAX_SCORE, 'spec'),
                (CostScorer.MAX_SCORE, 'cost'),
                (FutureScorer.MAX_SCORE, 'future')
            ]
            for max_val, weight_key in max_defs:
                total_max += max_val * w.get(weight_key, 1.0)
                
        except Exception as e:
            logger.error(f"Error calculating total_max: {e}")
            logger.error(f"WEIGHTS: {w}")
            raise e
        
        total_score = sum(weighted_scores.values())
        normalized_score = (total_score / total_max) * 100 if total_max > 0 else 0
        
        # スコアランク判定
        rank = self._get_rank(normalized_score)
        
        result = {
            'total_score': round(normalized_score, 1),
            'rank': rank,
            
            # カテゴリ別スコア
            'category_scores': {
                'price': round(weighted_scores['price_score'], 1),
                'location': round(weighted_scores['location_score'], 1),
                'spec': round(weighted_scores['spec_score'], 1),
                'cost': round(weighted_scores['cost_score'], 1),
                'future': round(weighted_scores['future_score'], 1)
            },
            
            # 詳細スコア
            'detail': {
                'price': price_detail,
                'location': location_detail,
                'spec': spec_detail,
                'cost': cost_detail,
                'future': future_detail
            }
        }
        
        return result
    
    def _get_rank(self, score: float) -> str:
        """
        スコアからランクを判定
        
        Args:
            score: 総合スコア（0-100）
            
        Returns:
            ランク文字列
        """
        if score >= 90:
            return '🌟🌟🌟 超お得！即決レベル'
        elif score >= 80:
            return '🌟🌟 かなりお得'
        elif score >= 70:
            return '🌟 お得'
        elif score >= 60:
            return '⭕ 標準的'
        else:
            return '△ 割高の可能性'


def main():
    """テスト用のメイン関数"""
    # サンプルデータ
    sample_property = {
        'title': 'サンプルマンション',
        'price': 5980,  # 5980万円
        'area': 70.5,   # 70.5㎡
        'price_per_sqm': 848000,  # ㎡単価
        'building_age': 5,
        'floor': 8,
        'direction': '南',
        'layout': '3LDK',
        'address': '東京都渋谷区恵比寿1-1-1',
        'prefecture': '東京都',
        'city': '渋谷区',
        'station_name': '恵比寿',
        'station_distance': 5,
        'management_fee': 15000,
        'repair_reserve': 8000,
        'features': '{"auto_lock": true, "delivery_box": true, "pet_ok": true}'
    }
    
    # 比較対象物件（サンプル）
    comparable = [
        {'price': 6200, 'area': 72, 'price_per_sqm': 860000, 'building_age': 3,
         'management_fee': 16000, 'repair_reserve': 9000},
        {'price': 5800, 'area': 68, 'price_per_sqm': 850000, 'building_age': 7,
         'management_fee': 14000, 'repair_reserve': 8500},
        {'price': 6500, 'area': 75, 'price_per_sqm': 870000, 'building_age': 2,
         'management_fee': 17000, 'repair_reserve': 10000},
    ]
    
    scorer = PropertyScorer()
    
    print("\n=== 物件スコア分析 ===")
    score_result = scorer.calculate_score(sample_property, comparable)
    print(f"総合スコア: {score_result['total_score']}点")
    print(f"ランク: {score_result['rank']}")
    print("\nカテゴリ別スコア:")
    for category, score in score_result['category_scores'].items():
        print(f"  {category}: {score}点")


if __name__ == '__main__':
    main()
