"""
Script pour ajouter la colonne profile_picture à la table user

Exécuter avec:
python update_profile_picture.py
"""

from sqlalchemy import create_engine, text
import os
import logging
import sys

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """Exécute la migration pour ajouter le champ profile_picture à la table user"""
    
    # Récupérer l'URL de la base de données depuis les variables d'environnement
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        logger.error("Variable d'environnement DATABASE_URL non définie")
        sys.exit(1)
    
    # Créer une connexion à la base de données
    engine = create_engine(database_url)
    conn = engine.connect()
    
    try:
        # Vérifier si la colonne existe déjà
        check_column_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'user' AND column_name = 'profile_picture'
        """)
        
        result = conn.execute(check_column_query)
        column_exists = result.fetchone() is not None
        
        if column_exists:
            logger.info("La colonne profile_picture existe déjà dans la table user")
            return
        
        # Ajouter la colonne profile_picture
        alter_table_query = text("""
            ALTER TABLE "user"
            ADD COLUMN profile_picture VARCHAR(255)
        """)
        
        conn.execute(alter_table_query)
        conn.commit()
        
        logger.info("La colonne profile_picture a été ajoutée avec succès à la table user")
        
    except Exception as e:
        logger.error(f"Erreur lors de la migration: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    logger.info("Début de la migration pour ajouter la colonne profile_picture")
    run_migration()
    logger.info("Migration terminée")