"""
Module pour la fonctionnalité Marketing IA
"""
import os
import json
import uuid
import logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash, current_app, session, Response
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

# Configurer le logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

from main import db
from models import User
from models_marketing import (
    MarketingCampaign, 
    EmailContent, 
    SocialMediaPost, 
    InfluencerBrief, 
    ContentGeneration,
    MarketingSchedule,
    EditorialCalendarEntry,
    MarketingAsset
)
from openai_marketing import generate_marketing_content, create_content_variations, analyze_content_performance, generate_editorial_calendar
from email_service import send_email
from s3_storage import S3Storage, BUCKET_NAME_PREFIX
from auth import login_required
import language

# Création du blueprint Marketing
marketing_bp = Blueprint('marketing', __name__, url_prefix='/marketing')

def _(key, default=None):
    """Fonction de traduction pour ce module"""
    result = language.get_text(key, session.get('lang', 'fr'))
    # Si la clé n'existe pas dans les traductions, utiliser la valeur par défaut
    if result == key and default is not None:
        return default
    return result

def init_app(app):
    """Initialiser les routes marketing pour l'application Flask"""
    app.register_blueprint(marketing_bp)
    
    # S'assurer que les dossiers temporaires existent
    os.makedirs('static/temp/marketing', exist_ok=True)


@marketing_bp.route('/')
@login_required
def marketing_dashboard():
    """Page principale du tableau de bord marketing"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    # Récupérer les campagnes récentes
    campaigns = MarketingCampaign.query.filter_by(user_id=user.id).order_by(
        MarketingCampaign.created_at.desc()).limit(5).all()
    
    # Récupérer les contenus générés récemment
    generated_contents = ContentGeneration.query.filter_by(
        user_id=user.id).order_by(
        ContentGeneration.created_at.desc()).limit(10).all()
    
    # Récupérer les statistiques de base
    campaigns_count = MarketingCampaign.query.filter_by(user_id=user.id).count()
    emails_count = EmailContent.query.join(MarketingCampaign).filter(
        MarketingCampaign.user_id == user.id).count()
    social_posts_count = SocialMediaPost.query.join(MarketingCampaign).filter(
        MarketingCampaign.user_id == user.id).count()
    
    return render_template(
        'marketing/dashboard.html',
        campaigns=campaigns,
        generated_contents=generated_contents,
        campaigns_count=campaigns_count,
        emails_count=emails_count,
        social_posts_count=social_posts_count,
        _=_
    )


@marketing_bp.route('/campaigns')
@login_required
def list_campaigns():
    """Liste des campagnes marketing"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    # Récupérer toutes les campagnes de l'utilisateur
    campaigns = MarketingCampaign.query.filter_by(user_id=user.id).order_by(
        MarketingCampaign.created_at.desc()).all()
    
    return render_template(
        'marketing/campaigns/list.html',
        campaigns=campaigns,
        _=_
    )


@marketing_bp.route('/campaigns/create', methods=['GET', 'POST'])
@login_required
def create_campaign():
    """Créer une nouvelle campagne marketing"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            # Créer la campagne avec les données du formulaire
            campaign = MarketingCampaign(
                user_id=user.id,
                name=request.form.get('name'),
                description=request.form.get('description'),
                campaign_type=request.form.get('campaign_type'),
                status='draft',
                target_audience=request.form.get('target_audience'),
                budget=request.form.get('budget') if request.form.get('budget') else None
            )
            
            # Gérer les dates si elles sont fournies
            start_date_str = request.form.get('start_date')
            if start_date_str:
                campaign.start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            
            end_date_str = request.form.get('end_date')
            if end_date_str:
                campaign.end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            
            db.session.add(campaign)
            db.session.commit()
            
            flash(_('campaign_created_success'), 'success')
            
            # Rediriger vers la page appropriée selon le type de campagne
            if campaign.campaign_type == 'email':
                return redirect(url_for('marketing.create_email_content', campaign_id=campaign.id))
            elif campaign.campaign_type == 'social':
                return redirect(url_for('marketing.create_social_post', campaign_id=campaign.id))
            elif campaign.campaign_type == 'influencer':
                return redirect(url_for('marketing.create_influencer_brief', campaign_id=campaign.id))
            else:
                return redirect(url_for('marketing.view_campaign', campaign_id=campaign.id))
                
        except Exception as e:
            db.session.rollback()
            flash(f"{_('campaign_creation_error')}: {str(e)}", 'danger')
    
    return render_template(
        'marketing/campaigns/create.html',
        _=_
    )


@marketing_bp.route('/campaigns/<int:campaign_id>')
@login_required
def view_campaign(campaign_id):
    """Afficher les détails d'une campagne"""
    from flask_login import current_user
    
    campaign = MarketingCampaign.query.filter_by(id=campaign_id, user_id=current_user.id).first_or_404()
    
    # Récupérer les contenus associés selon le type de campagne
    if campaign.campaign_type == 'email':
        contents = EmailContent.query.filter_by(campaign_id=campaign.id).all()
    elif campaign.campaign_type == 'social':
        contents = SocialMediaPost.query.filter_by(campaign_id=campaign.id).all()
    elif campaign.campaign_type == 'influencer':
        contents = InfluencerBrief.query.filter_by(campaign_id=campaign.id).all()
    else:
        contents = []
    
    return render_template(
        'marketing/campaigns/view.html',
        campaign=campaign,
        contents=contents,
        _=_
    )


