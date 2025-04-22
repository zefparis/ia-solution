"""
API Gateway - Point d'entrée unique pour tous les microservices

Ce module implémente un API Gateway qui :
1. Route les requêtes vers les microservices appropriés
2. Gère l'authentification et l'autorisation
3. Applique le rate limiting
4. Fournit une documentation API unifiée
5. Surveille les performances et la disponibilité des services
"""

import os
import json
import time
import logging
import traceback
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.exceptions import HTTPException
from functools import wraps

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Création du Blueprint pour l'API Gateway
api_gateway = Blueprint('api_gateway', __name__, url_prefix='/api')


# Fonction pour vérifier si un utilisateur est authentifié
def is_authenticated():
    """
    Vérifie si l'utilisateur est authentifié.
    
    Returns:
        bool: True si l'utilisateur est authentifié, False sinon
    """
    # Pour l'instant, simplement vérifier si un token est présent dans les en-têtes
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return False
    
    # Dans un environnement de production, nous vérifierions la validité du token
    # avec le service d'authentification
    token = auth_header.split(' ')[1]
    
    # Simuler une vérification de token
    if token:
        # Stocker des informations utilisateur dans g pour les middlewares suivants
        g.user_id = "user_123"  # Exemple d'ID utilisateur
        g.user_roles = ["user"]  # Exemple de rôles utilisateur
        return True
    
    return False


# Décorateur pour exiger l'authentification
def require_auth(f):
    """
    Décorateur pour exiger l'authentification pour un endpoint.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_authenticated():
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Authentication required'
            }), 401
        return f(*args, **kwargs)
    return decorated


# Décorateur pour exiger des rôles spécifiques
def require_roles(roles):
    """
    Décorateur pour exiger des rôles spécifiques pour un endpoint.
    
    Args:
        roles (list): Liste des rôles autorisés
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not is_authenticated():
                return jsonify({
                    'error': 'Unauthorized',
                    'message': 'Authentication required'
                }), 401
            
            # Vérifier si l'utilisateur a les rôles requis
            user_roles = getattr(g, 'user_roles', [])
            if not any(role in user_roles for role in roles):
                return jsonify({
                    'error': 'Forbidden',
                    'message': 'Insufficient permissions'
                }), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator


# Middleware pour le logging des requêtes
@api_gateway.before_request
def log_request():
    """Enregistre les informations de la requête entrante."""
    g.request_start_time = time.time()
    
    # Enregistrer les informations de base de la requête
    logger.info(f"Requête reçue: {request.method} {request.path}")
    
    # Enregistrer des informations supplémentaires en mode debug
    if logger.level <= logging.DEBUG:
        logger.debug(f"Headers: {dict(request.headers)}")
        logger.debug(f"Args: {dict(request.args)}")
        
        # Enregistrer le corps de la requête si c'est du JSON
        if request.is_json:
            try:
                body = request.get_json()
                logger.debug(f"Body: {json.dumps(body)}")
            except Exception:
                logger.debug("Impossible de parser le corps de la requête en JSON")


# Middleware pour le logging des réponses
@api_gateway.after_request
def log_response(response):
    """Enregistre les informations de la réponse sortante."""
    # Calculer le temps de réponse
    request_time = getattr(g, 'request_start_time', time.time())
    elapsed_time = (time.time() - request_time) * 1000  # en ms
    
    # Ajouter des en-têtes de performance
    response.headers['X-Response-Time'] = f"{elapsed_time:.2f}ms"
    
    # Enregistrer les informations de base de la réponse
    logger.info(f"Réponse envoyée: {response.status_code} en {elapsed_time:.2f}ms")
    
    # Enregistrer des informations supplémentaires en mode debug
    if logger.level <= logging.DEBUG:
        logger.debug(f"Headers: {dict(response.headers)}")
        
    return response


# Gestionnaire d'exceptions global
@api_gateway.errorhandler(Exception)
def handle_error(e):
    """Gestionnaire d'exceptions global pour l'API Gateway."""
    # Préparer la réponse
    error_response = {
        'error': type(e).__name__,
        'message': str(e),
        'timestamp': datetime.now().isoformat()
    }
    
    # Déterminer le code de statut HTTP
    if isinstance(e, HTTPException):
        status_code = e.code
    else:
        status_code = 500
        # Ajouter des informations de débogage en développement
        if current_app.debug:
            error_response['traceback'] = traceback.format_exc()
    
    # Enregistrer l'erreur
    logger.error(f"Erreur {status_code}: {error_response['error']} - {error_response['message']}")
    
    return jsonify(error_response), status_code


