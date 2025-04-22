from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class SubscriptionPlan(db.Model):
    """Modèle pour les plans d'abonnement disponibles"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)  # 'free', 'essential', 'pro', 'premium'
    display_name = db.Column(db.String(50), nullable=False)  # Nom affiché à l'utilisateur
    price = db.Column(db.Numeric(6, 2), nullable=False)  # Prix mensuel
    currency = db.Column(db.String(3), nullable=False, default='EUR')  # Devise (EUR ou USD)
    storage_limit = db.Column(db.BigInteger, nullable=False)  # Limite de stockage en octets
    description = db.Column(db.Text, nullable=True)  # Description du plan
    features = db.Column(db.Text, nullable=True)  # Liste des fonctionnalités séparées par des virgules
    is_active = db.Column(db.Boolean, default=True)  # Si le plan est disponible
    region = db.Column(db.String(10), nullable=True)  # Région cible (ex: 'rdc' pour République Démocratique du Congo)
    
    # Relation avec les abonnements
    subscriptions = db.relationship('Subscription', backref='plan', lazy='dynamic')
    
    def __repr__(self):
        currency_symbol = '$' if self.currency == 'USD' else '€'
        return f'<SubscriptionPlan {self.name}: {self.price}{currency_symbol}>'

class Subscription(db.Model):
    """Modèle pour les abonnements des utilisateurs"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plan.id'), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)  # Date de fin d'abonnement
    is_trial = db.Column(db.Boolean, default=False)  # Si c'est une période d'essai
    is_active = db.Column(db.Boolean, default=True)  # Si l'abonnement est actif
    auto_renew = db.Column(db.Boolean, default=True)  # Renouvellement automatique
    last_payment_date = db.Column(db.DateTime, nullable=True)  # Date du dernier paiement
    next_payment_date = db.Column(db.DateTime, nullable=True)  # Date du prochain paiement
    payment_method = db.Column(db.String(50), nullable=True)  # Méthode de paiement utilisée
    
    # Relation avec l'utilisateur
    user = db.relationship('User', backref=db.backref('subscriptions', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Subscription {self.id}: {self.plan.name} - {self.end_date.strftime("%Y-%m-%d")}>'
    
    @property
    def is_expired(self):
        """Vérifier si l'abonnement est expiré"""
        return self.end_date < datetime.utcnow()
    
    @property
    def days_remaining(self):
        """Calculer le nombre de jours restants"""
        if self.is_expired:
            return 0
        delta = self.end_date - datetime.utcnow()
        return delta.days
    
    @classmethod
    def create_trial(cls, user_id, days=14):
        """Créer un abonnement d'essai pour un nouvel utilisateur"""
        # Chercher le plan gratuit
        free_plan = SubscriptionPlan.query.filter_by(name='Essai gratuit').first()
        if not free_plan:
            return None
        
        # Créer l'abonnement d'essai
        end_date = datetime.utcnow() + timedelta(days=days)
        trial = cls(
            user_id=user_id,
            plan_id=free_plan.id,
            end_date=end_date,
            is_trial=True,
            auto_renew=False
        )
        
        db.session.add(trial)
        db.session.commit()
        return trial


class User(db.Model):
    """Model for storing user information (AWS Cognito)"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)  # Username est maintenant l'email
    email = db.Column(db.String(120), unique=True, nullable=False)
    display_name = db.Column(db.String(80), nullable=True)  # Nom d'affichage de l'utilisateur
    profile_picture = db.Column(db.String(255), nullable=True)  # Chemin vers la photo de profil
    cognito_id = db.Column(db.String(36), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    
    # S3 bucket info
    s3_bucket_name = db.Column(db.String(255), nullable=True)  # Nom du bucket S3 de l'utilisateur
    storage_used = db.Column(db.BigInteger, default=0)  # Stockage utilisé en octets
    last_storage_check = db.Column(db.DateTime, nullable=True)  # Dernière vérification du stockage
    
    # Relationship to conversations
    conversations = db.relationship('Conversation', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    @property
    def active_subscription(self):
        """Retourne l'abonnement actif de l'utilisateur"""
        # Utiliser SQL brut pour éviter les problèmes avec les colonnes ajoutées récemment
        from sqlalchemy.sql import text
        conn = db.engine.connect()
        result = conn.execute(text(
            f"SELECT id, user_id, plan_id, start_date, end_date, is_trial, is_active, auto_renew, last_payment_date, next_payment_date "
            f"FROM subscription WHERE user_id = {self.id} AND is_active = true ORDER BY end_date DESC LIMIT 1"
        ))
        row = result.fetchone()
        if not row:
            return None
            
        # Créer manuellement un objet Subscription sans utiliser le modèle complet
        sub = Subscription(
            id=row[0],
            user_id=row[1],
            plan_id=row[2],
            start_date=row[3],
            end_date=row[4],
            is_trial=row[5],
            is_active=row[6],
            auto_renew=row[7],
            last_payment_date=row[8],
            next_payment_date=row[9]
        )
        return sub
    
    @property
    def subscription_plan(self):
        """Retourne le plan d'abonnement actif de l'utilisateur"""
        active_sub = self.active_subscription
        if active_sub:
            return active_sub.plan
        return None
    
    @property
    def storage_limit(self):
        """Retourne la limite de stockage de l'utilisateur en octets"""
        plan = self.subscription_plan
        if plan:
            # Convertir GB en octets
            return plan.storage_limit * 1024 * 1024 * 1024
        return 1024 * 1024 * 100  # 100 MB par défaut
    
    @property
    def storage_percentage(self):
        """Retourne le pourcentage de stockage utilisé"""
        if self.storage_limit == 0:
            return 100
        return min(100, int((self.storage_used / self.storage_limit) * 100))

class Conversation(db.Model):
    """Model for storing conversations"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Nullable pour la rétro-compatibilité
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to messages
    messages = db.relationship('Message', backref='conversation', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Conversation {self.id}>'


class Message(db.Model):
    """Model for storing individual messages in a conversation"""
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Message {self.id}: {self.role}>'
    
    def to_dict(self):
        """Convert message to a dictionary format for Mistral API"""
        return {
            'role': self.role,
            'content': self.content
        }


class ExtractedText(db.Model):
    """Model for storing text extracted from images"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    title = db.Column(db.String(255), nullable=True)
    content = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(50), default="camera", nullable=False)  # 'camera', 'upload', etc.
    confidence = db.Column(db.Float, nullable=True)  # Score de confiance de l'OCR
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Classification pour comptabilité
    is_processed = db.Column(db.Boolean, default=False)  # Si le document a été traité
    document_type = db.Column(db.String(50), nullable=True)  # Facture, reçu, relevé bancaire, etc.
    
    # Relation avec une transaction (si identifiée)
    transaction_id = db.Column(db.Integer, db.ForeignKey('financial_transaction.id'), nullable=True)
    
    # Relationship to user
    user = db.relationship('User', backref=db.backref('extracted_texts', lazy='dynamic'))
    
    def __repr__(self):
        return f'<ExtractedText {self.id}: {self.title or "Untitled"}>'


class Category(db.Model):
    """Catégories de dépenses et revenus"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'expense' ou 'income'
    color = db.Column(db.String(10), nullable=True)  # Code couleur pour l'UI
    icon = db.Column(db.String(50), nullable=True)  # Icône associée
    
    # Relation avec l'utilisateur
    user = db.relationship('User', backref=db.backref('categories', lazy='dynamic'))
    
    # Relations avec les transactions
    transactions = db.relationship('FinancialTransaction', backref='category', lazy='dynamic')
    
    def __repr__(self):
        return f'<Category {self.name}: {self.type}>'


class FinancialTransaction(db.Model):
    """Transactions financières (dépenses ou revenus)"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)  # Montant avec 2 décimales
    description = db.Column(db.String(255), nullable=True)
    transaction_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_expense = db.Column(db.Boolean, default=True)  # True = dépense, False = revenu
    payment_method = db.Column(db.String(50), nullable=True)  # Carte, espèces, virement, etc.
    
    # TVA et taxes
    tax_rate = db.Column(db.Numeric(5, 2), nullable=True)  # Taux de TVA en pourcentage
    tax_amount = db.Column(db.Numeric(10, 2), nullable=True)  # Montant de la TVA
    
    # Relation avec le document extrait
    extracted_texts = db.relationship('ExtractedText', backref='transaction', lazy='dynamic')
    
    # Relation avec l'utilisateur
    user = db.relationship('User', backref=db.backref('transactions', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Transaction {self.id}: {self.amount}€ - {self.description or "Sans description"}>'


class Vendor(db.Model):
    """Fournisseurs/Commerçants"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text, nullable=True)
    contact = db.Column(db.String(100), nullable=True)
    siret = db.Column(db.String(20), nullable=True)  # Numéro SIRET pour les entreprises françaises
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relation avec l'utilisateur
    user = db.relationship('User', backref=db.backref('vendors', lazy='dynamic'))
    
    # Relation avec les transactions
    transactions = db.relationship('FinancialTransaction', 
                                 secondary='vendor_transaction',
                                 backref=db.backref('vendors', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Vendor {self.name}>'


# Table d'association entre vendors et transactions
vendor_transaction = db.Table('vendor_transaction',
    db.Column('vendor_id', db.Integer, db.ForeignKey('vendor.id'), primary_key=True),
    db.Column('transaction_id', db.Integer, db.ForeignKey('financial_transaction.id'), primary_key=True)
)


class TaxReport(db.Model):
    """Rapports fiscaux"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # On conserve title pour la compatibilité, mais on ajoute name qui sera utilisé par notre nouvelle interface
    title = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=True)  # Pour la nouvelle interface
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    report_type = db.Column(db.String(50), nullable=True)  # Trimestriel, annuel, etc.
    status = db.Column(db.String(50), default='draft')  # draft, submitted, etc.
    
    # Contenu du rapport
    report_html = db.Column(db.Text, nullable=True)  # Contenu HTML généré par OpenAI
    ai_analysis = db.Column(db.Text, nullable=True)  # Analyse IA pour la nouvelle interface
    notes = db.Column(db.Text, nullable=True)  # Notes personnelles ajoutées au rapport
    
    # Montants calculés
    total_income = db.Column(db.Numeric(12, 2), nullable=True)
    total_expenses = db.Column(db.Numeric(12, 2), nullable=True)
    total_tax = db.Column(db.Numeric(12, 2), nullable=True)
    net_profit = db.Column(db.Numeric(12, 2), nullable=True)
    profit = db.Column(db.Numeric(12, 2), nullable=True)  # Synonyme de net_profit pour la nouvelle interface
    
    # Relation avec l'utilisateur
    user = db.relationship('User', backref=db.backref('tax_reports', lazy='dynamic'))
    
    def __repr__(self):
        return f'<TaxReport {self.title or self.name}: {self.start_date} - {self.end_date}>'


class Customer(db.Model):
    """Modèle pour les clients (destinataires des factures/devis)"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # Nom du client (personne ou entreprise)
    contact_name = db.Column(db.String(100), nullable=True)  # Nom du contact si différent
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(50), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(50), nullable=True)
    tax_id = db.Column(db.String(50), nullable=True)  # Numéro SIRET, TVA, etc.
    is_company = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', backref=db.backref('customers', lazy='dynamic'))
    invoices = db.relationship('Invoice', backref='customer', lazy='dynamic')
    quotes = db.relationship('Quote', backref='customer', lazy='dynamic')
    
    def __repr__(self):
        return f'<Customer {self.name}>'


class Invoice(db.Model):
    """Modèle pour les factures"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    invoice_number = db.Column(db.String(50), nullable=False, unique=True)
    reference = db.Column(db.String(100), nullable=True)  # Référence interne optionnelle
    issue_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='draft')  # draft, sent, paid, overdue, cancelled
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)
    terms = db.Column(db.Text, nullable=True)  # Conditions de paiement
    payment_info = db.Column(db.Text, nullable=True)  # Informations de paiement
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)  # Date de paiement
    
    # Relations
    user = db.relationship('User', backref=db.backref('invoices', lazy='dynamic'))
    items = db.relationship('InvoiceItem', backref='invoice', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number}: {self.total}€>'
    
    @property
    def is_paid(self):
        return self.status == 'paid'
    
    @property
    def is_overdue(self):
        if not self.due_date:
            return False
        return self.due_date < datetime.utcnow().date() and self.status not in ['paid', 'cancelled']
    
    def calculate_totals(self):
        """Calculer les totaux de la facture"""
        items = self.items.all()
        self.subtotal = sum(item.subtotal for item in items)
        self.tax_amount = sum(item.tax_amount for item in items)
        self.total = self.subtotal + self.tax_amount
        return self.total


