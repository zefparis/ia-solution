#!/usr/bin/env python3
"""
Script pour mettre à jour le schéma de la table tax_report
Ajoute les nouvelles colonnes nécessaires pour la fonctionnalité de rapports fiscaux
"""
import os
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Récupérer l'URL de la base de données
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    logger.error("Variable d'environnement DATABASE_URL non définie")
    sys.exit(1)

def add_column_if_not_exists(engine, table_name, column_name, column_definition):
    """Ajoute une colonne à une table si elle n'existe pas déjà"""
    try:
        # Vérifier si la colonne existe déjà
        query = text(f"""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = '{table_name}' AND column_name = '{column_name}'
        """)
        with engine.connect() as conn:
            result = conn.execute(query)
            # Si la colonne existe déjà, ne rien faire
            if result.rowcount > 0:
                logger.info(f"La colonne {column_name} existe déjà dans {table_name}")
                return False
            
            # Si la colonne n'existe pas, l'ajouter
            alter_query = text(f"""
            ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}
            """)
            conn.execute(alter_query)
            conn.commit()
            logger.info(f"Colonne {column_name} ajoutée à {table_name}")
            return True
    except SQLAlchemyError as e:
        logger.error(f"Erreur lors de l'ajout de la colonne {column_name}: {str(e)}")
        return False

def main():
    """Fonction principale pour mettre à jour le schéma"""
    try:
        logger.info("Connexion à la base de données...")
        engine = create_engine(database_url)
        
        # Colonnes à ajouter avec leurs définitions
        columns_to_add = [
            ("name", "VARCHAR(100)"),
            ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ("ai_analysis", "TEXT"),
            ("notes", "TEXT"),
            ("profit", "NUMERIC(12, 2)")
        ]
        
        # Ajouter chaque colonne
        success = True
        for column_name, column_definition in columns_to_add:
            if not add_column_if_not_exists(engine, "tax_report", column_name, column_definition):
                success = False
        
        if success:
            logger.info("Mise à jour du schéma réussie!")
        else:
            logger.warning("Certaines colonnes n'ont pas pu être ajoutées.")
            
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du schéma: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()