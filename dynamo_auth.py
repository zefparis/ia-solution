"""
Service d'authentification utilisant AWS Cognito et DynamoDB
"""

import os
import uuid
import base64
import hmac
import hashlib
import logging
import json
import time
from datetime import datetime, timedelta
from functools import wraps

import boto3
from botocore.exceptions import ClientError
from flask import request, redirect, url_for, session, flash, g

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Importation des modèles DynamoDB
from dynamo_models import User

# Récupération des variables d'environnement AWS Cognito
USER_POOL_ID = os.environ.get('AWS_COGNITO_USER_POOL_ID')
APP_CLIENT_ID = os.environ.get('AWS_COGNITO_APP_CLIENT_ID')
APP_CLIENT_SECRET = os.environ.get('AWS_COGNITO_APP_CLIENT_SECRET')
AWS_REGION = os.environ.get('AWS_REGION', 'eu-west-3')

def get_cognito_client():
    """Create and return a boto3 Cognito client"""
    client = boto3.client(
        'cognito-idp',
        region_name=AWS_REGION,
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
    )
    return client

def login_user(username, password):
    """Authenticate a user with AWS Cognito and return tokens"""
    try:
        cognito = get_cognito_client()
        
        auth_params = {
            'USERNAME': username,
            'PASSWORD': password
        }
        
        # Add secret hash if we have a client secret
        if APP_CLIENT_SECRET:
            auth_params['SECRET_HASH'] = get_secret_hash(username)
        
        # Initialize auth flow
        response = cognito.initiate_auth(
            ClientId=APP_CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters=auth_params
        )
        
        if 'ChallengeName' in response:
            if response['ChallengeName'] == 'NEW_PASSWORD_REQUIRED':
                return {
                    'success': False,
                    'message': 'Vous devez changer votre mot de passe',
                    'challenge': 'NEW_PASSWORD_REQUIRED',
                    'session': response.get('Session')
                }
            else:
                return {
                    'success': False,
                    'message': f"Challenge non supporté: {response['ChallengeName']}",
                    'challenge': response['ChallengeName']
                }
        
        # Get tokens from the auth flow
        access_token = response['AuthenticationResult']['AccessToken']
        id_token = response['AuthenticationResult']['IdToken']
        refresh_token = response['AuthenticationResult']['RefreshToken']
        expires_in = response['AuthenticationResult']['ExpiresIn']
        
        # Get user info from the access token
        user_info = get_user_info(access_token)
        
        # Check if the user exists in DynamoDB, if not create one
        try:
            user = None
            for u in User.scan(User.email == username, limit=1):
                user = u
                break
            
            if not user:
                # Create new user in DynamoDB
                cognito_id = user_info.get('sub') if user_info else f"cognito_{str(uuid.uuid4())}"
                user = User(
                    id=str(uuid.uuid4()),
                    email=username,
                    username=user_info.get('email', username),
                    cognito_id=cognito_id,
                    is_active=True,
                    created_at=datetime.now()
                )
                user.save()
        except Exception as e:
            logger.error(f"Error finding/creating DynamoDB user: {e}")
        
        return {
            'success': True,
            'message': 'Connexion réussie',
            'tokens': {
                'access_token': access_token,
                'id_token': id_token,
                'refresh_token': refresh_token,
                'expires_in': expires_in,
                'user_id': user.id if user else None,
                'email': username
            }
        }
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'UserNotConfirmedException':
            return {
                'success': False,
                'message': 'Votre compte n\'est pas encore confirmé. Veuillez vérifier votre email.',
                'user_not_confirmed': True
            }
        elif error_code == 'NotAuthorizedException':
            if 'Password attempts exceeded' in error_message:
                return {
                    'success': False,
                    'message': 'Trop de tentatives de connexion. Veuillez réessayer plus tard.'
                }
            else:
                return {
                    'success': False,
                    'message': 'Email ou mot de passe incorrect.'
                }
        else:
            logger.error(f"Cognito auth error: {error_code} - {error_message}")
            return {
                'success': False,
                'message': 'Erreur lors de la connexion: ' + error_message
            }
    
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return {
            'success': False,
            'message': 'Une erreur est survenue lors de la connexion.'
        }