# Endpoint de santé pour l'API Gateway
@api_gateway.route('/health', methods=['GET'])
def health_check():
    """Endpoint de vérification de l'état de l'API Gateway."""
    start_time = time.time()
    
    # Récupérer l'état des services enregistrés
    services_status = {}
    
    # Utiliser les services disponibles dans l'application
    if hasattr(current_app, 'services'):
        for service_name, service_info in current_app.services.items():
            # Vérifier si le service a un endpoint de santé
            if hasattr(service_info, 'health_check') and callable(service_info.health_check):
                try:
                    service_status = service_info.health_check()
                    services_status[service_name] = service_status
                except Exception as e:
                    services_status[service_name] = {
                        'status': 'error',
                        'message': str(e)
                    }
    
    # Vérifier si Redis est disponible
    redis_status = "unavailable"
    if hasattr(current_app, 'extensions') and 'redis_cache' in current_app.extensions:
        try:
            redis_client = current_app.extensions['redis_cache'].redis_client
            if redis_client.ping():
                redis_status = "available"
        except Exception as e:
            redis_status = f"error: {str(e)}"
    
    # Préparer la réponse
    response = {
        'service': 'api_gateway',
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'uptime': time.time() - current_app.start_time if hasattr(current_app, 'start_time') else 0,
        'response_time_ms': (time.time() - start_time) * 1000,
        'services': services_status,
        'dependencies': {
            'redis': {
                'status': redis_status
            }
        }
    }
    
    return jsonify(response)


# Endpoint de documentation de l'API
@api_gateway.route('/docs', methods=['GET'])
def api_docs():
    """Endpoint pour la documentation de l'API."""
    # Dans une implémentation complète, on renverrait une documentation OpenAPI
    # ou une redirection vers Swagger UI
    return jsonify({
        'message': 'API Documentation',
        'endpoints': {
            '/api/health': {
                'methods': ['GET'],
                'description': 'Vérifier l\'état de l\'API Gateway'
            },
            '/api/docs': {
                'methods': ['GET'],
                'description': 'Documentation de l\'API'
            },
            '/api/openai/health': {
                'methods': ['GET'],
                'description': 'Vérifier l\'état du service OpenAI'
            },
            '/api/openai/complete': {
                'methods': ['POST'],
                'description': 'Générer une complétion de texte avec OpenAI'
            },
            '/api/openai/analyze': {
                'methods': ['POST'],
                'description': 'Analyser du texte avec OpenAI'
            },
            '/api/search/health': {
                'methods': ['GET'],
                'description': 'Vérifier l\'état du service de recherche'
            },
            '/api/search/<index>/_search': {
                'methods': ['POST'],
                'description': 'Rechercher des documents dans un index'
            },
            '/api/search/<index>/_search/text': {
                'methods': ['GET'],
                'description': 'Rechercher du texte dans un index'
            },
            '/api/process-analysis/health': {
                'methods': ['GET'],
                'description': 'Vérifier l\'état du service d\'analyse des processus'
            },
            '/api/process-analysis/processes': {
                'methods': ['GET', 'POST'],
                'description': 'Récupérer la liste des processus ou créer un nouveau processus'
            },
            '/api/process-analysis/processes/<id>': {
                'methods': ['GET', 'PUT', 'DELETE'],
                'description': 'Gérer un processus spécifique'
            },
            '/api/process-analysis/processes/<id>/analyze': {
                'methods': ['POST'],
                'description': 'Analyser un processus pour générer des optimisations'
            },
            '/api/process-analysis/processes/<id>/optimizations': {
                'methods': ['GET', 'POST'],
                'description': 'Gérer les optimisations d\'un processus'
            }
        }
    })


def register_gateway(app):
    """
    Enregistre l'API Gateway auprès de l'application Flask.
    
    Args:
        app: L'application Flask
    """
    # Enregistrer le blueprint
    app.register_blueprint(api_gateway)
    
    # Stocker l'heure de démarrage pour le calcul de l'uptime
    app.start_time = time.time()
    
    # Initialiser le registre des services
    if not hasattr(app, 'services'):
        app.services = {}
    
    logger.info("API Gateway enregistré avec succès")