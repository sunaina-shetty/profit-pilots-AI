import os
import sys
import time

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from backend.shared.db import get_mongo_collection, SQL_ENGINE
from sqlalchemy import text

def seed_demo_data():
    print("Seeding demo events and historical journal logs...")
    coll = get_mongo_collection("decision_journal")
    
    sample_entries = [
        {
            "event_type": "CYCLE_DECISION",
            "symbol": "RELIANCE.NS",
            "price": 2865.20,
            "decision": {
                "action": "BUY",
                "size_tier": "FULL",
                "reason": "Unanimous Consensus (3/3): Trend, News, and Contrarian agree on BUY setup.",
                "agent_votes": {
                    "trend": {"vote": "BUY", "confidence": 0.88},
                    "news": {"vote": "BUY", "confidence": 0.82},
                    "contrarian": {"vote": "BUY", "confidence": 0.70}
                }
            },
            "risk_verdict": {
                "approved": True,
                "qty": 35,
                "stop_loss": 2822.20,
                "reason": "Approved 1% equity risk sizing (35 shares, FULL tier)"
            },
            "plain_text": "EXECUTED BUY 35 shares of RELIANCE.NS at Rs 2865.20 with mandatory stop-loss at Rs 2822.20. Council consensus: Unanimous agreement across trend, news sentiment, and technical health.",
            "timestamp": time.time() - 3600
        },
        {
            "event_type": "CYCLE_DECISION",
            "symbol": "RELIANCE.NS",
            "price": 2894.50,
            "decision": {
                "action": "HOLD",
                "size_tier": "ZERO",
                "reason": "Disagreement detected (1 BUY, 1 SELL, 1 HOLD). Disagreement is a risk signal -> HOLD.",
                "agent_votes": {
                    "trend": {"vote": "BUY", "confidence": 0.65},
                    "news": {"vote": "HOLD", "confidence": 0.50},
                    "contrarian": {"vote": "SELL", "confidence": 0.75}
                }
            },
            "risk_verdict": {"approved": False, "reason": "No actionable consensus (HOLD)"},
            "plain_text": "At Rs 2894.50, the council opted to HOLD RELIANCE.NS. Contrarian agent detected overbought resistance. Zero capital committed.",
            "timestamp": time.time() - 1800
        }
    ]

    for entry in sample_entries:
        coll.insert_one(entry)

    print(f"Seeded {len(sample_entries)} historical journal entries successfully!")

if __name__ == "__main__":
    seed_demo_data()

