"""
Script pour initialiser des données de test pour le tableau de bord financier
"""
import os
import sys
import logging
import random
from datetime import datetime, timedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from flask import Flask
import pandas as pd
import numpy as np

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialiser l'application Flask
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Importer les modèles après avoir configuré l'application
from models import db, User
from dashboard_models import TransactionCategory, Transaction

def create_sample_categories(user_id):
    """Créer des catégories d'exemple pour un utilisateur"""
    logger.info(f"Création des catégories d'exemple pour l'utilisateur {user_id}")
    
    # Catégories de dépenses
    expense_categories = [
        {"name": "Alimentation", "type": "expense", "color": "#FF5733", "icon": "shopping-cart"},
        {"name": "Logement", "type": "expense", "color": "#33A8FF", "icon": "home"},
        {"name": "Transport", "type": "expense", "color": "#33FF57", "icon": "car"},
        {"name": "Loisirs", "type": "expense", "color": "#A833FF", "icon": "gamepad"},
        {"name": "Santé", "type": "expense", "color": "#FF33A8", "icon": "medkit"},
        {"name": "Éducation", "type": "expense", "color": "#33FFA8", "icon": "book"},
        {"name": "Abonnements", "type": "expense", "color": "#FFA833", "icon": "calendar"},
        {"name": "Divers", "type": "expense", "color": "#888888", "icon": "ellipsis-h"}
    ]
    
    # Catégories de revenus
    income_categories = [
        {"name": "Salaire", "type": "income", "color": "#4CAF50", "icon": "money-bill"},
        {"name": "Freelance", "type": "income", "color": "#2196F3", "icon": "laptop"},
        {"name": "Investissements", "type": "income", "color": "#9C27B0", "icon": "chart-line"},
        {"name": "Remboursements", "type": "income", "color": "#607D8B", "icon": "receipt"},
        {"name": "Autres revenus", "type": "income", "color": "#795548", "icon": "plus-circle"}
    ]
    
    all_categories = []
    
    # Créer les catégories de dépenses
    for cat_data in expense_categories:
        category = TransactionCategory.query.filter_by(
            user_id=user_id, 
            name=cat_data["name"],
            type=cat_data["type"]
        ).first()
        
        if not category:
            category = TransactionCategory(
                user_id=user_id,
                name=cat_data["name"],
                type=cat_data["type"],
                color=cat_data["color"],
                icon=cat_data["icon"]
            )
            db.session.add(category)
            logger.info(f"Ajout de la catégorie de dépense: {cat_data['name']}")
        
        all_categories.append(category)
    
    # Créer les catégories de revenus
    for cat_data in income_categories:
        category = TransactionCategory.query.filter_by(
            user_id=user_id, 
            name=cat_data["name"],
            type=cat_data["type"]
        ).first()
        
        if not category:
            category = TransactionCategory(
                user_id=user_id,
                name=cat_data["name"],
                type=cat_data["type"],
                color=cat_data["color"],
                icon=cat_data["icon"]
            )
            db.session.add(category)
            logger.info(f"Ajout de la catégorie de revenu: {cat_data['name']}")
        
        all_categories.append(category)
    
    db.session.commit()
    return all_categories

