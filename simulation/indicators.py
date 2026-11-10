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

    plus_di_val = float(np.nan_to_num(pdi[-1])) if len(pdi) > 0 else 0.0
    minus_di_val = float(np.nan_to_num(mdi[-1])) if len(mdi) > 0 else 0.0

    if n <= period:
        return 0.0, plus_di_val, minus_di_val
    if n <= 2 * period:
        # If between period and 2*period, take mean of dx
        valid_dx = dx[period:]
        adx_val = float(np.mean(valid_dx)) if len(valid_dx) > 0 else 0.0
        return adx_val, plus_di_val, minus_di_val

    adx_s = np.zeros(n)
    adx_s[2 * period] = np.mean(dx[period : 2 * period + 1])
    for i in range(2 * period + 1, n):
        adx_s[i] = (adx_s[i - 1] * (period - 1) + dx[i]) / period

    return float(np.nan_to_num(adx_s[-1])), plus_di_val, minus_di_val


def compute_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
    """
    Computes Supertrend indicator on OHLC DataFrame.
    Returns: (latest_supertrend_price, direction [1 for Bullish, -1 for Bearish])
    """
    n = len(df)
    if n == 0:
        return 0.0, 1
    if n < period:
        mid = float((df["high"].iloc[-1] + df["low"].iloc[-1]) / 2.0)
        return mid, 1

    highs = df["high"].values.astype(float)
    lows = df["low"].values.astype(float)
    closes = df["close"].values.astype(float)

    # True Range
    tr = np.zeros(n)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))

    # ATR Wilder smoothing
    atr = np.zeros(n)
    if n >= period:
        atr[period - 1] = np.mean(tr[:period])
        for i in range(period, n):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period

    hl2 = (highs + lows) / 2.0
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)

    final_upper = np.zeros(n)
    final_lower = np.zeros(n)
    trend = np.zeros(n, dtype=int)
    supertrend = np.zeros(n)

    for i in range(n):
        if i == 0:
            final_upper[i] = basic_upper[i]
            final_lower[i] = basic_lower[i]
            trend[i] = 1
            supertrend[i] = final_lower[i]
        else:
            # Upper band
            if basic_upper[i] < final_upper[i - 1] or closes[i - 1] > final_upper[i - 1]:
                final_upper[i] = basic_upper[i]
            else:
                final_upper[i] = final_upper[i - 1]

            # Lower band
            if basic_lower[i] > final_lower[i - 1] or closes[i - 1] < final_lower[i - 1]:
                final_lower[i] = basic_lower[i]
            else:
                final_lower[i] = final_lower[i - 1]

            # Trend direction
            if supertrend[i - 1] == final_upper[i - 1]:
                if closes[i] > final_upper[i]:
                    trend[i] = 1
                    supertrend[i] = final_lower[i]
                else:
                    trend[i] = -1
                    supertrend[i] = final_upper[i]
            else:
                if closes[i] < final_lower[i]:
                    trend[i] = -1
                    supertrend[i] = final_upper[i]
                else:
                    trend[i] = 1
                    supertrend[i] = final_lower[i]

    return round(float(supertrend[-1]), 2), int(trend[-1])


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

    # EMA 50 & EMA 200
    ema50_series = closes.ewm(span=50, adjust=False).mean()
    ema200_series = closes.ewm(span=200, adjust=False).mean()

    # MACD (12, 26, 9)
    ema12_series = closes.ewm(span=12, adjust=False).mean()
    ema26_series = closes.ewm(span=26, adjust=False).mean()
    macd_series = ema12_series - ema26_series
    macd_sig_series = macd_series.ewm(span=9, adjust=False).mean()
    macd_hist_series = macd_series - macd_sig_series

    # Donchian Channel (20 periods)
    donchian_up_series = highs.rolling(window=20, min_periods=3).max()
    donchian_lo_series = lows.rolling(window=20, min_periods=3).min()
    donchian_mid_series = (donchian_up_series + donchian_lo_series) / 2.0

    # Stochastic Oscillator (14, 3, 3)
    stoch_low14 = lows.rolling(window=14, min_periods=3).min()
    stoch_high14 = highs.rolling(window=14, min_periods=3).max()
    stoch_denom = (stoch_high14 - stoch_low14).replace(0, 1e-9)
    fast_k_series = 100.0 * (closes - stoch_low14) / stoch_denom
    stoch_k_series = fast_k_series.rolling(window=3, min_periods=1).mean()
    stoch_d_series = stoch_k_series.rolling(window=3, min_periods=1).mean()

    # Volume 20 SMA
    vol_sma_series = vols.rolling(window=20, min_periods=1).mean()

    # Supertrend (10, 3)
    st_val, st_dir = compute_supertrend(df_all, period=10, multiplier=3.0)

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
    ema50_val = float(ema50_series.iloc[-1])
    ema200_val = float(ema200_series.iloc[-1])
    rsi_val = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 50.0
    atr_val = float(atr_series.iloc[-1]) if not pd.isna(atr_series.iloc[-1]) else 5.0
    pct_b_val = float(pct_b_series.iloc[-1]) if not pd.isna(pct_b_series.iloc[-1]) else 0.5
    bb_upper_val = float(upper_band.iloc[-1]) if not pd.isna(upper_band.iloc[-1]) else current_price * 1.01
    bb_lower_val = float(lower_band.iloc[-1]) if not pd.isna(lower_band.iloc[-1]) else current_price * 0.99
    bb_mid_val = float(sma20.iloc[-1]) if not pd.isna(sma20.iloc[-1]) else current_price
    vwap_val = float(curr_vwap_series.iloc[-1])

    macd_line_val = float(macd_series.iloc[-1])
    macd_signal_val = float(macd_sig_series.iloc[-1])
    macd_hist_val = float(macd_hist_series.iloc[-1])

    donchian_up_val = float(donchian_up_series.iloc[-1]) if not pd.isna(donchian_up_series.iloc[-1]) else current_price
    donchian_lo_val = float(donchian_lo_series.iloc[-1]) if not pd.isna(donchian_lo_series.iloc[-1]) else current_price
    donchian_mid_val = float(donchian_mid_series.iloc[-1]) if not pd.isna(donchian_mid_series.iloc[-1]) else current_price

    stoch_k_val = float(stoch_k_series.iloc[-1]) if not pd.isna(stoch_k_series.iloc[-1]) else 50.0
    stoch_d_val = float(stoch_d_series.iloc[-1]) if not pd.isna(stoch_d_series.iloc[-1]) else 50.0
    vol_sma_val = float(vol_sma_series.iloc[-1]) if not pd.isna(vol_sma_series.iloc[-1]) else 1000.0

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
    adx_res = compute_adx(df_all, period=14)
    if isinstance(adx_res, tuple):
        adx_val, pdi_val, mdi_val = adx_res
    else:
        adx_val = adx_res
        pdi_val, mdi_val = 0.0, 0.0

    return {
        "price": current_price,
        "ema9": round(ema9_val, 2),
        "ema21": round(ema21_val, 2),
        "ema50": round(ema50_val, 2),
        "ema200": round(ema200_val, 2),
        "rsi": round(rsi_val, 1),
        "atr": round(atr_val, 2),
        "vwap": round(vwap_val, 2),
        "pct_b": round(pct_b_val, 3),
        "bb_upper": round(bb_upper_val, 2),
        "bb_lower": round(bb_lower_val, 2),
        "bb_mid": round(bb_mid_val, 2),
        "supertrend": round(st_val, 2),
        "supertrend_dir": st_dir,
        "macd_line": round(macd_line_val, 2),
        "macd_signal": round(macd_signal_val, 2),
        "macd_hist": round(macd_hist_val, 2),
        "donchian_upper": round(donchian_up_val, 2),
        "donchian_lower": round(donchian_lo_val, 2),
        "donchian_mid": round(donchian_mid_val, 2),
        "stoch_k": round(stoch_k_val, 1),
        "stoch_d": round(stoch_d_val, 1),
        "volume_sma": round(vol_sma_val, 0),
        "price_30m_ago": round(price_30m_ago, 2),
        "closes_below_vwap_count": closes_below_vwap,
        "bars_count": len(df_curr_5m),
        "vwap_sigma": round(vwap_sigma, 4),
        "adx": round(adx_val, 2),
        "pdi": round(pdi_val, 2),
        "mdi": round(mdi_val, 2),
        # Expose DataFrames for ORB/regime use (not serialized to JSON)
        "_df_curr_5m": df_curr_5m,
        "_vwap_series": curr_vwap_series,
        "_closes_series": closes,
        "_rsi_series": rsi_series,
        "_ema9_series": ema9_series,
        "_ema21_series": ema21_series,
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


def enrich_candles_with_all_indicators(candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enriches all candles with indicators from all 10 trading strategies:
    EMA9, EMA21, EMA50, EMA200, VWAP, Bollinger Bands (Upper, Mid, Lower),
    Supertrend, Donchian Channels (High, Low), RSI 14, MACD, and Stochastic.
    """
    if not candles:
        return []

    try:
        df = pd.DataFrame(candles)
        closes = df["close"].astype(float)
        highs = df["high"].astype(float)
        lows = df["low"].astype(float)
        vols = df["volume"].astype(float)

        # 1. EMAs across multiple time windows (Strat 1, 2, 5, 10)
        df["ema9"] = closes.ewm(span=9, adjust=False).mean().round(2)
        df["ema21"] = closes.ewm(span=21, adjust=False).mean().round(2)
        df["ema50"] = closes.ewm(span=50, adjust=False).mean().round(2)
        df["ema200"] = closes.ewm(span=200, adjust=False).mean().round(2)

        # 2. Bollinger Bands (20, 2) (Strat 6)
        sma20 = closes.rolling(20, min_periods=1).mean()
        std20 = closes.rolling(20, min_periods=1).std().fillna(0)
        df["bb_upper"] = (sma20 + 2.0 * std20).round(2)
        df["bb_middle"] = sma20.round(2)
        df["bb_lower"] = (sma20 - 2.0 * std20).round(2)

        # 3. Donchian Channels 20 (Strat 9)
        df["donchian_high"] = highs.rolling(20, min_periods=1).max().round(2)
        df["donchian_low"] = lows.rolling(20, min_periods=1).min().round(2)

        # 4. RSI 14 (Strat 1, 5, 6, 8)
        delta = closes.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        ag = gain.ewm(alpha=1/14, min_periods=1).mean()
        al = loss.ewm(alpha=1/14, min_periods=1).mean()
        rs = ag / (al + 1e-9)
        df["rsi14"] = (100.0 - (100.0 / (1.0 + rs))).round(2)

        # 5. MACD (12, 26, 9) (Strat 5)
        ema12 = closes.ewm(span=12, adjust=False).mean()
        ema26 = closes.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        df["macd"] = macd.round(2)
        df["macd_signal"] = signal.round(2)
        df["macd_hist"] = (macd - signal).round(2)

        # 6. Stochastic Oscillator (14, 3) (Strat 10)
        l14 = lows.rolling(14, min_periods=1).min()
        h14 = highs.rolling(14, min_periods=1).max()
        k = 100.0 * (closes - l14) / (h14 - l14 + 1e-9)
        df["stoch_k"] = k.round(2)
        df["stoch_d"] = k.rolling(3, min_periods=1).mean().round(2)

        # 7. VWAP (Strat 3 & Council)
        typ = (highs + lows + closes) / 3.0
        cum_vp = (typ * vols).cumsum()
        cum_v = vols.cumsum()
        df["vwap"] = (cum_vp / np.maximum(1.0, cum_v)).round(2)

        # 8. Supertrend (Strat 2)
        tr1 = highs - lows
        tr2 = (highs - closes.shift(1).fillna(closes.iloc[0])).abs()
        tr3 = (lows - closes.shift(1).fillna(closes.iloc[0])).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(10, min_periods=1).mean()
        hl2 = (highs + lows) / 2.0
        df["supertrend"] = (hl2 - 2.0 * atr).round(2)

        # 9. ORB (Strat 4)
        orb_h = float(highs.iloc[:3].max()) if len(highs) >= 3 else float(highs.iloc[0])
        orb_l = float(lows.iloc[:3].min()) if len(lows) >= 3 else float(lows.iloc[0])
        df["orb_high"] = round(orb_h, 2)
        df["orb_low"] = round(orb_l, 2)

        # Replace NaN with safe defaults
        df = df.fillna(0.0)
        return df.to_dict(orient="records")
    except Exception:
        return candles
