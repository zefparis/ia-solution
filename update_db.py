import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import inspect

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Création de la base Flask
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

# Fonction pour vérifier si une colonne existe
def column_exists(table_name, column_name):
    with app.app_context():
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns

# Fonction pour ajouter une colonne si elle n'existe pas
def add_column_if_not_exists(table_name, column_name, column_type):
    if not column_exists(table_name, column_name):
        logger.info(f"Ajout de la colonne {column_name} à la table {table_name}")
        with db.engine.connect() as conn:
            stmt = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            conn.execute(db.text(stmt))
            conn.commit()
    else:
        logger.info(f"La colonne {column_name} existe déjà dans la table {table_name}")

# Fonction pour vérifier si une table existe
def table_exists(table_name):
    with app.app_context():
        inspector = inspect(db.engine)
        return table_name in inspector.get_table_names()

# Fonction pour créer les plans d'abonnement par défaut
def create_subscription_plans():
    with app.app_context():
        from models import SubscriptionPlan
        
        # Vérifier si des plans existent déjà
        existing_plans = SubscriptionPlan.query.count()
        if existing_plans > 0:
            logger.info(f"{existing_plans} plans d'abonnement existent déjà")
            return
        
        # Définir les plans par défaut
        plans = [
            {
                'name': 'free',
                'display_name': 'Essai Gratuit',
                'price': 0.00,
                'storage_limit': 1024 * 1024 * 1024,  # 1 GB
                'description': 'Accès complet pendant 14 jours pour découvrir toutes les fonctionnalités.',
                'features': 'Accès complet pendant 14 jours,1 GB de stockage,Sauvegarde de 5 conversations,Compatibilité mobile'
            },
            {
                'name': 'essential',
                'display_name': 'Essentiel',
                'price': 12.00,
                'storage_limit': 10 * 1024 * 1024 * 1024,  # 10 GB
                'description': 'Idéal pour les indépendants et les petites entreprises.',
                'features': '10 GB de stockage,Sauvegarde illimitée des conversations,Support par email,Exportation de données'
            },
            {
                'name': 'pro',
                'display_name': 'Professionnel',
                'price': 25.00,
                'storage_limit': 50 * 1024 * 1024 * 1024,  # 50 GB
                'description': 'Pour les professionnels qui ont besoin de plus de capacité et de fonctionnalités.',
                'features': '50 GB de stockage,Toutes les fonctionnalités Essentiel,Priorité dans les réponses de l\'IA,Support prioritaire,Analyses financières avancées'
            },
            {
                'name': 'premium',
                'display_name': 'Premium',
                'price': 49.00,
                'storage_limit': 100 * 1024 * 1024 * 1024,  # 100 GB
                'description': 'Notre offre la plus complète pour les entreprises exigeantes.',
                'features': '100 GB de stockage,Toutes les fonctionnalités Professionnel,Support dédié,Fonctionnalités exclusives,Rapports fiscaux personnalisés'
            }
        ]
        
        # Créer les plans dans la base de données
        for plan_data in plans:
            plan = SubscriptionPlan(**plan_data)
            db.session.add(plan)
        
        db.session.commit()
        logger.info("Plans d'abonnement créés avec succès")

# Fonction pour ajouter les champs liés au stockage à la table User
def add_storage_fields_to_user():
    add_column_if_not_exists('user', 's3_bucket_name', 'VARCHAR(255)')
    add_column_if_not_exists('user', 'storage_used', 'BIGINT DEFAULT 0')
    add_column_if_not_exists('user', 'last_storage_check', 'TIMESTAMP')

# Fonction principale pour mettre à jour la base de données
def update_database():
    with app.app_context():
        # Importer les modèles pour que create_all puisse les utiliser
        from models import User, Conversation, Message, ExtractedText
        from models import Category, FinancialTransaction, Vendor, TaxReport
        from models import SubscriptionPlan, Subscription
        from models_business import BusinessReport
        
        # Création des tables si elles n'existent pas
        db.create_all()
        logger.info("Tables créées/vérifiées")
        
        # Ajout des colonnes manquantes à extracted_text
        add_column_if_not_exists('extracted_text', 'is_processed', 'BOOLEAN DEFAULT FALSE')
        add_column_if_not_exists('extracted_text', 'document_type', 'VARCHAR(50)')
        add_column_if_not_exists('extracted_text', 'transaction_id', 'INTEGER')
        
        # Ajout de la colonne report_html à tax_report pour stocker les rapports générés par IA
        add_column_if_not_exists('tax_report', 'report_html', 'TEXT')
        
        # Ajout des champs liés au stockage et aux abonnements
        add_storage_fields_to_user()
        
        # Ajout du champ email_sent à business_report
        if table_exists('business_report'):
            add_column_if_not_exists('business_report', 'email_sent', 'BOOLEAN DEFAULT FALSE')
            logger.info("Colonne email_sent ajoutée à la table business_report si nécessaire")
        
        # Créer les plans d'abonnement si la table existe
        if table_exists('subscription_plan'):
            create_subscription_plans()
        
        # Ajout de contrainte de clé étrangère si necessaire
        try:
            with db.engine.connect() as conn:
                stmt = db.text("""
                    ALTER TABLE extracted_text 
                    ADD CONSTRAINT fk_transaction 
                    FOREIGN KEY (transaction_id) 
                    REFERENCES financial_transaction(id)
                """)
                conn.execute(stmt)
                conn.commit()
                logger.info("Contrainte de clé étrangère ajoutée à extracted_text.transaction_id")
        except Exception as e:
            # La contrainte peut déjà exister ou la colonne n'existe pas encore
            logger.warning(f"Impossible d'ajouter la contrainte: {str(e)}")

if __name__ == "__main__":
    update_database()
    logger.info("Mise à jour de la base de données terminée")