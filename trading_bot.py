"""
trading_bot.py
Robot de Trading - Bourse de Casablanca
Mohamed Fadel Babiya

GitHub Actions lance ce script toutes les 5 minutes.
Le script execute UN seul cycle d'analyse et s'arrete.
L'etat est sauvegarde dans config.json entre chaque run.
"""

import json
import os
import subprocess
from datetime import datetime, date, timezone, timedelta
import pandas as pd

from data_fetcher  import get_historical_ohlcv, get_live_price
from indicators    import full_analysis
from excel_manager import (create_excel, add_trade_row,
                            fill_presentation, save_archive)

CONFIG_FILE = "config.json"
EXCEL_FILE  = "Mohamed_Fadel_Babiya_Trading_Simulation.xlsx"
MAX_DAYS    = 10
MAX_TRADES  = 2

# Fuseau horaire Maroc UTC+1
MAROC_TZ = timezone(timedelta(hours=1))

# Jours feries Maroc 2026
JOURS_FERIES = [
    "2026-01-01", "2026-01-11", "2026-05-01",
    "2026-07-30", "2026-08-14", "2026-11-06", "2026-11-18"
]

# ═══════════════════════════════════════════════
# 1. CONFIG
# ═══════════════════════════════════════════════
def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

# ═══════════════════════════════════════════════
# 2. HORAIRES - TIMEZONE MAROC
# ═══════════════════════════════════════════════
def now_maroc() -> datetime:
    """Retourne l'heure actuelle au Maroc (UTC+1)"""
    return datetime.now(timezone.utc).astimezone(MAROC_TZ)

def is_trading_day() -> bool:
    """Lundi-Vendredi, hors jours feries marocains"""
    today = now_maroc().date()
    if today.weekday() >= 5:
        return False
    if today.strftime("%Y-%m-%d") in JOURS_FERIES:
        return False
    return True

def is_market_open() -> bool:
    """Bourse de Casablanca : 9h30 a 15h30 (heure Maroc)"""
    now = now_maroc()
    t   = now.hour * 60 + now.minute
    return (9 * 60 + 30) <= t <= (15 * 60 + 30)

def is_market_closed_for_day() -> bool:
    """Retourne True apres 15h30 heure Maroc"""
    now = now_maroc()
    return now.hour * 60 + now.minute > 15 * 60 + 30

def is_new_trading_day(cfg: dict) -> bool:
    today_str = now_maroc().date().strftime("%Y-%m-%d")
    return cfg.get("current_trading_date", "") != today_str

# ═══════════════════════════════════════════════
# 3. INITIALISATION DU JOUR
# ═══════════════════════════════════════════════
def initialize_new_day(cfg: dict) -> dict:
    """
    Appelee une seule fois par jour (premier run).
    Remet a zero le compteur de trades.
    Incremente le jour.
    """
    today_str = now_maroc().date().strftime("%Y-%m-%d")

    if cfg["current_trading_date"] != "":
        cfg["current_day"] += 1

    cfg["current_trading_date"] = today_str
    cfg["day_initialized"]      = True
    cfg["trade_count"]          = 0
    cfg["attendre_logged"]      = False

    print(f"Nouveau jour initialise : J{cfg['current_day']} - {today_str}")
    return cfg

