"""
Module d'Intelligence Prédictive Commerciale.

Ce module fournit des fonctionnalités d'analyse prédictive pour les ventes,
l'analyse des clients et l'optimisation des catalogues produits pour les TPE/PME.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash
from flask_login import current_user
from werkzeug.utils import secure_filename
from sqlalchemy.exc import SQLAlchemyError

from models import db
from models_predictive import (
    SalesPrediction, 
    PredictionScenario, 
    CustomerInsight, 
    ProductCatalogInsight,
    MarketTrend,
    PredictiveAlert
)
import language

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Création du blueprint
predictive_bp = Blueprint('predictive', __name__, url_prefix='/predictive')

# Constantes
ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx', 'json'}

@predictive_bp.before_request
def before_request():
    """Exécuté avant chaque requête au blueprint."""
    # Vérifier si l'utilisateur est authentifié
    if 'access_token' not in session:
        # Rediriger vers la page de connexion AWS Cognito
        return redirect(url_for('login'))

def get_translations():
    """Obtenir les traductions pour le module"""
    return {
        'title': {
            'fr': 'Intelligence Prédictive Commerciale',
            'en': 'Predictive Business Intelligence'
        },
        'dashboard': {
            'fr': 'Tableau de bord prédictif',
            'en': 'Predictive Dashboard'
        },
        'sales_predictions': {
            'fr': 'Prévisions de ventes',
            'en': 'Sales Forecasting'
        },
        'customer_insights': {
            'fr': 'Analyse des clients',
            'en': 'Customer Insights'
        },
        'product_catalog': {
            'fr': 'Optimisation du catalogue',
            'en': 'Catalog Optimization'
        },
        'market_trends': {
            'fr': 'Tendances du marché',
            'en': 'Market Trends'
        },
        'alerts': {
            'fr': 'Alertes prédictives',
            'en': 'Predictive Alerts'
        },
        'new_prediction': {
            'fr': 'Nouvelle prévision',
            'en': 'New Prediction'
        },
        'edit_prediction': {
            'fr': 'Modifier la prévision',
            'en': 'Edit Prediction'
        },
        'view_prediction': {
            'fr': 'Voir la prévision',
            'en': 'View Prediction'
        },
        'prediction_name': {
            'fr': 'Nom de la prévision',
            'en': 'Prediction Name'
        },
        'prediction_description': {
            'fr': 'Description',
            'en': 'Description'
        },
        'start_date': {
            'fr': 'Date de début',
            'en': 'Start Date'
        },
        'end_date': {
            'fr': 'Date de fin',
            'en': 'End Date'
        },
        'create': {
            'fr': 'Créer',
            'en': 'Create'
        },
        'update': {
            'fr': 'Mettre à jour',
            'en': 'Update'
        },
        'cancel': {
            'fr': 'Annuler',
            'en': 'Cancel'
        },
        'delete': {
            'fr': 'Supprimer',
            'en': 'Delete'
        },
        'confirm_delete': {
            'fr': 'Êtes-vous sûr de vouloir supprimer cette prévision ?',
            'en': 'Are you sure you want to delete this prediction?'
        },
        'optimistic': {
            'fr': 'Optimiste',
            'en': 'Optimistic'
        },
        'realistic': {
            'fr': 'Réaliste',
            'en': 'Realistic'
        },
        'pessimistic': {
            'fr': 'Pessimiste',
            'en': 'Pessimistic'
        },
        'custom': {
            'fr': 'Personnalisé',
            'en': 'Custom'
        },
        'probability': {
            'fr': 'Probabilité',
            'en': 'Probability'
        },
        'customer_name': {
            'fr': 'Nom du client',
            'en': 'Customer Name'
        },
        'development_potential': {
            'fr': 'Potentiel de développement',
            'en': 'Development Potential'
        },
        'churn_risk': {
            'fr': 'Risque de désengagement',
            'en': 'Churn Risk'
        },
        'purchase_trend': {
            'fr': 'Tendance d\'achat',
            'en': 'Purchase Trend'
        },
        'recommendations': {
            'fr': 'Recommandations',
            'en': 'Recommendations'
        },
        'customer_category': {
            'fr': 'Catégorie de client',
            'en': 'Customer Category'
        },
        'vip': {
            'fr': 'VIP',
            'en': 'VIP'
        },
        'regular': {
            'fr': 'Régulier',
            'en': 'Regular'
        },
        'occasional': {
            'fr': 'Occasionnel',
            'en': 'Occasional'
        },
        'inactive': {
            'fr': 'Inactif',
            'en': 'Inactive'
        },
        'new': {
            'fr': 'Nouveau',
            'en': 'New'
        },
        'catalog_name': {
            'fr': 'Nom de l\'analyse',
            'en': 'Analysis Name'
        },
        'trend_name': {
            'fr': 'Nom de la tendance',
            'en': 'Trend Name'
        },
        'trend_type': {
            'fr': 'Type de tendance',
            'en': 'Trend Type'
        },
        'seasonal': {
            'fr': 'Saisonnière',
            'en': 'Seasonal'
        },
        'emerging': {
            'fr': 'Émergente',
            'en': 'Emerging'
        },
        'declining': {
            'fr': 'En déclin',
            'en': 'Declining'
        },
        'impact': {
            'fr': 'Impact',
            'en': 'Impact'
        },
        'duration': {
            'fr': 'Durée estimée',
            'en': 'Estimated Duration'
        },
        'affected_categories': {
            'fr': 'Catégories concernées',
            'en': 'Affected Categories'
        },
        'alert_title': {
            'fr': 'Titre de l\'alerte',
            'en': 'Alert Title'
        },
        'alert_message': {
            'fr': 'Message',
            'en': 'Message'
        },
        'alert_type': {
            'fr': 'Type d\'alerte',
            'en': 'Alert Type'
        },
        'opportunity': {
            'fr': 'Opportunité',
            'en': 'Opportunity'
        },
        'risk': {
            'fr': 'Risque',
            'en': 'Risk'
        },
        'info': {
            'fr': 'Information',
            'en': 'Information'
        },
        'priority': {
            'fr': 'Priorité',
            'en': 'Priority'
        },
        'status': {
            'fr': 'Statut',
            'en': 'Status'
        },
        'unread': {
            'fr': 'Non lu',
            'en': 'Unread'
        },
        'read': {
            'fr': 'Lu',
            'en': 'Read'
        },
        'processed': {
            'fr': 'Traité',
            'en': 'Processed'
        },
        'ignored': {
            'fr': 'Ignoré',
            'en': 'Ignored'
        },
        'no_predictions': {
            'fr': 'Aucune prévision disponible. Créez votre première prévision !',
            'en': 'No predictions available. Create your first prediction!'
        },
        'no_customers': {
            'fr': 'Aucune analyse client disponible.',
            'en': 'No customer insights available.'
        },
        'no_catalog': {
            'fr': 'Aucune analyse de catalogue disponible.',
            'en': 'No catalog analysis available.'
        },
        'no_trends': {
            'fr': 'Aucune tendance de marché identifiée.',
            'en': 'No market trends identified.'
        },
        'no_alerts': {
            'fr': 'Aucune alerte prédictive.',
            'en': 'No predictive alerts.'
        },
        'save': {
            'fr': 'Enregistrer',
            'en': 'Save'
        },
        'back': {
            'fr': 'Retour',
            'en': 'Back'
        },
        'import_data': {
            'fr': 'Importer des données',
            'en': 'Import Data'
        },
        'export_results': {
            'fr': 'Exporter les résultats',
            'en': 'Export Results'
        },
        'generate_report': {
            'fr': 'Générer un rapport',
            'en': 'Generate Report'
        },
        'data_source': {
            'fr': 'Source de données',
            'en': 'Data Source'
        },
        'upload_file': {
            'fr': 'Télécharger un fichier',
            'en': 'Upload File'
        },
        'use_existing_data': {
            'fr': 'Utiliser les données existantes',
            'en': 'Use Existing Data'
        },
        'prediction_settings': {
            'fr': 'Paramètres de prévision',
            'en': 'Prediction Settings'
        },
        'time_period': {
            'fr': 'Période',
            'en': 'Time Period'
        },
        'forecast_horizon': {
            'fr': 'Horizon de prévision',
            'en': 'Forecast Horizon'
        },
        'granularity': {
            'fr': 'Granularité',
            'en': 'Granularity'
        },
        'daily': {
            'fr': 'Quotidienne',
            'en': 'Daily'
        },
        'weekly': {
            'fr': 'Hebdomadaire',
            'en': 'Weekly'
        },
        'monthly': {
            'fr': 'Mensuelle',
            'en': 'Monthly'
        },
        'quarterly': {
            'fr': 'Trimestrielle',
            'en': 'Quarterly'
        },
        'yearly': {
            'fr': 'Annuelle',
            'en': 'Yearly'
        },
        'scenario_settings': {
            'fr': 'Paramètres des scénarios',
            'en': 'Scenario Settings'
        },
        'include_scenario': {
            'fr': 'Inclure le scénario',
            'en': 'Include Scenario'
        },
        'submit': {
            'fr': 'Soumettre',
            'en': 'Submit'
        }
    }

def get_current_language():
    """Obtenir la langue actuelle"""
    from flask import g
    return getattr(g, 'lang', 'fr')

def get_user_id():
    """
    Obtenir l'ID numérique de l'utilisateur connecté à partir de la session.
    Retourne l'ID de la table user correspondant à l'e-mail ou username stocké dans la session.
    """
    from models import User
    
    # Récupérer l'email ou le username de la session
    user_info = session.get('user_info', {})
    email_or_username = user_info.get('sub', session.get('username', ''))
    
    if not email_or_username:
        logger.warning("Aucun identifiant utilisateur trouvé dans la session")
        return None
    
    # Chercher l'utilisateur par e-mail ou username
    try:
        user = User.query.filter((User.email == email_or_username) | 
                                (User.username == email_or_username)).first()
        
        if user:
            logger.debug(f"Utilisateur trouvé avec ID: {user.id}")
            return user.id
        else:
            logger.warning(f"Aucun utilisateur trouvé pour '{email_or_username}'")
            return None
    except Exception as e:
        logger.error(f"Erreur lors de la recherche de l'utilisateur: {str(e)}")
        return None

def init_app(app):
    """Initialiser le module d'intelligence prédictive"""
    logger.info("Initialisation du module d'Intelligence Prédictive Commerciale")
    
    app.register_blueprint(predictive_bp)
    
    # Ajouter les traductions au contexte global des templates
    @app.context_processor
    def inject_predictive_translations():
        return {'predictive_translations': get_translations(), 'current_language': get_current_language()}

