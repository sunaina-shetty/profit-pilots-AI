import hmac
import hashlib
import json
import time
from typing import Dict, Any, Tuple
from backend.shared.config import RISK_TOKEN_SECRET

def generate_risk_token(payload: Dict[str, Any], expires_in_seconds: int = 30) -> str:
    """
    Generate an HMAC-SHA256 signed approval token bound to an approved order payload.
    Valid for a short duration (default 30s) to prevent replay attacks.
    """
    expires_at = time.time() + expires_in_seconds
    token_data = {
        "symbol": payload.get("symbol"),
        "side": payload.get("side"),
        "qty": payload.get("qty"),
        "stop_loss": payload.get("stop_loss"),
        "entry_price": payload.get("entry_price"),
        "expires_at": expires_at,
        "nonce": payload.get("nonce", time.time())
    }
    serialized = json.dumps(token_data, sort_keys=True)
    sig = hmac.new(
        RISK_TOKEN_SECRET.encode("utf-8"),
        serialized.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"{sig}:{serialized}"

def verify_risk_token(token_str: str, expected_payload: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Verify the cryptographic signature, expiration, and payload match of an approval token.
    """
    if not token_str or ":" not in token_str:
        return False, "Malformed token format"
    
    try:
        sig, serialized = token_str.split(":", 1)
        expected_sig = hmac.new(
            RISK_TOKEN_SECRET.encode("utf-8"),
            serialized.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(sig, expected_sig):
            return False, "Invalid token cryptographic signature"
        
        data = json.loads(serialized)
        
        # Check expiration
        if time.time() > data.get("expires_at", 0):
            return False, "Risk approval token has expired"
        
        # Check payload integrity
        for key in ["symbol", "side", "qty"]:
            if str(data.get(key)) != str(expected_payload.get(key)):
                return False, f"Token mismatch on {key}: token has {data.get(key)}, order has {expected_payload.get(key)}"
        
        return True, "Valid"
    except Exception as e:
        return False, f"Token verification error: {str(e)}"

