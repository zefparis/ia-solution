import os
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text
from models import db, User, SubscriptionPlan, Subscription
from forms import SubscriptionForm, CreditCardForm, CancelSubscriptionForm
from auth import login_required, get_user_info
from s3_storage import S3Storage

subscription_bp = Blueprint('subscription', __name__)
logger = logging.getLogger(__name__)

# Fonction utilitaire pour convertir les octets en format lisible
def format_size(size_bytes):
    """Convertit une taille en octets en format lisible (KB, MB, GB)"""
    if size_bytes == 0:
        return "0 B"
    size_names = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"

# Alias pour la cohérence du code
format_bytes = format_size

# Décorateur pour vérifier si l'utilisateur a un abonnement actif
def subscription_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        username = session.get('username')
        if not username:
            flash('Veuillez vous connecter pour accéder à cette fonctionnalité.', 'warning')
            return redirect(url_for('login'))
        
        user = User.query.filter_by(username=username).first()
        if not user:
            flash('Utilisateur non trouvé.', 'danger')
            return redirect(url_for('login'))
        
        active_sub = user.active_subscription
        if not active_sub or active_sub.is_expired:
            flash('Vous devez avoir un abonnement actif pour accéder à cette fonctionnalité.', 'warning')
            return redirect(url_for('subscription.plans'))
        
        return f(*args, **kwargs)
    
    return decorated_function

# Page d'accueil des abonnements - affiche le statut actuel
@subscription_bp.route('/')
@login_required
def index():
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    active_sub = user.active_subscription
    storage_used = format_size(user.storage_used)
    storage_limit = format_size(user.storage_limit)
    
    return render_template(
        'subscription/index.html',
        user=user,
        subscription=active_sub,
        storage_used=storage_used,
        storage_limit=storage_limit,
        storage_percentage=user.storage_percentage
    )

# Page des différents plans disponibles
@subscription_bp.route('/plans')
@login_required
def plans():
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    # Détecter la région (paramètre ou session)
    region = request.args.get('region') or session.get('region')
    
    # Si une région est spécifiée, la stocker en session
    if region:
        session['region'] = region
    
    # Récupérer les plans en fonction de la région
    if region == 'rdc':
        # Plans spécifiques pour la RDC (en USD)
        available_plans = SubscriptionPlan.query.filter_by(is_active=True, region='rdc').all()
    else:
        # Plans standards (en EUR) pour les autres régions
        available_plans = SubscriptionPlan.query.filter(
            SubscriptionPlan.is_active == True,
            (SubscriptionPlan.region.is_(None) | (SubscriptionPlan.region == ''))
        ).all()
    
    # Si aucun plan n'est disponible pour la région, utiliser les plans standards
    if not available_plans:
        available_plans = SubscriptionPlan.query.filter_by(is_active=True).filter(
            (SubscriptionPlan.region.is_(None) | (SubscriptionPlan.region == ''))
        ).all()
    
    # Récupérer l'abonnement actif de l'utilisateur
    active_sub = user.active_subscription
    current_plan_id = active_sub.plan_id if active_sub else None
    
    storage_used = format_size(user.storage_used)
    
    return render_template(
        'subscription/plans.html',
        user=user,
        plans=available_plans,
        current_plan_id=current_plan_id,
        storage_used=storage_used,
        current_region=region or 'default'
    )

