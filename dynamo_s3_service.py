"""
Service pour gérer le stockage de fichiers sur Amazon S3
"""

import os
import uuid
import logging
import mimetypes
from io import BytesIO
from datetime import datetime, timedelta
from urllib.parse import unquote

import boto3
from botocore.exceptions import ClientError
from werkzeug.utils import secure_filename

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Récupération des variables d'environnement AWS S3
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'ia-solution-files')
AWS_REGION = os.environ.get('AWS_REGION', 'eu-west-3')

class S3Service:
    """Service de gestion des fichiers sur Amazon S3"""
    
    def __init__(self, bucket_name=None, region=None):
        """Initialise le service S3"""
        self.bucket_name = bucket_name or S3_BUCKET_NAME
        self.region = region or AWS_REGION
        
        # Initialiser le client S3
        self.s3 = boto3.client(
            's3',
            region_name=self.region,
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
        )
        
        logger.info("Connexion à S3 établie")
    
    def upload_file(self, file_storage, folder='uploads', file_name=None, public=False):
        """
        Télécharger un fichier sur S3
        
        Args:
            file_storage: Flask FileStorage ou chemin vers le fichier local
            folder: Dossier dans le bucket S3
            file_name: Nom du fichier (généré automatiquement si non fourni)
            public: Rendre le fichier public (accessible sans authentification)
            
        Returns:
            dict: Résultat de l'upload avec URL et autres informations
        """
        try:
            if not file_name:
                # Générer un nom de fichier unique basé sur l'horodatage
                original_filename = getattr(file_storage, 'filename', 'file')
                file_ext = os.path.splitext(original_filename)[1]
                file_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}{file_ext}"
            
            # Sanitize the file name
            file_name = secure_filename(file_name)
            
            # Construire le chemin complet dans S3
            s3_path = f"{folder}/{file_name}"
            
            # Déterminer le type MIME
            content_type = mimetypes.guess_type(file_name)[0] or 'application/octet-stream'
            
            # Préparer les extra_args pour l'upload
            extra_args = {
                'ContentType': content_type
            }
            
            # Si le fichier doit être public, ajouter l'ACL approprié
            if public:
                extra_args['ACL'] = 'public-read'
            
            # Télécharger le fichier sur S3
            if hasattr(file_storage, 'read'):
                # C'est un objet FileStorage
                file_data = file_storage.read()
                self.s3.upload_fileobj(
                    BytesIO(file_data),
                    self.bucket_name,
                    s3_path,
                    ExtraArgs=extra_args
                )
            else:
                # C'est un chemin de fichier local
                self.s3.upload_file(
                    file_storage,  # Chemin local
                    self.bucket_name,
                    s3_path,
                    ExtraArgs=extra_args
                )
            
            # Générer l'URL du fichier
            if public:
                file_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_path}"
            else:
                # Générer une URL présignée pour les fichiers privés
                file_url = self.generate_presigned_url(s3_path)
            
            return {
                'success': True,
                'file_name': file_name,
                'file_path': s3_path,
                'file_url': file_url,
                'file_size': len(file_data) if hasattr(file_storage, 'read') else os.path.getsize(file_storage),
                'content_type': content_type,
                'is_public': public
            }
        
        except Exception as e:
            logger.error(f"Erreur lors de l'upload du fichier sur S3: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_file(self, file_path):
        """
        Supprimer un fichier de S3
        
        Args:
            file_path: Chemin du fichier dans S3
            
        Returns:
            dict: Résultat de la suppression
        """
        try:
            # Extraire le chemin du fichier si une URL complète est fournie
            if file_path.startswith('http'):
                file_path = file_path.split('.com/')[1]
                file_path = unquote(file_path)
            
            # Supprimer le fichier
            self.s3.delete_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            
            return {
                'success': True,
                'message': f"Fichier {file_path} supprimé avec succès"
            }
        
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du fichier de S3: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_presigned_url(self, file_path, expiry=3600):
        """
        Générer une URL présignée pour un fichier privé
        
        Args:
            file_path: Chemin du fichier dans S3
            expiry: Durée de validité de l'URL en secondes (1 heure par défaut)
            
        Returns:
            str: URL présignée
        """
        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_path
                },
                ExpiresIn=expiry
            )
            
            return url
        
        except Exception as e:
            logger.error(f"Erreur lors de la génération de l'URL présignée: {str(e)}")
            return None
    
    def list_files(self, folder='uploads', max_files=100):
        """
        Lister les fichiers dans un dossier S3
        
        Args:
            folder: Dossier dans le bucket S3
            max_files: Nombre maximum de fichiers à retourner
            
        Returns:
            list: Liste des fichiers avec leurs informations
        """
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=folder,
                MaxKeys=max_files
            )
            
            files = []
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    file_path = obj['Key']
                    file_name = os.path.basename(file_path)
                    
                    # Générer l'URL du fichier
                    file_url = self.generate_presigned_url(file_path)
                    
                    files.append({
                        'file_name': file_name,
                        'file_path': file_path,
                        'file_url': file_url,
                        'file_size': obj['Size'],
                        'last_modified': obj['LastModified']
                    })
            
            return {
                'success': True,
                'files': files,
                'count': len(files)
            }
        
        except Exception as e:
            logger.error(f"Erreur lors de la liste des fichiers de S3: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'files': []
            }
    
    def copy_file(self, source_path, dest_path, make_public=False):
        """
        Copier un fichier dans S3
        
        Args:
            source_path: Chemin du fichier source dans S3
            dest_path: Chemin de destination dans S3
            make_public: Rendre le fichier public (accessible sans authentification)
            
        Returns:
            dict: Résultat de la copie
        """
        try:
            # Préparer les extra_args pour la copie
            extra_args = {}
            
            # Si le fichier doit être public, ajouter l'ACL approprié
            if make_public:
                extra_args['ACL'] = 'public-read'
            
            # Copier le fichier
            self.s3.copy_object(
                Bucket=self.bucket_name,
                CopySource={
                    'Bucket': self.bucket_name,
                    'Key': source_path
                },
                Key=dest_path,
                **extra_args
            )
            
            # Générer l'URL du fichier
            if make_public:
                file_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{dest_path}"
            else:
                # Générer une URL présignée pour les fichiers privés
                file_url = self.generate_presigned_url(dest_path)
            
            return {
                'success': True,
                'source_path': source_path,
                'dest_path': dest_path,
                'file_url': file_url,
                'is_public': make_public
            }
        
        except Exception as e:
            logger.error(f"Erreur lors de la copie du fichier dans S3: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

# Service S3 par défaut
default_s3_service = S3Service()