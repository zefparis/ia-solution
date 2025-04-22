"""
Blueprint pour les fonctionnalités d'analyse business avec DynamoDB
"""

import os
import uuid
import logging
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, jsonify
import openai

from dynamo_auth import login_required
from dynamo_models import BusinessReport, User
from dynamo_s3_service import default_s3_service as s3_service
from language import get_text

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration OpenAI
openai.api_key = os.environ.get('OPENAI_API_KEY')

# Création du blueprint
business_blueprint = Blueprint('business', __name__)

@business_blueprint.route('/')
def business_home():
    """Page d'accueil de la section business"""
    return render_template('business/index.html', _=get_text)

@business_blueprint.route('/consultation', methods=['GET', 'POST'])
def business_consultation():
    """Page de formulaire pour la consultation business personnalisée"""
    if request.method == 'POST':
        # Récupérer les données du formulaire
        company_name = request.form.get('company_name')
        company_sector = request.form.get('company_sector')
        company_size = request.form.get('company_size')
        company_description = request.form.get('company_description')
        
        if not company_name or not company_description:
            flash(get_text('business.error_missing_fields'), 'danger')
            return render_template('business/consultation.html', _=get_text)
        
        # Créer l'entrée dans DynamoDB
        try:
            report_id = str(uuid.uuid4())
            
            # Déterminer l'ID utilisateur (si connecté)
            user_id = None
            if g.user:
                user_id = g.user.id
            elif 'user_id' in session:
                user_id = session['user_id']
            
            # Créer le rapport
            report = BusinessReport(
                id=report_id,
                user_id=user_id,
                company_name=company_name,
                company_sector=company_sector,
                company_size=company_size,
                status='processing'
            )
            report.save()
            
            # Stocker les données complètes dans la session pour le traitement
            session['company_data'] = {
                'report_id': report_id,
                'company_name': company_name,
                'company_sector': company_sector,
                'company_size': company_size,
                'company_description': company_description
            }
            
            # Rediriger vers la page de traitement
            return redirect(url_for('business.business_transition', report_id=report_id))
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du rapport: {str(e)}")
            flash(get_text('business.error_processing'), 'danger')
            return render_template('business/consultation.html', _=get_text)
    
    # Afficher le formulaire en GET
    return render_template('business/consultation.html', _=get_text)

@business_blueprint.route('/transition/<report_id>')
def business_transition(report_id):
    """Page de transition montrant l'analyse en cours"""
    try:
        # Vérifier si le rapport existe
        report = None
        for r in BusinessReport.scan(BusinessReport.id == report_id):
            report = r
            break
        
        if not report:
            flash(get_text('business.error_report_not_found'), 'danger')
            return redirect(url_for('business.business_consultation'))
        
        # Si les données ne sont pas dans la session, redirect vers le rapport s'il existe
        if 'company_data' not in session and report.report_html:
            return redirect(url_for('business.business_report', report_id=report_id))
        
        return render_template('business/transition.html', report_id=report_id, _=get_text)
        
    except Exception as e:
        logger.error(f"Erreur lors de l'accès au rapport: {str(e)}")
        flash(get_text('business.error_processing'), 'danger')
        return redirect(url_for('business.business_consultation'))