@marketing_bp.route('/campaigns/<int:campaign_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_campaign(campaign_id):
    """Modifier une campagne existante"""
    from flask_login import current_user
    
    campaign = MarketingCampaign.query.filter_by(id=campaign_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        try:
            # Mettre à jour les champs avec les données du formulaire
            campaign.name = request.form.get('name')
            campaign.description = request.form.get('description')
            campaign.target_audience = request.form.get('target_audience')
            campaign.budget = request.form.get('budget') if request.form.get('budget') else None
            
            # Gérer les dates si elles sont fournies
            start_date_str = request.form.get('start_date')
            if start_date_str:
                campaign.start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            
            end_date_str = request.form.get('end_date')
            if end_date_str:
                campaign.end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            
            db.session.commit()
            flash(_('campaign_updated_success'), 'success')
            return redirect(url_for('marketing.view_campaign', campaign_id=campaign.id))
                
        except Exception as e:
            db.session.rollback()
            flash(f"{_('campaign_update_error')}: {str(e)}", 'danger')
    
    return render_template(
        'marketing/campaigns/edit.html',
        campaign=campaign,
        _=_
    )


@marketing_bp.route('/campaigns/<int:campaign_id>/delete', methods=['POST'])
@login_required
def delete_campaign(campaign_id):
    """Supprimer une campagne"""
    from flask_login import current_user
    
    campaign = MarketingCampaign.query.filter_by(id=campaign_id, user_id=current_user.id).first_or_404()
    
    try:
        db.session.delete(campaign)
        db.session.commit()
        flash(_('campaign_deleted_success'), 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"{_('campaign_deletion_error')}: {str(e)}", 'danger')
    
    return redirect(url_for('marketing.list_campaigns'))


@marketing_bp.route('/content-generator')
@login_required
def content_generator():
    """Interface de génération de contenu marketing par IA"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    # Récupérer les contenus générés récemment
    recent_contents = ContentGeneration.query.filter_by(
        user_id=user.id).order_by(
        ContentGeneration.created_at.desc()).limit(10).all()
    
    return render_template(
        'marketing/content_generator.html',
        recent_contents=recent_contents,
        _=_
    )


@marketing_bp.route('/editorial-calendar')
@login_required
def view_editorial_calendar():
    """Page du calendrier éditorial"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    # Récupérer les entrées prochaines du calendrier
    upcoming_contents = EditorialCalendarEntry.query.filter_by(user_id=user.id) \
        .filter(EditorialCalendarEntry.scheduled_date >= datetime.utcnow()) \
        .order_by(EditorialCalendarEntry.scheduled_date) \
        .limit(10) \
        .all()
    
    # Calculer des statistiques pour le calendrier
    stats = {
        'total_items': EditorialCalendarEntry.query.filter_by(user_id=user.id).count(),
        'email_count': EditorialCalendarEntry.query.filter_by(user_id=user.id, content_type='email').count(),
        'social_count': EditorialCalendarEntry.query.filter_by(user_id=user.id, content_type='social').count(),
        'blog_count': EditorialCalendarEntry.query.filter_by(user_id=user.id, content_type='blog').count(),
        'ad_count': EditorialCalendarEntry.query.filter_by(user_id=user.id, content_type='ad').count(),
    }
    
    # Déterminer la plateforme la plus active
    platform_counts = db.session.query(
        EditorialCalendarEntry.platform, 
        db.func.count(EditorialCalendarEntry.id).label('count')
    ).filter(
        EditorialCalendarEntry.user_id == user.id,
        EditorialCalendarEntry.platform != None
    ).group_by(
        EditorialCalendarEntry.platform
    ).order_by(
        db.desc('count')
    ).first()
    
    stats['most_active_platform'] = platform_counts[0] if platform_counts else _('none', 'Aucune')
    
    return render_template(
        'marketing/editorial_calendar.html',
        upcoming_contents=upcoming_contents,
        stats=stats,
        _=_
    )


@marketing_bp.route('/calendar-events')
@login_required
def calendar_events():
    """API pour récupérer les événements du calendrier pour FullCalendar"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify([])
    
    # Récupérer les données de la requête (plage de dates)
    start = request.args.get('start')
    end = request.args.get('end')
    
    # Convertir les dates si elles sont fournies
    if start:
        start_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
    else:
        start_date = datetime.utcnow() - timedelta(days=30)
        
    if end:
        end_date = datetime.fromisoformat(end.replace('Z', '+00:00'))
    else:
        end_date = datetime.utcnow() + timedelta(days=60)
    
    # Récupérer les entrées du calendrier pour cette plage de dates
    entries = EditorialCalendarEntry.query.filter(
        EditorialCalendarEntry.user_id == user.id,
        EditorialCalendarEntry.scheduled_date >= start_date,
        EditorialCalendarEntry.scheduled_date <= end_date
    ).all()
    
    # Convertir les entrées en format événement pour FullCalendar
    events = [entry.to_calendar_event() for entry in entries]
    
    return jsonify(events)


@marketing_bp.route('/generate-calendar', methods=['POST'])
@login_required
def generate_calendar():
    """API pour générer un calendrier éditorial avec OpenAI"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({
            'success': False,
            'error': _('error_user_not_found')
        }), 403
    
    try:
        # Récupérer les données du formulaire
        business_sector = request.form.get('business_sector')
        platforms = request.form.getlist('platforms')
        topics = request.form.getlist('topics')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        frequency = request.form.get('frequency')
        additional_notes = request.form.get('additional_notes', '')
        
        # Créer un calendrier dans la base de données
        calendar = MarketingSchedule(
            user_id=user.id,
            title=f"Calendrier {business_sector} {start_date} à {end_date}",
            schedule_type='editorial',
            start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
            end_date=datetime.strptime(end_date, '%Y-%m-%d').date(),
            frequency=frequency,
            platforms=platforms,
            topics=topics,
            status='active'
        )
        
        db.session.add(calendar)
        db.session.commit()
        
        # Générer le calendrier éditorial avec OpenAI
        calendar_entries = generate_editorial_calendar(
            business_sector=business_sector,
            platforms=platforms,
            topics=topics,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            language=session.get('lang', 'fr')
        )
        
        # Créer les entrées du calendrier dans la base de données
        for entry in calendar_entries:
            try:
                # Assurer que la date est au bon format
                if isinstance(entry.get('date'), str):
                    scheduled_date = datetime.strptime(entry.get('date'), '%Y-%m-%d')
                    if 'time' in entry and entry.get('time'):
                        try:
                            time_parts = entry.get('time').split(':')
                            hour = int(time_parts[0])
                            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                            scheduled_date = scheduled_date.replace(hour=hour, minute=minute)
                        except:
                            # Si l'heure est mal formatée, utiliser midi par défaut
                            scheduled_date = scheduled_date.replace(hour=12, minute=0)
                else:
                    # Date par défaut si absente
                    scheduled_date = datetime.utcnow() + timedelta(days=1)
                
                # Déterminer le type de contenu en fonction de la plateforme
                content_type = 'email'
                if entry.get('platform'):
                    if entry.get('platform').lower() in ['facebook', 'instagram', 'twitter', 'linkedin', 'tiktok']:
                        content_type = 'social'
                    elif entry.get('platform').lower() in ['blog', 'website']:
                        content_type = 'blog'
                    elif entry.get('platform').lower() in ['google ads', 'facebook ads', 'ads']:
                        content_type = 'ad'
                
                # Créer l'entrée
                calendar_entry = EditorialCalendarEntry(
                    user_id=user.id,
                    schedule_id=calendar.id,
                    title=entry.get('title') or entry.get('content_idea') or f"Contenu {entry.get('platform')}",
                    description=entry.get('content_idea') or entry.get('brief_content_idea') or '',
                    content_type=content_type,
                    platform=entry.get('platform', '').lower(),
                    scheduled_date=scheduled_date,
                    topic=entry.get('topic', ''),
                    notes=additional_notes
                )
                
                db.session.add(calendar_entry)
            except Exception as e:
                # Journaliser l'erreur mais continuer avec les autres entrées
                logger.error(f"Erreur lors de la création d'une entrée de calendrier: {str(e)}")
        
        # Sauvegarder toutes les entrées
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': _('calendar_generated_success')
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération du calendrier: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@marketing_bp.route('/add-calendar-event', methods=['POST'])
@login_required
def add_calendar_event():
    """API pour ajouter un événement au calendrier manuellement"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({
            'success': False,
            'error': _('error_user_not_found')
        }), 403
    
    try:
        # Récupérer les données du formulaire
        title = request.form.get('title')
        description = request.form.get('description', '')
        date_str = request.form.get('date')
        time_str = request.form.get('time', '12:00')
        platform = request.form.get('platform')
        
        # Déterminer le type de contenu en fonction de la plateforme
        content_type = 'email'
        if platform:
            if platform in ['facebook', 'instagram', 'twitter', 'linkedin', 'tiktok']:
                content_type = 'social'
            elif platform in ['blog', 'website']:
                content_type = 'blog'
            elif platform in ['ad', 'google ads', 'facebook ads', 'ads']:
                content_type = 'ad'
        
        # Créer la date complète
        scheduled_date = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
        
        # Créer l'entrée dans le calendrier
        entry = EditorialCalendarEntry(
            user_id=user.id,
            title=title,
            description=description,
            content_type=content_type,
            platform=platform,
            scheduled_date=scheduled_date,
            status='planned'
        )
        
        db.session.add(entry)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'id': entry.id,
            'message': _('content_added_success')
        })
        
    except Exception as e:
        app.logger.error(f"Erreur lors de l'ajout d'un événement au calendrier: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@marketing_bp.route('/update-calendar-event', methods=['POST'])
@login_required
def update_calendar_event():
    """API pour mettre à jour un événement du calendrier"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({
            'success': False,
            'error': _('error_user_not_found')
        }), 403
    
    try:
        # Récupérer les données du formulaire
        content_id = request.form.get('content_id')
        title = request.form.get('title')
        description = request.form.get('description', '')
        date_str = request.form.get('date')
        time_str = request.form.get('time', '12:00')
        platform = request.form.get('platform')
        
        # Récupérer l'entrée
        entry = EditorialCalendarEntry.query.filter_by(
            id=content_id, 
            user_id=user.id
        ).first_or_404()
        
        # Mettre à jour les champs
        entry.title = title
        entry.description = description
        entry.platform = platform
        
        # Déterminer le type de contenu en fonction de la plateforme
        if platform:
            if platform in ['facebook', 'instagram', 'twitter', 'linkedin', 'tiktok']:
                entry.content_type = 'social'
            elif platform in ['blog', 'website']:
                entry.content_type = 'blog'
            elif platform in ['ad', 'google ads', 'facebook ads', 'ads']:
                entry.content_type = 'ad'
            elif platform == 'email':
                entry.content_type = 'email'
        
        # Mettre à jour la date
        if date_str:
            try:
                scheduled_date = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
                entry.scheduled_date = scheduled_date
            except:
                # Conserver la date actuelle en cas d'erreur
                pass
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': _('content_updated_success')
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour d'un événement du calendrier: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@marketing_bp.route('/delete-calendar-event', methods=['DELETE'])
@login_required
def delete_calendar_event():
    """API pour supprimer un événement du calendrier"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({
            'success': False,
            'error': _('error_user_not_found')
        }), 403
    
    try:
        # Récupérer l'ID de l'événement
        content_id = request.args.get('id')
        
        # Récupérer l'entrée
        entry = EditorialCalendarEntry.query.filter_by(
            id=content_id, 
            user_id=user.id
        ).first_or_404()
        
        # Supprimer l'entrée
        db.session.delete(entry)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': _('content_deleted_success')
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la suppression d'un événement du calendrier: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@marketing_bp.route('/export-calendar')
@login_required
def export_calendar():
    """Exporter le calendrier éditorial au format CSV"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('marketing.editorial_calendar'))
    
    import csv
    from io import StringIO
    
    try:
        # Récupérer toutes les entrées du calendrier de l'utilisateur
        entries = EditorialCalendarEntry.query.filter_by(
            user_id=user.id
        ).order_by(
            EditorialCalendarEntry.scheduled_date
        ).all()
        
        # Créer un buffer pour le CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Écrire l'en-tête
        writer.writerow([
            _('title'), 
            _('description'), 
            _('date'), 
            _('time'), 
            _('platform'), 
            _('content_type'), 
            _('topic'), 
            _('status'), 
            _('notes')
        ])
        
        # Écrire les données
        for entry in entries:
            writer.writerow([
                entry.title,
                entry.description or '',
                entry.scheduled_date.strftime('%Y-%m-%d'),
                entry.scheduled_date.strftime('%H:%M'),
                entry.platform or '',
                entry.content_type,
                entry.topic or '',
                entry.status,
                entry.notes or ''
            ])
        
        # Préparation de la réponse
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=calendrier_editorial.csv"}
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exportation du calendrier: {str(e)}")
        flash(_('error_exporting_calendar'), 'danger')
        return redirect(url_for('marketing.editorial_calendar'))


