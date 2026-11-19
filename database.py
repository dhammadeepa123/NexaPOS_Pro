import sqlite3
import hashlib
import shutil
import os
from datetime import datetime, timedelta
import random

DB_NAME = "nexapos.db"
BACKUP_DIR = "backups"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def setup_database():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Users Table (SHA-256 Encrypted Passwords + Roles)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)

    # 2. Products Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        cost_price REAL NOT NULL,
        sell_price REAL NOT NULL,
        stock INTEGER NOT NULL,
        min_stock INTEGER DEFAULT 5
    )
    """)

    # 3. Sales Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT UNIQUE NOT NULL,
        customer_name TEXT DEFAULT 'Walk-in Customer',
        subtotal REAL NOT NULL,
        discount REAL DEFAULT 0,
        tax REAL DEFAULT 0,
        total REAL NOT NULL,
        profit REAL NOT NULL,
        payment_method TEXT DEFAULT 'Cash',
        sale_date TEXT NOT NULL
    )
    """)

    # 4. Sale Items Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sale_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        qty INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        line_total REAL NOT NULL,
        FOREIGN KEY (sale_id) REFERENCES sales(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
    """)

    # Default Users (Admin & Cashier)
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            [
                ("admin", hash_password("admin123"), "Admin"),
                ("cashier", hash_password("cashier123"), "Cashier"),
            ],
        )

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        seed_demo_data(conn)

    conn.close()

def seed_demo_data(conn):
    cursor = conn.cursor()
    demo_products = [
        ("TECH-001", "Wireless Gaming Mouse", "Electronics", 3200, 4800, 24, 5),
        ("TECH-002", "Mechanical Keyboard RGB", "Electronics", 8500, 12500, 12, 4),
        ("TECH-003", "USB-C Fast Charger 65W", "Accessories", 2800, 4200, 3, 5),
        ("TECH-004", "Noise Cancelling Headset", "Audio", 9500, 14900, 9, 3),
        ("TECH-005", "1TB NVMe SSD Drive", "Storage", 14000, 19500, 15, 4),
        ("TECH-006", "24-inch IPS Monitor", "Monitors", 32000, 42500, 6, 2),
        ("TECH-007", "Laptop Cooling Pad", "Accessories", 2200, 3600, 18, 5),
        ("TECH-008", "Bluetooth Speaker Pro", "Audio", 5400, 8200, 4, 5),
        ("TECH-009", "Webcam 1080p HD", "Electronics", 4100, 6500, 11, 4),
        ("TECH-010", "External HDD 2TB", "Storage", 15500, 21000, 2, 4),
    ]
    cursor.executemany("""
        INSERT INTO products (sku, name, category, cost_price, sell_price, stock, min_stock)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, demo_products)
    conn.commit()

    cursor.execute("SELECT id, name, cost_price, sell_price FROM products")
    prods = cursor.fetchall()

    customers = ["Kasun Perera", "Nimali Silva", "Dilshan Fernando", "Walk-in Customer", "Tharindu Jayasinghe"]
    payments = ["Cash", "Card", "Bank Transfer"]

    for day_offset in range(6, -1, -1):
        date_obj = datetime.now() - timedelta(days=day_offset)
        for _ in range(random.randint(2, 3)):
            inv_no = f"INV-{date_obj.strftime('%Y%m%d')}-{random.randint(100,999)}"
            cust = random.choice(customers)
            pay = random.choice(payments)
            picked = random.sample(prods, random.randint(1, 3))

            subtotal = 0
            total_cost = 0
            items_to_insert = []
            for p in picked:
                q = random.randint(1, 2)
                lt = q * p["sell_price"]
                subtotal += lt
                total_cost += q * p["cost_price"]
                items_to_insert.append((p["id"], p["name"], q, p["sell_price"], lt))

            discount = round(subtotal * 0.05, 2) if subtotal > 15000 else 0
            tax = round((subtotal - discount) * 0.02, 2)
            total = round(subtotal - discount + tax, 2)
            profit = round((subtotal - discount) - total_cost, 2)
            sale_time = date_obj.strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
                INSERT INTO sales (invoice_no, customer_name, subtotal, discount, tax, total, profit, payment_method, sale_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (inv_no, cust, subtotal, discount, tax, total, profit, pay, sale_time))
            sale_id = cursor.lastrowid

            for pid, pname, q, uprice, lt in items_to_insert:
                cursor.execute("""
                    INSERT INTO sale_items (sale_id, product_id, product_name, qty, unit_price, line_total)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (sale_id, pid, pname, q, uprice, lt))

    conn.commit()

# --- AUTHENTICATION ---
def authenticate_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username, role FROM users WHERE username = ? AND password_hash = ?",
        (username.strip(), hash_password(password.strip())),
    )
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

# --- BACKUP ---
def backup_database():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"nexapos_backup_{ts}.db")
    shutil.copy2(DB_NAME, dest)
    return dest

# --- PRODUCT CRUD & LOW STOCK ---
def get_all_products(search_query=""):
    conn = get_connection()
    cursor = conn.cursor()
    if search_query:
        q = f"%{search_query}%"
        cursor.execute("SELECT * FROM products WHERE name LIKE ? OR sku LIKE ? OR category LIKE ? ORDER BY id DESC", (q, q, q))
    else:
        cursor.execute("SELECT * FROM products ORDER BY id DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_low_stock_products():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE stock <= min_stock ORDER BY stock ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def restock_product(prod_id, add_qty=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (int(add_qty), prod_id))
    conn.commit()
    conn.close()

def add_product(sku, name, category, cost_price, sell_price, stock, min_stock=5):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO products (sku, name, category, cost_price, sell_price, stock, min_stock)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (sku, name, category, float(cost_price), float(sell_price), int(stock), int(min_stock)))
    conn.commit()
    conn.close()

def update_product(prod_id, sku, name, category, cost_price, sell_price, stock, min_stock):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE products SET sku=?, name=?, category=?, cost_price=?, sell_price=?, stock=?, min_stock=?
        WHERE id=?
    """, (sku, name, category, float(cost_price), float(sell_price), int(stock), int(min_stock), prod_id))
    conn.commit()
    conn.close()

