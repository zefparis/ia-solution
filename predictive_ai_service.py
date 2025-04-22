"""
Service d'IA pour l'Intelligence Prédictive Commerciale.

Ce module fournit des fonctions d'analyse prédictive alimentées par l'IA
pour générer des prévisions de ventes, analyser les clients et optimiser
les catalogues produits.
"""

import os
import json
import logging
import numpy as np
from datetime import datetime, timedelta
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

# Pour l'intégration avec OpenAI
from openai import OpenAI

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation du client OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
else:
    openai_client = None
    logger.warning("OPENAI_API_KEY non définie. Les fonctionnalités d'IA seront limitées.")


def generate_sales_prediction(prediction_id):
    """
    Génère les prévisions de ventes pour tous les scénarios d'une prédiction.
    
    Args:
        prediction_id (int): ID de la prédiction à générer
    
    Returns:
        bool: True si la génération a réussi, False sinon
    """
    logger.info(f"Génération des prévisions de ventes pour la prédiction {prediction_id}")
    
    try:
        # Récupérer la prédiction
        prediction = SalesPrediction.query.get(prediction_id)
        if not prediction:
            logger.error(f"Prédiction {prediction_id} non trouvée")
            return False
        
        # Mettre à jour le statut
        prediction.status = 'processing'
        db.session.commit()
        
        # Extraire les paramètres
        start_date = prediction.start_date
        end_date = prediction.end_date
        granularity = prediction.prediction_parameters.get('granularity', 'monthly')
        
        # Générer les dates pour la période de prévision
        date_range = generate_date_range(start_date, end_date, granularity)
        
        # Générer une structure de résultats de base pour la prédiction
        prediction.prediction_results = {
            'dates': date_range
        }
        
        # Pour chaque scénario, générer des prévisions
        for scenario in prediction.scenarios:
            # Générer les données de prévision
            scenario_data = generate_scenario_data(scenario.scenario_type, date_range)
            
            # Stocker les résultats
            scenario.results = scenario_data
        
        # Mettre à jour le statut et enregistrer
        prediction.status = 'completed'
        prediction.confidence_score = 0.85  # Score de confiance fictif
        db.session.commit()
        
        # Créer une alerte pour informer de la complétion
        create_prediction_completion_alert(prediction)
        
        return True
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erreur SQL lors de la génération des prévisions: {str(e)}")
        
        # Mettre à jour le statut en cas d'échec
        try:
            prediction = SalesPrediction.query.get(prediction_id)
            if prediction:
                prediction.status = 'failed'
                db.session.commit()
        except:
            pass
            
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la génération des prévisions: {str(e)}")
        
        # Mettre à jour le statut en cas d'échec
        try:
            prediction = SalesPrediction.query.get(prediction_id)
            if prediction:
                prediction.status = 'failed'
                db.session.commit()
        except:
            pass
            
        return False