def generate_realistic_transactions(user_id, categories, months=12):
    """
    Générer des transactions réalistes sur plusieurs mois
    avec des tendances saisonnières, des événements exceptionnels, etc.
    """
    logger.info(f"Génération de transactions réalistes sur {months} mois pour l'utilisateur {user_id}")
    
    # Date actuelle et date de début (il y a X mois)
    end_date = datetime.now()
    start_date = end_date - relativedelta(months=months)
    
    # Séparer les catégories par type
    expense_categories = [c for c in categories if c.type == 'expense']
    income_categories = [c for c in categories if c.type == 'income']
    
    # Configuration des moyennes et écarts types pour les différentes catégories
    # Format: (moyenne, écart type, fréquence mensuelle)
    expense_config = {
        "Alimentation": (400, 100, 8),  # Courses régulières
        "Logement": (800, 50, 1),       # Loyer mensuel
        "Transport": (150, 30, 4),      # Essence, transports
        "Loisirs": (120, 80, 3),        # Sorties, cinéma
        "Santé": (70, 150, 0.5),        # Consultations occasionnelles
        "Éducation": (50, 70, 0.3),     # Livres, formations
        "Abonnements": (90, 10, 1),     # Netflix, Spotify, etc.
        "Divers": (60, 40, 2)           # Dépenses diverses
    }
    
    income_config = {
        "Salaire": (2200, 100, 1),      # Salaire mensuel
        "Freelance": (400, 300, 0.7),   # Missions occasionnelles
        "Investissements": (50, 20, 0.8), # Revenus d'investissement
        "Remboursements": (70, 150, 0.2), # Remboursements médicaux
        "Autres revenus": (30, 100, 0.1)  # Cadeaux, etc.
    }
    
    # Listes pour stocker les données de transactions
    all_transactions = []
    
    # Pour chaque mois dans la période
    current_date = start_date
    month_count = 0
    
    while current_date <= end_date:
        month_count += 1
        # Facteur saisonnier (été plus dépensier, hiver plus économe)
        month_num = current_date.month
        seasonal_factor = 1.0 + 0.2 * np.sin((month_num - 3) * np.pi / 6)  # Pic en été (juin-juillet)
        
        # Facteur d'événement exceptionnel (1% de chance d'une grosse dépense/revenu)
        has_exceptional_event = random.random() < 0.05
        
        # Générer les dépenses pour ce mois
        for category in expense_categories:
            category_name = category.name
            if category_name in expense_config:
                mean, std, freq = expense_config[category_name]
                
                # Appliquer facteur saisonnier
                adjusted_mean = mean * seasonal_factor
                
                # Déterminer le nombre de transactions pour cette catégorie ce mois-ci
                num_transactions = max(1, int(random.normalvariate(freq, freq/3)))
                
                for _ in range(num_transactions):
                    # Générer un montant réaliste
                    amount = max(5, random.normalvariate(adjusted_mean / freq, std / freq))
                    
                    # Date aléatoire dans le mois
                    days_in_month = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                    transaction_day = random.randint(1, days_in_month.day)
                    transaction_date = current_date.replace(day=transaction_day)
                    
                    # Si la date est dans le futur, sauter cette transaction
                    if transaction_date > datetime.now():
                        continue
                    
                    # Créer une description réaliste
                    descriptions = {
                        "Alimentation": ["Supermarché", "Boulangerie", "Épicerie", "Marché", "Restaurant"],
                        "Logement": ["Loyer", "Électricité", "Eau", "Internet", "Assurance habitation"],
                        "Transport": ["Essence", "Transports en commun", "Péage", "Parking", "Entretien voiture"],
                        "Loisirs": ["Cinéma", "Restaurant", "Concert", "Abonnement salle de sport", "Jeux vidéo"],
                        "Santé": ["Pharmacie", "Médecin", "Dentiste", "Optique", "Mutuelle"],
                        "Éducation": ["Livres", "Formation", "Cours", "Matériel scolaire"],
                        "Abonnements": ["Netflix", "Spotify", "Amazon Prime", "Disney+", "Xbox Game Pass"],
                        "Divers": ["Cadeau", "Vêtements", "Accessoires", "Coiffeur", "Décoration"]
                    }
                    
                    desc_options = descriptions.get(category_name, ["Paiement"])
                    description = random.choice(desc_options)
                    
                    # Ajouter la transaction
                    transaction = Transaction(
                        user_id=user_id,
                        category_id=category.id,
                        description=description,
                        amount=Decimal(str(round(amount, 2))),
                        date=transaction_date,
                        notes=None
                    )
                    all_transactions.append(transaction)
        
        # Générer les revenus pour ce mois
        for category in income_categories:
            category_name = category.name
            if category_name in income_config:
                mean, std, freq = income_config[category_name]
                
                # Les revenus sont moins saisonniers mais peuvent avoir des primes (fin d'année)
                year_end_bonus = 1.0 + (0.5 if month_num == 12 else 0)
                adjusted_mean = mean * year_end_bonus
                
                # Probabilité d'avoir cette transaction ce mois-ci
                if random.random() <= freq:
                    # Générer un montant réaliste
                    amount = max(10, random.normalvariate(adjusted_mean, std))
                    
                    # Date aléatoire, mais les salaires sont plutôt en début de mois
                    if category_name == "Salaire":
                        transaction_day = random.randint(1, 5)  # 1er au 5 du mois
                    else:
                        days_in_month = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                        transaction_day = random.randint(1, days_in_month.day)
                    
                    transaction_date = current_date.replace(day=transaction_day)
                    
                    # Si la date est dans le futur, sauter
                    if transaction_date > datetime.now():
                        continue
                    
                    # Descriptions réalistes
                    descriptions = {
                        "Salaire": ["Salaire mensuel", "Paye", "Rémunération"],
                        "Freelance": ["Mission freelance", "Contrat", "Prestation"],
                        "Investissements": ["Dividendes", "Intérêts", "Revenu locatif", "Plus-value"],
                        "Remboursements": ["Remboursement médical", "Remboursement transport", "Remboursement achat"],
                        "Autres revenus": ["Cadeau", "Vente", "Remboursement", "Prime"]
                    }
                    
                    desc_options = descriptions.get(category_name, ["Revenu"])
                    description = random.choice(desc_options)
                    
                    # Ajouter la transaction
                    transaction = Transaction(
                        user_id=user_id,
                        category_id=category.id,
                        description=description,
                        amount=Decimal(str(round(amount, 2))),
                        date=transaction_date,
                        notes=None
                    )
                    all_transactions.append(transaction)
        
        # Ajouter un événement exceptionnel?
        if has_exceptional_event:
            # 70% chance d'avoir une grosse dépense, 30% chance d'avoir un gros revenu
            if random.random() < 0.7:
                # Grosse dépense
                exceptional_category = random.choice(expense_categories)
                exceptional_amount = random.uniform(500, 2000)
                exceptional_descriptions = [
                    "Réparation voiture", "Nouvel ordinateur", "Électroménager", 
                    "Travaux maison", "Voyage", "Meuble", "Appareil électronique"
                ]
                
                transaction_day = random.randint(1, 28)
                transaction_date = current_date.replace(day=transaction_day)
                
                if transaction_date <= datetime.now():
                    transaction = Transaction(
                        user_id=user_id,
                        category_id=exceptional_category.id,
                        description=random.choice(exceptional_descriptions) + " (exceptionnel)",
                        amount=Decimal(str(round(exceptional_amount, 2))),
                        date=transaction_date,
                        notes="Dépense exceptionnelle"
                    )
                    all_transactions.append(transaction)
            else:
                # Gros revenu
                exceptional_category = random.choice(income_categories)
                exceptional_amount = random.uniform(300, 1500)
                exceptional_descriptions = [
                    "Prime exceptionnelle", "Bonus", "Remboursement important",
                    "Vente exceptionnelle", "Cadeau"
                ]
                
                transaction_day = random.randint(1, 28)
                transaction_date = current_date.replace(day=transaction_day)
                
                if transaction_date <= datetime.now():
                    transaction = Transaction(
                        user_id=user_id,
                        category_id=exceptional_category.id,
                        description=random.choice(exceptional_descriptions) + " (exceptionnel)",
                        amount=Decimal(str(round(exceptional_amount, 2))),
                        date=transaction_date,
                        notes="Revenu exceptionnel"
                    )
                    all_transactions.append(transaction)
        
        # Passer au mois suivant
        current_date = current_date + relativedelta(months=1)
    
    # Enregistrer toutes les transactions
    logger.info(f"Ajout de {len(all_transactions)} transactions à la base de données")
    db.session.add_all(all_transactions)
    db.session.commit()
    
    return all_transactions

