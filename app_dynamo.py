"""
Configuration de base de l'application Flask avec DynamoDB
Remplace l'architecture traditionnelle avec SQLAlchemy
"""

import os
import logging
from datetime import datetime

from flask import Flask, session, g, redirect, url_for, request, flash, jsonify
from flask_wtf.csrf import CSRFProtect

from dynamo_auth import get_current_user, login_required, admin_required, get_user_info
from dynamo_models import setup_tables, User
from dynamo_s3_service import default_s3_service as s3_service

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Créer l'application Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "une-cle-secrete-par-defaut")

# Protection CSRF
csrf = CSRFProtect(app)

@app.before_request
def load_user():
    """Charge l'utilisateur courant avant chaque requête"""
    g.user = None
    
    # Si un token d'accès est présent dans la session
    if 'access_token' in session:
        try:
            # Obtenir les informations de l'utilisateur (optionnel)
            if 'user_id' in session:
                g.user = get_current_user()
            
            # Si aucun utilisateur n'est trouvé mais qu'un token est présent
            if g.user is None and 'email' in session:
                user_info = get_user_info(session['access_token'])
                if user_info and 'email' in user_info:
                    # Récupérer ou créer l'utilisateur dans DynamoDB
                    user = User.find_by_email(user_info['email'])
                    if user:
                        g.user = user
                        session['user_id'] = user.id
        except Exception as e:
            logger.error(f"Erreur lors du chargement de l'utilisateur: {str(e)}")

@app.context_processor
def utility_processor():
    """Injecte des variables utilitaires dans tous les templates"""
    return {
        'user': g.user,
        'now': datetime.now()
    }

@app.route('/healthcheck')
def healthcheck():
    """Endpoint simple pour vérifier que l'application est opérationnelle"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })

# Fonction pour initialiser l'application avec les blueprints et configurations
def create_app():
    """Crée et configure l'application Flask avec tous les blueprints"""
    # Initialisation des tables DynamoDB
    try:
        logger.info("Initialisation des tables DynamoDB...")
        table_results = setup_tables(wait=True)
        for table, status in table_results.items():
            logger.info(f"Table {table}: {status}")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation des tables DynamoDB: {str(e)}")
    
    # Import des blueprints ici pour éviter les importations circulaires
    try:
        # Exemple d'import d'un blueprint
        # from modules_dynamo import modules_blueprint
        # app.register_blueprint(modules_blueprint, url_prefix='/modules')
        pass
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement des blueprints: {str(e)}")
    
    return app

# Créer l'application si ce fichier est exécuté directement
if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)