@marketing_bp.route('/generate-content-from-calendar', methods=['POST'])
@login_required
def generate_content_from_calendar():
    """Générer du contenu basé sur une entrée du calendrier éditorial"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({
            'success': False,
            'error': _('error_user_not_found')
        }), 403
    
    try:
        # Récupérer l'ID de l'entrée
        content_id = request.args.get('id')
        
        # Récupérer l'entrée
        entry = EditorialCalendarEntry.query.filter_by(
            id=content_id, 
            user_id=user.id
        ).first_or_404()
        
        # Stocker les informations dans la session pour les utiliser dans le générateur de contenu
        session['calendar_entry_id'] = entry.id
        session['content_type'] = entry.content_type
        session['platform'] = entry.platform
        session['content_title'] = entry.title
        session['content_description'] = entry.description
        
        return jsonify({
            'success': True,
            'message': _('content_ready_for_generation')
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la préparation de la génération de contenu: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@marketing_bp.route('/generate-content', methods=['POST'])
@login_required
def generate_content():
    """API pour générer du contenu marketing avec OpenAI"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({
            'success': False,
            'error': _('error_user_not_found')
        }), 403
    
    content_type = request.form.get('content_type')
    business_sector = request.form.get('business_sector')
    platform = request.form.get('platform')
    language_code = request.form.get('language', session.get('language', 'fr'))
    prompt_instructions = request.form.get('prompt_instructions')
    
    try:
        # Construire le prompt pour OpenAI
        prompt = f"Vous êtes un expert en marketing pour le secteur {business_sector}. "
        
        if content_type == 'email':
            prompt += "Créez un email marketing convaincant "
        elif content_type == 'social':
            prompt += f"Créez une publication pour {platform} "
        elif content_type == 'blog':
            prompt += "Rédigez un article de blog engageant "
        elif content_type == 'ad':
            prompt += "Créez une publicité persuasive "
        
        if prompt_instructions:
            prompt += f"avec les instructions suivantes: {prompt_instructions}"
        
        # Générer le contenu avec OpenAI
        generated_content = generate_marketing_content(prompt, language_code)
        
        # Enregistrer dans la base de données
        content = ContentGeneration(
            user_id=user.id,
            content_type=content_type,
            prompt=prompt,
            generated_content=generated_content,
            platform=platform,
            business_sector=business_sector,
            language=language_code
        )
        
        db.session.add(content)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'content': generated_content,
            'content_id': content.id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@marketing_bp.route('/content/<int:content_id>/variations', methods=['POST'])
