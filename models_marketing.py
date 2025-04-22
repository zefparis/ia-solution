"""
Module pour les modèles de la fonctionnalité Marketing IA
"""
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON

from main import db


class MarketingCampaign(db.Model):
    """Modèle pour les campagnes marketing"""
    __tablename__ = 'marketing_campaign'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    campaign_type = db.Column(db.String(50), nullable=False)  # 'email', 'social', 'influencer'
    status = db.Column(db.String(20), nullable=False, default='draft')  # 'draft', 'scheduled', 'active', 'completed', 'paused'
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    target_audience = db.Column(db.Text, nullable=True)  # Description de l'audience cible
    budget = db.Column(db.Numeric(10, 2), nullable=True)  # Budget alloué
    performance_metrics = db.Column(JSON, nullable=True)  # KPIs stockés en JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    user = db.relationship('User', backref=db.backref('marketing_campaigns', lazy='dynamic'))
    email_contents = db.relationship('EmailContent', backref='campaign', lazy='dynamic', cascade="all, delete-orphan")
    social_posts = db.relationship('SocialMediaPost', backref='campaign', lazy='dynamic', cascade="all, delete-orphan")
    influencer_briefs = db.relationship('InfluencerBrief', backref='campaign', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<MarketingCampaign {self.name}>'


class EmailContent(db.Model):
    """Modèle pour le contenu des emails marketing"""
    __tablename__ = 'email_content'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('marketing_campaign.id'), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    preview_text = db.Column(db.String(255), nullable=True)
    html_content = db.Column(db.Text, nullable=False)
    text_content = db.Column(db.Text, nullable=True)
    is_template = db.Column(db.Boolean, default=False)  # Si c'est un template réutilisable
    schedule_date = db.Column(db.DateTime, nullable=True)  # Date planifiée d'envoi
    sent_date = db.Column(db.DateTime, nullable=True)  # Date réelle d'envoi
    status = db.Column(db.String(20), nullable=False, default='draft')  # 'draft', 'scheduled', 'sent', 'failed'
    recipient_list = db.Column(JSON, nullable=True)  # Liste des destinataires en JSON
    open_rate = db.Column(db.Float, nullable=True)  # Taux d'ouverture
    click_rate = db.Column(db.Float, nullable=True)  # Taux de clic
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<EmailContent {self.subject}>'


class SocialMediaPost(db.Model):
    """Modèle pour les publications sur réseaux sociaux"""
    __tablename__ = 'social_media_post'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('marketing_campaign.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)  # 'facebook', 'instagram', 'twitter', 'linkedin', etc.
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)  # URL de l'image
    video_url = db.Column(db.String(255), nullable=True)  # URL de la vidéo
    hashtags = db.Column(db.String(255), nullable=True)  # Hashtags associés
    status = db.Column(db.String(20), nullable=False, default='draft')  # 'draft', 'scheduled', 'published', 'failed'
    schedule_date = db.Column(db.DateTime, nullable=True)  # Date planifiée
    published_date = db.Column(db.DateTime, nullable=True)  # Date réelle de publication
    post_url = db.Column(db.String(255), nullable=True)  # URL de la publication après publication
    engagement_metrics = db.Column(JSON, nullable=True)  # Likes, shares, comments en JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SocialMediaPost {self.platform} {self.id}>'


class InfluencerBrief(db.Model):
    """Modèle pour les briefs d'influenceurs"""
    __tablename__ = 'influencer_brief'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('marketing_campaign.id'), nullable=False)
    influencer_name = db.Column(db.String(100), nullable=False)
    influencer_contact = db.Column(db.String(255), nullable=True)  # Email ou autre contact
    influencer_platform = db.Column(db.String(50), nullable=False)  # 'instagram', 'tiktok', 'youtube', etc.
    influencer_audience = db.Column(db.Text, nullable=True)  # Description de l'audience
    brief_content = db.Column(db.Text, nullable=False)  # Contenu du brief
    objectives = db.Column(db.Text, nullable=False)  # Objectifs de la collaboration
    deliverables = db.Column(db.Text, nullable=False)  # Livrables attendus
    key_messages = db.Column(db.Text, nullable=True)  # Messages clés à communiquer
    budget = db.Column(db.Numeric(10, 2), nullable=True)  # Budget pour cet influenceur
    status = db.Column(db.String(20), nullable=False, default='draft')  # 'draft', 'proposed', 'accepted', 'in_progress', 'completed'
    timeline = db.Column(db.JSON, nullable=True)  # Étapes clés en JSON
    results = db.Column(db.JSON, nullable=True)  # Résultats en JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<InfluencerBrief {self.influencer_name}>'