# ═══════════════════════════════════════════════
# 4. EXPLICATION (vocabulaire du cours uniquement)
# ═══════════════════════════════════════════════
def build_explication(analysis: dict, action: str,
                       prix: float, cfg: dict,
                       qty_avant_vente: int = 0,
                       buy_price_avant_vente: float = 0) -> str:
    """
    Explication en francais, 100% basee sur le vocabulaire du cours.
    Aucun emoji, aucun terme hors cours.
    """
    lines = ["Analyse des indicateurs du jour :"]

    for nom, signal, detail in analysis["indicateurs"]:
        lines.append(f"{nom} : {detail}.")

    lines.append(
        f"Resultat : {analysis['nb_achat']} signal(s) d'achat, "
        f"{analysis['nb_vente']} signal(s) de vente, "
        f"{analysis['nb_neutre']} neutre(s). "
        f"Strategie appliquee : {analysis['strategie']}."
    )

    if action == "ACHETER":
        invest = round(cfg["capital"] * cfg["invest_pct"])
        qty    = int(invest / prix)
        sl     = round(prix * 0.98, 2)
        tp     = round(prix * 1.04, 2)
        lines.append(
            f"Decision : ACHETER. "
            f"{analysis['nb_achat']} indicateurs confirment le signal d'achat "
            f"(signal {analysis['force']}). "
            f"Achat de {qty} actions a {prix:.2f} MAD. "
            f"Stop-Loss fixe a {sl:.2f} MAD (-2%). "
            f"Take-Profit fixe a {tp:.2f} MAD (+4%). "
            f"Ratio gain/risque : 1:2."
        )

    elif action == "VENDRE":
        gp = round((prix - buy_price_avant_vente) * qty_avant_vente, 2)

        if prix <= cfg.get("stop_loss_price", 0):
            raison = (
                f"Stop-Loss atteint a {cfg.get('stop_loss_price', 0):.2f} MAD. "
                f"Fermeture automatique pour proteger le capital."
            )
        elif prix >= cfg.get("take_profit_price", 0):
            raison = (
                f"Take-Profit atteint a {cfg.get('take_profit_price', 0):.2f} MAD. "
                f"Securisation des gains. Ratio gain/risque 1:2 respecte."
            )
        else:
            raison = (
                f"{analysis['nb_vente']} signaux de danger detectes. "
                f"Cloture anticipee pour proteger le capital. "
                f"Sortie avant Stop-Loss justifiee par les indicateurs."
            )

        lines.append(
            f"Decision : VENDRE. "
            f"{raison} "
            f"Vente de {qty_avant_vente} actions a {prix:.2f} MAD. "
            f"Gain/Perte de cette operation : {gp:+.2f} MAD."
        )

    elif action == "CONSERVER":
        lines.append(
            "Decision : CONSERVER. "
            "Aucun signal de sortie suffisamment fort detecte "
            "(moins de 3 indicateurs de vente). "
            "Position maintenue conformement au plan de trading."
        )

    else:
        lines.append(
            "Decision : ATTENDRE. "
            f"Signaux insuffisants ou contradictoires "
            f"({analysis['nb_achat']} achat(s) contre {analysis['nb_vente']} vente(s)). "
            "Minimum 3 signaux requis pour agir. "
            "Aucune operation effectuee ce cycle."
        )

    return " ".join(lines)

# ═══════════════════════════════════════════════
# 5. DECISION
# ═══════════════════════════════════════════════
def decide_action(analysis: dict, cfg: dict, prix: float) -> str:
    """
    Regles du cours :
      Stop-Loss atteint      -> VENDRE (priorite absolue)
      Take-Profit atteint    -> VENDRE
      3+ signaux de vente    -> VENDRE (sortie anticipee)
      3+ signaux d'achat     -> ACHETER (si libre et trades restants)
      Sinon                  -> CONSERVER / ATTENDRE
    """
    position = cfg.get("position_open", False)

    if position:
        if prix <= cfg.get("stop_loss_price", 0):
            return "VENDRE"
        if prix >= cfg.get("take_profit_price", 0):
            return "VENDRE"
        if analysis["nb_vente"] >= 3:
            return "VENDRE"
        return "CONSERVER"
    else:
        if (analysis["decision"] == "ACHETER"
                and cfg.get("trade_count", 0) < MAX_TRADES):
            return "ACHETER"
        return "ATTENDRE"

