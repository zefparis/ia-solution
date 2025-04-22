"""
Service OpenAI - Microservice responsable des interactions avec l'API OpenAI

Ce service encapsule toutes les interactions avec l'API OpenAI, fournissant 
une interface unifiée et optimisée avec mise en cache des résultats.
"""

import os
import json
import logging
import time
from datetime import datetime

import openai
from openai import OpenAI
from flask import Blueprint, request, jsonify, current_app

from cache.flask_integration import openai_cached, rate_limited

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Création du Blueprint pour le service OpenAI
openai_service = Blueprint('openai_service', __name__, url_prefix='/api/openai')

# Client OpenAI
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


@openai_service.route('/health', methods=['GET'])
def health_check():
    """Endpoint de vérification de l'état du service OpenAI."""
    start_time = time.time()
    
    # Vérifier que la clé API OpenAI est configurée
    api_key = os.environ.get("OPENAI_API_KEY")
    api_key_status = "disponible" if api_key else "non configurée"
    
    # Vérifier l'accès au cache Redis si disponible
    redis_status = "non vérifié"
    if hasattr(current_app, 'extensions') and 'redis_cache' in current_app.extensions:
        try:
            redis_client = current_app.extensions['redis_cache'].redis_client
            if redis_client.ping():
                redis_status = "disponible"
            else:
                redis_status = "non disponible"
        except Exception as e:
            redis_status = f"erreur: {str(e)}"
    
    # Préparer la réponse
    response = {
        'service': 'openai_service',
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'response_time_ms': (time.time() - start_time) * 1000,
        'dependencies': {
            'openai_api': {
                'status': 'unchecked',  # Nous ne faisons pas d'appel API dans le healthcheck
                'api_key': api_key_status
            },
            'redis_cache': {
                'status': redis_status
            }
        }
    }
    
    return jsonify(response)


@openai_service.route('/complete', methods=['POST'])
@rate_limited(limit=60, period=60)  # Limiter à 60 requêtes par minute
@openai_cached(ttl=24*3600)  # Mettre en cache pendant 24 heures
def complete_text():
    """
    Endpoint pour compléter du texte avec l'API OpenAI.
    
    Requête JSON attendue:
    {
        "prompt": "Texte à compléter",
        "model": "gpt-4o", // Optionnel, par défaut "gpt-4o"
        "temperature": 0.7, // Optionnel, par défaut 0.7
        "max_tokens": 500, // Optionnel, par défaut 500
        "stream": false // Optionnel, par défaut false
    }
    """
    # Récupérer et valider les paramètres
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({
            'error': 'Paramètres manquants',
            'message': 'Le paramètre "prompt" est requis'
        }), 400
    
    # Extraire les paramètres
    prompt = data['prompt']
    model = data.get('model', 'gpt-4o')  # le newest OpenAI model est "gpt-4o" which was released May 13, 2024
    temperature = float(data.get('temperature', 0.7))
    max_tokens = int(data.get('max_tokens', 500))
    stream = bool(data.get('stream', False))
    
    # Vérifier si le streaming est demandé
    if stream:
        return stream_completion(prompt, model, temperature, max_tokens)
    
    # Sinon, effectuer une requête standard
    try:
        start_time = time.time()
        
        # Appel à l'API OpenAI
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Calculer le temps de réponse
        elapsed_time = time.time() - start_time
        
        # Préparer la réponse JSON
        result = {
            'text': response.choices[0].message.content,
            'model': model,
            'usage': {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            },
            'response_time_seconds': elapsed_time
        }
        
        return jsonify(result)
    
    except openai.OpenAIError as e:
        logger.error(f"Erreur OpenAI: {e}")
        return jsonify({
            'error': 'Erreur OpenAI',
            'message': str(e)
        }), 500
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        return jsonify({
            'error': 'Erreur serveur',
            'message': str(e)
        }), 500


def stream_completion(prompt, model, temperature, max_tokens):
    """
    Effectue une complétion en streaming et renvoie les résultats au fur et à mesure.
    
    Args:
        prompt (str): Prompt pour la complétion
        model (str): Modèle à utiliser
        temperature (float): Température pour la génération
        max_tokens (int): Nombre maximum de tokens
        
    Returns:
        flask.Response: Réponse en streaming
    """
    def generate():
        try:
            # Appel à l'API OpenAI avec streaming
            response = openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            # Envoyer les chunks de réponse au fur et à mesure
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield f"data: {json.dumps({'text': content})}\n\n"
            
            # Indiquer la fin du streaming
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            logger.error(f"Erreur lors du streaming: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return current_app.response_class(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'  # Pour Nginx
        }
    )


