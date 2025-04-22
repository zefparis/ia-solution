"""
Module pour intégrer AWS Textract pour l'extraction de texte à partir d'images
"""
import base64
import json
import logging
import re
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

def get_textract_client():
    """
    Crée et retourne un client AWS Textract
    """
    return boto3.client('textract', 
                       region_name='eu-west-3')  # Utilisez la même région que votre bucket S3

def extract_text_from_base64(base64_image):
    """
    Extrait du texte à partir d'une image encodée en base64 en utilisant AWS Textract
    
    Args:
        base64_image (str): Image encodée en base64
        
    Returns:
        dict: Résultats de l'extraction avec texte brut et analyse
    """
    try:
        # Décoder l'image base64
        image_bytes = base64.b64decode(base64_image)
        
        # Obtenir le client Textract
        textract_client = get_textract_client()
        
        # Appeler l'API Textract pour l'analyse d'image brute
        response = textract_client.detect_document_text(
            Document={'Bytes': image_bytes}
        )
        
        # Extraire le texte complet
        full_text = ""
        for item in response["Blocks"]:
            if item["BlockType"] == "LINE":
                full_text += item["Text"] + "\n"
        
        # Analyse avancée pour documents financiers (factures, reçus)
        # Réutiliser l'image pour une analyse plus spécifique
        analysis_response = textract_client.analyze_document(
            Document={'Bytes': image_bytes},
            FeatureTypes=['FORMS', 'TABLES']
        )
        
        # Extraire les champs-clés potentiels
        extracted_info = extract_financial_info(analysis_response)
        
        return {
            "success": True,
            "text": full_text.strip(),
            "extracted_info": extracted_info
        }
    
    except ClientError as e:
        logger.error(f"Erreur AWS Textract: {str(e)}")
        return {
            "success": False,
            "error": f"Erreur lors de l'extraction avec AWS Textract: {str(e)}",
            "text": ""
        }
    except Exception as e:
        logger.error(f"Erreur inattendue: {str(e)}")
        return {
            "success": False,
            "error": f"Erreur inattendue lors de l'extraction: {str(e)}",
            "text": ""
        }

def analyze_expense_document(base64_image):
    """
    Analyse un document de dépense (facture, reçu) en utilisant AnalyzeExpense d'AWS Textract
    
    Args:
        base64_image (str): Image encodée en base64
        
    Returns:
        dict: Résultats détaillés de l'analyse avec montants, dates, vendeur...
    """
    try:
        # Décoder l'image base64
        image_bytes = base64.b64decode(base64_image)
        
        # Obtenir le client Textract
        textract_client = get_textract_client()
        
        # Appeler l'API Textract pour l'analyse spécifique de dépenses
        response = textract_client.analyze_expense(
            Document={'Bytes': image_bytes}
        )
        
        # Extraire les informations pertinentes
        result = {}
        
        # Extraire le texte complet
        full_text = ""
        
        # Traiter les documents
        if 'ExpenseDocuments' in response:
            for doc in response['ExpenseDocuments']:
                # Identifier le type de document
                doc_type = "receipt" if 'Receipt' in str(doc) else "invoice"
                result['document_type'] = doc_type
                
                # Extraire les champs pour factures/reçus
                if 'SummaryFields' in doc:
                    for field in doc['SummaryFields']:
                        if 'Type' in field and 'ValueDetection' in field:
                            field_type = field['Type']['Text']
                            field_value = field['ValueDetection'].get('Text', '')
                            
                            # Traiter les différents types de champs
                            if field_type == 'TOTAL':
                                result['amount'] = clean_amount(field_value)
                            elif field_type == 'INVOICE_RECEIPT_DATE':
                                result['date'] = field_value
                            elif field_type == 'VENDOR_NAME':
                                result['vendor'] = field_value
                            elif field_type == 'TAX':
                                result['tax_amount'] = clean_amount(field_value)
                            elif field_type == 'SUBTOTAL':
                                result['subtotal'] = clean_amount(field_value)
        
        # Essayer de collecter du texte brut à partir de la réponse
        blocks_found = False
        for block in response.get('Blocks', []):
            if block.get('BlockType') == 'LINE':
                full_text += block.get('Text', '') + "\n"
                blocks_found = True
        
        # Si aucun bloc de texte n'a été trouvé dans la réponse AnalyzeExpense,
        # essayer d'extraire le texte avec detect_document_text
        if not blocks_found:
            try:
                # Appeler l'API de base pour l'extraction de texte
                text_response = textract_client.detect_document_text(
                    Document={'Bytes': image_bytes}
                )
                
                for item in text_response.get("Blocks", []):
                    if item.get("BlockType") == "LINE":
                        full_text += item.get("Text", "") + "\n"
            except Exception as e:
                logger.warning(f"Erreur lors de l'extraction secondaire de texte: {str(e)}")
                
        # Si le texte est toujours vide, essayer de construire un texte à partir des champs extraits
        if not full_text.strip() and 'vendor' in result:
            full_text = f"Document: {result.get('document_type', 'Facture/Reçu')}\n"
            if 'vendor' in result:
                full_text += f"Fournisseur: {result['vendor']}\n"
            if 'amount' in result:
                full_text += f"Montant: {result['amount']}\n"
            if 'date' in result:
                full_text += f"Date: {result['date']}\n"
        
        result['full_text'] = full_text.strip()
        
        # Si le montant n'a pas été trouvé, essayer de l'extraire du texte
        if 'amount' not in result:
            amount_match = re.search(r'(?:TOTAL|MONTANT)\s*:?\s*(\d+[,.]\d+)', full_text, re.IGNORECASE)
            if amount_match:
                result['amount'] = clean_amount(amount_match.group(1))
        
        # Si la date n'a pas été trouvée, essayer de l'extraire du texte
        if 'date' not in result:
            date_match = re.search(r'(?:DATE)\s*:?\s*(\d{2}[/.-]\d{2}[/.-]\d{4})', full_text, re.IGNORECASE)
            if date_match:
                result['date'] = date_match.group(1)
        
        return {
            "success": True,
            "extracted_info": result,
            "text": full_text
        }
    
    except ClientError as e:
        logger.error(f"Erreur AWS Textract AnalyzeExpense: {str(e)}")
        return {
            "success": False,
            "error": f"Erreur lors de l'analyse avec AWS Textract: {str(e)}",
            "text": ""
        }
    except Exception as e:
        logger.error(f"Erreur inattendue: {str(e)}")
        return {
            "success": False,
            "error": f"Erreur inattendue lors de l'analyse: {str(e)}",
            "text": ""
        }