def delete_product(prod_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id=?", (prod_id,))
    conn.commit()
    conn.close()

# --- CHECKOUT & SALES ---
def record_sale(customer_name, cart_items, discount_pct, tax_pct, payment_method):
    conn = get_connection()
    cursor = conn.cursor()

    inv_no = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    subtotal = sum(item['qty'] * item['sell_price'] for item in cart_items)
    total_cost = sum(item['qty'] * item['cost_price'] for item in cart_items)
    discount_amt = round(subtotal * (discount_pct / 100.0), 2)
    tax_amt = round((subtotal - discount_amt) * (tax_pct / 100.0), 2)
    grand_total = round(subtotal - discount_amt + tax_amt, 2)
    net_profit = round((subtotal - discount_amt) - total_cost, 2)
    sale_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO sales (invoice_no, customer_name, subtotal, discount, tax, total, profit, payment_method, sale_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (inv_no, customer_name or "Walk-in Customer", subtotal, discount_amt, tax_amt, grand_total, net_profit, payment_method, sale_date))
    sale_id = cursor.lastrowid

    for item in cart_items:
        line_total = round(item['qty'] * item['sell_price'], 2)
        cursor.execute("""
            INSERT INTO sale_items (sale_id, product_id, product_name, qty, unit_price, line_total)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sale_id, item['id'], item['name'], item['qty'], item['sell_price'], line_total))
        cursor.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (item['qty'], item['id']))

    conn.commit()
    conn.close()

    return {
        "invoice_no": inv_no,
        "customer_name": customer_name or "Walk-in Customer",
        "subtotal": subtotal,
        "discount": discount_amt,
        "tax": tax_amt,
        "total": grand_total,
        "profit": net_profit,
        "payment_method": payment_method,
        "sale_date": sale_date,
        "items": cart_items,
    }

def get_sale_details_by_invoice(invoice_no):
    """Past Invoice Viewer & Reprint PDF සඳහා සම්පූර්ණ විස්තර ගන්නවා"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sales WHERE invoice_no = ?", (invoice_no,))
    sale = cursor.fetchone()
    if not sale:
        conn.close()
        return None
    sale_dict = dict(sale)
    cursor.execute("SELECT product_name as name, qty, unit_price as sell_price, line_total FROM sale_items WHERE sale_id = ?", (sale_dict["id"],))
    sale_dict["items"] = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return sale_dict

# --- ANALYTICS ---
def get_dashboard_kpis():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(SUM(total), 0), COALESCE(SUM(profit), 0), COUNT(*) FROM sales")
    revenue, profit, total_orders = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) FROM products WHERE stock <= min_stock")
    low_stock_count = cursor.fetchone()[0]
    conn.close()
    return {
        "revenue": round(revenue, 2),
        "profit": round(profit, 2),
        "orders": total_orders,
        "low_stock": low_stock_count,
    }

def get_daily_sales_chart_data():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT substr(sale_date, 1, 10) as day, SUM(total) as daily_rev, SUM(profit) as daily_prof
        FROM sales GROUP BY day ORDER BY day ASC LIMIT 10
    """)
    rows = cursor.fetchall()
    conn.close()
    return [r["day"][5:] for r in rows], [r["daily_rev"] for r in rows], [r["daily_prof"] for r in rows]

def get_category_stock_chart_data():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT category, SUM(stock) as total_stock FROM products GROUP BY category")
    rows = cursor.fetchall()
    conn.close()
    return [r["category"] for r in rows], [r["total_stock"] for r in rows]

def get_all_sales():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sales ORDER BY id DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows