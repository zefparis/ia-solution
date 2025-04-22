"""
Module pour l'intégration d'OpenAI pour la génération de contenu marketing
"""
import os
import json
import logging
from openai import OpenAI

# Configurer le logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialiser le client OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

def generate_marketing_content(prompt, language='fr'):
    """
    Génère du contenu marketing en utilisant l'API OpenAI
    
    Args:
        prompt (str): Instructions pour la génération de contenu
        language (str): Code de langue (fr, en, etc.)
    
    Returns:
        str: Contenu généré
    """
    try:
        # Adapter les instructions selon la langue
        if language == 'en':
            system_prompt = "You are an expert marketing content creator. Create engaging and persuasive content."
        else:  # Par défaut en français
            system_prompt = "Vous êtes un expert en création de contenu marketing. Créez du contenu engageant et persuasif."

        # Appel à l'API OpenAI
        # Le modèle le plus récent d'OpenAI est "gpt-4o" qui a été publié le 13 mai 2024.
        # Ne pas le modifier sauf si explicitement demandé par l'utilisateur
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.7
        )
        
        # Extraire et retourner le contenu généré
        return response.choices[0].message.content
    
    except Exception as e:
        logger.error(f"Erreur lors de la génération de contenu marketing: {str(e)}")
        raise