@business_blueprint.route('/generate/<report_id>')
def generate_report(report_id):
    """
    Point d'API pour générer le rapport d'analyse depuis la page de transition
    via une requête AJAX
    """
    try:
        # Récupérer les données de la session
        company_data = session.get('company_data')
        if not company_data or company_data.get('report_id') != report_id:
            return jsonify({
                'success': False,
                'message': get_text('business.error_data_not_found')
            })
        
        # Vérifier si le rapport existe
        report = None
        for r in BusinessReport.scan(BusinessReport.id == report_id):
            report = r
            break
        
        if not report:
            return jsonify({
                'success': False,
                'message': get_text('business.error_report_not_found')
            })
        
        # Générer l'analyse
        analysis_result = generate_business_analysis(company_data)
        
        if not analysis_result.get('success'):
            return jsonify({
                'success': False,
                'message': analysis_result.get('message')
            })
        
        # Mettre à jour le rapport dans DynamoDB
        report.report_html = analysis_result['html']
        report.status = 'completed'
        report.save()
        
        # Nettoyer les données de la session
        session.pop('company_data', None)
        
        return jsonify({
            'success': True,
            'report_id': report_id
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@business_blueprint.route('/report/<report_id>')
def business_report(report_id):
    """Afficher le rapport d'analyse business"""
    try:
        # Vérifier si le rapport existe
        report = None
        for r in BusinessReport.scan(BusinessReport.id == report_id):
            report = r
            break
        
        if not report:
            flash(get_text('business.error_report_not_found'), 'danger')
            return redirect(url_for('business.business_consultation'))
        
        # Si le rapport est encore en traitement
        if report.status == 'processing' and 'company_data' in session:
            return redirect(url_for('business.business_transition', report_id=report_id))
        
        # Si le rapport n'a pas de contenu HTML
        if not report.report_html:
            flash(get_text('business.error_report_empty'), 'danger')
            return redirect(url_for('business.business_consultation'))
        
        # Vérifier si l'utilisateur peut accéder au rapport
        if report.user_id and g.user and report.user_id != g.user.id:
            # Si le rapport appartient à un autre utilisateur et n'est pas partagé
            if not report.is_shared:
                flash(get_text('business.error_access_denied'), 'danger')
                return redirect(url_for('business.business_consultation'))
        
        return render_template(
            'business/report.html',
            report=report,
            _=get_text
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'accès au rapport: {str(e)}")
        flash(get_text('business.error_processing'), 'danger')
        return redirect(url_for('business.business_consultation'))

@business_blueprint.route('/reports')
@login_required
def my_reports():
    """Liste des rapports de l'utilisateur"""
    try:
        # Récupérer les rapports de l'utilisateur
        reports = list(BusinessReport.scan(BusinessReport.user_id == g.user.id))
        
        return render_template(
            'business/my_reports.html',
            reports=reports,
            _=get_text
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'accès aux rapports: {str(e)}")
        flash(get_text('business.error_loading_reports'), 'danger')
        return redirect(url_for('business.business_home'))

@business_blueprint.route('/share/<report_id>')
@login_required
def share_report(report_id):
    """Génère un lien de partage pour un rapport"""
    try:
        # Vérifier si le rapport existe et appartient à l'utilisateur
        report = None
        for r in BusinessReport.scan(
            BusinessReport.id == report_id,
            BusinessReport.user_id == g.user.id
        ):
            report = r
            break
        
        if not report:
            flash(get_text('business.error_report_not_found'), 'danger')
            return redirect(url_for('business.my_reports'))
        
        # Générer un token de partage s'il n'existe pas
        if not report.share_token:
            report.share_token = str(uuid.uuid4())
        
        # Activer le partage
        report.is_shared = True
        report.save()
        
        # Générer l'URL de partage
        share_url = url_for('business.view_shared_report', share_token=report.share_token, _external=True)
        
        return render_template(
            'business/share.html',
            report=report,
            share_url=share_url,
            _=get_text
        )
        
    except Exception as e:
        logger.error(f"Erreur lors du partage du rapport: {str(e)}")
        flash(get_text('business.error_sharing'), 'danger')
        return redirect(url_for('business.my_reports'))

@business_blueprint.route('/shared/<share_token>')
def view_shared_report(share_token):
    """Affiche un rapport partagé via un token"""
    try:
        # Vérifier si le rapport existe avec ce token de partage
        report = None
        for r in BusinessReport.scan(
            BusinessReport.share_token == share_token,
            BusinessReport.is_shared == True
        ):
            report = r
            break
        
        if not report:
            flash(get_text('business.error_shared_not_found'), 'danger')
            return redirect(url_for('business.business_home'))
        
        return render_template(
            'business/report.html',
            report=report,
            is_shared=True,
            _=get_text
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'accès au rapport partagé: {str(e)}")
        flash(get_text('business.error_processing'), 'danger')
        return redirect(url_for('business.business_home'))

def generate_business_analysis(company_data):
    """
    Génère une analyse SWOT et des recommandations en utilisant OpenAI
    
    Args:
        company_data (dict): Données de l'entreprise
    
    Returns:
        dict: Résultat de l'analyse avec HTML formaté
    """
    try:
        company_name = company_data.get('company_name', '')
        company_sector = company_data.get('company_sector', '')
        company_size = company_data.get('company_size', '')
        company_description = company_data.get('company_description', '')
        
        # Préparer le prompt pour OpenAI
        prompt = f"""
        Analyse SWOT et recommandations stratégiques pour l'entreprise suivante:
        
        Nom: {company_name}
        Secteur: {company_sector}
        Taille: {company_size}
        Description: {company_description}
        
        Format souhaité:
        1. Introduction brève sur l'entreprise
        2. Analyse SWOT détaillée (Forces, Faiblesses, Opportunités, Menaces)
        3. Recommandations stratégiques à court et moyen terme
        4. Conclusion
        
        Utilise un langage professionnel mais accessible, et fournis une analyse approfondie et pertinente.
        Les recommandations doivent être adaptées à la taille de l'entreprise et à son secteur.
        """
        
        # Appeler l'API OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Tu es un consultant business spécialisé dans l'analyse stratégique d'entreprise. Tu fournis des analyses SWOT détaillées et des recommandations stratégiques basées sur les informations fournies."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Récupérer la réponse
        analysis_text = response.choices[0].message.content.strip()
        
        # Formater le texte en HTML
        html_content = format_analysis_to_html(analysis_text, company_name)
        
        return {
            'success': True,
            'text': analysis_text,
            'html': html_content
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération de l'analyse: {str(e)}")
        return {
            'success': False,
            'message': str(e)
        }

def format_analysis_to_html(analysis_text, company_name):
    """Convertit le texte brut de l'analyse en HTML formaté"""
    # Version simple: convertir les sauts de ligne en balises <p> et ajouter une structure HTML de base
    paragraphs = analysis_text.split('\n\n')
    formatted_paragraphs = []
    
    for paragraph in paragraphs:
        if paragraph.strip():
            # Détecter les titres
            if paragraph.strip().startswith('# '):
                title = paragraph.strip()[2:]
                formatted_paragraphs.append(f'<h2>{title}</h2>')
            elif paragraph.strip().startswith('## '):
                title = paragraph.strip()[3:]
                formatted_paragraphs.append(f'<h3>{title}</h3>')
            # Détecter les listes
            elif paragraph.strip().startswith('- ') or paragraph.strip().startswith('* '):
                items = paragraph.strip().split('\n')
                list_items = ''.join([f'<li>{item[2:]}</li>' for item in items])
                formatted_paragraphs.append(f'<ul>{list_items}</ul>')
            # Détecter les sections SWOT
            elif 'Forces:' in paragraph or 'FORCES:' in paragraph or 'Forces :' in paragraph:
                formatted_paragraphs.append('<div class="swot-section strengths"><h3>Forces</h3>')
                content = paragraph.split(':', 1)[1].strip()
                formatted_paragraphs.append(f'<p>{content}</p></div>')
            elif 'Faiblesses:' in paragraph or 'FAIBLESSES:' in paragraph or 'Faiblesses :' in paragraph:
                formatted_paragraphs.append('<div class="swot-section weaknesses"><h3>Faiblesses</h3>')
                content = paragraph.split(':', 1)[1].strip()
                formatted_paragraphs.append(f'<p>{content}</p></div>')
            elif 'Opportunités:' in paragraph or 'OPPORTUNITÉS:' in paragraph or 'Opportunités :' in paragraph:
                formatted_paragraphs.append('<div class="swot-section opportunities"><h3>Opportunités</h3>')
                content = paragraph.split(':', 1)[1].strip()
                formatted_paragraphs.append(f'<p>{content}</p></div>')
            elif 'Menaces:' in paragraph or 'MENACES:' in paragraph or 'Menaces :' in paragraph:
                formatted_paragraphs.append('<div class="swot-section threats"><h3>Menaces</h3>')
                content = paragraph.split(':', 1)[1].strip()
                formatted_paragraphs.append(f'<p>{content}</p></div>')
            # Détecter les recommandations
            elif 'Recommandations:' in paragraph or 'RECOMMANDATIONS:' in paragraph or 'Recommandations :' in paragraph:
                formatted_paragraphs.append('<div class="recommendations-section"><h3>Recommandations</h3>')
                content = paragraph.split(':', 1)[1].strip()
                formatted_paragraphs.append(f'<p>{content}</p></div>')
            # Paragraphes normaux
            else:
                formatted_paragraphs.append(f'<p>{paragraph}</p>')
    
    # Assembler le HTML complet
    html_content = f"""
    <div class="business-report">
        <header class="report-header">
            <h1>Analyse Stratégique: {company_name}</h1>
            <p class="report-date">Généré le {datetime.now().strftime('%d/%m/%Y')}</p>
        </header>
        
        <div class="report-content">
            {''.join(formatted_paragraphs)}
        </div>
        
        <footer class="report-footer">
            <p>Ce rapport a été généré automatiquement par IA-Solution.</p>
            <p>© {datetime.now().year} IA-Solution - Tous droits réservés</p>
        </footer>
    </div>
    """
    
    return html_content

def init_app(app):
    """Enregistre le blueprint business dans l'application Flask"""
    app.register_blueprint(business_blueprint, url_prefix='/business')