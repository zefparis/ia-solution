import os
import logging
from flask import Flask
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String
from sqlalchemy.sql import text
from sqlalchemy.ext.declarative import declarative_base

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def add_payment_method_field():
    """
    Ajoute le champ payment_method à la table subscription
    """
    try:
        # Connexion à la base de données
        db_url = os.environ.get('DATABASE_URL')
        
        if not db_url:
            logger.error("DATABASE_URL n'est pas défini dans les variables d'environnement")
            return False
        
        # Création de la connexion
        engine = create_engine(db_url)
        
        # Vérifier si la colonne existe déjà
        with engine.connect() as connection:
            result = connection.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='subscription' AND column_name='payment_method'"
            ))
            
            if result.fetchone():
                logger.info("Le champ payment_method existe déjà dans la table subscription")
                return True
            
            # Ajouter la colonne
            connection.execute(text(
                "ALTER TABLE subscription ADD COLUMN payment_method VARCHAR(50)"
            ))
            
            logger.info("Champ payment_method ajouté avec succès à la table subscription")
            return True
            
    except Exception as e:
        logger.error(f"Erreur lors de l'ajout du champ payment_method: {str(e)}")
        return False


if __name__ == "__main__":
    success = add_payment_method_field()
    if success:
        print("Migration terminée avec succès!")
    else:
        print("Échec de la migration.")