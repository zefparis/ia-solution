"""
Modèles pour le service d'analyse des processus d'entreprise.
"""

from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from flask_sqlalchemy import SQLAlchemy

# Import db from outside to avoid circular imports
try:
    from main import db
except ImportError:
    # Configuration en mode autonome pour les tests
    db = SQLAlchemy()


class BusinessProcess(db.Model):
    """Modèle pour les processus d'entreprise identifiés."""
    __tablename__ = 'business_processes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), nullable=False, index=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    department = db.Column(db.String(50))
    current_state = db.Column(JSONB)  # État actuel du processus (diagramme, étapes, etc.)
    pain_points = db.Column(JSONB)  # Points de douleur identifiés
    kpis = db.Column(JSONB)  # Indicateurs clés de performance
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    optimizations = db.relationship('ProcessOptimization', back_populates='process', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<BusinessProcess {self.name}>'


class ProcessOptimization(db.Model):
    """Modèle pour les optimisations proposées pour un processus."""
    __tablename__ = 'process_optimizations'
    
    id = db.Column(db.Integer, primary_key=True)
    process_id = db.Column(db.Integer, db.ForeignKey('business_processes.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    benefits = db.Column(JSONB)  # Bénéfices attendus (gains de temps, économies, etc.)
    implementation_plan = db.Column(JSONB)  # Plan de mise en œuvre
    resources_required = db.Column(JSONB)  # Ressources nécessaires
    estimated_roi = db.Column(db.Float)  # ROI estimé
    priority = db.Column(db.String(20))  # Haute, Moyenne, Basse
    status = db.Column(db.String(20), default='proposed')  # proposed, approved, in_progress, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    process = db.relationship('BusinessProcess', back_populates='optimizations')
    milestones = db.relationship('ImplementationMilestone', back_populates='optimization', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<ProcessOptimization {self.title}>'


class ImplementationMilestone(db.Model):
    """Modèle pour les jalons de mise en œuvre des optimisations."""
    __tablename__ = 'implementation_milestones'
    
    id = db.Column(db.Integer, primary_key=True)
    optimization_id = db.Column(db.Integer, db.ForeignKey('process_optimizations.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    planned_date = db.Column(db.Date)
    completed_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed, delayed
    completion_percentage = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    optimization = db.relationship('ProcessOptimization', back_populates='milestones')
    
    def __repr__(self):
        return f'<ImplementationMilestone {self.title}>'


class ResultMeasurement(db.Model):
    """Modèle pour les mesures de résultats des optimisations."""
    __tablename__ = 'result_measurements'
    
    id = db.Column(db.Integer, primary_key=True)
    optimization_id = db.Column(db.Integer, db.ForeignKey('process_optimizations.id'), nullable=False)
    metric_name = db.Column(db.String(100), nullable=False)
    baseline_value = db.Column(db.Float)
    target_value = db.Column(db.Float)
    current_value = db.Column(db.Float)
    unit = db.Column(db.String(50))
    measurement_date = db.Column(db.Date, default=datetime.utcnow)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    optimization = db.relationship('ProcessOptimization')
    
    def __repr__(self):
        return f'<ResultMeasurement {self.metric_name}>'