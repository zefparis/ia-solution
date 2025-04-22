#!/usr/bin/env python3
"""
Script simple pour vérifier la connexion à DynamoDB
"""

import os
import sys
import logging
import boto3
from pynamodb.connection import Connection

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Récupération des variables d'environnement AWS
AWS_REGION = os.environ.get('AWS_REGION', 'eu-west-3')
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')

def check_aws_credentials():
    """Vérifie que les variables d'environnement AWS sont définies"""
    missing_vars = []
    
    if not AWS_ACCESS_KEY_ID:
        missing_vars.append('AWS_ACCESS_KEY_ID')
    
    if not AWS_SECRET_ACCESS_KEY:
        missing_vars.append('AWS_SECRET_ACCESS_KEY')
    
    if missing_vars:
        logger.error(f"Variables d'environnement manquantes: {', '.join(missing_vars)}")
        return False
    
    return True

def check_dynamodb_connection():
    """Vérifie la connexion à DynamoDB"""
    try:
        # Méthode 1: Utiliser boto3 directement
        dynamodb = boto3.client(
            'dynamodb',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        
        # Lister les tables pour vérifier la connexion
        response = dynamodb.list_tables()
        tables = response.get('TableNames', [])
        
        logger.info(f"Connexion à DynamoDB réussie avec boto3!")
        logger.info(f"Tables disponibles: {', '.join(tables) if tables else 'Aucune table'}")
        
        # Méthode 2: Utiliser PynamoDB
        connection = Connection(
            region=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        
        # Vérifier la connexion en listant les tables
        pynamo_tables = list(connection.list_tables())
        
        logger.info(f"Connexion à DynamoDB réussie avec PynamoDB!")
        logger.info(f"Tables disponibles: {', '.join(pynamo_tables) if pynamo_tables else 'Aucune table'}")
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la connexion à DynamoDB: {str(e)}")
        return False

def main():
    """Fonction principale"""
    logger.info("Vérification de la connexion à DynamoDB...")
    
    # Vérifier les variables d'environnement
    if not check_aws_credentials():
        logger.error("Les variables d'environnement AWS ne sont pas correctement configurées.")
        return False
    
    # Vérifier la connexion à DynamoDB
    if not check_dynamodb_connection():
        logger.error("Impossible de se connecter à DynamoDB.")
        return False
    
    logger.info("Connexion à DynamoDB réussie!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)