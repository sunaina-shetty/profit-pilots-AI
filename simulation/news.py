import os
import re
import json
import time
import datetime
from email.utils import parsedate_to_datetime
from typing import List, Dict, Any, Tuple, Optional
import requests
import feedparser
from simulation.llm import call_llm
from simulation.config import POPULAR_NSE_STOCKS, DEFAULT_CONFIG

# Financial keyword lexicon for deterministic fallback scoring
POSITIVE_WORDS = {
    "profit": 0.7, "growth": 0.6, "surge": 0.8, "rally": 0.7, "gain": 0.5,
    "beat": 0.75, "record": 0.8, "bullish": 0.8, "upgrade": 0.8, "dividend": 0.6,
    "order": 0.5, "win": 0.6, "expansion": 0.6, "buyback": 0.8, "partnership": 0.6
}
NEGATIVE_WORDS = {
    "loss": -0.8, "fall": -0.5, "drop": -0.6, "plunge": -0.85, "slump": -0.75,
    "miss": -0.7, "cut": -0.6, "bearish": -0.8, "downgrade": -0.8, "probe": -0.85,
    "fraud": -0.95, "penalty": -0.75, "fine": -0.7, "delay": -0.6, "concern": -0.5
}
CRITICAL_EVENT_KEYWORDS = [
    "fraud", "probe", "investigation", "sebi", "cbi", "raid", "ceo resigns",
    "scam", "default", "bankruptcy", "insolvency", "penalty", "arrest"
]

HIGH_VOLATILITY_KEYWORDS = [
    "earnings", "results", "q1", "q2", "q3", "q4", "merger", "acquisition",
    "budget", "rbi", "rate hike", "fed", "election", "guidance"
]

def get_company_name(symbol: str) -> str:
    for item in POPULAR_NSE_STOCKS:
        if item["symbol"] == symbol or item["symbol"].replace(".NS", "") == symbol.replace(".NS", ""):
            return item["name"]
    return symbol.replace(".NS", "")

_MC_CACHE: Dict[Tuple[str, Optional[str]], List[Dict[str, Any]]] = {}
_RSS_CACHE: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
_HEADLINE_SCORE_CACHE: Dict[str, float] = {}