# ═══════════════════════════════════════════════
# 6. EXECUTION DU TRADE
# ═══════════════════════════════════════════════
def execute_trade(action: str, prix: float, cfg: dict):
    """
    Met a jour la config.
    Retourne : (qty, gain, buy_price_utilise)
    """
    if action == "ACHETER":
        invest = round(cfg["capital"] * cfg["invest_pct"])
        qty    = int(invest / prix)
        sl     = round(prix * 0.98, 2)
        tp     = round(prix * 1.04, 2)
        cfg.update({
            "position_open":     True,
            "buy_price":         prix,
            "quantity":          qty,
            "stop_loss_price":   sl,
            "take_profit_price": tp,
            "invest_amount":     invest,
        })
        print(f"ACHAT  : {qty} x {prix:.2f} MAD = {qty*prix:,.0f} MAD")
        print(f"Stop-Loss : {sl:.2f} MAD | Take-Profit : {tp:.2f} MAD")
        return qty, 0.0, prix

    elif action == "VENDRE":
        bp   = cfg["buy_price"]
        qty  = cfg["quantity"]
        gain = round((prix - bp) * qty, 2)

        # Mise a jour capital AVANT reset
        cfg["capital"]       = round(cfg["capital"] + gain, 2)
        cfg["total_gain"]    = round(cfg.get("total_gain", 0) + gain, 2)
        cfg["nb_operations"] = cfg.get("nb_operations", 0) + 1
        cfg["trade_count"]   = cfg.get("trade_count", 0) + 1

        if gain >= 0:
            cfg["nb_win"]  = cfg.get("nb_win", 0) + 1
        else:
            cfg["nb_loss"] = cfg.get("nb_loss", 0) + 1

        # Reset position APRES avoir sauvegarde tout
        cfg.update({
            "position_open":     False,
            "buy_price":         0,
            "quantity":          0,
            "stop_loss_price":   0,
            "take_profit_price": 0,
        })
        print(f"VENTE  : {qty} x {prix:.2f} MAD | G/P : {gain:+.2f} MAD")
        print(f"Capital actuel : {cfg['capital']:,.0f} MAD")
        return qty, gain, bp

    return 0, 0.0, 0.0

# ═══════════════════════════════════════════════
# 7. GIT PUSH
# ═══════════════════════════════════════════════
def git_push(jour: int):
    try:
        now_m = now_maroc()
        subprocess.run(["git","config","user.email","bot@trading-maroc.ma"], check=True)
        subprocess.run(["git","config","user.name", "Robot Trading"],        check=True)
        subprocess.run(["git","add","-A"],                                    check=True)
        msg = (f"Jour {jour} - "
               f"{now_m.strftime('%d/%m/%Y %H:%M')} - "
               f"mise a jour automatique")
        result = subprocess.run(["git","commit","-m", msg], capture_output=True)
        if result.returncode == 0:
            subprocess.run(["git","push"], check=True)
            print("GitHub mis a jour")
        else:
            print("Aucune modification a pousser")
    except subprocess.CalledProcessError as e:
        print(f"Git erreur : {e}")