# Page de souscription à un plan spécifique
@subscription_bp.route('/subscribe/<int:plan_id>', methods=['GET', 'POST'])
@login_required
def subscribe(plan_id):
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    # Vérifier si le plan existe et est actif
    plan = SubscriptionPlan.query.filter_by(id=plan_id, is_active=True).first_or_404()
    
    # Initialiser le formulaire
    form = SubscriptionForm()
    
    # Créer les choix pour le RadioField
    plans = SubscriptionPlan.query.filter_by(is_active=True).all()
    form.plan_id.choices = [(p.id, p.name) for p in plans]
    
    # Définir la valeur par défaut
    form.plan_id.default = plan_id
    form.process()  # Nécessaire pour appliquer la valeur par défaut
    
    # Si l'utilisateur a un abonnement actif pour le même plan
    active_sub = user.active_subscription
    if active_sub and active_sub.plan_id == plan_id and not active_sub.is_expired:
        flash('Vous êtes déjà abonné à ce plan.', 'info')
        return redirect(url_for('subscription.index'))
    
    if form.validate_on_submit():
        # Traitement du paiement selon la méthode choisie
        payment_method = form.payment_method.data
        
        # Stocker les informations en session
        session['selected_plan_id'] = plan_id
        session['auto_renew'] = form.auto_renew.data
        
        if payment_method == 'credit_card':
            # Rediriger vers le formulaire de paiement par carte
            return redirect(url_for('subscription.payment'))
        
        elif payment_method == 'mobile_payment':
            # Rediriger vers la page de paiement mobile
            return redirect(url_for('unipesa.mobile_payment_page', plan_id=plan_id))
        
        elif payment_method in ['paypal', 'bank_transfer']:
            # Pour les autres méthodes, simuler une redirection vers un processeur de paiement
            # Dans un environnement de production, vous redirigeriez vers le fournisseur de paiement
            flash(f'Redirection vers {payment_method} pour le paiement...', 'info')
            
            # Pour le moment, créer directement l'abonnement (simulation)
            try:
                # Expiration dans 30 jours (mensuel)
                end_date = datetime.utcnow() + timedelta(days=30)
                
                # Créer le nouvel abonnement
                new_subscription = Subscription(
                    user_id=user.id,
                    plan_id=plan_id,
                    end_date=end_date,
                    is_trial=False,
                    auto_renew=form.auto_renew.data
                )
                
                # Si l'utilisateur a déjà un abonnement actif, le désactiver
                if active_sub:
                    active_sub.is_active = False
                
                db.session.add(new_subscription)
                db.session.commit()
                
                # Créer le bucket S3 si ce n'est pas déjà fait
                if not user.s3_bucket_name:
                    s3 = S3Storage()
                    s3.create_user_bucket(user.id)
                    user.s3_bucket_name = f"benji-assistant-{user.id}"
                    db.session.commit()
                
                flash('Votre abonnement a été activé avec succès! Vous pouvez maintenant utiliser toutes les fonctionnalités de l\'application.', 'success')
                # Redirection vers la page de succès qui fera la redirection vers la page d'accueil
                return redirect(url_for('subscription.success'))
                
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"Erreur lors de la création de l'abonnement: {str(e)}")
                flash('Une erreur est survenue lors de la création de votre abonnement. Veuillez réessayer.', 'danger')
    
    return render_template(
        'subscription/subscribe.html',
        form=form,
        plan=plan,
        user=user
    )

# Page de paiement par carte de crédit
@subscription_bp.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    # Récupérer le plan sélectionné depuis la session
    plan_id = session.get('selected_plan_id')
    auto_renew = session.get('auto_renew', True)
    
    if not plan_id:
        flash('Aucun plan sélectionné.', 'warning')
        return redirect(url_for('subscription.plans'))
    
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    form = CreditCardForm()
    
    if form.validate_on_submit():
        # Dans un environnement de production, vous traiteriez ici le paiement avec Stripe, etc.
        # Pour le moment, simuler un paiement réussi
        try:
            # Expiration dans 30 jours (mensuel)
            end_date = datetime.utcnow() + timedelta(days=30)
            
            # Créer le nouvel abonnement
            new_subscription = Subscription(
                user_id=user.id,
                plan_id=plan_id,
                end_date=end_date,
                is_trial=False,
                auto_renew=auto_renew,
                last_payment_date=datetime.utcnow(),
                next_payment_date=end_date
            )
            
            # Si l'utilisateur a déjà un abonnement actif, le désactiver
            active_sub = user.active_subscription
            if active_sub:
                active_sub.is_active = False
            
            db.session.add(new_subscription)
            db.session.commit()
            
            # Créer le bucket S3 si ce n'est pas déjà fait
            if not user.s3_bucket_name:
                s3 = S3Storage()
                s3.create_user_bucket(user.id)
                user.s3_bucket_name = f"benji-assistant-{user.id}"
                db.session.commit()
            
            # Nettoyer la session
            session.pop('selected_plan_id', None)
            session.pop('auto_renew', None)
            
            flash('Paiement effectué avec succès! Votre abonnement est maintenant actif. Vous pouvez utiliser toutes les fonctionnalités de l\'application.', 'success')
            # Redirection vers la page de succès qui fera la redirection vers la page d'accueil
            return redirect(url_for('subscription.success'))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la création de l'abonnement: {str(e)}")
            flash('Une erreur est survenue lors du traitement du paiement. Veuillez réessayer.', 'danger')
    
    return render_template(
        'subscription/payment.html',
        form=form,
        plan=plan,
        user=user
    )

