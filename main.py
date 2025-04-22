import os
import logging
import requests
import random
import datetime
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, Response, g, send_from_directory
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from dotenv import load_dotenv
from decimal import Decimal
from sqlalchemy import func, extract
import language

# Configure logging
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'app.log')
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Créer l'application Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Import models (après configuration de l'app)
from models import db
from models import Conversation, Message, User, ExtractedText, Category, FinancialTransaction, Vendor, TaxReport
from models import SubscriptionPlan, Subscription
from models_business import BusinessReport
from models_payment import UniPesaPayment
from models_marketing import MarketingCampaign, EmailContent, SocialMediaPost, InfluencerBrief, ContentGeneration, MarketingSchedule, MarketingAsset
from models_training import Course, Lesson, Quiz, QuizQuestion, Enrollment, ProgressRecord, QuizAttempt, QuizAnswer, KnowledgeBase
from models_predictive import SalesPrediction, PredictionScenario, CustomerInsight, ProductCatalogInsight, MarketTrend, PredictiveAlert

# Initialize database
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Define constants
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4"  # Utilisation de gpt-4 car notre compte n'a pas encore accès à gpt-4o

# Import forms
from forms import LoginForm, RegisterForm, ConfirmationForm, ForgotPasswordForm, ResetPasswordForm, ResendConfirmationForm
from forms import SubscriptionForm, CreditCardForm, CancelSubscriptionForm, BusinessConsultationForm

# Import authentication
import auth
from auth import login_user, register_user, confirm_signup, get_user_info, logout_user, login_required, admin_required

# Import modules
import finance_blueprint as finance_bp  # Import du module finance blueprint
import subscription  # Import du module d'abonnement
import business  # Import du module business
import dashboard  # Import du module tableau de bord
import unified_dashboard  # Import du module tableau de bord unifié
import language  # Import du module de gestion des langues
import export_powerpoint  # Import du module d'exportation PowerPoint
import unipesa_payment  # Import du module de paiement mobile UniPesa pour la RDC
import export  # Import du module d'exportation rapide multi-formats
import marketing  # Import du module marketing IA
import training  # Import du module formation interactive
import marketplace  # Import du module API marketplace
import process_analysis  # Import du module d'analyse des processus
import predictive_intelligence  # Import du module d'intelligence prédictive commerciale
import modules  # Import du système de modules

# Benji's personality phrases - Version améliorée sans répétitions
GREETING_PHRASES = [
    "Prêt à t'aider sur tout sujet ! Que puis-je faire pour toi aujourd'hui ?",
    "Quoi de neuf ? Je suis là pour répondre à tes questions.",
    "Besoin d'un coup de main ? Je suis à ta disposition.",
    "Que souhaites-tu explorer ensemble aujourd'hui ?",
    "Comment puis-je t'assister ? Je suis opérationnel !",
    "Un projet en tête ? Je suis là pour t'aider à le concrétiser.",
    "À ton écoute pour toute question ou demande."
]

ANSWER_INTROS = [
    "Hop, voilà ce que j'ai trouvé pour toi 👇",
    "Alors là, c'est facile. Regarde :",
    "Check ça, c'est pile ce qu'il te faut 👌",
    "Pas de panique, j'ai une réponse clean pour toi 💡"
]

CLARIFICATION_REQUESTS = [
    "Tu peux me donner un peu plus de détails ?",
    "Hmm j'suis pas sûr de capter à 100%, tu peux reformuler vite fait ?",
    "Explique-moi vite fait et je te sors un truc top.",
    "C'est pas clair clair, mais j'suis chaud si tu précises un peu."
]

COMPLETION_PHRASES = [
    "Et voilà le travail, chef 👨‍🍳",
    "C'est dans la boîte ! Tu veux autre chose ?",
    "Fini comme un pro 💼 Si t'as besoin d'autre chose, je suis là.",
    "C'est fait, easy 💪 Tu me dis si on continue."
]

RESET_PHRASES = [
    "Ok, on fait table rase 🧼 Nouveau départ, nouveau flow !",
    "Hop, tout effacé. On repart à zéro !",
    "T'as cliqué sur reset ? T'inquiète, c'est tout propre maintenant.",
    "Historique vidé ! C'est reparti comme en 40."
]

# Initialize database
def init_db():
    with app.app_context():
        db.create_all()
        logger.debug("Database tables created")

# Get or create active conversation
def get_active_conversation():
    with app.app_context():
        # Check if user is logged in
        username = session.get('username')
        user = None
        
        if username:
            # Get user from database
            user = User.query.filter_by(username=username).first()
        
        if user:
            # Get the most recent conversation for this user or create a new one
            conversation = Conversation.query.filter_by(user_id=user.id).order_by(Conversation.last_updated.desc()).first()
            if not conversation:
                conversation = Conversation(user_id=user.id)
                db.session.add(conversation)
                db.session.commit()
                logger.debug(f"Created new conversation with ID: {conversation.id} for user {username}")
        else:
            # Anonymous conversation (no user logged in)
            # Either get the most recent anonymous conversation or create a new one
            conversation = Conversation.query.filter_by(user_id=None).order_by(Conversation.last_updated.desc()).first()
            if not conversation:
                conversation = Conversation(user_id=None)
                db.session.add(conversation)
                db.session.commit()
                logger.debug(f"Created new anonymous conversation with ID: {conversation.id}")
        
        return conversation

