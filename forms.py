from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, EmailField, RadioField, BooleanField, SelectField, TextAreaField, HiddenField, SelectMultipleField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional

class LoginForm(FlaskForm):
    """Form for user login"""
    username = EmailField('Email', validators=[
        DataRequired(),
        Email(message='Veuillez entrer une adresse email valide')
    ])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Se connecter')

class RegisterForm(FlaskForm):
    """Form for user registration"""
    username = EmailField('Email (sera utilisé comme identifiant)', validators=[
        DataRequired(),
        Email(message='Veuillez entrer une adresse email valide')
    ])
    display_name = StringField('Nom d\'utilisateur à afficher', validators=[
        DataRequired(),
        Length(min=3, max=20, message='Le nom d\'utilisateur doit contenir entre 3 et 20 caractères')
    ])
    password = PasswordField('Mot de passe', validators=[
        DataRequired(),
        Length(min=8, message='Le mot de passe doit contenir au moins 8 caractères')
    ])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[
        DataRequired(),
        EqualTo('password', message='Les mots de passe doivent correspondre')
    ])
    submit = SubmitField('S\'inscrire')

class ConfirmationForm(FlaskForm):
    """Form for confirming user registration"""
    username = EmailField('Email', validators=[
        DataRequired(),
        Email(message='Veuillez entrer une adresse email valide')
    ])
    confirmation_code = StringField('Code de confirmation', validators=[DataRequired()])
    submit = SubmitField('Confirmer')

class ForgotPasswordForm(FlaskForm):
    """Form for initiating forgot password"""
    username = EmailField('Email', validators=[
        DataRequired(),
        Email(message='Veuillez entrer une adresse email valide')
    ])
    submit = SubmitField('Réinitialiser mon mot de passe')
    
class ResetPasswordForm(FlaskForm):
    """Form for resetting password with confirmation code"""
    username = EmailField('Email', validators=[
        DataRequired(),
        Email(message='Veuillez entrer une adresse email valide')
    ])
    confirmation_code = StringField('Code de confirmation', validators=[DataRequired()])
    new_password = PasswordField('Nouveau mot de passe', validators=[
        DataRequired(),
        Length(min=8, message='Le mot de passe doit contenir au moins 8 caractères')
    ])
    confirm_new_password = PasswordField('Confirmer le nouveau mot de passe', validators=[
        DataRequired(),
        EqualTo('new_password', message='Les mots de passe doivent correspondre')
    ])
    submit = SubmitField('Réinitialiser le mot de passe')
    
class ResendConfirmationForm(FlaskForm):
    """Form for resending confirmation code"""
    username = EmailField('Email', validators=[
        DataRequired(),
        Email(message='Veuillez entrer une adresse email valide')
    ])
    submit = SubmitField('Renvoyer le code')


