"""
Module pour la fonctionnalité API Marketplace:
- Store d'extensions métier
- Connecteurs personnalisés
- Intégrations tierces
- Templates d'automatisation
"""
import logging
import os
import json
import uuid
from datetime import datetime
import random
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

from models import User, db
from models_marketplace import (
    MarketplaceExtension, ExtensionVersion, ExtensionInstallation, 
    ExtensionReview, ApiConnection, AutomationTemplate, AutomationInstance
)
from language import get_text as _
from s3_storage import S3Storage

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Création du blueprint
marketplace_bp = Blueprint('marketplace', __name__, url_prefix='/marketplace')

# Configuration des dossiers
TEMP_FOLDER = os.path.join('static', 'temp', 'marketplace')
os.makedirs(TEMP_FOLDER, exist_ok=True)

# Fonction pour initialiser les données de démonstration
def init_marketplace_data():
    """Initialise les données de démonstration pour le module API Marketplace si nécessaire"""
    # Vérifier si des données existent déjà
    extensions_count = MarketplaceExtension.query.count()
    if extensions_count > 0:
        logger.info(f"Des données existent déjà dans le Marketplace ({extensions_count} extensions).")
        return
    
    logger.info("Initialisation des données du Marketplace API...")
    
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
            'description': "Utilisez l'intelligence artificielle pour créer des prévisions budgétaires précises basées sur vos données historiques et les tendances du marché.",
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
            'description': "Création automatisée de campagnes d'emails marketing personnalisées avec analyse des performances et optimisation des taux d'ouverture.",
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
            for i in range(2):
                rating = 4 + (i % 2)  # Alternance entre 4 et 5 étoiles
                review = ExtensionReview(
                    user_id=admin_user.id,
                    extension_id=extension.id,
                    rating=rating,
                    title=f"Très bonne extension" if rating == 5 else "Bonne extension",
                    comment=f"Cette extension a vraiment amélioré mon travail quotidien.",
                    created_at=datetime.utcnow()
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

# Configuration S3
BUCKET_NAME_PREFIX = os.environ.get('BUCKET_NAME_PREFIX', 'ia-solution')


def init_app(app):
    """Initialiser les routes API Marketplace pour l'application Flask"""
    app.register_blueprint(marketplace_bp)
    
    # Ajout des modèles au contexte de l'application
    with app.app_context():
        db.create_all()
        # Initialiser les données de démonstration
        init_marketplace_data()


@marketplace_bp.route('/')
def marketplace_home():
    """Page principale du marketplace d'extensions"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first() if username else None
    
    # Récupérer les extensions populaires
    featured_extensions = MarketplaceExtension.query.filter_by(
        is_featured=True, is_published=True
    ).order_by(MarketplaceExtension.average_rating.desc()).limit(4).all()
    
    # Récupérer les extensions par catégorie
    extensions_by_category = {}
    
    # Définir les catégories avec des informations supplémentaires pour l'affichage
    all_categories = [
        {'slug': 'business', 'name': _('marketplace_category_business', 'Business'), 
         'icon': 'fas fa-briefcase', 'description': _('marketplace_category_business_desc', 'Solutions pour votre entreprise')},
        {'slug': 'finance', 'name': _('marketplace_category_finance', 'Finance'), 
         'icon': 'fas fa-chart-line', 'description': _('marketplace_category_finance_desc', 'Outils financiers et comptables')},
        {'slug': 'marketing', 'name': _('marketplace_category_marketing', 'Marketing'), 
         'icon': 'fas fa-bullhorn', 'description': _('marketplace_category_marketing_desc', 'Outils pour vos campagnes marketing')},
        {'slug': 'productivity', 'name': _('marketplace_category_productivity', 'Productivité'), 
         'icon': 'fas fa-tasks', 'description': _('marketplace_category_productivity_desc', 'Améliorez votre efficacité')},
        {'slug': 'communication', 'name': _('marketplace_category_communication', 'Communication'), 
         'icon': 'fas fa-comments', 'description': _('marketplace_category_communication_desc', 'Solutions de communication')},
        {'slug': 'analytics', 'name': _('marketplace_category_analytics', 'Analytique'), 
         'icon': 'fas fa-chart-bar', 'description': _('marketplace_category_analytics_desc', 'Analysez vos données')},
        {'slug': 'integration', 'name': _('marketplace_category_integration', 'Intégration'), 
         'icon': 'fas fa-plug', 'description': _('marketplace_category_integration_desc', 'Connectez vos outils préférés')}
    ]
    
    categories = [cat['slug'] for cat in all_categories]
    
    for category in categories:
        extensions = MarketplaceExtension.query.filter_by(
            category=category, is_published=True
        ).order_by(MarketplaceExtension.downloads_count.desc()).limit(4).all()
        
        if extensions:
            extensions_by_category[category] = extensions
    
    # Récupérer les extensions installées par l'utilisateur
    user_extensions = []
    if user:
        installations = ExtensionInstallation.query.filter_by(
            user_id=user.id, is_active=True
        ).all()
        
        for installation in installations:
            user_extensions.append({
                'extension': installation.extension,
                'installed_version': installation.version,
                'installation_date': installation.installation_date
            })
    
    # Récupérer les templates d'automatisation populaires
    # Comme il n'y a pas d'attribut popularity_score, nous utilisons is_featured et created_at
    popular_templates = AutomationTemplate.query.join(MarketplaceExtension).filter(
        MarketplaceExtension.is_published == True
    ).order_by(AutomationTemplate.is_featured.desc(), AutomationTemplate.created_at.desc()).limit(4).all()
    
    # Import du module language pour la traduction
    import language as lang
    
    return render_template(
        'marketplace/index.html',
        is_authenticated=user is not None,
        user=user,
        featured_extensions=featured_extensions,
        extensions_by_category=extensions_by_category,
        user_extensions=user_extensions,
        categories=all_categories,
        popular_templates=popular_templates,
        language=lang,
        _=_  # Passer la fonction de traduction
    )


@marketplace_bp.route('/extensions')
def list_extensions():
    """Liste toutes les extensions disponibles"""
    # Récupérer les extensions publiées
    extensions = MarketplaceExtension.query.filter_by(is_published=True).all()
    
    # Import du module language pour la traduction
    import language as lang
    
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first() if username else None
    
    # Utiliser notre template simplifié au lieu du template complexe
    return render_template(
        'marketplace/extensions/simple.html',
        is_authenticated=user is not None,
        user=user,
        extensions=extensions,
        language=lang,
        _=_  # Passer la fonction de traduction
    )


@marketplace_bp.route('/extensions/<string:slug>')
def view_extension(slug):
    """Afficher les détails d'une extension"""
    extension = MarketplaceExtension.query.filter_by(slug=slug).first_or_404()
    
    # Récupérer les versions
    versions = ExtensionVersion.query.filter_by(extension_id=extension.id).order_by(ExtensionVersion.published_at.desc()).all()
    
    # Récupérer les avis
    reviews = ExtensionReview.query.filter_by(extension_id=extension.id, is_approved=True).order_by(ExtensionReview.created_at.desc()).all()
    
    # Vérifier si l'utilisateur a déjà installé cette extension
    is_installed = False
    user_installation = None
    if session.get('username'):
        user = User.query.filter_by(username=session.get('username')).first()
        if user:
            user_installation = ExtensionInstallation.query.filter_by(
                user_id=user.id, extension_id=extension.id, is_active=True
            ).first()
            is_installed = user_installation is not None
    
    # Récupérer les extensions similaires
    similar_extensions = MarketplaceExtension.query.filter(
        MarketplaceExtension.category == extension.category,
        MarketplaceExtension.id != extension.id,
        MarketplaceExtension.is_published == True
    ).order_by(MarketplaceExtension.downloads_count.desc()).limit(3).all()
    
    # Import du module language pour la traduction
    import language as lang
    
    return render_template(
        'marketplace/extensions/view.html',
        extension=extension,
        versions=versions,
        reviews=reviews,
        is_installed=is_installed,
        user_installation=user_installation,
        similar_extensions=similar_extensions,
        language=lang,
        _=_  # Passer la fonction de traduction
    )


@marketplace_bp.route('/extensions/<string:slug>/install', methods=['POST'])
@login_required
def install_extension(slug):
    """Installer une extension"""
    extension = MarketplaceExtension.query.filter_by(slug=slug).first_or_404()
    
    # Vérifier si l'extension est déjà installée
    existing_installation = ExtensionInstallation.query.filter_by(
        user_id=current_user.id, extension_id=extension.id, is_active=True
    ).first()
    
    if existing_installation:
        flash(_('marketplace_extension_already_installed', 'Cette extension est déjà installée.'), 'warning')
        return redirect(url_for('marketplace.view_extension', slug=slug))
    
    # Récupérer la dernière version
    latest_version = ExtensionVersion.query.filter_by(
        extension_id=extension.id, is_active=True
    ).order_by(ExtensionVersion.published_at.desc()).first()
    
    if not latest_version:
        flash(_('marketplace_no_versions_available', 'Aucune version disponible pour cette extension.'), 'error')
        return redirect(url_for('marketplace.view_extension', slug=slug))
    
    # Créer l'installation
    installation = ExtensionInstallation(
        user_id=current_user.id,
        extension_id=extension.id,
        version=latest_version.version_number,
        installation_date=datetime.utcnow(),
        is_active=True
    )
    
    try:
        db.session.add(installation)
        
        # Mettre à jour le compteur de téléchargements
        extension.downloads_count += 1
        
        db.session.commit()
        flash(_('marketplace_extension_installed', 'Extension installée avec succès !'), 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'installation de l'extension: {str(e)}")
        flash(_('marketplace_installation_error', 'Une erreur est survenue lors de l\'installation.'), 'error')
    
    return redirect(url_for('marketplace.view_extension', slug=slug))


@marketplace_bp.route('/extensions/<string:slug>/uninstall', methods=['POST'])
@login_required
def uninstall_extension(slug):
    """Désinstaller une extension"""
    extension = MarketplaceExtension.query.filter_by(slug=slug).first_or_404()
    
    # Trouver l'installation
    installation = ExtensionInstallation.query.filter_by(
        user_id=current_user.id, extension_id=extension.id, is_active=True
    ).first()
    
    if not installation:
        flash(_('marketplace_extension_not_installed', 'Cette extension n\'est pas installée.'), 'warning')
        return redirect(url_for('marketplace.view_extension', slug=slug))
    
    try:
        # Désactiver l'installation
        installation.is_active = False
        
        db.session.commit()
        flash(_('marketplace_extension_uninstalled', 'Extension désinstallée avec succès.'), 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la désinstallation de l'extension: {str(e)}")
        flash(_('marketplace_uninstallation_error', 'Une erreur est survenue lors de la désinstallation.'), 'error')
    
    return redirect(url_for('marketplace.view_extension', slug=slug))


@marketplace_bp.route('/search')
def search():
    """Recherche globale dans le marketplace"""
    q = request.args.get('q', '')
    
    if not q:
        # Si pas de requête, rediriger vers la page d'accueil du marketplace
        return redirect(url_for('marketplace.marketplace_home'))
    
    # Rechercher les extensions
    search_term = f"%{q}%"
    extensions = MarketplaceExtension.query.filter(
        db.or_(
            MarketplaceExtension.name.ilike(search_term),
            MarketplaceExtension.description.ilike(search_term),
            MarketplaceExtension.short_description.ilike(search_term)
        ),
        MarketplaceExtension.is_published == True
    ).all()
    
    # Rechercher les templates d'automatisation
    templates = AutomationTemplate.query.filter(
        db.or_(
            AutomationTemplate.name.ilike(search_term),
            AutomationTemplate.description.ilike(search_term)
        )
    ).all()
    
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first() if username else None
    
    # Import du module language pour la traduction
    import language as lang
    
    return render_template(
        'marketplace/search_results.html',
        is_authenticated=user is not None,
        user=user,
        query=q,
        extensions=extensions,
        templates=templates,
        language=lang,
        _=_  # Passer la fonction de traduction
    )


@marketplace_bp.route('/extensions/<string:slug>/review', methods=['POST'])
@login_required
def submit_review(slug):
    """Soumettre un avis sur une extension"""
    extension = MarketplaceExtension.query.filter_by(slug=slug).first_or_404()
    
    # Vérifier si l'utilisateur a déjà laissé un avis
    existing_review = ExtensionReview.query.filter_by(
        user_id=current_user.id, extension_id=extension.id
    ).first()
    
    rating = int(request.form.get('rating', 0))
    title = request.form.get('title', '')
    comment = request.form.get('comment', '')
    
    if rating < 1 or rating > 5:
        flash(_('marketplace_invalid_rating', 'Veuillez fournir une note valide (1-5).'), 'error')
        return redirect(url_for('marketplace.view_extension', slug=slug))
    
    try:
        if existing_review:
            # Mettre à jour l'avis existant
            existing_review.rating = rating
            existing_review.title = title
            existing_review.comment = comment
            existing_review.updated_at = datetime.utcnow()
        else:
            # Créer un nouvel avis
            review = ExtensionReview(
                user_id=current_user.id,
                extension_id=extension.id,
                rating=rating,
                title=title,
                comment=comment
            )
            db.session.add(review)
        
        # Mettre à jour la note moyenne de l'extension
        reviews = ExtensionReview.query.filter_by(extension_id=extension.id).all()
        total_rating = sum(review.rating for review in reviews)
        if reviews:
            extension.average_rating = total_rating / len(reviews)
        
        db.session.commit()
        flash(_('marketplace_review_submitted', 'Votre avis a été soumis avec succès.'), 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la soumission de l'avis: {str(e)}")
        flash(_('marketplace_review_error', 'Une erreur est survenue lors de la soumission de votre avis.'), 'error')
    
    return redirect(url_for('marketplace.view_extension', slug=slug))


@marketplace_bp.route('/api-connections')
@login_required
def list_api_connections():
    """Liste les connexions API de l'utilisateur"""
    connections = ApiConnection.query.filter_by(user_id=current_user.id).all()
    
    # Import du module language pour la traduction
    import language as lang
    
    return render_template(
        'marketplace/api_connections/list.html',
        connections=connections,
        language=lang,
        _=_  # Passer la fonction de traduction
    )


@marketplace_bp.route('/api-connections/create', methods=['GET', 'POST'])
@login_required
def create_api_connection():
    """Créer une nouvelle connexion API"""
    # Récupérer les extensions de type connector/integration
    connector_extensions = MarketplaceExtension.query.filter(
        MarketplaceExtension.extension_type.in_(['connector', 'integration']),
        MarketplaceExtension.is_published == True
    ).all()
    
    if request.method == 'POST':
        extension_id = request.form.get('extension_id')
        name = request.form.get('name')
        description = request.form.get('description', '')
        api_key = request.form.get('api_key', '')
        endpoint_url = request.form.get('endpoint_url', '')
        
        # Validation des champs requis
        if not all([extension_id, name]):
            flash(_('marketplace_required_fields', 'Veuillez remplir tous les champs obligatoires.'), 'error')
            return render_template(
                'marketplace/api_connections/form.html',
                extensions=connector_extensions
            )
        
        # Convertir les entrées en types appropriés
        try:
            extension_id = int(extension_id)
        except ValueError:
            flash(_('marketplace_invalid_extension', 'Extension invalide.'), 'error')
            return render_template(
                'marketplace/api_connections/form.html',
                extensions=connector_extensions
            )
        
        # Vérifier que l'extension existe
        extension = MarketplaceExtension.query.get(extension_id)
        if not extension:
            flash(_('marketplace_extension_not_found', 'Extension introuvable.'), 'error')
            return render_template(
                'marketplace/api_connections/form.html',
                extensions=connector_extensions
            )
        
        # Créer la connexion API
        connection = ApiConnection(
            user_id=current_user.id,
            extension_id=extension_id,
            name=name,
            description=description,
            api_key=api_key,  # En production, cela devrait être crypté
            endpoint_url=endpoint_url,
            connection_status='pending'
        )
        
        try:
            db.session.add(connection)
            db.session.commit()
            flash(_('marketplace_connection_created', 'Connexion API créée avec succès.'), 'success')
            return redirect(url_for('marketplace.list_api_connections'))
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la création de la connexion API: {str(e)}")
            flash(_('marketplace_connection_error', 'Une erreur est survenue lors de la création de la connexion.'), 'error')
    
    return render_template(
        'marketplace/api_connections/form.html',
        extensions=connector_extensions
    )


@marketplace_bp.route('/api-connections/<int:connection_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_api_connection(connection_id):
    """Modifier une connexion API existante"""
    connection = ApiConnection.query.filter_by(id=connection_id, user_id=current_user.id).first_or_404()
    
    # Récupérer les extensions de type connector/integration
    connector_extensions = MarketplaceExtension.query.filter(
        MarketplaceExtension.extension_type.in_(['connector', 'integration']),
        MarketplaceExtension.is_published == True
    ).all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        api_key = request.form.get('api_key', '')
        endpoint_url = request.form.get('endpoint_url', '')
        
        # Validation des champs requis
        if not name:
            flash(_('marketplace_required_fields', 'Veuillez remplir tous les champs obligatoires.'), 'error')
            return render_template(
                'marketplace/api_connections/form.html',
                connection=connection,
                extensions=connector_extensions
            )
        
        # Mettre à jour la connexion
        connection.name = name
        connection.description = description
        if api_key:  # Mettre à jour seulement si fourni
            connection.api_key = api_key  # En production, cela devrait être crypté
        connection.endpoint_url = endpoint_url
        connection.connection_status = 'pending'  # Réinitialiser le statut car les informations ont changé
        
        try:
            db.session.commit()
            flash(_('marketplace_connection_updated', 'Connexion API mise à jour avec succès.'), 'success')
            return redirect(url_for('marketplace.list_api_connections'))
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la mise à jour de la connexion API: {str(e)}")
            flash(_('marketplace_connection_update_error', 'Une erreur est survenue lors de la mise à jour de la connexion.'), 'error')
    
    return render_template(
        'marketplace/api_connections/form.html',
        connection=connection,
        extensions=connector_extensions
    )


@marketplace_bp.route('/api-connections/<int:connection_id>/delete', methods=['POST'])
@login_required
def delete_api_connection(connection_id):
    """Supprimer une connexion API"""
    connection = ApiConnection.query.filter_by(id=connection_id, user_id=current_user.id).first_or_404()
    
    try:
        db.session.delete(connection)
        db.session.commit()
        flash(_('marketplace_connection_deleted', 'Connexion API supprimée avec succès.'), 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la suppression de la connexion API: {str(e)}")
        flash(_('marketplace_connection_delete_error', 'Une erreur est survenue lors de la suppression de la connexion.'), 'error')
    
    return redirect(url_for('marketplace.list_api_connections'))


@marketplace_bp.route('/api-connections/<int:connection_id>/test', methods=['POST'])
@login_required
def test_api_connection(connection_id):
    """Tester une connexion API"""
    connection = ApiConnection.query.filter_by(id=connection_id, user_id=current_user.id).first_or_404()
    
    # Simulation d'un test de connexion
    # En production, cela devrait réellement tester la connexion avec l'API
    success = random.choice([True, False])
    
    if success:
        connection.connection_status = 'active'
        connection.error_message = None
        connection.last_connected = datetime.utcnow()
        flash(_('marketplace_connection_test_success', 'Test de connexion réussi.'), 'success')
    else:
        connection.connection_status = 'error'
        connection.error_message = "Erreur de connexion simulée. Vérifiez vos identifiants."
        flash(_('marketplace_connection_test_error', 'Échec du test de connexion. Vérifiez vos identifiants.'), 'error')
    
    try:
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erreur lors du test de la connexion API: {str(e)}")
        flash(_('marketplace_connection_test_db_error', 'Une erreur est survenue lors du test.'), 'error')
    
    return redirect(url_for('marketplace.list_api_connections'))


@marketplace_bp.route('/automation-templates')
def list_automation_templates():
    """Liste les templates d'automatisation disponibles"""
    # Récupérer les paramètres de filtre
    category = request.args.get('category', '')
    difficulty = request.args.get('difficulty', '')
    search = request.args.get('search', '')
    
    # Construire la requête
    query = AutomationTemplate.query.join(MarketplaceExtension).filter(
        MarketplaceExtension.is_published == True
    )
    
    if category:
        query = query.filter(AutomationTemplate.category == category)
    
    if difficulty:
        query = query.filter(AutomationTemplate.difficulty_level == difficulty)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (AutomationTemplate.name.ilike(search_term)) | 
            (AutomationTemplate.description.ilike(search_term))
        )
    
    # Récupérer les résultats
    templates = query.all()
    
    # Récupérer toutes les catégories pour les filtres
    all_categories = db.session.query(AutomationTemplate.category).distinct().all()
    all_categories = [cat[0] for cat in all_categories]
    
    # Difficultés pour les filtres
    difficulties = ['beginner', 'intermediate', 'advanced']
    
    # Import du module language pour la traduction
    import language as lang
    
    return render_template(
        'marketplace/automation/list_templates.html',
        templates=templates,
        categories=all_categories,
        difficulties=difficulties,
        current_category=category,
        current_difficulty=difficulty,
        current_search=search,
        language=lang,
        _=_  # Passer la fonction de traduction
    )


@marketplace_bp.route('/automation-templates/<int:template_id>')
def view_automation_template(template_id):
    """Afficher les détails d'un template d'automatisation"""
    template = AutomationTemplate.query.filter_by(id=template_id).first_or_404()
    
    # Vérifier que l'extension associée est publiée
    if not template.extension.is_published:
        return redirect(url_for('marketplace.list_automation_templates'))
    
    # Récupérer les instances créées par l'utilisateur pour ce template
    user_instances = []
    if session.get('username'):
        user = User.query.filter_by(username=session.get('username')).first()
        if user:
            user_instances = AutomationInstance.query.filter_by(
                user_id=user.id, template_id=template.id
            ).all()
    
    # Import du module language pour la traduction
    import language as lang
    
    return render_template(
        'marketplace/automation/view_template.html',
        template=template,
        user_instances=user_instances,
        language=lang,
        _=_  # Passer la fonction de traduction
    )


@marketplace_bp.route('/automation-instances')
@login_required
def list_automation_instances():
    """Liste les instances d'automatisation de l'utilisateur"""
    instances = AutomationInstance.query.filter_by(user_id=current_user.id).all()
    
    # Import du module language pour la traduction
    import language as lang
    
    return render_template(
        'marketplace/automation/list_instances.html',
        instances=instances,
        language=lang,
        _=_  # Passer la fonction de traduction
    )


@marketplace_bp.route('/automation-templates/<int:template_id>/create-instance', methods=['GET', 'POST'])
@login_required
def create_automation_instance(template_id):
    """Créer une nouvelle instance d'automatisation à partir d'un template"""
    template = AutomationTemplate.query.filter_by(id=template_id).first_or_404()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        # Récupérer les données de configuration du formulaire
        # Dans un cas réel, cela dépendrait du schéma du template
        config_data = {}
        for key, value in request.form.items():
            if key.startswith('config_'):
                field_name = key[7:]  # Retirer le préfixe 'config_'
                config_data[field_name] = value
        
        # Validation des champs requis
        if not name:
            flash(_('marketplace_required_fields', 'Veuillez remplir tous les champs obligatoires.'), 'error')
            return render_template(
                'marketplace/automation/instance_form.html',
                template=template
            )
        
        # Créer l'instance
        instance = AutomationInstance(
            user_id=current_user.id,
            template_id=template.id,
            name=name,
            description=description,
            configuration=json.dumps(config_data),
            status='active'
        )
        
        try:
            db.session.add(instance)
            db.session.commit()
            flash(_('marketplace_instance_created', 'Instance d\'automatisation créée avec succès.'), 'success')
            return redirect(url_for('marketplace.list_automation_instances'))
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la création de l'instance d'automatisation: {str(e)}")
            flash(_('marketplace_instance_error', 'Une erreur est survenue lors de la création de l\'instance.'), 'error')
    
    return render_template(
        'marketplace/automation/instance_form.html',
        template=template
    )


@marketplace_bp.route('/automation-instances/<int:instance_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_automation_instance(instance_id):
    """Modifier une instance d'automatisation existante"""
    instance = AutomationInstance.query.filter_by(id=instance_id, user_id=current_user.id).first_or_404()
    template = instance.template
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        # Récupérer les données de configuration du formulaire
        config_data = {}
        for key, value in request.form.items():
            if key.startswith('config_'):
                field_name = key[7:]  # Retirer le préfixe 'config_'
                config_data[field_name] = value
        
        # Validation des champs requis
        if not name:
            flash(_('marketplace_required_fields', 'Veuillez remplir tous les champs obligatoires.'), 'error')
            return render_template(
                'marketplace/automation/instance_form.html',
                instance=instance,
                template=template
            )
        
        # Mettre à jour l'instance
        instance.name = name
        instance.description = description
        instance.configuration = json.dumps(config_data)
        
        try:
            db.session.commit()
            flash(_('marketplace_instance_updated', 'Instance d\'automatisation mise à jour avec succès.'), 'success')
            return redirect(url_for('marketplace.list_automation_instances'))
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la mise à jour de l'instance d'automatisation: {str(e)}")
            flash(_('marketplace_instance_update_error', 'Une erreur est survenue lors de la mise à jour de l\'instance.'), 'error')
    
    return render_template(
        'marketplace/automation/instance_form.html',
        instance=instance,
        template=template
    )


@marketplace_bp.route('/automation-instances/<int:instance_id>/toggle', methods=['POST'])
@login_required
def toggle_automation_instance(instance_id):
    """Activer/désactiver une instance d'automatisation"""
    instance = AutomationInstance.query.filter_by(id=instance_id, user_id=current_user.id).first_or_404()
    
    # Inverser le statut
    if instance.status == 'active':
        instance.status = 'paused'
        message = _('marketplace_instance_paused', 'Instance d\'automatisation mise en pause.')
    else:
        instance.status = 'active'
        message = _('marketplace_instance_activated', 'Instance d\'automatisation activée.')
    
    try:
        db.session.commit()
        flash(message, 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erreur lors du changement de statut de l'instance d'automatisation: {str(e)}")
        flash(_('marketplace_instance_toggle_error', 'Une erreur est survenue lors du changement de statut.'), 'error')
    
    return redirect(url_for('marketplace.list_automation_instances'))


@marketplace_bp.route('/automation-instances/<int:instance_id>/delete', methods=['POST'])
@login_required
def delete_automation_instance(instance_id):
    """Supprimer une instance d'automatisation"""
    instance = AutomationInstance.query.filter_by(id=instance_id, user_id=current_user.id).first_or_404()
    
    try:
        db.session.delete(instance)
        db.session.commit()
        flash(_('marketplace_instance_deleted', 'Instance d\'automatisation supprimée avec succès.'), 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la suppression de l'instance d'automatisation: {str(e)}")
        flash(_('marketplace_instance_delete_error', 'Une erreur est survenue lors de la suppression de l\'instance.'), 'error')
    
    return redirect(url_for('marketplace.list_automation_instances'))


@marketplace_bp.route('/my-extensions')
@login_required
def my_extensions():
    """Afficher les extensions installées par l'utilisateur"""
    installations = ExtensionInstallation.query.filter_by(
        user_id=current_user.id, is_active=True
    ).all()
    
    # Import du module language pour la traduction
    import language as lang
    
    return render_template(
        'marketplace/extensions/my_extensions.html',
        installations=installations,
        language=lang,
        _=_  # Passer la fonction de traduction
    )


@marketplace_bp.route('/developer/dashboard')
@login_required
def developer_dashboard():
    """Tableau de bord pour les développeurs d'extensions"""
    # Récupérer les extensions développées par l'utilisateur
    extensions = MarketplaceExtension.query.filter_by(developer_id=current_user.id).all()
    
    # Statistiques
    total_downloads = sum(ext.downloads_count for ext in extensions)
    avg_rating = sum(ext.average_rating for ext in extensions if ext.average_rating > 0) / len([ext for ext in extensions if ext.average_rating > 0]) if any(ext.average_rating > 0 for ext in extensions) else 0
    
    return render_template(
        'marketplace/developer/dashboard.html',
        extensions=extensions,
        total_downloads=total_downloads,
        avg_rating=avg_rating
    )


@marketplace_bp.route('/developer/extensions/create', methods=['GET', 'POST'])
@login_required
def create_extension():
    """Créer une nouvelle extension"""
    if request.method == 'POST':
        name = request.form.get('name')
        slug = request.form.get('slug')
        description = request.form.get('description')
        short_description = request.form.get('short_description')
        category = request.form.get('category')
        subcategory = request.form.get('subcategory')
        extension_type = request.form.get('extension_type')
        price_type = request.form.get('price_type')
        price = request.form.get('price') if price_type == 'paid' else None
        
        # Validation des champs requis
        required_fields = [name, slug, description, category, extension_type, price_type]
        if not all(required_fields):
            flash(_('marketplace_required_fields', 'Veuillez remplir tous les champs obligatoires.'), 'error')
            return render_template('marketplace/developer/extension_form.html')
        
        # Conversion des types
        if price:
            try:
                price = float(price)
            except ValueError:
                flash(_('marketplace_invalid_price', 'Prix invalide.'), 'error')
                return render_template('marketplace/developer/extension_form.html')
        
        # Vérifier si le slug est unique
        if MarketplaceExtension.query.filter_by(slug=slug).first():
            flash(_('marketplace_slug_exists', 'Ce slug est déjà utilisé.'), 'error')
            return render_template('marketplace/developer/extension_form.html')
        
        # Créer l'extension
        extension = MarketplaceExtension(
            name=name,
            slug=slug,
            description=description,
            short_description=short_description,
            developer_id=current_user.id,
            category=category,
            subcategory=subcategory,
            extension_type=extension_type,
            price_type=price_type,
            price=price,
            is_published=False  # Par défaut, non publiée
        )
        
        try:
            db.session.add(extension)
            db.session.commit()
            flash(_('marketplace_extension_created', 'Extension créée avec succès.'), 'success')
            return redirect(url_for('marketplace.developer_dashboard'))
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la création de l'extension: {str(e)}")
            flash(_('marketplace_extension_creation_error', 'Une erreur est survenue lors de la création de l\'extension.'), 'error')
    
    return render_template('marketplace/developer/extension_form.html')


# Route de recherche globale dans le marketplace (déjà implémentée ci-dessus)


@marketplace_bp.route('/developer')
@login_required
def developer_portal():
    """Portail des développeurs d'extensions"""
    # Récupérer les extensions développées par l'utilisateur
    extensions = MarketplaceExtension.query.filter_by(developer_id=current_user.id).all()
    
    # Import du module language pour la traduction
    import language as lang
    
    return render_template(
        'marketplace/developer/portal.html',
        extensions=extensions,
        language=lang,
        _=_  # Passer la fonction de traduction
    )

# Routes supplémentaires pour les développeurs d'extensions
# - Gestion des versions
# - Statistiques et analytiques
# - Gestion des paiements
# - etc.