# Load conversation history
def load_memory():
    try:
        with app.app_context():
            conversation = get_active_conversation()
            # Use a session-bound query to avoid detached instance errors
            messages = Message.query.filter_by(conversation_id=conversation.id).order_by(Message.timestamp).all()
            return [message.to_dict() for message in messages]
    except Exception as e:
        logger.error(f"Error loading conversation: {str(e)}")
        return []

# Save message to database
def save_message(role, content):
    try:
        with app.app_context():
            conversation = get_active_conversation()
            message = Message(conversation_id=conversation.id, role=role, content=content)
            db.session.add(message)
            db.session.commit()
            logger.debug(f"Saved {role} message to conversation {conversation.id}")
    except Exception as e:
        logger.error(f"Error saving message: {str(e)}")
        db.session.rollback()

@app.route("/")
def home():
    # Si l'utilisateur est connecté mais que son compte n'existe pas en base
    # On s'assure qu'il est envoyé à la page d'accueil et non au chat
    if 'username' in session:
        username = session.get('username')
        user = User.query.filter_by(username=username).first()
        if not user:
            # En cas d'erreur de synchronisation entre Cognito et la base de données
            logger.warning(f"User {username} in session but not found in database")
            # Nettoyer la session pour éviter les erreurs
            session.clear()
            flash("Votre session a expiré ou n'est plus valide. Veuillez vous reconnecter.", "warning")
            return redirect(url_for('login'))
    
    # Pass a random greeting to the template for initial message
    greeting = random.choice(GREETING_PHRASES)
    # Ensure language module is initialized before serving the page
    import language as lang
    # Créer une fonction de traduction pour le template
    def _(key, default=None):
        return lang.get_text(key, default)
    return render_template("index.html", initial_greeting=greeting, language=lang, _=_)

@app.route("/chat")
@login_required
def chat_page():
    """Page dédiée au chat avec l'assistant"""
    # Récupérer le paramètre topic s'il existe
    topic = request.args.get('topic', '')
    initial_message = ""
    
    # Adapter le message initial en fonction du topic
    if topic == 'business':
        initial_message = "Bonjour ! Je suis votre consultant IA. Décrivez votre entreprise, vos défis actuels ou les objectifs que vous souhaitez atteindre, et je vous proposerai des solutions adaptées à votre situation."
    else:
        # Message standard avec une salutation aléatoire
        initial_message = random.choice(GREETING_PHRASES)
    
    # Ensure language module is available in template
    import language as lang
    return render_template("chat.html", initial_greeting=initial_message, language=lang)