@login_required
def create_variations(content_id):
    """Créer des variations d'un contenu existant"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({
            'success': False,
            'error': _('error_user_not_found')
        }), 403
    
    content = ContentGeneration.query.filter_by(id=content_id, user_id=user.id).first_or_404()
    
    try:
        # Générer des variations avec OpenAI
        variations = create_content_variations(content.generated_content, int(request.form.get('num_variations', 3)))
        
        result = []
        for variation in variations:
            # Enregistrer chaque variation dans la base de données
            var_content = ContentGeneration(
                user_id=user.id,
                content_type=content.content_type,
                prompt=f"Variation de {content.prompt}",
                generated_content=variation,
                platform=content.platform,
                business_sector=content.business_sector,
                language=content.language
            )
            
            db.session.add(var_content)
            result.append({
                'content': variation,
                'content_id': var_content.id
            })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'variations': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@marketing_bp.route('/campaigns/<int:campaign_id>/email', methods=['GET', 'POST'])
@login_required
def create_email_content(campaign_id):
    """Créer un contenu email pour une campagne"""
    from flask_login import current_user
    
    campaign = MarketingCampaign.query.filter_by(id=campaign_id, user_id=current_user.id).first_or_404()
    
    if campaign.campaign_type != 'email':
        flash(_('campaign_type_mismatch'), 'danger')
        return redirect(url_for('marketing.view_campaign', campaign_id=campaign.id))
    
    if request.method == 'POST':
        try:
            # Créer le contenu email avec les données du formulaire
            email_content = EmailContent(
                campaign_id=campaign.id,
                subject=request.form.get('subject'),
                preview_text=request.form.get('preview_text'),
                html_content=request.form.get('html_content'),
                text_content=request.form.get('text_content'),
                status='draft'
            )
            
            # Gérer la date d'envoi si fournie
            schedule_date_str = request.form.get('schedule_date')
            if schedule_date_str:
                email_content.schedule_date = datetime.strptime(schedule_date_str, '%Y-%m-%d')
                email_content.status = 'scheduled'
            
            # Gérer les destinataires (simplifié pour l'instant)
            recipients = request.form.get('recipients')
            if recipients:
                email_content.recipient_list = json.dumps(recipients.split(','))
            
            db.session.add(email_content)
            db.session.commit()
            
            flash(_('email_content_created_success'), 'success')
            return redirect(url_for('marketing.view_campaign', campaign_id=campaign.id))
                
        except Exception as e:
            db.session.rollback()
            flash(f"{_('email_content_creation_error')}: {str(e)}", 'danger')
    
    return render_template(
        'marketing/emails/create.html',
        campaign=campaign,
        _=_
    )


@marketing_bp.route('/campaigns/<int:campaign_id>/social', methods=['GET', 'POST'])
@login_required
def create_social_post(campaign_id):
    """Créer une publication sociale pour une campagne"""
    from flask_login import current_user
    
    campaign = MarketingCampaign.query.filter_by(id=campaign_id, user_id=current_user.id).first_or_404()
    
    if campaign.campaign_type != 'social':
        flash(_('campaign_type_mismatch'), 'danger')
        return redirect(url_for('marketing.view_campaign', campaign_id=campaign.id))
    
    if request.method == 'POST':
        try:
            # Créer la publication sociale avec les données du formulaire
            social_post = SocialMediaPost(
                campaign_id=campaign.id,
                platform=request.form.get('platform'),
                content=request.form.get('content'),
                hashtags=request.form.get('hashtags'),
                status='draft'
            )
            
            # Gérer l'image si fournie
            if 'image' in request.files and request.files['image'].filename:
                image_file = request.files['image']
                filename = f"{uuid.uuid4()}_{secure_filename(image_file.filename)}"
                filepath = os.path.join('static/temp/marketing', filename)
                image_file.save(filepath)
                
                # Upload vers S3
                s3_key = f"users/{current_user.id}/marketing/{filename}"
                s3 = S3Storage()
                with open(filepath, 'rb') as file_obj:
                    s3.upload_file(current_user.id, file_obj, s3_key)
                
                # Mettre à jour l'URL de l'image
                # Générer une URL présignée pour l'image
                s3 = S3Storage()
                url = s3.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': BUCKET_NAME_PREFIX, 'Key': s3_key},
                    ExpiresIn=3600  # URL valide 1 heure
                )
                social_post.image_url = url
                
                # Supprimer le fichier temporaire
                os.remove(filepath)
            
            # Gérer la date de publication si fournie
            schedule_date_str = request.form.get('schedule_date')
            if schedule_date_str:
                social_post.schedule_date = datetime.strptime(schedule_date_str, '%Y-%m-%d')
                social_post.status = 'scheduled'
            
            db.session.add(social_post)
            db.session.commit()
            
            flash(_('social_post_created_success'), 'success')
            return redirect(url_for('marketing.view_campaign', campaign_id=campaign.id))
                
        except Exception as e:
            db.session.rollback()
            flash(f"{_('social_post_creation_error')}: {str(e)}", 'danger')
    
    return render_template(
        'marketing/social/create.html',
        campaign=campaign,
        _=_
    )


@marketing_bp.route('/campaigns/<int:campaign_id>/influencer', methods=['GET', 'POST'])
@login_required
def create_influencer_brief(campaign_id):
    """Créer un brief influenceur pour une campagne"""
    from flask_login import current_user
    
    campaign = MarketingCampaign.query.filter_by(id=campaign_id, user_id=current_user.id).first_or_404()
    
    if campaign.campaign_type != 'influencer':
        flash(_('campaign_type_mismatch'), 'danger')
        return redirect(url_for('marketing.view_campaign', campaign_id=campaign.id))
    
    if request.method == 'POST':
        try:
            # Créer le brief influenceur avec les données du formulaire
            influencer_brief = InfluencerBrief(
                campaign_id=campaign.id,
                influencer_name=request.form.get('influencer_name'),
                influencer_contact=request.form.get('influencer_contact'),
                influencer_platform=request.form.get('influencer_platform'),
                influencer_audience=request.form.get('influencer_audience'),
                brief_content=request.form.get('brief_content'),
                objectives=request.form.get('objectives'),
                deliverables=request.form.get('deliverables'),
                key_messages=request.form.get('key_messages'),
                budget=request.form.get('budget') if request.form.get('budget') else None,
                status='draft'
            )
            
            db.session.add(influencer_brief)
            db.session.commit()
            
            flash(_('influencer_brief_created_success'), 'success')
            return redirect(url_for('marketing.view_campaign', campaign_id=campaign.id))
                
        except Exception as e:
            db.session.rollback()
            flash(f"{_('influencer_brief_creation_error')}: {str(e)}", 'danger')
    
    return render_template(
        'marketing/influencer/create.html',
        campaign=campaign,
        _=_
    )


@marketing_bp.route('/editorial-calendar')
@login_required
def editorial_calendar():
    """Afficher et gérer le calendrier éditorial"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    schedules = MarketingSchedule.query.filter_by(user_id=user.id).order_by(
        MarketingSchedule.created_at.desc()).all()
    
    return render_template(
        'marketing/editorial_calendar.html',
        schedules=schedules,
        _=_
    )