# Annulation d'un abonnement
@subscription_bp.route('/cancel', methods=['GET', 'POST'])
@login_required
@subscription_required
def cancel():
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    active_sub = user.active_subscription
    
    form = CancelSubscriptionForm()
    
    if form.validate_on_submit() and form.confirm_cancel.data:
        try:
            # Désactiver l'abonnement mais le conserver jusqu'à sa date d'expiration
            active_sub.auto_renew = False
            db.session.commit()
            
            # Enregistrer les commentaires (dans un système réel, vous pourriez les enregistrer dans une table de feedback)
            reason = form.reason.data
            feedback = form.feedback.data
            logger.info(f"Abonnement annulé par l'utilisateur {user.id}. Raison: {reason}, Commentaires: {feedback}")
            
            flash('Votre abonnement a été annulé. Vous pourrez continuer à utiliser le service jusqu\'à la fin de votre période de facturation.', 'info')
            return redirect(url_for('subscription.index'))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erreur lors de l'annulation de l'abonnement: {str(e)}")
            flash('Une erreur est survenue lors de l\'annulation de votre abonnement. Veuillez réessayer.', 'danger')
    
    return render_template(
        'subscription/cancel.html',
        form=form,
        subscription=active_sub,
        user=user
    )

# Gestionnaire d'historique des paiements
@subscription_bp.route('/history')
@login_required
def history():
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    # Récupérer tous les abonnements de l'utilisateur, actifs et inactifs
    subscriptions = Subscription.query.filter_by(user_id=user.id).order_by(Subscription.start_date.desc()).all()
    
    return render_template(
        'subscription/history.html',
        subscriptions=subscriptions,
        user=user
    )

# Page de succès après abonnement
@subscription_bp.route('/success')
@login_required
def success():
    """Page de confirmation après un abonnement réussi"""
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    active_sub = user.active_subscription
    
    return render_template(
        'subscription/success.html',
        user=user,
        subscription=active_sub
    )

# Estimation de la taille de stockage utilisée (mise à jour périodique)
@subscription_bp.route('/update-storage', methods=['POST'])
@login_required
@subscription_required
def update_storage():
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    # Vérifier si la mise à jour est nécessaire (pas plus d'une fois par jour)
    last_check = user.last_storage_check
    if last_check and (datetime.utcnow() - last_check).total_seconds() < 86400:  # 24 heures
        return redirect(url_for('subscription.index'))
    
    try:
        # Obtenir l'utilisation du stockage depuis S3
        s3 = S3Storage()
        storage_size = s3.get_storage_usage(user.id)
        
        # Mettre à jour l'utilisateur
        user.storage_used = storage_size
        user.last_storage_check = datetime.utcnow()
        db.session.commit()
        
        flash('Utilisation du stockage mise à jour.', 'success')
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du stockage: {str(e)}")
        flash('Impossible de mettre à jour l\'utilisation du stockage.', 'danger')
    
    return redirect(url_for('subscription.index'))

# Souscription directe (version simplifiée sans utiliser payment_method)
@subscription_bp.route('/quick-subscribe/<int:plan_id>')
@login_required
def quick_subscribe(plan_id):
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    # Vérifier si le plan existe et est actif
    plan = SubscriptionPlan.query.filter_by(id=plan_id, is_active=True).first_or_404()
    
    # Pour éviter les erreurs en attendant la mise à jour du schéma, on vérifie manuellement
    conn = db.engine.connect()
    result = conn.execute(text(
        f"SELECT * FROM subscription WHERE user_id = {user.id} AND is_active = true ORDER BY end_date DESC LIMIT 1"
    ))
    active_sub_row = result.fetchone()
    
    if active_sub_row and active_sub_row[2] == plan_id and active_sub_row[3] > datetime.utcnow():
        flash('Vous êtes déjà abonné à ce plan.', 'info')
        return redirect(url_for('subscription.index'))
    
    # Pour le moment, créer directement l'abonnement (simulation PayPal)
    try:
        # Expiration dans 30 jours (mensuel)
        end_date = datetime.utcnow() + timedelta(days=30)
        
        # Si l'utilisateur a déjà un abonnement actif, le désactiver via SQL direct
        if active_sub_row:
            conn.execute(text(
                f"UPDATE subscription SET is_active = false WHERE id = {active_sub_row[0]}"
            ))
        
        # Insérer directement l'abonnement via SQL pour éviter les erreurs de mapping
        conn.execute(text(
            "INSERT INTO subscription (user_id, plan_id, start_date, end_date, is_trial, is_active, auto_renew, last_payment_date, next_payment_date) " +
            f"VALUES ({user.id}, {plan_id}, '{datetime.utcnow()}', '{end_date}', false, true, true, '{datetime.utcnow()}', '{end_date}')"
        ))
        
        conn.commit()
        
        # Créer le bucket S3 si ce n'est pas déjà fait
        if not user.s3_bucket_name:
            s3 = S3Storage()
            s3.create_user_bucket(user.id)
            user.s3_bucket_name = f"benji-assistant-{user.id}"
            db.session.commit()
        
        flash('Votre abonnement a été activé avec succès! Vous pouvez maintenant utiliser toutes les fonctionnalités de l\'application.', 'success')
        # Redirection vers la page de succès qui fera la redirection vers la page d'accueil
        return redirect(url_for('subscription.success'))
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logger.error(f"Erreur lors de la création de l'abonnement: {str(e)}")
        flash('Une erreur est survenue lors de la création de votre abonnement. Veuillez réessayer.', 'danger')
        return redirect(url_for('subscription.plans'))

