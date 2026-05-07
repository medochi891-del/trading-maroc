"""
=====================================================
 indicators.py
 Indicateurs techniques – 100% issus du cours
 ─────────────────────────────────────────────
 1. RSI  (Relative Strength Index)
 2. Moyennes Mobiles  (SMA / EMA)
 3. MACD
 4. Bandes de Bollinger
 5. Chandeliers japonais  (Doji, Marteau, Englobante)
 6. Supports et Résistances
 7. Épaule-Tête-Épaule  (ETE / ETEI)
=====================================================
"""

import pandas as pd
import numpy as np


# ══════════════════════════════════════════════════
# 1. RSI  ← cours : "mesure la force du marché"
# ══════════════════════════════════════════════════
def calculate_rsi(close: pd.Series, period: int = 14) -> float:
    """
    RSI = 100 – (100 / (1 + G/P))
    G = moyenne des gains | P = moyenne des pertes
    """
    if len(close) < period + 1:
        return 50.0
    delta    = close.diff()
    gain     = delta.where(delta > 0, 0.0)
    loss     = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs       = avg_gain / avg_loss.replace(0, np.nan)
    rsi      = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0


# ══════════════════════════════════════════════════
# 2. Moyennes Mobiles  ← cours : SMA + EMA
# ══════════════════════════════════════════════════
def calculate_sma(close: pd.Series, period: int) -> float:
    """Moyenne Mobile Simple (SMA)"""
    if len(close) < period:
        return float(close.mean())
    return float(close.rolling(window=period).mean().iloc[-1])


def calculate_ema(close: pd.Series, period: int) -> float:
    """Moyenne Mobile Exponentielle (EMA) – plus réactive"""
    if len(close) < period:
        return float(close.mean())
    return float(close.ewm(span=period, adjust=False).mean().iloc[-1])


def signal_mm(close: pd.Series) -> dict:
    """
    Signal Moyennes Mobiles :
    Croisement haussier MM5 > MM10 → achat
    Croisement baissier MM5 < MM10 → vente
    """
    mm5      = calculate_sma(close, 5)
    mm10     = calculate_sma(close, 10)
    mm5_prev = float(close.rolling(5).mean().iloc[-2])  if len(close) >= 6  else mm5
    mm10_prev= float(close.rolling(10).mean().iloc[-2]) if len(close) >= 11 else mm10

    if mm5_prev <= mm10_prev and mm5 > mm10:
        signal = "ACHAT"
        detail = f"Croisement haussier MM5({mm5:.2f}) > MM10({mm10:.2f}) → signal d'achat"
    elif mm5_prev >= mm10_prev and mm5 < mm10:
        signal = "VENTE"
        detail = f"Croisement baissier MM5({mm5:.2f}) < MM10({mm10:.2f}) → signal de vente"
    elif mm5 > mm10:
        signal = "ACHAT"
        detail = f"MM5({mm5:.2f}) au-dessus de MM10({mm10:.2f}) → tendance haussière"
    else:
        signal = "NEUTRE"
        detail = f"MM5({mm5:.2f}) ≈ MM10({mm10:.2f}) → pas de signal clair"

    return {"signal": signal, "detail": detail, "mm5": mm5, "mm10": mm10}


# ══════════════════════════════════════════════════
# 3. MACD  ← cours : "indicateur de tendance et de momentum"
# ══════════════════════════════════════════════════
def calculate_macd(close: pd.Series) -> dict:
    """
    MACD = EMA(12) – EMA(26)
    Ligne signal = EMA(9) du MACD
    Signal d'achat  : MACD croise au-dessus de la ligne signal
    Signal de vente : MACD croise en dessous
    """
    if len(close) < 26:
        return {"signal": "NEUTRE", "detail": "Données insuffisantes pour MACD", "macd": 0, "signal_line": 0}

    ema12   = close.ewm(span=12, adjust=False).mean()
    ema26   = close.ewm(span=26, adjust=False).mean()
    macd    = ema12 - ema26
    sig_line= macd.ewm(span=9, adjust=False).mean()

    macd_val     = float(macd.iloc[-1])
    sig_val      = float(sig_line.iloc[-1])
    macd_prev    = float(macd.iloc[-2])
    sig_prev     = float(sig_line.iloc[-2])

    if macd_prev <= sig_prev and macd_val > sig_val:
        signal = "ACHAT"
        detail = f"MACD({macd_val:.3f}) croise au-dessus de la ligne signal({sig_val:.3f}) → signal d'achat"
    elif macd_prev >= sig_prev and macd_val < sig_val:
        signal = "VENTE"
        detail = f"MACD({macd_val:.3f}) croise en dessous de la ligne signal({sig_val:.3f}) → signal de vente"
    elif macd_val > sig_val:
        signal = "ACHAT"
        detail = f"MACD({macd_val:.3f}) au-dessus de la ligne signal → momentum haussier"
    else:
        signal = "NEUTRE"
        detail = f"MACD({macd_val:.3f}) ≈ ligne signal({sig_val:.3f}) → pas de signal clair"

    return {"signal": signal, "detail": detail, "macd": macd_val, "signal_line": sig_val}


