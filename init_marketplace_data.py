"""
Script d'initialisation des données de démonstration pour le module API Marketplace.
Ce script crée des extensions, des templates d'automatisation et d'autres données
pour illustrer les fonctionnalités du marketplace.
"""
import os
import sys
import json
import logging
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError

# Ajouter le répertoire parent au path pour permettre les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from models import db, User
from models_marketplace import (
    MarketplaceExtension,
    ExtensionVersion,
    ApiConnection,
    AutomationTemplate,
    ExtensionReview
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_marketplace_data():
    """Initialise les données de démonstration pour le module API Marketplace"""
    logger.info("Initialisation des données du Marketplace API...")
    
    # Vérifier si des données existent déjà
    extensions_count = MarketplaceExtension.query.count()
    if extensions_count > 0:
        logger.info(f"Des données existent déjà dans le Marketplace ({extensions_count} extensions). Initialisation annulée.")
        return
    
    # Utiliser un utilisateur existant pour les extensions développées par l'administrateur
    # Nous utilisons l'ID 1 qui correspond à l'utilisateur principal (lecoinrdc@gmail.com)
    admin_user = User.query.get(1)
    if not admin_user:
        logger.error("Aucun utilisateur trouvé avec l'ID 1, impossible d'initialiser les données du marketplace")
        return
    logger.info(f"Utilisation de l'utilisateur {admin_user.username} (ID: {admin_user.id}) pour les extensions du marketplace")
    
    # Extensions par catégorie
    extensions_data = [
        # Catégorie Finance
        {
            'name': 'Comptabilité Automatisée',
            'slug': 'comptabilite-automatisee',
            'description': "Extension permettant l'automatisation des tâches comptables quotidiennes incluant la catégorisation des transactions, le rapprochement bancaire, et la préparation des déclarations fiscales.",
            'short_description': "Automatisez vos tâches comptables quotidiennes",
            'developer_id': admin_user.id,
            'category': 'finance',
            'subcategory': 'comptabilité',
            'extension_type': 'extension',
            'version': '1.2.0',
            'icon_url': '/static/img/marketplace/finance_icon.svg',
            'cover_image': '/static/img/marketplace/accounting_cover.jpg',
            'price_type': 'free',
            'is_published': True,
            'is_verified': True,
            'is_featured': True,
            'average_rating': 4.8,
            'downloads_count': 1250,
        },
        {
            'name': 'Prévisions Budgétaires IA',
            'slug': 'previsions-budgetaires-ia',
            'description': "Utilisez l'intelligence artificielle pour créer des prévisions budgétaires précises basées sur vos données historiques et les tendances du marché. L'extension analyse vos flux de trésorerie et propose des scénarios optimisés pour améliorer votre gestion financière.",
            'short_description': "Prévisions budgétaires basées sur l'IA",
            'developer_id': admin_user.id,
            'category': 'finance',
            'subcategory': 'prévisions',
            'extension_type': 'extension',
            'version': '2.0.1',
            'icon_url': '/static/img/marketplace/budget_icon.svg',
            'cover_image': '/static/img/marketplace/budget_cover.jpg',
            'price_type': 'paid',
            'price': 9.99,
            'currency': 'EUR',
            'is_published': True,
            'is_verified': True,
            'is_featured': True,
            'average_rating': 4.6,
            'downloads_count': 856,
        },
        
        # Catégorie Marketing
        {
            'name': 'Générateur de Campagnes Emails',
            'slug': 'generateur-campagnes-emails',
            'description': "Création automatisée de campagnes d'emails marketing personnalisées avec analyse des performances et optimisation des taux d'ouverture et de conversion. Intégration simple avec les principales plateformes d'emailing.",
            'short_description': "Créez et analysez vos campagnes d'emails",
            'developer_id': admin_user.id,
            'category': 'marketing',
            'subcategory': 'email',
            'extension_type': 'extension',
            'version': '1.5.3',
            'icon_url': '/static/img/marketplace/email_icon.svg',
            'cover_image': '/static/img/marketplace/email_cover.jpg',
            'price_type': 'free',
            'is_published': True,
            'is_verified': True,
            'is_featured': False,
            'average_rating': 4.2,
            'downloads_count': 2105,
        },
        {
            'name': 'Planificateur de Contenu Social',
            'slug': 'planificateur-contenu-social',
            'description': "Planifiez et programmez votre contenu sur les réseaux sociaux avec une interface intuitive. Analysez les performances et optimisez votre stratégie grâce aux rapports détaillés et aux recommandations personnalisées.",
            'short_description': "Gestion complète de vos réseaux sociaux",
            'developer_id': admin_user.id,
            'category': 'marketing',
            'subcategory': 'réseaux sociaux',
            'extension_type': 'extension',
            'version': '3.1.0',
            'icon_url': '/static/img/marketplace/social_icon.svg',
            'cover_image': '/static/img/marketplace/social_cover.jpg',
            'price_type': 'paid',
            'price': 14.99,
            'currency': 'EUR',
            'is_published': True,
            'is_verified': True,
            'is_featured': True,
            'average_rating': 4.7,
            'downloads_count': 1890,
        },
        
        # Catégorie RH
        {
            'name': 'Gestionnaire de Recrutement',
            'slug': 'gestionnaire-recrutement',
            'description': "Simplifiez votre processus de recrutement avec cette extension complète. Suivez les candidatures, organisez les entretiens et évaluez les candidats dans une interface unifiée. Inclut des modèles d'offres d'emploi et un système d'évaluation des compétences.",
            'short_description': "Solution complète pour votre recrutement",
            'developer_id': admin_user.id,
            'category': 'ressources humaines',
            'subcategory': 'recrutement',
            'extension_type': 'extension',
            'version': '2.2.1',
            'icon_url': '/static/img/marketplace/hr_icon.svg',
            'cover_image': '/static/img/marketplace/recruitment_cover.jpg',
            'price_type': 'paid',
            'price': 19.99,
            'currency': 'EUR',
            'is_published': True,
            'is_verified': True,
            'is_featured': False,
            'average_rating': 4.5,
            'downloads_count': 720,
        },
        
        # Catégorie CRM
        {
            'name': 'Connecteur CRM Avancé',
            'slug': 'connecteur-crm-avance',
            'description': "Intégrez vos données CRM existantes avec IA-Solution pour une vue à 360° de vos clients. Compatible avec les principales plateformes CRM comme Salesforce, HubSpot et Zoho CRM.",
            'short_description': "Synchronisez vos données CRM avec IA-Solution",
            'developer_id': admin_user.id,
            'category': 'crm',
            'subcategory': 'intégration',
            'extension_type': 'connector',
            'version': '1.0.4',
            'icon_url': '/static/img/marketplace/crm_icon.svg',
            'cover_image': '/static/img/marketplace/crm_cover.jpg',
            'price_type': 'free',
            'is_published': True,
            'is_verified': True,
            'is_featured': False,
            'average_rating': 4.3,
            'downloads_count': 1560,
        },
        
        # Catégorie Productivité
        {
            'name': 'Assistant de Rédaction IA',
            'slug': 'assistant-redaction-ia',
            'description': "Améliorez votre productivité rédactionnelle avec cet assistant alimenté par l'IA. Générez des contenus professionnels, corrigez la grammaire et le style, et adaptez le ton en fonction de votre audience.",
            'short_description': "Créez du contenu professionnel avec l'IA",
            'developer_id': admin_user.id,
            'category': 'productivité',
            'subcategory': 'rédaction',
            'extension_type': 'extension',
            'version': '2.1.5',
            'icon_url': '/static/img/marketplace/writing_icon.svg',
            'cover_image': '/static/img/marketplace/writing_cover.jpg',
            'price_type': 'paid',
            'price': 7.99,
            'currency': 'EUR',
            'is_published': True,
            'is_verified': True,
            'is_featured': True,
            'average_rating': 4.9,
            'downloads_count': 2850,
        },
    ]
    
    # Templates d'automatisation
    templates_data = [
        {
            'name': 'Rapports Financiers Hebdomadaires',
            'description': "Automatisez la génération et l'envoi de rapports financiers hebdomadaires à votre équipe. Inclut les flux de trésorerie, les ventes, et les dépenses principales.",
            'category': 'finance',
            'difficulty_level': 'beginner',
            'estimated_time_minutes': 30,
            'is_featured': True,
        },
        {
            'name': 'Suivi des Prospects et Relances',
            'description': "Workflow automatisé pour suivre les prospects, envoyer des emails de relance personnalisés et programmer des rendez-vous basés sur les interactions.",
            'category': 'ventes',
            'difficulty_level': 'intermediate',
            'estimated_time_minutes': 45,
            'is_featured': True,
        },
        {
            'name': 'Analyse de Sentiment Clients',
            'description': "Analysez automatiquement les retours clients provenant de diverses sources (emails, réseaux sociaux, formulaires) et générez des rapports d'insights.",
            'category': 'marketing',
            'difficulty_level': 'advanced',
            'estimated_time_minutes': 60,
            'is_featured': False,
        },
        {
            'name': 'Intégration des Nouveaux Employés',
            'description': "Processus d'onboarding automatisé pour les nouveaux employés: envoi de documents, configuration des accès, planification des formations et suivi de progression.",
            'category': 'ressources humaines',
            'difficulty_level': 'beginner',
            'estimated_time_minutes': 50,
            'is_featured': False,
        },
    ]
    
    # Créer les extensions
    created_extensions = []
    for ext_data in extensions_data:
        try:
            extension = MarketplaceExtension(**ext_data)
            db.session.add(extension)
            db.session.flush()  # Pour obtenir l'ID sans commit
            created_extensions.append(extension)
            
            # Créer une version pour cette extension
            version = ExtensionVersion(
                extension_id=extension.id,
                version_number=ext_data['version'],
                release_notes="Version initiale avec toutes les fonctionnalités de base.",
                download_url=f"/marketplace/download/{extension.slug}/{ext_data['version']}",
                is_active=True,
            )
            db.session.add(version)
            
            # Ajouter quelques avis
            for i in range(3):
                rating = 4 + (i % 2)  # Alternance entre 4 et 5 étoiles
                review = ExtensionReview(
                    user_id=admin_user.id,
                    extension_id=extension.id,
                    rating=rating,
                    title=f"Très bonne extension" if rating == 5 else "Bonne extension",
                    comment=f"Cette extension a vraiment amélioré mon travail quotidien. {'Je la recommande vivement!' if rating == 5 else 'Quelques améliorations seraient bienvenues.'}",
                    created_at=datetime.utcnow() - timedelta(days=i*5)
                )
                db.session.add(review)
                
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la création de l'extension {ext_data['name']}: {str(e)}")
            return
    
    # Créer les templates d'automatisation
    for i, tmpl_data in enumerate(templates_data):
        try:
            # Associer chaque template à une extension
            extension_id = created_extensions[i % len(created_extensions)].id
            
            # Définition simplifiée du workflow
            workflow_definition = {
                "steps": [
                    {
                        "id": "step1",
                        "name": "Collecte de données",
                        "type": "data_collection",
                        "config": {"source": "database"}
                    },
                    {
                        "id": "step2",
                        "name": "Traitement",
                        "type": "processing",
                        "config": {"method": "ai_analysis"}
                    },
                    {
                        "id": "step3",
                        "name": "Action finale",
                        "type": "action",
                        "config": {"action_type": "notification"}
                    }
                ],
                "connections": [
                    {"from": "step1", "to": "step2"},
                    {"from": "step2", "to": "step3"}
                ]
            }
            
            template = AutomationTemplate(
                extension_id=extension_id,
                name=tmpl_data['name'],
                description=tmpl_data['description'],
                workflow_definition=json.dumps(workflow_definition),
                category=tmpl_data['category'],
                difficulty_level=tmpl_data['difficulty_level'],
                estimated_time_minutes=tmpl_data['estimated_time_minutes'],
                is_featured=tmpl_data['is_featured']
            )
            db.session.add(template)
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la création du template {tmpl_data['name']}: {str(e)}")
            return
    
    # Valider toutes les modifications
    try:
        db.session.commit()
        logger.info(f"Initialisation des données du Marketplace terminée: {len(extensions_data)} extensions et {len(templates_data)} templates créés")
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la validation finale: {str(e)}")


if __name__ == "__main__":
    with app.app_context():
        init_marketplace_data()