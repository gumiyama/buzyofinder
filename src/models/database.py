"""
Database models for property data
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()


class Property(Base):
    """物件情報モデル"""
    __tablename__ = 'properties'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # データソース情報
    source = Column(String(50), nullable=False)  # SUUMO, HOMES, athome
    source_id = Column(String(100), unique=True, nullable=False)  # ソースサイトの物件ID
    url = Column(Text, nullable=False)

    # 基本情報
    title = Column(String(200))
    price = Column(Integer)  # 価格（万円）
    area = Column(Float)  # 専有面積（㎡）
    price_per_sqm = Column(Float)  # ㎡単価

    # 物件詳細
    building_age = Column(Integer)  # 築年数
    floor = Column(Integer)  # 階数
    direction = Column(String(10))  # 向き（南、東、西、北）
    layout = Column(String(20))  # 間取り（3LDK等）

    # 立地情報
    address = Column(String(300))
    prefecture = Column(String(20))  # 都道府県
    city = Column(String(50))  # 市区町村
    station_name = Column(String(100))  # 最寄駅
    station_distance = Column(Integer)  # 駅距離（分）
    access_info = Column(Text)  # 全てのアクセス情報（改行区切り等）

    # コスト情報
    management_fee = Column(Integer)  # 管理費（円）
    repair_reserve = Column(Integer)  # 修繕積立金（円）

    # 設備（JSON形式で保存）
    features = Column(Text)  # {"auto_lock": true, "pet_ok": false, ...}

    # メタデータ
    # first_seen: 初めて物件を発見した日時
    # last_seen_at: データソース上で最後に存在確認できた日時
    # price_changed_at: 最後に価格変更を検知した日時（新規登録時はNULL）
    # last_updated: 価格変更や再掲載など、物件レコードの実質的な変更日時
    first_seen = Column(DateTime, default=datetime.now)
    last_seen_at = Column(DateTime, default=datetime.now)
    price_changed_at = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)  # 販売中かどうか

    def __repr__(self):
        return f"<Property(id={self.id}, title='{self.title}', price={self.price}万円)>"


class PropertyScore(Base):
    """物件スコア情報モデル"""
    __tablename__ = 'property_scores'

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(Integer, nullable=False)  # Property.id への参照

    # スコア（各カテゴリ）
    total_score = Column(Float)  # 総合スコア
    price_score = Column(Float)  # 価格適正性スコア（30点満点）
    location_score = Column(Float)  # 立地スコア（25点満点）
    spec_score = Column(Float)  # 物件スペックスコア（25点満点）
    cost_score = Column(Float)  # 維持コストスコア（15点満点）
    future_score = Column(Float)  # 将来性スコア（5点満点）

    # ターゲット層
    target_type = Column(String(20))  # 'family' or 'dinks'

    # メタデータ
    calculated_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<PropertyScore(property_id={self.property_id}, total={self.total_score:.1f})>"


class AreaStats(Base):
    """エリア統計情報モデル"""
    __tablename__ = 'area_stats'

    id = Column(Integer, primary_key=True, autoincrement=True)
    area_code = Column(String(50), unique=True, nullable=False)  # 市区町村コード
    area_name = Column(String(100))  # エリア名

    # 統計情報
    avg_price_per_sqm = Column(Float)  # 平均㎡単価
    median_price = Column(Float)  # 中央値価格
    std_price_per_sqm = Column(Float)  # ㎡単価の標準偏差
    sample_count = Column(Integer)  # サンプル数

    # メタデータ
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<AreaStats(area={self.area_name}, avg_price={self.avg_price_per_sqm:.0f}円/㎡)>"


class PriceHistory(Base):
    """物件価格履歴モデル"""
    __tablename__ = 'price_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(Integer, nullable=False)  # Property.id への参照
    price = Column(Integer, nullable=False)  # 価格（万円）
    recorded_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<PriceHistory(property_id={self.property_id}, price={self.price}万円, date={self.recorded_at})>"


def _ensure_property_observation_columns(engine):
    """既存SQLite DBへ観測日時カラムを安全に追加・初期化する。"""
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(properties)")).fetchall()
        if not rows:
            # 新規DBはBase.metadata.create_all()で最新スキーマが作られる。
            return

        columns = {row[1] for row in rows}
        if 'last_seen_at' not in columns:
            conn.execute(text("ALTER TABLE properties ADD COLUMN last_seen_at DATETIME"))
        if 'price_changed_at' not in columns:
            conn.execute(text("ALTER TABLE properties ADD COLUMN price_changed_at DATETIME"))

        # 既存レコードは、少なくとも最後にDB更新された時点までは存在確認済みとみなす。
        conn.execute(text("""
            UPDATE properties
            SET last_seen_at = COALESCE(last_seen_at, last_updated, first_seen)
            WHERE last_seen_at IS NULL
        """))

        # 価格履歴が2件以上ある物件だけ、最新履歴日時を価格変更日時として復元する。
        # 初回登録1件だけの物件は「価格変更なし」なのでNULLのままにする。
        conn.execute(text("""
            UPDATE properties
            SET price_changed_at = (
                SELECT MAX(ph.recorded_at)
                FROM price_history ph
                WHERE ph.property_id = properties.id
            )
            WHERE price_changed_at IS NULL
              AND (
                  SELECT COUNT(*)
                  FROM price_history ph2
                  WHERE ph2.property_id = properties.id
              ) > 1
        """))


def get_engine(db_path='data/mansion_scientist.db'):
    """データベースエンジンを取得"""
    engine = create_engine(f'sqlite:///{db_path}')
    _ensure_property_observation_columns(engine)
    return engine


def init_db(db_path='data/mansion_scientist.db'):
    """データベースを初期化"""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """データベースセッションを取得"""
    Session = sessionmaker(bind=engine)
    return Session()


def save_or_update_property(session, detail, source_id):
    """物件情報を保存または更新（存在確認日時・価格履歴付き）"""
    try:
        existing = session.query(Property).filter_by(source_id=source_id).first()
        now = datetime.now()

        if existing:
            # ページ取得に成功した時点で「現在も掲載を確認できた」と記録する。
            existing.last_seen_at = now

            # 将来is_active=False運用を入れても、再発見時は安全に復帰できる。
            if existing.is_active is False:
                existing.is_active = True
                existing.last_updated = now

            # 価格変更のチェック
            new_price = detail.get('price')
            if new_price and existing.price != new_price:
                history = PriceHistory(
                    property_id=existing.id,
                    price=new_price,
                    recorded_at=now
                )
                session.add(history)

                existing.price = new_price
                existing.price_per_sqm = detail.get('price_per_sqm')
                existing.price_changed_at = now
                existing.last_updated = now
                session.commit()
                return "updated"

            # 価格不変でも存在確認日時は必ず保存する。
            session.commit()
            return "exists"

        # 新規保存
        property_obj = Property(
            source=detail.get('source', 'SUUMO'),
            source_id=source_id,
            url=detail.get('url'),
            title=detail.get('title'),
            price=detail.get('price'),
            area=detail.get('area'),
            price_per_sqm=detail.get('price_per_sqm'),
            layout=detail.get('layout'),
            building_age=detail.get('building_age'),
            floor=detail.get('floor'),
            direction=detail.get('direction'),
            address=detail.get('address'),
            prefecture=detail.get('prefecture'),
            city=detail.get('city'),
            station_name=detail.get('station_name'),
            station_distance=detail.get('station_distance'),
            access_info=detail.get('access_info'),
            management_fee=detail.get('management_fee'),
            repair_reserve=detail.get('repair_reserve'),
            features=detail.get('features', '{}'),
            is_active=True,
            first_seen=now,
            last_seen_at=now,
            price_changed_at=None,
            last_updated=now
        )
        session.add(property_obj)
        session.flush()  # IDを取得するためにフラッシュ

        # 初回価格も履歴に記録。ただし「価格変更」とは扱わない。
        if property_obj.price:
            history = PriceHistory(
                property_id=property_obj.id,
                price=property_obj.price,
                recorded_at=now
            )
            session.add(history)

        session.commit()
        return "saved"
    except Exception:
        session.rollback()
        raise