def fetch_moneycontrol_news(symbol: str, target_date_str: str = None) -> List[Dict[str, Any]]:
    """
    Fetches real-time headlines directly from Moneycontrol RSS and news feeds.
    Prioritizes company-specific news and breaking market headlines.
    """
    cache_key = (symbol, target_date_str)
    if cache_key in _MC_CACHE:
        return _MC_CACHE[cache_key]

    if os.getenv("OFFLINE", "0") == "1":
        return []

    company_name = get_company_name(symbol)
    clean_sym = symbol.replace(".NS", "").replace(".BO", "").upper()
    keywords = [clean_sym.lower(), company_name.lower()]
    # Common short abbreviations
    if "hdfc" in clean_sym.lower():
        keywords.append("hdfc")
    elif "tcs" in clean_sym.lower():
        keywords.append("tcs")
        keywords.append("tata consultancy")
    elif "reliance" in clean_sym.lower():
        keywords.append("reliance")
        keywords.append("ril")
    elif "infy" in clean_sym.lower():
        keywords.append("infosys")

    urls = [
        "https://www.moneycontrol.com/rss/latestnews.xml",
        "https://www.moneycontrol.com/rss/business.xml",
        "https://www.moneycontrol.com/rss/marketreports.xml",
        "https://www.moneycontrol.com/rss/MCtopnews.xml"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    headlines = []
    seen_titles = set()
    ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    now_ist = datetime.datetime.now(ist_tz)

    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.content)
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                if not title or title in seen_titles:
                    continue

                title_lower = title.lower()
                summary = entry.get("summary", "").strip()
                summary_lower = summary.lower()

                # Check relevance: matches company keyword, or is a breaking market headline
                is_relevant = any(k in title_lower or k in summary_lower for k in keywords)
                is_breaking_market = any(k in title_lower for k in ["nifty", "sensex", "market", "rbi", "sebi"])

                if not (is_relevant or is_breaking_market):
                    continue

                published_str = entry.get("published", "")
                try:
                    pub_dt = parsedate_to_datetime(published_str)
                    pub_ist = pub_dt.astimezone(ist_tz)
                except Exception:
                    pub_ist = now_ist

                seen_titles.add(title)
                headlines.append({
                    "title": title,
                    "summary": summary[:200] if summary else "",
                    "source": "Moneycontrol",
                    "link": entry.get("link", ""),
                    "published_ist": pub_ist,
                    "published_iso": pub_ist.isoformat(),
                    "time_str": pub_ist.strftime("%H:%M"),
                    "is_company_specific": is_relevant
                })
        except Exception:
            continue

    # Fallback: if no specific Moneycontrol RSS item matched, fetch via Google RSS with Moneycontrol source
    if not any(h.get("is_company_specific") for h in headlines):
        try:
            mc_query = f"{company_name}+site:moneycontrol.com"
            fallback_url = f"https://news.google.com/rss/search?q={requests.utils.quote(mc_query)}&hl=en-IN&gl=IN&ceid=IN:en"
            resp = requests.get(fallback_url, headers=headers, timeout=5)
            if resp.status_code == 200:
                feed = feedparser.parse(resp.content)
                for entry in feed.entries[:8]:
                    title = entry.get("title", "").strip()
                    if title and title not in seen_titles:
                        seen_titles.add(title)
                        pub_str = entry.get("published", "")
                        try:
                            pub_dt = parsedate_to_datetime(pub_str).astimezone(ist_tz)
                        except Exception:
                            pub_dt = now_ist
                        headlines.append({
                            "title": title,
                            "summary": "",
                            "source": "Moneycontrol (via feed)",
                            "link": entry.get("link", ""),
                            "published_ist": pub_dt,
                            "published_iso": pub_dt.isoformat(),
                            "time_str": pub_dt.strftime("%H:%M"),
                            "is_company_specific": True
                        })
        except Exception:
            pass

    _MC_CACHE[cache_key] = headlines
    return headlines


