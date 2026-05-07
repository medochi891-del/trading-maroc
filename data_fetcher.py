"""
=====================================================
 data_fetcher.py
 Sources de données :
   - Yahoo Finance  → Historique OHLCV (60 jours)
   - casablancabourse.com → Prix en temps réel
=====================================================
"""

import yfinance as yf
import requests
import re
import pandas as pd
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

TICKER_YAHOO = "IAM.PA"   # Maroc Telecom sur Yahoo Finance
TICKER_CSE   = "IAM"      # Maroc Telecom sur casablancabourse.com


def get_historical_ohlcv(period="3mo"):
    """
    Récupère l'historique OHLCV depuis Yahoo Finance.
    Retourne un DataFrame avec colonnes : Open, High, Low, Close, Volume
    """
    try:
        ticker = yf.Ticker(TICKER_YAHOO)
        df = ticker.history(period=period)
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        if len(df) < 30:
            print(f"⚠️  Historique insuffisant : {len(df)} jours")
            return None
        print(f"✅ Historique chargé : {len(df)} jours (Yahoo Finance)")
        return df
    except Exception as e:
        print(f"❌ Erreur Yahoo Finance : {e}")
        return None


def get_live_price():
    """
    Récupère le prix en temps réel depuis casablancabourse.com.
    Fallback sur Yahoo Finance si le site est inaccessible.
    """
    # ── Tentative 1 : casablancabourse.com ──
    try:
        url = f"https://www.casablancabourse.com/{TICKER_CSE}/action/capitalisation/"
        r = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        prices = re.findall(r"(\d{2,5}(?:[.,]\d{1,2})?)\s*(?:DH|MAD)", text)
        if prices:
            price = float(prices[0].replace(",", "."))
            print(f"✅ Prix en direct : {price:.2f} MAD (casablancabourse.com)")
            return price
    except Exception as e:
        print(f"⚠️  casablancabourse.com inaccessible : {e}")

    # ── Fallback : Yahoo Finance ──
    try:
        ticker = yf.Ticker(TICKER_YAHOO)
        info  = ticker.fast_info
        price = float(info.last_price)
        print(f"✅ Prix en direct : {price:.2f} MAD (Yahoo Finance - fallback)")
        return price
    except Exception as e:
        print(f"❌ Fallback Yahoo échoué : {e}")
        return None


def get_current_ohlc():
    """
    Retourne le dernier chandelier OHLC du jour depuis Yahoo Finance.
    """
    try:
        ticker = yf.Ticker(TICKER_YAHOO)
        df = ticker.history(period="5d", interval="1d")
        if df.empty:
            return None
        last = df.iloc[-1]
        return {
            "open":   float(last["Open"]),
            "high":   float(last["High"]),
            "low":    float(last["Low"]),
            "close":  float(last["Close"]),
            "volume": float(last["Volume"]),
        }
    except Exception as e:
        print(f"❌ Erreur OHLC du jour : {e}")
        return None