@openai_service.route('/analyze', methods=['POST'])
@rate_limited(limit=30, period=60)  # Limiter à 30 requêtes par minute
@openai_cached(ttl=24*3600)  # Mettre en cache pendant 24 heures
def analyze_text():
    """
    Endpoint pour analyser du texte avec l'API OpenAI et extraire des informations structurées.
    
    Requête JSON attendue:
    {
        "text": "Texte à analyser",
        "analysis_type": "sentiment|entities|keywords|summary|custom",
        "custom_instructions": "Instructions personnalisées si analysis_type=custom",
        "model": "gpt-4o", // Optionnel, par défaut "gpt-4o"
        "format": "json|text", // Optionnel, par défaut "json"
    }
    """
    # Récupérer et valider les paramètres
    data = request.get_json()
    if not data or 'text' not in data or 'analysis_type' not in data:
        return jsonify({
            'error': 'Paramètres manquants',
            'message': 'Les paramètres "text" et "analysis_type" sont requis'
        }), 400
    
    # Extraire les paramètres
    text = data['text']
    analysis_type = data['analysis_type']
    custom_instructions = data.get('custom_instructions', '')
    model = data.get('model', 'gpt-4o')  # le newest OpenAI model est "gpt-4o" which was released May 13, 2024
    response_format = data.get('format', 'json')
    
    # Construire les instructions en fonction du type d'analyse
    if analysis_type == 'sentiment':
        instructions = """
        Analyse le sentiment du texte suivant et fournit:
        1. Le score de sentiment (de -1 à 1, où -1 est très négatif et 1 très positif)
        2. La confiance de ton analyse (de 0 à 1)
        3. Les émotions détectées (liste)
        4. Un résumé de ton analyse
        
        Réponds uniquement au format JSON avec cette structure:
        {
            "sentiment_score": float,
            "confidence": float,
            "emotions": [str],
            "summary": str
        }
        """
    elif analysis_type == 'entities':
        instructions = """
        Identifie les entités nommées dans le texte suivant:
        1. Personnes
        2. Organisations
        3. Lieux
        4. Dates
        5. Autres entités pertinentes
        
        Réponds uniquement au format JSON avec cette structure:
        {
            "entities": {
                "persons": [{"name": str, "mentions": int}],
                "organizations": [{"name": str, "mentions": int}],
                "locations": [{"name": str, "mentions": int}],
                "dates": [{"date": str, "context": str}],
                "other": [{"type": str, "name": str, "mentions": int}]
            }
        }
        """
    elif analysis_type == 'keywords':
        instructions = """
        Extrais les mots-clés et expressions importantes du texte suivant:
        1. Les 10 mots-clés les plus importants
        2. Les 5 expressions/concepts clés
        3. Une catégorisation du texte
        
        Réponds uniquement au format JSON avec cette structure:
        {
            "keywords": [{"word": str, "relevance": float}],
            "key_phrases": [{"phrase": str, "relevance": float}],
            "categories": [str]
        }
        """
    elif analysis_type == 'summary':
        instructions = """
        Fais un résumé concis du texte suivant:
        1. Un résumé court (max 50 mots)
        2. Un résumé détaillé (max 200 mots)
        3. Les points clés (bullet points)
        
        Réponds uniquement au format JSON avec cette structure:
        {
            "short_summary": str,
            "detailed_summary": str,
            "key_points": [str]
        }
        """
    elif analysis_type == 'custom':
        if not custom_instructions:
            return jsonify({
                'error': 'Instructions manquantes',
                'message': 'Le paramètre "custom_instructions" est requis pour le type d\'analyse "custom"'
            }), 400
        instructions = custom_instructions
    else:
        return jsonify({
            'error': 'Type d\'analyse invalide',
            'message': 'Le type d\'analyse doit être l\'un des suivants: sentiment, entities, keywords, summary, custom'
        }), 400
    
    # Construire le prompt complet
    prompt = f"{instructions}\n\nTexte à analyser: {text}"
    
    try:
        start_time = time.time()
        
        # Configuration du format de réponse pour OpenAI
        response_format_param = None
        if response_format == 'json':
            response_format_param = {"type": "json_object"}
        
        # Appel à l'API OpenAI
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": prompt}],
            response_format=response_format_param
        )
        
        # Calculer le temps de réponse
        elapsed_time = time.time() - start_time
        
        # Préparer la réponse
        content = response.choices[0].message.content
        
        # Si le format est JSON, valider et parser la réponse
        if response_format == 'json':
            try:
                result = json.loads(content)
                # Ajouter des métadonnées
                result['_metadata'] = {
                    'analysis_type': analysis_type,
                    'model': model,
                    'response_time_seconds': elapsed_time,
                    'timestamp': datetime.now().isoformat()
                }
                return jsonify(result)
            except json.JSONDecodeError:
                # Si la réponse n'est pas un JSON valide, la renvoyer comme texte
                logger.warning("La réponse OpenAI n'est pas un JSON valide, renvoi en tant que texte")
                return jsonify({
                    'text': content,
                    '_metadata': {
                        'analysis_type': analysis_type,
                        'model': model,
                        'response_time_seconds': elapsed_time,
                        'timestamp': datetime.now().isoformat(),
                        'format_warning': 'La réponse n\'était pas au format JSON valide'
                    }
                })
        else:
            # Réponse au format texte
            return jsonify({
                'text': content,
                '_metadata': {
                    'analysis_type': analysis_type,
                    'model': model,
                    'response_time_seconds': elapsed_time,
                    'timestamp': datetime.now().isoformat()
                }
            })
    
    except openai.OpenAIError as e:
        logger.error(f"Erreur OpenAI: {e}")
        return jsonify({
            'error': 'Erreur OpenAI',
            'message': str(e)
        }), 500
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        return jsonify({
            'error': 'Erreur serveur',
            'message': str(e)
        }), 500


def register_service(app):
    """
    Enregistre le service OpenAI auprès de l'application Flask.
    
    Args:
        app: L'application Flask
    """
    # Enregistrer le blueprint
    app.register_blueprint(openai_service)
    
    logger.info("Service OpenAI enregistré avec succès")