# Gestion des fichiers et test de l'intégration S3
@subscription_bp.route('/files', methods=['GET', 'POST'])
@login_required
def files():
    """Gérer les fichiers de l'utilisateur et tester l'intégration S3"""
    import io
    from s3_storage import S3Storage
    
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash('Utilisateur non trouvé.', 'danger')
        return redirect(url_for('subscription.index'))
    
    # Récupérer l'abonnement actif de l'utilisateur
    active_sub = user.active_subscription
    
    # Initialiser le stockage S3
    s3 = S3Storage()
    s3_available = s3.s3_client is not None
    
    # Liste des fichiers
    files = []
    
    if s3_available:
        # Si formulaire soumis pour upload
        if request.method == 'POST' and 'file' in request.files:
            file = request.files['file']
            
            if file and file.filename:
                # Vérifier d'abord si l'utilisateur a un abonnement actif
                if not active_sub:
                    flash('Vous avez besoin d\'un abonnement pour uploader des fichiers.', 'warning')
                    return redirect(url_for('subscription.plans'))
                
                # Créer le dossier utilisateur si nécessaire
                s3.create_user_bucket(user.id)
                
                # Lire le fichier
                file_data = file.read()
                file_size = len(file_data)
                
                # Vérifier la limite de stockage
                plan = SubscriptionPlan.query.get(active_sub.plan_id)
                storage_limit = plan.storage_limit * 1024 * 1024 * 1024  # convertir GB en octets
                
                # Obtenir l'utilisation actuelle du stockage
                current_usage = s3.get_storage_usage(user.id)
                
                if current_usage + file_size > storage_limit:
                    flash('Espace de stockage insuffisant pour ce fichier.', 'danger')
                else:
                    # Upload le fichier
                    file_obj = io.BytesIO(file_data)
                    url = s3.upload_file(
                        user.id, 
                        file_obj, 
                        file.filename, 
                        file.content_type or 'application/octet-stream'
                    )
                    
                    if url:
                        # Mettre à jour l'utilisation du stockage
                        new_usage = s3.get_storage_usage(user.id)
                        user.storage_used = new_usage
                        user.last_storage_check = datetime.utcnow()
                        db.session.commit()
                        
                        flash(f'Fichier {file.filename} uploadé avec succès!', 'success')
                    else:
                        flash('Erreur lors de l\'upload du fichier.', 'danger')
        
        # Si demande de suppression
        elif request.method == 'POST' and request.form.get('delete'):
            filename = request.form.get('delete')
            
            if filename:
                # Assurez-vous que filename est bien le nom du fichier sans le préfixe
                # La fonction delete_file dans S3Storage va reconstituer le chemin complet
                result = s3.delete_file(user.id, filename)
                
                if result:
                    # Mettre à jour l'utilisation du stockage
                    new_usage = s3.get_storage_usage(user.id)
                    user.storage_used = new_usage
                    user.last_storage_check = datetime.utcnow()
                    db.session.commit()
                    
                    flash(f'Fichier {filename} supprimé avec succès!', 'success')
                else:
                    flash('Erreur lors de la suppression du fichier.', 'danger')
        
        # Récupérer la liste des fichiers
        files = s3.list_files(user.id)
        
        # Filtrer les fichiers comme .keep
        files = [f for f in files if not f.endswith('.keep')]
        
        # Mettre à jour l'utilisation du stockage
        new_usage = s3.get_storage_usage(user.id)
        user.storage_used = new_usage
        user.last_storage_check = datetime.utcnow()
        db.session.commit()
    
    # Calculer l'utilisation du stockage
    storage_used = user.storage_used or 0
    storage_limit = 0
    
    if active_sub:
        plan = SubscriptionPlan.query.get(active_sub.plan_id)
        storage_limit = plan.storage_limit * 1024 * 1024 * 1024
    
    # Convertir en unités lisibles
    storage_used_readable = format_size(storage_used)
    storage_limit_readable = format_size(storage_limit) if storage_limit > 0 else "0 B"
    
    # Calculer le pourcentage d'utilisation
    usage_percent = (storage_used / storage_limit) * 100 if storage_limit > 0 else 0
    
    return render_template(
        'subscription/files.html',
        files=files,
        s3_available=s3_available,
        active_subscription=active_sub,
        storage_used=storage_used_readable,
        storage_limit=storage_limit_readable,
        usage_percent=usage_percent
    )

def init_app(app):
    """Initialiser les routes de gestion des abonnements"""
    app.register_blueprint(subscription_bp, url_prefix='/subscription')