"""
Script pour ajouter les champs de stockage S3 à la table utilisateur
"""
import os
import logging
from flask import Flask
from dotenv import load_dotenv
from models import db
from sqlalchemy import Column, String, BigInteger, DateTime
from sqlalchemy.sql import text

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

def add_storage_fields():
    """
    Ajoute les champs nécessaires pour le stockage S3 à la table utilisateur
    """
    with app.app_context():
        # Liste des colonnes à ajouter à la table user
        columns_to_add = [
            {'name': 's3_bucket_name', 'type': 'VARCHAR(255)'},
            {'name': 'storage_used', 'type': 'BIGINT', 'default': '0'},
            {'name': 'last_storage_check', 'type': 'TIMESTAMP'}
        ]
        
        conn = db.engine.connect()
        transaction = conn.begin()
        
        try:
            # Vérifier si les colonnes existent déjà
            for column in columns_to_add:
                check_sql = text(
                    f"SELECT column_name FROM information_schema.columns "
                    f"WHERE table_name='user' AND column_name='{column['name']}'"
                )
                result = conn.execute(check_sql)
                exists = result.fetchone() is not None
                
                # Si la colonne n'existe pas, l'ajouter
                if not exists:
                    default = f" DEFAULT {column.get('default', 'NULL')}" if 'default' in column else ""
                    alter_sql = text(
                        f"ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS {column['name']} {column['type']}{default}"
                    )
                    conn.execute(alter_sql)
                    logger.debug(f"Ajout de la colonne {column['name']} à la table user")
                else:
                    logger.debug(f"La colonne {column['name']} existe déjà dans la table user")
            
            # Valider la transaction
            transaction.commit()
            logger.info("Migration des champs de stockage terminée avec succès")
            
        except Exception as e:
            # Annuler la transaction en cas d'erreur
            transaction.rollback()
            logger.error(f"Erreur lors de la migration: {str(e)}")
            raise
        finally:
            # Fermer la connexion
            conn.close()

if __name__ == "__main__":
    # Exécuter la migration
    add_storage_fields()