# ══════════════════════════════════════════════════
# 4. Bandes de Bollinger  ← cours : "mesurer la volatilité"
# ══════════════════════════════════════════════════
def calculate_bollinger(close: pd.Series, period: int = 20) -> dict:
    """
    Bande centrale  = MM20
    Bande supérieure = MM20 + 2σ
    Bande inférieure = MM20 – 2σ
    Prix ≈ bande haute → surachat
    Prix ≈ bande basse → survente
    """
    if len(close) < period:
        return {"signal": "NEUTRE", "detail": "Données insuffisantes pour Bollinger",
                "upper": 0, "middle": 0, "lower": 0}

    mm20    = close.rolling(window=period).mean()
    std     = close.rolling(window=period).std()
    upper   = float((mm20 + 2 * std).iloc[-1])
    middle  = float(mm20.iloc[-1])
    lower   = float((mm20 - 2 * std).iloc[-1])
    price   = float(close.iloc[-1])
    band_width = upper - lower

    pct = (price - lower) / band_width if band_width > 0 else 0.5

    if pct >= 0.85:
        signal = "VENTE"
        detail = (f"Prix({price:.2f}) proche de la bande haute de Bollinger({upper:.2f}) "
                  f"→ zone de surachat → signal de vente")
    elif pct <= 0.15:
        signal = "ACHAT"
        detail = (f"Prix({price:.2f}) proche de la bande basse de Bollinger({lower:.2f}) "
                  f"→ zone de survente → signal d'achat")
    else:
        signal = "NEUTRE"
        detail = f"Prix({price:.2f}) en zone centrale de Bollinger → pas de signal"

    return {"signal": signal, "detail": detail,
            "upper": upper, "middle": middle, "lower": lower}


# ══════════════════════════════════════════════════
# 5. Chandeliers japonais  ← cours : Doji, Marteau, Englobante
# ══════════════════════════════════════════════════
def analyze_chandelier(ohlc_df: pd.DataFrame) -> dict:
    """
    Analyse les 2 derniers chandeliers pour détecter :
    - Doji          : indécision du marché
    - Marteau       : possible retournement à la hausse
    - Englobante    : signal fort de changement de tendance
    """
    if len(ohlc_df) < 2:
        return {"signal": "NEUTRE", "detail": "Données insuffisantes pour chandeliers",
                "pattern": "Aucun"}

    curr = ohlc_df.iloc[-1]
    prev = ohlc_df.iloc[-2]

    o, h, l, c = curr["Open"], curr["High"], curr["Low"], curr["Close"]
    po, ph, pl, pc = prev["Open"], prev["High"], prev["Low"], prev["Close"]

    body       = abs(c - o)
    total_range= h - l if h != l else 0.0001
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    # ── Doji : corps très petit ──
    if body / total_range < 0.1:
        return {"signal": "NEUTRE",
                "detail": "Doji détecté → indécision du marché",
                "pattern": "Doji"}

    # ── Marteau (Hammer) : longue mèche basse, corps en haut ──
    if (lower_wick >= 2 * body and upper_wick <= 0.3 * body and c > o):
        return {"signal": "ACHAT",
                "detail": "Marteau (Hammer) détecté → possible retournement à la hausse",
                "pattern": "Marteau"}

    # ── Englobante haussière ──
    if (pc < po and c > o and c > po and o < pc):
        return {"signal": "ACHAT",
                "detail": "Englobante haussière détectée → signal fort de changement de tendance à la hausse",
                "pattern": "Englobante haussière"}

    # ── Englobante baissière ──
    if (pc > po and c < o and c < po and o > pc):
        return {"signal": "VENTE",
                "detail": "Englobante baissière détectée → signal fort de changement de tendance à la baisse",
                "pattern": "Englobante baissière"}

    # ── Chandelier haussier standard ──
    if c > o:
        return {"signal": "ACHAT",
                "detail": f"Chandelier haussier : clôture({c:.2f}) > ouverture({o:.2f})",
                "pattern": "Haussier"}

    # ── Chandelier baissier standard ──
    return {"signal": "VENTE",
            "detail": f"Chandelier baissier : clôture({c:.2f}) < ouverture({o:.2f})",
            "pattern": "Baissier"}


