#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module pour la conversion de devises
"""
import requests
import json
import os
from datetime import datetime, timedelta
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Taux de change par défaut (à utiliser en cas d'erreur d'API)
DEFAULT_RATES = {
    "EUR_USD": 1.09,  # 1 EUR = 1.09 USD
    "USD_EUR": 0.92,  # 1 USD = 0.92 EUR
    "EUR_CDF": 2750,  # 1 EUR = 2750 CDF
    "USD_CDF": 2520,  # 1 USD = 2520 CDF
    "CDF_EUR": 0.00036,  # 1 CDF = 0.00036 EUR
    "CDF_USD": 0.00040,  # 1 CDF = 0.00040 USD
}

# Cache pour les taux de change
EXCHANGE_RATES_CACHE = {
    "rates": DEFAULT_RATES.copy(),
    "last_updated": datetime.now() - timedelta(days=1)  # Forcer la mise à jour au premier appel
}

def get_exchange_rates():
    """
    Récupère les taux de change actuels ou utilise les taux en cache si mis à jour récemment
    """
    global EXCHANGE_RATES_CACHE
    
    # Vérifier si nous devons mettre à jour les taux (pas plus d'une fois par jour)
    if (datetime.now() - EXCHANGE_RATES_CACHE["last_updated"]).total_seconds() < 86400:
        return EXCHANGE_RATES_CACHE["rates"]
    
    try:
        # Vous pouvez utiliser une API de taux de change comme ExchangeRate-API, Fixer.io, etc.
        # Pour cet exemple, nous utilisons des taux fixes
        logger.info("Mise à jour des taux de change")
        
        # Dans une version de production, vous utiliseriez une API comme:
        # response = requests.get("https://api.exchangerate-api.com/v4/latest/EUR")
        # data = response.json()
        # rates = data["rates"]
        
        # Pour l'instant, nous utilisons les taux par défaut
        EXCHANGE_RATES_CACHE["rates"] = DEFAULT_RATES.copy()
        EXCHANGE_RATES_CACHE["last_updated"] = datetime.now()
        
        return EXCHANGE_RATES_CACHE["rates"]
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des taux de change: {str(e)}")
        return DEFAULT_RATES

def convert_price(amount, from_currency, to_currency):
    """
    Convertit un montant d'une devise à une autre
    """
    if from_currency == to_currency:
        return amount
    
    rates = get_exchange_rates()
    rate_key = f"{from_currency}_{to_currency}"
    
    # Si le taux direct n'existe pas, essayer d'utiliser le taux inverse
    if rate_key not in rates:
        inverse_rate_key = f"{to_currency}_{from_currency}"
        if inverse_rate_key in rates:
            return amount / rates[inverse_rate_key]
        else:
            logger.error(f"Taux de change non disponible pour {rate_key}")
            return amount  # Retourner le montant d'origine en cas d'erreur
    
    return amount * rates[rate_key]

def format_price(amount, currency):
    """
    Formate un prix avec le symbole de devise approprié
    """
    if currency == "EUR":
        return f"{amount:.2f} €"
    elif currency == "USD":
        return f"{amount:.2f} $"
    elif currency == "CDF":
        return f"{amount:.0f} FC"
    else:
        return f"{amount:.2f} {currency}"

def get_currency_symbol(currency):
    """
    Retourne le symbole pour une devise donnée
    """
    symbols = {
        "EUR": "€",
        "USD": "$",
        "CDF": "FC"
    }
    return symbols.get(currency, currency)