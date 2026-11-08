import os
import math
import hashlib
import datetime
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List, Optional
from simulation.config import TOTAL_DAY_CANDLES

# B: 5-minute window is approximately 60 trading days back from today
REAL_5MIN_WINDOW_TRADING_DAYS = 60
_ONLINE_FAILED = False

def get_seed_from_str(s: str) -> int:
    return int(hashlib.md5(s.encode('utf-8')).hexdigest()[:8], 16)

def is_within_5min_window(date_str: str) -> bool:
    """B: Returns True if the date is within yfinance's ~60-trading-day 5-min history window."""
    try:
        target = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        today = datetime.date.today()
        # Approximate: 60 trading days ~ 84 calendar days
        cutoff = today - datetime.timedelta(days=84)
        return target >= cutoff and target <= today
    except Exception:
        return False

def fetch_daily_ohlc(symbol: str, target_date_str: str = None) -> Tuple[Dict[str, float], str, str]:
    """
    Fetches real daily OHLC from yfinance.
    Returns: (ohlc_dict, data_source_label, resolved_date_str)
    """
    global _ONLINE_FAILED
    if os.getenv("OFFLINE", "0") == "1" or _ONLINE_FAILED:
        return _get_mock_daily_ohlc(symbol, target_date_str)

    try:
        import yfinance as yf
        # Format symbol for NSE if needed
        yf_symbol = symbol if symbol.endswith(".NS") or "." in symbol else f"{symbol}.NS"
        ticker = yf.Ticker(yf_symbol)

        # Pull 5 days of history to capture target date and previous close
        df = ticker.history(period="1mo", interval="1d")
        if df.empty:
            return _get_mock_daily_ohlc(symbol, target_date_str)

        df = df.reset_index()
        # Normalise Date column to YYYY-MM-DD string
        df["DateStr"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

        if target_date_str:
            matched_rows = df[df["DateStr"] == target_date_str]
            if matched_rows.empty:
                # Target date not in history, take last available trading day before target date
                prev_rows = df[df["DateStr"] <= target_date_str]
                if not prev_rows.empty:
                    idx = prev_rows.index[-1]
                else:
                    idx = df.index[-1]
            else:
                idx = matched_rows.index[0]
        else:
            idx = df.index[-1]

        target_row = df.iloc[idx]
        resolved_date = target_row["DateStr"]

        # Previous close
        if idx > 0:
            prev_close = float(df.iloc[idx - 1]["Close"])
        else:
            prev_close = float(target_row["Open"]) * 0.995

        open_p = round(float(target_row["Open"]), 2)
        high_p = round(float(target_row["High"]), 2)
        low_p = round(float(target_row["Low"]), 2)
        close_p = round(float(target_row["Close"]), 2)
        volume = int(target_row["Volume"]) if "Volume" in target_row and not pd.isna(target_row["Volume"]) else 2500000

        # Safety checks
        high_p = max(high_p, open_p, close_p)
        low_p = min(low_p, open_p, close_p)
        if high_p == low_p:
            high_p += 1.0
            low_p = max(0.5, low_p - 1.0)

        ohlc = {
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "prev_close": round(prev_close, 2),
            "volume": max(10000, volume)
        }
        return ohlc, "REAL DAILY BAR -> SIMULATED INTRADAY PATH", resolved_date

    except Exception as e:
        _ONLINE_FAILED = True
        return _get_mock_daily_ohlc(symbol, target_date_str)

def _get_mock_daily_ohlc(symbol: str, target_date_str: str = None) -> Tuple[Dict[str, float], str, str]:
    today = target_date_str or datetime.date.today().strftime("%Y-%m-%d")
    seed = get_seed_from_str(f"{symbol}_{today}_mock")
    rng = np.random.RandomState(seed)

    base_price = 3850.0 if "TCS" in symbol else (2900.0 if "RELIANCE" in symbol else 1500.0)
    drift = rng.uniform(-0.02, 0.02)
    open_p = round(base_price * (1.0 + drift), 2)
    prev_close = round(base_price, 2)

    range_pct = rng.uniform(0.015, 0.035)
    high_p = round(open_p * (1.0 + range_pct * rng.uniform(0.4, 0.9)), 2)
    low_p = round(open_p * (1.0 - range_pct * rng.uniform(0.4, 0.9)), 2)
    close_p = round(rng.uniform(low_p, high_p), 2)

    high_p = max(high_p, open_p, close_p)
    low_p = min(low_p, open_p, close_p)
    volume = int(rng.uniform(1500000, 5000000))

    ohlc = {
        "open": open_p,
        "high": high_p,
        "low": low_p,
        "close": close_p,
        "prev_close": prev_close,
        "volume": volume
    }
    return ohlc, "OFFLINE DEMO DATA", today

def fetch_5min_candles(
    symbol: str,
    target_date_str: str
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], bool, str, float]:
    """
    B: Fetch 5-minute intraday candles for a given date.
    Returns:
      (candles_today, warmup_candles, is_real, data_banner, avg_opening_volume)

    candles_today: list of 5m candle dicts covering 09:15–15:30 for target_date
    warmup_candles: list of 5m candle dicts for 14+ prior trading days (for indicator warm-up)
    is_real: True if real yfinance 5m data was found
    data_banner: string message for the UI
    avg_opening_volume: average first-bar volume across prior 14 days (for ORB "in play" check)
    """
    global _ONLINE_FAILED
    if os.getenv("OFFLINE", "0") == "1" or _ONLINE_FAILED:
        # Offline fallback: synthetic path
        return _synthetic_5min_fallback(symbol, target_date_str)

    if not is_within_5min_window(target_date_str):
        return _synthetic_5min_fallback(symbol, target_date_str)

    try:
        import yfinance as yf
        yf_symbol = symbol if symbol.endswith(".NS") or "." in symbol else f"{symbol}.NS"
        ticker = yf.Ticker(yf_symbol)

        # Fetch 60 days of 5-min data
        df_5m = ticker.history(period="60d", interval="5m")
        if df_5m.empty:
            return _synthetic_5min_fallback(symbol, target_date_str)

        df_5m = df_5m.reset_index()
        # Normalise datetime column
        if "Datetime" in df_5m.columns:
            df_5m["dt"] = pd.to_datetime(df_5m["Datetime"])
        elif "Date" in df_5m.columns:
            df_5m["dt"] = pd.to_datetime(df_5m["Date"])
        else:
            return _synthetic_5min_fallback(symbol, target_date_str)

        # Convert to IST (UTC+5:30)
        ist_offset = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        if df_5m["dt"].dt.tz is None:
            df_5m["dt"] = df_5m["dt"].dt.tz_localize("UTC")
        df_5m["dt"] = df_5m["dt"].dt.tz_convert(ist_offset)
        df_5m["date_str"] = df_5m["dt"].dt.strftime("%Y-%m-%d")
        df_5m["time_str"] = df_5m["dt"].dt.strftime("%H:%M")

        # Filter target date — market hours 09:15–15:30
        df_today = df_5m[
            (df_5m["date_str"] == target_date_str) &
            (df_5m["time_str"] >= "09:15") &
            (df_5m["time_str"] <= "15:25")
        ].copy()

        if len(df_today) < 10:
            # Not enough bars → fall back to synthetic
            return _synthetic_5min_fallback(symbol, target_date_str)

        candles_today = _df_to_candle_list(df_today, target_date_str)

        # Warmup: collect previous 14+ trading days
        all_dates = sorted(df_5m["date_str"].unique())
        try:
            today_idx = all_dates.index(target_date_str)
        except ValueError:
            today_idx = len(all_dates) - 1

        prior_dates = all_dates[max(0, today_idx - 20):today_idx]  # up to 20 prior trading days

        warmup_candles: List[Dict[str, Any]] = []
        opening_volumes: List[float] = []

        for d in prior_dates[-14:]:
            df_d = df_5m[
                (df_5m["date_str"] == d) &
                (df_5m["time_str"] >= "09:15") &
                (df_5m["time_str"] <= "15:25")
            ].copy()
            if len(df_d) >= 5:
                day_candles = _df_to_candle_list(df_d, d)
                warmup_candles.extend(day_candles)
                # First bar volume for ORB in-play baseline
                opening_volumes.append(float(df_d.iloc[0]["Volume"]) if not pd.isna(df_d.iloc[0]["Volume"]) else 0.0)

        avg_opening_volume = float(np.mean(opening_volumes)) if opening_volumes else 0.0

        data_banner = f"REAL 5-MINUTE DATA | {target_date_str} | {len(candles_today)} bars"
        return candles_today, warmup_candles, True, data_banner, avg_opening_volume

    except Exception as e:
        _ONLINE_FAILED = True
        return _synthetic_5min_fallback(symbol, target_date_str)