# ══════════════════════════════════════════════════
# 6. Supports et Résistances  ← cours : "niveaux clés"
# ══════════════════════════════════════════════════
def calculate_supports_resistances(high: pd.Series, low: pd.Series, close: pd.Series) -> dict:
    """
    Support    : niveau où le prix arrête de baisser (min des 20 derniers jours)
    Résistance : niveau où le prix arrête de monter  (max des 20 derniers jours)
    """
    if len(close) < 20:
        return {"signal": "NEUTRE", "detail": "Données insuffisantes pour supports/résistances",
                "support": 0, "resistance": 0}

    support    = float(low.rolling(20).min().iloc[-1])
    resistance = float(high.rolling(20).max().iloc[-1])
    price      = float(close.iloc[-1])
    sr_range   = resistance - support

    pct = (price - support) / sr_range if sr_range > 0 else 0.5

    if pct <= 0.10:
        signal = "ACHAT"
        detail = (f"Prix({price:.2f}) proche du support({support:.2f}) "
                  f"→ zone d'achat, les acheteurs interviennent")
    elif pct >= 0.90:
        signal = "VENTE"
        detail = (f"Prix({price:.2f}) proche de la résistance({resistance:.2f}) "
                  f"→ zone de vente, les vendeurs interviennent")
    else:
        signal = "NEUTRE"
        detail = (f"Prix({price:.2f}) entre support({support:.2f}) "
                  f"et résistance({resistance:.2f}) → zone neutre")

    return {"signal": signal, "detail": detail,
            "support": support, "resistance": resistance}


# ══════════════════════════════════════════════════
# 7. Épaule-Tête-Épaule (ETE)  ← cours : "figure chartiste"
# ══════════════════════════════════════════════════
def detect_ete(close: pd.Series, high: pd.Series) -> dict:
    """
    Détecte la figure ETE (Épaule-Tête-Épaule) :
    - 3 sommets : gauche < tête > droite
    - Signal de retournement à la baisse si neckline cassée
    Détecte aussi ETEI (inversée) pour retournement à la hausse.
    """
    if len(close) < 30:
        return {"signal": "NEUTRE",
                "detail": "Données insuffisantes pour détecter une figure ETE (minimum 30 jours)",
                "pattern": "Aucun"}

    # Trouver les sommets locaux (fenêtre de 5 jours)
    h = high.values
    sommets = []
    for i in range(5, len(h) - 5):
        if h[i] == max(h[i-5:i+6]):
            sommets.append((i, h[i]))

    # Trouver les creux locaux
    l = close.values
    creux = []
    for i in range(5, len(l) - 5):
        if l[i] == min(l[i-5:i+6]):
            creux.append((i, l[i]))

    # ── Chercher ETE : 3 sommets avec tête plus haute ──
    if len(sommets) >= 3:
        s1, s2, s3 = sommets[-3], sommets[-2], sommets[-1]
        if s2[1] > s1[1] and s2[1] > s3[1] and abs(s1[1] - s3[1]) / s2[1] < 0.05:
            neckline = (s1[1] + s3[1]) / 2
            if float(close.iloc[-1]) < neckline:
                return {
                    "signal": "VENTE",
                    "detail": (f"Figure ETE détectée → Épaule G({s1[1]:.2f}), "
                               f"Tête({s2[1]:.2f}), Épaule D({s3[1]:.2f}). "
                               f"Neckline cassée à {neckline:.2f} → signal de retournement baissier"),
                    "pattern": "ETE"
                }

    # ── Chercher ETEI : 3 creux avec tête plus basse ──
    if len(creux) >= 3:
        c1, c2, c3 = creux[-3], creux[-2], creux[-1]
        if c2[1] < c1[1] and c2[1] < c3[1] and abs(c1[1] - c3[1]) / c2[1] < 0.05:
            neckline = (c1[1] + c3[1]) / 2
            if float(close.iloc[-1]) > neckline:
                return {
                    "signal": "ACHAT",
                    "detail": (f"Figure ETEI (inversée) détectée → signal de retournement haussier. "
                               f"Neckline franchie à {neckline:.2f}"),
                    "pattern": "ETEI"
                }

    return {"signal": "NEUTRE",
            "detail": "Aucune figure ETE/ETEI détectée actuellement",
            "pattern": "Aucun"}