class SubscriptionForm(FlaskForm):
    """Form for selecting a subscription plan"""
    plan_id = RadioField('Plan d\'abonnement', coerce=int, validators=[DataRequired()])
    auto_renew = BooleanField('Renouvellement automatique', default=True)
    payment_method = RadioField('Méthode de paiement', choices=[
        ('credit_card', 'Carte de crédit'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Virement bancaire'),
        ('mobile_payment', 'Paiement mobile (M-Pesa, Orange Money, Airtel Money)')
    ], default='credit_card')
    submit = SubmitField('S\'abonner')


class CreditCardForm(FlaskForm):
    """Form for credit card payment"""
    card_number = StringField('Numéro de carte', validators=[
        DataRequired(),
        Length(min=13, max=19, message='Numéro de carte invalide')
    ])
    cardholder_name = StringField('Nom du titulaire', validators=[DataRequired()])
    expiry_month = SelectField('Mois d\'expiration', choices=[
        (str(i).zfill(2), str(i).zfill(2)) for i in range(1, 13)
    ], validators=[DataRequired()])
    expiry_year = SelectField('Année d\'expiration', choices=[
        (str(i), str(i)) for i in range(2025, 2036)
    ], validators=[DataRequired()])
    cvv = StringField('Code de sécurité (CVV)', validators=[
        DataRequired(),
        Length(min=3, max=4, message='CVV invalide')
    ])
    submit = SubmitField('Payer maintenant')


class CancelSubscriptionForm(FlaskForm):
    """Form for canceling a subscription"""
    confirm_cancel = BooleanField('Je confirme vouloir annuler mon abonnement', validators=[DataRequired()])
    reason = SelectField('Raison de l\'annulation', choices=[
        ('price', 'Prix trop élevé'),
        ('features', 'Fonctionnalités insuffisantes'),
        ('usage', 'Je n\'utilise pas assez le service'),
        ('competing_service', 'J\'utilise un service concurrent'),
        ('other', 'Autre raison')
    ])
    feedback = TextAreaField('Commentaires (facultatif)')
    submit = SubmitField('Confirmer l\'annulation')


class UpdateProfileForm(FlaskForm):
    """Formulaire pour mettre à jour les informations de profil"""
    display_name = StringField('Nom d\'affichage', validators=[
        DataRequired(),
        Length(min=3, max=20, message='Le nom d\'affichage doit contenir entre 3 et 20 caractères')
    ])
    profile_picture = FileField('Photo de profil', validators=[
        Optional(),
        FileAllowed(['jpg', 'png', 'jpeg'], 'Images uniquement (jpg, png, jpeg)')
    ])
    submit = SubmitField('Mettre à jour')


class BusinessConsultationForm(FlaskForm):
    """Formulaire pour la consultation business personnalisée"""
    company_name = StringField('Nom de l\'entreprise', validators=[
        DataRequired(),
        Length(min=2, max=100, message='Le nom de l\'entreprise doit contenir entre 2 et 100 caractères')
    ])
    
    industry = SelectField('Secteur d\'activité', validators=[DataRequired()], choices=[
        ('', 'Sélectionnez un secteur'),
        ('technology', 'Technologie et informatique'),
        ('retail', 'Commerce de détail'),
        ('manufacturing', 'Fabrication et industrie'),
        ('finance', 'Finance et assurance'),
        ('healthcare', 'Santé et bien-être'),
        ('education', 'Éducation et formation'),
        ('hospitality', 'Hôtellerie et restauration'),
        ('real_estate', 'Immobilier'),
        ('construction', 'Construction et BTP'),
        ('agriculture', 'Agriculture'),
        ('transport', 'Transport et logistique'),
        ('media', 'Médias et divertissement'),
        ('legal', 'Services juridiques'),
        ('consulting', 'Conseil et services professionnels'),
        ('nonprofit', 'Organisation à but non lucratif'),
        ('other', 'Autre')
    ])
    
    company_size = SelectField('Taille de l\'entreprise', validators=[DataRequired()], choices=[
        ('', 'Sélectionnez une taille'),
        ('solo', 'Auto-entrepreneur / Indépendant'),
        ('micro', 'Micro-entreprise (1-9 employés)'),
        ('small', 'Petite entreprise (10-49 employés)'),
        ('medium', 'Moyenne entreprise (50-249 employés)'),
        ('large', 'Grande entreprise (250+ employés)')
    ])
    
    company_age = SelectField('Âge de l\'entreprise', validators=[DataRequired()], choices=[
        ('', 'Sélectionnez l\'âge'),
        ('startup', 'Startup / En création'),
        ('1-2', '1-2 ans'),
        ('3-5', '3-5 ans'),
        ('6-10', '6-10 ans'),
        ('11-20', '11-20 ans'),
        ('20+', 'Plus de 20 ans')
    ])
    
    annual_revenue = SelectField('Chiffre d\'affaires annuel', choices=[
        ('', 'Sélectionnez une tranche'),
        ('prefer_not', 'Je préfère ne pas indiquer'),
        ('less_100k', 'Moins de 100 000 €'),
        ('100k-500k', '100 000 € - 500 000 €'),
        ('500k-1m', '500 000 € - 1 million €'),
        ('1m-5m', '1 - 5 millions €'),
        ('5m-20m', '5 - 20 millions €'),
        ('20m+', 'Plus de 20 millions €')
    ])
    
    business_challenges = TextAreaField('Défis actuels', validators=[
        DataRequired(),
        Length(min=30, max=1000, message='Veuillez décrire vos défis en 30 à 1000 caractères')
    ])
    
    growth_goals = TextAreaField('Objectifs de croissance', validators=[
        DataRequired(),
        Length(min=30, max=1000, message='Veuillez décrire vos objectifs en 30 à 1000 caractères')
    ])
    
    current_strengths = TextAreaField('Points forts actuels', validators=[
        Optional(),
        Length(max=1000, message='Maximum 1000 caractères')
    ])
    
    improvement_areas = SelectMultipleField('Domaines à améliorer', validators=[DataRequired()], choices=[
        ('sales', 'Ventes et développement commercial'),
        ('marketing', 'Marketing et communication'),
        ('operations', 'Opérations et processus internes'),
        ('finance', 'Gestion financière'),
        ('hr', 'Ressources humaines et recrutement'),
        ('technology', 'Technologie et systèmes d\'information'),
        ('customer_service', 'Service client'),
        ('product_development', 'Développement de produits/services'),
        ('strategy', 'Stratégie globale'),
        ('international', 'Expansion internationale'),
        ('digital_transformation', 'Transformation digitale')
    ])
    
    additional_info = TextAreaField('Informations complémentaires', validators=[
        Optional(),
        Length(max=1000, message='Maximum 1000 caractères')
    ])
    
    submit = SubmitField('Obtenir mon analyse personnalisée')