def extract_financial_info(analysis_response):
    """
    Extrait les informations financières pertinentes d'une réponse Textract
    
    Args:
        analysis_response (dict): Réponse de l'API Textract
        
    Returns:
        dict: Informations financières extraites (montant, date, vendeur, etc.)
    """
    result = {}
    
    # Texte complet pour les expressions régulières
    full_text = ""
    
    # Extraire les données de formulaire
    form_data = {}
    for block in analysis_response["Blocks"]:
        # Collecter le texte complet
        if block["BlockType"] == "LINE":
            full_text += block["Text"] + "\n"
        
        # Extraire les paires clé-valeur
        if block["BlockType"] == "KEY_VALUE_SET":
            if "KEY" in block.get("EntityTypes", []):
                key = ""
                for relationship in block.get("Relationships", []):
                    if relationship["Type"] == "CHILD":
                        for child_id in relationship["Ids"]:
                            child_block = next((b for b in analysis_response["Blocks"] if b["Id"] == child_id), None)
                            if child_block and child_block["BlockType"] == "WORD":
                                key += child_block["Text"] + " "
                
                # Chercher la valeur associée
                value = ""
                for relationship in block.get("Relationships", []):
                    if relationship["Type"] == "VALUE":
                        for value_id in relationship["Ids"]:
                            value_block = next((b for b in analysis_response["Blocks"] if b["Id"] == value_id), None)
                            if value_block:
                                for child_relationship in value_block.get("Relationships", []):
                                    if child_relationship["Type"] == "CHILD":
                                        for child_id in child_relationship["Ids"]:
                                            child_block = next((b for b in analysis_response["Blocks"] if b["Id"] == child_id), None)
                                            if child_block and child_block["BlockType"] == "WORD":
                                                value += child_block["Text"] + " "
                
                key = key.strip().lower()
                value = value.strip()
                if key and value:
                    form_data[key] = value
    
    # Essayer d'identifier des informations financières spécifiques
    # Montant / Total
    for key in ["total", "montant", "amount", "somme"]:
        if key in form_data:
            result["amount"] = clean_amount(form_data[key])
            break
    
    # Date
    for key in ["date", "date de facturation", "date d'émission"]:
        if key in form_data:
            result["date"] = form_data[key]
            break
    
    # Vendeur / Fournisseur
    for key in ["fournisseur", "vendeur", "société", "magasin", "émetteur", "de"]:
        if key in form_data:
            result["vendor"] = form_data[key]
            break
    
    # TVA
    for key in ["tva", "taxe", "tax"]:
        if key in form_data:
            result["tax_amount"] = clean_amount(form_data[key])
            break
    
    # Si certaines informations n'ont pas été trouvées, utiliser des expressions régulières
    if "amount" not in result:
        amount_match = re.search(r'(?:TOTAL|MONTANT)\s*:?\s*(\d+[,.]\d+)', full_text, re.IGNORECASE)
        if amount_match:
            result["amount"] = clean_amount(amount_match.group(1))
    
    if "date" not in result:
        date_match = re.search(r'(?:DATE)\s*:?\s*(\d{2}[/.-]\d{2}[/.-]\d{4})', full_text, re.IGNORECASE)
        if date_match:
            result["date"] = date_match.group(1)
    
    if "vendor" not in result:
        vendor_match = re.search(r'(?:FOURNISSEUR|VENDEUR|MAGASIN)\s*:?\s*([A-Za-z0-9\s]{3,30})', full_text, re.IGNORECASE)
        if vendor_match:
            result["vendor"] = vendor_match.group(1).strip()
    
    # Déterminer le type de document
    if re.search(r'\b(?:FACTURE|INVOICE)\b', full_text, re.IGNORECASE):
        result["document_type"] = "invoice"
    elif re.search(r'\b(?:REÇU|TICKET|RECEIPT)\b', full_text, re.IGNORECASE):
        result["document_type"] = "receipt"
    else:
        result["document_type"] = "unknown"
    
    return result

def clean_amount(amount_str):
    """
    Nettoie et convertit une chaîne de montant en décimal
    
    Args:
        amount_str (str): Chaîne contenant un montant
        
    Returns:
        str: Montant nettoyé au format décimal
    """
    # Supprimer les symboles de devise et caractères non numériques (sauf point et virgule)
    clean = re.sub(r'[^\d,.]', '', amount_str)
    
    # Remplacer les virgules par des points pour la conversion
    clean = clean.replace(',', '.')
    
    # S'il y a plusieurs points, garder uniquement le dernier
    if clean.count('.') > 1:
        parts = clean.rsplit('.', 1)
        clean = parts[0].replace('.', '') + '.' + parts[1]
    
    try:
        # Convertir en décimal et formater avec 2 décimales
        return str(round(Decimal(clean), 2))
    except:
        return "0.00"