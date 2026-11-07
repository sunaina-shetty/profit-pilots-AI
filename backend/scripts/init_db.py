import os
import sys

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from backend.shared.db import init_sql_tables, get_mongo_collection

def main():
    print("=" * 60)
    print("ProfitPilot AI - Initializing Database Schemas")
    print("=" * 60)
    
    print("[1/2] Creating SQL Relational Tables (MySQL / SQLite fallback)...")
    init_sql_tables()
    print("      -> system_state: created & seeded")
    print("      -> account_balance: created & initialized (Rs 1,00,000.00)")
    print("      -> orders: created")
    print("      -> positions: created")
    print("      -> risk_events: created")

    print("[2/2] Checking Mongo Collections (MongoDB / JSON fallback)...")
    j_coll = get_mongo_collection("decision_journal")
    count = j_coll.count_documents({})
    print(f"      -> decision_journal collection ready (current count: {count})")
    
    print("Database initialization completed successfully!\n")

if __name__ == "__main__":
    main()

