import os
import logging
import boto3
from warrant import Cognito
from jose import jwt
from flask import session, redirect, url_for, flash, request
from functools import wraps

# Configuration AWS Cognito
COGNITO_USER_POOL_ID = os.environ.get('AWS_COGNITO_USER_POOL_ID')
COGNITO_APP_CLIENT_ID = os.environ.get('AWS_COGNITO_APP_CLIENT_ID')
COGNITO_APP_CLIENT_SECRET = os.environ.get('AWS_COGNITO_APP_CLIENT_SECRET')
AWS_REGION = os.environ.get('AWS_REGION')

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_cognito_client():
    """Create and return a boto3 Cognito client"""
    return boto3.client('cognito-idp', region_name=AWS_REGION)

def login_user(username, password):
    """Authenticate a user with AWS Cognito and return tokens"""
    try:
        # Create a Cognito Identity Provider client
        client = get_cognito_client()
        
        # Initiate auth
        response = client.initiate_auth(
            ClientId=COGNITO_APP_CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password,
                'SECRET_HASH': get_secret_hash(username) if COGNITO_APP_CLIENT_SECRET else None
            }
        )
        
        # Check for challenge
        if 'ChallengeName' in response:
            logger.debug(f"Authentication challenge: {response['ChallengeName']}")
            return {'error': f"Authentication challenge required: {response['ChallengeName']}"}
        
        # Get tokens
        tokens = response['AuthenticationResult']
        return {
            'id_token': tokens['IdToken'],
            'access_token': tokens['AccessToken'],
            'refresh_token': tokens['RefreshToken'],
            'expires_in': tokens['ExpiresIn']
        }
        
    except client.exceptions.NotAuthorizedException as e:
        logger.error(f"NotAuthorizedException: {e}")
        return {'error': 'Nom d\'utilisateur ou mot de passe incorrect'}
    
    except client.exceptions.UserNotFoundException as e:
        logger.error(f"UserNotFoundException: {e}")
        return {'error': 'Nom d\'utilisateur ou mot de passe incorrect'}
    
    except Exception as e:
        logger.error(f"Login error: {e}")
        return {'error': f'Erreur d\'authentification: {str(e)}'}

def get_secret_hash(username):
    """
    Generate a secret hash for Cognito client with a secret.
    Only needed if your app client has a client secret.
    """
    if not COGNITO_APP_CLIENT_SECRET:
        return None
        
    try:
        from hmac import HMAC
        import hashlib
        import base64
        
        message = username + COGNITO_APP_CLIENT_ID
        dig = HMAC(
            key=COGNITO_APP_CLIENT_SECRET.encode('utf-8'),
            msg=message.encode('utf-8'), 
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(dig).decode()
    except Exception as e:
        logger.error(f"Error generating secret hash: {e}")
        return None

def register_user(username, email, password):
    """Register a new user with AWS Cognito"""
    try:
        client = get_cognito_client()
        
        response = client.sign_up(
            ClientId=COGNITO_APP_CLIENT_ID,
            SecretHash=get_secret_hash(username) if COGNITO_APP_CLIENT_SECRET else None,
            Username=username,
            Password=password,
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': email
                }
            ]
        )
        
        return {'success': True, 'user_id': response['UserSub']}
    
    except client.exceptions.UsernameExistsException:
        return {'error': 'Ce nom d\'utilisateur existe déjà.'}
    
    except client.exceptions.InvalidPasswordException:
        return {'error': 'Mot de passe invalide. Le mot de passe doit comporter au moins 8 caractères et contenir des majuscules, minuscules, chiffres et caractères spéciaux.'}
    
    except client.exceptions.InvalidParameterException as e:
        return {'error': f'Paramètre invalide: {str(e)}'}
    
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return {'error': f'Erreur d\'inscription: {str(e)}'}

