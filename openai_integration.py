import json
import os
from typing import List, Dict, Any, Optional

# Nous utilisons "gpt-4" car le compte actuel n'a pas accès à "gpt-4o"
# Revenir à "gpt-4o" si l'accès est activé ultérieurement
from openai import OpenAI

# Configuration du client OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def get_completion(messages: List[Dict[str, str]], 
                   model: str = "gpt-4", 
                   temperature: float = 0.8,
                   max_tokens: int = 2000) -> str:
    """
    Obtient une réponse du modèle OpenAI pour une liste de messages.
    
    Args:
        messages: Liste de dictionnaires contenant "role" et "content" pour chaque message
        model: Modèle OpenAI à utiliser
        temperature: Contrôle de la créativité (0 à 1)
        max_tokens: Nombre maximum de tokens pour la réponse
        
    Returns:
        La réponse générée par le modèle
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Erreur lors de l'appel à l'API OpenAI: {e}")
        return f"Désolé, une erreur s'est produite lors de la communication avec l'API. Détails: {str(e)}"

def analyze_document(text: str) -> Dict[str, Any]:
    """
    Analyse un document financier pour en extraire les informations pertinentes.
    
    Args:
        text: Le texte du document à analyser
        
    Returns:
        Un dictionnaire contenant les informations extraites
    """
    prompt = [
        {"role": "system", "content": """
        Tu es un expert en analyse de documents financiers. Ton travail consiste à extraire les informations 
        pertinentes des documents comme les factures, reçus et relevés bancaires. 
        
        Fournis les informations suivantes au format JSON :
        - document_type: le type de document (facture, reçu, relevé bancaire, etc.)
        - vendor: le nom du fournisseur ou commerçant
        - date: la date de la transaction (format YYYY-MM-DD)
        - amount: le montant total (nombre décimal)
        - tax_amount: le montant de la TVA si présent (nombre décimal)
        - tax_rate: le taux de TVA en pourcentage (nombre décimal)
        - payment_method: le moyen de paiement (carte, espèces, chèque, etc.)
        - category: suggestion de catégorie (restauration, transport, logement, etc.)
        - description: description concise de la transaction
        - is_expense: true si c'est une dépense, false si c'est un revenu
        - confidence: ton niveau de confiance sur cette analyse (0 à 1)
        - details: tout détail supplémentaire pertinent
        
        Si une information est manquante, utilise null pour sa valeur.
        """
        },
        {"role": "user", "content": f"Voici le texte extrait d'un document financier :\n\n{text}\n\nAnalyse ce document et extrais les informations pertinentes."}
    ]
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=prompt,
            temperature=0.3,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        # Convertir la réponse JSON en dictionnaire Python
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f"Erreur lors de l'analyse du document: {e}")
        return {
            "document_type": "inconnu",
            "confidence": 0,
            "error": str(e)
        }

def generate_tax_report(transactions: List[Dict[str, Any]], 
                        start_date: str, 
                        end_date: str,
                        user_info: Dict[str, Any]) -> str:
    """
    Génère un rapport fiscal basé sur une liste de transactions.
    
    Args:
        transactions: Liste des transactions à inclure dans le rapport
        start_date: Date de début de la période (format YYYY-MM-DD)
        end_date: Date de fin de la période (format YYYY-MM-DD)
        user_info: Informations sur l'utilisateur
        
    Returns:
        Un rapport formaté en HTML
    """
    # Transformation des transactions en texte pour le prompt
    transactions_text = json.dumps(transactions, indent=2, ensure_ascii=False)
    
    prompt = [
        {"role": "system", "content": """
        Tu es un expert-comptable virtuel. Ton travail consiste à générer des rapports fiscaux clairs et informatifs
        basés sur les transactions fournies. Le rapport doit être formaté en HTML pour l'affichage sur le web.
        
        Le rapport doit inclure:
        1. Un résumé des revenus et dépenses
        2. Une répartition par catégorie
        3. Un calcul de la TVA (si applicable)
        4. Une estimation des impôts (si possible)
        5. Des graphiques et tableaux pertinents (décrits en HTML, ils seront rendus côté client)
        6. Des recommandations fiscales personnalisées
        
        Utilise des balises HTML appropriées pour structurer le rapport, mais pas de balises head, body ou html complètes.
        """
        },
        {"role": "user", "content": f"""
        Voici les transactions pour la période du {start_date} au {end_date}:
        
        {transactions_text}
        
        Informations sur l'utilisateur:
        {json.dumps(user_info, indent=2, ensure_ascii=False)}
        
        Génère un rapport fiscal complet formaté en HTML.
        """}
    ]
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=prompt,
            temperature=0.5,
            max_tokens=4000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Erreur lors de la génération du rapport fiscal: {e}")
        return f"""
        <div class="alert alert-danger">
            <h4>Erreur lors de la génération du rapport</h4>
            <p>{str(e)}</p>
        </div>
        """

def financial_advice(transactions: List[Dict[str, Any]], 
                    user_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Génère des conseils financiers personnalisés basés sur l'historique de transactions.
    
    Args:
        transactions: Liste des transactions récentes
        user_profile: Profil et préférences de l'utilisateur
        
    Returns:
        Dictionnaire contenant des conseils et analyses
    """
    transactions_text = json.dumps(transactions, indent=2, ensure_ascii=False)
    profile_text = json.dumps(user_profile, indent=2, ensure_ascii=False)
    
    prompt = [
        {"role": "system", "content": """
        Tu es un conseiller financier virtuel. Ton objectif est d'analyser les habitudes de dépenses
        et de fournir des conseils financiers personnalisés. 
        
        Réponds au format JSON avec les sections suivantes:
        - spending_analysis: analyse des habitudes de dépenses
        - savings_opportunities: opportunités d'économies identifiées
        - budget_recommendations: recommandations pour un meilleur budget
        - financial_goals: suggestions d'objectifs financiers adaptés
        - action_items: actions concrètes à entreprendre (liste)
        """
        },
        {"role": "user", "content": f"""
        Voici mes transactions récentes:
        {transactions_text}
        
        Et mon profil:
        {profile_text}
        
        Analyse mes finances et donne-moi des conseils personnalisés.
        """}
    ]
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=prompt,
            temperature=0.7,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f"Erreur lors de la génération des conseils financiers: {e}")
        return {
            "error": str(e),
            "spending_analysis": "Analyse non disponible en raison d'une erreur.",
            "action_items": ["Réessayer plus tard."]
        }


