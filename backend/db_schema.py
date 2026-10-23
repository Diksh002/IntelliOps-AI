"""
IntelliOps AI — Relational Business Database Schema
Defines the normalized relational schema for enterprise business analytics,
sales forecasting, customer churn prediction, and decision intelligence.
"""

import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_connection(db_path: str = "datascout.db", read_only: bool = False) -> sqlite3.Connection:
    """
    Get an active SQLite connection with row factory and foreign keys enabled.
    """
    if read_only:
        uri = f"file:{os.path.abspath(db_path)}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        conn = sqlite3.connect(db_path)
    
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_relational_schema(db_path: str = "datascout.db") -> None:
    """
    Safely creates all relational business tables and indexes without
    dropping or modifying existing tables (such as transactions and payroll).
    """
    logger.info(f"Initializing Relational Business Schema in: {db_path}")
    conn = get_connection(db_path)
    cursor = conn.cursor()

    try:
        # Start transaction
        cursor.execute("BEGIN TRANSACTION;")

        # 1. Product Categories
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Products
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
                unit_price REAL NOT NULL CHECK(unit_price > 0),
                unit_cost REAL NOT NULL CHECK(unit_cost > 0),
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'discontinued', 'upcoming')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. Customers
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_code TEXT NOT NULL UNIQUE,
                company_name TEXT NOT NULL,
                contact_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                region TEXT NOT NULL CHECK(region IN ('NA', 'EMEA', 'APAC', 'LATAM')),
                tier TEXT NOT NULL CHECK(tier IN ('Enterprise', 'Mid-Market', 'SMB')),
                industry TEXT NOT NULL,
                signup_date TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1))
            );
        """)

        # 4. Marketing Campaigns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS marketing_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                channel TEXT NOT NULL CHECK(channel IN (
                    'Email', 'Search / PPC', 'Social Media', 
                    'Webinar / Event', 'Direct Outreach', 'Partner Referral'
                )),
                budget REAL NOT NULL CHECK(budget >= 0),
                spend REAL NOT NULL CHECK(spend >= 0),
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                target_region TEXT NOT NULL CHECK(target_region IN ('All', 'NA', 'EMEA', 'APAC', 'LATAM')),
                status TEXT NOT NULL DEFAULT 'completed' CHECK(status IN ('planned', 'active', 'completed', 'cancelled'))
            );
        """)

        # 5. Orders
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT NOT NULL UNIQUE,
                customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
                campaign_id INTEGER REFERENCES marketing_campaigns(id) ON DELETE SET NULL,
                order_date TEXT NOT NULL,
                subtotal REAL NOT NULL CHECK(subtotal >= 0),
                discount REAL NOT NULL DEFAULT 0.0 CHECK(discount >= 0),
                tax REAL NOT NULL DEFAULT 0.0 CHECK(tax >= 0),
                total_amount REAL NOT NULL CHECK(total_amount >= 0),
                status TEXT NOT NULL CHECK(status IN ('completed', 'pending', 'cancelled', 'refunded')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 6. Order Items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                unit_price REAL NOT NULL CHECK(unit_price >= 0),
                discount REAL NOT NULL DEFAULT 0.0 CHECK(discount >= 0),
                total_price REAL NOT NULL CHECK(total_price >= 0),
                UNIQUE(order_id, product_id)
            );
        """)

        # 7. Payments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_number TEXT NOT NULL UNIQUE,
                order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                payment_date TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                payment_method TEXT NOT NULL CHECK(payment_method IN (
                    'Credit Card', 'Bank Wire', 'ACH Transfer', 'Net 30 Invoicing', 'PayPal'
                )),
                status TEXT NOT NULL CHECK(status IN ('completed', 'pending', 'failed', 'refunded'))
            );
        """)

        # 8. Inventory (Product stock per regional warehouse)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                warehouse_region TEXT NOT NULL CHECK(warehouse_region IN ('NA', 'EMEA', 'APAC', 'LATAM')),
                stock_on_hand INTEGER NOT NULL CHECK(stock_on_hand >= 0),
                reorder_point INTEGER NOT NULL CHECK(reorder_point >= 0),
                safety_stock INTEGER NOT NULL CHECK(safety_stock >= 0),
                last_restocked_date TEXT,
                UNIQUE(product_id, warehouse_region)
            );
        """)

        # 9. Customer Interactions (Engagement touchpoints for churn modeling)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                interaction_date TEXT NOT NULL,
                channel TEXT NOT NULL CHECK(channel IN (
                    'Platform Login', 'API Call', 'Email Opened', 'Sales Call', 'Executive Review', 'Webinar'
                )),
                interaction_type TEXT NOT NULL,
                notes TEXT
            );
        """)

        # 10. Support Tickets (Customer satisfaction & churn indicators)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_number TEXT NOT NULL UNIQUE,
                customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
                created_date TEXT NOT NULL,
                resolved_date TEXT,
                category TEXT NOT NULL CHECK(category IN (
                    'Bug / Defect', 'Billing / Invoice', 'Integration Help', 
                    'Performance', 'Feature Request', 'Onboarding'
                )),
                priority TEXT NOT NULL CHECK(priority IN ('Low', 'Medium', 'High', 'Critical')),
                status TEXT NOT NULL CHECK(status IN ('open', 'in_progress', 'resolved', 'closed')),
                resolution_time_hours REAL CHECK(resolution_time_hours IS NULL OR resolution_time_hours >= 0),
                customer_satisfaction INTEGER CHECK(
                    customer_satisfaction IS NULL OR (customer_satisfaction >= 1 AND customer_satisfaction <= 5)
                )
            );
        """)

        # Indexes for High-Performance Business Queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_region ON customers(region);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_tier ON customers(tier);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_product ON inventory(product_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_customer ON customer_interactions(customer_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_date ON customer_interactions(interaction_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_support_tickets_customer ON support_tickets(customer_id);")

        conn.commit()
        logger.info("[OK] Relational business schema initialized successfully.")

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to initialize relational schema: {str(e)}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    init_relational_schema()
