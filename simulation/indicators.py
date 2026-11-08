import numpy as np
import pandas as pd
from typing import List, Dict, Any

def resample_to_5min(candles_1m: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Converts 1-minute candles to 5-minute bars.
    Returns DataFrame with columns: open, high, low, close, volume, time.
    """
    if not candles_1m:
        return pd.DataFrame()

    bars_5m = []
    # Group in chunks of 5
    for i in range(0, len(candles_1m), 5):
        chunk = candles_1m[i : i + 5]
        if not chunk:
            continue
        bar_open = chunk[0]["open"]
        bar_close = chunk[-1]["close"]
        bar_high = max(c["high"] for c in chunk)
        bar_low = min(c["low"] for c in chunk)
        bar_vol = sum(c["volume"] for c in chunk)
        bar_time = chunk[-1]["time"]
        
        bars_5m.append({
            "time": bar_time,
            "open": bar_open,
            "high": bar_high,
            "low": bar_low,
            "close": bar_close,
            "volume": bar_vol
        })
        
    return pd.DataFrame(bars_5m)


def compute_vwap_sigma_from_series(df_curr_5m: pd.DataFrame, vwap_series: pd.Series) -> float:
    """
    D: Compute sigma = std(close - VWAP) over all bars so far today.
    Requires >= 3 bars for a meaningful value.
    """
    if len(df_curr_5m) < 3:
        return 0.0
    deviations = df_curr_5m["close"].values - vwap_series.values
    return float(np.std(deviations, ddof=1)) if len(deviations) >= 2 else 0.0


def compute_adx(df: pd.DataFrame, period: int = 14) -> float:
    """
    E: ADX14 on the given OHLC DataFrame. Returns the latest ADX value.
    Uses Wilder's smoothing (same as standard ADX). Safe for any bar count.
    """
    n = len(df)
    if n < period + 1:
        return 0.0

    highs = df["high"].values.astype(float)
    lows = df["low"].values.astype(float)
    closes = df["close"].values.astype(float)

    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    tr = np.zeros(n)

    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm[i] = up if (up > down and up > 0) else 0.0
        minus_dm[i] = down if (down > up and down > 0) else 0.0
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )

    # Wilder smoothing with safe zero handling
    def wilder_smooth(arr, p):
        s = np.zeros(n)
        if n > p:
            s[p] = np.sum(arr[1:p + 1])
            for i in range(p + 1, n):
                s[i] = s[i - 1] - (s[i - 1] / p) + arr[i]
        return s

    atr_s = wilder_smooth(tr, period)
    pdm_s = wilder_smooth(plus_dm, period)
    mdm_s = wilder_smooth(minus_dm, period)

    with np.errstate(divide='ignore', invalid='ignore'):
        pdi = np.where(atr_s > 0, 100.0 * pdm_s / (atr_s + 1e-9), 0.0)
        mdi = np.where(atr_s > 0, 100.0 * mdm_s / (atr_s + 1e-9), 0.0)
        sum_di = pdi + mdi
        dx = np.where(sum_di > 0, 100.0 * np.abs(pdi - mdi) / (sum_di + 1e-9), 0.0)
        dx = np.nan_to_num(dx)

    if n <= period:
        return 0.0
    if n <= 2 * period:
        # If between period and 2*period, take mean of dx
        valid_dx = dx[period:]
        return float(np.mean(valid_dx)) if len(valid_dx) > 0 else 0.0

    adx_s = np.zeros(n)
    adx_s[2 * period] = np.mean(dx[period : 2 * period + 1])
    for i in range(2 * period + 1, n):
        adx_s[i] = (adx_s[i - 1] * (period - 1) + dx[i]) / period

    return float(np.nan_to_num(adx_s[-1]))


def compute_indicators(prior_day_1m: List[Dict[str, Any]], current_day_1m: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes EMA9, EMA21, RSI14, ATR14, VWAP (resets daily), Bollinger %B,
    VWAP sigma, and ADX14 on closed 5-minute bars.
    Returns the latest indicator values and historical series for decision rules.
    If current_day_1m already contains 5-min bars (from real data fetch), it is
    used directly without resampling.
    """
    # Auto-detect: if input has fewer than 376 bars it's already 5m bars
    if prior_day_1m and len(prior_day_1m) <= 80:
        # Already 5m bars — treat as-is
        df_prior_5m = _candle_list_to_df(prior_day_1m)
    else:
        df_prior_5m = resample_to_5min(prior_day_1m)

    if current_day_1m and len(current_day_1m) <= 80:
        df_curr_5m = _candle_list_to_df(current_day_1m)
    else:
        df_curr_5m = resample_to_5min(current_day_1m)
    
    if df_curr_5m.empty:
        return {}

    n_prior = len(df_prior_5m)
    df_all = pd.concat([df_prior_5m, df_curr_5m], ignore_index=True)
    
    closes = df_all["close"]
    highs = df_all["high"]
    lows = df_all["low"]
    vols = df_all["volume"]

    # EMA 9 & EMA 21
    ema9_series = closes.ewm(span=9, adjust=False).mean()
    ema21_series = closes.ewm(span=21, adjust=False).mean()

    # RSI 14
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    rsi_series = 100.0 - (100.0 / (1.0 + rs))

    # ATR 14
    prev_close = closes.shift(1).fillna(closes.iloc[0])
    tr1 = highs - lows
    tr2 = (highs - prev_close).abs()
    tr3 = (lows - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_series = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

    # Bollinger Bands & %B (20 periods, 2 std)
    sma20 = closes.rolling(window=20, min_periods=15).mean()
    std20 = closes.rolling(window=20, min_periods=15).std()
    upper_band = sma20 + 2.0 * std20
    lower_band = sma20 - 2.0 * std20
    band_width = upper_band - lower_band
    pct_b_series = (closes - lower_band) / (band_width + 1e-9)

    # VWAP: Resets daily! Calculated strictly on current day's candles
    curr_tp = (df_curr_5m["high"] + df_curr_5m["low"] + df_curr_5m["close"]) / 3.0
    curr_cum_vol = df_curr_5m["volume"].cumsum()
    curr_cum_tp_vol = (curr_tp * df_curr_5m["volume"]).cumsum()
    curr_vwap_series = curr_cum_tp_vol / (curr_cum_vol + 1e-9)

    # Current bar values (at the end of current day)
    curr_idx = len(df_all) - 1
    curr_5m_idx = len(df_curr_5m) - 1
    
    current_price = float(closes.iloc[-1])
    ema9_val = float(ema9_series.iloc[-1])
    ema21_val = float(ema21_series.iloc[-1])
    rsi_val = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 50.0
    atr_val = float(atr_series.iloc[-1]) if not pd.isna(atr_series.iloc[-1]) else 5.0
    pct_b_val = float(pct_b_series.iloc[-1]) if not pd.isna(pct_b_series.iloc[-1]) else 0.5
    vwap_val = float(curr_vwap_series.iloc[-1])

    # Price 30 mins ago on 5m bars (6 bars ago)
    price_30m_ago = float(df_curr_5m["close"].iloc[-6]) if len(df_curr_5m) >= 6 else float(df_curr_5m["open"].iloc[0])

    # Consecutive closes below VWAP check
    closes_below_vwap = 0
    for k in range(min(5, len(df_curr_5m))):
        bar_k_close = float(df_curr_5m["close"].iloc[-(k + 1)])
        bar_k_vwap = float(curr_vwap_series.iloc[-(k + 1)])
        if bar_k_close < bar_k_vwap:
            closes_below_vwap += 1
        else:
            break

    # D: VWAP sigma
    vwap_sigma = compute_vwap_sigma_from_series(df_curr_5m, curr_vwap_series)

    # E: ADX14 computed on df_all (warmed up from prior day)
    adx_val = compute_adx(df_all, period=14)

    return {
        "price": current_price,
        "ema9": round(ema9_val, 2),
        "ema21": round(ema21_val, 2),
        "rsi": round(rsi_val, 1),
        "atr": round(atr_val, 2),
        "vwap": round(vwap_val, 2),
        "pct_b": round(pct_b_val, 3),
        "price_30m_ago": round(price_30m_ago, 2),
        "closes_below_vwap_count": closes_below_vwap,
        "bars_count": len(df_curr_5m),
        "vwap_sigma": round(vwap_sigma, 4),
        "adx": round(adx_val, 2),
        # Expose DataFrames for ORB/regime use (not serialized to JSON)
        "_df_curr_5m": df_curr_5m,
        "_vwap_series": curr_vwap_series,
    }


def _candle_list_to_df(candles: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert a list of candle dicts to a DataFrame with standard columns."""
    if not candles:
        return pd.DataFrame()
    rows = []
    for c in candles:
        rows.append({
            "time": c.get("time", ""),
            "open": float(c.get("open", 0)),
            "high": float(c.get("high", 0)),
            "low": float(c.get("low", 0)),
            "close": float(c.get("close", 0)),
            "volume": float(c.get("volume", 0)),
        })
    return pd.DataFrame(rows)
