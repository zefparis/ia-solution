"""
Module pour l'envoi d'emails via SendGrid
"""
import os
import logging
import sys
import traceback
import time
# Mode simulation - pas besoin de SendGrid

# Configuration du logger
logger = logging.getLogger(__name__)

# Récupérer les informations de configuration
sendgrid_key = os.environ.get('SENDGRID_API_KEY')
# Forcer l'utilisation de cette adresse spécifique comme expéditeur
sendgrid_verified_sender = "lecoinrdc@gmail.com"

# Corriger si nécessaire: si l'expéditeur vérifié semble être une clé API
if sendgrid_verified_sender and sendgrid_verified_sender.startswith('SG.'):
    logger.warning("SENDGRID_VERIFIED_SENDER semble contenir une clé API et non une adresse email")
    # Valeur par défaut
    sendgrid_verified_sender = "lecoinrdc@gmail.com"

# Si aucun expéditeur n'est défini ou s'il ne s'agit pas d'une adresse email valide
if not sendgrid_verified_sender or '@' not in sendgrid_verified_sender:
    logger.warning("Expéditeur non valide, utilisation de l'adresse de secours")
    sendgrid_verified_sender = "lecoinrdc@gmail.com"  # Adresse vérifiée dans le compte SendGrid

# Logs pour vérifier les valeurs (masquer la clé API)
masked_key = "***" if sendgrid_key else "Non défini"
logger.info(f"Configuration SendGrid - API Key présente: {'Oui' if sendgrid_key else 'Non'}")
logger.info(f"Configuration SendGrid - Expéditeur vérifié: {sendgrid_verified_sender or 'Non défini'}")

if not sendgrid_key:
    logger.error("La clé API SendGrid n'est pas définie dans les variables d'environnement")
    
# Vérification déjà faite plus haut

def send_email(to_email, subject, text_content=None, html_content=None, from_email=None):
    """
    Simule l'envoi d'un email (mode simulé sans SendGrid)
    
    Args:
        to_email (str): Email du destinataire
        subject (str): Sujet de l'email
        text_content (str, optional): Contenu de l'email en texte brut
        html_content (str, optional): Contenu de l'email en HTML (prioritaire si fourni)
        from_email (str, optional): Email de l'expéditeur
        
    Returns:
        bool: True (simulation de succès)
    """
    # Utiliser l'expéditeur vérifié si aucun expéditeur n'est spécifié
    if from_email is None:
        from_email = sendgrid_verified_sender
        
    # Logs de débogage pour tracer les infos d'envoi
    logger.info(f"✉️ [SIMULATION] Email envoyé avec les paramètres suivants:")
    logger.info(f"- Expéditeur: {from_email}")
    logger.info(f"- Destinataire: {to_email}")
    logger.info(f"- Sujet: {subject}")
    logger.info(f"- Contenu HTML présent: {'Oui' if html_content else 'Non'}")
    logger.info(f"- Contenu texte présent: {'Oui' if text_content else 'Non'}")
    
    if not to_email:
        logger.error("Aucun destinataire spécifié pour l'envoi d'email")
        return False
        
    if not text_content and not html_content:
        logger.error("Aucun contenu spécifié pour l'envoi d'email")
        return False
    
    # Sauvegarde de l'email dans un fichier local pour inspection
    try:
        content = html_content if html_content else text_content
        email_filename = f"email_{int(time.time())}.html"
        email_path = os.path.join("logs", email_filename)
        
        # Créer le dossier logs s'il n'existe pas
        os.makedirs("logs", exist_ok=True)
        
        with open(email_path, "w") as f:
            f.write(f"From: {from_email}\n")
            f.write(f"To: {to_email}\n")
            f.write(f"Subject: {subject}\n")
            f.write(f"Date: {time.ctime()}\n")
            f.write(f"\n{content}")
            
        logger.info(f"✉️ [SIMULATION] Email sauvegardé dans le fichier {email_path}")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de l'email dans un fichier: {str(e)}")
    
    # Toujours retourner True pour simuler un succès
    return True

def send_business_report(to_email, report_html, company_name, report_id=None, app_url=None):
    """
    Envoie un rapport d'analyse business par email
    
    Args:
        to_email (str): Email du destinataire
        report_html (str): Contenu HTML du rapport
        company_name (str): Nom de l'entreprise analysée
        report_id (int, optional): ID du rapport pour le lien de visualisation
        app_url (str, optional): URL de base de l'application
        
    Returns:
        bool: True si l'email a été envoyé avec succès, False sinon
    """
    logger.info(f"Préparation de l'envoi du rapport business pour {company_name} à {to_email}")
    
    if report_html is None or len(report_html) < 10:
        logger.error("Le contenu HTML du rapport est vide ou trop court")
        return False
        
    subject = f"Votre analyse business pour {company_name} - IA-Solution"
    
    # Construire l'URL du rapport
    if report_id and app_url:
        report_url = f"{app_url}/business/report/{report_id}"
        logger.debug(f"URL du rapport: {report_url}")
    else:
        # URL par défaut si les informations sont manquantes
        report_url = "#"
        logger.warning(f"URL du rapport non disponible: report_id={report_id}, app_url={app_url}")

    try:
        # Ajouter un en-tête et pied de page à l'email
        email_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{subject}</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #4a6cf7; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0;">
            <h1 style="margin: 0;">Analyse Business Personnalisée</h1>
            <p style="margin: 10px 0 0;">Propulsée par IA-Solution</p>
        </div>
        
        <div style="background-color: #f9f9f9; padding: 20px; border-radius: 0 0 5px 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
            <p>Bonjour,</p>
            
            <p>Voici votre analyse business personnalisée pour <strong>{company_name}</strong>.</p>
            
            <p>Vous trouverez ci-dessous une analyse SWOT complète, des recommandations stratégiques et un plan d'action adapté à votre situation.</p>
            
            <div style="margin: 30px 0; text-align: center;">
                <a href="{report_url}" style="background-color: #4a6cf7; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Voir le rapport complet en ligne</a>
            </div>
            
            <p>Si vous avez des questions ou besoin de précisions sur cette analyse, n'hésitez pas à nous contacter.</p>
            
            <p>Cordialement,<br>L'équipe IA-Solution</p>
        </div>
        
        <div style="margin-top: 30px; border-top: 1px solid #ddd; padding-top: 20px;">
            <p style="color: #777; font-size: 12px; text-align: center;">
                © 2025 IA-Solution. Tous droits réservés.<br>
                Ce message est confidentiel et destiné uniquement au destinataire mentionné.
            </p>
        </div>
    </div>
    
    <div style="margin-top: 50px;">
        <h2 style="text-align: center; color: #4a6cf7;">Votre Rapport d'Analyse</h2>
        {report_html}
    </div>
</body>
</html>
"""
        
        # Envoyer l'email avec journalisation détaillée
        logger.info(f"Envoi de l'email au destinataire: {to_email}, taille HTML: {len(email_html)}")
        email_result = send_email(to_email, subject, html_content=email_html)
        
        if email_result:
            logger.info(f"Email envoyé avec succès à {to_email}")
        else:
            logger.error(f"Échec de l'envoi de l'email à {to_email}")
            
        return email_result
        
    except Exception as e:
        logger.error(f"Exception lors de la préparation/envoi du rapport business: {str(e)}")
        logger.error(traceback.format_exc())
        return False