@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    if not OPENAI_API_KEY:
        return jsonify({"error": "OPENAI_API_KEY is not set"}), 500
    
    # Get user message
    data = request.json
    user_message = data.get("message", "")
    
    if not user_message.strip():
        return jsonify({"error": "Empty message"}), 400
    
    # Load conversation history
    memory = load_memory()
    
    # Add system message for personalization at the beginning of the conversation
    system_message = {"role": "system", "content": "Tu es Benji, un assistant IA professionnel et sympathique. Tu parles TOUJOURS en français avec un ton naturel et professionnel. IMPORTANT: Même si l'utilisateur te parle en anglais, tu DOIS répondre en français. Tu expliques clairement, tu donnes des conseils pratiques, et tu restes toujours constructif et positif. N'utilise jamais l'anglais, uniquement le français. IMPORTANT: Ne commence JAMAIS ta réponse par 'Benji:' ou par des salutations répétitives comme 'Bonjour', 'Salut', 'Hello' - va directement à l'information utile pour éviter les répétitions."}
    
    # Create a new memory array with system message first
    memory_with_system = [system_message] + memory
    
    # Save user message to database
    save_message('user', user_message)
    
    # Add user message to memory for API call
    memory_with_system.append({"role": "user", "content": user_message})
    
    # Prepare OpenAI API request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    payload = {
        "model": OPENAI_MODEL,
        "messages": memory_with_system,
        "temperature": 0.8,
        "max_tokens": 1000,
        "stream": True  # Enable streaming
    }
    
    # Check if we should stream the response or use normal mode
    use_stream = request.json.get("stream", True)  # Par défaut, on utilise le streaming
    
    if not use_stream:
        # Non-streaming mode for compatibility
        try:
            # Call OpenAI API
            response = requests.post(
                OPENAI_API_URL,
                headers=headers,
                json={**payload, "stream": False}
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            # Extract assistant's reply
            assistant_message = response_data["choices"][0]["message"]["content"]
            
            # Save assistant message to database
            save_message('assistant', assistant_message)
            
            return jsonify({"response": assistant_message})
        
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error: {str(e)}")
            return jsonify({"error": f"API request failed: {str(e)}"}), 500
        except (KeyError, IndexError) as e:
            logger.error(f"Error parsing API response: {str(e)}")
            return jsonify({"error": "Invalid response from API"}), 500
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return jsonify({"error": "An unexpected error occurred"}), 500
    
    # Streaming mode
    def generate():
        try:
            # Complete message that will be saved to the database
            complete_message = ""
            
            # Call OpenAI API with streaming
            response = requests.post(
                OPENAI_API_URL,
                headers=headers,
                json=payload,
                stream=True
            )
            
            response.raise_for_status()
            
            # Process each chunk of the stream
            for line in response.iter_lines():
                if line:
                    # Remove the "data: " prefix and parse JSON
                    line_text = line.decode('utf-8')
                    
                    # Skip the [DONE] line
                    if line_text == "data: [DONE]":
                        continue
                        
                    if line_text.startswith("data: "):
                        json_str = line_text[6:]  # Remove "data: " prefix
                        try:
                            chunk = json.loads(json_str)
                            
                            # Extract the delta content if present
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                
                                if content:
                                    complete_message += content
                                    
                                    # Send the chunk to the client
                                    yield f"data: {json.dumps({'chunk': content})}\n\n"
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing JSON chunk: {e}")
            
            # Save the complete message to the database
            if complete_message:
                with app.app_context():
                    save_message('assistant', complete_message)
            
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API streaming error: {str(e)}")
            error_msg = {"error": f"API request failed: {str(e)}"}
            yield f"data: {json.dumps(error_msg)}\n\n"
        except Exception as e:
            logger.error(f"Unexpected streaming error: {str(e)}")
            error_msg = {"error": "An unexpected error occurred"}
            yield f"data: {json.dumps(error_msg)}\n\n"
    
    # Return the streaming response
    return Response(generate(), mimetype="text/event-stream")

@app.route("/history")
@login_required
def history():
    memory = load_memory()
    return jsonify(memory)

@app.route("/clear", methods=["POST"])
@login_required
def clear():
    try:
        with app.app_context():
            # Delete all messages from the active conversation
            conversation = get_active_conversation()
            Message.query.filter_by(conversation_id=conversation.id).delete()
            db.session.commit()
            logger.debug(f"Cleared all messages from conversation {conversation.id}")
            
            # Return a random reset message
            reset_message = random.choice(RESET_PHRASES)
            return jsonify({"status": "History cleared", "message": reset_message})
    except Exception as e:
        logger.error(f"Error clearing history: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Failed to clear history"}), 500

