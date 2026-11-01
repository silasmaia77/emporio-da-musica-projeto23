import sqlite3
import unicodedata
from contextlib import contextmanager
from pathlib import Path

def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(text or '').lower()) if not unicodedata.combining(c))

@contextmanager
def connect(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=15000')
    conn.create_function('norm', 1, normalize, deterministic=True)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def initialize(path):
    with connect(path) as c:
        c.execute('PRAGMA journal_mode=WAL')
        c.executescript('''
        CREATE TABLE IF NOT EXISTS categories(category_id INTEGER PRIMARY KEY,name TEXT NOT NULL,description TEXT);
        CREATE TABLE IF NOT EXISTS customers(customer_id INTEGER PRIMARY KEY,name TEXT,phone TEXT,email TEXT,city TEXT,phone_e164 TEXT);
        CREATE TABLE IF NOT EXISTS products(product_id INTEGER PRIMARY KEY,category_id INTEGER REFERENCES categories,name TEXT NOT NULL,description TEXT,price_cents INTEGER NOT NULL CHECK(price_cents>=0),stock_quantity INTEGER CHECK(stock_quantity>=0),status TEXT,specs_json TEXT,created_at TEXT,quality_status TEXT);
        CREATE TABLE IF NOT EXISTS orders(order_id INTEGER PRIMARY KEY,customer_id INTEGER REFERENCES customers,order_date TEXT,status TEXT,total_cents INTEGER,payment_method TEXT,tracking_code TEXT,estimated_delivery TEXT,notes TEXT);
        CREATE TABLE IF NOT EXISTS order_items(item_id INTEGER PRIMARY KEY,order_id INTEGER REFERENCES orders,product_id INTEGER REFERENCES products,quantity INTEGER CHECK(quantity>0));
        CREATE TABLE IF NOT EXISTS promotions(promotion_id INTEGER PRIMARY KEY,product_id INTEGER REFERENCES products,discount_percent REAL CHECK(discount_percent BETWEEN 0 AND 100),description TEXT,is_active INTEGER CHECK(is_active IN (0,1)));
        CREATE TABLE IF NOT EXISTS source_aux(sheet TEXT,row_number INTEGER,data_json TEXT,PRIMARY KEY(sheet,row_number));
        CREATE TABLE IF NOT EXISTS import_runs(id INTEGER PRIMARY KEY,sha256 TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS sessions(session_id TEXT PRIMARY KEY,customer_id INTEGER REFERENCES customers,auth_source TEXT NOT NULL DEFAULT 'anonymous');
        CREATE TABLE IF NOT EXISTS turns(id INTEGER PRIMARY KEY,session_id TEXT REFERENCES sessions,role TEXT,content TEXT,created_at REAL);
        CREATE TABLE IF NOT EXISTS queue(id INTEGER PRIMARY KEY,message_id TEXT UNIQUE NOT NULL,session_id TEXT NOT NULL,sender TEXT NOT NULL,body TEXT NOT NULL,inbound_at REAL NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',attempts INTEGER NOT NULL DEFAULT 0,available_at REAL NOT NULL DEFAULT 0,lease_until REAL,reply TEXT,outbound_json TEXT,error TEXT);
        CREATE TABLE IF NOT EXISTS support(id INTEGER PRIMARY KEY,session_id TEXT REFERENCES sessions,summary TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS identity_bindings(sender TEXT PRIMARY KEY,customer_id INTEGER REFERENCES customers,verified_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
        CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
        CREATE INDEX IF NOT EXISTS idx_items_order ON order_items(order_id);
        CREATE INDEX IF NOT EXISTS idx_items_product ON order_items(product_id);
        CREATE INDEX IF NOT EXISTS idx_promotions_product ON promotions(product_id);
        CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id,id);
        CREATE INDEX IF NOT EXISTS idx_queue_status ON queue(status,available_at,id);
        DROP VIEW IF EXISTS catalog;
        CREATE VIEW catalog AS SELECT p.*,c.name AS category_name,
          COALESCE((SELECT MAX(discount_percent) FROM promotions t WHERE t.product_id=p.product_id AND t.is_active=1),0) AS discount_percent,
          (SELECT COUNT(*) FROM promotions t WHERE t.product_id=p.product_id AND t.is_active=1) AS active_promotion_count,
          CASE WHEN p.status='active' AND p.stock_quantity>0 THEN 1 ELSE 0 END AS can_offer
          FROM products p JOIN categories c USING(category_id);
        ''')
