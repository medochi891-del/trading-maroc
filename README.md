# 🤖 Robot de Trading – Bourse de Casablanca
**Mohamed Fadel Babiya**

---

## 📋 Description

Simulation de trading automatique sur la Bourse de Casablanca.  
**100% basé sur les stratégies et indicateurs du cours.**

---

## 🧠 Indicateurs utilisés (du cours uniquement)

| Indicateur | Rôle |
|-----------|------|
| RSI | Détecter surachat/survente |
| Moyennes Mobiles (MM5/MM10) | Identifier la tendance |
| MACD | Confirmer tendance et signaux |
| Bandes de Bollinger | Mesurer la volatilité |
| Chandeliers japonais | Signaux de retournement |
| Supports / Résistances | Niveaux clés d'entrée/sortie |
| Figure ETE / ETEI | Retournement de tendance |

---

## 📊 Règles de décision

```
3+ signaux d'achat  → ACHETER  ✅
3+ signaux de vente → VENDRE   🔴
Stop-Loss atteint   → VENDRE   🔴 (priorité absolue)
Take-Profit atteint → VENDRE   🔴
Signaux insuffisants → ATTENDRE ⏳
```

---

## 💰 Gestion du risque (du cours)

- **Stop-Loss** : –2% du prix d'achat
- **Take-Profit** : +4% du prix d'achat
- **Ratio gain/risque** : 1:2
- **Montant investi** : 20% du capital actuel
- **Maximum** : 3 opérations par jour

---

## ⏰ Fonctionnement

```
Chaque lundi → vendredi
Toutes les 5 minutes de 9h30 à 15h30
        ↓
Analyse des 7 indicateurs
        ↓
Décision si 3 signaux minimum
        ↓
Mise à jour Excel + GitHub
```

---

## 🚀 Installation (5 minutes)

1. Créer un compte sur **github.com**
2. Créer un repository nommé `trading-maroc`
3. Uploader tous les fichiers du ZIP
4. Aller dans **Actions** → Enable workflows
5. C'est tout ✅

---

## 📁 Fichiers

| Fichier | Rôle |
|---------|------|
| `trading_bot.py` | Robot principal |
| `indicators.py` | Calcul des indicateurs |
| `data_fetcher.py` | Récupération des données |
| `excel_manager.py` | Gestion du fichier Excel |
| `config.json` | Configuration et état |
| `requirements.txt` | Bibliothèques |
| `.github/workflows/trading.yml` | Automatisation |
| `Mohamed_Fadel_Babiya_Trading_Simulation.xlsx` | Créé automatiquement |
| `archive/` | Copies journalières |