# Admin routes
@app.route("/admin")
@admin_required
def admin():
    # Get page number for pagination
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of conversations per page
    
    # Get all conversations with pagination
    pagination = Conversation.query.order_by(Conversation.last_updated.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    conversations = pagination.items
    
    # Calculate total messages across all conversations
    total_messages = Message.query.count()
    
    # Get the timestamp of the last activity
    last_message = Message.query.order_by(Message.timestamp.desc()).first()
    last_activity = last_message.timestamp if last_message else "Aucune activité"
    
    # Get total number of conversations
    total_conversations = Conversation.query.count()
    
    # Calculate pagination display values
    start_idx = (pagination.page - 1) * pagination.per_page + 1 if total_conversations > 0 else 0
    end_idx = min((pagination.page) * pagination.per_page, total_conversations)
    
    # Get search term if any
    search_term = request.args.get('search', '')
    
    return render_template("admin.html", 
                          conversations=conversations, 
                          pagination=pagination,
                          total_messages=total_messages, 
                          total_conversations=total_conversations,
                          last_activity=last_activity,
                          search_term=search_term,
                          start_idx=start_idx,
                          end_idx=end_idx,
                          Message=Message)

@app.route("/admin/conversation/<int:conversation_id>/delete", methods=["POST"])
@admin_required
def admin_delete_conversation(conversation_id):
    try:
        # Find the conversation by ID
        conversation = Conversation.query.get_or_404(conversation_id)
        
        # Delete the conversation (cascade will delete its messages too)
        db.session.delete(conversation)
        db.session.commit()
        
        logger.debug(f"Deleted conversation {conversation_id}")
        return redirect(url_for('admin'))
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        db.session.rollback()
        return redirect(url_for('admin'))

@app.route("/admin/search", methods=["GET"])
@admin_required
def admin_search():
    search_term = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = 5
    
    if not search_term:
        return redirect(url_for('admin'))
    
    # Search for conversations with messages containing the search term
    # This is a basic search implementation that can be improved with more complex queries
    matching_messages = Message.query.filter(Message.content.ilike(f'%{search_term}%')).all()
    conversation_ids = set(message.conversation_id for message in matching_messages)
    
    if not conversation_ids:
        flash("Aucun résultat trouvé pour votre recherche.", "info")
        return redirect(url_for('admin'))
    
    # Get the conversations with matching messages
    conversations_query = Conversation.query.filter(Conversation.id.in_(conversation_ids))
    
    # Apply pagination to the query
    pagination = conversations_query.paginate(page=page, per_page=per_page, error_out=False)
    conversations = pagination.items
    
    total_conversations = conversations_query.count()
    
    # Calculate pagination display values
    start_idx = (pagination.page - 1) * pagination.per_page + 1 if total_conversations > 0 else 0
    end_idx = min((pagination.page) * pagination.per_page, total_conversations)
    
    return render_template("admin.html", 
                          conversations=conversations, 
                          pagination=pagination,
                          total_messages=Message.query.count(), 
                          total_conversations=Conversation.query.count(),
                          last_activity=Message.query.order_by(Message.timestamp.desc()).first().timestamp if Message.query.count() > 0 else "Aucune activité",
                          search_term=search_term,
                          start_idx=start_idx,
                          end_idx=end_idx,
                          search_results=True,
                          search_count=total_conversations,
                          Message=Message)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        try:
            # Authenticate user
            result = login_user(username, password)
            
            if "error" in result:
                flash(result["error"], "danger")
                return render_template("login.html", form=form)
            
            # Set session variables
            session['username'] = username
            session['access_token'] = result['access_token']
            session['id_token'] = result['id_token']
            session['refresh_token'] = result['refresh_token']
            
            # Get user info from Cognito
            user_info = get_user_info(result['access_token'])
            
            # Check if user exists in the database
            user = User.query.filter_by(username=username).first()
            
            if not user:
                try:
                    # Create a new user in the database
                    # Extract cognito_id from user info
                    cognito_id = user_info.get('attributes', {}).get('sub')
                    if not cognito_id:
                        logger.error("Cognito ID not found in user info")
                        flash("Une erreur est survenue lors de la création de votre compte. Veuillez contacter le support.", "danger")
                        return render_template("login.html", form=form)
                    
                    user = User(
                        username=username,
                        email=username,  # Cognito uses email as username
                        display_name=user_info.get('preferred_username', username),
                        cognito_id=cognito_id
                    )
                    db.session.add(user)
                    db.session.commit()
                    logger.debug(f"Created new user in database: {username}")
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error creating user in database: {str(e)}")
                    # Essayer de récupérer l'utilisateur existant en cas de violation de contrainte
                    user = User.query.filter_by(email=username).first()
                    if not user:
                        flash("Une erreur est survenue lors de l'accès à votre compte. Veuillez contacter le support.", "danger")
                        return render_template("login.html", form=form)
            
            # Set session is_admin flag
            groups = user_info.get('cognito:groups', [])
            session['is_admin'] = 'admin' in groups
            
            flash("Connexion réussie !", "success")
            
            # Redirect to the originally requested page, or to home
            next_page = request.args.get('next') or session.pop('next_url', None) or url_for('home')
            return redirect(next_page)
            
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            flash("Une erreur est survenue lors de la connexion. Veuillez réessayer.", "danger")
    
    return render_template("login.html", form=form)

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        display_name = form.display_name.data
        
        try:
            # Register user in Cognito
            result = register_user(username, username, password)  # email = username
            
            if "error" in result:
                flash(result["error"], "danger")
                return render_template("register.html", form=form)
            
            # Extract cognito_id from the registration result
            cognito_id = result.get('user_id')
            if not cognito_id:
                logger.error("Cognito ID not found in registration result")
                flash("Une erreur est survenue lors de la création de votre compte. Veuillez contacter le support.", "danger")
                return render_template("register.html", form=form)

            # Create user in database
            user = User(
                username=username,
                email=username,  # Cognito uses email as username
                display_name=display_name,
                cognito_id=cognito_id
            )
            db.session.add(user)
            db.session.commit()
            
            flash("Inscription réussie ! Veuillez vérifier votre email pour confirmer votre compte.", "success")
            return redirect(url_for('confirm'))
            
        except Exception as e:
            logger.error(f"Error during registration: {str(e)}")
            db.session.rollback()
            flash("Une erreur est survenue lors de l'inscription. Veuillez réessayer.", "danger")
    
    return render_template("register.html", form=form)

@app.route("/confirm", methods=["GET", "POST"])
def confirm():
    form = ConfirmationForm()
    
    if form.validate_on_submit():
        username = form.username.data
        confirmation_code = form.confirmation_code.data
        
        try:
            # Confirm user in Cognito
            result = confirm_signup(username, confirmation_code)
            
            if "error" in result:
                flash(result["error"], "danger")
                return render_template("confirm.html", form=form)
            
            flash("Votre compte a été confirmé avec succès ! Vous pouvez maintenant vous connecter.", "success")
            return redirect(url_for('login'))
            
        except Exception as e:
            logger.error(f"Error during confirmation: {str(e)}")
            flash("Une erreur est survenue lors de la confirmation. Veuillez réessayer.", "danger")
    
    return render_template("confirm.html", form=form)

@app.route("/logout")
def logout():
    # Clear user session
    logout_user()
    flash("Vous avez été déconnecté avec succès.", "success")
    return redirect(url_for('home'))

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    from forms import UpdateProfileForm
    import os
    from werkzeug.utils import secure_filename
    import uuid
    
    form = UpdateProfileForm()
    
    # Récupérer l'utilisateur actuel
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash("Utilisateur introuvable. Veuillez vous reconnecter.", "danger")
        return redirect(url_for('login'))
    
    if form.validate_on_submit():
        try:
            # Update user display name in the database
            user.display_name = form.display_name.data
            
            # Traiter l'upload de photo de profil si présent
            if form.profile_picture.data:
                # Vérifier si c'est bien un fichier
                uploaded_file = form.profile_picture.data
                if uploaded_file.filename:
                    # Sécuriser le nom de fichier
                    filename = secure_filename(uploaded_file.filename)
                    # Ajouter un identifiant unique pour éviter les collisions
                    unique_filename = f"{uuid.uuid4().hex}_{filename}"
                    
                    # Définir le chemin où sauvegarder l'image
                    upload_folder = 'static/uploads/profile_pictures'
                    file_path = os.path.join(upload_folder, unique_filename)
                    
                    # Sauvegarder le fichier
                    uploaded_file.save(file_path)
                    
                    # Mettre à jour le profil de l'utilisateur avec le chemin de l'image
                    # Utiliser un chemin relatif pour l'URL
                    user.profile_picture = f"uploads/profile_pictures/{unique_filename}"
                    
                    logger.debug(f"Photo de profil enregistrée: {file_path}")
            
            db.session.commit()
            flash("Votre profil a été mis à jour avec succès.", "success")
            
        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            db.session.rollback()
            flash("Une erreur est survenue lors de la mise à jour du profil.", "danger")
    
    # Pre-fill the form with current user data
    elif request.method == "GET":
        form.display_name.data = user.display_name
    
    # Récupérer l'abonnement actif
    subscription = user.active_subscription
    plan = user.subscription_plan
    
    return render_template("profile.html", 
                          form=form, 
                          user=user, 
                          subscription=subscription,
                          plan=plan)

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    form = ForgotPasswordForm()
    
    if form.validate_on_submit():
        username = form.username.data
        
        try:
            # Initiate forgot password flow in Cognito
            result = auth.forgot_password(username)
            
            if "error" in result:
                flash(result["error"], "danger")
                return render_template("forgot_password.html", form=form)
            
            flash("Un code de réinitialisation a été envoyé à votre adresse email.", "success")
            return redirect(url_for('reset_password', username=username))
            
        except Exception as e:
            logger.error(f"Error initiating forgot password: {str(e)}")
            flash("Une erreur est survenue. Veuillez réessayer.", "danger")
    
    return render_template("forgot_password.html", form=form)

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    form = ResetPasswordForm()
    
    # Pre-fill username if provided in query parameters
    if request.method == "GET" and request.args.get('username'):
        form.username.data = request.args.get('username')
    
    if form.validate_on_submit():
        username = form.username.data
        confirmation_code = form.confirmation_code.data
        new_password = form.new_password.data
        
        try:
            # Confirm forgot password in Cognito
            result = auth.confirm_forgot_password(username, confirmation_code, new_password)
            
            if "error" in result:
                flash(result["error"], "danger")
                return render_template("reset_password.html", form=form)
            
            flash("Votre mot de passe a été réinitialisé avec succès. Vous pouvez maintenant vous connecter avec votre nouveau mot de passe.", "success")
            return redirect(url_for('login'))
            
        except Exception as e:
            logger.error(f"Error resetting password: {str(e)}")
            flash("Une erreur est survenue lors de la réinitialisation du mot de passe. Veuillez réessayer.", "danger")
    
    return render_template("reset_password.html", form=form)

@app.route("/resend-confirmation", methods=["GET", "POST"])
def resend_confirmation():
    form = ResendConfirmationForm()
    
    if form.validate_on_submit():
        username = form.username.data
        
        try:
            # Resend confirmation code in Cognito
            result = auth.resend_confirmation_code(username)
            
            if "error" in result:
                flash(result["error"], "danger")
                return render_template("resend_confirmation.html", form=form)
            
            flash("Un nouveau code de confirmation a été envoyé à votre adresse email.", "success")
            return redirect(url_for('confirm'))
            
        except Exception as e:
            logger.error(f"Error resending confirmation code: {str(e)}")
            flash("Une erreur est survenue. Veuillez réessayer.", "danger")
    
    return render_template("resend_confirmation.html", form=form)

@app.route("/ocr")
@login_required
def ocr():
    """Render the OCR page for camera text extraction"""
    return render_template("ocr_new.html")
    
@app.route("/api/process-document", methods=["POST"])
@login_required
def process_document():
    """Traite un document PDF ou Word téléchargé et extrait son texte"""
    try:
        # Vérifier si un fichier a été fourni
        if 'document' not in request.files:
            return jsonify({"success": False, "error": "Aucun fichier fourni"}), 400
        
        document_file = request.files['document']
        
        # Si l'utilisateur n'a pas sélectionné de fichier
        if document_file.filename == '':
            return jsonify({"success": False, "error": "Aucun fichier sélectionné"}), 400
        
        # Importer le module de traitement des documents
        from document_parser import extract_text_from_document, is_allowed_file
        
        # Vérifier si le type de fichier est autorisé
        if not is_allowed_file(document_file.filename, ['.pdf', '.docx']):
            return jsonify({
                "success": False, 
                "error": "Type de fichier non pris en charge. Extensions autorisées: PDF, DOCX"
            }), 400
        
        # Extraire le texte du document
        result = extract_text_from_document(document_file)
        
        if not result.get('success', False):
            return jsonify({
                "success": False, 
                "error": result.get('error', "Erreur inconnue lors du traitement du document")
            }), 500
        
        # Récupérer l'utilisateur courant
        username = session.get('username')
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({"success": False, "error": "Utilisateur non trouvé"}), 403
        
        # Créer un titre par défaut si nécessaire
        title = f"Document {result.get('document_type', '').upper()} - {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"
        
        # Ajouter des métadonnées au titre si disponibles
        metadata = result.get('metadata', {})
        if metadata.get('title'):
            title = metadata.get('title')
        
        # Filtrer le texte pour éviter les caractères problématiques
        text_content = result.get('text', '')
        
        # Créer un nouvel enregistrement ExtractedText
        extracted_text = ExtractedText(
            user_id=user.id,
            title=title,
            content=text_content,
            source=result.get('document_type', 'document')
        )
        
        db.session.add(extracted_text)
        db.session.commit()
        
        # Renvoyer les données extraites
        return jsonify({
            "success": True,
            "text": text_content,
            "metadata": metadata,
            "id": extracted_text.id,
            "document_type": result.get('document_type', 'document'),
            "title": title
        })
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save-extracted-text", methods=["POST"])
@login_required
def save_extracted_text():
    """Save text extracted from an image to the database using AWS Textract"""
    try:
        logger.debug("Received request to save extracted text")
        data = request.json
        logger.debug(f"Request data keys: {list(data.keys())}")
        
        base64_image = data.get("image", "")
        if base64_image is not None:
            base64_image = base64_image.strip()
        else:
            base64_image = ""
            
        title = data.get("title", "")
        if title is not None:
            title = title.strip()
        if not title:
            title = "Texte extrait"
            
        use_textract = data.get("use_textract", True)  # Par défaut, utiliser Textract
        
        # Mode standard ou analyse de facture/reçu
        analyze_expense = data.get("analyze_expense", True)  # Par défaut, utiliser AnalyzeExpense
        
        # Variables par défaut
        text_content = ""
        extracted_info = {}
        
        # Vérifier si nous avons une image à traiter
        if not base64_image:
            # Fallback vers le texte pré-extrait si fourni
            logger.debug("No image provided, using pre-extracted text")
            text_content = data.get("text", "").strip()
            if not text_content:
                return jsonify({"success": False, "error": "Aucune image ou texte fourni"}), 400
        else:
            logger.debug(f"Processing base64 image (length: {len(base64_image)})")
            # Nettoyer les préfixes des données base64 si présents
            if "base64," in base64_image:
                base64_image = base64_image.split("base64,")[1]
                logger.debug(f"Removed base64 prefix (new length: {len(base64_image)})")
            
            # Utiliser AWS Textract pour l'extraction avancée si demandé
            if use_textract:
                try:
                    logger.debug(f"Using AWS Textract with analyze_expense={analyze_expense}")
                    # Import Textract modules
                    import sys
                    logger.debug(f"Python path: {sys.path}")
                    logger.debug(f"Trying to import aws_textract...")
                    
                    from aws_textract import extract_text_from_base64, analyze_expense_document
                    logger.debug("Successfully imported aws_textract modules")
                    
                    if analyze_expense:
                        # Utiliser l'analyse spécifique pour factures/reçus
                        logger.debug("Calling analyze_expense_document...")
                        result = analyze_expense_document(base64_image)
                        logger.debug("AWS Textract analyze_expense completed")
                    else:
                        # Utiliser l'extraction de texte standard
                        logger.debug("Calling extract_text_from_base64...")
                        result = extract_text_from_base64(base64_image)
                        logger.debug("AWS Textract extract_text completed")
                    
                    logger.debug(f"Textract result keys: {list(result.keys())}")
                    
                    if not result.get("success", False):
                        logger.error(f"Textract extraction failed: {result.get('error')}")
                        # Fallback vers Tesseract local en cas d'échec
                        text_content = data.get("text", "").strip()
                        logger.debug(f"Falling back to pre-extracted text: {text_content[:100]}...")
                        
                        if not text_content:
                            logger.error("No fallback text available")
                            return jsonify({"success": False, "error": f"Échec de l'extraction avec AWS Textract: {result.get('error')}"}), 500
                    else:
                        text_content = result["text"]
                        extracted_info = result.get("extracted_info", {})
                        logger.debug(f"Successfully extracted text with Textract (length: {len(text_content)})")
                        if extracted_info:
                            logger.debug(f"Extracted info keys: {list(extracted_info.keys())}")
                except ImportError as import_error:
                    logger.error(f"Error importing aws_textract: {str(import_error)}")
                    # Fallback vers le texte pré-extrait en cas d'erreur
                    text_content = data.get("text", "").strip()
                    logger.debug(f"Falling back to pre-extracted text due to import error")
                    if not text_content:
                        return jsonify({"success": False, "error": f"Module AWS Textract non disponible: {str(import_error)}"}), 500
                except Exception as textract_error:
                    logger.error(f"Error using AWS Textract: {str(textract_error)}")
                    # Dump the traceback for debugging
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    
                    # Fallback vers le texte pré-extrait en cas d'erreur
                    text_content = data.get("text", "").strip()
                    logger.debug(f"Falling back to pre-extracted text due to error")
                    if not text_content:
                        return jsonify({"success": False, "error": f"Erreur lors de l'utilisation d'AWS Textract: {str(textract_error)}"}), 500
            else:
                # Utiliser le texte fourni directement
                logger.debug("Using pre-extracted text (Textract disabled)")
                text_content = data.get("text", "").strip()
                
                if not text_content:
                    return jsonify({"success": False, "error": "Le texte extrait est vide"}), 400
        
        # Get current user
        username = session.get('username')
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({"success": False, "error": "Utilisateur non trouvé"}), 403
        
        # Créer un nouvel enregistrement ExtractedText
        extracted_text = ExtractedText(
            user_id=user.id,
            title=title,
            content=text_content,
            source="camera"
        )
        
        # Ajouter les informations financières extraites si disponibles
        if 'document_type' in extracted_info:
            extracted_text.document_type = extracted_info['document_type']
            extracted_text.is_processed = True
        
        db.session.add(extracted_text)
        db.session.commit()
        
        # Si des informations financières ont été extraites, créer automatiquement une transaction
        if 'amount' in extracted_info and extracted_info['amount'] != "0.00":
            try:
                # Déterminer si c'est une dépense (par défaut: oui)
                is_expense = True
                
                # Créer la transaction
                transaction = FinancialTransaction(
                    user_id=user.id,
                    amount=Decimal(extracted_info['amount']),
                    description=title,
                    transaction_date=parse_date(extracted_info.get('date')),
                    is_expense=is_expense
                )
                
                # Ajouter TVA si présente
                if 'tax_amount' in extracted_info:
                    transaction.tax_amount = Decimal(extracted_info['tax_amount'])
                
                db.session.add(transaction)
                
                # Lier la transaction au texte extrait
                extracted_text.transaction_id = transaction.id
                
                db.session.commit()
                
                logger.debug(f"Created transaction from extracted text: {transaction.id}")
            except Exception as transaction_error:
                logger.error(f"Error creating transaction: {str(transaction_error)}")
                # Ne pas échouer si la création de transaction échoue
        
        logger.debug(f"Saved extracted text with ID: {extracted_text.id}")
        return jsonify({
            "success": True, 
            "message": "Texte enregistré avec succès",
            "id": extracted_text.id,
            "extracted_info": extracted_info
        })
    
    except Exception as e:
        logger.error(f"Error saving extracted text: {str(e)}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

def parse_date(date_str):
    """Parse une date depuis différents formats vers datetime.date"""
    if not date_str:
        return datetime.datetime.now().date()
    
    formats = [
        '%d/%m/%Y',  # 31/12/2025
        '%d-%m-%Y',  # 31-12-2025
        '%Y-%m-%d',  # 2025-12-31
        '%d.%m.%Y',  # 31.12.2025
        '%m/%d/%Y',  # 12/31/2025
    ]
    
    for fmt in formats:
        try:
            return datetime.datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    # Si aucun format ne correspond, retourner la date du jour
    return datetime.datetime.now().date()

@app.route("/api/get-extracted-texts", methods=["GET"])
@login_required
def get_extracted_texts():
    """Get all extracted texts for the current user"""
    try:
        # Get current user
        username = session.get('username')
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({"success": False, "error": "Utilisateur non trouvé"}), 403
        
        # Get all extracted texts for the user
        texts = ExtractedText.query.filter_by(user_id=user.id).order_by(ExtractedText.created_at.desc()).all()
        
        # Convert to list of dictionaries
        texts_list = [{
            "id": text.id,
            "title": text.title,
            "content": text.content[:100] + "..." if len(text.content) > 100 else text.content,
            "created_at": text.created_at.strftime("%d/%m/%Y %H:%M"),
            "source": text.source,
            "processed": text.is_processed
        } for text in texts]
        
        return jsonify({"success": True, "texts": texts_list})
    
    except Exception as e:
        logger.error(f"Error getting extracted texts: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/delete-extracted-text/<int:text_id>", methods=["DELETE"])
@login_required
def delete_extracted_text(text_id):
    """Delete an extracted text by ID"""
    try:
        # Get current user
        username = session.get('username')
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({"success": False, "error": "Utilisateur non trouvé"}), 403
        
        # Get the text to delete
        text = ExtractedText.query.filter_by(id=text_id, user_id=user.id).first()
        
        if not text:
            return jsonify({"success": False, "error": "Texte non trouvé ou vous n'avez pas les permissions nécessaires"}), 404
        
        # Delete the text
        db.session.delete(text)
        db.session.commit()
        
        logger.debug(f"Deleted extracted text with ID: {text_id}")
        return jsonify({"success": True})
    
    except Exception as e:
        logger.error(f"Error deleting extracted text: {str(e)}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# Ces modules sont déjà initialisés plus bas dans le code
# Ne pas initialiser deux fois pour éviter les conflits

# Importer le module de facturation
import invoicing

# Ces modules sont initialisés plus bas dans le code

# Rediriger les URLs de l'ancien tableau de bord vers le nouveau tableau de bord unifié
@app.route('/dashboard')
@login_required
def redirect_old_dashboard():
    return redirect(url_for('unified_dashboard.dashboard_home'))

# Attraper toutes les routes de l'ancien tableau de bord et rediriger vers le nouveau
@app.route('/dashboard/<path:subpath>')
@login_required
def redirect_dashboard_subpaths(subpath):
    # Par défaut, rediriger vers la page principale du tableau de bord unifié
    return redirect(url_for('unified_dashboard.dashboard_home'))

# Route de redirection pour les liens d'authentification
@app.route('/r')
def auth_redirect():
    return app.send_static_file('redirect.html')

@app.route('/legal')
def legal_info():
    today = datetime.datetime.now().strftime("%d/%m/%Y")
    import language as lang
    return render_template('legal/legal_info.html', today=today, language=lang)

@app.route('/legal/en')
def legal_info_en():
    today = datetime.datetime.now().strftime("%m/%d/%Y")
    import language as lang
    return render_template('legal/legal_info_en.html', today=today, language=lang)

@app.route('/presentation')
def presentation_preview():
    """Route pour afficher la prévisualisation de la présentation en français"""
    return send_from_directory('presentation', 'preview.html')

@app.route('/presentation/en')
def presentation_preview_en():
    """Route pour afficher la prévisualisation de la présentation en anglais"""
    return send_from_directory('presentation', 'preview_en.html')

@app.route('/presentation/images/<path:filename>')
def presentation_images(filename):
    """Route pour servir les images de la présentation"""
    return send_from_directory('presentation/images', filename)

@app.route('/presentation/<path:filename>')
def presentation_files(filename):
    """Route générique pour servir n'importe quel fichier du dossier présentation"""
    return send_from_directory('presentation', filename)

# Initialiser les modules
finance_bp.init_app(app)
subscription.init_app(app)
business.init_app(app)
dashboard.init_app(app)
unified_dashboard.init_app(app)
export_powerpoint.init_app(app)  # Export PowerPoint
invoicing.init_app(app)  # Module de facturation
language.init_app(app)  # Module de langue
unipesa_payment.init_app(app)  # Module de paiement mobile pour la RDC
export.init_app(app)  # Module d'exportation rapide multi-formats
marketing.init_app(app)  # Module marketing IA
training.init_app(app)  # Module formation interactive
marketplace.init_app(app)  # Module API marketplace
process_analysis.init_app(app)  # Module d'analyse des processus
predictive_intelligence.init_app(app)  # Module d'intelligence prédictive commerciale
modules.init_app(app)  # Système de modules métiers

# Route de redirection pour la compatibilité avec l'ancien chemin /invoice
@app.route('/invoice')
def invoice_redirect():
    """Redirection vers le module de facturation pour compatibilité avec les anciens liens"""
    return redirect(url_for('invoicing.index'))

# Initialiser la base de données au démarrage
init_db()

# Initialiser les données de démo pour les modules
from init_modules_data import init_modules_data
with app.app_context():
    init_modules_data()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)