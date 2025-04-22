"""
Module contenant les modèles de données DynamoDB pour l'application IA-Solution
Remplace les modèles SQLAlchemy avec des modèles PynamoDB pour une architecture AWS complète
"""

import os
import uuid
from datetime import datetime
from decimal import Decimal

from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, UTCDateTimeAttribute, 
    BooleanAttribute, ListAttribute, MapAttribute, JSONAttribute
)

# Configuration des variables d'environnement AWS
AWS_REGION = os.environ.get('AWS_REGION', 'eu-west-3')

# Classes de base et utilitaires
class BaseModel(Model):
    """Classe de base pour tous les modèles DynamoDB"""
    
    class Meta:
        region = AWS_REGION
        # La capacité provisionnée est requise si billing_mode n'est pas PAY_PER_REQUEST
        read_capacity_units = 5
        write_capacity_units = 5

    # Attributs communs à tous les modèles
    id = UnicodeAttribute(hash_key=True)  # Clé primaire
    created_at = UTCDateTimeAttribute(default=datetime.now)
    updated_at = UTCDateTimeAttribute(default=datetime.now)

    @classmethod
    def setup_table(cls, wait=False):
        """Crée la table si elle n'existe pas"""
        if not cls.exists():
            cls.create_table(wait=wait)
            return True
        return False

    def save(self, **expected_values):
        """Surcharge la méthode save pour mettre à jour automatiquement updated_at"""
        self.updated_at = datetime.now()
        super().save(**expected_values)

    def to_dict(self):
        """Convertit le modèle en dictionnaire"""
        return self.attribute_values


# Définition des modèles pour les utilisateurs
class User(BaseModel):
    """Modèle pour les utilisateurs de l'application"""
    
    class Meta(BaseModel.Meta):
        table_name = 'IA_Solution_Users'
    
    # Attributs spécifiques aux utilisateurs
    username = UnicodeAttribute(null=False)
    email = UnicodeAttribute(null=False)
    cognito_id = UnicodeAttribute(null=False)
    is_admin = BooleanAttribute(default=False)
    is_active = BooleanAttribute(default=True)
    language = UnicodeAttribute(default='fr')
    profile_picture_url = UnicodeAttribute(null=True)
    plan_id = UnicodeAttribute(null=True)
    subscription_status = UnicodeAttribute(default='free')
    subscription_end_date = UTCDateTimeAttribute(null=True)
    
    @classmethod
    def create_user(cls, username, email, cognito_id):
        """Méthode pour créer un nouvel utilisateur"""
        user = cls(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            cognito_id=cognito_id
        )
        user.save()
        return user
    
    @classmethod
    def find_by_email(cls, email):
        """Recherche un utilisateur par son email"""
        for user in cls.scan(User.email == email):
            return user
        return None
    
    @classmethod
    def find_by_cognito_id(cls, cognito_id):
        """Recherche un utilisateur par son ID Cognito"""
        for user in cls.scan(User.cognito_id == cognito_id):
            return user
        return None


# Modèle pour les rapports d'analyse business
class BusinessReport(BaseModel):
    """Modèle pour les rapports d'analyse business"""
    
    class Meta(BaseModel.Meta):
        table_name = 'IA_Solution_Business_Reports'
    
    user_id = UnicodeAttribute(null=False)  # ID de l'utilisateur propriétaire
    company_name = UnicodeAttribute(null=False)
    company_sector = UnicodeAttribute(null=True)
    company_size = UnicodeAttribute(null=True)
    analysis_type = UnicodeAttribute(default='swot')
    report_html = UnicodeAttribute(null=True)
    status = UnicodeAttribute(default='pending')
    is_shared = BooleanAttribute(default=False)
    share_token = UnicodeAttribute(null=True)

# Modèle pour les catégories de transactions financières
class TransactionCategory(MapAttribute):
    """Modèle pour les catégories de transactions financières"""
    id = UnicodeAttribute()
    name = UnicodeAttribute()
    type = UnicodeAttribute()  # 'expense' ou 'income'
    color = UnicodeAttribute(null=True)
    icon = UnicodeAttribute(null=True)