def _df_to_candle_list(df: "pd.DataFrame", date_str: str) -> List[Dict[str, Any]]:
    """Convert a filtered yfinance 5m DataFrame to our candle dict format."""
    candles = []
    base_dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    for _, row in df.iterrows():
        time_str = row["time_str"] if "time_str" in row else row["dt"].strftime("%H:%M")
        try:
            ts = datetime.datetime.combine(base_dt.date(), datetime.time(*map(int, time_str.split(":")))).replace(tzinfo=ist_tz)
            unix_ts = int(ts.timestamp())
        except Exception:
            unix_ts = int(base_dt.replace(tzinfo=ist_tz).timestamp())
        o = round(float(row["Open"]), 2)
        h = round(float(row["High"]), 2)
        l = round(float(row["Low"]), 2)
        c = round(float(row["Close"]), 2)
        v = int(row["Volume"]) if not pd.isna(row["Volume"]) else 0
        h = max(h, o, c)
        l = min(l, o, c)
        candles.append({
            "time": time_str,
            "time_str": time_str,
            "timestamp": unix_ts,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": max(0, v)
        })
    return candles


def _synthetic_5min_fallback(
    symbol: str,
    target_date_str: str
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], bool, str, float]:
    """
    B: Synthetic 5-min candles from daily OHLC when real data unavailable.
    Returns is_real=False and a warning banner.
    """
    ohlc, _, resolved = _get_mock_daily_ohlc(symbol, target_date_str)
    # Generate 1-min synthetic candles then resample to 5-min
    candles_1m = generate_intraday_candles(symbol, resolved, ohlc)
    candles_5m = _resample_1m_to_5m_candles(candles_1m, resolved)

    # Warmup: generate 14 prior synthetic days
    warmup_5m: List[Dict[str, Any]] = []
    opening_volumes: List[float] = []
    try:
        base_dt = datetime.datetime.strptime(resolved, "%Y-%m-%d")
    except Exception:
        base_dt = datetime.datetime.today()

    for days_back in range(14, 0, -1):
        prior_dt = base_dt - datetime.timedelta(days=days_back)
        prior_str = prior_dt.strftime("%Y-%m-%d")
        prior_ohlc, _, _ = _get_mock_daily_ohlc(symbol, prior_str)
        prior_1m = generate_intraday_candles(symbol, prior_str, prior_ohlc)
        prior_5m = _resample_1m_to_5m_candles(prior_1m, prior_str)
        warmup_5m.extend(prior_5m)
        if prior_5m:
            opening_volumes.append(float(prior_5m[0]["volume"]))

    avg_opening_volume = float(np.mean(opening_volumes)) if opening_volumes else 0.0
    banner = "SYNTHETIC DATA: not valid for judging strategy quality"
    return candles_5m, warmup_5m, False, banner, avg_opening_volume


