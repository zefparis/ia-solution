"""
Module pour les modèles additionnels du tableau de bord financier
"""
from datetime import datetime
from models import db, User


class TransactionCategory(db.Model):
    """Modèle pour les catégories de transactions financières"""
    __tablename__ = 'transaction_category'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'expense' ou 'income'
    color = db.Column(db.String(10), nullable=True)  # Code couleur pour l'UI
    icon = db.Column(db.String(50), nullable=True)  # Icône associée
    
    # Relation avec l'utilisateur
    user = db.relationship('User', backref=db.backref('transaction_categories', lazy='dynamic'))
    
    # Relation avec les transactions
    transactions = db.relationship('Transaction', backref='category', lazy='dynamic')
    
    def __repr__(self):
        return f'<TransactionCategory {self.name}: {self.type}>'


class Transaction(db.Model):
    """Modèle pour les transactions financières"""
    __tablename__ = 'transaction'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('transaction_category.id'), nullable=True)
    description = db.Column(db.String(255), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    
    # Relations
    user = db.relationship('User', backref=db.backref('user_transactions', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Transaction {self.id}: {self.amount}€ - {self.description or "Sans description"}>'


class CashflowPrediction(db.Model):
    """Modèle pour stocker les prédictions de flux de trésorerie"""
    __tablename__ = 'cashflow_prediction'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    prediction_date = db.Column(db.Date, nullable=False)
    predicted_income = db.Column(db.Numeric(10, 2), nullable=False)
    predicted_expense = db.Column(db.Numeric(10, 2), nullable=False)
    confidence_score = db.Column(db.Float, nullable=True)  # Score de confiance de 0 à 1
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', backref=db.backref('cashflow_predictions', lazy='dynamic'))
    
    def __repr__(self):
        return f'<CashflowPrediction {self.prediction_date}: Income={self.predicted_income}, Expense={self.predicted_expense}>'


class FinancialAlert(db.Model):
    """Modèle pour les alertes financières"""
    __tablename__ = 'financial_alert'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    alert_level = db.Column(db.String(20), nullable=False)  # 'info', 'warning', 'danger'
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime, nullable=True)  # Date d'expiration de l'alerte
    
    # Relations
    user = db.relationship('User', backref=db.backref('financial_alerts', lazy='dynamic'))
    
    def __repr__(self):
        return f'<FinancialAlert {self.title}: {self.alert_level}>'


class DashboardSettings(db.Model):
    """Modèle pour stocker les préférences du tableau de bord"""
    __tablename__ = 'dashboard_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    layout = db.Column(db.Text, nullable=True)  # JSON avec la disposition des widgets
    widgets_visibility = db.Column(db.Text, nullable=True)  # JSON avec la visibilité des widgets
    theme = db.Column(db.String(50), nullable=True, default='dark')  # Thème préféré
    period_days = db.Column(db.Integer, nullable=True, default=180)  # Période d'analyse en jours
    prediction_months = db.Column(db.Integer, nullable=True, default=6)  # Mois de prévision
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', backref=db.backref('dashboard_settings', uselist=False))
    
    def __repr__(self):
        return f'<DashboardSettings for user_id={self.user_id}>'