def fetch_rss_headlines(symbol: str, target_date_str: str) -> List[Dict[str, Any]]:
    """
    Fetches headlines from Google News RSS.
    Converts published times to IST datetime.
    """
    cache_key = (symbol, target_date_str)
    if cache_key in _RSS_CACHE:
        return _RSS_CACHE[cache_key]

    if os.getenv("OFFLINE", "0") == "1":
        return []

    company_name = get_company_name(symbol)
    
    try:
        dt = datetime.datetime.strptime(target_date_str, "%Y-%m-%d")
    except Exception:
        dt = datetime.datetime.now()
        
    day_minus_1 = (dt - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    day_plus_1 = (dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    url = (
        f"https://news.google.com/rss/search?"
        f"q={requests.utils.quote(company_name)}+share+after:{day_minus_1}+before:{day_plus_1}"
        f"&hl=en-IN&gl=IN&ceid=IN:en"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code != 200:
            return []
        
        feed = feedparser.parse(resp.content)
        headlines = []
        ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            published_str = entry.get("published", "")
            if not title or not published_str:
                continue

            try:
                pub_dt = parsedate_to_datetime(published_str)
                pub_ist = pub_dt.astimezone(ist_tz)
            except Exception:
                pub_ist = datetime.datetime(dt.year, dt.month, dt.day, 9, 0, tzinfo=ist_tz)

            headlines.append({
                "title": title,
                "published_ist": pub_ist,
                "published_iso": pub_ist.isoformat(),
                "time_str": pub_ist.strftime("%H:%M")
            })

        _RSS_CACHE[cache_key] = headlines
        return headlines
    except Exception:
        return []

def keyword_score_headline(text: str) -> float:
    """Fallback sentiment score based on financial lexicon (-1.0 to 1.0)."""
    text_lower = text.lower()
    score = 0.0
    matches = 0
    
    for word, weight in POSITIVE_WORDS.items():
        if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
            score += weight
            matches += 1
            
    for word, weight in NEGATIVE_WORDS.items():
        if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
            score += weight
            matches += 1
            
    if matches > 0:
        return max(-1.0, min(1.0, score / matches))
    return 0.0

def score_headlines_batch(headlines: List[Dict[str, Any]]) -> List[float]:
    if not headlines:
        return []

    # Fast path: check score cache for each headline
    for h in headlines:
        title = h["title"]
        if title not in _HEADLINE_SCORE_CACHE:
            _HEADLINE_SCORE_CACHE[title] = keyword_score_headline(title)

    return [_HEADLINE_SCORE_CACHE[h["title"]] for h in headlines]

def evaluate_news_agent(
    all_headlines: List[Dict[str, Any]],
    simulated_ist_dt: datetime.datetime,
    default_yes: bool = False
) -> Dict[str, Any]:
    """
    Agent 2 — Moneycontrol News Sentiment Agent.
    - If default_yes=True: Defaults to YES (BUY / approve), monitoring feeds continuously.
      If sudden negative or critical news is received -> flips to HOLD or SELL immediately.
    - If default_yes=False: Standard deterministic score evaluation for test backward compatibility.
    """
    visible_headlines = []
    for h in all_headlines:
        pub_dt = h["published_ist"]
        if pub_dt.tzinfo is None:
            ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
            pub_dt = pub_dt.replace(tzinfo=ist_tz)
        if simulated_ist_dt.tzinfo is None:
            ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
            sim_dt = simulated_ist_dt.replace(tzinfo=ist_tz)
        else:
            sim_dt = simulated_ist_dt

        if pub_dt <= sim_dt:
            age_min = max(1.0, (sim_dt - pub_dt).total_seconds() / 60.0)
            item = dict(h)
            item["age_minutes"] = age_min
            visible_headlines.append(item)

    if not visible_headlines:
        if default_yes:
            return {
                "score": 0.50,
                "confidence": 65.0,
                "signal": "BUY",
                "classification": "MONEYCONTROL: DEFAULT YES",
                "reason": "Moneycontrol: Default YES (Monitoring live feeds for sudden adverse events)",
                "status": "YES",
                "veto_buy": False,
                "veto_short": False,
                "headlines": [],
                "facts": {
                    "headlines_count": 0,
                    "net_sentiment": 0.50,
                    "score": 0.50,
                    "classification": "MONEYCONTROL: DEFAULT YES",
                    "veto_buy": False,
                    "veto_short": False,
                    "default_yes_active": True
                }
            }

        return {
            "score": 0.0,
            "confidence": 0.0,
            "signal": "HOLD",
            "classification": "INSUFFICIENT DATA",
            "reason": "No news: No fresh news published prior to this candle",
            "veto_buy": False,
            "veto_short": False,
            "headlines": [],
            "facts": {
                "headlines_count": 0,
                "net_sentiment": 0.0,
                "score": 0.0,
                "classification": "INSUFFICIENT DATA",
                "veto_buy": False,
                "veto_short": False
            }
        }

    scores = score_headlines_batch(visible_headlines)
    
    net_sentiment = 0.0
    has_critical_event = False
    has_high_volatility = False

    enriched_headlines = []
    for idx, item in enumerate(visible_headlines):
        sentiment = scores[idx]
        age_min = item["age_minutes"]
        decay = 0.5 ** (age_min / 120.0)
        net_sentiment += sentiment * decay

        title_lower = item["title"].lower()
        is_crit = any(kw in title_lower for kw in CRITICAL_EVENT_KEYWORDS)
        is_high_vol = any(kw in title_lower for kw in HIGH_VOLATILITY_KEYWORDS)
        if is_crit:
            has_critical_event = True
        if is_high_vol:
            has_high_volatility = True

        h_class = "CRITICAL EVENT" if is_crit else ("POSITIVE" if sentiment > 0.2 else ("NEGATIVE" if sentiment < -0.2 else "NEUTRAL"))
        enriched_headlines.append({
            "title": item["title"],
            "published_iso": item.get("published_iso", ""),
            "time_str": item.get("time_str", "09:00"),
            "sentiment": round(sentiment, 2),
            "classification": h_class,
            "age_minutes": round(age_min, 1)
        })

    # With fewer than 2 headlines cap net at 0.30
    if len(visible_headlines) < 2:
        net_sentiment = min(0.30, max(-0.30, net_sentiment))
    else:
        net_sentiment = max(-1.0, min(1.0, net_sentiment / max(1.0, len(visible_headlines) ** 0.5)))

    net_sentiment = round(net_sentiment, 3)
    score = net_sentiment

    # Classification
    if has_critical_event:
        classification = "CRITICAL EVENT"
    elif score >= 0.30:
        classification = "POSITIVE"
    elif score <= -0.30:
        classification = "NEGATIVE"
    elif has_high_volatility:
        classification = "HIGH VOLATILITY"
    else:
        classification = "NEUTRAL"

    veto_buy = (score < DEFAULT_CONFIG.news_buy_veto_threshold) or has_critical_event
    veto_short = (score > DEFAULT_CONFIG.news_short_veto_threshold)

    conf = min(100.0, round(max(30.0, 40.0 + abs(score) * 55.0), 1))

    # Detect sudden news shock (recent high-impact headline)
    has_negative_keyword = lambda text: any(kw in text.lower() for kw in ["drop", "loss", "plunge", "slump", "fall", "cut", "delay", "probe", "fine", "penalty", "miss", "downgrade", "fraud", "scam", "decline"])
    sudden_critical = [
        h for h in enriched_headlines
        if h["age_minutes"] <= 120 and (h["sentiment"] <= -0.70 or h["classification"] == "CRITICAL EVENT")
    ]
    sudden_adverse = [
        h for h in enriched_headlines
        if h["age_minutes"] <= 120 and (h["sentiment"] < 0.0 or has_negative_keyword(h["title"]))
    ]

    if has_critical_event or (sudden_critical and default_yes):
        sig = "SELL"
        culprit = sudden_critical[0]["title"] if sudden_critical else "Critical Event"
        reason = f"Moneycontrol ALERT: Sudden adverse shock '{culprit[:60]}...' -> SELL / Emergency Square-Off"
        veto_buy = True
    elif default_yes and sudden_adverse:
        sig = "HOLD"
        culprit = sudden_adverse[0]["title"]
        reason = f"Moneycontrol ALERT: Sudden negative news '{culprit[:60]}...' -> HOLD (Veto Buy)"
        veto_buy = True
    elif score >= 0.35:
        sig = "BUY"
        reason = f"Bullish news momentum (net sentiment {score:+.2f} across {len(visible_headlines)} headlines)"
    elif score <= -0.35:
        sig = "SELL"
        reason = f"Bearish news risk (net sentiment {score:+.2f} across {len(visible_headlines)} headlines)"
    elif default_yes and not veto_buy:
        # User requirement: default it should be YES if it receives any sudden news it should be hold/sell
        sig = "BUY"
        reason = f"Moneycontrol: YES (Default Active • Net sentiment {score:+.2f} across {len(visible_headlines)} headlines, no sudden adverse shocks)"
    else:
        sig = "HOLD"
        reason = f"Neutral news environment (net sentiment {score:+.2f} across {len(visible_headlines)} headlines)"

    if veto_buy:
        reason += f" [VETO BUY: sentiment {score:+.2f} or Critical Event]"
    elif veto_short:
        reason += f" [VETO SHORT: sentiment {score:+.2f} > +0.50]"

    return {
        "status": "YES" if (default_yes and sig == "BUY") else sig,
        "score": score,
        "confidence": conf,
        "signal": sig,
        "classification": classification,
        "reason": reason,
        "veto_buy": veto_buy,
        "veto_short": veto_short,
        "headlines": enriched_headlines,
        "facts": {
            "headlines_count": len(visible_headlines),
            "net_sentiment": net_sentiment,
            "classification": classification,
            "score": score,
            "veto_buy": veto_buy,
            "veto_short": veto_short
        }
    }