def _resample_1m_to_5m_candles(candles_1m: List[Dict[str, Any]], date_str: str) -> List[Dict[str, Any]]:
    """Resample 1-minute candles to 5-minute OHLCV candles."""
    result = []
    ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    try:
        base_dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        base_dt = datetime.datetime.today()

    for i in range(0, len(candles_1m), 5):
        chunk = candles_1m[i:i+5]
        if not chunk:
            continue
        bar_open = chunk[0]["open"]
        bar_close = chunk[-1]["close"]
        bar_high = max(c["high"] for c in chunk)
        bar_low = min(c["low"] for c in chunk)
        bar_vol = sum(c.get("volume", 0) for c in chunk)
        bar_time = chunk[-1]["time"]  # closing time of this 5m bar
        open_time = chunk[0]["time"]
        try:
            bar_dt = datetime.datetime.combine(base_dt.date(), datetime.time(*map(int, open_time.split(":")))).replace(tzinfo=ist_tz)
            unix_ts = int(bar_dt.timestamp())
        except Exception:
            unix_ts = 1700000000 + (i // 5) * 300
        result.append({
            "time": bar_time,
            "time_str": bar_time,
            "timestamp": unix_ts,
            "open": bar_open,
            "high": bar_high,
            "low": bar_low,
            "close": bar_close,
            "volume": bar_vol
        })
    return result


def generate_intraday_candles(symbol: str, date_str: str, ohlc: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Generates exactly 375 1-minute candles from 09:15 to 15:30.
    Seed = symbol + date.
    - Starts at Open, ends at Close
    - Touches High and Low exactly
    - Brownian-bridge path strictly clipped to [Low, High]
    - Wicks inside [Low, High]
    - U-shaped volume summing exactly to day's volume
    """
    O = float(ohlc["open"])
    H = float(ohlc["high"])
    L = float(ohlc["low"])
    C = float(ohlc["close"])
    total_vol = int(ohlc["volume"])

    N = TOTAL_DAY_CANDLES # 375
    seed = get_seed_from_str(f"{symbol}_{date_str}")
    rng = np.random.RandomState(seed)

    # 1. Pick timestamps for exact High and Low extremes
    # Distribute them realistically (e.g. one morning, one afternoon or vice-versa)
    if C >= O:
        # Bullish day: low usually earlier, high later
        t_low = rng.randint(20, 160)
        t_high = rng.randint(200, 360)
    else:
        # Bearish day: high earlier, low later
        t_high = rng.randint(20, 160)
        t_low = rng.randint(200, 360)

    # Key checkpoints: (index, target_price)
    checkpoints = sorted([
        (0, O),
        (t_low, L),
        (t_high, H),
        (N - 1, C)
    ], key=lambda x: x[0])

    # 2. Connect checkpoints using piecewise Brownian bridges
    closes = np.zeros(N)
    for k in range(len(checkpoints) - 1):
        i_start, p_start = checkpoints[k]
        i_end, p_end = checkpoints[k + 1]
        length = i_end - i_start

        # Standard brownian bridge
        dt = 1.0 / length
        dW = rng.normal(0, np.sqrt(dt), length)
        W = np.concatenate(([0], np.cumsum(dW)))
        # Bridge formula
        bridge = W - (np.arange(length + 1) / float(length)) * W[-1]

        # Scale bridge volatility relative to price range
        vol_scale = (H - L) * 0.25 * rng.uniform(0.6, 1.2)
        segment = p_start + (np.arange(length + 1) / float(length)) * (p_end - p_start) + bridge * vol_scale

        # Clip strictly to [L, H]
        segment = np.clip(segment, L, H)
        # Ensure exact checkpoints
        segment[0] = p_start
        segment[-1] = p_end

        closes[i_start : i_end + 1] = segment

    # Strictly guarantee exact touchpoints
    closes[0] = O
    closes[N - 1] = C
    closes[t_low] = L
    closes[t_high] = H
    closes = np.clip(closes, L, H)

    # 3. U-shaped Volume distribution
    # Higher at open (09:15) and close (15:30), lower at lunch (midday)
    t_norm = np.linspace(-1.0, 1.0, N)
    u_weights = 1.0 + 3.0 * (t_norm ** 2) + rng.uniform(0, 0.4, N)
    u_weights = np.maximum(0.1, u_weights)
    vols = np.round((u_weights / np.sum(u_weights)) * total_vol).astype(int)
    # Adjust last bar so sum is exact
    vols[-1] += total_vol - np.sum(vols)

    # 4. Construct 1-minute OHLC candles
    candles = []
    base_time = datetime.datetime.strptime(f"{date_str} 09:15", "%Y-%m-%d %H:%M")

    for i in range(N):
        curr_time = base_time + datetime.timedelta(minutes=i)
        time_str = curr_time.strftime("%H:%M")

        c_open = O if i == 0 else candles[i - 1]["close"]
        c_close = round(float(closes[i]), 2)

        # Intra-candle noise for High and Low
        wick_range = abs(c_close - c_open) + (H - L) * 0.015 * rng.uniform(0.2, 1.0)
        c_high = round(max(c_open, c_close) + rng.uniform(0, wick_range * 0.5), 2)
        c_low = round(min(c_open, c_close) - rng.uniform(0, wick_range * 0.5), 2)

        # Strict boundary clamping
        c_high = min(H, max(c_high, c_open, c_close))
        c_low = max(L, min(c_low, c_open, c_close))

        if i == t_high:
            c_high = H
        if i == t_low:
            c_low = L

        candles.append({
            "index": i,
            "time": time_str,
            "time_str": time_str,
            "timestamp": int(curr_time.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=5, minutes=30))).timestamp()),
            "open": c_open,
            "high": c_high,
            "low": c_low,
            "close": c_close,
            "volume": int(max(10, vols[i]))
        })

    return candles

def generate_fake_prior_day_candles(symbol: str, date_str: str, prev_close: float) -> List[Dict[str, Any]]:
    """
    Generates 375 1-minute candles for the prior day ending exactly at prev_close.
    Ensures indicators (EMA9, EMA21, RSI14, ATR14, VWAP) are warm and fully valid at 09:30.
    """
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        prior_date_str = (dt - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    except Exception:
        prior_date_str = "2026-11-05"

    seed = get_seed_from_str(f"{symbol}_{date_str}_prior")
    rng = np.random.RandomState(seed)

    prior_open = round(prev_close * rng.uniform(0.99, 1.01), 2)
    prior_high = round(max(prior_open, prev_close) * rng.uniform(1.005, 1.015), 2)
    prior_low = round(min(prior_open, prev_close) * rng.uniform(0.985, 0.995), 2)

    prior_ohlc = {
        "open": prior_open,
        "high": prior_high,
        "low": prior_low,
        "close": prev_close,
        "volume": 2000000
    }

    # Generate 375 candles with prior date string
    candles = generate_intraday_candles(symbol, prior_date_str, prior_ohlc)
    return candles
