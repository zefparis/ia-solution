#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour ajouter les colonnes 'currency' et 'region' à la table subscription_plan
"""
import os
from sqlalchemy import text

def update_subscription_plan_table():
    """
    Ajoute les colonnes currency et region à la table subscription_plan
    en utilisant des commandes SQL directes pour éviter les problèmes de migration.
    """
    from main import app
    from models import db
    
    with app.app_context():
        try:
            # Vérifier si la colonne currency existe déjà
            check_currency_sql = text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='subscription_plan' AND column_name='currency';
            """)
            result = db.session.execute(check_currency_sql)
            currency_exists = result.fetchone() is not None
            
            # Ajouter la colonne currency si elle n'existe pas
            if not currency_exists:
                print("Ajout de la colonne 'currency' à la table subscription_plan...")
                add_currency_sql = text("""
                ALTER TABLE subscription_plan ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'EUR';
                """)
                db.session.execute(add_currency_sql)
                print("Colonne 'currency' ajoutée avec succès !")
            else:
                print("La colonne 'currency' existe déjà.")
                
            # Vérifier si la colonne region existe déjà
            check_region_sql = text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='subscription_plan' AND column_name='region';
            """)
            result = db.session.execute(check_region_sql)
            region_exists = result.fetchone() is not None
            
            # Ajouter la colonne region si elle n'existe pas
            if not region_exists:
                print("Ajout de la colonne 'region' à la table subscription_plan...")
                add_region_sql = text("""
                ALTER TABLE subscription_plan ADD COLUMN region VARCHAR(10);
                """)
                db.session.execute(add_region_sql)
                print("Colonne 'region' ajoutée avec succès !")
            else:
                print("La colonne 'region' existe déjà.")
                
            # Commiter les changements
            db.session.commit()
            print("Migration terminée avec succès !")
            
        except Exception as e:
            db.session.rollback()
            print(f"Erreur lors de la migration : {str(e)}")
            raise e

if __name__ == '__main__':
    update_subscription_plan_table()