class ContentGeneration(db.Model):
    """Modèle pour stocker les contenus générés par IA"""
    __tablename__ = 'content_generation'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content_type = db.Column(db.String(50), nullable=False)  # 'email', 'social', 'blog', 'ad', etc.
    prompt = db.Column(db.Text, nullable=False)  # Prompt utilisé pour générer le contenu
    generated_content = db.Column(db.Text, nullable=False)  # Contenu généré
    platform = db.Column(db.String(50), nullable=True)  # Plateforme cible si applicable
    business_sector = db.Column(db.String(100), nullable=True)  # Secteur d'activité
    language = db.Column(db.String(10), nullable=False, default='fr')  # Langue du contenu
    is_favorite = db.Column(db.Boolean, default=False)  # Si marqué comme favori
    is_used = db.Column(db.Boolean, default=False)  # Si utilisé dans une campagne
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    user = db.relationship('User', backref=db.backref('generated_contents', lazy='dynamic'))

    def __repr__(self):
        return f'<ContentGeneration {self.content_type} {self.id}>'


class MarketingSchedule(db.Model):
    """Modèle pour le calendrier éditorial IA"""
    __tablename__ = 'marketing_schedule'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    schedule_type = db.Column(db.String(50), nullable=False)  # 'editorial', 'campaign', 'social', etc.
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    frequency = db.Column(db.String(50), nullable=True)  # 'daily', 'weekly', 'monthly', etc.
    platforms = db.Column(db.JSON, nullable=True)  # Plateformes couvertes
    topics = db.Column(db.JSON, nullable=True)  # Sujets planifiés
    generated_schedule = db.Column(db.JSON, nullable=True)  # Calendrier généré par l'IA
    status = db.Column(db.String(20), nullable=False, default='draft')  # 'draft', 'active', 'completed', 'archived'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    user = db.relationship('User', backref=db.backref('marketing_schedules', lazy='dynamic'))

    def __repr__(self):
        return f'<MarketingSchedule {self.title}>'


class EditorialCalendarEntry(db.Model):
    """Modèle pour les entrées du calendrier éditorial"""
    __tablename__ = 'editorial_calendar_entry'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('marketing_schedule.id'), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    content_type = db.Column(db.String(50), nullable=False)  # 'email', 'social', 'blog', 'ad', etc.
    platform = db.Column(db.String(50), nullable=True)  # 'facebook', 'instagram', 'twitter', 'linkedin', etc.
    scheduled_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='planned')  # 'planned', 'in_progress', 'completed', 'cancelled'
    topic = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', backref=db.backref('calendar_entries', lazy='dynamic'))
    schedule = db.relationship('MarketingSchedule', backref=db.backref('entries', lazy='dynamic'))
    
    def __repr__(self):
        return f'<EditorialCalendarEntry {self.id} - {self.title}>'

    def to_calendar_event(self):
        """Convertit l'entrée en format événement pour le calendrier fullcalendar.js"""
        # Déterminer la couleur en fonction du type de contenu
        color_map = {
            'email': 'primary',
            'social': 'info',
            'blog': 'success',
            'ad': 'warning',
            'other': 'secondary'
        }
        
        color = color_map.get(self.content_type, 'secondary')
        
        return {
            'id': self.id,
            'title': self.title,
            'start': self.scheduled_date.isoformat(),
            'allDay': False,
            'description': self.description,
            'platform': self.platform,
            'content_type': self.content_type,
            'className': f'bg-{color}',
            'extendedProps': {
                'status': self.status,
                'topic': self.topic,
                'notes': self.notes
            }
        }


class MarketingAsset(db.Model):
    """Modèle pour les ressources marketing (images, bannières, etc.)"""
    __tablename__ = 'marketing_asset'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey('marketing_campaign.id'), nullable=True)
    asset_type = db.Column(db.String(50), nullable=False)  # 'image', 'banner', 'logo', 'video', etc.
    asset_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    s3_key = db.Column(db.String(255), nullable=False)  # Chemin dans S3
    url = db.Column(db.String(500), nullable=True)  # URL publique
    dimensions = db.Column(db.String(20), nullable=True)  # Format "largeurxhauteur"
    file_size = db.Column(db.Integer, nullable=True)  # Taille en octets
    file_type = db.Column(db.String(50), nullable=True)  # MIME type
    tags = db.Column(db.JSON, nullable=True)  # Tags pour faciliter la recherche
    is_generated = db.Column(db.Boolean, default=False)  # Si généré par IA
    generation_prompt = db.Column(db.Text, nullable=True)  # Prompt utilisé pour la génération
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    user = db.relationship('User', backref=db.backref('marketing_assets', lazy='dynamic'))
    campaign = db.relationship('MarketingCampaign', backref=db.backref('assets', lazy='dynamic'))

    def __repr__(self):
        return f'<MarketingAsset {self.asset_name}>'