# ══════════════════════════════════════════════════
# 8. Analyse complète — tous les indicateurs ensemble
# ══════════════════════════════════════════════════
def full_analysis(df: pd.DataFrame) -> dict:
    """
    Lance tous les indicateurs du cours et retourne :
    - Le score global (nb signaux achat vs vente)
    - La décision finale
    - Le détail de chaque indicateur
    - La stratégie recommandée
    """
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]

    # ── Calcul de tous les indicateurs ──
    rsi_val  = calculate_rsi(close)
    mm_res   = signal_mm(close)
    macd_res = calculate_macd(close)
    boll_res = calculate_bollinger(close)
    supp_res = calculate_supports_resistances(high, low, close)
    ete_res  = detect_ete(close, high)
    chand_res= analyze_chandelier(df)

    # ── Interprétation RSI ──
    if rsi_val < 30:
        rsi_signal = "ACHAT"
        rsi_detail = f"RSI = {rsi_val:.1f} < 30 → zone de survente → signal d'achat"
    elif rsi_val > 70:
        rsi_signal = "VENTE"
        rsi_detail = f"RSI = {rsi_val:.1f} > 70 → zone de surachat → signal de vente"
    else:
        rsi_signal = "NEUTRE"
        rsi_detail = f"RSI = {rsi_val:.1f} → zone neutre (30-70) → pas de signal"

    # ── Comptage des signaux ──
    indicateurs = [
        ("RSI",                    rsi_signal,        rsi_detail),
        ("Moyennes Mobiles",       mm_res["signal"],   mm_res["detail"]),
        ("MACD",                   macd_res["signal"], macd_res["detail"]),
        ("Bandes de Bollinger",    boll_res["signal"], boll_res["detail"]),
        ("Supports/Résistances",   supp_res["signal"], supp_res["detail"]),
        ("Chandeliers japonais",   chand_res["signal"],chand_res["detail"]),
        ("Figure ETE",             ete_res["signal"],  ete_res["detail"]),
    ]

    achats  = [(n, d) for n, s, d in indicateurs if s == "ACHAT"]
    ventes  = [(n, d) for n, s, d in indicateurs if s == "VENTE"]
    neutres = [(n, d) for n, s, d in indicateurs if s == "NEUTRE"]

    nb_achat = len(achats)
    nb_vente = len(ventes)

    # ── Décision finale ──
    if nb_achat >= 3 and nb_achat > nb_vente:
        decision = "ACHETER"
        force    = "fort" if nb_achat >= 4 else "modéré"
    elif nb_vente >= 3 and nb_vente > nb_achat:
        decision = "VENDRE"
        force    = "fort" if nb_vente >= 4 else "modéré"
    elif nb_achat == 2 and nb_vente <= 1:
        decision = "ACHETER"
        force    = "faible"
    elif nb_vente == 2 and nb_achat <= 1:
        decision = "VENDRE"
        force    = "faible"
    else:
        decision = "ATTENDRE"
        force    = "neutre"

    # ── Stratégie recommandée ──
    if rsi_val < 30 or rsi_val > 70 or boll_res["signal"] != "NEUTRE":
        strategie = "Stratégie contre-tendance"
    elif mm_res["signal"] != "NEUTRE" or macd_res["signal"] != "NEUTRE":
        strategie = "Stratégie de suivi de tendance"
    else:
        strategie = "Aucune stratégie claire"

    return {
        "decision":   decision,
        "force":      force,
        "strategie":  strategie,
        "rsi":        rsi_val,
        "nb_achat":   nb_achat,
        "nb_vente":   nb_vente,
        "nb_neutre":  len(neutres),
        "indicateurs":indicateurs,
        "achats":     achats,
        "ventes":     ventes,
    }