def confirm_signup(username, confirmation_code):
    """Confirm a user's registration with the verification code"""
    try:
        client = get_cognito_client()
        
        response = client.confirm_sign_up(
            ClientId=COGNITO_APP_CLIENT_ID,
            SecretHash=get_secret_hash(username) if COGNITO_APP_CLIENT_SECRET else None,
            Username=username,
            ConfirmationCode=confirmation_code
        )
        
        return {'success': True}
    
    except client.exceptions.CodeMismatchException:
        return {'error': 'Code de vérification incorrect.'}
    
    except client.exceptions.ExpiredCodeException:
        return {'error': 'Code de vérification expiré.'}
    
    except Exception as e:
        logger.error(f"Confirmation error: {e}")
        return {'error': f'Erreur de confirmation: {str(e)}'}

def forgot_password(username):
    """Initiate forgot password flow for a user"""
    try:
        client = get_cognito_client()
        
        response = client.forgot_password(
            ClientId=COGNITO_APP_CLIENT_ID,
            SecretHash=get_secret_hash(username) if COGNITO_APP_CLIENT_SECRET else None,
            Username=username
        )
        
        # Get delivery details
        delivery = response.get('CodeDeliveryDetails', {})
        logger.debug(f"Forgot password initiated for user: {username}")
        
        return {'success': True, 'delivery': delivery}
    
    except client.exceptions.UserNotFoundException:
        logger.error(f"User not found during forgot password: {username}")
        return {'error': 'Utilisateur non trouvé.'}
    
    except client.exceptions.InvalidParameterException:
        logger.error(f"Invalid parameter for forgot password: {username}")
        return {'error': 'Paramètre invalide. Veuillez vérifier votre nom d\'utilisateur.'}
    
    except client.exceptions.LimitExceededException:
        logger.error(f"Limit exceeded for forgot password: {username}")
        return {'error': 'Limite dépassée. Veuillez réessayer plus tard.'}
    
    except Exception as e:
        logger.error(f"Unexpected error during forgot password: {str(e)}")
        return {'error': f'Une erreur s\'est produite: {str(e)}'}

def confirm_forgot_password(username, confirmation_code, new_password):
    """Complete forgot password by confirming code and setting new password"""
    try:
        client = get_cognito_client()
        
        response = client.confirm_forgot_password(
            ClientId=COGNITO_APP_CLIENT_ID,
            SecretHash=get_secret_hash(username) if COGNITO_APP_CLIENT_SECRET else None,
            Username=username,
            ConfirmationCode=confirmation_code,
            Password=new_password
        )
        
        logger.debug(f"Password reset confirmed for user: {username}")
        return {'success': True}
    
    except client.exceptions.CodeMismatchException:
        logger.error(f"Invalid confirmation code for reset: {username}")
        return {'error': 'Code de confirmation invalide.'}
    
    except client.exceptions.ExpiredCodeException:
        logger.error(f"Expired confirmation code for reset: {username}")
        return {'error': 'Le code de confirmation a expiré. Veuillez recommencer.'}
    
    except client.exceptions.UserNotFoundException:
        logger.error(f"User not found during reset: {username}")
        return {'error': 'Utilisateur non trouvé.'}
    
    except client.exceptions.InvalidPasswordException:
        logger.error(f"Invalid password during reset: {username}")
        return {'error': 'Mot de passe invalide. Le mot de passe doit comporter au moins 8 caractères et contenir des majuscules, minuscules, chiffres et caractères spéciaux.'}
    
    except Exception as e:
        logger.error(f"Unexpected error during password reset: {str(e)}")
        return {'error': f'Une erreur s\'est produite: {str(e)}'}

def resend_confirmation_code(username):
    """Resend confirmation code to user"""
    try:
        client = get_cognito_client()
        
        response = client.resend_confirmation_code(
            ClientId=COGNITO_APP_CLIENT_ID,
            SecretHash=get_secret_hash(username) if COGNITO_APP_CLIENT_SECRET else None,
            Username=username
        )
        
        delivery = response.get('CodeDeliveryDetails', {})
        logger.debug(f"Confirmation code resent for user: {username}")
        
        return {'success': True, 'delivery': delivery}
    
    except client.exceptions.UserNotFoundException:
        logger.error(f"User not found during resend: {username}")
        return {'error': 'Utilisateur non trouvé.'}
    
    except client.exceptions.InvalidParameterException:
        logger.error(f"Invalid parameter for resend: {username}")
        return {'error': 'Paramètre invalide.'}
    
    except client.exceptions.LimitExceededException:
        logger.error(f"Limit exceeded for resend: {username}")
        return {'error': 'Limite dépassée. Veuillez réessayer plus tard.'}
    
    except Exception as e:
        logger.error(f"Unexpected error during resend: {str(e)}")
        return {'error': f'Une erreur s\'est produite: {str(e)}'}

