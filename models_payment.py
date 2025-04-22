"""
Modèles de données pour le système de paiement UniPesa
"""
from datetime import datetime
from models import db

class UniPesaPayment(db.Model):
    """Modèle pour les paiements mobiles via UniPesa"""
    __tablename__ = 'unipesa_payment'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    transaction_id = db.Column(db.String(100), unique=True, nullable=False)
    reference = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, success, failed
    description = db.Column(db.String(255), nullable=True)
    
    # Données de l'abonnement
    subscription_plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plan.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    callback_data = db.Column(db.Text, nullable=True)  # Stocke les données brutes du callback
    
    # Relations
    user = db.relationship('User', backref=db.backref('unipesa_payments', lazy='dynamic'))
    subscription_plan = db.relationship('SubscriptionPlan', backref=db.backref('unipesa_payments', lazy='dynamic'))
    
    def __repr__(self):
        return f'<UniPesaPayment {self.transaction_id} - {self.status}>'
    
    @classmethod
    def get_by_transaction_id(cls, transaction_id):
        """Récupère un paiement par son ID de transaction"""
        return cls.query.filter_by(transaction_id=transaction_id).first()
    
    @classmethod
    def get_by_reference(cls, reference):
        """Récupère un paiement par sa référence"""
        return cls.query.filter_by(reference=reference).first()
    
    @classmethod
    def get_user_payments(cls, user_id):
        """Récupère tous les paiements d'un utilisateur"""
        return cls.query.filter_by(user_id=user_id).order_by(cls.created_at.desc()).all()
    
    def update_status(self, status, callback_data=None):
        """Met à jour le statut d'un paiement"""
        self.status = status
        if callback_data:
            self.callback_data = callback_data
        db.session.commit()