def generate_editorial_calendar(business_sector, platforms, topics, start_date, end_date, frequency='weekly', language='fr'):
    """
    Génère un calendrier éditorial intelligent pour différentes plateformes
    
    Args:
        business_sector (str): Secteur d'activité de l'entreprise
        platforms (list): Liste des plateformes à utiliser
        topics (list): Liste des sujets à couvrir
        start_date (str): Date de début (format YYYY-MM-DD)
        end_date (str): Date de fin (format YYYY-MM-DD)
        frequency (str): Fréquence des publications (daily, weekly, etc.)
        language (str): Code de langue (fr, en, etc.)
    
    Returns:
        list: Liste des entrées du calendrier éditorial
    """
    try:
        # Adapter les instructions selon la langue
        if language == 'en':
            system_prompt = "You are an expert content strategist. Create a strategic editorial calendar based on the provided parameters."
            prompt = f"""
            Create a detailed editorial calendar for a business in the {business_sector} sector.
            
            Parameters:
            - Platforms: {', '.join(platforms)}
            - Topics to cover: {', '.join(topics)}
            - Start date: {start_date}
            - End date: {end_date}
            - Post frequency: {frequency}
            
            For each entry, include:
            1. Date (in YYYY-MM-DD format)
            2. Platform (from the list provided)
            3. Content type (post, story, reel, newsletter, etc.)
            4. Brief content idea (1-2 sentences)
            5. Best time to post (HH:MM format)
            
            Return the calendar as a JSON array of objects with these fields.
            """
        else:  # Par défaut en français
            system_prompt = "Vous êtes un expert en stratégie de contenu. Créez un calendrier éditorial stratégique basé sur les paramètres fournis."
            prompt = f"""
            Créez un calendrier éditorial détaillé pour une entreprise du secteur {business_sector}.
            
            Paramètres :
            - Plateformes : {', '.join(platforms)}
            - Sujets à couvrir : {', '.join(topics)}
            - Date de début : {start_date}
            - Date de fin : {end_date}
            - Fréquence de publication : {frequency}
            
            Pour chaque entrée, incluez :
            1. Date (au format YYYY-MM-DD)
            2. Plateforme (parmi la liste fournie)
            3. Type de contenu (publication, story, reel, newsletter, etc.)
            4. Idée de contenu brève (1-2 phrases)
            5. Meilleur moment pour publier (format HH:MM)
            
            Retournez le calendrier sous forme d'un tableau JSON d'objets avec ces champs.
            """

        # Appel à l'API OpenAI
        response = openai.chat.completions.create(
            model="gpt-4o",  # Le modèle le plus récent d'OpenAI
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        # Parser et retourner le calendrier
        result = json.loads(response.choices[0].message.content)
        
        # Gérer différentes structures de réponse possibles
        if 'calendar' in result:
            return result['calendar']
        elif 'schedule' in result:
            return result['schedule']
        elif 'entries' in result:
            return result['entries']
        else:
            # Si aucun champ spécifique n'est identifié, essayer de trouver une liste
            for key, value in result.items():
                if isinstance(value, list):
                    return value
            
            # Si aucune liste n'est trouvée, retourner une liste vide
            logger.warning("Impossible de trouver le calendrier éditorial dans la réponse de l'API")
            return []
    
    except Exception as e:
        logger.error(f"Erreur lors de la génération du calendrier éditorial : {str(e)}")
        raise


def create_content_variations(original_content, num_variations=3, language='fr'):
    """
    Crée des variations d'un contenu marketing existant
    
    Args:
        original_content (str): Contenu original
        num_variations (int): Nombre de variations à générer
        language (str): Code de langue (fr, en, etc.)
    
    Returns:
        list: Liste des variations générées
    """
    try:
        # Adapter les instructions selon la langue
        if language == 'en':
            prompt = f"Create {num_variations} different variations of the following content. Maintain the same message but vary the tone, structure, and wording:\n\n{original_content}"
        else:  # Par défaut en français
            prompt = f"Créez {num_variations} variations différentes du contenu suivant. Conservez le même message mais variez le ton, la structure et le vocabulaire :\n\n{original_content}"

        # Appel à l'API OpenAI
        response = openai.chat.completions.create(
            model="gpt-4o",  # Le modèle le plus récent d'OpenAI est "gpt-4o"
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.8,
            response_format={"type": "json_object"}
        )
        
        # Essayer de parser la réponse en tant que JSON
        try:
            content = response.choices[0].message.content
            # Si la réponse est déjà en JSON, la parser
            data = json.loads(content)
            
            # Vérifier différentes structures possibles
            if 'variations' in data:
                return data['variations']
            elif 'results' in data:
                return data['results']
            else:
                # Essayer de trouver une liste dans le JSON
                for key, value in data.items():
                    if isinstance(value, list):
                        return value
                
                # Si on ne trouve pas de liste, retourner les valeurs
                return list(data.values())
                
        except json.JSONDecodeError:
            # Si ce n'est pas du JSON, essayer de parser le texte en sections
            content = response.choices[0].message.content
            variations = []
            current_var = ""
            
            for line in content.split('\n'):
                if line.strip().startswith(('Variation', 'Version', '#', '1.', '2.', '3.')):
                    if current_var:
                        variations.append(current_var.strip())
                    current_var = line.split(':', 1)[-1] if ':' in line else ""
                else:
                    current_var += "\n" + line
            
            if current_var:
                variations.append(current_var.strip())
            
            # Si nous n'avons pas réussi à extraire des variations, diviser simplement le texte
            if not variations:
                variations = [content]
            
            return variations[:num_variations]
    
    except Exception as e:
        logger.error(f"Erreur lors de la création de variations de contenu: {str(e)}")
        raise


def analyze_content_performance(content, metrics, language='fr'):
    """
    Analyse la performance d'un contenu marketing et fournit des recommandations
    
    Args:
        content (str): Contenu à analyser
        metrics (dict): Métriques de performance (vues, clics, conversions, etc.)
        language (str): Code de langue (fr, en, etc.)
    
    Returns:
        dict: Analyse et recommandations
    """
    try:
        # Adapter les instructions selon la langue
        if language == 'en':
            system_prompt = "You are an expert marketing analyst. Analyze the content and its performance metrics, then provide improvement recommendations."
            prompt = f"Content: {content}\n\nPerformance Metrics: {json.dumps(metrics)}\n\nProvide an analysis of this content's performance and suggestions for improvement. Return your response as JSON with 'analysis', 'strengths', 'weaknesses', and 'recommendations' fields."
        else:  # Par défaut en français
            system_prompt = "Vous êtes un expert en analyse marketing. Analysez le contenu et ses métriques de performance, puis fournissez des recommandations d'amélioration."
            prompt = f"Contenu : {content}\n\nMétriques de performance : {json.dumps(metrics)}\n\nFournissez une analyse de la performance de ce contenu et des suggestions d'amélioration. Retournez votre réponse en JSON avec les champs 'analyse', 'forces', 'faiblesses' et 'recommandations'."

        # Appel à l'API OpenAI
        response = openai.chat.completions.create(
            model="gpt-4o",  # Le modèle le plus récent d'OpenAI est "gpt-4o"
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        
        # Parser et retourner l'analyse
        return json.loads(response.choices[0].message.content)
    
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse de performance du contenu: {str(e)}")
        raise


# La fonction de génération de calendrier a été définie au début du fichier