def get_openai_response(prompt: str, 
                        model: str = "gpt-4", 
                        temperature: float = 0.7, 
                        max_tokens: int = 3000,
                        json_mode: bool = False,
                        system_prompt: Optional[str] = None) -> str:
    """
    Obtient une réponse d'OpenAI pour un prompt donné.
    
    Args:
        prompt: Le texte du prompt à envoyer à l'API
        model: Le modèle OpenAI à utiliser
        temperature: Contrôle de la créativité (0 à 1)
        max_tokens: Nombre maximum de tokens pour la réponse
        json_mode: Si True, demande une réponse au format JSON
        system_prompt: Instructions système personnalisées (optionnel)
        
    Returns:
        La réponse générée par le modèle
    """
    try:
        # Créer les messages avec ou sans system prompt
        if system_prompt:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        else:
            messages = [{"role": "user", "content": prompt}]
        
        # Configuration de la requête
        request_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Ajouter le format JSON si demandé
        if json_mode:
            request_params["response_format"] = {"type": "json_object"}
        
        # Appel à l'API
        response = client.chat.completions.create(**request_params)
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Erreur lors de l'appel à l'API OpenAI: {e}")
        if json_mode:
            # Retourner un JSON d'erreur valide
            return json.dumps({
                "error": str(e),
                "message": "Une erreur s'est produite lors de la communication avec l'API."
            })
        else:
            return f"Désolé, une erreur s'est produite lors de la communication avec l'API. Détails: {str(e)}"