# ═══════════════════════════════════════════════
# 8. MAIN
# ═══════════════════════════════════════════════
def main():
    cfg = load_config()

    # Verifications de base
    if not is_trading_day():
        print("Weekend ou jour ferie - aucune operation.")
        return

    jour = cfg["current_day"]

    # Gestion fin de journee
    if is_market_closed_for_day():
        if cfg.get("day_initialized") and not cfg.get("archive_saved_today", False):

            # Si aucune operation du tout aujourd'hui -> noter dans Excel
            if cfg.get("trade_count", 0) == 0 and not cfg.get("attendre_logged", False):
                prix_cloture = get_live_price()
                add_trade_row(
                    jour        = jour,
                    trade_num   = 1,
                    date_str    = now_maroc().date().strftime("%d/%m/%Y"),
                    action      = "ATTENDRE",
                    prix_achat  = None,
                    prix_actuel = prix_cloture,
                    quantite    = None,
                    valeur      = None,
                    gain_perte  = None,
                    strategie   = "Aucune strategie applicable",
                    explication = (
                        "Analyse complete effectuee tout au long de la seance. "
                        "Aucun signal suffisamment fort detecte (minimum 3 indicateurs requis). "
                        "Aucune operation effectuee. Discipline de trading respectee."
                    ),
                )
                cfg["attendre_logged"] = True

            # Dernier jour -> Presentation
            if jour == MAX_DAYS:
                fill_presentation(
                    config     = cfg,
                    total_gain = cfg.get("total_gain", 0),
                    nb_ops     = cfg.get("nb_operations", 0),
                    nb_win     = cfg.get("nb_win", 0),
                    nb_loss    = cfg.get("nb_loss", 0),
                )

            save_archive(jour)
            cfg["archive_saved_today"] = True
            cfg["day_initialized"]     = False
            save_config(cfg)
            git_push(jour)

        print("Bourse fermee pour aujourd'hui.")
        return

    if not is_market_open():
        print("Bourse pas encore ouverte - attente de 9h30.")
        return

    if jour > MAX_DAYS:
        print("Simulation terminee - 10 jours completes.")
        return

    print(f"Bourse de Casablanca | {cfg['stock_name']}")
    print(f"Jour {jour}/{MAX_DAYS} - "
          f"{now_maroc().strftime('%d/%m/%Y %H:%M')} (heure Maroc)")
    print(f"Capital : {cfg['capital']:,.0f} MAD "
          f"| Operations : {cfg.get('trade_count',0)}/{MAX_TRADES}")

    # Initialisation du nouveau jour
    if is_new_trading_day(cfg):
        cfg = initialize_new_day(cfg)
        cfg["archive_saved_today"] = False
        if jour == 1 and not os.path.exists(EXCEL_FILE):
            create_excel(cfg)
        save_config(cfg)

    # Limite atteinte
    if cfg.get("trade_count", 0) >= MAX_TRADES:
        print(f"Maximum {MAX_TRADES} operations atteint pour aujourd'hui.")
        return

    # Donnees
    df_hist = get_historical_ohlcv(period="3mo")
    prix    = get_live_price()

    if df_hist is None or prix is None:
        print("Donnees indisponibles - nouvelle tentative dans 5 min")
        return

    print(f"Prix actuel : {prix:.2f} MAD")

    # Prix live dans l'historique
    df_live = pd.concat([
        df_hist,
        pd.DataFrame(
            {"Open": [prix], "High": [prix],
             "Low":  [prix], "Close":[prix], "Volume":[0]},
            index=[pd.Timestamp.now(tz="UTC")]
        )
    ])

    # Analyse
    analysis = full_analysis(df_live)
    action   = decide_action(analysis, cfg, prix)

    print(f"RSI : {analysis['rsi']:.1f} | "
          f"Achats : {analysis['nb_achat']} | "
          f"Ventes : {analysis['nb_vente']} | "
          f"Decision : {action}")

    # CONSERVER ou ATTENDRE -> pas d'ecriture dans Excel
    if action in ["CONSERVER", "ATTENDRE"]:
        print(f"{action} - pas d'operation ce cycle")
        save_config(cfg)
        return

    # Sauvegarder avant execute_trade
    qty_avant       = cfg.get("quantity", 0)
    bp_avant        = cfg.get("buy_price", 0)
    sl_avant        = cfg.get("stop_loss_price", 0)
    tp_avant        = cfg.get("take_profit_price", 0)

    # Execution
    qty, gain, bp_utilise = execute_trade(action, prix, cfg)

    # Explication construite avec les valeurs AVANT reset
    cfg_pour_expl = dict(cfg)
    cfg_pour_expl["stop_loss_price"]   = sl_avant
    cfg_pour_expl["take_profit_price"] = tp_avant

    explication = build_explication(
        analysis              = analysis,
        action                = action,
        prix                  = prix,
        cfg                   = cfg_pour_expl,
        qty_avant_vente       = qty_avant if action == "VENDRE" else qty,
        buy_price_avant_vente = bp_avant,
    )

    valeur = round(qty * prix, 2) if action == "ACHETER" else 0.0
    gp     = gain                  if action == "VENDRE"  else None

    # Numero operation
    trade_num = cfg.get("trade_count", 0) if action == "VENDRE" else cfg.get("trade_count", 0) + 1

    add_trade_row(
        jour        = jour,
        trade_num   = trade_num,
        date_str    = now_maroc().date().strftime("%d/%m/%Y"),
        action      = action,
        prix_achat  = cfg["buy_price"] if action == "ACHETER" else bp_avant,
        prix_actuel = prix,
        quantite    = qty,
        valeur      = valeur,
        gain_perte  = gp,
        strategie   = analysis["strategie"],
        explication = explication,
    )

    save_config(cfg)
    git_push(jour)


if __name__ == "__main__":
    main()
