"""
Module pour les modèles de données de l'API Marketplace
"""
from datetime import datetime
import json
from sqlalchemy.dialects.postgresql import JSON
from models import db, User


class MarketplaceExtension(db.Model):
    """Modèle pour les extensions et intégrations marketplace"""
    __tablename__ = 'marketplace_extension'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)
    short_description = db.Column(db.String(200), nullable=True)
    developer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    category = db.Column(db.String(50), nullable=False)
    subcategory = db.Column(db.String(50), nullable=True)
    extension_type = db.Column(db.String(50), nullable=False)  # 'connector', 'extension', 'template', 'integration'
    version = db.Column(db.String(20), nullable=False, default='1.0.0')
    icon_url = db.Column(db.String(255), nullable=True)
    cover_image = db.Column(db.String(255), nullable=True)
    screenshots = db.Column(db.Text, nullable=True)  # JSON list of screenshot URLs
    price_type = db.Column(db.String(20), nullable=False, default='free')  # 'free', 'paid', 'subscription'
    price = db.Column(db.Numeric(10, 2), nullable=True)  # NULL for free extensions
    currency = db.Column(db.String(3), nullable=True, default='USD')
    documentation_url = db.Column(db.String(255), nullable=True)
    support_email = db.Column(db.String(100), nullable=True)
    website_url = db.Column(db.String(255), nullable=True)
    configuration_schema = db.Column(db.Text, nullable=True)  # JSON schema for configuration
    api_spec = db.Column(db.Text, nullable=True)  # OpenAPI spec for API connectors
    sample_code = db.Column(db.Text, nullable=True)
    required_permissions = db.Column(db.Text, nullable=True)  # JSON list of required permissions
    is_published = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    is_featured = db.Column(db.Boolean, default=False)
    average_rating = db.Column(db.Float, default=0)
    downloads_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    developer = db.relationship('User', backref=db.backref('developed_extensions', lazy='dynamic'))
    installations = db.relationship('ExtensionInstallation', backref='extension', lazy='dynamic', cascade='all, delete-orphan')
    reviews = db.relationship('ExtensionReview', backref='extension', lazy='dynamic', cascade='all, delete-orphan')
    versions = db.relationship('ExtensionVersion', backref='extension', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<MarketplaceExtension {self.name}>'
    
    def get_screenshots(self):
        """Retourne les screenshots sous forme de liste"""
        if not self.screenshots:
            return []
        return json.loads(self.screenshots)
    
    def set_screenshots(self, screenshot_list):
        """Enregistre les screenshots à partir d'une liste"""
        self.screenshots = json.dumps(screenshot_list)
    
    def get_required_permissions(self):
        """Retourne les permissions requises sous forme de liste"""
        if not self.required_permissions:
            return []
        return json.loads(self.required_permissions)
    
    def set_required_permissions(self, permission_list):
        """Enregistre les permissions requises à partir d'une liste"""
        self.required_permissions = json.dumps(permission_list)
    
    def get_configuration_schema(self):
        """Retourne le schéma de configuration sous forme de dictionnaire"""
        if not self.configuration_schema:
            return {}
        return json.loads(self.configuration_schema)
    
    def set_configuration_schema(self, schema_dict):
        """Enregistre le schéma de configuration à partir d'un dictionnaire"""
        self.configuration_schema = json.dumps(schema_dict)


class ExtensionVersion(db.Model):
    """Modèle pour les versions d'une extension"""
    __tablename__ = 'marketplace_extension_version'
    
    id = db.Column(db.Integer, primary_key=True)
    extension_id = db.Column(db.Integer, db.ForeignKey('marketplace_extension.id'), nullable=False)
    version_number = db.Column(db.String(20), nullable=False)
    release_notes = db.Column(db.Text, nullable=True)
    download_url = db.Column(db.String(255), nullable=False)
    published_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    min_platform_version = db.Column(db.String(20), nullable=True)
    checksum = db.Column(db.String(64), nullable=True)  # SHA-256 hash
    file_size = db.Column(db.Integer, nullable=True)  # Size in bytes
    
    def __repr__(self):
        return f'<ExtensionVersion {self.extension_id}-{self.version_number}>'


class ExtensionInstallation(db.Model):
    """Modèle pour les installations d'extensions par les utilisateurs"""
    __tablename__ = 'marketplace_extension_installation'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    extension_id = db.Column(db.Integer, db.ForeignKey('marketplace_extension.id'), nullable=False)
    version = db.Column(db.String(20), nullable=False)
    installation_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    configuration = db.Column(db.Text, nullable=True)  # JSON configuration data
    usage_data = db.Column(db.Text, nullable=True)  # JSON usage statistics
    
    # Relations
    user = db.relationship('User', backref=db.backref('installed_extensions', lazy='dynamic'))
    
    def __repr__(self):
        return f'<ExtensionInstallation {self.user_id}-{self.extension_id}>'
    
    def get_configuration(self):
        """Retourne la configuration sous forme de dictionnaire"""
        if not self.configuration:
            return {}
        return json.loads(self.configuration)
    
    def set_configuration(self, config_dict):
        """Enregistre la configuration à partir d'un dictionnaire"""
        self.configuration = json.dumps(config_dict)
    
    def get_usage_data(self):
        """Retourne les données d'utilisation sous forme de dictionnaire"""
        if not self.usage_data:
            return {}
        return json.loads(self.usage_data)
    
    def set_usage_data(self, usage_dict):
        """Enregistre les données d'utilisation à partir d'un dictionnaire"""
        self.usage_data = json.dumps(usage_dict)


class ExtensionReview(db.Model):
    """Modèle pour les avis sur les extensions"""
    __tablename__ = 'marketplace_extension_review'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    extension_id = db.Column(db.Integer, db.ForeignKey('marketplace_extension.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    title = db.Column(db.String(100), nullable=True)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_approved = db.Column(db.Boolean, default=True)
    
    # Relations
    user = db.relationship('User', backref=db.backref('extension_reviews', lazy='dynamic'))
    
    def __repr__(self):
        return f'<ExtensionReview {self.user_id}-{self.extension_id}>'


class ApiConnection(db.Model):
    """Modèle pour les connexions API configurées par les utilisateurs"""
    __tablename__ = 'marketplace_api_connection'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    extension_id = db.Column(db.Integer, db.ForeignKey('marketplace_extension.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    api_key = db.Column(db.Text, nullable=True)  # Encrypted API key or token
    credentials = db.Column(db.Text, nullable=True)  # Encrypted JSON credentials
    endpoint_url = db.Column(db.String(255), nullable=True)
    last_connected = db.Column(db.DateTime, nullable=True)
    connection_status = db.Column(db.String(20), default='pending')  # 'pending', 'active', 'error'
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', backref=db.backref('api_connections', lazy='dynamic'))
    extension = db.relationship('MarketplaceExtension')
    
    def __repr__(self):
        return f'<ApiConnection {self.name}>'
    
    def get_credentials(self):
        """Retourne les identifiants décryptés sous forme de dictionnaire"""
        if not self.credentials:
            return {}
        # Note: Dans une implémentation réelle, décrypter les données ici
        return json.loads(self.credentials)
    
    def set_credentials(self, credentials_dict):
        """Enregistre les identifiants sous forme cryptée"""
        # Note: Dans une implémentation réelle, crypter les données ici
        self.credentials = json.dumps(credentials_dict)


class AutomationTemplate(db.Model):
    """Modèle pour les modèles d'automatisation"""
    __tablename__ = 'marketplace_automation_template'
    
    id = db.Column(db.Integer, primary_key=True)
    extension_id = db.Column(db.Integer, db.ForeignKey('marketplace_extension.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    workflow_definition = db.Column(db.Text, nullable=False)  # JSON workflow definition
    input_schema = db.Column(db.Text, nullable=True)  # JSON schema for inputs
    output_schema = db.Column(db.Text, nullable=True)  # JSON schema for outputs
    category = db.Column(db.String(50), nullable=False)
    difficulty_level = db.Column(db.String(20), default='beginner')  # 'beginner', 'intermediate', 'advanced'
    estimated_time_minutes = db.Column(db.Integer, nullable=True)
    is_featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    extension = db.relationship('MarketplaceExtension')
    instances = db.relationship('AutomationInstance', backref='template', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<AutomationTemplate {self.name}>'
    
    def get_workflow_definition(self):
        """Retourne la définition du workflow sous forme de dictionnaire"""
        return json.loads(self.workflow_definition)
    
    def set_workflow_definition(self, workflow_dict):
        """Enregistre la définition du workflow à partir d'un dictionnaire"""
        self.workflow_definition = json.dumps(workflow_dict)
    
    def get_input_schema(self):
        """Retourne le schéma d'entrée sous forme de dictionnaire"""
        if not self.input_schema:
            return {}
        return json.loads(self.input_schema)
    
    def set_input_schema(self, schema_dict):
        """Enregistre le schéma d'entrée à partir d'un dictionnaire"""
        self.input_schema = json.dumps(schema_dict)
    
    def get_output_schema(self):
        """Retourne le schéma de sortie sous forme de dictionnaire"""
        if not self.output_schema:
            return {}
        return json.loads(self.output_schema)
    
    def set_output_schema(self, schema_dict):
        """Enregistre le schéma de sortie à partir d'un dictionnaire"""
        self.output_schema = json.dumps(schema_dict)


class AutomationInstance(db.Model):
    """Modèle pour les instances d'automatisation créées par les utilisateurs"""
    __tablename__ = 'marketplace_automation_instance'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('marketplace_automation_template.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    configuration = db.Column(db.Text, nullable=False)  # JSON configuration
    status = db.Column(db.String(20), default='active')  # 'active', 'paused', 'error'
    last_run = db.Column(db.DateTime, nullable=True)
    success_count = db.Column(db.Integer, default=0)
    error_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', backref=db.backref('automation_instances', lazy='dynamic'))
    
    def __repr__(self):
        return f'<AutomationInstance {self.name}>'
    
    def get_configuration(self):
        """Retourne la configuration sous forme de dictionnaire"""
        return json.loads(self.configuration)
    
    def set_configuration(self, config_dict):
        """Enregistre la configuration à partir d'un dictionnaire"""
        self.configuration = json.dumps(config_dict)