from datetime import datetime
import json
from models import db  # Import db from models.py

class BusinessReport(db.Model):
    """Modèle pour stocker les analyses business personnalisées"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Informations sur l'entreprise
    company_name = db.Column(db.String(100), nullable=False)
    industry = db.Column(db.String(50), nullable=False)
    company_size = db.Column(db.String(20), nullable=False)
    company_age = db.Column(db.String(20), nullable=False)
    annual_revenue = db.Column(db.String(20))
    
    # Défis et objectifs
    business_challenges = db.Column(db.Text, nullable=False)
    growth_goals = db.Column(db.Text, nullable=False)
    current_strengths = db.Column(db.Text)
    improvement_areas = db.Column(db.String(500), nullable=False)  # Liste stockée en format JSON
    additional_info = db.Column(db.Text)
    
    # Résultats de l'analyse
    analysis_summary = db.Column(db.Text)
    strengths = db.Column(db.Text)  # Liste stockée en format JSON
    weaknesses = db.Column(db.Text)  # Liste stockée en format JSON
    opportunities = db.Column(db.Text)  # Liste stockée en format JSON
    threats = db.Column(db.Text)  # Liste stockée en format JSON
    recommendations = db.Column(db.Text)  # Liste stockée en format JSON
    action_plan = db.Column(db.Text)  # Liste stockée en format JSON
    
    # Métadonnées
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    email_sent = db.Column(db.Boolean, default=False)
    
    # Relations
    user = db.relationship('User', backref=db.backref('business_reports', lazy=True))
    
    def __repr__(self):
        return f'<BusinessReport {self.id}: {self.company_name}>'
    
    def get_improvement_areas_list(self):
        """Convertir la chaîne JSON en liste"""
        if not self.improvement_areas:
            return []
        return json.loads(self.improvement_areas)
    
    def set_improvement_areas_list(self, areas_list):
        """Convertir la liste en chaîne JSON"""
        self.improvement_areas = json.dumps(areas_list)
    
    def get_strengths_list(self):
        """Convertir la chaîne JSON en liste"""
        if not self.strengths:
            return []
        return json.loads(self.strengths)
    
    def set_strengths_list(self, strengths_list):
        """Convertir la liste en chaîne JSON"""
        self.strengths = json.dumps(strengths_list)
    
    def get_weaknesses_list(self):
        """Convertir la chaîne JSON en liste"""
        if not self.weaknesses:
            return []
        return json.loads(self.weaknesses)
    
    def set_weaknesses_list(self, weaknesses_list):
        """Convertir la liste en chaîne JSON"""
        self.weaknesses = json.dumps(weaknesses_list)
    
    def get_opportunities_list(self):
        """Convertir la chaîne JSON en liste"""
        if not self.opportunities:
            return []
        return json.loads(self.opportunities)
    
    def set_opportunities_list(self, opportunities_list):
        """Convertir la liste en chaîne JSON"""
        self.opportunities = json.dumps(opportunities_list)
    
    def get_threats_list(self):
        """Convertir la chaîne JSON en liste"""
        if not self.threats:
            return []
        return json.loads(self.threats)
    
    def set_threats_list(self, threats_list):
        """Convertir la liste en chaîne JSON"""
        self.threats = json.dumps(threats_list)
    
    def get_recommendations_dict(self):
        """Convertir la chaîne JSON en dictionnaire"""
        if not self.recommendations:
            return {}
        return json.loads(self.recommendations)
    
    def set_recommendations_dict(self, recommendations_dict):
        """Convertir le dictionnaire en chaîne JSON"""
        self.recommendations = json.dumps(recommendations_dict)
    
    def get_action_plan_list(self):
        """Convertir la chaîne JSON en liste"""
        if not self.action_plan:
            return []
        return json.loads(self.action_plan)
    
    def set_action_plan_list(self, action_plan_list):
        """Convertir la liste en chaîne JSON"""
        self.action_plan = json.dumps(action_plan_list)
    
    def to_dict(self):
        """Convertir l'objet en dictionnaire pour l'affichage"""
        return {
            'id': self.id,
            'company_name': self.company_name,
            'industry': self.industry,
            'company_size': self.company_size,
            'company_age': self.company_age,
            'annual_revenue': self.annual_revenue,
            'business_challenges': self.business_challenges,
            'growth_goals': self.growth_goals,
            'current_strengths': self.current_strengths,
            'improvement_areas': self.get_improvement_areas_list(),
            'additional_info': self.additional_info,
            'analysis_summary': self.analysis_summary,
            'strengths': self.get_strengths_list(),
            'weaknesses': self.get_weaknesses_list(),
            'opportunities': self.get_opportunities_list(),
            'threats': self.get_threats_list(),
            'recommendations': self.get_recommendations_dict(),
            'action_plan': self.get_action_plan_list(),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }