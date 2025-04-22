"""
Script pour migrer les données de PostgreSQL vers DynamoDB
Transfère les données des tables existantes vers les nouvelles tables DynamoDB
"""

import os
import sys
import uuid
import logging
from datetime import datetime
from decimal import Decimal

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    # Importation des modèles PostgreSQL
    from models import User as SQLUser
    from models import db as sql_db
    
    # Importer les autres modèles PostgreSQL selon les besoins
    from models_business import BusinessReport as SQLBusinessReport
    from dashboard_models import Transaction as SQLTransaction, TransactionCategory as SQLTransactionCategory
    from models_modules import ModuleCategory as SQLModuleCategory, Module as SQLModule
    from models_marketplace import MarketplaceExtension
    from models_marketing import MarketingContent as SQLMarketingContent
    from models_process import BusinessProcess as SQLBusinessProcess
    from models_predictive import BusinessPrediction as SQLBusinessPrediction
    
    # Importation des modèles DynamoDB
    from dynamo_models import (
        User, BusinessReport, Transaction, TransactionCategory, 
        CashflowPrediction, SubscriptionPlan,
        ModuleCategory, Module, ModuleVersion,
        ModuleReview, ModuleInstallation,
        MarketingContent, EditorialCalendarEvent,
        BusinessProcess, BusinessPrediction
    )
except ImportError as e:
    logger.error(f"Erreur d'importation: {e}")
    sys.exit(1)

def create_dynamo_tables():
    """Crée les tables DynamoDB nécessaires"""
    logger.info("Création des tables DynamoDB...")
    
    from dynamo_models import setup_tables
    
    # Créer les tables
    try:
        results = setup_tables(wait=True)
        for table, status in results.items():
            logger.info(f"Table {table}: {status}")
    except Exception as e:
        logger.error(f"Erreur lors de la création des tables: {e}")
        return False
    
    return True

def migrate_users():
    """Migre les utilisateurs de PostgreSQL vers DynamoDB"""
    logger.info("Migration des utilisateurs...")
    
    try:
        # Compter les utilisateurs dans PostgreSQL
        total_users = SQLUser.query.count()
        logger.info(f"Nombre total d'utilisateurs à migrer: {total_users}")
        
        migrated_count = 0
        error_count = 0
        
        # Migrer chaque utilisateur
        for sql_user in SQLUser.query.all():
            try:
                # Vérifier si l'utilisateur existe déjà dans DynamoDB
                existing_user = None
                try:
                    for user in User.scan(User.email == sql_user.email):
                        existing_user = user
                        break
                except Exception:
                    pass
                
                if existing_user:
                    logger.info(f"L'utilisateur {sql_user.email} existe déjà dans DynamoDB, mise à jour...")
                    user_id = existing_user.id
                else:
                    # Créer un nouvel ID
                    user_id = str(uuid.uuid4())
                
                # Créer/mettre à jour l'utilisateur DynamoDB
                dynamo_user = User(
                    id=user_id,
                    username=sql_user.username if hasattr(sql_user, 'username') else sql_user.email,
                    email=sql_user.email,
                    cognito_id=getattr(sql_user, 'cognito_id', f"local_{user_id}"),
                    is_admin=getattr(sql_user, 'is_admin', False),
                    is_active=getattr(sql_user, 'is_active', True),
                    language=getattr(sql_user, 'language', 'fr'),
                    profile_picture_url=getattr(sql_user, 'profile_picture_url', None),
                    subscription_status=getattr(sql_user, 'subscription_status', 'free')
                )
                
                # Convertir les dates si nécessaire
                if hasattr(sql_user, 'subscription_end_date') and sql_user.subscription_end_date:
                    dynamo_user.subscription_end_date = sql_user.subscription_end_date
                
                dynamo_user.save()
                migrated_count += 1
                
                if migrated_count % 10 == 0 or migrated_count == total_users:
                    logger.info(f"Progression: {migrated_count}/{total_users} utilisateurs migrés")
                
            except Exception as e:
                logger.error(f"Erreur lors de la migration de l'utilisateur {getattr(sql_user, 'email', 'inconnu')}: {e}")
                error_count += 1
        
        logger.info(f"Migration des utilisateurs terminée: {migrated_count} réussis, {error_count} erreurs")
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de la migration des utilisateurs: {e}")
        return False

def migrate_business_reports():
    """Migre les rapports business de PostgreSQL vers DynamoDB"""
    logger.info("Migration des rapports business...")
    
    try:
        # Compter les rapports dans PostgreSQL
        total_reports = SQLBusinessReport.query.count()
        logger.info(f"Nombre total de rapports à migrer: {total_reports}")
        
        migrated_count = 0
        error_count = 0
        
        # Migrer chaque rapport
        for sql_report in SQLBusinessReport.query.all():
            try:
                # Créer un rapport DynamoDB
                dynamo_report = BusinessReport(
                    id=str(uuid.uuid4()),
                    user_id=str(sql_report.user_id) if sql_report.user_id else None,
                    company_name=sql_report.company_name,
                    company_sector=getattr(sql_report, 'company_sector', None),
                    company_size=getattr(sql_report, 'company_size', None),
                    report_html=sql_report.report_html,
                    status=getattr(sql_report, 'status', 'completed'),
                    is_shared=getattr(sql_report, 'is_shared', False),
                    share_token=getattr(sql_report, 'share_token', None)
                )
                
                dynamo_report.save()
                migrated_count += 1
                
                if migrated_count % 10 == 0 or migrated_count == total_reports:
                    logger.info(f"Progression: {migrated_count}/{total_reports} rapports migrés")
                
            except Exception as e:
                logger.error(f"Erreur lors de la migration du rapport {getattr(sql_report, 'id', 'inconnu')}: {e}")
                error_count += 1
        
        logger.info(f"Migration des rapports business terminée: {migrated_count} réussis, {error_count} erreurs")
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de la migration des rapports business: {e}")
        return False

def migrate_transactions():
    """Migre les transactions et catégories de PostgreSQL vers DynamoDB"""
    logger.info("Migration des transactions financières...")
    
    try:
        # Migrer d'abord les catégories
        categories_map = {}  # Pour mapper les ID PostgreSQL aux ID DynamoDB
        
        # Compter les catégories dans PostgreSQL
        total_categories = SQLTransactionCategory.query.count()
        logger.info(f"Nombre total de catégories à migrer: {total_categories}")
        
        migrated_categories = 0
        error_categories = 0
        
        # Migrer chaque catégorie
        for sql_category in SQLTransactionCategory.query.all():
            try:
                # Créer une catégorie DynamoDB (comme MapAttribute pour Transaction)
                dynamo_category = TransactionCategory(
                    id=str(uuid.uuid4()),
                    name=sql_category.name,
                    type=sql_category.type,
                    color=getattr(sql_category, 'color', None),
                    icon=getattr(sql_category, 'icon', None)
                )
                
                # Stocker le mappage pour les transactions
                categories_map[sql_category.id] = dynamo_category
                migrated_categories += 1
                
            except Exception as e:
                logger.error(f"Erreur lors de la migration de la catégorie {getattr(sql_category, 'name', 'inconnue')}: {e}")
                error_categories += 1
        
        logger.info(f"Migration des catégories terminée: {migrated_categories} réussies, {error_categories} erreurs")
        
        # Maintenant migrer les transactions
        total_transactions = SQLTransaction.query.count()
        logger.info(f"Nombre total de transactions à migrer: {total_transactions}")
        
        migrated_transactions = 0
        error_transactions = 0
        
        # Migrer chaque transaction
        for sql_transaction in SQLTransaction.query.all():
            try:
                # Récupérer la catégorie correspondante
                category = None
                if sql_transaction.category_id and sql_transaction.category_id in categories_map:
                    category = categories_map[sql_transaction.category_id]
                
                # Créer une transaction DynamoDB
                dynamo_transaction = Transaction(
                    id=str(uuid.uuid4()),
                    user_id=str(sql_transaction.user_id),
                    description=sql_transaction.description,
                    amount=Decimal(str(sql_transaction.amount)),
                    category=category,
                    date=sql_transaction.date,
                    notes=getattr(sql_transaction, 'notes', None),
                    document_url=getattr(sql_transaction, 'document_url', None)
                )
                
                dynamo_transaction.save()
                migrated_transactions += 1
                
                if migrated_transactions % 10 == 0 or migrated_transactions == total_transactions:
                    logger.info(f"Progression: {migrated_transactions}/{total_transactions} transactions migrées")
                
            except Exception as e:
                logger.error(f"Erreur lors de la migration de la transaction {getattr(sql_transaction, 'id', 'inconnue')}: {e}")
                error_transactions += 1
        
        logger.info(f"Migration des transactions terminée: {migrated_transactions} réussies, {error_transactions} erreurs")
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de la migration des transactions: {e}")
        return False

def migrate_modules():
    """Migre les modules et catégories de PostgreSQL vers DynamoDB"""
    logger.info("Migration des modules...")
    
    try:
        # Migrer d'abord les catégories
        categories_map = {}  # Pour mapper les ID PostgreSQL aux ID DynamoDB
        
        # Compter les catégories dans PostgreSQL
        total_categories = SQLModuleCategory.query.count()
        logger.info(f"Nombre total de catégories de modules à migrer: {total_categories}")
        
        migrated_categories = 0
        error_categories = 0
        
        # Migrer chaque catégorie
        for sql_category in SQLModuleCategory.query.all():
            try:
                # Créer une catégorie DynamoDB
                dynamo_category = ModuleCategory(
                    id=str(uuid.uuid4()),
                    name=sql_category.name,
                    description=getattr(sql_category, 'description', None),
                    icon=getattr(sql_category, 'icon', None)
                )
                
                dynamo_category.save()
                
                # Stocker le mappage pour les modules
                categories_map[sql_category.id] = dynamo_category.id
                migrated_categories += 1
                
            except Exception as e:
                logger.error(f"Erreur lors de la migration de la catégorie {getattr(sql_category, 'name', 'inconnue')}: {e}")
                error_categories += 1
        
        logger.info(f"Migration des catégories de modules terminée: {migrated_categories} réussies, {error_categories} erreurs")
        
        # Maintenant migrer les modules
        total_modules = SQLModule.query.count()
        logger.info(f"Nombre total de modules à migrer: {total_modules}")
        
        migrated_modules = 0
        error_modules = 0
        
        # Migrer chaque module
        for sql_module in SQLModule.query.all():
            try:
                # Récupérer la catégorie correspondante
                category_id = None
                if sql_module.category_id and sql_module.category_id in categories_map:
                    category_id = categories_map[sql_module.category_id]
                
                # Créer les versions du module
                versions = []
                if hasattr(sql_module, 'versions') and sql_module.versions:
                    try:
                        for version in sql_module.versions:
                            versions.append(ModuleVersion(
                                version_number=version.version_number,
                                release_date=version.release_date,
                                changes=version.changes,
                                is_current=version.is_current
                            ))
                    except Exception as e:
                        logger.error(f"Erreur lors de la conversion des versions: {e}")
                
                # Créer un module DynamoDB
                dynamo_module = Module(
                    id=str(uuid.uuid4()),
                    name=sql_module.name,
                    short_description=getattr(sql_module, 'short_description', None),
                    full_description=getattr(sql_module, 'full_description', None),
                    category_id=category_id,
                    price=Decimal(str(getattr(sql_module, 'price', 0))),
                    icon_url=getattr(sql_module, 'icon_url', None),
                    is_official=getattr(sql_module, 'is_official', False),
                    is_published=getattr(sql_module, 'is_published', True),
                    author_id=str(sql_module.author_id) if getattr(sql_module, 'author_id', None) else None,
                    average_rating=Decimal(str(getattr(sql_module, 'average_rating', 0))),
                    versions=versions,
                    installation_count=int(getattr(sql_module, 'installation_count', 0))
                )
                
                # Gérer les listes
                if hasattr(sql_module, 'screenshot_urls') and sql_module.screenshot_urls:
                    dynamo_module.screenshot_urls = sql_module.screenshot_urls
                
                dynamo_module.save()
                migrated_modules += 1
                
                if migrated_modules % 10 == 0 or migrated_modules == total_modules:
                    logger.info(f"Progression: {migrated_modules}/{total_modules} modules migrés")
                
            except Exception as e:
                logger.error(f"Erreur lors de la migration du module {getattr(sql_module, 'name', 'inconnu')}: {e}")
                error_modules += 1
        
        logger.info(f"Migration des modules terminée: {migrated_modules} réussis, {error_modules} erreurs")
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de la migration des modules: {e}")
        return False

def migrate_marketing_content():
    """Migre le contenu marketing de PostgreSQL vers DynamoDB"""
    logger.info("Migration du contenu marketing...")
    
    try:
        # Compter le contenu dans PostgreSQL
        total_content = SQLMarketingContent.query.count()
        logger.info(f"Nombre total de contenus marketing à migrer: {total_content}")
        
        migrated_count = 0
        error_count = 0
        
        # Migrer chaque contenu marketing
        for sql_content in SQLMarketingContent.query.all():
            try:
                # Créer un contenu marketing DynamoDB
                dynamo_content = MarketingContent(
                    id=str(uuid.uuid4()),
                    user_id=str(sql_content.user_id),
                    title=sql_content.title,
                    content_type=getattr(sql_content, 'content_type', 'general'),
                    content=sql_content.content,
                    target_audience=getattr(sql_content, 'target_audience', None),
                    language=getattr(sql_content, 'language', 'fr')
                )
                
                # Gérer les tags
                if hasattr(sql_content, 'tags') and sql_content.tags:
                    try:
                        dynamo_content.tags = sql_content.tags.split(',')
                    except Exception:
                        pass
                
                dynamo_content.save()
                migrated_count += 1
                
                if migrated_count % 10 == 0 or migrated_count == total_content:
                    logger.info(f"Progression: {migrated_count}/{total_content} contenus marketing migrés")
                
            except Exception as e:
                logger.error(f"Erreur lors de la migration du contenu marketing {getattr(sql_content, 'title', 'inconnu')}: {e}")
                error_count += 1
        
        logger.info(f"Migration du contenu marketing terminée: {migrated_count} réussis, {error_count} erreurs")
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de la migration du contenu marketing: {e}")
        return False

