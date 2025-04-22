import os
import logging
import requests
import random
import datetime
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, Response
from dotenv import load_dotenv
from decimal import Decimal
from sqlalchemy import func, extract

# Configure logging
logging.basicConfig(level=logging.DEBUG)
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
from models_business import db as db_business, BusinessReport

# Initialize database
db.init_app(app)
db_business.init_app(app)

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
import finance  # Import du module finance
import subscription  # Import du module d'abonnement
import business  # Import du module business

# Benji's personality phrases
GREETING_PHRASES = [
    "Yo ! Moi c'est Benji. Prêt à t'aider, tranquille ✌️",
    "Salut à toi ! Pose ta question, je m'occupe du reste 😎",
    "Hello l'ami ! Dis-moi ce que tu veux faire aujourd'hui.",
    "Bienvenue dans ton coin perso. On va gérer ça en douceur 🚀"
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
        db_business.create_all()
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
    # Pass a random greeting to the template for initial message
    greeting = random.choice(GREETING_PHRASES)
    return render_template("index.html", initial_greeting=greeting)

@app.route("/chat")
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
    
    return render_template("chat.html", initial_greeting=initial_message)

@app.route("/api/chat", methods=["POST"])
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
    system_message = {"role": "system", "content": "Tu es Benji, un assistant perso cool et relax. Tu parles TOUJOURS en français comme un bon pote, avec un ton naturel, sans être vulgaire ni trop familier. IMPORTANT: Même si l'utilisateur te parle en anglais, tu DOIS répondre en français. Tu expliques clairement, tu donnes des conseils pratiques, et tu restes toujours de bonne humeur. N'utilise jamais l'anglais, uniquement le français."}
    
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
def history():
    memory = load_memory()
    return jsonify(memory)

@app.route("/clear", methods=["POST"])
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
            session['access_token'] = result['AccessToken']
            session['id_token'] = result['IdToken']
            session['refresh_token'] = result['RefreshToken']
            
            # Get user info from Cognito
            user_info = get_user_info(result['AccessToken'])
            
            # Check if user exists in the database
            user = User.query.filter_by(username=username).first()
            
            if not user:
                # Create a new user in the database
                user = User(
                    username=username,
                    email=username,  # Cognito uses email as username
                    display_name=user_info.get('preferred_username', username)
                )
                db.session.add(user)
                db.session.commit()
                logger.debug(f"Created new user in database: {username}")
            
            # Set session is_admin flag
            groups = user_info.get('cognito:groups', [])
            session['is_admin'] = 'admin' in groups
            
            flash("Connexion réussie !", "success")
            
            # Redirect to the originally requested page, or to home
            next_page = request.args.get('next') or url_for('home')
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
            
            # Create user in database
            user = User(
                username=username,
                email=username,  # Cognito uses email as username
                display_name=display_name
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
    
    form = UpdateProfileForm()
    
    if form.validate_on_submit():
        try:
            # Update user display name in the database
            username = session.get('username')
            user = User.query.filter_by(username=username).first()
            
            if user:
                user.display_name = form.display_name.data
                db.session.commit()
                flash("Votre profil a été mis à jour avec succès.", "success")
            else:
                flash("Utilisateur introuvable.", "danger")
            
        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            db.session.rollback()
            flash("Une erreur est survenue lors de la mise à jour du profil.", "danger")
    
    # Pre-fill the form with current user data
    if request.method == "GET":
        username = session.get('username')
        user = User.query.filter_by(username=username).first()
        
        if user:
            form.display_name.data = user.display_name
    
    return render_template("profile.html", form=form)

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
    return render_template("ocr.html")

@app.route("/api/save-extracted-text", methods=["POST"])
@login_required
def save_extracted_text():
    """Save text extracted from an image to the database"""
    try:
        data = request.json
        text_content = data.get("text", "").strip()
        title = data.get("title", "").strip() or "Texte extrait"
        
        # Ensure the content is not empty
        if not text_content:
            return jsonify({"success": False, "error": "Le texte extrait est vide"}), 400
        
        # Get current user
        username = session.get('username')
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({"success": False, "error": "Utilisateur non trouvé"}), 403
        
        # Create a new ExtractedText record
        extracted_text = ExtractedText(
            user_id=user.id,
            title=title,
            content=text_content,
            source="camera"
        )
        
        db.session.add(extracted_text)
        db.session.commit()
        
        logger.debug(f"Saved extracted text with ID: {extracted_text.id}")
        return jsonify({
            "success": True, 
            "message": "Texte enregistré avec succès",
            "id": extracted_text.id
        })
    
    except Exception as e:
        logger.error(f"Error saving extracted text: {str(e)}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

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

# Initialiser le module finance
finance.init_app(app)

# Initialiser le module de gestion des abonnements
subscription.init_app(app)

# Initialiser le module business
business.init_app(app)

# Route de redirection pour les liens d'authentification
@app.route('/r')
def auth_redirect():
    return app.send_static_file('redirect.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)