def logout_user():
    """Clear user session and Cognito tokens"""
    if 'access_token' in session:
        try:
            client = get_cognito_client()
            
            # Attempt to global sign out from Cognito
            client.global_sign_out(
                AccessToken=session['access_token']
            )
        except Exception as e:
            logger.error(f"Logout error: {e}")
    
    # Clear the session
    session.clear()
    return True

def get_user_info(access_token):
    """Get user details from Cognito using access token"""
    try:
        client = get_cognito_client()
        
        response = client.get_user(
            AccessToken=access_token
        )
        
        # Extract user attributes
        user_info = {
            'username': response['Username'],
            'attributes': {}
        }
        
        for attr in response['UserAttributes']:
            user_info['attributes'][attr['Name']] = attr['Value']
        
        return user_info
    
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        return None

def is_token_valid(token):
    """Verify if the JWT token is valid"""
    try:
        # Decode token without verification (just to check expiration)
        # In production, you should verify the token signature
        decoded = jwt.get_unverified_claims(token)
        
        # Check if token is expired
        import time
        current_time = int(time.time())
        
        if decoded.get('exp') and decoded.get('exp') < current_time:
            logger.debug("Token is expired")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return False

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        if 'access_token' not in session:
            flash('Veuillez vous connecter pour accéder à cette page.', 'danger')
            # Store original destination to redirect after login
            session['next_url'] = request.path
            return redirect(url_for('login'))
        
        # Check if token is still valid
        if not is_token_valid(session['access_token']):
            flash('Votre session a expiré. Veuillez vous reconnecter.', 'warning')
            # Clear the session
            session.clear()
            session['next_url'] = request.path
            return redirect(url_for('login'))
        
        # Vérifier si l'utilisateur existe dans la base de données locale
        from models import User
        username = session.get('username')
        if not username:
            flash('Information utilisateur manquante. Veuillez vous reconnecter.', 'warning')
            session.clear()
            session['next_url'] = request.path
            return redirect(url_for('login'))
        
        # Vérifier dans la base de données
        user = User.query.filter_by(username=username).first()
        if not user:
            flash('Utilisateur non trouvé. Veuillez vous reconnecter.', 'danger')
            session.clear()
            session['next_url'] = request.path
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin privileges for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First check if user is logged in
        if 'access_token' not in session:
            flash('Veuillez vous connecter pour accéder à cette page.', 'danger')
            session['next_url'] = request.path
            return redirect(url_for('login'))
        
        # Check if token is valid
        if not is_token_valid(session['access_token']):
            flash('Votre session a expiré. Veuillez vous reconnecter.', 'warning')
            session.clear()
            session['next_url'] = request.path
            return redirect(url_for('login'))
        
        # Vérifier si l'utilisateur existe dans la base de données locale
        from models import User
        username = session.get('username')
        if not username:
            flash('Information utilisateur manquante. Veuillez vous reconnecter.', 'warning')
            session.clear()
            session['next_url'] = request.path
            return redirect(url_for('login'))
        
        # Vérifier dans la base de données
        user = User.query.filter_by(username=username).first()
        if not user:
            flash('Utilisateur non trouvé. Veuillez vous reconnecter.', 'danger')
            session.clear()
            session['next_url'] = request.path
            return redirect(url_for('login'))
        
        # Check if user is an admin based on session
        is_admin = session.get('is_admin', False)
        
        if not is_admin:
            flash('Vous n\'avez pas les droits d\'accès à cette page.', 'danger')
            return redirect(url_for('home'))
        
        return f(*args, **kwargs)
    return decorated_function