@predictive_bp.route('/')
def index():
    """Page d'accueil du module d'intelligence prédictive"""
    logger.info("Affichage de la page d'accueil du module d'intelligence prédictive")
    
    lang = get_current_language()
    translations = get_translations()
    
    # Récupérer l'ID utilisateur à partir de la base de données
    user_id = get_user_id()
    
    # Récupérer les données clés pour le tableau de bord
    latest_predictions = SalesPrediction.query.filter_by(user_id=user_id).order_by(SalesPrediction.date_created.desc()).limit(5).all()
    high_potential_customers = CustomerInsight.query.filter_by(user_id=user_id).order_by(CustomerInsight.development_potential_score.desc()).limit(5).all()
    high_risk_customers = CustomerInsight.query.filter_by(user_id=user_id).order_by(CustomerInsight.churn_risk_score.desc()).limit(5).all()
    latest_trends = MarketTrend.query.filter_by(user_id=user_id).order_by(MarketTrend.date_created.desc()).limit(5).all()
    recent_alerts = PredictiveAlert.query.filter_by(user_id=user_id, status='unread').order_by(PredictiveAlert.date_created.desc()).limit(5).all()
    
    return render_template(
        'predictive/index.html',
        lang=lang,
        translations=translations,
        latest_predictions=latest_predictions,
        high_potential_customers=high_potential_customers,
        high_risk_customers=high_risk_customers,
        latest_trends=latest_trends,
        recent_alerts=recent_alerts
    )

