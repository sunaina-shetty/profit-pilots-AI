import os
import json
import time
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.shared.config import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB,
    MONGO_URI, STARTING_CASH
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ----------------- SQL Database Layer ----------------- #
def get_sql_engine():
    """
    Returns a SQLAlchemy Engine for MySQL if accessible;
    otherwise falls back gracefully to SQLite.
    """
    mysql_url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    try:
        engine = create_engine(mysql_url, pool_pre_ping=True, pool_recycle=300)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine, "mysql"
    except Exception:
        # Fallback to local SQLite database
        sqlite_file = DATA_DIR / "profitpilot.db"
        sqlite_url = f"sqlite:///{sqlite_file}"
        engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
        return engine, "sqlite"

SQL_ENGINE, SQL_DIALECT = get_sql_engine()
SQLSession = sessionmaker(bind=SQL_ENGINE)

def init_sql_tables():
    """Create all relational tables required by PS-02."""
    with SQL_ENGINE.connect() as conn:
        trans = conn.begin()
        try:
            # 1. Kill Switch & System State table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS system_state (
                    key_name VARCHAR(64) PRIMARY KEY,
                    val_str VARCHAR(256),
                    updated_at DOUBLE
                )
            """))

            # 2. Account balance & equity table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS account_balance (
                    id INT PRIMARY KEY,
                    cash DOUBLE NOT NULL,
                    start_of_day_equity DOUBLE NOT NULL,
                    realized_pnl DOUBLE DEFAULT 0.0,
                    unrealized_pnl DOUBLE DEFAULT 0.0,
                    updated_at DOUBLE NOT NULL
                )
            """))

            # 3. Orders table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id VARCHAR(64) PRIMARY KEY,
                    symbol VARCHAR(32) NOT NULL,
                    side VARCHAR(16) NOT NULL,
                    qty INT NOT NULL,
                    price DOUBLE NOT NULL,
                    stop_loss DOUBLE NOT NULL,
                    take_profit DOUBLE,
                    status VARCHAR(32) NOT NULL,
                    fees DOUBLE DEFAULT 0.0,
                    slippage DOUBLE DEFAULT 0.0,
                    approval_token TEXT,
                    created_at DOUBLE NOT NULL
                )
            """))

            # 4. Positions table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS positions (
                    symbol VARCHAR(32) PRIMARY KEY,
                    qty INT NOT NULL,
                    avg_entry_price DOUBLE NOT NULL,
                    current_price DOUBLE NOT NULL,
                    unrealized_pnl DOUBLE DEFAULT 0.0,
                    stop_loss DOUBLE NOT NULL,
                    take_profit DOUBLE,
                    updated_at DOUBLE NOT NULL
                )
            """))

            # 5. Risk events table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS risk_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type VARCHAR(64) NOT NULL,
                    symbol VARCHAR(32),
                    reason TEXT NOT NULL,
                    details TEXT,
                    created_at DOUBLE NOT NULL
                )
            """) if SQL_DIALECT == "sqlite" else text("""
                CREATE TABLE IF NOT EXISTS risk_events (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    event_type VARCHAR(64) NOT NULL,
                    symbol VARCHAR(32),
                    reason TEXT NOT NULL,
                    details TEXT,
                    created_at DOUBLE NOT NULL
                )
            """))

            # Seed system state if not existing
            res = conn.execute(text("SELECT val_str FROM system_state WHERE key_name = 'kill_switch'")).fetchone()
            if not res:
                conn.execute(text("INSERT INTO system_state (key_name, val_str, updated_at) VALUES ('kill_switch', 'OFF', :ts)"), {"ts": time.time()})
                conn.execute(text("INSERT INTO system_state (key_name, val_str, updated_at) VALUES ('market_state', 'RUNNING', :ts)"), {"ts": time.time()})

            # Seed starting account balance if not existing
            res_bal = conn.execute(text("SELECT id FROM account_balance WHERE id = 1")).fetchone()
            if not res_bal:
                conn.execute(text("""
                    INSERT INTO account_balance (id, cash, start_of_day_equity, realized_pnl, unrealized_pnl, updated_at)
                    VALUES (1, :cash, :equity, 0.0, 0.0, :ts)
                """), {"cash": STARTING_CASH, "equity": STARTING_CASH, "ts": time.time()})

            trans.commit()
        except Exception as e:
            trans.rollback()
            raise e


# ----------------- Mongo Document Layer ----------------- #
class FileMongoCollection:
    """Fallback JSON-based file storage when standalone MongoDB is not reachable."""
    def __init__(self, name: str):
        self.name = name
        self.file_path = DATA_DIR / f"mongo_{name}.json"
        if not self.file_path.exists():
            with open(self.file_path, "w") as f:
                json.dump([], f)

    def _read(self):
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def _write(self, docs):
        with open(self.file_path, "w") as f:
            json.dump(docs, f, indent=2)

    def insert_one(self, doc):
        docs = self._read()
        doc_copy = dict(doc)
        if "_id" not in doc_copy:
            doc_copy["_id"] = f"{int(time.time()*1000)}_{len(docs)}"
        docs.append(doc_copy)
        self._write(docs)
        return doc_copy

    def find(self, filter_dict=None, sort=None, limit=None):
        docs = self._read()
        if filter_dict:
            res = []
            for d in docs:
                match = True
                for k, v in filter_dict.items():
                    if d.get(k) != v:
                        match = False
                        break
                if match:
                    res.append(d)
            docs = res
        if sort:
            key, direction = sort[0]
            docs = sorted(docs, key=lambda x: x.get(key, 0), reverse=(direction < 0))
        if limit:
            docs = docs[:limit]
        return docs

    def count_documents(self, filter_dict=None):
        return len(self.find(filter_dict or {}))


def get_mongo_collection(coll_name: str):
    """
    Returns a PyMongo Collection if MongoDB server is active,
    or transparently returns a local file-based collection.
    """
    try:
        import pymongo
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=500)
        client.server_info()
        db = client.get_database()
        return db[coll_name]
    except Exception:
        return FileMongoCollection(coll_name)