def get_secret_hash(username):
    """
    Generate a secret hash for Cognito client with a secret.
    Only needed if your app client has a client secret.
    """
    if not APP_CLIENT_SECRET:
        return None
    
    message = username + APP_CLIENT_ID
    dig = hmac.new(
        key=APP_CLIENT_SECRET.encode('utf-8'),
        msg=message.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(dig).decode()

def register_user(username, email, password):
    """Register a new user with AWS Cognito"""
    try:
        cognito = get_cognito_client()
        
        # Prepare attributes
        user_attributes = [
            {'Name': 'email', 'Value': email},
            {'Name': 'email_verified', 'Value': 'false'}
        ]
        
        # Add secret hash if we have a client secret
        kwargs = {
            'ClientId': APP_CLIENT_ID,
            'Username': email,  # Use email as username
            'Password': password,
            'UserAttributes': user_attributes
        }
        
        if APP_CLIENT_SECRET:
            kwargs['SecretHash'] = get_secret_hash(email)
        
        # Register user
        response = cognito.sign_up(**kwargs)
        
        # Create user in DynamoDB
        try:
            user = User(
                id=str(uuid.uuid4()),
                email=email,
                username=username,
                cognito_id=response['UserSub'],
                is_active=False,  # User is not active until confirmed
                created_at=datetime.now()
            )
            user.save()
        except Exception as e:
            logger.error(f"Error creating DynamoDB user: {e}")
        
        return {
            'success': True,
            'message': 'Inscription réussie. Veuillez confirmer votre compte avec le code envoyé à votre email.',
            'user_id': response['UserSub']
        }
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'UsernameExistsException':
            return {
                'success': False,
                'message': 'Un utilisateur avec cet email existe déjà.'
            }
        elif error_code == 'InvalidPasswordException':
            return {
                'success': False,
                'message': 'Le mot de passe ne respecte pas les critères de sécurité.'
            }
        else:
            logger.error(f"Cognito registration error: {error_code} - {error_message}")
            return {
                'success': False,
                'message': 'Erreur lors de l\'inscription: ' + error_message
            }
    
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return {
            'success': False,
            'message': 'Une erreur est survenue lors de l\'inscription.'
        }

def confirm_signup(username, confirmation_code):
    """Confirm a user's registration with the verification code"""
    try:
        cognito = get_cognito_client()
        
        # Prepare kwargs
        kwargs = {
            'ClientId': APP_CLIENT_ID,
            'Username': username,
            'ConfirmationCode': confirmation_code
        }
        
        if APP_CLIENT_SECRET:
            kwargs['SecretHash'] = get_secret_hash(username)
        
        # Confirm signup
        cognito.confirm_sign_up(**kwargs)
        
        # Activate user in DynamoDB
        try:
            for user in User.scan(User.email == username, limit=1):
                user.is_active = True
                user.save()
                break
        except Exception as e:
            logger.error(f"Error activating DynamoDB user: {e}")
        
        return {
            'success': True,
            'message': 'Votre compte a été confirmé avec succès. Vous pouvez maintenant vous connecter.'
        }
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'CodeMismatchException':
            return {
                'success': False,
                'message': 'Le code de confirmation est incorrect.'
            }
        elif error_code == 'ExpiredCodeException':
            return {
                'success': False,
                'message': 'Le code de confirmation a expiré. Veuillez demander un nouveau code.'
            }
        else:
            logger.error(f"Cognito confirmation error: {error_code} - {error_message}")
            return {
                'success': False,
                'message': 'Erreur lors de la confirmation: ' + error_message
            }
    
    except Exception as e:
        logger.error(f"Confirmation error: {str(e)}")
        return {
            'success': False,
            'message': 'Une erreur est survenue lors de la confirmation.'
        }

def forgot_password(username):
    """Initiate forgot password flow for a user"""
    try:
        cognito = get_cognito_client()
        
        # Prepare kwargs
        kwargs = {
            'ClientId': APP_CLIENT_ID,
            'Username': username
        }
        
        if APP_CLIENT_SECRET:
            kwargs['SecretHash'] = get_secret_hash(username)
        
        # Initiate forgot password
        cognito.forgot_password(**kwargs)
        
        return {
            'success': True,
            'message': 'Un code de réinitialisation a été envoyé à votre email.'
        }
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'UserNotFoundException':
            # For security, don't indicate if user exists
            return {
                'success': True,
                'message': 'Si un compte existe avec cet email, un code de réinitialisation a été envoyé.'
            }
        elif error_code == 'LimitExceededException':
            return {
                'success': False,
                'message': 'Trop de demandes. Veuillez réessayer plus tard.'
            }
        else:
            logger.error(f"Cognito forgot password error: {error_code} - {error_message}")
            return {
                'success': False,
                'message': 'Erreur lors de la réinitialisation: ' + error_message
            }
    
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        return {
            'success': False,
            'message': 'Une erreur est survenue lors de la demande de réinitialisation.'
        }

def confirm_forgot_password(username, confirmation_code, new_password):
    """Complete forgot password by confirming code and setting new password"""
    try:
        cognito = get_cognito_client()
        
        # Prepare kwargs
        kwargs = {
            'ClientId': APP_CLIENT_ID,
            'Username': username,
            'ConfirmationCode': confirmation_code,
            'Password': new_password
        }
        
        if APP_CLIENT_SECRET:
            kwargs['SecretHash'] = get_secret_hash(username)
        
        # Confirm forgot password
        cognito.confirm_forgot_password(**kwargs)
        
        return {
            'success': True,
            'message': 'Votre mot de passe a été réinitialisé avec succès. Vous pouvez maintenant vous connecter.'
        }
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'CodeMismatchException':
            return {
                'success': False,
                'message': 'Le code de confirmation est incorrect.'
            }
        elif error_code == 'ExpiredCodeException':
            return {
                'success': False,
                'message': 'Le code de confirmation a expiré. Veuillez demander un nouveau code.'
            }
        elif error_code == 'InvalidPasswordException':
            return {
                'success': False,
                'message': 'Le mot de passe ne respecte pas les critères de sécurité.'
            }
        else:
            logger.error(f"Cognito confirm forgot password error: {error_code} - {error_message}")
            return {
                'success': False,
                'message': 'Erreur lors de la réinitialisation: ' + error_message
            }
    
    except Exception as e:
        logger.error(f"Confirm forgot password error: {str(e)}")
        return {
            'success': False,
            'message': 'Une erreur est survenue lors de la réinitialisation du mot de passe.'
        }

def resend_confirmation_code(username):
    """Resend confirmation code to user"""
    try:
        cognito = get_cognito_client()
        
        # Prepare kwargs
        kwargs = {
            'ClientId': APP_CLIENT_ID,
            'Username': username
        }
        
        if APP_CLIENT_SECRET:
            kwargs['SecretHash'] = get_secret_hash(username)
        
        # Resend confirmation code
        cognito.resend_confirmation_code(**kwargs)
        
        return {
            'success': True,
            'message': 'Un nouveau code de confirmation a été envoyé à votre email.'
        }
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'UserNotFoundException':
            return {
                'success': False,
                'message': 'Aucun utilisateur trouvé avec cet email.'
            }
        elif error_code == 'LimitExceededException':
            return {
                'success': False,
                'message': 'Trop de demandes. Veuillez réessayer plus tard.'
            }
        else:
            logger.error(f"Cognito resend code error: {error_code} - {error_message}")
            return {
                'success': False,
                'message': 'Erreur lors de l\'envoi du code: ' + error_message
            }
    
    except Exception as e:
        logger.error(f"Resend code error: {str(e)}")
        return {
            'success': False,
            'message': 'Une erreur est survenue lors de l\'envoi du code de confirmation.'
        }

def logout_user():
    """Clear user session and Cognito tokens"""
    session.pop('access_token', None)
    session.pop('id_token', None)
    session.pop('refresh_token', None)
    session.pop('user_id', None)
    session.pop('email', None)
    return True

def get_user_info(access_token):
    """Get user details from Cognito using access token"""
    try:
        cognito = get_cognito_client()
        
        # Get user info
        response = cognito.get_user(
            AccessToken=access_token
        )
        
        # Extract user attributes
        user_attrs = {}
        for attr in response['UserAttributes']:
            user_attrs[attr['Name']] = attr['Value']
        
        return user_attrs
    
    except ClientError as e:
        logger.error(f"Cognito get user error: {e}")
        return None
    
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        return None

def is_token_valid(token):
    """Verify if the JWT token is valid"""
    if not token:
        return False
    
    try:
        # Simple check if token is expired
        # In a real implementation, you should verify the signature and claims
        # using the JWT library and Cognito's JWKS
        
        # Extract payload
        parts = token.split('.')
        if len(parts) != 3:
            return False
        
        # Decode payload (Base64)
        padded = parts[1] + '=' * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.b64decode(padded).decode('utf-8'))
        
        # Check exp claim
        if 'exp' in payload:
            exp_time = datetime.fromtimestamp(payload['exp'])
            if exp_time < datetime.now():
                return False
        
        return True
    
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        return False