@predictive_bp.route('/sales-predictions')

def sales_predictions():
    """Liste des prévisions de ventes"""
    logger.info("Affichage de la liste des prévisions de ventes")
    
    lang = get_current_language()
    translations = get_translations()
    
    # Récupérer l'ID utilisateur à partir de la base de données
    user_id = get_user_id()
    
    predictions = SalesPrediction.query.filter_by(user_id=user_id).order_by(SalesPrediction.date_created.desc()).all()
    
    return render_template(
        'predictive/sales_predictions.html',
        lang=lang,
        translations=translations,
        predictions=predictions
    )

@predictive_bp.route('/new-prediction', methods=['GET', 'POST'])

def new_prediction():
    """Création d'une nouvelle prévision de ventes"""
    logger.info("Page de création d'une nouvelle prévision de ventes")
    
    lang = get_current_language()
    translations = get_translations()
    user_id = get_user_id()
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
            
            # Créer la prévision de base
            prediction = SalesPrediction(
                user_id=user_id,
                name=name,
                description=description,
                start_date=start_date,
                end_date=end_date,
                status='pending',
                prediction_parameters={}
            )
            
            # Ajouter les paramètres si fournis
            if request.form.get('granularity'):
                if not prediction.prediction_parameters:
                    prediction.prediction_parameters = {}
                prediction.prediction_parameters['granularity'] = request.form.get('granularity')
            
            # Ajouter les scénarios
            db.session.add(prediction)
            db.session.flush()  # Pour obtenir l'ID de la prévision
            
            # Scénario optimiste
            if request.form.get('include_optimistic') == 'on':
                optimistic = PredictionScenario(
                    prediction_id=prediction.id,
                    name=translations['optimistic'][lang],
                    scenario_type='optimistic',
                    probability=float(request.form.get('optimistic_probability', 0.25))
                )
                db.session.add(optimistic)
            
            # Scénario réaliste
            if request.form.get('include_realistic') == 'on':
                realistic = PredictionScenario(
                    prediction_id=prediction.id,
                    name=translations['realistic'][lang],
                    scenario_type='realistic',
                    probability=float(request.form.get('realistic_probability', 0.5))
                )
                db.session.add(realistic)
            
            # Scénario pessimiste
            if request.form.get('include_pessimistic') == 'on':
                pessimistic = PredictionScenario(
                    prediction_id=prediction.id,
                    name=translations['pessimistic'][lang],
                    scenario_type='pessimistic',
                    probability=float(request.form.get('pessimistic_probability', 0.25))
                )
                db.session.add(pessimistic)
            
            db.session.commit()
            
            # Après avoir créé la prévision, lancer l'analyse en arrière-plan
            # Dans une application réelle, cela serait fait avec une tâche asynchrone (Celery, etc.)
            # generate_prediction_results.delay(prediction.id)
            
            flash('Prévision créée avec succès. L\'analyse est en cours.', 'success')
            return redirect(url_for('predictive.view_prediction', prediction_id=prediction.id))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la création de la prévision: {str(e)}")
            flash('Erreur lors de la création de la prévision. Veuillez réessayer.', 'danger')
    
    # Valeurs par défaut
    today = datetime.today().date()
    default_start = today - timedelta(days=365)  # 1 an en arrière
    default_end = today + timedelta(days=90)     # 3 mois en avant
    
    return render_template(
        'predictive/new_prediction.html',
        lang=lang,
        translations=translations,
        default_start=default_start.strftime('%Y-%m-%d'),
        default_end=default_end.strftime('%Y-%m-%d')
    )

