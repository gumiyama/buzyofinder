"""
分譲マンション お得サイエンティスト - メインアプリ
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from src.models.database import init_db, get_session, get_engine, Property, PropertyScore
from src.models.database import init_db, get_session, get_engine, Property, PropertyScore
# from src.scoring.property_scorer import PropertyScorer
from src.scoring.price_scorer import PriceScorer
from src.scoring.location_scorer import LocationScorer
from src.scoring.spec_scorer import SpecScorer
from src.scoring.cost_scorer import CostScorer
from src.scoring.future_scorer import FutureScorer
import logging

logger = logging.getLogger(__name__)

class SafePropertyScorer:
    """物件の総合お得度スコアを算出（Safe Version）"""
    
    # 標準の重み係数（全て1.0に統一して100点超えを防止）
    WEIGHTS = {
        'price': 1.0,      # 価格適正性: 30点
        'location': 1.0,   # 立地: 25.0点
        'spec': 1.0,       # 物件スペック: 25.0点
        'cost': 1.0,       # 維持コスト: 15.0点
        'future': 1.0      # 将来性: 5.0点
    }
    
    def __init__(self):
        self.price_scorer = PriceScorer()
        self.location_scorer = LocationScorer()
        self.spec_scorer = SpecScorer()
        self.cost_scorer = CostScorer()
        self.future_scorer = FutureScorer()
    
    # スペック評価ロジックを緩和版に差し替え
    def _calculate_age_score(self, building_age):
        if building_age is None: return 4.0
        # 基準を緩和：築10年まで満点近く、築30年でもそこそこ
        if building_age <= 5: return 8.0
        elif building_age <= 15: return 7.0  # 10->15
        elif building_age <= 25: return 5.0  # 15->25
        elif building_age <= 35: return 3.0  # 20->35
        else: return max(1.0, 3.0 - (building_age - 35) * 0.1)

    def _calculate_area_score(self, area, layout):
        if area is None: return 2.5
        # 基準を緩和：広さの評価を甘く
        if 50 <= area <= 100: return 5.0     # 上限80->100
        elif 40 <= area < 50 or 100 < area <= 120: return 4.0 # 3.5->4.0
        elif area > 120: return 3.0 
        else: return 2.0

    def _calculate_floor_score(self, floor, direction):
        score = 0.0
        if floor is not None:
            if floor >= 10: score += 3.0
            elif floor >= 3: score += 2.5 # 5->3階以上で良しとする
            elif floor >= 2: score += 2.0
            else: score += 1.0 # 1階
        else: score += 1.5
        
        if direction:
            d = direction
            if '南' in d: score += 2.0
            elif '東' in d or '西' in d: score += 2.0 # 東西も南と同じく高評価に変更
            elif '北' in d: score += 1.0 # 北も0.5->1.0
        else: score += 1.0
        return min(5.0, score)

    def _calculate_equipment_score(self, features):
        score = 2.0 # 基礎点を加算（何もないことはないので）
        equipment = {}
        if features:
            try:
                import json
                equipment = json.loads(features) if isinstance(features, str) else features
            except: pass
        
        # 加点幅を増やす
        if equipment.get('auto_lock'): score += 1.5
        if equipment.get('delivery_box'): score += 1.5
        if equipment.get('pet_ok'): score += 2.0
        if equipment.get('floor_heating'): score += 2.0 # ない場合が多いのであればデカイ
        
        return min(7.0, score)

    def calculate_score(self, property_data, comparable_properties=None):
        # ... (中略) ...
        # 注意: SafePropertyScorerはクラス内でインスタンス化された各カテゴリのscorerを使っているので
        # ここで定義したメソッドをインスタンスメソッドとして使うには、
        # __init__ で self.spec_scorer を自作のものに差し替えるか、
        # あるいは spec_scorer.py 自体を書き換える必要がある。
        # 今回は SafePropertyScorer 内で spec_scorer の計算ロジックをオーバーライドする形にするため
        # calculate メソッド内で直接上記メソッドを呼び出すように変更する。
        
        price_detail = self.price_scorer.calculate(property_data, comparable_properties)
        location_detail = self.location_scorer.calculate(property_data)
        # spec_detail = self.spec_scorer.calculate(property_data) # これを使わず
        
        # 自クラスのメソッドで計算
        spec_detail = {
            'age_score': self._calculate_age_score(property_data.get('building_age')),
            'area_score': self._calculate_area_score(property_data.get('area'), property_data.get('layout')),
            'floor_score': self._calculate_floor_score(property_data.get('floor'), property_data.get('direction')),
            'equipment_score': self._calculate_equipment_score(property_data.get('features')),
            'score': 0.0
        }
        spec_detail['score'] = min(
            spec_detail['age_score'] + spec_detail['area_score'] + 
            spec_detail['floor_score'] + spec_detail['equipment_score'],
            SpecScorer.MAX_SCORE
        )

        cost_detail = self.cost_scorer.calculate(property_data, comparable_properties)
        future_detail = self.future_scorer.calculate(property_data)

        w = self.WEIGHTS
        
        weighted_scores = {}
        weighted_scores['price_score'] = price_detail['score'] * w['price']
        weighted_scores['location_score'] = location_detail['score'] * w['location']
        weighted_scores['spec_score'] = spec_detail['score'] * w['spec']
        weighted_scores['cost_score'] = cost_detail['score'] * w['cost']
        weighted_scores['future_score'] = future_detail['score'] * w['future']
        
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
        
        # スコアランク判定
        rank = self._get_rank(normalized_score)
        
        return {
            'total_score': round(normalized_score, 1),
            'rank': rank,
            'category_scores': {
                'price': round(weighted_scores['price_score'], 1),
                'location': round(weighted_scores['location_score'], 1),
                'spec': round(weighted_scores['spec_score'], 1),
                'cost': round(weighted_scores['cost_score'], 1),
                'future': round(weighted_scores['future_score'], 1)
            },
            'detail': {
                'price': price_detail,
                'location': location_detail,
                'spec': spec_detail,
                'cost': cost_detail,
                'future': future_detail
            }
        }
    
    def _get_rank(self, score: float) -> str:
        if score >= 90: return '🌟🌟🌟 超お得！即決レベル'
        elif score >= 80: return '🌟🌟 かなりお得'
        elif score >= 70: return '🌟 お得'
        elif score >= 60: return '⭕ 標準的'
        else: return '△ 割高の可能性'

# ページ設定
st.set_page_config(
    page_title="AI分譲マンションファインダー",
    page_icon="assets/app_logo.png",
    layout="wide"
)

# サイドバー（ロゴ表示）
st.sidebar.image("assets/app_logo.png", use_container_width=True)

# タイトル
st.title("AI分譲マンションファインダー")
st.markdown("一都三県の分譲マンション物件をAIが科学的に分析し、真のお得物件を発掘します")
st.caption("Last Updated: 2026-01-01 21:57 | Total: 5,124 properties")  # 更新確認用

# データベース初期化
@st.cache_resource
def init_database():
    return init_db()

engine = init_database()

# セッション取得
def get_db_session():
    return get_session(engine)

# 利用可能な駅名を取得
@st.cache_data(ttl=3600)
def get_unique_stations():
    session = get_db_session()
    try:
        results = session.query(Property.station_name).filter(
            Property.station_name != None,
            Property.station_name != ''
        ).distinct().order_by(Property.station_name).all()
        stations = [r[0] for r in results]
        
        # 「バス」が含まれるものを後ろに回す
        train_stations = [s for s in stations if "バス" not in s]
        bus_stations = [s for s in stations if "バス" in s]
        
        return train_stations + bus_stations
    except Exception as e:
        logger.error(f"Error fetching stations: {e}")
        return []
        session.close()

# 利用可能な都道府県と市区町村を取得
@st.cache_data(ttl=3600)
def get_locations():
    session = get_db_session()
    try:
        # 都道府県
        prefs = session.query(Property.prefecture).filter(
            Property.prefecture != None
        ).distinct().all()
        prefs = [r[0] for r in prefs]
        
        # 市区町村（都道府県ごと）
        cities = session.query(Property.prefecture, Property.city).filter(
            Property.city != None
        ).distinct().all()
        
        city_map = {}
        for p, c in cities:
            if not p: continue
            if p not in city_map: city_map[p] = []
            city_map[p].append(c)
            
        return prefs, city_map
    except Exception as e:
        logger.error(f"Error fetching locations: {e}")
        return [], {}
    finally:
        session.close()

# サイドバー
st.sidebar.header("⚙️ 設定")

# 地域フィルタ
prefs, city_map = get_locations()

# 都道府県選択
selected_prefs = st.sidebar.multiselect(
    "都道府県を選択",
    options=prefs,
    default=[]
)

# 市区町村選択
available_cities = []
if selected_prefs:
    for p in selected_prefs:
        available_cities.extend(city_map.get(p, []))
else:
    # 都道府県未選択時は全表示（ただし多すぎる場合は制限するなど検討）
    for cities in city_map.values():
        available_cities.extend(cities)
        
available_cities = sorted(list(set(available_cities)))

city_filter = st.sidebar.multiselect(
    "市区町村を選択",
    options=available_cities,
    default=[]
)

# 価格フィルタ
price_min, price_max = st.sidebar.slider(
    "価格帯 (万円)",
    min_value=0,
    max_value=30000,
    value=(0, 20000),
    step=500
)

# 駅フィルタ
station_options = get_unique_stations()

# 駅名検索ボックス
station_search = st.sidebar.text_input(
    "🔍 駅名で検索",
    placeholder="例: 大井町、渋谷、新宿...",
    help="駅名の一部を入力すると、候補が絞り込まれます"
)

# 検索キーワードでフィルタリング
if station_search:
    filtered_stations = [s for s in station_options if station_search.lower() in s.lower()]
else:
    filtered_stations = station_options

station_filter = st.sidebar.multiselect(
    "最寄り駅を選択",
    options=filtered_stations,
    default=[]
)

# 築年数フィルタ
age_min, age_max = st.sidebar.slider(
    "築年数 (年)",
    min_value=0,
    max_value=60,
    value=(0, 60),
    step=1
)

# 間取りフィルタ
layout_options = ["1R", "1K", "1DK", "1LDK", "2K", "2DK", "2LDK", "3K", "3DK", "3LDK", "4K", "4DK", "4LDK"]
layout_filter = st.sidebar.multiselect(
    "間取りを選択",
    options=layout_options,
    default=[]
)


# データベースから物件を取得
# @st.cache_data(ttl=60)  # 反映を早めるため1分に短縮
def get_properties_from_db(layout_filter=None, city_filter=None, price_range=None, station_filter=None, age_range=None, prefecture_filter=None):
    """データベースから物件データを取得"""
    try:
        session = get_db_session()
        query = session.query(Property).filter(Property.is_active == True)
        
        # フィルタ適用
        if layout_filter:
            query = query.filter(Property.layout.in_(layout_filter))
        
        if station_filter:
            query = query.filter(Property.station_name.in_(station_filter))
            
        if age_range:
            min_a, max_a = age_range
            query = query.filter(Property.building_age >= min_a, Property.building_age <= max_a)
            
        if prefecture_filter:
            query = query.filter(Property.prefecture.in_(prefecture_filter))
            
        if city_filter:
            # 市区町村フィルタがある場合はそちらを優先（AND条件になるのでOK）
            from sqlalchemy import or_
            conditions = [Property.city.like(f"%{city}%") for city in city_filter]
            query = query.filter(or_(*conditions))
            
        if price_range:
            min_p, max_p = price_range
            query = query.filter(Property.price >= min_p, Property.price <= max_p)
            
        properties_db = query.all()
        
        if not properties_db:
            return []

        # データベースの物件を辞書形式に変換
        raw_properties_list = []
        for prop in properties_db:
            raw_properties_list.append({
                'id': prop.id,
                'source_id': prop.source_id,
                'title': prop.title or '',
                'price': prop.price,
                'area': prop.area,
                'price_per_sqm': prop.price_per_sqm,
                'building_age': prop.building_age,
                'floor': prop.floor,
                'direction': prop.direction or '',
                'layout': prop.layout or '',
                'address': prop.address or '',
                'prefecture': prop.prefecture or '',
                'city': prop.city or '',
                'station_name': prop.station_name or '',
                'station_distance': prop.station_distance,
                'access_info': prop.access_info or '',
                'management_fee': prop.management_fee,
                'repair_reserve': prop.repair_reserve,
                'features': prop.features or '{}',
                'url': prop.url,
                'first_seen': prop.first_seen,
                'last_updated': prop.last_updated
            })
            
        # 名寄せ処理（同一物件の重複排除）
        # キー: (タイトル, 面積(整数), 階数, 間取り)
        unique_props = {}
        for p in raw_properties_list:
            # タイトルが「物件...」のものは名寄せ対象外（ID違いの可能性あるため）だが、
            # 基本的には同じ部屋ならまとめたい。
            # 面積は微妙な誤差を許容するため四捨五入して整数で扱う
            area_key = int(round(p['area'])) if p['area'] else 0
            key = (p['title'], area_key, p['floor'], p['layout'])
            
            if key not in unique_props:
                unique_props[key] = p
            else:
                # 既にある場合は、より新しい情報（source_idが大きい、または更新日時が新しい）を採用
                # ここでは簡易的にsource_id（文字列だが数値的）が大きい方を採用
                curr = unique_props[key]
                if p['source_id'] > curr['source_id']:
                     unique_props[key] = p
        
        properties_list = list(unique_props.values())
        session.close()
        return properties_list
        
    except Exception as e:
        st.error(f"データベースエラー: {e}")
        return []

# 物件の一言コメント・強み弱みを生成
def generate_property_analysis(prop, score_data):
    """物件の分析コメントを生成"""
    total_score = score_data['total_score']
    
    # 一言コメント
    if total_score >= 70:
        comment = "🌟 非常にお買い得な物件です！"
    elif total_score >= 60:
        comment = "✨ お買い得度が高い物件です"
    elif total_score >= 50:
        comment = "👍 バランスの良い物件です"
    elif total_score >= 40:
        comment = "📊 標準的な物件です"
    else:
        comment = "⚠️ 慎重に検討が必要な物件です"
    
    # 強み・弱みの判定用データ抽出
    details = score_data.get('detail', {})
    price_detail = details.get('price', {})
    location_detail = details.get('location', {})
    spec_detail = details.get('spec', {})
    future_detail = details.get('future', {})
    
    # 強み（スコアが高い項目を抽出）
    strengths = []
    
    if price_detail.get('score', 0) >= 8:
        strengths.append(f"価格が相場より割安（㎡単価: {prop['price_per_sqm']/10000:.1f}万円/㎡）")
    
    if spec_detail.get('age_score', 0) >= 6:
        strengths.append(f"築年数が浅い（築{prop['building_age']}年）")
    
    if location_detail.get('station_score', 0) >= 8:
        if prop['station_distance']:
            strengths.append(f"駅近で便利（徒歩{prop['station_distance']}分）")
        else:
            strengths.append("駅近で便利")
    
    if spec_detail.get('area_score', 0) >= 4:
        strengths.append(f"{prop['area']}㎡のゆとりある面積")
    
    if future_detail.get('brand_score', 0) >= 1.0:
        strengths.append("資産価値の高い大手ブランド物件")
    
    if not strengths:
        strengths.append("バランスの取れた物件構成")
    
    # 弱み（スコアが低い項目を抽出）
    weaknesses = []
    
    if price_detail.get('score', 0) <= 3:
        weaknesses.append(f"価格が相場より高め（㎡単価: {prop['price_per_sqm']/10000:.1f}万円/㎡）")
    if spec_detail.get('age_score', 0) <= 3:
        weaknesses.append(f"築年数が経過（築{prop['building_age']}年）")
    if location_detail.get('station_score', 0) <= 3:
        if prop['station_distance']:
            weaknesses.append(f"駅から距離あり（徒歩{prop['station_distance']}分）")
        else:
            weaknesses.append("駅距離不明（要確認）")
    if spec_detail.get('floor_score', 0) <= 1:
        weaknesses.append(f"低層階・向きに懸念（{prop['floor']}階 / {prop['direction']}向き）")
    
    # 維持費・将来性
    if future_detail.get('management_score', 0) <= 0.3:
        weaknesses.append("管理・修繕積立金のバランスに懸念")
    elif prop.get('management_fee') and prop.get('repair_reserve'):
        total_monthly = (prop['management_fee'] or 0) + (prop['repair_reserve'] or 0)
        if total_monthly > 35000:
            weaknesses.append(f"維持費が高め（月{total_monthly:,}円）")
    
    if not weaknesses:
        weaknesses.append("特に大きな懸念点はありません")
    
    return {
        'comment': comment,
        'strengths': strengths[:3],  # 最大3つ
        'weaknesses': weaknesses[:3]  # 最大3つ
    }

# スコアリング実行
# @st.cache_data(ttl=10)
def calculate_scores(properties):
    """物件のスコアを計算"""
    scorer = SafePropertyScorer()
    results = []
    
    for prop in properties:
        # 比較対象の抽出
        try:
            comparable = [p for p in properties if p.get('station_name') == prop.get('station_name') and p.get('source_id') != prop.get('source_id')]
        except Exception as e:
            st.error(f"Error filtering comparable: {e}")
            st.write("Current prop:", prop)
            raise e
            
        try:
            # スコア計算の実行
            score_result = scorer.calculate_score(prop, comparable)
            
            results.append({
                'property': prop,
                'score': score_result
            })
        except TypeError as e:
            st.error(f"❌ TypeError detected in scoring loop")
            st.write(f"Error Detail: {e}")
            st.write("--- Object Information ---")
            st.write("Prop Type:", type(prop))
            st.write("Prop Sample:", {k: v for i, (k, v) in enumerate(prop.items()) if i < 5})
            st.write("Comparable Type:", type(comparable))
            if comparable:
                st.write("First Comparable Element Type:", type(comparable[0]))
            
            # 内部のどこで起きてるかさらに絞り込み
            st.write("--- Sub-scorer check ---")
            try:
                from src.scoring.price_scorer import PriceScorer
                ps = PriceScorer()
                st.write("PriceScorer test result:", ps.calculate(prop, comparable))
            except Exception as pe:
                st.write("PriceScorer failed with:", pe)
                
            raise e
        except Exception as e:
            st.error(f"General Error: {e}")
            raise e
    
    # スコア順にソート
    try:
        results.sort(key=lambda x: x['score']['total_score'], reverse=True)
    except Exception as e:
        st.error(f"Error sorting results: {e}")
        if results:
            st.write("First result score detail:", results[0].get('score'))
        raise e
        
    return results

# メインコンテンツ
properties = get_properties_from_db(
    layout_filter=layout_filter, 
    city_filter=city_filter,
    price_range=(price_min, price_max),
    station_filter=station_filter,
    age_range=(age_min, age_max),
    prefecture_filter=selected_prefs
)
scored_properties = calculate_scores(properties)

# 統計情報
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("総物件数", f"{len(properties)}件")

if scored_properties:
    with col2:
        avg_score = sum([r['score']['total_score'] for r in scored_properties]) / len(scored_properties)
        st.metric("平均スコア", f"{avg_score:.1f}点")
    with col3:
        avg_price = sum([r['property']['price'] for r in scored_properties]) / len(scored_properties)
        st.metric("平均価格", f"{avg_price:.0f}万円")
    with col4:
        avg_sqm = sum([r['property']['price_per_sqm'] for r in scored_properties]) / len(scored_properties)
        st.metric("平均㎡単価", f"{avg_sqm/10000:.1f}万円")
else:
    with col2:
        st.metric("平均スコア", "N/A")
    with col3:
        st.metric("平均価格", "N/A")
    with col4:
        st.metric("平均㎡単価", "N/A")

st.markdown("---")

# 物件一覧
st.header("📋 物件一覧（お得度順）")

# ページネーション
ITEMS_PER_PAGE = 20
total_items = len(scored_properties)
total_pages = max(1, (total_items - 1) // ITEMS_PER_PAGE + 1)

if total_items > 0:
    col_p1, col_p2 = st.columns([1, 4])
    with col_p1:
        current_page = st.number_input("ページ", min_value=1, max_value=total_pages, value=1)
    
    start_idx = (current_page - 1) * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, total_items)
    
    st.info(f"全 {total_items} 件中 {start_idx + 1} 〜 {end_idx} 件を表示しています")
    
    # ページ表示用のスライス
    display_properties = scored_properties[start_idx:end_idx]
    
    for i, result in enumerate(display_properties):
        display_idx = start_idx + i + 1
        prop = result['property']
        score_data = result['score']
        total_score = score_data['total_score']
        rank = score_data['rank']
        
        # 物件分析を生成
        analysis = generate_property_analysis(prop, score_data)
        
        with st.expander(f"**{display_idx}位** - {prop['title']} - **{total_score}点** {rank}", expanded=(i < 3)):
            # 基本情報
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"### 📍 基本情報")
                st.markdown(f"**物件名**: {prop['title']}")
                st.markdown(f"**住所**: {prop['address']}")
                
                # アクセス情報
                if prop.get('access_info'):
                    st.markdown("**🚉 交通アクセス**:")
                    access_list = prop['access_info'].split('\n')
                    for access in access_list:
                        clean = re.sub(r'^[ \t\n\r\]\[]+|[ \t\n\r\]\[]+$', '', access).strip()
                        if clean:
                            st.markdown(f"&nbsp;&nbsp;◦ {clean}")
                else:
                    if prop['station_distance']:
                        st.markdown(f"**最寄駅**: {prop['station_name']}駅 徒歩{prop['station_distance']}分")
                    else:
                        st.markdown(f"**最寄駅**: {prop['station_name']}駅")
                
                st.markdown(f"**向き**: {prop['direction'] or '不明'}")
                st.markdown(f"**物件URL**: [{prop['url']}]({prop['url']})")
                
                if prop.get('first_seen'):
                    first_seen_str = prop['first_seen'].strftime('%Y年%m月%d日 %H:%M')
                    st.markdown(f"**データ取得日**: {first_seen_str}")
                
                if prop.get('last_updated') and prop.get('first_seen'):
                    if prop['last_updated'] != prop['first_seen']:
                        last_updated_str = prop['last_updated'].strftime('%Y年%m月%d日 %H:%M')
                        st.markdown(f"**最終更新日**: {last_updated_str}")
                
                st.markdown("### 💬 一言コメント")
                st.info(analysis['comment'])
                
                col_s, col_w = st.columns(2)
                with col_s:
                    st.markdown("### ✅ 強み")
                    for strength in analysis['strengths']:
                        st.markdown(f"- {strength}")
                
                with col_w:
                    st.markdown("### ⚠️ 弱み")
                    for weakness in analysis['weaknesses']:
                        st.markdown(f"- {weakness}")
                
                st.markdown(f"### 💰 価格情報")
                price_data = {
                    "項目": ["価格", "専有面積", "㎡単価"],
                    "値": [
                        f"{prop['price']:,}万円",
                        f"{prop['area']}㎡",
                        f"{prop['price_per_sqm'] / 10000:.1f}万円/㎡"
                    ]
                }
                st.table(price_data)
                
                st.markdown(f"### 🏠 物件詳細")
                detail_data = {
                    "項目": ["築年数", "間取り", "階数", "向き"],
                    "値": [
                        f"{prop['building_age']}年",
                        prop['layout'],
                        f"{prop['floor']}階",
                        prop['direction']
                    ]
                }
                st.table(detail_data)
                
                st.markdown(f"### 💵 維持費")
                mgmt_fee = prop['management_fee'] if prop['management_fee'] else 0
                repair_fee = prop['repair_reserve'] if prop['repair_reserve'] else 0
                
                cost_data = {
                    "項目": ["管理費", "修繕積立金", "合計"],
                    "値": [
                        f"{prop['management_fee']:,}円/月" if prop['management_fee'] else "データなし",
                        f"{prop['repair_reserve']:,}円/月" if prop['repair_reserve'] else "データなし",
                        f"{(mgmt_fee + repair_fee):,}円/月" if (mgmt_fee + repair_fee) > 0 else "データなし"
                    ]
                }
                st.table(cost_data)
            
            with col2:
                st.markdown(f"### 📊 スコア詳細")
                st.markdown(f"**総合スコア**: {total_score}点")
                st.markdown(f"**ランク**: {rank}")
                st.markdown("")
                
                st.markdown("**カテゴリ別スコア（100点満点換算）**")
                
                # 各カテゴリの満点（ScorerのMAX_SCOREに準拠）
                max_scores = {
                    'price': 30.0,
                    'location': 25.0,
                    'spec': 25.0,
                    'cost': 15.0,
                    'future': 5.0
                }
                
                categories = score_data['category_scores']
                for cat, score in categories.items():
                    cat_name = {
                        'price': '💰 価格適正性',
                        'location': '📍 立地',
                        'spec': '🏠 スペック',
                        'cost': '💵 維持コスト',
                        'future': '📈 将来性'
                    }[cat]
                    
                    m_score = max_scores.get(cat, 30.0)
                    normalized_score = (score / m_score) * 100
                    st.metric(cat_name, f"{normalized_score:.1f}点")
                
                st.markdown("### 📈 スコア可視化")
                
                # チャート用に100点満点に正規化
                radar_values = []
                radar_categories = ['💰 価格', '📍 立地', '🏠 スペ', '💵 コスト', '📈 将来性']
                
                # 順序をチャートに合わせる
                cat_keys = ['price', 'location', 'spec', 'cost', 'future']
                for key in cat_keys:
                    val = categories.get(key, 0)
                    m_score = max_scores.get(key, 30.0)
                    normalized = (val / m_score) * 100
                    radar_values.append(normalized)
                
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(
                    r=radar_values,
                    theta=radar_categories,
                    fill='toself',
                    name='スコア（100点換算）',
                    hovertemplate="%{theta}: %{r:.1f}点"
                ))
                
                fig.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True, 
                            range=[0, 100],
                            tickfont=dict(size=10)
                        )
                    ),
                    showlegend=False,
                    height=300,
                    margin=dict(l=40, r=40, t=20, b=20)
                )
                
                st.plotly_chart(fig, use_container_width=True, key=f"radar_chart_{display_idx}")
else:
    st.info("表示する物件がありません。フィルタ条件を変更してください。")

# フッター
st.markdown("---")
st.markdown("""
### ⚠️ 注意事項
- このシステムは個人的な物件調査の効率化を目的としています
- スコアは参考値であり、最終的な判断は自己責任でお願いします
- 実際の物件購入前には必ず現地確認と専門家への相談をお勧めします
""")
