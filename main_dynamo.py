"""
Application principale IA-Solution utilisant DynamoDB au lieu de PostgreSQL
Maximise l'utilisation des services AWS : DynamoDB, Cognito et S3
"""

import os
import logging
import json
from datetime import datetime, timedelta
from decimal import Decimal

from flask import (
    Flask, render_template, session, request, redirect, 
    url_for, flash, jsonify, g, send_file, make_response
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename

# Initialisation du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Importation des services et modèles DynamoDB
from dynamo_auth import (
    login_user, register_user, confirm_signup, 
    forgot_password, confirm_forgot_password, 
    resend_confirmation_code, get_user_info, 
    logout_user, login_required, admin_required, 
    get_current_user, refresh_access_token
)
from dynamo_s3_service import S3Service, default_s3_service
from dynamo_models import (
    User, BusinessReport, Transaction, CashflowPrediction, 
    SubscriptionPlan, ModuleCategory, Module, ModuleReview, 
    ModuleInstallation, MarketingContent, EditorialCalendarEvent,
    BusinessProcess, BusinessPrediction, setup_tables
)
from language import get_text

# Création de l'application Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "1nPpRuqNpECqFG1TqwHKfBTc8JEf5FQv")

# Protection CSRF
csrf = CSRFProtect(app)

# Configuration de l'application
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload
app.config['TEMPLATES_AUTO_RELOAD'] = True

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
            logger.error(f"Erreur lors du chargement de l'utilisateur: {e}")

@app.context_processor
def utility_processor():
    """Injecte des variables utilitaires dans tous les templates"""
    return {
        'user': g.user,
        'now': datetime.now(),
        '_': get_text  # Fonction de traduction
    }

# Route d'accueil
@app.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html', _=get_text)

# Routes d'authentification
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash(get_text('auth.error_missing_fields'), 'danger')
            return render_template('auth/login.html', _=get_text)
        
        result = login_user(email, password)
        
        if result['success']:
            # Stocker les tokens dans la session
            session['access_token'] = result['tokens']['access_token']
            session['id_token'] = result['tokens']['id_token']
            session['refresh_token'] = result['tokens']['refresh_token']
            session['user_id'] = result['tokens']['user_id']
            session['email'] = result['tokens']['email']
            
            # Redirection après connexion
            next_url = session.get('next_url')
            if next_url:
                session.pop('next_url', None)
                return redirect(next_url)
            
            return redirect(url_for('index'))
        else:
            # Gérer le cas où l'utilisateur n'est pas confirmé
            if result.get('user_not_confirmed'):
                session['temp_username'] = email
                return redirect(url_for('confirm_account'))
            
            flash(result['message'], 'danger')
            return render_template('auth/login.html', _=get_text)
    
    return render_template('auth/login.html', _=get_text)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Page d'inscription"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not email or not password or not confirm_password:
            flash(get_text('auth.error_missing_fields'), 'danger')
            return render_template('auth/register.html', _=get_text)
        
        if password != confirm_password:
            flash(get_text('auth.error_passwords_mismatch'), 'danger')
            return render_template('auth/register.html', _=get_text)
        
        result = register_user(username, email, password)
        
        if result['success']:
            session['temp_username'] = email
            flash(result['message'], 'success')
            return redirect(url_for('confirm_account'))
        else:
            flash(result['message'], 'danger')
            return render_template('auth/register.html', _=get_text)
    
    return render_template('auth/register.html', _=get_text)

@app.route('/confirm', methods=['GET', 'POST'])
def confirm_account():
    """Page de confirmation de compte"""
    if 'temp_username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        confirmation_code = request.form.get('confirmation_code')
        username = session['temp_username']
        
        if not confirmation_code:
            flash(get_text('auth.error_missing_code'), 'danger')
            return render_template('auth/confirm.html', _=get_text)
        
        result = confirm_signup(username, confirmation_code)
        
        if result['success']:
            session.pop('temp_username', None)
            flash(result['message'], 'success')
            return redirect(url_for('login'))
        else:
            flash(result['message'], 'danger')
            return render_template('auth/confirm.html', _=get_text)
    
    return render_template('auth/confirm.html', username=session['temp_username'], _=get_text)

@app.route('/resend-code', methods=['POST'])
def resend_code():
    """Renvoie le code de confirmation"""
    if 'temp_username' not in session:
        return jsonify({'success': False, 'message': get_text('auth.error_no_username')})
    
    username = session['temp_username']
    result = resend_confirmation_code(username)
    
    return jsonify(result)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password_route():
    """Page de récupération de mot de passe"""
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash(get_text('auth.error_missing_email'), 'danger')
            return render_template('auth/forgot_password.html', _=get_text)
        
        result = forgot_password(email)
        
        if result['success']:
            session['temp_username'] = email
            flash(result['message'], 'success')
            return redirect(url_for('reset_password'))
        else:
            flash(result['message'], 'danger')
            return render_template('auth/forgot_password.html', _=get_text)
    
    return render_template('auth/forgot_password.html', _=get_text)

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Page de réinitialisation de mot de passe"""
    if 'temp_username' not in session:
        return redirect(url_for('forgot_password_route'))
    
    if request.method == 'POST':
        confirmation_code = request.form.get('confirmation_code')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        username = session['temp_username']
        
        if not confirmation_code or not new_password or not confirm_password:
            flash(get_text('auth.error_missing_fields'), 'danger')
            return render_template('auth/reset_password.html', _=get_text)
        
        if new_password != confirm_password:
            flash(get_text('auth.error_passwords_mismatch'), 'danger')
            return render_template('auth/reset_password.html', _=get_text)
        
        result = confirm_forgot_password(username, confirmation_code, new_password)
        
        if result['success']:
            session.pop('temp_username', None)
            flash(result['message'], 'success')
            return redirect(url_for('login'))
        else:
            flash(result['message'], 'danger')
            return render_template('auth/reset_password.html', _=get_text)
    
    return render_template('auth/reset_password.html', username=session['temp_username'], _=get_text)

@app.route('/logout')
def logout():
    """Déconnecte l'utilisateur"""
    logout_user()
    flash(get_text('auth.logout_success'), 'success')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    """Page de profil utilisateur"""
    return render_template('auth/profile.html', _=get_text)

@app.route('/admin')
@admin_required
def admin():
    """Page d'administration"""
    return render_template('admin/index.html', _=get_text)

# Utilitaires de média
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Sert les fichiers téléchargés (uniquement pour le développement local)"""
    # En production, les fichiers devraient être servis directement depuis S3
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

# Route de healthcheck
@app.route('/healthcheck')
def healthcheck():
    """Endpoint simple pour vérifier que l'application est opérationnelle"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'environment': 'dynamodb'
    })

# Fonction pour initialiser l'application avec les blueprints et configurations
def create_app():
    """Crée et configure l'application Flask avec tous les blueprints"""
    global app
    
    # Initialisation des tables DynamoDB si nécessaire
    try:
        logger.info("Initialisation des tables DynamoDB...")
        setup_tables(wait=True)
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation des tables DynamoDB: {e}")
    
    # Import des blueprints ici pour éviter les importations circulaires
    try:
        # Importer les blueprints
        try:
            from business_dynamo import business_blueprint
            app.register_blueprint(business_blueprint, url_prefix='/business')
        except ImportError as e:
            logger.error(f"Erreur lors de l'importation du blueprint business: {e}")
        
        # Autres blueprints à importer ici
        # ...
        
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement des blueprints: {e}")
    
    # Création du dossier d'uploads s'il n'existe pas
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    return app

# Gérer les nombres décimaux dans les réponses JSON
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super(DecimalEncoder, self).default(o)

app.json_encoder = DecimalEncoder

# Créer l'application si ce fichier est exécuté directement
if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)