"""
Script d'initialisation pour configurer les tables DynamoDB et charger des données d'exemple
"""

import os
import sys
import uuid
import logging
from datetime import datetime, timedelta
from decimal import Decimal

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from dynamo_models import (
        User, BusinessReport, Transaction, CashflowPrediction, 
        SubscriptionPlan, ModuleCategory, Module, ModuleReview, 
        ModuleInstallation, MarketingContent, EditorialCalendarEvent,
        BusinessProcess, BusinessPrediction, ModuleVersion,
        TransactionCategory, setup_tables
    )
except ImportError as e:
    logger.error(f"Erreur lors de l'importation des modèles: {e}")
    sys.exit(1)

def create_subscription_plans():
    """Crée les plans d'abonnement de base"""
    plans = [
        {
            'id': str(uuid.uuid4()),
            'name': 'Gratuit',
            'description': 'Accès limité aux fonctionnalités de base',
            'price_monthly': Decimal('0'),
            'price_yearly': Decimal('0'),
            'storage_limit_mb': Decimal('100'),
            'features': {
                'assistant_ai': True,
                'ocr_basic': True,
                'financial_reports': False,
                'marketing_ai': False,
                'process_analysis': False,
                'predictive_intelligence': False
            },
            'is_active': True
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'Standard',
            'description': 'Accès à toutes les fonctionnalités essentielles pour les petites entreprises',
            'price_monthly': Decimal('9.99'),
            'price_yearly': Decimal('99.99'),
            'storage_limit_mb': Decimal('1000'),
            'features': {
                'assistant_ai': True,
                'ocr_basic': True,
                'ocr_advanced': True,
                'financial_reports': True,
                'marketing_ai': True,
                'process_analysis': False,
                'predictive_intelligence': False
            },
            'is_active': True
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'Premium',
            'description': 'Accès complet à toutes les fonctionnalités avancées pour les PME',
            'price_monthly': Decimal('29.99'),
            'price_yearly': Decimal('299.99'),
            'storage_limit_mb': Decimal('10000'),
            'features': {
                'assistant_ai': True,
                'ocr_basic': True,
                'ocr_advanced': True,
                'financial_reports': True,
                'marketing_ai': True,
                'process_analysis': True,
                'predictive_intelligence': True
            },
            'is_active': True
        }
    ]
    
    for plan_data in plans:
        try:
            # Vérifier si le plan existe déjà
            for plan in SubscriptionPlan.scan(SubscriptionPlan.name == plan_data['name']):
                logger.info(f"Plan {plan_data['name']} existe déjà.")
                break
            else:
                # Créer le nouveau plan
                plan = SubscriptionPlan(**plan_data)
                plan.save()
                logger.info(f"Plan créé: {plan_data['name']}")
        except Exception as e:
            logger.error(f"Erreur lors de la création du plan {plan_data['name']}: {e}")
    
    return True

def create_module_categories():
    """Crée les catégories de modules"""
    categories = [
        {
            'id': str(uuid.uuid4()),
            'name': 'Finance',
            'description': 'Modules pour la gestion financière et comptable',
            'icon': 'fas fa-money-bill'
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'Marketing',
            'description': 'Modules pour le marketing et la communication',
            'icon': 'fas fa-bullhorn'
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'Productivité',
            'description': 'Modules pour améliorer l\'efficacité et la productivité',
            'icon': 'fas fa-tasks'
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'RH',
            'description': 'Modules pour la gestion des ressources humaines',
            'icon': 'fas fa-users'
        }
    ]
    
    for category_data in categories:
        try:
            # Vérifier si la catégorie existe déjà
            for category in ModuleCategory.scan(ModuleCategory.name == category_data['name']):
                logger.info(f"Catégorie {category_data['name']} existe déjà.")
                break
            else:
                # Créer la nouvelle catégorie
                category = ModuleCategory(**category_data)
                category.save()
                logger.info(f"Catégorie créée: {category_data['name']}")
        except Exception as e:
            logger.error(f"Erreur lors de la création de la catégorie {category_data['name']}: {e}")
    
    return True

def create_sample_modules():
    """Crée des modules d'exemple"""
    # Obtenir les catégories
    categories = list(ModuleCategory.scan())
    if not categories:
        logger.error("Aucune catégorie trouvée. Créez d'abord des catégories.")
        return False
    
    category_map = {category.name: category.id for category in categories}
    
    modules = [
        {
            'id': str(uuid.uuid4()),
            'name': 'Facturation Avancée',
            'short_description': 'Module de facturation avec modèles personnalisables',
            'full_description': 'Ce module offre des fonctionnalités avancées de facturation avec des modèles entièrement personnalisables, des rappels automatiques et des tableaux de bord de suivi des paiements.',
            'category_id': category_map.get('Finance'),
            'price': Decimal('0'),
            'is_official': True,
            'is_published': True,
            'average_rating': Decimal('4.5'),
            'installation_count': Decimal('158'),
            'versions': [
                ModuleVersion(
                    version_number='1.0.0',
                    release_date=datetime.now() - timedelta(days=30),
                    changes='Version initiale',
                    is_current=False
                ),
                ModuleVersion(
                    version_number='1.1.0',
                    release_date=datetime.now() - timedelta(days=7),
                    changes='Ajout de modèles supplémentaires et corrections de bugs',
                    is_current=True
                )
            ]
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'Email Marketing Pro',
            'short_description': 'Outils de création et d\'analyse de campagnes email',
            'full_description': 'Module complet pour la création, l\'envoi et l\'analyse de campagnes d\'email marketing. Inclut des modèles réactifs, des systèmes de segmentation avancés et des rapports détaillés sur les performances.',
            'category_id': category_map.get('Marketing'),
            'price': Decimal('4.99'),
            'is_official': True,
            'is_published': True,
            'average_rating': Decimal('4.2'),
            'installation_count': Decimal('87'),
            'versions': [
                ModuleVersion(
                    version_number='1.0.0',
                    release_date=datetime.now() - timedelta(days=60),
                    changes='Version initiale',
                    is_current=True
                )
            ]
        }
    ]
    
    for module_data in modules:
        try:
            # Vérifier si le module existe déjà
            for module in Module.scan(Module.name == module_data['name']):
                logger.info(f"Module {module_data['name']} existe déjà.")
                break
            else:
                # Créer le nouveau module
                module = Module(**module_data)
                module.save()
                logger.info(f"Module créé: {module_data['name']}")
        except Exception as e:
            logger.error(f"Erreur lors de la création du module {module_data['name']}: {e}")
    
    return True

def main():
    """Fonction principale pour initialiser DynamoDB"""
    try:
        # Configurer les tables
        logger.info("Configuration des tables DynamoDB...")
        results = setup_tables()
        for table, status in results.items():
            logger.info(f"Table {table}: {status}")
        
        # Créer les données d'exemple
        logger.info("Création des plans d'abonnement...")
        create_subscription_plans()
        
        logger.info("Création des catégories de modules...")
        create_module_categories()
        
        logger.info("Création des modules d'exemple...")
        create_sample_modules()
        
        logger.info("Initialisation DynamoDB terminée avec succès!")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de DynamoDB: {e}")
        return False

if __name__ == '__main__':
    main()