# Modèle pour les transactions financières
class Transaction(BaseModel):
    """Modèle pour les transactions financières"""
    
    class Meta(BaseModel.Meta):
        table_name = 'IA_Solution_Transactions'
    
    user_id = UnicodeAttribute(null=False)
    description = UnicodeAttribute(null=True)
    amount = NumberAttribute(null=False)
    category = MapAttribute(null=True)  # TransactionCategory incorporée
    date = UTCDateTimeAttribute(null=False)
    notes = UnicodeAttribute(null=True)
    document_url = UnicodeAttribute(null=True)


# Modèle pour les prédictions de flux de trésorerie
class CashflowPrediction(BaseModel):
    """Modèle pour les prédictions de flux de trésorerie"""
    
    class Meta(BaseModel.Meta):
        table_name = 'IA_Solution_Cashflow_Predictions'
    
    user_id = UnicodeAttribute(null=False)
    prediction_date = UTCDateTimeAttribute(null=False)
    predicted_income = NumberAttribute(null=False)
    predicted_expense = NumberAttribute(null=False)
    confidence_score = NumberAttribute(null=True)


# Modèle pour les plans d'abonnement
class SubscriptionPlan(BaseModel):
    """Modèle pour les plans d'abonnement"""
    
    class Meta(BaseModel.Meta):
        table_name = 'IA_Solution_Subscription_Plans'
    
    name = UnicodeAttribute(null=False)
    description = UnicodeAttribute(null=True)
    price_monthly = NumberAttribute(default=0)
    price_yearly = NumberAttribute(default=0)
    storage_limit_mb = NumberAttribute(default=100)
    features = JSONAttribute(null=True)  # Liste des fonctionnalités incluses
    is_active = BooleanAttribute(default=True)


# Modèle pour les modules du système de modules
class ModuleCategory(BaseModel):
    """Modèle pour les catégories de modules"""
    
    class Meta(BaseModel.Meta):
        table_name = 'IA_Solution_Module_Categories'
    
    name = UnicodeAttribute(null=False)
    description = UnicodeAttribute(null=True)
    icon = UnicodeAttribute(null=True)


class ModuleVersion(MapAttribute):
    """Modèle pour les versions de modules (inclus dans Module)"""
    version_number = UnicodeAttribute()
    release_date = UTCDateTimeAttribute()
    changes = UnicodeAttribute(null=True)
    is_current = BooleanAttribute(default=False)


class Module(BaseModel):
    """Modèle pour les modules disponibles dans le système"""
    
    class Meta(BaseModel.Meta):
        table_name = 'IA_Solution_Modules'
    
    name = UnicodeAttribute(null=False)
    short_description = UnicodeAttribute(null=True)
    full_description = UnicodeAttribute(null=True)
    category_id = UnicodeAttribute(null=False)
    price = NumberAttribute(default=0)  # 0 = gratuit
    icon_url = UnicodeAttribute(null=True)
    screenshot_urls = ListAttribute(of=UnicodeAttribute, null=True)
    is_official = BooleanAttribute(default=False)
    is_published = BooleanAttribute(default=False)
    author_id = UnicodeAttribute(null=True)
    average_rating = NumberAttribute(default=0)
    versions = ListAttribute(of=ModuleVersion, null=True)
    installation_count = NumberAttribute(default=0)


class ModuleReview(BaseModel):
    """Modèle pour les avis sur les modules"""
    
    class Meta(BaseModel.Meta):
        table_name = 'IA_Solution_Module_Reviews'
    
    module_id = UnicodeAttribute(null=False)
    user_id = UnicodeAttribute(null=False)
    rating = NumberAttribute(null=False)  # 1-5
    comment = UnicodeAttribute(null=True)
    is_verified_purchase = BooleanAttribute(default=False)