def migrate_business_processes():
    """Migre les processus business de PostgreSQL vers DynamoDB"""
    logger.info("Migration des processus business...")
    
    try:
        # Compter les processus dans PostgreSQL
        total_processes = SQLBusinessProcess.query.count()
        logger.info(f"Nombre total de processus business à migrer: {total_processes}")
        
        migrated_count = 0
        error_count = 0
        
        # Migrer chaque processus
        for sql_process in SQLBusinessProcess.query.all():
            try:
                # Créer un processus DynamoDB
                dynamo_process = BusinessProcess(
                    id=str(uuid.uuid4()),
                    user_id=str(sql_process.user_id),
                    name=sql_process.name,
                    description=getattr(sql_process, 'description', None),
                    current_state=getattr(sql_process, 'current_state', None),
                    desired_state=getattr(sql_process, 'desired_state', None),
                    analysis_result=getattr(sql_process, 'analysis_result', None),
                    status=getattr(sql_process, 'status', 'initiated'),
                    completion_percentage=int(getattr(sql_process, 'completion_percentage', 0))
                )
                
                # Gérer les points d'optimisation
                if hasattr(sql_process, 'optimization_points') and sql_process.optimization_points:
                    try:
                        if isinstance(sql_process.optimization_points, list):
                            dynamo_process.optimization_points = sql_process.optimization_points
                        else:
                            dynamo_process.optimization_points = list(sql_process.optimization_points.split(','))
                    except Exception:
                        pass
                
                dynamo_process.save()
                migrated_count += 1
                
                if migrated_count % 10 == 0 or migrated_count == total_processes:
                    logger.info(f"Progression: {migrated_count}/{total_processes} processus business migrés")
                
            except Exception as e:
                logger.error(f"Erreur lors de la migration du processus {getattr(sql_process, 'name', 'inconnu')}: {e}")
                error_count += 1
        
        logger.info(f"Migration des processus business terminée: {migrated_count} réussis, {error_count} erreurs")
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de la migration des processus business: {e}")
        return False

def migrate_business_predictions():
    """Migre les prédictions business de PostgreSQL vers DynamoDB"""
    logger.info("Migration des prédictions business...")
    
    try:
        # Compter les prédictions dans PostgreSQL
        total_predictions = SQLBusinessPrediction.query.count()
        logger.info(f"Nombre total de prédictions business à migrer: {total_predictions}")
        
        migrated_count = 0
        error_count = 0
        
        # Migrer chaque prédiction
        for sql_prediction in SQLBusinessPrediction.query.all():
            try:
                # Créer une prédiction DynamoDB
                dynamo_prediction = BusinessPrediction(
                    id=str(uuid.uuid4()),
                    user_id=str(sql_prediction.user_id),
                    prediction_type=sql_prediction.prediction_type,
                    target_period=sql_prediction.target_period,
                    prediction_data=sql_prediction.prediction_data,
                    confidence_level=Decimal(str(getattr(sql_prediction, 'confidence_level', 0))),
                    methodology=getattr(sql_prediction, 'methodology', None),
                    created_date=getattr(sql_prediction, 'created_date', datetime.now())
                )
                
                dynamo_prediction.save()
                migrated_count += 1
                
                if migrated_count % 10 == 0 or migrated_count == total_predictions:
                    logger.info(f"Progression: {migrated_count}/{total_predictions} prédictions business migrées")
                
            except Exception as e:
                logger.error(f"Erreur lors de la migration de la prédiction {getattr(sql_prediction, 'id', 'inconnue')}: {e}")
                error_count += 1
        
        logger.info(f"Migration des prédictions business terminée: {migrated_count} réussies, {error_count} erreurs")
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de la migration des prédictions business: {e}")
        return False

def main():
    """Fonction principale pour exécuter la migration"""
    try:
        # Créer les tables DynamoDB
        if not create_dynamo_tables():
            logger.error("Échec de la création des tables DynamoDB, migration annulée.")
            return
        
        # Démarrer une session Flask pour accéder aux modèles SQLAlchemy
        from main import app
        with app.app_context():
            # Effectuer la migration pour chaque type de données
            migrate_users()
            migrate_business_reports()
            migrate_transactions()
            migrate_modules()
            migrate_marketing_content()
            migrate_business_processes()
            migrate_business_predictions()
            
            logger.info("Migration de PostgreSQL vers DynamoDB terminée avec succès!")
    
    except Exception as e:
        logger.error(f"Erreur lors de la migration: {e}")
        return False

if __name__ == "__main__":
    main()