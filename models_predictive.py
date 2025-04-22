"""
Module de modèles pour l'Intelligence Prédictive Commerciale.

Ce module contient les modèles de données pour stocker et traiter
les informations liées aux prévisions de ventes, l'analyse de clients
et les recommandations pour l'optimisation des catalogues produits.
"""

from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from models import db


class SalesPrediction(db.Model):
    """Modèle pour les prévisions de ventes"""
    __tablename__ = 'sales_prediction'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    date_modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Période de prévision
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    
    # Paramètres de prédiction
    prediction_parameters = db.Column(JSONB, nullable=True)
    
    # Résultats de prédiction (JSON avec différents scénarios)
    prediction_results = db.Column(JSONB, nullable=True)
    
    # État de la prédiction (pending, processing, completed, failed)
    status = db.Column(db.String(20), default='pending')
    
    # Données d'entrée utilisées pour la prédiction
    input_data_sources = db.Column(JSONB, nullable=True)
    
    # Métadonnées et métriques de performance
    confidence_score = db.Column(db.Float, nullable=True)
    accuracy_metrics = db.Column(JSONB, nullable=True)
    
    # Relations
    user = db.relationship('User', backref=db.backref('sales_predictions', lazy='dynamic'))
    scenarios = db.relationship('PredictionScenario', backref='prediction', lazy='dynamic',
                              cascade='all, delete-orphan')

    def __repr__(self):
        return f'<SalesPrediction {self.name}>'


class PredictionScenario(db.Model):
    """Modèle pour les différents scénarios de prévision"""
    __tablename__ = 'prediction_scenario'

    id = db.Column(db.Integer, primary_key=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey('sales_prediction.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Type de scénario (optimiste, pessimiste, réaliste, personnalisé)
    scenario_type = db.Column(db.String(50), nullable=False)
    
    # Paramètres spécifiques au scénario
    parameters = db.Column(JSONB, nullable=True)
    
    # Résultats détaillés du scénario
    results = db.Column(JSONB, nullable=True)
    
    # Probabilité estimée de ce scénario
    probability = db.Column(db.Float, nullable=True)
    
    def __repr__(self):
        return f'<PredictionScenario {self.name}>'


class CustomerInsight(db.Model):
    """Modèle pour les insights et analyses de clients"""
    __tablename__ = 'customer_insight'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_id = db.Column(db.Integer, nullable=True)  # ID externe du client
    customer_name = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    date_modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Score de potentiel de développement (0-100)
    development_potential_score = db.Column(db.Float, nullable=True)
    
    # Score de risque de désengagement (0-100)
    churn_risk_score = db.Column(db.Float, nullable=True)
    
    # Tendance d'achat (croissant, décroissant, stable)
    purchase_trend = db.Column(db.String(50), nullable=True)
    
    # Historique des interactions et achats
    interaction_history = db.Column(JSONB, nullable=True)
    
    # Recommandations personnalisées
    recommendations = db.Column(JSONB, nullable=True)
    
    # Catégorisation du client (VIP, régulier, occasionnel, etc.)
    customer_category = db.Column(db.String(50), nullable=True)
    
    # Données d'analyse supplémentaires
    analysis_data = db.Column(JSONB, nullable=True)
    
    # Relations
    user = db.relationship('User', backref=db.backref('customer_insights', lazy='dynamic'))
    
    def __repr__(self):
        return f'<CustomerInsight {self.customer_name}>'


class ProductCatalogInsight(db.Model):
    """Modèle pour les insights et optimisations du catalogue produits"""
    __tablename__ = 'product_catalog_insight'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    date_modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Analyse de la performance du catalogue
    catalog_analysis = db.Column(JSONB, nullable=True)
    
    # Recommandations d'optimisation
    optimization_recommendations = db.Column(JSONB, nullable=True)
    
    # Tendances identifiées
    identified_trends = db.Column(JSONB, nullable=True)
    
    # Opportunités de développement de nouveaux produits
    new_product_opportunities = db.Column(JSONB, nullable=True)
    
    # Produits à risque ou en déclin
    declining_products = db.Column(JSONB, nullable=True)
    
    # Produits performants
    performing_products = db.Column(JSONB, nullable=True)
    
    # Relations
    user = db.relationship('User', backref=db.backref('product_catalog_insights', lazy='dynamic'))
    
    def __repr__(self):
        return f'<ProductCatalogInsight {self.name}>'


class MarketTrend(db.Model):
    """Modèle pour les tendances du marché identifiées"""
    __tablename__ = 'market_trend'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    date_modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Type de tendance (saisonnière, émergente, en déclin, etc.)
    trend_type = db.Column(db.String(50), nullable=False)
    
    # Force/impact de la tendance (1-10)
    impact_score = db.Column(db.Integer, nullable=True)
    
    # Durée estimée de la tendance
    estimated_duration = db.Column(db.String(100), nullable=True)
    
    # Catégories ou produits concernés
    affected_categories = db.Column(JSONB, nullable=True)
    
    # Recommandations d'actions
    recommended_actions = db.Column(JSONB, nullable=True)
    
    # Source(s) de l'identification
    source = db.Column(db.String(200), nullable=True)
    
    # Relations
    user = db.relationship('User', backref=db.backref('market_trends', lazy='dynamic'))
    
    def __repr__(self):
        return f'<MarketTrend {self.name}>'


class PredictiveAlert(db.Model):
    """Modèle pour les alertes et notifications prédictives"""
    __tablename__ = 'predictive_alert'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Type d'alerte (opportunité, risque, information)
    alert_type = db.Column(db.String(50), nullable=False)
    
    # Niveau de priorité (1-5)
    priority = db.Column(db.Integer, nullable=False, default=3)
    
    # État de l'alerte (non lue, lue, traitée, ignorée)
    status = db.Column(db.String(50), default='unread')
    
    # Entité concernée (client, produit, marché, etc.)
    entity_type = db.Column(db.String(50), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True)
    
    # Actions recommandées
    recommended_actions = db.Column(JSONB, nullable=True)
    
    # Date d'échéance/expiration
    expiry_date = db.Column(db.DateTime, nullable=True)
    
    # Relations
    user = db.relationship('User', backref=db.backref('predictive_alerts', lazy='dynamic'))
    
    def __repr__(self):
        return f'<PredictiveAlert {self.title}>'