@predictive_bp.route('/prediction/<int:prediction_id>')

def view_prediction(prediction_id):
    """Affichage d'une prévision spécifique"""
    user_id = get_user_id()
    logger.info(f"Affichage de la prévision {prediction_id}")
    
    lang = get_current_language()
    translations = get_translations()
    
    prediction = SalesPrediction.query.filter_by(id=prediction_id, user_id=user_id).first_or_404()
    scenarios = PredictionScenario.query.filter_by(prediction_id=prediction_id).all()
    
    return render_template(
        'predictive/view_prediction.html',
        lang=lang,
        translations=translations,
        prediction=prediction,
        scenarios=scenarios
    )

@predictive_bp.route('/prediction/<int:prediction_id>/edit', methods=['GET', 'POST'])

def edit_prediction(prediction_id):
    """Édition d'une prévision existante"""
    user_id = get_user_id()
    logger.info(f"Édition de la prévision {prediction_id}")
    
    lang = get_current_language()
    translations = get_translations()
    
    prediction = SalesPrediction.query.filter_by(id=prediction_id, user_id=user_id).first_or_404()
    
    if request.method == 'POST':
        try:
            prediction.name = request.form.get('name')
            prediction.description = request.form.get('description')
            prediction.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            prediction.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
            
            # Mettre à jour les paramètres
            if not prediction.prediction_parameters:
                prediction.prediction_parameters = {}
            prediction.prediction_parameters['granularity'] = request.form.get('granularity')
            
            # Mettre à jour les scénarios existants
            for scenario in prediction.scenarios:
                if scenario.scenario_type == 'optimistic':
                    if request.form.get('include_optimistic') == 'on':
                        scenario.probability = float(request.form.get('optimistic_probability', 0.25))
                    else:
                        db.session.delete(scenario)
                elif scenario.scenario_type == 'realistic':
                    if request.form.get('include_realistic') == 'on':
                        scenario.probability = float(request.form.get('realistic_probability', 0.5))
                    else:
                        db.session.delete(scenario)
                elif scenario.scenario_type == 'pessimistic':
                    if request.form.get('include_pessimistic') == 'on':
                        scenario.probability = float(request.form.get('pessimistic_probability', 0.25))
                    else:
                        db.session.delete(scenario)
            
            # Ajouter les nouveaux scénarios
            existing_types = [s.scenario_type for s in prediction.scenarios]
            
            if 'optimistic' not in existing_types and request.form.get('include_optimistic') == 'on':
                optimistic = PredictionScenario(
                    prediction_id=prediction.id,
                    name=translations['optimistic'][lang],
                    scenario_type='optimistic',
                    probability=float(request.form.get('optimistic_probability', 0.25))
                )
                db.session.add(optimistic)
                
            if 'realistic' not in existing_types and request.form.get('include_realistic') == 'on':
                realistic = PredictionScenario(
                    prediction_id=prediction.id,
                    name=translations['realistic'][lang],
                    scenario_type='realistic',
                    probability=float(request.form.get('realistic_probability', 0.5))
                )
                db.session.add(realistic)
                
            if 'pessimistic' not in existing_types and request.form.get('include_pessimistic') == 'on':
                pessimistic = PredictionScenario(
                    prediction_id=prediction.id,
                    name=translations['pessimistic'][lang],
                    scenario_type='pessimistic',
                    probability=float(request.form.get('pessimistic_probability', 0.25))
                )
                db.session.add(pessimistic)
            
            # Si les paramètres ont changé, marquer comme à recalculer
            prediction.status = 'pending'
            
            db.session.commit()
            
            flash('Prévision mise à jour avec succès. L\'analyse est en cours.', 'success')
            return redirect(url_for('predictive.view_prediction', prediction_id=prediction.id))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la mise à jour de la prévision: {str(e)}")
            flash('Erreur lors de la mise à jour de la prévision. Veuillez réessayer.', 'danger')
    
    # Récupérer les scénarios
    scenarios = {s.scenario_type: s for s in prediction.scenarios}
    
    return render_template(
        'predictive/edit_prediction.html',
        lang=lang,
        translations=translations,
        prediction=prediction,
        scenarios=scenarios
    )