class InvoiceItem(db.Model):
    """Modèle pour les lignes de facture"""
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=0)  # Pourcentage de TVA
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    
    def __repr__(self):
        return f'<InvoiceItem {self.id}: {self.description[:20]}...>'
    
    def calculate(self):
        """Calculer les montants de la ligne"""
        self.subtotal = self.quantity * self.unit_price
        self.tax_amount = self.subtotal * (self.tax_rate / 100)
        self.total = self.subtotal + self.tax_amount
        return self.total


class Quote(db.Model):
    """Modèle pour les devis"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    quote_number = db.Column(db.String(50), nullable=False, unique=True)
    reference = db.Column(db.String(100), nullable=True)  # Référence interne optionnelle
    issue_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    expiry_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='draft')  # draft, sent, accepted, rejected, expired
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)
    terms = db.Column(db.Text, nullable=True)  # Conditions du devis
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    accepted_at = db.Column(db.DateTime, nullable=True)  # Date d'acceptation
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=True)  # Si converti en facture
    
    # Relations
    user = db.relationship('User', backref=db.backref('quotes', lazy='dynamic'))
    items = db.relationship('QuoteItem', backref='quote', lazy='dynamic', cascade="all, delete-orphan")
    invoice = db.relationship('Invoice', backref=db.backref('quote', uselist=False))
    
    def __repr__(self):
        return f'<Quote {self.quote_number}: {self.total}€>'
    
    @property
    def is_accepted(self):
        return self.status == 'accepted'
    
    @property
    def is_expired(self):
        if not self.expiry_date:
            return False
        return self.expiry_date < datetime.utcnow().date() and self.status not in ['accepted', 'rejected']
    
    def calculate_totals(self):
        """Calculer les totaux du devis"""
        items = self.items.all()
        self.subtotal = sum(item.subtotal for item in items)
        self.tax_amount = sum(item.tax_amount for item in items)
        self.total = self.subtotal + self.tax_amount
        return self.total
        
    def convert_to_invoice(self):
        """Convertir le devis en facture"""
        if self.status != 'accepted':
            return None
            
        # Créer une nouvelle facture
        invoice = Invoice(
            user_id=self.user_id,
            customer_id=self.customer_id,
            invoice_number=f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{self.id}",
            reference=f"Devis {self.quote_number}",
            issue_date=datetime.utcnow().date(),
            due_date=(datetime.utcnow() + timedelta(days=30)).date(),  # Échéance par défaut à 30 jours
            subtotal=self.subtotal,
            tax_amount=self.tax_amount,
            total=self.total,
            notes=self.notes,
            terms=self.terms
        )
        
        db.session.add(invoice)
        db.session.flush()  # Pour obtenir l'ID de la facture
        
        # Copier les lignes du devis vers la facture
        for quote_item in self.items.all():
            invoice_item = InvoiceItem(
                invoice_id=invoice.id,
                description=quote_item.description,
                quantity=quote_item.quantity,
                unit_price=quote_item.unit_price,
                tax_rate=quote_item.tax_rate,
                subtotal=quote_item.subtotal,
                tax_amount=quote_item.tax_amount,
                total=quote_item.total
            )
            db.session.add(invoice_item)
        
        # Mettre à jour le devis
        self.invoice_id = invoice.id
        
        return invoice


class QuoteItem(db.Model):
    """Modèle pour les lignes de devis"""
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey('quote.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=0)  # Pourcentage de TVA
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    
    def __repr__(self):
        return f'<QuoteItem {self.id}: {self.description[:20]}...>'
    
    def calculate(self):
        """Calculer les montants de la ligne"""
        self.subtotal = self.quantity * self.unit_price
        self.tax_amount = self.subtotal * (self.tax_rate / 100)
        self.total = self.subtotal + self.tax_amount
        return self.total


class CompanyInfo(db.Model):
    """Informations de l'entreprise de l'utilisateur pour les factures/devis"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(50), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(50), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    website = db.Column(db.String(100), nullable=True)
    tax_id = db.Column(db.String(50), nullable=True)  # Numéro de TVA
    registration_number = db.Column(db.String(50), nullable=True)  # SIRET, numéro d'entreprise
    bank_name = db.Column(db.String(100), nullable=True)
    bank_account = db.Column(db.String(50), nullable=True)
    bank_iban = db.Column(db.String(50), nullable=True)
    bank_bic = db.Column(db.String(20), nullable=True)
    logo = db.Column(db.String(255), nullable=True)  # Chemin vers le logo
    
    # Relation avec l'utilisateur
    user = db.relationship('User', backref=db.backref('company_info', uselist=False))
    
    def __repr__(self):
        return f'<CompanyInfo {self.name}>'