def generate_date_range(start_date, end_date, granularity):
    """
    Génère une liste de dates formatées en fonction de la granularité.
    
    Args:
        start_date (date): Date de début
        end_date (date): Date de fin
        granularity (str): Granularité ('daily', 'weekly', 'monthly', 'quarterly', 'yearly')
    
    Returns:
        list: Liste des dates formatées
    """
    date_format = '%Y-%m-%d'  # Format standard
    
    if granularity == 'daily':
        delta = timedelta(days=1)
        date_list = []
        
        current_date = start_date
        while current_date <= end_date:
            date_list.append(current_date.strftime(date_format))
            current_date += delta
            
        return date_list
        
    elif granularity == 'weekly':
        # Arrondir à la semaine
        start_date = start_date - timedelta(days=start_date.weekday())
        
        date_list = []
        current_date = start_date
        
        while current_date <= end_date:
            date_list.append(current_date.strftime(date_format))
            current_date += timedelta(days=7)
            
        return date_list
        
    elif granularity == 'monthly':
        date_list = []
        
        # Commencer au premier jour du mois
        current_date = datetime(start_date.year, start_date.month, 1).date()
        
        while current_date <= end_date:
            date_list.append(current_date.strftime(date_format))
            
            # Avancer au mois suivant
            month = current_date.month + 1
            year = current_date.year
            
            if month > 12:
                month = 1
                year += 1
                
            current_date = datetime(year, month, 1).date()
            
        return date_list
        
    elif granularity == 'quarterly':
        date_list = []
        
        # Commencer au premier jour du trimestre
        quarter_month = ((start_date.month - 1) // 3) * 3 + 1
        current_date = datetime(start_date.year, quarter_month, 1).date()
        
        while current_date <= end_date:
            date_list.append(current_date.strftime(date_format))
            
            # Avancer au trimestre suivant
            month = current_date.month + 3
            year = current_date.year
            
            if month > 12:
                month = month - 12
                year += 1
                
            current_date = datetime(year, month, 1).date()
            
        return date_list
        
    elif granularity == 'yearly':
        date_list = []
        
        # Commencer au premier jour de l'année
        current_date = datetime(start_date.year, 1, 1).date()
        
        while current_date <= end_date:
            date_list.append(current_date.strftime(date_format))
            current_date = datetime(current_date.year + 1, 1, 1).date()
            
        return date_list
        
    else:
        # Par défaut, mensuel
        return generate_date_range(start_date, end_date, 'monthly')


def generate_scenario_data(scenario_type, date_range):
    """
    Génère des données de prévision pour un scénario spécifique.
    
    Dans une application réelle, cela utiliserait des modèles de ML,
    mais ici nous générons des données fictives pour démonstration.
    
    Args:
        scenario_type (str): Type de scénario ('optimistic', 'realistic', 'pessimistic', 'custom')
        date_range (list): Liste des dates pour lesquelles générer des données
    
    Returns:
        dict: Données du scénario (date => valeur)
    """
    # Point de départ des ventes et tendance de base
    base_value = 10000  # Valeur de départ
    
    # Facteurs de croissance selon le scénario
    growth_factors = {
        'optimistic': 1.05,  # Croissance de 5% par période
        'realistic': 1.02,   # Croissance de 2% par période
        'pessimistic': 0.98, # Décroissance de 2% par période
        'custom': 1.03       # Croissance de 3% par période
    }
    
    # Volatilité selon le scénario
    volatilities = {
        'optimistic': 0.05,   # Faible volatilité
        'realistic': 0.10,    # Volatilité moyenne
        'pessimistic': 0.15,  # Haute volatilité
        'custom': 0.08        # Volatilité personnalisée
    }
    
    # Facteur de saisonnalité (plus élevé pour Q4/fin d'année, plus bas pour Q1)
    def seasonality_factor(date_str):
        date = datetime.strptime(date_str, '%Y-%m-%d')
        month = date.month
        
        if month in [10, 11, 12]:  # Q4
            return 1.2
        elif month in [7, 8, 9]:   # Q3
            return 1.1
        elif month in [4, 5, 6]:   # Q2
            return 1.0
        else:                      # Q1
            return 0.9
    
    # Générer les données
    growth_factor = growth_factors.get(scenario_type, 1.0)
    volatility = volatilities.get(scenario_type, 0.1)
    
    scenario_data = {}
    current_value = base_value
    
    for i, date in enumerate(date_range):
        # Appliquer saisonnalité
        seasonal_value = current_value * seasonality_factor(date)
        
        # Appliquer volatilité aléatoire
        random_factor = 1 + np.random.normal(0, volatility)
        final_value = max(0, seasonal_value * random_factor)  # Éviter les valeurs négatives
        
        # Arrondir à 2 décimales
        scenario_data[date] = round(final_value, 2)
        
        # Calculer la valeur pour la période suivante (appliquer croissance)
        current_value = current_value * growth_factor
    
    return scenario_data


def analyze_customer_data(user_id, customer_data=None):
    """
    Analyse les données clients pour identifier les potentiels, risques et tendances.
    
    Args:
        user_id (int): ID de l'utilisateur
        customer_data (dict, optional): Données clients externes à analyser
        
    Returns:
        dict: Résultats de l'analyse
    """
    logger.info(f"Analyse des données clients pour l'utilisateur {user_id}")
    
    try:
        # Dans une application réelle, on utiliserait des modèles de ML
        # Ici, nous allons simuler quelques insights pour démonstration
        
        # Exemple de résultats d'analyse
        results = {
            'high_potential_customers': [],
            'high_risk_customers': [],
            'customer_segments': {},
            'recommendations': {}
        }
        
        # Dans une application réelle, ces données proviendraient d'une analyse ML
        # des comportements d'achat, engagement, etc.
        sample_customers = [
            {
                'customer_id': 1001,
                'name': 'Société ABC',
                'development_potential': 85.5,
                'churn_risk': 15.2,
                'purchase_trend': 'growing',
                'category': 'vip',
                'recommendations': [
                    'Offrir une montée en gamme de services',
                    'Proposer un programme de partenariat exclusif',
                    'Planifier une réunion de revue stratégique'
                ]
            },
            {
                'customer_id': 1002,
                'name': 'Entreprise XYZ',
                'development_potential': 45.8,
                'churn_risk': 78.9,
                'purchase_trend': 'declining',
                'category': 'regular',
                'recommendations': [
                    'Contacter rapidement pour comprendre leurs besoins',
                    'Offrir un programme de fidélité personnalisé',
                    'Proposer une remise sur le prochain achat'
                ]
            },
            {
                'customer_id': 1003,
                'name': 'Startup 123',
                'development_potential': 92.1,
                'churn_risk': 12.5,
                'purchase_trend': 'growing',
                'category': 'new',
                'recommendations': [
                    'Proposer des produits complémentaires',
                    'Établir un programme d\'accompagnement',
                    'Inviter à un événement exclusif'
                ]
            }
        ]
        
        # Traiter et enregistrer les insights pour chaque client
        for customer in sample_customers:
            # Créer ou mettre à jour l'insight client
            insight = CustomerInsight.query.filter_by(
                user_id=user_id, 
                customer_id=customer['customer_id']
            ).first()
            
            if not insight:
                insight = CustomerInsight(
                    user_id=user_id,
                    customer_id=customer['customer_id'],
                    customer_name=customer['name']
                )
            
            # Mettre à jour les données
            insight.development_potential_score = customer['development_potential']
            insight.churn_risk_score = customer['churn_risk']
            insight.purchase_trend = customer['purchase_trend']
            insight.customer_category = customer['category']
            insight.recommendations = {'items': customer['recommendations']}
            
            db.session.add(insight)
            
            # Ajouter aux résultats
            if customer['development_potential'] >= 75:
                results['high_potential_customers'].append(customer)
            
            if customer['churn_risk'] >= 75:
                results['high_risk_customers'].append(customer)
            
            # Ajouter au segment
            category = customer['category']
            if category not in results['customer_segments']:
                results['customer_segments'][category] = []
            
            results['customer_segments'][category].append(customer)
        
        # Créer des alertes pour les clients à haut potentiel et haut risque
        for customer in results['high_potential_customers']:
            create_customer_potential_alert(user_id, customer)
        
        for customer in results['high_risk_customers']:
            create_customer_risk_alert(user_id, customer)
        
        db.session.commit()
        return results
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erreur SQL lors de l'analyse des clients: {str(e)}")
        return {'error': str(e)}
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse des clients: {str(e)}")
        return {'error': str(e)}


def analyze_product_catalog(user_id, catalog_data=None):
    """
    Analyse le catalogue produits pour identifier les opportunités d'optimisation.
    
    Args:
        user_id (int): ID de l'utilisateur
        catalog_data (dict, optional): Données du catalogue à analyser
        
    Returns:
        dict: Résultats de l'analyse
    """
    logger.info(f"Analyse du catalogue produits pour l'utilisateur {user_id}")
    
    try:
        # Créer une nouvelle analyse de catalogue
        catalog_insight = ProductCatalogInsight(
            user_id=user_id,
            name="Analyse du catalogue " + datetime.now().strftime("%B %Y"),
            description="Analyse automatique du catalogue produits"
        )
        
        # Dans une application réelle, ces données proviendraient d'une analyse ML
        # Ici, nous simulons quelques résultats
        
        # Analyse de performance du catalogue
        catalog_insight.catalog_analysis = {
            'total_products': 120,
            'active_products': 98,
            'performing_products': 45,
            'underperforming_products': 32,
            'new_products': 22,
            'performance_by_category': {
                'Catégorie A': 85.5,
                'Catégorie B': 62.7,
                'Catégorie C': 41.2
            }
        }
        
        # Recommandations d'optimisation
        catalog_insight.optimization_recommendations = {
            'general': [
                "Optimiser la gamme de prix pour la Catégorie B",
                "Simplifier le catalogue en retirant les produits inactifs",
                "Améliorer les descriptions produits pour augmenter les conversions"
            ],
            'specific_products': [
                {
                    'product_id': 'P1001',
                    'name': 'Produit X',
                    'recommendation': 'Réduire le prix de 5%'
                },
                {
                    'product_id': 'P2002',
                    'name': 'Produit Y',
                    'recommendation': 'Mettre en avant dans les promotions'
                }
            ]
        }
        
        # Tendances identifiées
        catalog_insight.identified_trends = {
            'growing_categories': ['Catégorie A', 'Catégorie E'],
            'declining_categories': ['Catégorie C'],
            'seasonal_patterns': {
                'Catégorie B': 'Q4',
                'Catégorie D': 'Q2'
            }
        }
        
        # Opportunités de nouveaux produits
        catalog_insight.new_product_opportunities = [
            {
                'name': 'Extension de la gamme A',
                'description': 'Ajouter des produits premium à la Catégorie A',
                'potential_score': 87
            },
            {
                'name': 'Produits complémentaires pour B',
                'description': 'Développer des accessoires pour la Catégorie B',
                'potential_score': 76
            }
        ]
        
        # Produits en déclin
        catalog_insight.declining_products = [
            {
                'product_id': 'P3003',
                'name': 'Produit Z',
                'decline_rate': '-18.5%',
                'recommendation': 'Revoir le positionnement ou retirer du catalogue'
            }
        ]
        
        # Produits performants
        catalog_insight.performing_products = [
            {
                'product_id': 'P1001',
                'name': 'Produit X',
                'growth_rate': '+22.3%',
                'recommendation': 'Développer des variantes'
            }
        ]
        
        db.session.add(catalog_insight)
        
        # Créer des alertes pour les opportunités et risques identifiés
        create_catalog_alerts(user_id, catalog_insight)
        
        db.session.commit()
        
        return {
            'success': True,
            'catalog_insight_id': catalog_insight.id
        }
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erreur SQL lors de l'analyse du catalogue: {str(e)}")
        return {'error': str(e)}
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse du catalogue: {str(e)}")
        return {'error': str(e)}


def analyze_market_trends(user_id):
    """
    Analyse les tendances du marché pour identifier des opportunités.
    
    Args:
        user_id (int): ID de l'utilisateur
        
    Returns:
        dict: Résultats de l'analyse
    """
    logger.info(f"Analyse des tendances du marché pour l'utilisateur {user_id}")
    
    try:
        # Si OpenAI est configuré, utiliser l'IA pour générer des tendances
        if openai_client:
            return analyze_market_trends_with_ai(user_id)
        else:
            # Fallback sur des tendances de démonstration
            return create_demo_market_trends(user_id)
            
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse des tendances: {str(e)}")
        return {'error': str(e)}


def analyze_market_trends_with_ai(user_id):
    """
    Utilise l'IA (OpenAI) pour analyser les tendances du marché.
    
    Args:
        user_id (int): ID de l'utilisateur
        
    Returns:
        dict: Résultats de l'analyse
    """
    logger.info(f"Analyse des tendances du marché avec IA pour l'utilisateur {user_id}")
    
    try:
        # Demander à l'IA de générer des tendances du marché
        # Note: la nouvelle version du modèle est "gpt-4o" qui a été
        # lancée après votre date limite de connaissance
        response = openai_client.chat.completions.create(
            model="gpt-4o",  # Ou "gpt-4" si "gpt-4o" n'est pas disponible
            messages=[
                {
                    "role": "system",
                    "content": "Tu es un analyste expert en tendances commerciales et marketing. "
                    + "Génère une liste de tendances actuelles du marché qui pourraient être pertinentes pour une PME. "
                    + "Pour chaque tendance, inclure: nom, description, type (émergente, saisonnière, en déclin), "
                    + "impact estimé (de 1 à 10), durée estimée, et catégories affectées."
                },
                {
                    "role": "user",
                    "content": "Génère 5 tendances de marché actuelles significatives pour les PME en 2025, "
                    + "avec un mix de tendances émergentes, saisonnières et en déclin."
                }
            ],
            response_format={"type": "json_object"}
        )
        
        # Extraire et traiter les résultats
        trends_data = json.loads(response.choices[0].message.content)
        
        # Enregistrer les tendances en base de données
        for trend in trends_data.get('trends', []):
            market_trend = MarketTrend(
                user_id=user_id,
                name=trend.get('name', 'Tendance sans nom'),
                description=trend.get('description', ''),
                trend_type=trend.get('type', 'emerging'),
                impact_score=trend.get('impact', 5),
                estimated_duration=trend.get('duration', ''),
                affected_categories=trend.get('categories', []),
                source='AI Analysis',
                recommended_actions=trend.get('recommendations', [])
            )
            db.session.add(market_trend)
            
            # Créer une alerte pour les tendances à fort impact
            if trend.get('impact', 0) >= 7:
                create_trend_alert(user_id, market_trend)
        
        db.session.commit()
        
        return {
            'success': True, 
            'trends_count': len(trends_data.get('trends', [])),
            'trends': trends_data.get('trends', [])
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'analyse des tendances avec IA: {str(e)}")
        # Fallback sur des tendances de démonstration
        return create_demo_market_trends(user_id)


def create_demo_market_trends(user_id):
    """
    Crée des tendances de marché de démonstration.
    
    Args:
        user_id (int): ID de l'utilisateur
        
    Returns:
        dict: Résultats de la création
    """
    logger.info(f"Création de tendances de démonstration pour l'utilisateur {user_id}")
    
    try:
        # Exemples de tendances
        trends = [
            {
                'name': 'Durabilité et économie circulaire',
                'description': 'Les consommateurs privilégient de plus en plus les produits et services durables et les entreprises qui adoptent des pratiques d\'économie circulaire.',
                'trend_type': 'emerging',
                'impact_score': 8,
                'estimated_duration': 'Long terme (> 5 ans)',
                'affected_categories': ['Tous secteurs', 'Produits de consommation', 'Emballage'],
                'recommended_actions': [
                    'Évaluer votre chaîne d\'approvisionnement pour identifier les opportunités de durabilité',
                    'Communiquer sur vos initiatives écologiques',
                    'Développer des options de produits/services écologiques'
                ]
            },
            {
                'name': 'Intelligence artificielle générative pour les PME',
                'description': 'Démocratisation des outils d\'IA générative permettant aux petites entreprises d\'automatiser des tâches complexes et d\'améliorer leur productivité.',
                'trend_type': 'emerging',
                'impact_score': 9,
                'estimated_duration': 'Long terme (> 5 ans)',
                'affected_categories': ['Tous secteurs', 'Marketing', 'Service client', 'Développement produit'],
                'recommended_actions': [
                    'Explorer les outils d\'IA adaptés à votre secteur',
                    'Former votre équipe aux usages de l\'IA',
                    'Identifier les processus qui pourraient bénéficier de l\'automatisation'
                ]
            },
            {
                'name': 'Achats saisonniers de fin d\'année',
                'description': 'Augmentation traditionnelle des dépenses de consommation durant le dernier trimestre avec les fêtes et événements commerciaux.',
                'trend_type': 'seasonal',
                'impact_score': 7,
                'estimated_duration': '3-4 mois (octobre à janvier)',
                'affected_categories': ['Commerce de détail', 'E-commerce', 'Produits de luxe', 'Alimentation'],
                'recommended_actions': [
                    'Planifier vos promotions spéciales fin d\'année',
                    'Optimiser votre stock pour les produits à forte demande',
                    'Préparer votre stratégie marketing pour la saison'
                ]
            },
            {
                'name': 'Déclin des supports marketing traditionnels',
                'description': 'Diminution de l\'efficacité des supports publicitaires traditionnels (imprimés, radio, TV) au profit du digital et des médias sociaux.',
                'trend_type': 'declining',
                'impact_score': 6,
                'estimated_duration': 'Long terme (tendance continue)',
                'affected_categories': ['Marketing', 'Publicité', 'Médias'],
                'recommended_actions': [
                    'Réévaluer votre mix marketing',
                    'Développer votre présence sur les canaux digitaux',
                    'Former votre équipe aux nouvelles techniques de marketing'
                ]
            },
            {
                'name': 'Hyperlocal et commerce de proximité',
                'description': 'Regain d\'intérêt pour les commerces locaux, les circuits courts et les produits régionaux.',
                'trend_type': 'emerging',
                'impact_score': 7,
                'estimated_duration': 'Moyen terme (2-3 ans)',
                'affected_categories': ['Commerce de détail', 'Alimentation', 'Services'],
                'recommended_actions': [
                    'Mettre en avant vos racines locales',
                    'Développer des partenariats avec d\'autres entreprises locales',
                    'Adapter votre communication pour souligner votre ancrage local'
                ]
            }
        ]
        
        # Créer les tendances en base de données
        created_trends = []
        for trend_data in trends:
            market_trend = MarketTrend(
                user_id=user_id,
                name=trend_data['name'],
                description=trend_data['description'],
                trend_type=trend_data['trend_type'],
                impact_score=trend_data['impact_score'],
                estimated_duration=trend_data['estimated_duration'],
                affected_categories=trend_data['affected_categories'],
                recommended_actions=trend_data['recommended_actions'],
                source='Demo Data'
            )
            db.session.add(market_trend)
            created_trends.append(market_trend)
            
            # Créer une alerte pour les tendances à fort impact
            if trend_data['impact_score'] >= 7:
                create_trend_alert(user_id, market_trend)
        
        db.session.commit()
        
        return {
            'success': True,
            'trends_count': len(trends),
            'trends': trends
        }
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erreur SQL lors de la création des tendances de démo: {str(e)}")
        return {'error': str(e)}
    except Exception as e:
        logger.error(f"Erreur lors de la création des tendances de démo: {str(e)}")
        return {'error': str(e)}


# Fonctions utilitaires pour la création d'alertes

def create_prediction_completion_alert(prediction):
    """Crée une alerte pour informer de la complétion d'une prévision"""
    alert = PredictiveAlert(
        user_id=prediction.user_id,
        title=f"Prévision '{prediction.name}' complétée",
        message=f"Votre prévision de ventes a été générée avec succès. Vous pouvez maintenant consulter les résultats.",
        alert_type='info',
        priority=3,
        entity_type='prediction',
        entity_id=prediction.id
    )
    db.session.add(alert)
    return alert


def create_customer_potential_alert(user_id, customer):
    """Crée une alerte pour un client à fort potentiel"""
    alert = PredictiveAlert(
        user_id=user_id,
        title=f"Client à fort potentiel: {customer['name']}",
        message=f"Client identifié avec un fort potentiel de développement ({customer['development_potential']:.1f}/100). Considérez de prendre contact pour développer la relation.",
        alert_type='opportunity',
        priority=4,
        entity_type='customer',
        entity_id=customer['customer_id'],
        recommended_actions=[
            'Contacter le client pour discuter de ses besoins',
            'Proposer des produits/services complémentaires',
            'Préparer une offre spéciale'
        ]
    )
    db.session.add(alert)
    return alert


def create_customer_risk_alert(user_id, customer):
    """Crée une alerte pour un client à risque de désengagement"""
    alert = PredictiveAlert(
        user_id=user_id,
        title=f"Client à risque: {customer['name']}",
        message=f"Client identifié avec un risque élevé de désengagement ({customer['churn_risk']:.1f}/100). Une action rapide est recommandée pour maintenir la relation.",
        alert_type='risk',
        priority=5,
        entity_type='customer',
        entity_id=customer['customer_id'],
        recommended_actions=[
            'Contacter le client pour comprendre ses besoins actuels',
            'Proposer une offre de fidélisation',
            'Revue des dernières interactions pour identifier les problèmes potentiels'
        ]
    )
    db.session.add(alert)
    return alert


def create_catalog_alerts(user_id, catalog_insight):
    """Crée des alertes basées sur l'analyse du catalogue"""
    # Alerte pour les opportunités de nouveaux produits
    if catalog_insight.new_product_opportunities:
        for opportunity in catalog_insight.new_product_opportunities:
            if opportunity.get('potential_score', 0) >= 75:
                alert = PredictiveAlert(
                    user_id=user_id,
                    title=f"Nouvelle opportunité produit: {opportunity.get('name')}",
                    message=f"Une opportunité de nouveau produit a été identifiée: {opportunity.get('description')}",
                    alert_type='opportunity',
                    priority=4,
                    entity_type='catalog',
                    entity_id=catalog_insight.id
                )
                db.session.add(alert)
    
    # Alerte pour les produits en déclin
    if catalog_insight.declining_products:
        for product in catalog_insight.declining_products:
            alert = PredictiveAlert(
                user_id=user_id,
                title=f"Produit en déclin: {product.get('name')}",
                message=f"Le produit montre un déclin de {product.get('decline_rate')}. Recommandation: {product.get('recommendation')}",
                alert_type='risk',
                priority=3,
                entity_type='catalog',
                entity_id=catalog_insight.id
            )
            db.session.add(alert)
    
    return True


def create_trend_alert(user_id, trend):
    """Crée une alerte pour une tendance de marché importante"""
    alert_type = 'opportunity' if trend.trend_type in ['emerging', 'seasonal'] else 'risk'
    priority = min(5, max(1, trend.impact_score // 2 + 1))  # Convertir impact (1-10) en priorité (1-5)
    
    alert = PredictiveAlert(
        user_id=user_id,
        title=f"Tendance de marché: {trend.name}",
        message=f"Tendance {trend.trend_type} identifiée avec un impact de {trend.impact_score}/10: {trend.description}",
        alert_type=alert_type,
        priority=priority,
        entity_type='trend',
        entity_id=trend.id,
        recommended_actions=trend.recommended_actions
    )
    db.session.add(alert)
    return alert