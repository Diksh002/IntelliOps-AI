import sqlite3
import random
from datetime import datetime, timedelta

def generate_seed_data():
    print("Generating synthetic enterprise data...")
    random.seed(42)
    
    # Connect to SQLite
    conn = sqlite3.connect("datascout.db")
    cursor = conn.cursor()
    
    # 1. Transactions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            region TEXT,
            product TEXT,
            amount REAL,
            category TEXT
        )
    """)
    
    regions = ["NA", "EMEA", "APAC", "LATAM"]
    products = ["DataScout Pro", "DataScout Lite", "Consulting", "Support"]
    categories = ["Software", "Services"]
    
    data = []
    start_date = datetime(2024, 1, 1)
    
    for i in range(1000):
        date = start_date + timedelta(days=random.randint(0, 364))
        region = random.choice(regions)
        product = random.choice(products)
        category = "Software" if "DataScout" in product else "Services"
        amount = random.uniform(1000, 50000)
        
        data.append((date.strftime("%Y-%m-%d"), region, product, round(amount, 2), category))
        
    cursor.execute("SELECT COUNT(*) FROM transactions")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO transactions (date, region, product, amount, category) VALUES (?, ?, ?, ?, ?)", data)
        print("Inserted 1000 synthetic transaction records.")
    else:
        print("Transactions table already contains data, skipping insertion.")
    
    # 2. Payroll Table (Sensitive)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payroll (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT,
            name TEXT,
            salary REAL,
            department TEXT
        )
    """)
    
    payroll_data = [
        ("EMP001", "Alice Smith", 120000, "Engineering"),
        ("EMP002", "Bob Jones", 85000, "Sales"),
        ("EMP003", "Charlie Brown", 95000, "Marketing"),
    ]
    cursor.execute("SELECT COUNT(*) FROM payroll")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO payroll (employee_id, name, salary, department) VALUES (?, ?, ?, ?)", payroll_data)
        print("Inserted 3 payroll records.")
    else:
        print("Payroll table already contains data, skipping insertion.")

    conn.commit()
    conn.close()
    print("Database seeded successfully: datascout.db")

if __name__ == "__main__":
    generate_seed_data()