@marketing_bp.route('/create-schedule', methods=['GET', 'POST'])
@login_required
def create_schedule():
    """Créer un nouveau calendrier éditorial"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            # Créer le calendrier avec les données du formulaire
            schedule = MarketingSchedule(
                user_id=user.id,
                title=request.form.get('title'),
                schedule_type=request.form.get('schedule_type'),
                start_date=datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date(),
                end_date=datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date(),
                frequency=request.form.get('frequency'),
                status='draft'
            )
            
            # Gérer les plateformes sélectionnées
            platforms = request.form.getlist('platforms')
            if platforms:
                schedule.platforms = json.dumps(platforms)
            
            # Gérer les sujets
            topics = request.form.get('topics')
            if topics:
                schedule.topics = json.dumps(topics.split(','))
            
            db.session.add(schedule)
            db.session.commit()
            
            # Rediriger vers la génération du calendrier
            return redirect(url_for('marketing.generate_schedule', schedule_id=schedule.id))
                
        except Exception as e:
            db.session.rollback()
            flash(f"{_('schedule_creation_error')}: {str(e)}", 'danger')
    
    return render_template(
        'marketing/schedule/create.html',
        _=_
    )


@marketing_bp.route('/schedule/<int:schedule_id>/generate')
@login_required
def generate_schedule(schedule_id):
    """Générer un calendrier éditorial avec IA"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    schedule = MarketingSchedule.query.filter_by(id=schedule_id, user_id=user.id).first_or_404()
    
    # Cette fonction sera implémentée dans une version future
    # Pour l'instant, on va créer un calendrier simplifié
    
    try:
        # Exemple simple pour démonstration
        generated_schedule = []
        current_date = schedule.start_date
        
        platforms = json.loads(schedule.platforms) if schedule.platforms else []
        topics = json.loads(schedule.topics) if schedule.topics else ["Contenu général"]
        
        topic_index = 0
        
        while current_date <= schedule.end_date:
            for platform in platforms:
                generated_schedule.append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "platform": platform,
                    "topic": topics[topic_index % len(topics)],
                    "content_type": "post" if platform != "email" else "newsletter",
                    "status": "planned"
                })
            
            topic_index += 1
            
            # Avancer la date selon la fréquence
            if schedule.frequency == 'daily':
                current_date += timedelta(days=1)
            elif schedule.frequency == 'weekly':
                current_date += timedelta(days=7)
            elif schedule.frequency == 'biweekly':
                current_date += timedelta(days=14)
            else:  # monthly
                # Approximation simple pour un mois
                current_date += timedelta(days=30)
        
        # Sauvegarder le calendrier généré
        schedule.generated_schedule = json.dumps(generated_schedule)
        schedule.status = 'active'
        db.session.commit()
        
        flash(_('schedule_generated_success'), 'success')
        return redirect(url_for('marketing.view_schedule', schedule_id=schedule.id))
        
    except Exception as e:
        flash(f"{_('schedule_generation_error')}: {str(e)}", 'danger')
        return redirect(url_for('marketing.editorial_calendar'))


