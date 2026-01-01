#!/usr/bin/env python
"""
全物件のスコアを再計算してDBに保存するスクリプト
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.database import get_session, get_engine, Property, PropertyScore
from sqlalchemy import delete
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def recalculate_all_scores():
    """全物件のスコアを再計算"""
    engine = get_engine()
    session = get_session(engine)
    
    try:
        # 既存のスコアを全削除
        logger.info("既存スコアを削除中...")
        session.execute(delete(PropertyScore))
        session.commit()
        logger.info("削除完了。")
        
        # 全物件取得
        properties = session.query(Property).filter(Property.is_active == True).all()
        total = len(properties)
        logger.info(f"対象物件数: {total}件")
        
        # SafePropertyScorerをインポート（app.pyから）
        # app.pyのSafePropertyScorerクラスをそのまま使いたいが、
        # app.pyはStreamlitコードなので直接importできない。
        # 代わりに、既存のscorerを使って計算する。
        
        from src.scoring.price_scorer import PriceScorer
        from src.scoring.location_scorer import LocationScorer
        from src.scoring.spec_scorer import SpecScorer
        from src.scoring.cost_scorer import CostScorer
        from src.scoring.future_scorer import FutureScorer
        
        price_scorer = PriceScorer()
        location_scorer = LocationScorer()
        spec_scorer = SpecScorer()
        cost_scorer = CostScorer()
        future_scorer = FutureScorer()
        
        # WEIGHTSを全て1.0に統一（100点超えを防ぐ）
        WEIGHTS = {
            'price': 1.0,
            'location': 1.0,  # 1.1 → 1.0
            'spec': 1.0,
            'cost': 1.0,
            'future': 1.0     # 1.1 → 1.0
        }
        
        updated_count = 0
        
        for idx, prop in enumerate(properties, 1):
            if idx % 100 == 0:
                logger.info(f"処理中... {idx}/{total}")
            
            try:
                # 物件データを辞書に変換
                prop_dict = {
                    'id': prop.id,
                    'source_id': prop.source_id,
                    'title': prop.title,
                    'price': prop.price,
                    'area': prop.area,
                    'price_per_sqm': prop.price_per_sqm,
                    'building_age': prop.building_age,
                    'floor': prop.floor,
                    'direction': prop.direction,
                    'layout': prop.layout,
                    'station_name': prop.station_name,
                    'station_distance': prop.station_distance,
                    'management_fee': prop.management_fee,
                    'repair_reserve': prop.repair_reserve,
                    'features': prop.features
                }
                
                # 比較対象物件（同じ駅の物件）
                comparable = []
                if prop.station_name:
                    comparable_props = session.query(Property).filter(
                        Property.station_name == prop.station_name,
                        Property.id != prop.id,
                        Property.is_active == True
                    ).all()
                    
                    comparable = [{
                        'price': p.price,
                        'area': p.area,
                        'price_per_sqm': p.price_per_sqm,
                        'building_age': p.building_age,
                        'management_fee': p.management_fee,
                        'repair_reserve': p.repair_reserve
                    } for p in comparable_props]
                
                # 各カテゴリスコア計算
                price_detail = price_scorer.calculate(prop_dict, comparable)
                location_detail = location_scorer.calculate(prop_dict)
                spec_detail = spec_scorer.calculate(prop_dict)
                cost_detail = cost_scorer.calculate(prop_dict, comparable)
                future_detail = future_scorer.calculate(prop_dict)
                
                # 重み付けスコア
                w = WEIGHTS
                weighted_scores = {
                    'price_score': price_detail['score'] * w['price'],
                    'location_score': location_detail['score'] * w['location'],
                    'spec_score': spec_detail['score'] * w['spec'],
                    'cost_score': cost_detail['score'] * w['cost'],
                    'future_score': future_detail['score'] * w['future']
                }
                
                # 総合スコアを100点満点に正規化
                total_max = sum([
                    PriceScorer.MAX_SCORE * w['price'],
                    LocationScorer.MAX_SCORE * w['location'],
                    SpecScorer.MAX_SCORE * w['spec'],
                    CostScorer.MAX_SCORE * w['cost'],
                    FutureScorer.MAX_SCORE * w['future']
                ])
                
                total_score = sum(weighted_scores.values())
                raw_normalized_score = (total_score / total_max) * 100 if total_max > 0 else 0
                normalized_score = min(100.0, raw_normalized_score)  # 上限を100点にキャップ
                
                # DBに保存
                score_record = PropertyScore(
                    property_id=prop.id,
                    total_score=round(normalized_score, 2),
                    price_score=round(weighted_scores['price_score'], 2),
                    location_score=round(weighted_scores['location_score'], 2),
                    spec_score=round(weighted_scores['spec_score'], 2),
                    cost_score=round(weighted_scores['cost_score'], 2),
                    future_score=round(weighted_scores['future_score'], 2)
                )
                
                session.add(score_record)
                updated_count += 1
                
            except Exception as e:
                logger.error(f"物件ID {prop.id} のスコア計算エラー: {e}")
                continue
        
        session.commit()
        logger.info(f"完了！ {updated_count}件のスコアを再計算しました。")
        
    except Exception as e:
        logger.error(f"エラー: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == '__main__':
    recalculate_all_scores()