def refresh_access_token(refresh_token):
    """Refresh the access token using the refresh token"""
    try:
        cognito = get_cognito_client()
        
        auth_params = {
            'REFRESH_TOKEN': refresh_token
        }
        
        # Add secret hash if we have a client secret
        if APP_CLIENT_SECRET and 'email' in session:
            auth_params['SECRET_HASH'] = get_secret_hash(session['email'])
        
        # Refresh token
        response = cognito.initiate_auth(
            ClientId=APP_CLIENT_ID,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters=auth_params
        )
        
        # Get tokens from the auth flow
        access_token = response['AuthenticationResult']['AccessToken']
        id_token = response['AuthenticationResult']['IdToken']
        expires_in = response['AuthenticationResult']['ExpiresIn']
        
        # Update session
        session['access_token'] = access_token
        session['id_token'] = id_token
        
        return {
            'success': True,
            'access_token': access_token,
            'id_token': id_token,
            'expires_in': expires_in
        }
    
    except Exception as e:
        logger.error(f"Refresh token error: {str(e)}")
        return {
            'success': False,
            'message': 'Une erreur est survenue lors du rafraîchissement du token.'
        }

def get_current_user():
    """Get the current user from DynamoDB based on session user_id"""
    try:
        if 'user_id' not in session:
            return None
        
        user_id = session['user_id']
        
        try:
            user = User.get(user_id)
            return user
        except User.DoesNotExist:
            return None
        
    except Exception as e:
        logger.error(f"Get current user error: {str(e)}")
        return None

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        if 'access_token' not in session:
            # Store the URL the user was trying to access
            session['next_url'] = request.url
            flash('Veuillez vous connecter pour accéder à cette page.', 'warning')
            return redirect(url_for('login'))
        
        # Check if token is valid
        if not is_token_valid(session['access_token']):
            # Try to refresh token
            if 'refresh_token' in session:
                refresh_result = refresh_access_token(session['refresh_token'])
                if not refresh_result['success']:
                    session.pop('access_token', None)
                    session['next_url'] = request.url
                    flash('Votre session a expiré. Veuillez vous reconnecter.', 'warning')
                    return redirect(url_for('login'))
            else:
                session.pop('access_token', None)
                session['next_url'] = request.url
                flash('Votre session a expiré. Veuillez vous reconnecter.', 'warning')
                return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    
    return decorated_function

def admin_required(f):
    """Decorator to require admin privileges for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First check if user is logged in
        if 'access_token' not in session:
            session['next_url'] = request.url
            flash('Veuillez vous connecter pour accéder à cette page.', 'warning')
            return redirect(url_for('login'))
        
        # Check if user is admin
        user = get_current_user()
        if not user or not user.is_admin:
            flash('Vous n\'avez pas les permissions nécessaires pour accéder à cette page.', 'danger')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    
    return decorated_function