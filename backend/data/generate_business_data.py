"""
IntelliOps AI — Synthetic Relational Business Data Generator
Generates logically consistent, deterministic enterprise business data for:
- Sales Forecasting (temporal trends, seasonality, daily patterns)
- Customer Churn Prediction (RFM features, tenure, activity drop-offs, explicit 90-day churn target)
- Product Demand Estimation (product-level volumes and stock levels)
- Anomaly Detection (controlled, documented synthetic anomalies)
- Customer Segmentation (clustering on behavioral RFM & tier attributes)
- Marketing Campaign Analytics (campaign spend, reach, and regional lift)
"""

import sqlite3
import random
import os
import sys
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple

# Ensure parent directory (backend) is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_business_data(
    db_path: str = "datascout.db",
    scale: str = "small",
    seed: int = 42,
    force: bool = False
) -> Dict[str, int]:
    """
    Generates deterministic synthetic business data and populates the SQLite database.
    
    Args:
        db_path: Path to the SQLite database file
        scale: Dataset size ('small', 'medium', 'large')
        seed: Random seed for deterministic reproducibility
        force: If True, clear existing business tables before inserting
        
    Returns:
        Dictionary of row counts created per table
    """
    logger.info(f"Generating synthetic business data [Scale: {scale.upper()}, Seed: {seed}] -> {db_path}")
    random.seed(seed)

    # Scale configuration parameters
    scale_configs = {
        "small": {
            "num_customers": 150,
            "min_orders_per_customer": 2,
            "max_orders_per_customer": 12,
            "campaign_count": 10,
            "interactions_per_customer": (4, 15),
            "ticket_probability": 0.45,
        },
        "medium": {
            "num_customers": 500,
            "min_orders_per_customer": 3,
            "max_orders_per_customer": 18,
            "campaign_count": 20,
            "interactions_per_customer": (6, 22),
            "ticket_probability": 0.50,
        },
        "large": {
            "num_customers": 2000,
            "min_orders_per_customer": 4,
            "max_orders_per_customer": 25,
            "campaign_count": 40,
            "interactions_per_customer": (8, 30),
            "ticket_probability": 0.55,
        }
    }
    config = scale_configs.get(scale.lower(), scale_configs["small"])

    # Ensure schema is present
    from db_schema import init_relational_schema, get_connection
    init_relational_schema(db_path)

    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM customers;")
    existing_customers = cursor.fetchone()[0]
    if existing_customers > 0 and not force:
        logger.info(f"Database already contains {existing_customers} customers. Skipping generation (use force=True to regenerate).")
        counts = {}
        for tbl in ["categories", "products", "customers", "marketing_campaigns", "orders", "order_items", "payments", "inventory", "customer_interactions", "support_tickets"]:
            cursor.execute(f"SELECT COUNT(*) FROM {tbl};")
            counts[tbl] = cursor.fetchone()[0]
        conn.close()
        return counts

    try:
        cursor.execute("BEGIN TRANSACTION;")

        if force:
            logger.info("Force flag detected: clearing relational business tables...")
            for tbl in ["payments", "order_items", "orders", "support_tickets", "customer_interactions", "inventory", "marketing_campaigns", "customers", "products", "categories"]:
                cursor.execute(f"DELETE FROM {tbl};")

        # ----------------------------------------------------------------------
        # 1. Product Categories (5 realistic enterprise tech categories)
        # ----------------------------------------------------------------------
        categories_data = [
            (1, "Enterprise Software", "On-premise and hybrid core operational intelligence software licenses"),
            (2, "Cloud Subscriptions", "SaaS and cloud-hosted subscription tiers with monthly/annual billing"),
            (3, "Hardware & Edge Devices", "Specialized telemetry, IoT gateways, and enterprise server appliances"),
            (4, "Professional Services", "Architecture design, deployment engineering, and custom consulting"),
            (5, "Cybersecurity & Compliance", "Access governance, automated audit logging, and security monitoring add-ons")
        ]
        cursor.executemany("INSERT INTO categories (id, name, description) VALUES (?, ?, ?);", categories_data)

        # ----------------------------------------------------------------------
        # 2. Products (15 standardized SKUs across categories)
        # ----------------------------------------------------------------------
        products_data = [
            # Enterprise Software (Category 1)
            (1, "SW-DS-CORE", "DataScout Core Platform License", 1, 12000.00, 2400.00, "active"),
            (2, "SW-DS-ADV", "DataScout Advanced Analytics Suite", 1, 24000.00, 4800.00, "active"),
            (3, "SW-DS-ENT", "DataScout Enterprise Unlimited", 1, 48000.00, 8000.00, "active"),
            # Cloud Subscriptions (Category 2)
            (4, "SAAS-BAS", "DataScout Cloud Starter (Annual)", 2, 3600.00, 720.00, "active"),
            (5, "SAAS-PRO", "DataScout Cloud Professional (Annual)", 2, 9600.00, 1800.00, "active"),
            (6, "SAAS-ENT", "DataScout Cloud Enterprise Plus", 2, 24000.00, 4200.00, "active"),
            # Hardware & Edge (Category 3)
            (7, "HW-GW-100", "DataScout Edge Gateway 100", 3, 1850.00, 1150.00, "active"),
            (8, "HW-GW-500", "DataScout Industrial Gateway 500", 3, 4200.00, 2600.00, "active"),
            (9, "HW-SRV-900", "DataScout Telemetry Appliance Server", 3, 9800.00, 6400.00, "active"),
            # Professional Services (Category 4)
            (10, "PS-DEP-SM", "Standard Implementation Package", 4, 5000.00, 2500.00, "active"),
            (11, "PS-DEP-LG", "Enterprise Architecture Onboarding", 4, 15000.00, 7500.00, "active"),
            (12, "PS-HLTH", "Platform Health Check & Optimization", 4, 3500.00, 1500.00, "active"),
            # Cybersecurity & Compliance (Category 5)
            (13, "SEC-AUD", "Continuous Audit & Compliance Scanner", 5, 4500.00, 1200.00, "active"),
            (14, "SEC-ENC", "Hardware-Grade Zero-Trust Encryption", 5, 7500.00, 2100.00, "active"),
            (15, "SEC-SOC", "Managed Security Intelligence Feed", 5, 11000.00, 3300.00, "active"),
        ]
        cursor.executemany("""
            INSERT INTO products (id, sku, name, category_id, unit_price, unit_cost, status)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, products_data)

        # ----------------------------------------------------------------------
        # 3. Inventory Setup (4 regions: NA, EMEA, APAC, LATAM)
        # ----------------------------------------------------------------------
        regions = ["NA", "EMEA", "APAC", "LATAM"]
        inventory_data = []
        for p in products_data:
            p_id = p[0]
            cat_id = p[3]
            for reg in regions:
                if cat_id == 3:  # Physical Hardware
                    stock = random.randint(40, 250)
                    reorder = 35
                    safety = 20
                else:  # Digital/Service (unlimited virtual capacity, tracked for capacity planning)
                    stock = 9999
                    reorder = 100
                    safety = 50
                inventory_data.append((p_id, reg, stock, reorder, safety, "2024-01-05"))
        cursor.executemany("""
            INSERT INTO inventory (product_id, warehouse_region, stock_on_hand, reorder_point, safety_stock, last_restocked_date)
            VALUES (?, ?, ?, ?, ?, ?);
        """, inventory_data)

        # ----------------------------------------------------------------------
        # 4. Marketing Campaigns (Historical calendar 2024-2025)
        # ----------------------------------------------------------------------
        campaigns_data = [
            (1, "Q1-2024-NewYear-Launch", "Search / PPC", 45000.0, 43200.0, "2024-01-10", "2024-02-28", "All", "completed"),
            (2, "Q2-2024-CloudMigration-Push", "Webinar / Event", 35000.0, 36500.0, "2024-04-01", "2024-05-15", "NA", "completed"),
            (3, "Q3-2024-APAC-Expansion", "Direct Outreach", 60000.0, 58900.0, "2024-07-01", "2024-08-31", "APAC", "completed"),
            (4, "Q4-2024-BudgetFlush-Promo", "Email", 25000.0, 24100.0, "2024-11-01", "2024-12-20", "All", "completed"),
            (5, "CyberWeek-2024-FlashOffer", "Search / PPC", 30000.0, 31200.0, "2024-11-24", "2024-11-30", "NA", "completed"),
            (6, "Q1-2025-SecurityFirst-Tour", "Webinar / Event", 40000.0, 39500.0, "2025-01-15", "2025-03-01", "EMEA", "completed"),
            (7, "Q2-2025-EdgeAI-Summit", "Social Media", 20000.0, 19800.0, "2025-04-10", "2025-05-20", "All", "completed"),
            (8, "Q3-2025-PartnerSynergy", "Partner Referral", 50000.0, 48200.0, "2025-07-15", "2025-08-31", "LATAM", "completed"),
            (9, "Q4-2025-EnterpriseUpgrade", "Email", 28000.0, 27500.0, "2025-10-15", "2025-12-15", "All", "completed"),
            (10, "CyberWeek-2025-CloudBooster", "Search / PPC", 35000.0, 34800.0, "2025-11-23", "2025-11-29", "All", "completed"),
        ]
        cursor.executemany("""
            INSERT INTO marketing_campaigns (id, name, channel, budget, spend, start_date, end_date, target_region, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, campaigns_data)

        # ----------------------------------------------------------------------
        # 5. Customers
        # ----------------------------------------------------------------------
        industries = ["Financial Services", "Healthcare", "Manufacturing", "Retail & E-commerce", "Technology & SaaS", "Logistics & Energy"]
        company_suffixes = ["Technologies", "Enterprises", "Holdings", "Logistics", "Health", "Capital", "Group", "Solutions", "Systems"]
        first_names = ["James", "Emma", "Liam", "Olivia", "Noah", "Ava", "Alexander", "Sophia", "Daniel", "Isabella", "David", "Mia", "Marcus", "Elena", "Carlos"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Chen", "Patel", "Muller", "Tanaka", "Silva", "Taylor", "Wilson"]

        tier_weights = ["Enterprise"] * 25 + ["Mid-Market"] * 45 + ["SMB"] * 30
        region_weights = ["NA"] * 40 + ["EMEA"] * 30 + ["APAC"] * 20 + ["LATAM"] * 10

        customers_data = []
        customer_churn_status = {}  # cust_id -> bool is_churned

        start_calendar = datetime(2024, 1, 1)

        for c_id in range(1, config["num_customers"] + 1):
            c_code = f"CUST-{c_id:04d}"
            industry = random.choice(industries)
            c_name = f"{random.choice(last_names)} {random.choice(company_suffixes)}"
            contact = f"{random.choice(first_names)} {random.choice(last_names)}"
            email = f"contact.{c_id}@{c_name.lower().replace(' ', '').replace('&', '')}.com"
            region = random.choice(region_weights)
            tier = random.choice(tier_weights)
            
            # Signup date distributed across 2024 and early 2025
            signup_days = random.randint(0, 450)
            signup_dt = start_calendar + timedelta(days=signup_days)
            signup_date = signup_dt.strftime("%Y-%m-%d")

            # Assign synthetic churn pattern: ~22-26% of customers will deliberately churn
            # (no purchases after 2024-10-01)
            is_churn_candidate = (random.random() < 0.36) and (signup_days < 350)
            customer_churn_status[c_id] = is_churn_candidate

            is_active = 0 if is_churn_candidate else 1
            customers_data.append((c_id, c_code, c_name, contact, email, region, tier, industry, signup_date, is_active))

        cursor.executemany("""
            INSERT INTO customers (id, customer_code, company_name, contact_name, email, region, tier, industry, signup_date, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, customers_data)

        # ----------------------------------------------------------------------
        # 6. Orders and Order Items
        # ----------------------------------------------------------------------
        orders_data = []
        order_items_data = []
        payments_data = []
        interactions_data = []
        tickets_data = []

        order_id_counter = 1
        item_id_counter = 1
        payment_id_counter = 1
        ticket_id_counter = 1
        interaction_id_counter = 1

        end_calendar = datetime(2025, 12, 31)
        churn_cutoff_date = datetime(2024, 10, 1)

        # Map products for fast price lookup: id -> (price, cat_id)
        prod_map = {p[0]: (p[4], p[3]) for p in products_data}

        for c in customers_data:
            c_id = c[0]
            c_region = c[5]
            c_tier = c[6]
            c_signup = datetime.strptime(c[8], "%Y-%m-%d")
            is_churned = customer_churn_status[c_id]

            # Determine order count for customer
            if is_churned:
                # Churned customers place 1-3 orders early, then stop
                num_orders = random.randint(1, 3)
                max_order_date = churn_cutoff_date
            else:
                if c_tier == "Enterprise":
                    num_orders = random.randint(config["min_orders_per_customer"] + 3, config["max_orders_per_customer"] + 5)
                elif c_tier == "Mid-Market":
                    num_orders = random.randint(config["min_orders_per_customer"] + 1, config["max_orders_per_customer"])
                else:
                    num_orders = random.randint(config["min_orders_per_customer"], config["max_orders_per_customer"] - 2)
                max_order_date = end_calendar

            # Generate order dates chronologically
            available_days = max(1, (max_order_date - c_signup).days)
            order_days = sorted([random.randint(0, available_days) for _ in range(num_orders)])

            for day_offset in order_days:
                order_dt = c_signup + timedelta(days=day_offset)
                if order_dt > end_calendar:
                    continue
                
                # Check for Anomaly 1: APAC Supply Chain Shock (August - September 2024)
                # In APAC during this window, hardware orders drop significantly
                is_apac_shock = (c_region == "APAC" and datetime(2024, 8, 1) <= order_dt <= datetime(2024, 9, 30))

                # Check for Anomaly 2: Cyber Week Spike (late November)
                is_cyber_week = (
                    (datetime(2024, 11, 24) <= order_dt <= datetime(2024, 11, 30)) or
                    (datetime(2025, 11, 23) <= order_dt <= datetime(2025, 11, 29))
                )

                # Match active marketing campaign if applicable
                matched_campaign = None
                order_date_str = order_dt.strftime("%Y-%m-%d")
                for camp in campaigns_data:
                    c_start = datetime.strptime(camp[5], "%Y-%m-%d")
                    c_end = datetime.strptime(camp[6], "%Y-%m-%d")
                    c_target = camp[7]
                    if c_start <= order_dt <= c_end and (c_target == "All" or c_target == c_region):
                        matched_campaign = camp[0]
                        break

                # Determine order items count (1-4 products per order)
                num_items = random.choices([1, 2, 3, 4], weights=[50, 30, 15, 5])[0]
                selected_prods = random.sample(list(prod_map.keys()), num_items)

                order_subtotal = 0.0
                current_order_items = []

                for p_id in selected_prods:
                    unit_p, cat_id = prod_map[p_id]
                    
                    # If APAC hardware shock, suppress hardware quantity or skip
                    if is_apac_shock and cat_id == 3 and random.random() < 0.70:
                        continue
                    
                    # Quantity based on tier
                    if c_tier == "Enterprise":
                        qty = random.randint(2, 8) if cat_id in (2, 3) else 1
                    elif c_tier == "Mid-Market":
                        qty = random.randint(1, 4) if cat_id in (2, 3) else 1
                    else:
                        qty = 1
                    
                    # Discount logic
                    item_discount_rate = 0.05 if (matched_campaign or is_cyber_week) else 0.0
                    item_total = round(qty * unit_p * (1.0 - item_discount_rate), 2)
                    order_subtotal += item_total

                    current_order_items.append((
                        item_id_counter,
                        order_id_counter,
                        p_id,
                        qty,
                        unit_p,
                        round(qty * unit_p * item_discount_rate, 2),
                        item_total
                    ))
                    item_id_counter += 1

                if not current_order_items:
                    continue

                order_subtotal = round(order_subtotal, 2)
                # Regional tax rates (approximate B2B)
                tax_rate = 0.06 if c_region == "NA" else (0.19 if c_region == "EMEA" else 0.0)
                tax_amt = round(order_subtotal * tax_rate, 2)
                order_discount = 50.0 if (order_subtotal > 10000.0 and matched_campaign) else 0.0
                total_amount = round(order_subtotal + tax_amt - order_discount, 2)

                # Order status distribution
                status = random.choices(["completed", "completed", "completed", "cancelled", "refunded"], weights=[88, 5, 3, 2, 2])[0]
                order_num = f"ORD-{order_dt.strftime('%Y%m')}-{order_id_counter:05d}"

                orders_data.append((
                    order_id_counter,
                    order_num,
                    c_id,
                    matched_campaign,
                    order_date_str,
                    order_subtotal,
                    order_discount,
                    tax_amt,
                    total_amount,
                    status
                ))
                order_items_data.extend(current_order_items)

                # Generate Payment record
                payment_methods = ["Bank Wire", "Credit Card", "ACH Transfer", "Net 30 Invoicing"]
                pay_num = f"PAY-{order_dt.strftime('%Y%m')}-{payment_id_counter:05d}"
                pay_method = random.choice(payment_methods)
                
                if status == "completed":
                    payments_data.append((payment_id_counter, pay_num, order_id_counter, order_date_str, total_amount, pay_method, "completed"))
                    payment_id_counter += 1
                elif status == "refunded":
                    payments_data.append((payment_id_counter, pay_num, order_id_counter, order_date_str, total_amount, pay_method, "completed"))
                    payment_id_counter += 1
                    ref_num = f"REF-{order_dt.strftime('%Y%m')}-{payment_id_counter:05d}"
                    payments_data.append((payment_id_counter, ref_num, order_id_counter, order_date_str, total_amount, pay_method, "refunded"))
                    payment_id_counter += 1
                elif status == "cancelled":
                    payments_data.append((payment_id_counter, pay_num, order_id_counter, order_date_str, total_amount, pay_method, "failed"))
                    payment_id_counter += 1

                order_id_counter += 1

            # ------------------------------------------------------------------
            # 7. Customer Engagement Interactions
            # ------------------------------------------------------------------
            num_interactions = random.randint(*config["interactions_per_customer"])
            if is_churned:
                # Interactions cease after churn date
                interaction_max_dt = churn_cutoff_date
            else:
                interaction_max_dt = end_calendar
            
            span_days = max(1, (interaction_max_dt - c_signup).days)
            for _ in range(num_interactions):
                i_dt = c_signup + timedelta(days=random.randint(0, span_days))
                i_channel = random.choice(["Platform Login", "API Call", "Email Opened", "Sales Call", "Executive Review", "Webinar"])
                i_type = "Routine Activity" if "Login" in i_channel or "API" in i_channel else "Business Engagement"
                interactions_data.append((
                    interaction_id_counter,
                    c_id,
                    i_dt.strftime("%Y-%m-%d"),
                    i_channel,
                    i_type,
                    f"Customer interaction recorded via {i_channel}."
                ))
                interaction_id_counter += 1

            # ------------------------------------------------------------------
            # 8. Support Tickets
            # ------------------------------------------------------------------
            if random.random() < config["ticket_probability"]:
                num_tickets = random.randint(1, 4)
                for _ in range(num_tickets):
                    t_dt = c_signup + timedelta(days=random.randint(0, span_days))
                    t_date_str = t_dt.strftime("%Y-%m-%d")
                    t_num = f"TCK-{ticket_id_counter:05d}"
                    p_ref = random.choice(list(prod_map.keys()))

                    # Check for Anomaly 3: Software Incident in March 2025
                    is_incident_window = (datetime(2025, 3, 1) <= t_dt <= datetime(2025, 3, 31))
                    if is_incident_window and prod_map[p_ref][1] == 1:
                        cat = "Bug / Defect"
                        priority = "Critical"
                        csat = random.choice([1, 2])
                        hours = round(random.uniform(48.0, 168.0), 1)
                        t_status = "resolved"
                    else:
                        cat = random.choice(["Bug / Defect", "Billing / Invoice", "Integration Help", "Performance", "Feature Request", "Onboarding"])
                        priority = random.choice(["Low", "Medium", "High"])
                        csat = random.choice([3, 4, 5, 5])
                        hours = round(random.uniform(2.0, 36.0), 1)
                        t_status = "resolved" if t_dt < datetime(2025, 12, 15) else "open"

                    res_dt = (t_dt + timedelta(hours=hours)).strftime("%Y-%m-%d") if t_status == "resolved" else None

                    tickets_data.append((
                        ticket_id_counter,
                        t_num,
                        c_id,
                        p_ref,
                        t_date_str,
                        res_dt,
                        cat,
                        priority,
                        t_status,
                        hours if t_status == "resolved" else None,
                        csat if t_status == "resolved" else None
                    ))
                    ticket_id_counter += 1

        # Batch insert all records
        logger.info(f"Inserting {len(orders_data)} orders...")
        cursor.executemany("""
            INSERT INTO orders (id, order_number, customer_id, campaign_id, order_date, subtotal, discount, tax, total_amount, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, orders_data)

        logger.info(f"Inserting {len(order_items_data)} order items...")
        cursor.executemany("""
            INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, discount, total_price)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, order_items_data)

        logger.info(f"Inserting {len(payments_data)} payments...")
        cursor.executemany("""
            INSERT INTO payments (id, payment_number, order_id, payment_date, amount, payment_method, status)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, payments_data)

        logger.info(f"Inserting {len(interactions_data)} customer interactions...")
        cursor.executemany("""
            INSERT INTO customer_interactions (id, customer_id, interaction_date, channel, interaction_type, notes)
            VALUES (?, ?, ?, ?, ?, ?);
        """, interactions_data)

        logger.info(f"Inserting {len(tickets_data)} support tickets...")
        cursor.executemany("""
            INSERT INTO support_tickets (id, ticket_number, customer_id, product_id, created_date, resolved_date, category, priority, status, resolution_time_hours, customer_satisfaction)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, tickets_data)

        conn.commit()
        logger.info("[OK] Synthetic business data generated and committed successfully.")

        # Compute summary counts
        row_counts = {
            "categories": len(categories_data),
            "products": len(products_data),
            "customers": len(customers_data),
            "marketing_campaigns": len(campaigns_data),
            "orders": len(orders_data),
            "order_items": len(order_items_data),
            "payments": len(payments_data),
            "inventory": len(inventory_data),
            "customer_interactions": len(interactions_data),
            "support_tickets": len(tickets_data)
        }
        for tbl, cnt in row_counts.items():
            logger.info(f"  - {tbl}: {cnt:,} rows")

        return row_counts

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to generate synthetic data: {str(e)}", exc_info=True)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic business data for IntelliOps AI")
    parser.add_argument("--db", type=str, default="datascout.db", help="Target SQLite database file")
    parser.add_argument("--scale", type=str, default="small", choices=["small", "medium", "large"], help="Dataset size scale")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    parser.add_argument("--force", action="store_true", help="Clear and regenerate existing relational business data")
    args = parser.parse_args()

    generate_business_data(db_path=args.db, scale=args.scale, seed=args.seed, force=args.force)