class ModuleInstallation(BaseModel):
    """Modèle pour les installations de modules par les utilisateurs"""
    
    class Meta(BaseModel.Meta):
        table_name = 'IA_Solution_Module_Installations'
    
    user_id = UnicodeAttribute(null=False)
    module_id = UnicodeAttribute(null=False)
    version_number = UnicodeAttribute(null=False)
    installation_date = UTCDateTimeAttribute(default=datetime.now)
    is_active = BooleanAttribute(default=True)
    config = JSONAttribute(null=True)  # Configuration personnalisée du module


# Modèle pour les documents marketing
class MarketingContent(BaseModel):
    """Modèle pour le contenu marketing généré"""
    
    class Meta(BaseModel.Meta):
        table_name = 'IA_Solution_Marketing_Content'
    
    user_id = UnicodeAttribute(null=False)
    title = UnicodeAttribute(null=False)
    content_type = UnicodeAttribute(null=False)  # email, social, blog, etc.
    content = UnicodeAttribute(null=False)
    target_audience = UnicodeAttribute(null=True)
    language = UnicodeAttribute(default='fr')
    tags = ListAttribute(of=UnicodeAttribute, null=True)


# Modèle pour le calendrier éditorial
class EditorialCalendarEvent(BaseModel):
    """Modèle pour les événements du calendrier éditorial"""
    
    class Meta(BaseModel.Meta):
        table_name = 'IA_Solution_Editorial_Calendar'
    
    user_id = UnicodeAttribute(null=False)
    title = UnicodeAttribute(null=False)
    start_date = UTCDateTimeAttribute(null=False)
    end_date = UTCDateTimeAttribute(null=True)
    content_type = UnicodeAttribute(null=True)
    status = UnicodeAttribute(default='planned')  # planned, in_progress, completed
    description = UnicodeAttribute(null=True)
    content_id = UnicodeAttribute(null=True)  # Référence à un MarketingContent


# Modèle pour les processus métier analysés
class BusinessProcess(BaseModel):
    """Modèle pour les processus métier analysés"""
    
    class Meta(BaseModel.Meta):
        table_name = 'IA_Solution_Business_Processes'
    
    user_id = UnicodeAttribute(null=False)
    name = UnicodeAttribute(null=False)
    description = UnicodeAttribute(null=True)
    current_state = UnicodeAttribute(null=True)
    desired_state = UnicodeAttribute(null=True)
    analysis_result = UnicodeAttribute(null=True)
    optimization_points = ListAttribute(of=UnicodeAttribute, null=True)
    status = UnicodeAttribute(default='initiated')  # initiated, analyzing, completed
    completion_percentage = NumberAttribute(default=0)


# Modèle pour les prédictions commerciales
class BusinessPrediction(BaseModel):
    """Modèle pour les prédictions commerciales"""
    
    class Meta(BaseModel.Meta):
        table_name = 'IA_Solution_Business_Predictions'
    
    user_id = UnicodeAttribute(null=False)
    prediction_type = UnicodeAttribute(null=False)  # sales, client, catalog
    target_period = UnicodeAttribute(null=False)  # Q1_2025, etc.
    prediction_data = JSONAttribute(null=False)
    confidence_level = NumberAttribute(default=0)
    methodology = UnicodeAttribute(null=True)
    created_date = UTCDateTimeAttribute(default=datetime.now)


# Configuration d'initialisation des tables
def setup_tables(wait=True):
    """Configure toutes les tables DynamoDB"""
    models = [
        User, BusinessReport, Transaction, CashflowPrediction,
        SubscriptionPlan, ModuleCategory, Module, ModuleReview,
        ModuleInstallation, MarketingContent, EditorialCalendarEvent,
        BusinessProcess, BusinessPrediction
    ]
    
    results = {}
    for model in models:
        table_name = model.Meta.table_name
        try:
            created = model.setup_table(wait=wait)
            results[table_name] = 'Créée' if created else 'Déjà existante'
        except Exception as e:
            results[table_name] = f'Erreur: {str(e)}'
    
    return results


if __name__ == '__main__':
    # Si ce script est exécuté directement, configurer toutes les tables
    results = setup_tables()
    for table, status in results.items():
        print(f"Table {table}: {status}")