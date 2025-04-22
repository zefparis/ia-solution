#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour initialiser les plans d'abonnement en USD pour la RDC
"""
import os
import sys
from models import db, SubscriptionPlan

def init_rdc_plans():
    """
    Crée ou met à jour les plans d'abonnement spécifiques à la RDC en USD
    """
    print("Initialisation des plans d'abonnement en USD pour la RDC...")
    
    # Définir les plans RDC
    rdc_plans = [
        {
            'name': 'rdc_basic',
            'display_name': 'Basique RDC',
            'price': 10.00,
            'currency': 'USD',
            'storage_limit': 1073741824,  # 1 GB
            'description': 'Plan basique pour les utilisateurs en RDC',
            'features': 'Assistant IA,OCR basique,Document scanner,Dashboard financier',
            'region': 'rdc'
        },
        {
            'name': 'rdc_standard',
            'display_name': 'Standard RDC',
            'price': 25.00,
            'currency': 'USD',
            'storage_limit': 5368709120,  # 5 GB
            'description': 'Plan standard avec plus de fonctionnalités pour les utilisateurs en RDC',
            'features': 'Assistant IA avancé,OCR avancé,Document scanner,Dashboard financier,Rapports fiscaux,Factures et devis,Consultation business',
            'region': 'rdc'
        },
        {
            'name': 'rdc_premium',
            'display_name': 'Premium RDC',
            'price': 50.00,
            'currency': 'USD',
            'storage_limit': 10737418240,  # 10 GB
            'description': 'Plan premium avec toutes les fonctionnalités pour les utilisateurs en RDC',
            'features': 'Assistant IA avancé,OCR avancé,Document scanner,Dashboard financier,Rapports fiscaux,Factures et devis,Consultation business,Prévisions financières,Support prioritaire',
            'region': 'rdc'
        }
    ]
    
    # Créer ou mettre à jour les plans
    for plan_data in rdc_plans:
        # Vérifier si le plan existe déjà
        existing_plan = SubscriptionPlan.query.filter_by(name=plan_data['name']).first()
        
        if existing_plan:
            # Mettre à jour le plan existant
            print(f"Mise à jour du plan: {plan_data['display_name']}")
            for key, value in plan_data.items():
                setattr(existing_plan, key, value)
        else:
            # Créer un nouveau plan
            print(f"Création du plan: {plan_data['display_name']}")
            new_plan = SubscriptionPlan(**plan_data)
            db.session.add(new_plan)
    
    # Enregistrer les modifications
    db.session.commit()
    print("Plans d'abonnement RDC initialisés avec succès!")

if __name__ == '__main__':
    # Importer l'application Flask pour accéder à la BD
    from main import app
    
    with app.app_context():
        init_rdc_plans()