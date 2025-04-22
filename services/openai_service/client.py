"""
Client pour l'API OpenAI.

Ce module fournit une interface simplifiée pour interagir avec l'API OpenAI.
"""

import os
import logging
from openai import OpenAI

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client pour l'API OpenAI."""
    
    def __init__(self, api_key=None):
        """
        Initialise le client OpenAI.
        
        Args:
            api_key (str, optional): Clé API OpenAI. Si non fournie, utilise OPENAI_API_KEY de l'environnement.
        """
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        
        if not self.api_key:
            logger.warning("OpenAI API key not provided and not found in environment variables")
            
        self.client = OpenAI(api_key=self.api_key)
        
    def generate_text(self, prompt, model="gpt-4o", max_tokens=1000, temperature=0.7, response_format=None):
        """
        Génère du texte à partir d'un prompt en utilisant l'API OpenAI.
        
        Args:
            prompt (str): Prompt à soumettre à l'API
            model (str, optional): Modèle à utiliser. Par défaut "gpt-4o".
            max_tokens (int, optional): Nombre maximum de tokens à générer. Par défaut 1000.
            temperature (float, optional): Température de l'échantillonnage. Par défaut 0.7.
            response_format (dict, optional): Format de la réponse. Par défaut None.
            
        Returns:
            openai.ChatCompletion: Réponse de l'API OpenAI
        """
        try:
            # Préparer les paramètres de la requête
            params = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            # Ajouter le format de réponse si spécifié
            if response_format:
                params["response_format"] = response_format
            
            # Appeler l'API
            response = self.client.chat.completions.create(**params)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating text with OpenAI: {e}")
            raise
    
    def generate_streaming_text(self, prompt, model="gpt-4o", max_tokens=1000, temperature=0.7):
        """
        Génère du texte en streaming à partir d'un prompt en utilisant l'API OpenAI.
        
        Args:
            prompt (str): Prompt à soumettre à l'API
            model (str, optional): Modèle à utiliser. Par défaut "gpt-4o".
            max_tokens (int, optional): Nombre maximum de tokens à générer. Par défaut 1000.
            temperature (float, optional): Température de l'échantillonnage. Par défaut 0.7.
            
        Returns:
            iterator: Itérateur sur les chunks de réponse
        """
        try:
            # Appeler l'API en mode streaming
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating streaming text with OpenAI: {e}")
            raise
    
    def analyze_image(self, image_path, prompt, model="gpt-4o"):
        """
        Analyse une image en utilisant l'API Vision d'OpenAI.
        
        Args:
            image_path (str): Chemin vers l'image à analyser
            prompt (str): Instructions pour l'analyse de l'image
            model (str, optional): Modèle à utiliser. Par défaut "gpt-4o".
            
        Returns:
            str: Résultat de l'analyse
        """
        try:
            import base64
            
            # Lire et encoder l'image en base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Appeler l'API
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error analyzing image with OpenAI: {e}")
            raise
    
    def list_models(self):
        """
        Liste les modèles disponibles via l'API OpenAI.
        
        Returns:
            list: Liste des modèles disponibles
        """
        try:
            models = self.client.models.list()
            return [model.id for model in models.data]
            
        except Exception as e:
            logger.error(f"Error listing OpenAI models: {e}")
            return None