@marketing_bp.route('/schedule/<int:schedule_id>')
@login_required
def view_schedule(schedule_id):
    """Afficher un calendrier éditorial généré"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    schedule = MarketingSchedule.query.filter_by(id=schedule_id, user_id=user.id).first_or_404()
    
    # Convertir le calendrier généré en liste Python
    generated_schedule = json.loads(schedule.generated_schedule) if schedule.generated_schedule else []
    
    return render_template(
        'marketing/schedule/view.html',
        schedule=schedule,
        generated_schedule=generated_schedule,
        _=_
    )


@marketing_bp.route('/assets')
@login_required
def list_assets():
    """Liste des ressources marketing"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    assets = MarketingAsset.query.filter_by(user_id=user.id).order_by(
        MarketingAsset.created_at.desc()).all()
    
    return render_template(
        'marketing/assets/list.html',
        assets=assets,
        _=_
    )


@marketing_bp.route('/assets/upload', methods=['GET', 'POST'])
@login_required
def upload_asset():
    """Uploader une ressource marketing"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            if 'asset_file' not in request.files or not request.files['asset_file'].filename:
                flash(_('no_file_selected'), 'danger')
                return redirect(request.url)
            
            file = request.files['asset_file']
            filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
            filepath = os.path.join('static/temp/marketing', filename)
            file.save(filepath)
            
            # Déterminer le type d'asset
            file_type = file.content_type
            asset_type = request.form.get('asset_type')
            if not asset_type:
                if file_type.startswith('image/'):
                    asset_type = 'image'
                elif file_type.startswith('video/'):
                    asset_type = 'video'
                else:
                    asset_type = 'other'
            
            # Upload vers S3
            s3_key = f"users/{user.id}/marketing/assets/{filename}"
            s3 = S3Storage()
            with open(filepath, 'rb') as file_obj:
                s3.upload_file(user.id, file_obj, s3_key)
            
            # Créer l'asset dans la base de données
            asset = MarketingAsset(
                user_id=user.id,
                campaign_id=request.form.get('campaign_id', type=int),
                asset_type=asset_type,
                asset_name=request.form.get('asset_name') or os.path.splitext(file.filename)[0],
                description=request.form.get('description'),
                s3_key=s3_key,
                url=s3.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': BUCKET_NAME_PREFIX, 'Key': s3_key},
                    ExpiresIn=3600  # URL valide 1 heure
                ),
                file_type=file_type,
                file_size=os.path.getsize(filepath),
                is_generated=False
            )
            
            # Ajouter des tags si fournis
            tags = request.form.get('tags')
            if tags:
                asset.tags = json.dumps(tags.split(','))
            
            db.session.add(asset)
            db.session.commit()
            
            # Supprimer le fichier temporaire
            os.remove(filepath)
            
            flash(_('asset_uploaded_success'), 'success')
            return redirect(url_for('marketing.list_assets'))
                
        except Exception as e:
            db.session.rollback()
            flash(f"{_('asset_upload_error')}: {str(e)}", 'danger')
    
    # Récupérer les campagnes pour le dropdown
    campaigns = MarketingCampaign.query.filter_by(user_id=user.id).all() if user else []
    
    return render_template(
        'marketing/assets/upload.html',
        campaigns=campaigns,
        _=_
    )


@marketing_bp.route('/assets/generate', methods=['GET', 'POST'])
@login_required
def generate_asset():
    """Générer une ressource marketing avec IA"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Cette fonction sera implémentée dans une version future
        # Pour l'instant, on va afficher un message d'information
        flash(_('feature_coming_soon'), 'info')
        return redirect(url_for('marketing.list_assets'))
    
    # Récupérer les campagnes pour le dropdown
    campaigns = MarketingCampaign.query.filter_by(user_id=user.id).all()
    
    return render_template(
        'marketing/assets/generate.html',
        campaigns=campaigns,
        _=_
    )


@marketing_bp.route('/analytics')
@login_required
def marketing_analytics():
    """Visualiser les analytics marketing"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    # Cette fonction sera implémentée dans une version future
    # Pour l'instant, on va afficher une page avec des statistiques de base
    
    # Récupérer des statistiques de base
    campaigns_count = MarketingCampaign.query.filter_by(user_id=user.id).count()
    email_count = EmailContent.query.join(MarketingCampaign).filter(
        MarketingCampaign.user_id == user.id).count()
    social_posts_count = SocialMediaPost.query.join(MarketingCampaign).filter(
        MarketingCampaign.user_id == user.id).count()
    influencer_briefs_count = InfluencerBrief.query.join(MarketingCampaign).filter(
        MarketingCampaign.user_id == user.id).count()
    
    return render_template(
        'marketing/analytics.html',
        campaigns_count=campaigns_count,
        email_count=email_count,
        social_posts_count=social_posts_count,
        influencer_briefs_count=influencer_briefs_count,
        _=_
    )