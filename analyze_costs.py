
import logging
from src.models.database import init_db, get_session, Property
# Import SafePropertyScorer by instantiating it from the logic we know is in app.py
# ensuring we use the exact logic currently active.
# Since we can't easily import "SafePropertyScorer" from app.py without executing the whole script,
# I will copy the logic here for analysis.

import statistics

class CostScorer:
    """維持コストスコアを算出（15点満点）"""
    MAX_SCORE = 15.0
    
    def calculate(self, property_data, comparable_properties=None):
        scores = {
            'management_score': 0.0,
            'fixed_tax_score': 0.0,
            'total_cost_score': 0.0,
            'score': 0.0
        }
        
        # 1. 管理費・修繕積立金スコア（10点）
        scores['management_score'] = self._calculate_management_score(
            property_data,
            comparable_properties
        )
        
        # 2. 固定資産税スコア（2点）
        scores['fixed_tax_score'] = self._calculate_tax_score(property_data)
        
        # 3. トータルコスト効率（3点）
        scores['total_cost_score'] = self._calculate_total_cost_score(property_data)
        
        scores['score'] = min(
            scores['management_score'] + scores['fixed_tax_score'] + scores['total_cost_score'],
            self.MAX_SCORE
        )
        return scores
    
    def _calculate_management_score(self, property_data, comparable_properties=None):
        mgmt_fee = property_data.get('management_fee', 0) or 0
        repair_reserve = property_data.get('repair_reserve', 0) or 0
        area = property_data.get('area')
        
        if not area or area <= 0:
            return 5.0
        
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
                
                if monthly_cost_per_sqm <= avg_cost * 0.8:
                    return 10.0
                elif monthly_cost_per_sqm <= avg_cost * 0.9:
                    return 8.0
                elif monthly_cost_per_sqm <= avg_cost * 1.1:
                    return 6.0
                elif monthly_cost_per_sqm <= avg_cost * 1.2:
                    return 4.0
                else:
                    return 2.0
        
        # 絶対値評価
        if monthly_cost_per_sqm <= 300: return 10.0
        elif monthly_cost_per_sqm <= 350: return 8.0
        elif monthly_cost_per_sqm <= 400: return 6.0
        elif monthly_cost_per_sqm <= 500: return 4.0
        else: return 2.0

    def _calculate_tax_score(self, property_data):
        building_age = property_data.get('building_age')
        if building_age is None: return 1.0
        
        if building_age >= 20: return 2.0
        elif building_age >= 15: return 1.5
        elif building_age >= 10: return 1.0
        else: return 0.5

    def _calculate_total_cost_score(self, property_data):
        price = property_data.get('price')
        mgmt_fee = property_data.get('management_fee', 0) or 0
        repair_reserve = property_data.get('repair_reserve', 0) or 0
        
        if not price or price <= 0: return 1.5
        
        monthly_cost = mgmt_fee + repair_reserve
        annual_cost_ratio = (monthly_cost * 12) / (price * 10000) * 100
        
        if annual_cost_ratio <= 0.5: return 3.0
        elif annual_cost_ratio <= 0.7: return 2.5
        elif annual_cost_ratio <= 1.0: return 2.0
        elif annual_cost_ratio <= 1.5: return 1.0
        else: return 0.5

# Main analysis script
def analyze_costs():
    engine = init_db()
    session = get_session(engine)
    properties = session.query(Property).filter_by(is_active=True).limit(20).all()
    session.close()
    
    scorer = CostScorer()
    
    print(f"{'ID':<10} {'Area':<6} {'Mgmt+Rep':<10} {'/Sqm':<6} {'Score':<5} {'MgmtScore':<9} {'Method'}")
    print("-" * 70)
    
    all_props_dicts = []
    for p in properties:
        d = {
            'source_id': p.source_id,
            'management_fee': p.management_fee,
            'repair_reserve': p.repair_reserve,
            'area': p.area,
            'building_age': p.building_age,
            'price': p.price,
            'station_name': p.station_name # Used for finding logic but not in calculation directly
        }
        all_props_dicts.append(d)

    for p in all_props_dicts:
        # Create comparable
        comparable = [x for x in all_props_dicts if x != p] 
        # In real app, filtered by station. Let's filter by station here too if possible,
        # but for this small sample, maybe just use all as comparable to see the "Relative" effect?
        # Or better, let's strictly follow app logic: comparable is "Same Station"
        
        station_comparable = [x for x in all_props_dicts if x['station_name'] == p['station_name'] and x['source_id'] != p['source_id']]
        
        scores = scorer.calculate(p, station_comparable)
        
        total_monthly = (p['management_fee'] or 0) + (p['repair_reserve'] or 0)
        per_sqm = int(total_monthly / p['area']) if p['area'] else 0
        
        method = "Relative" if len(station_comparable) >= 3 else "Absolute"
        
        print(f"{p['source_id']:<10} {p['area']:<6.1f} {total_monthly:<10} {per_sqm:<6} {scores['score']:<5.1f} {scores['management_score']:<9.1f} {method}")

if __name__ == "__main__":
    analyze_costs()
