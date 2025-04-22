"""
Module pour les modèles du système de modules métier
"""
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON

from models import db, User


class ModuleCategory(db.Model):
    """Modèle pour les catégories de modules métier"""
    __tablename__ = 'module_category'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), nullable=True)  # Nom d'icône ou classe CSS
    color = db.Column(db.String(20), nullable=True)  # Code couleur pour l'UI
    parent_id = db.Column(db.Integer, db.ForeignKey('module_category.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relation parent-enfant pour les sous-catégories
    subcategories = db.relationship('ModuleCategory', 
                                   backref=db.backref('parent', remote_side=[id]),
                                   lazy='dynamic')
    
    # Relation avec les modules
    modules = db.relationship('BusinessModule', backref='category', lazy='dynamic')
    
    def __repr__(self):
        return f'<ModuleCategory {self.name}>'


class BusinessModule(db.Model):
    """Modèle pour les modules métier"""
    __tablename__ = 'business_module'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    short_description = db.Column(db.String(255), nullable=True)
    version = db.Column(db.String(20), nullable=False, default="1.0.0")
    category_id = db.Column(db.Integer, db.ForeignKey('module_category.id'), nullable=True)
    icon = db.Column(db.String(255), nullable=True)  # URL de l'icône ou nom de classe
    banner_image = db.Column(db.String(255), nullable=True)  # URL de l'image de bannière
    author = db.Column(db.String(100), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    is_official = db.Column(db.Boolean, default=False)  # Module officiel ou tiers
    is_featured = db.Column(db.Boolean, default=False)  # Module mis en avant
    price = db.Column(db.Numeric(10, 2), nullable=True)  # Prix du module (null = gratuit)
    currency = db.Column(db.String(3), default="EUR")
    dependencies = db.Column(JSON, nullable=True)  # Liste des dépendances
    requirements = db.Column(db.Text, nullable=True)  # Requirements techniques
    installation_script = db.Column(db.Text, nullable=True)  # Script d'installation
    uninstallation_script = db.Column(db.Text, nullable=True)  # Script de désinstallation
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    publish_date = db.Column(db.DateTime, nullable=True)
    download_count = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="draft")  # draft, published, deprecated
    
    # Relation avec les versions
    versions = db.relationship('ModuleVersion', backref='module', lazy='dynamic')
    
    # Relation avec les avis
    reviews = db.relationship('ModuleReview', backref='module', lazy='dynamic')
    
    # Relation avec les installations utilisateur
    installations = db.relationship('UserModuleInstallation', backref='module', lazy='dynamic')
    
    def __repr__(self):
        return f'<BusinessModule {self.name} v{self.version}>'
    
    @property
    def average_rating(self):
        """Calcule la note moyenne des avis"""
        reviews = self.reviews.all()
        if not reviews:
            return 0
        return sum(review.rating for review in reviews) / len(reviews)
    
    @property
    def review_count(self):
        """Retourne le nombre d'avis"""
        return self.reviews.count()
    
    @property
    def installation_count(self):
        """Retourne le nombre d'installations"""
        return self.installations.count()


class ModuleVersion(db.Model):
    """Modèle pour les versions de modules métier"""
    __tablename__ = 'module_version'
    
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('business_module.id'), nullable=False)
    version_number = db.Column(db.String(20), nullable=False)
    release_notes = db.Column(db.Text, nullable=True)
    installation_script = db.Column(db.Text, nullable=True)  # Script d'installation spécifique à cette version
    dependencies = db.Column(JSON, nullable=True)  # Liste des dépendances spécifiques à cette version
    is_latest = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ModuleVersion {self.module.name} v{self.version_number}>'


class ModuleReview(db.Model):
    """Modèle pour les avis sur les modules"""
    __tablename__ = 'module_review'
    
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('business_module.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # Note de 1 à 5
    title = db.Column(db.String(100), nullable=True)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relation avec l'utilisateur
    user = db.relationship('User', backref=db.backref('module_reviews', lazy='dynamic'))
    
    def __repr__(self):
        return f'<ModuleReview {self.module.name}: {self.rating}/5>'


class UserModuleInstallation(db.Model):
    """Modèle pour les installations de modules par utilisateur"""
    __tablename__ = 'user_module_installation'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('business_module.id'), nullable=False)
    version_id = db.Column(db.Integer, db.ForeignKey('module_version.id'), nullable=True)
    installation_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="active")  # active, disabled, uninstalled
    settings = db.Column(JSON, nullable=True)  # Paramètres personnalisés
    
    # Relation avec l'utilisateur
    user = db.relationship('User', backref=db.backref('installed_modules', lazy='dynamic'))
    
    # Relation avec la version (optionnelle)
    version = db.relationship('ModuleVersion', backref=db.backref('installations', lazy='dynamic'))
    
    def __repr__(self):
        return f'<UserModuleInstallation {self.user.username}: {self.module.name}>'