"""
Application principale avec architecture microservices

Cette application est une évolution de l'application originale avec une architecture
orientée microservices pour une meilleure scalabilité et maintenabilité.
"""

import os
import logging
import time
from datetime import datetime

from flask import Flask, jsonify, request
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importation des services
from services.api_gateway.gateway import register_gateway
from services.openai_service.service import register_service as register_openai_service
from services.search_service.service import register_service as register_search_service
from services.messaging_service.service import register_service as register_messaging_service
from services.process_analysis_service.service import register_service as register_process_analysis_service
from cache.flask_integration import init_redis_cache

def create_app():
    """
    Crée et configure l'application Flask avec l'architecture microservices.
    
    Returns:
        Flask: L'application Flask configurée
    """
    # Créer l'application Flask
    app = Flask(__name__)
    
    # Configurer l'application
    configure_app(app)
    
    # Initialiser le cache Redis
    init_redis_cache(app)
    
    # Enregistrer l'API Gateway
    register_gateway(app)
    
    # Enregistrer les services
    register_openai_service(app)
    register_search_service(app)
    register_messaging_service(app)
    register_process_analysis_service(app)
    
    # Enregistrer les routes de base
    register_base_routes(app)
    
    # Enregistrer les gestionnaires d'erreurs
    register_error_handlers(app)
    
    return app


def configure_app(app):
    """
    Configure l'application Flask.
    
    Args:
        app: L'application Flask
    """
    # Configuration de base
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'une_cle_secrete_par_defaut')
    app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Configuration de la base de données
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }
    
    # Configuration Redis
    app.config['REDIS_HOST'] = os.environ.get('REDIS_HOST', 'localhost')
    app.config['REDIS_PORT'] = int(os.environ.get('REDIS_PORT', 6379))
    app.config['REDIS_PASSWORD'] = os.environ.get('REDIS_PASSWORD')
    app.config['REDIS_DB'] = int(os.environ.get('REDIS_DB', 0))
    app.config['REDIS_DEFAULT_TTL'] = int(os.environ.get('REDIS_DEFAULT_TTL', 3600))
    
    # Configuration du rate limiting
    app.config['REDIS_ENABLE_GLOBAL_RATE_LIMITING'] = True
    app.config['REDIS_GLOBAL_RATE_LIMIT'] = 100  # requêtes
    app.config['REDIS_GLOBAL_RATE_PERIOD'] = 60  # secondes
    
    # Configuration Elasticsearch
    app.config['ELASTICSEARCH_HOSTS'] = os.environ.get('ELASTICSEARCH_HOSTS', 'http://localhost:9200')
    app.config['ELASTICSEARCH_USERNAME'] = os.environ.get('ELASTICSEARCH_USERNAME')
    app.config['ELASTICSEARCH_PASSWORD'] = os.environ.get('ELASTICSEARCH_PASSWORD')
    app.config['ELASTICSEARCH_CLOUD_ID'] = os.environ.get('ELASTICSEARCH_CLOUD_ID')
    app.config['ELASTICSEARCH_API_KEY'] = os.environ.get('ELASTICSEARCH_API_KEY')
    
    # Configuration RabbitMQ
    app.config['RABBITMQ_HOST'] = os.environ.get('RABBITMQ_HOST', 'localhost')
    app.config['RABBITMQ_PORT'] = int(os.environ.get('RABBITMQ_PORT', 5672))
    app.config['RABBITMQ_USERNAME'] = os.environ.get('RABBITMQ_USERNAME', 'guest')
    app.config['RABBITMQ_PASSWORD'] = os.environ.get('RABBITMQ_PASSWORD', 'guest')
    app.config['RABBITMQ_VHOST'] = os.environ.get('RABBITMQ_VHOST', '/')
    
    # Stocker l'heure de démarrage pour le calcul de l'uptime
    app.start_time = time.time()
    
    logger.info("Application configurée avec succès")


def register_base_routes(app):
    """
    Enregistre les routes de base de l'application.
    
    Args:
        app: L'application Flask
    """
    @app.route('/')
    def home():
        """Page d'accueil de l'API."""
        return jsonify({
            'name': 'IA-Solution API',
            'version': '2.0.0',
            'architecture': 'microservices',
            'documentation': '/api/docs',
            'health': '/api/health',
            'timestamp': datetime.now().isoformat()
        })
        
    @app.route('/info')
    def info():
        """Informations sur l'environnement d'exécution."""
        return jsonify({
            'environment': os.environ.get('FLASK_ENV', 'production'),
            'debug': app.debug,
            'uptime_seconds': time.time() - app.start_time,
            'timestamp': datetime.now().isoformat()
        })


def register_error_handlers(app):
    """
    Enregistre les gestionnaires d'erreurs globaux.
    
    Args:
        app: L'application Flask
    """
    @app.errorhandler(404)
    def not_found(error):
        """Gestionnaire pour les ressources non trouvées."""
        return jsonify({
            'error': 'Not Found',
            'message': 'La ressource demandée n\'existe pas',
            'path': request.path
        }), 404
        
    @app.errorhandler(405)
    def method_not_allowed(error):
        """Gestionnaire pour les méthodes non autorisées."""
        return jsonify({
            'error': 'Method Not Allowed',
            'message': f'La méthode {request.method} n\'est pas autorisée pour cette ressource',
            'path': request.path,
            'allowed_methods': error.valid_methods
        }), 405
        
    @app.errorhandler(500)
    def server_error(error):
        """Gestionnaire pour les erreurs serveur."""
        logger.error(f"Erreur 500: {str(error)}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Une erreur interne s\'est produite sur le serveur',
            'reference': datetime.now().isoformat()
        }), 500


# Application
app = create_app()

if __name__ == '__main__':
    # Exécuter l'application
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    logger.info(f"Démarrage de l'application sur {host}:{port}")
    app.run(host=host, port=port)