@predictive_bp.route('/prediction/<int:prediction_id>/delete', methods=['POST'])

def delete_prediction(prediction_id):
    """Suppression d'une prévision"""
    user_id = get_user_id()
    logger.info(f"Suppression de la prévision {prediction_id}")
    
    prediction = SalesPrediction.query.filter_by(id=prediction_id, user_id=user_id).first_or_404()
    
    try:
        db.session.delete(prediction)
        db.session.commit()
        flash('Prévision supprimée avec succès.', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la suppression de la prévision: {str(e)}")
        flash('Erreur lors de la suppression de la prévision. Veuillez réessayer.', 'danger')
    
    return redirect(url_for('predictive.sales_predictions'))

@predictive_bp.route('/customer-insights')

def customer_insights():
    user_id = get_user_id()
    """Liste des analyses clients"""
    logger.info("Affichage de la liste des analyses clients")
    
    lang = get_current_language()
    translations = get_translations()
    
    # Récupérer toutes les analyses clients
    insights = CustomerInsight.query.filter_by(user_id=user_id).order_by(CustomerInsight.date_created.desc()).all()
    
    # Segmentation des clients
    high_potential = [i for i in insights if i.development_potential_score and i.development_potential_score >= 75]
    high_risk = [i for i in insights if i.churn_risk_score and i.churn_risk_score >= 75]
    
    return render_template(
        'predictive/customer_insights.html',
        lang=lang,
        translations=translations,
        insights=insights,
        high_potential=high_potential,
        high_risk=high_risk
    )

@predictive_bp.route('/product-catalog')

def product_catalog():
    user_id = get_user_id()
    """Analyse et optimisation du catalogue produits"""
    logger.info("Affichage de la page d'optimisation du catalogue produits")
    
    lang = get_current_language()
    translations = get_translations()
    
    # Récupérer les analyses de catalogue
    catalog_insights = ProductCatalogInsight.query.filter_by(user_id=user_id).order_by(ProductCatalogInsight.date_created.desc()).all()
    
    return render_template(
        'predictive/product_catalog.html',
        lang=lang,
        translations=translations,
        catalog_insights=catalog_insights
    )

@predictive_bp.route('/market-trends')

def market_trends():
    user_id = get_user_id()
    """Analyse des tendances du marché"""
    logger.info("Affichage de la page des tendances du marché")
    
    lang = get_current_language()
    translations = get_translations()
    
    # Récupérer les tendances
    trends = MarketTrend.query.filter_by(user_id=user_id).order_by(MarketTrend.date_created.desc()).all()
    
    # Segmentation des tendances par type
    seasonal_trends = [t for t in trends if t.trend_type == 'seasonal']
    emerging_trends = [t for t in trends if t.trend_type == 'emerging']
    declining_trends = [t for t in trends if t.trend_type == 'declining']
    other_trends = [t for t in trends if t.trend_type not in ['seasonal', 'emerging', 'declining']]
    
    return render_template(
        'predictive/market_trends.html',
        lang=lang,
        translations=translations,
        trends=trends,
        seasonal_trends=seasonal_trends,
        emerging_trends=emerging_trends,
        declining_trends=declining_trends,
        other_trends=other_trends
    )

@predictive_bp.route('/alerts')

def alerts():
    user_id = get_user_id()
    """Liste des alertes prédictives"""
    logger.info("Affichage de la liste des alertes prédictives")
    
    lang = get_current_language()
    translations = get_translations()
    
    # Récupérer les alertes
    all_alerts = PredictiveAlert.query.filter_by(user_id=user_id).order_by(PredictiveAlert.date_created.desc()).all()
    
    # Segmentation des alertes par type et priorité
    unread_alerts = [a for a in all_alerts if a.status == 'unread']
    high_priority = [a for a in all_alerts if a.priority >= 4]
    opportunities = [a for a in all_alerts if a.alert_type == 'opportunity']
    risks = [a for a in all_alerts if a.alert_type == 'risk']
    
    return render_template(
        'predictive/alerts.html',
        lang=lang,
        translations=translations,
        all_alerts=all_alerts,
        unread_alerts=unread_alerts,
        high_priority=high_priority,
        opportunities=opportunities,
        risks=risks
    )

@predictive_bp.route('/alert/<int:alert_id>/mark-as-read', methods=['POST'])

def mark_alert_as_read(alert_id):
    user_id = get_user_id()
    """Marquer une alerte comme lue"""
    alert = PredictiveAlert.query.filter_by(id=alert_id, user_id=user_id).first_or_404()
    
    try:
        alert.status = 'read'
        db.session.commit()
        return jsonify({'success': True})
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erreur lors du marquage de l'alerte: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@predictive_bp.route('/api/prediction/<int:prediction_id>/data')

def prediction_data(prediction_id):
    user_id = get_user_id()
    """API pour récupérer les données d'une prévision pour les graphiques"""
    prediction = SalesPrediction.query.filter_by(id=prediction_id, user_id=user_id).first_or_404()
    
    # Si les résultats ne sont pas encore calculés
    if not prediction.prediction_results:
        return jsonify({'success': False, 'error': 'Prediction results not available yet'})
    
    # Formater les données pour les graphiques
    data = {
        'labels': [],
        'datasets': []
    }
    
    # Ajouter chaque scénario
    for scenario in prediction.scenarios:
        if not scenario.results:
            continue
            
        dataset = {
            'label': scenario.name,
            'data': [],
            'borderColor': get_scenario_color(scenario.scenario_type),
            'fill': False
        }
        
        # Ajouter les points de données
        for date, value in scenario.results.items():
            if date not in data['labels']:
                data['labels'].append(date)
            dataset['data'].append(value)
        
        data['datasets'].append(dataset)
    
    return jsonify({'success': True, 'data': data})

def get_scenario_color(scenario_type):
    """Obtenir la couleur pour un type de scénario"""
    colors = {
        'optimistic': '#28a745',  # Green
        'realistic': '#007bff',   # Blue
        'pessimistic': '#dc3545', # Red
        'custom': '#6610f2'       # Purple
    }
    return colors.get(scenario_type, '#6c757d')  # Default gray