def main():
    with app.app_context():
        # Obtenir l'utilisateur spécifique par son username
        username = input("Entrez le nom d'utilisateur pour lequel générer des données: ")
        user = User.query.filter_by(username=username).first()
        
        if not user:
            logger.error(f"Utilisateur '{username}' non trouvé")
            return
        
        user_id = user.id
        logger.info(f"Génération de données pour l'utilisateur {username} (ID: {user_id})")
        
        # Vérifier s'il y a déjà des données
        existing_categories = TransactionCategory.query.filter_by(user_id=user_id).count()
        existing_transactions = Transaction.query.filter_by(user_id=user_id).count()
        
        if existing_categories > 0 or existing_transactions > 0:
            confirm = input(f"L'utilisateur a déjà {existing_categories} catégories et {existing_transactions} transactions. Voulez-vous continuer et potentiellement ajouter des doublons? (o/n): ")
            if confirm.lower() != 'o':
                logger.info("Opération annulée")
                return
        
        # Créer les catégories
        categories = create_sample_categories(user_id)
        
        # Générer les transactions
        months = int(input("Sur combien de mois voulez-vous générer des données? (12 par défaut): ") or "12")
        transactions = generate_realistic_transactions(user_id, categories, months)
        
        logger.info(f"Données générées avec succès! {len(transactions)} transactions ajoutées.")
        
        # Récapitulatif des totaux
        expense_total = sum(float(t.amount) for t in transactions
                          if TransactionCategory.query.get(t.category_id).type == 'expense')
        income_total = sum(float(t.amount) for t in transactions
                         if TransactionCategory.query.get(t.category_id).type == 'income')
        
        print(f"\nRésumé des données générées:")
        print(f"- Catégories: {len(categories)} ({len([c for c in categories if c.type == 'expense'])} dépenses, {len([c for c in categories if c.type == 'income'])} revenus)")
        print(f"- Transactions: {len(transactions)}")
        print(f"- Total des dépenses: {expense_total:.2f} €")
        print(f"- Total des revenus: {income_total:.2f} €")
        print(f"- Solde: {income_total - expense_total:.2f} €")

if __name__ == "__main__":
    main()