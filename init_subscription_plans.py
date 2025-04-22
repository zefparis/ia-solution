"""
Script pour initialiser les plans d'abonnement dans la base de données
"""
import os
import logging
from flask import Flask
from dotenv import load_dotenv
from models import db, SubscriptionPlan

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Créer une mini-application Flask pour accéder à la base de données
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Définir les plans d'abonnement
SUBSCRIPTION_PLANS = [
    {
        "name": "Essai gratuit", 
        "display_name": "Essai gratuit",
        "price": 0.00, 
        "storage_limit": 1024 * 1024 * 1024,  # 1 GB
        "description": "Essai gratuit de 14 jours avec 1 Go de stockage.",
        "features": "Accès complet pendant 14 jours,1 Go de stockage,Support par email,Fonctionnalités de base"
    },
    {
        "name": "Essential", 
        "display_name": "Essentiel",
        "price": 12.00, 
        "storage_limit": 10 * 1024 * 1024 * 1024,  # 10 GB
        "description": "Plan de base avec 10 Go de stockage, idéal pour un usage personnel.",
        "features": "10 Go de stockage,Support par email,Fonctionnalités de base,Extraction OCR illimitée"
    },
    {
        "name": "Pro", 
        "display_name": "Professionnel",
        "price": 25.00, 
        "storage_limit": 50 * 1024 * 1024 * 1024,  # 50 GB
        "description": "Plan professionnel avec 50 Go de stockage, parfait pour les indépendants et petites entreprises.",
        "features": "50 Go de stockage,Support prioritaire,Toutes les fonctionnalités de base,Rapports financiers avancés,Exportation au format PDF"
    },
    {
        "name": "Premium", 
        "display_name": "Premium",
        "price": 49.00, 
        "storage_limit": 100 * 1024 * 1024 * 1024,  # 100 GB
        "description": "Plan premium avec 100 Go de stockage, pour les entreprises ayant des besoins importants.",
        "features": "100 Go de stockage,Support premium 24/7,Toutes les fonctionnalités avancées,Intégration API complète,Rapports personnalisés,Multi-utilisateurs"
    }
]

def init_subscription_plans():
    """
    Initialise les plans d'abonnement dans la base de données
    s'ils n'existent pas déjà
    """
    with app.app_context():
        # Vérifier si les plans existent déjà
        existing_plans = SubscriptionPlan.query.all()
        existing_plan_names = [plan.name for plan in existing_plans]
        
        # Nombre de plans ajoutés
        plans_added = 0
        
        # Ajouter les plans qui n'existent pas encore
        for plan_data in SUBSCRIPTION_PLANS:
            if plan_data["name"] not in existing_plan_names:
                plan = SubscriptionPlan(
                    name=plan_data["name"],
                    display_name=plan_data["display_name"],
                    price=plan_data["price"],
                    storage_limit=plan_data["storage_limit"],
                    description=plan_data["description"],
                    features=plan_data["features"],
                    is_active=True
                )
                db.session.add(plan)
                plans_added += 1
                logger.debug(f"Plan d'abonnement '{plan_data['name']}' ajouté")
            else:
                logger.debug(f"Le plan '{plan_data['name']}' existe déjà")
        
        # Sauvegarder les modifications
        if plans_added > 0:
            db.session.commit()
            logger.info(f"{plans_added} plans d'abonnement ont été ajoutés à la base de données")
        else:
            logger.info("Aucun nouveau plan d'abonnement à ajouter")

if __name__ == "__main__":
    # Créer les tables si elles n'existent pas
    with app.app_context():
        db.create_all()
    
    # Initialiser les plans d'abonnement
    init_subscription_plans()