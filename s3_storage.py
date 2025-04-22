import os
import logging
import boto3
from botocore.exceptions import ClientError
from io import BytesIO

# Définir une constante pour le préfixe de bucket
BUCKET_NAME_PREFIX = "ia-comptabilite"

class S3Storage:
    """Classe pour gérer le stockage dans AWS S3"""
    
    def __init__(self):
        """Initialiser la connexion à S3 avec les identifiants AWS"""
        self.s3_client = None
        try:
            # Vérifier si les clés AWS sont disponibles
            if not all([
                os.environ.get('AWS_ACCESS_KEY_ID'),
                os.environ.get('AWS_SECRET_ACCESS_KEY')
            ]):
                logging.warning("Identifiants AWS manquants. Le stockage S3 ne sera pas disponible.")
                return
                
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                region_name=os.environ.get('AWS_REGION', 'eu-west-3')
            )
            logging.info("Connexion à S3 établie")
        except Exception as e:
            logging.error(f"Erreur lors de la connexion à S3: {e}")
    
    def create_user_bucket(self, user_id):
        """
        Vérifie que l'utilisateur a bien accès au stockage S3
        Au lieu de créer un bucket dédié, on utilise un préfixe dans un bucket commun
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            bool: True si l'accès est disponible, False sinon
        """
        if not self.s3_client:
            logging.warning("Client S3 non initialisé. Impossible de vérifier le stockage utilisateur.")
            return False
            
        bucket_name = BUCKET_NAME_PREFIX
        
        try:
            # Vérifier si le bucket principal existe
            response = self.s3_client.list_buckets()
            bucket_exists = any(bucket['Name'] == bucket_name for bucket in response.get('Buckets', []))
            
            if not bucket_exists:
                logging.error(f"Le bucket principal {bucket_name} n'existe pas")
                return False
                
            # Créer un dossier pour l'utilisateur (virtuellement avec un objet vide)
            user_folder = f"users/{user_id}/"
            try:
                self.s3_client.put_object(
                    Bucket=bucket_name,
                    Key=user_folder + '.keep',
                    Body=''
                )
                logging.info(f"Dossier utilisateur {user_folder} vérifié avec succès dans {bucket_name}")
            except ClientError as e:
                logging.error(f"Erreur lors de la création du dossier utilisateur: {e}")
                return False
            
            return True
        except ClientError as e:
            logging.error(f"Erreur lors de l'accès au bucket: {e}")
            return False
    
    def upload_file(self, user_id, file_obj, file_name, content_type='application/octet-stream'):
        """
        Télécharge un fichier vers le bucket de l'utilisateur
        
        Args:
            user_id: ID de l'utilisateur
            file_obj: Objet fichier (BytesIO ou fichier ouvert)
            file_name: Nom du fichier dans le bucket
            content_type: Type MIME du fichier
            
        Returns:
            str: URL du fichier ou None si erreur
        """
        if not self.s3_client:
            logging.warning("Client S3 non initialisé. Impossible d'uploader le fichier.")
            return None
            
        bucket_name = BUCKET_NAME_PREFIX
        user_key = f"users/{user_id}/{file_name}"
        
        try:
            extra_args = {
                'ContentType': content_type
            }
            
            # Télécharger le fichier
            self.s3_client.upload_fileobj(
                file_obj,
                bucket_name,
                user_key,
                ExtraArgs=extra_args
            )
            
            # Générer une URL présignée valide 1 heure
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': user_key},
                ExpiresIn=3600  # URL valide 1 heure
            )
            
            return url
        except ClientError as e:
            logging.error(f"Erreur lors du téléchargement du fichier: {e}")
            return None
    
    def download_file(self, user_id, file_name):
        """
        Télécharge un fichier depuis le bucket de l'utilisateur
        
        Args:
            user_id: ID de l'utilisateur
            file_name: Nom du fichier dans le bucket
            
        Returns:
            BytesIO: Contenu du fichier ou None si erreur
        """
        if not self.s3_client:
            logging.warning("Client S3 non initialisé. Impossible de télécharger le fichier.")
            return None
            
        bucket_name = BUCKET_NAME_PREFIX
        user_key = f"users/{user_id}/{file_name}"
        file_obj = BytesIO()
        
        try:
            self.s3_client.download_fileobj(bucket_name, user_key, file_obj)
            file_obj.seek(0)  # Remettre le curseur au début
            return file_obj
        except ClientError as e:
            logging.error(f"Erreur lors du téléchargement du fichier: {e}")
            return None
    
    def list_files(self, user_id, prefix=''):
        """
        Liste les fichiers dans l'espace de l'utilisateur
        
        Args:
            user_id: ID de l'utilisateur
            prefix: Préfixe pour filtrer les fichiers (dossier)
            
        Returns:
            list: Liste des fichiers ou liste vide si erreur
        """
        if not self.s3_client:
            logging.warning("Client S3 non initialisé. Impossible de lister les fichiers.")
            return []
            
        bucket_name = BUCKET_NAME_PREFIX
        user_prefix = f"users/{user_id}/{prefix}"
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=user_prefix
            )
            
            if 'Contents' in response:
                # Retirer complètement le préfixe utilisateur pour avoir juste le nom du fichier
                # Exemple: "users/1234/fichier.pdf" -> "fichier.pdf"
                files = []
                for item in response['Contents']:
                    # Extraire uniquement le nom du fichier, sans le préfixe du dossier utilisateur
                    key_parts = item['Key'].split('/')
                    # Le nom du fichier est la dernière partie après le dernier '/'
                    if len(key_parts) >= 3:  # Format attendu: "users/[id]/[nom-fichier]"
                        file_name = key_parts[-1]
                        files.append(file_name)
                return files
            return []
        except ClientError as e:
            logging.error(f"Erreur lors de la liste des fichiers: {e}")
            return []
    
    def delete_file(self, user_id, file_name):
        """
        Supprime un fichier de l'espace utilisateur
        
        Args:
            user_id: ID de l'utilisateur
            file_name: Nom du fichier dans l'espace utilisateur
            
        Returns:
            bool: True si la suppression a réussi, False sinon
        """
        if not self.s3_client:
            logging.warning("Client S3 non initialisé. Impossible de supprimer le fichier.")
            return False
            
        bucket_name = BUCKET_NAME_PREFIX
        user_key = f"users/{user_id}/{file_name}"
        
        try:
            self.s3_client.delete_object(
                Bucket=bucket_name,
                Key=user_key
            )
            return True
        except ClientError as e:
            logging.error(f"Erreur lors de la suppression du fichier: {e}")
            return False
    
    def get_storage_usage(self, user_id):
        """
        Calcule l'utilisation du stockage pour un utilisateur
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            int: Taille en octets ou 0 si erreur
        """
        if not self.s3_client:
            logging.warning("Client S3 non initialisé. Impossible de calculer l'utilisation du stockage.")
            return 0
            
        bucket_name = BUCKET_NAME_PREFIX
        user_prefix = f"users/{user_id}/"
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=user_prefix
            )
            
            total_size = 0
            if 'Contents' in response:
                for item in response['Contents']:
                    total_size += item['Size']
            
            return total_size
        except ClientError as e:
            logging.error(f"Erreur lors du calcul du stockage: {e}")
            return 0