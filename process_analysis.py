"""
Module pour l'analyse des processus d'entreprise.

Ce module fournit une interface web pour interagir avec le service d'analyse
des processus d'entreprise.
"""

import os
import json
import logging
import requests
from datetime import datetime
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, abort, g
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

import language
from language import url_with_lang

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Création du blueprint
process_analysis_bp = Blueprint('process_analysis', __name__, url_prefix='/process-analysis')

# Constantes
API_ENDPOINT = '/api/process-analysis'


@process_analysis_bp.before_request
def before_request():
    """Exécuté avant chaque requête au blueprint."""
    # Vérifier si l'utilisateur est authentifié
    if 'access_token' not in session and request.endpoint != 'process_analysis.login_redirect':
        # Rediriger vers la page de connexion AWS Cognito
        return redirect(url_for('login'))


# Routes principales

# Fonctions utilitaires
def get_translations():
    """Obtenir les traductions pour le module."""
    return {
        # Titres et entêtes
        'title': {
            'fr': 'Analyse des Processus',
            'en': 'Process Analysis'
        },
        'process_list': {
            'fr': 'Liste des Processus',
            'en': 'Process List'
        },
        'new_process': {
            'fr': 'Créer un Nouveau Processus d\'Entreprise',
            'en': 'Create a New Business Process'
        },
        # Nouveau formulaire - sections
        'general_information': {
            'fr': 'Informations Générales',
            'en': 'General Information'
        },
        'process_name': {
            'fr': 'Nom du Processus',
            'en': 'Process Name'
        },
        'department': {
            'fr': 'Département',
            'en': 'Department'
        },
        'process_description': {
            'fr': 'Description du Processus',
            'en': 'Process Description'
        },
        'current_state': {
            'fr': 'État Actuel du Processus',
            'en': 'Current Process State'
        },
        'process_steps': {
            'fr': 'Étapes du Processus',
            'en': 'Process Steps'
        },
        'step_description': {
            'fr': 'Listez les étapes actuelles du processus et leur durée approximative.',
            'en': 'List the current steps of the process and their approximate duration.'
        },
        'bottlenecks': {
            'fr': 'Goulots d\'Étranglement',
            'en': 'Bottlenecks'
        },
        'bottlenecks_description': {
            'fr': 'Identifiez les points bloquants ou les étapes qui ralentissent le processus.',
            'en': 'Identify bottlenecks or steps that slow down the process.'
        },
        'pain_points': {
            'fr': 'Points de Douleur',
            'en': 'Pain Points'
        },
        'pain_points_description': {
            'fr': 'Identifiez les problèmes et frustrations liés à ce processus.',
            'en': 'Identify problems and frustrations related to this process.'
        },
        'kpis': {
            'fr': 'Indicateurs de Performance (KPIs)',
            'en': 'Key Performance Indicators (KPIs)'
        },
        'kpis_description': {
            'fr': 'Définissez des indicateurs mesurables pour évaluer l\'efficacité du processus.',
            'en': 'Define measurable indicators to evaluate process effectiveness.'
        },
        # Champs du formulaire
        'step_name': {
            'fr': 'Nom de l\'étape',
            'en': 'Step Name'
        },
        'step_duration': {
            'fr': 'Durée (jours)',
            'en': 'Duration (days)'
        },
        'add_step': {
            'fr': 'Ajouter une étape',
            'en': 'Add a Step'
        },
        'add_bottleneck': {
            'fr': 'Ajouter un goulot d\'étranglement',
            'en': 'Add a Bottleneck'
        },
        'pain_point': {
            'fr': 'Point de douleur',
            'en': 'Pain Point'
        },
        'impact': {
            'fr': 'Impact',
            'en': 'Impact'
        },
        'add_pain_point': {
            'fr': 'Ajouter un point de douleur',
            'en': 'Add a Pain Point'
        },
        'kpi_name': {
            'fr': 'Nom du KPI',
            'en': 'KPI Name'
        },
        'current_value': {
            'fr': 'Valeur actuelle',
            'en': 'Current Value'
        },
        'unit': {
            'fr': 'Unité',
            'en': 'Unit'
        },
        'target_value': {
            'fr': 'Valeur cible',
            'en': 'Target Value'
        },
        'add_kpi': {
            'fr': 'Ajouter un KPI',
            'en': 'Add a KPI'
        },
        'cancel': {
            'fr': 'Annuler',
            'en': 'Cancel'
        },
        'save_process': {
            'fr': 'Enregistrer le Processus',
            'en': 'Save Process'
        },
        'view_process': {
            'fr': 'Détails du Processus',
            'en': 'Process Details'
        },
        'edit_process': {
            'fr': 'Modifier le Processus',
            'en': 'Edit Process'
        },
        'view_optimization': {
            'fr': 'Détails de l\'Optimisation',
            'en': 'Optimization Details'
        },
        
        # Messages
        'process_created': {
            'fr': 'Processus créé avec succès',
            'en': 'Process created successfully'
        },
        'process_updated': {
            'fr': 'Processus mis à jour avec succès',
            'en': 'Process updated successfully'
        },
        'process_deleted': {
            'fr': 'Processus supprimé avec succès',
            'en': 'Process deleted successfully'
        },
        'optimization_created': {
            'fr': 'Optimisation créée avec succès',
            'en': 'Optimization created successfully'
        },
        'optimization_updated': {
            'fr': 'Optimisation mise à jour avec succès',
            'en': 'Optimization updated successfully'
        },
        'milestone_created': {
            'fr': 'Jalon créé avec succès',
            'en': 'Milestone created successfully'
        },
        'milestone_updated': {
            'fr': 'Jalon mis à jour avec succès',
            'en': 'Milestone updated successfully'
        },
        'result_created': {
            'fr': 'Mesure de résultat créée avec succès',
            'en': 'Result measurement created successfully'
        },
        
        # Erreurs
        'api_error': {
            'fr': 'Erreur lors de la communication avec l\'API',
            'en': 'Error communicating with the API'
        },
        'api_connection_error': {
            'fr': 'Erreur de connexion à l\'API',
            'en': 'API connection error'
        },
        'process_not_found': {
            'fr': 'Processus non trouvé',
            'en': 'Process not found'
        },
        'optimization_not_found': {
            'fr': 'Optimisation non trouvée',
            'en': 'Optimization not found'
        },
        'milestone_not_found': {
            'fr': 'Jalon non trouvé',
            'en': 'Milestone not found'
        },
        'feature_not_implemented': {
            'fr': 'Cette fonctionnalité n\'est pas encore implémentée',
            'en': 'This feature is not yet implemented'
        },
        
        # Page d'accueil d'analyse des processus
        'process_analysis_title': {
            'fr': 'Analyse et Optimisation des Processus d\'Entreprise',
            'en': 'Business Process Analysis and Optimization'
        },
        'our_approach': {
            'fr': 'Notre Approche',
            'en': 'Our Approach'
        },
        'approach_description': {
            'fr': 'Notre service d\'analyse et d\'optimisation des processus d\'entreprise vous aide à identifier les inefficacités et à mettre en œuvre des solutions sur mesure pour améliorer la performance de votre organisation.',
            'en': 'Our business process analysis and optimization service helps you identify inefficiencies and implement tailored solutions to improve your organization\'s performance.'
        },
        'methodology_title': {
            'fr': 'Notre Méthodologie en 5 Étapes',
            'en': 'Our 5-Step Methodology'
        },
        'step1_title': {
            'fr': '1. Analyse des Processus Existants',
            'en': '1. Analysis of Existing Processes'
        },
        'step1_desc': {
            'fr': 'Nous examinons en détail vos processus actuels pour comprendre leur fonctionnement et identifier les zones d\'amélioration potentielles.',
            'en': 'We examine your current processes in detail to understand how they work and identify potential areas for improvement.'
        },
        'step2_title': {
            'fr': '2. Identification des Points d\'Optimisation',
            'en': '2. Identification of Optimization Points'
        },
        'step2_desc': {
            'fr': 'Nous repérons les goulots d\'étranglement, les redondances et les étapes à faible valeur ajoutée dans vos flux de travail.',
            'en': 'We identify bottlenecks, redundancies, and low-value steps in your workflows.'
        },
        'step3_title': {
            'fr': '3. Solutions Sur Mesure',
            'en': '3. Tailored Solutions'
        },
        'step3_desc': {
            'fr': 'Nous développons des solutions personnalisées pour répondre à vos défis spécifiques et améliorer l\'efficacité de vos processus.',
            'en': 'We develop customized solutions to address your specific challenges and improve the efficiency of your processes.'
        },
        'step4_title': {
            'fr': '4. Accompagnement au Changement',
            'en': '4. Change Management Support'
        },
        'step4_desc': {
            'fr': 'Nous vous guidons à travers chaque étape de la mise en œuvre, en assurant une transition en douceur vers les nouveaux processus optimisés.',
            'en': 'We guide you through each implementation step, ensuring a smooth transition to the new optimized processes.'
        },
        'step5_title': {
            'fr': '5. Mesure et Garantie des Résultats',
            'en': '5. Measurement and Results Guarantee'
        },
        'step5_desc': {
            'fr': 'Nous suivons rigoureusement l\'impact des changements et garantissons des résultats mesurables en termes d\'efficacité, de coûts et de qualité.',
            'en': 'We rigorously track the impact of changes and guarantee measurable results in terms of efficiency, costs, and quality.'
        },
        'benefits': {
            'fr': 'Bénéfices',
            'en': 'Benefits'
        },
        'benefit1': {
            'fr': 'Réduction des délais de traitement jusqu\'à 40%',
            'en': 'Processing time reduction of up to 40%'
        },
        'benefit2': {
            'fr': 'Diminution des coûts opérationnels de 15 à 30%',
            'en': 'Operational cost reduction of 15-30%'
        },
        'benefit3': {
            'fr': 'Amélioration de la qualité et réduction des erreurs',
            'en': 'Quality improvement and error reduction'
        },
        'benefit4': {
            'fr': 'Augmentation de la satisfaction client',
            'en': 'Increased customer satisfaction'
        },
        'benefit5': {
            'fr': 'Meilleure utilisation des ressources',
            'en': 'Better resource utilization'
        },
        'benefit6': {
            'fr': 'Gain de temps pour se concentrer sur les activités à valeur ajoutée',
            'en': 'Time saved to focus on value-added activities'
        },
        'our_services': {
            'fr': 'Nos Services',
            'en': 'Our Services'
        },
        'service1': {
            'fr': 'Cartographie des processus existants',
            'en': 'Mapping of existing processes'
        },
        'service2': {
            'fr': 'Audit et analyse des performances',
            'en': 'Performance audit and analysis'
        },
        'service3': {
            'fr': 'Réingénierie des processus métier',
            'en': 'Business process reengineering'
        },
        'service4': {
            'fr': 'Automatisation des tâches répétitives',
            'en': 'Automation of repetitive tasks'
        },
        'service5': {
            'fr': 'Mise en place d\'indicateurs de performance (KPIs)',
            'en': 'Implementation of Key Performance Indicators (KPIs)'
        },
        'service6': {
            'fr': 'Formation et accompagnement des équipes',
            'en': 'Team training and support'
        },
        'service7': {
            'fr': 'Suivi et amélioration continue',
            'en': 'Monitoring and continuous improvement'
        },
        'view_my_processes': {
            'fr': 'Voir Mes Processus',
            'en': 'View My Processes'
        },
        'create_new_process': {
            'fr': 'Créer un Nouveau Processus',
            'en': 'Create a New Process'
        },
    }

def get_current_language():
    """Obtenir la langue actuelle."""
    return getattr(g, 'lang', 'fr')

# Fonction d'initialisation du module
def init_app(app):
    """Initialiser le module d'analyse des processus."""
    app.register_blueprint(process_analysis_bp)
    logger.info("Module d'analyse des processus initialisé")

@process_analysis_bp.route('/')
def index():
    """Page d'accueil du module d'analyse des processus."""
    translations = get_translations()
    lang = get_current_language()
    
    # Utiliser le sub (identifiant unique) de l'utilisateur depuis Cognito
    user_info = session.get('user_info', {})
    user_id = user_info.get('sub', session.get('username', ''))
    
    # Au lieu de créer un objet language personnalisé, utilisons le module language importé
    # qui a déjà la méthode get_text attendue par layout.html
    
    return render_template(
        'process_analysis/index.html',
        translations=translations,
        lang=lang,
        url_with_lang=url_with_lang,
        user_id=user_id
    )


@process_analysis_bp.route('/processes')
def processes():
    """Liste des processus d'entreprise."""
    translations = get_translations()
    lang = get_current_language()
    
    # Récupérer les processus via l'API
    user_info = session.get('user_info', {})
    user_id = user_info.get('sub', session.get('username', ''))
    company_id = session.get('company_id', 1)  # Par défaut, utiliser company_id=1
    
    try:
        response = requests.get(
            f'{request.host_url.rstrip("/")}{API_ENDPOINT}/processes',
            params={'user_id': user_id, 'company_id': company_id}
        )
        
        if response.status_code == 200:
            processes_data = response.json()
        else:
            logger.error(f"Error retrieving processes: {response.status_code} - {response.text}")
            processes_data = {'items': [], 'total': 0}
            flash(translations.get('api_error', 'Error retrieving processes'), 'danger')
    
    except Exception as e:
        logger.error(f"Error connecting to API: {e}")
        processes_data = {'items': [], 'total': 0}
        flash(translations.get('api_connection_error', 'Error connecting to the API'), 'danger')
    
    return render_template(
        'process_analysis/processes.html',
        translations=translations,
        processes=processes_data.get('items', []),
        total=processes_data.get('total', 0)
    )


@process_analysis_bp.route('/processes/new', methods=['GET', 'POST'])
def new_process():
    """Création d'un nouveau processus."""
    translations = get_translations()
    lang = get_current_language()
    
    if request.method == 'POST':
        user_info = session.get('user_info', {})
        user_id = user_info.get('sub', session.get('username', ''))
        company_id = session.get('company_id', 1)  # Par défaut, utiliser company_id=1
        
        # Récupérer les données du formulaire
        process_data = {
            'user_id': user_id,
            'company_id': company_id,
            'name': request.form.get('name'),
            'description': request.form.get('description'),
            'department': request.form.get('department')
        }
        
        # Récupérer les étapes du processus
        steps = []
        i = 0
        while request.form.get(f'step_name_{i}'):
            steps.append({
                'name': request.form.get(f'step_name_{i}'),
                'duration': int(request.form.get(f'step_duration_{i}', 0))
            })
            i += 1
        
        # Calculer la durée totale
        total_duration = sum(step['duration'] for step in steps)
        
        # Récupérer les goulots d'étranglement
        bottlenecks = [request.form.get(f'bottleneck_{i}') for i in range(10) if request.form.get(f'bottleneck_{i}')]
        
        # Construire l'état actuel
        process_data['current_state'] = {
            'steps': steps,
            'total_duration': total_duration,
            'bottlenecks': bottlenecks
        }
        
        # Récupérer les points de douleur
        pain_points = []
        i = 0
        while request.form.get(f'pain_point_name_{i}'):
            pain_points.append({
                'name': request.form.get(f'pain_point_name_{i}'),
                'impact': request.form.get(f'pain_point_impact_{i}', 'medium')
            })
            i += 1
        
        process_data['pain_points'] = pain_points
        
        # Récupérer les KPIs
        kpis = []
        i = 0
        while request.form.get(f'kpi_name_{i}'):
            try:
                value = float(request.form.get(f'kpi_value_{i}', 0))
                target = float(request.form.get(f'kpi_target_{i}', 0))
            except ValueError:
                value = 0
                target = 0
            
            kpis.append({
                'name': request.form.get(f'kpi_name_{i}'),
                'value': value,
                'unit': request.form.get(f'kpi_unit_{i}', ''),
                'target': target
            })
            i += 1
        
        process_data['kpis'] = kpis
        
        # Envoyer les données à l'API
        try:
            response = requests.post(
                f'{request.host_url.rstrip("/")}{API_ENDPOINT}/processes',
                json=process_data
            )
            
            if response.status_code == 201:
                result = response.json()
                flash(translations.get('process_created', 'Process created successfully'), 'success')
                
                # Si l'analyse a été démarrée automatiquement
                if result.get('analysis_started'):
                    flash(translations.get('analysis_started', 'Process analysis started automatically'), 'info')
                
                # Rediriger vers la liste des processus
                return redirect(url_for('process_analysis.processes'))
            else:
                logger.error(f"Error creating process: {response.status_code} - {response.text}")
                flash(translations.get('api_error', 'Error creating process'), 'danger')
        
        except Exception as e:
            logger.error(f"Error connecting to API: {e}")
            flash(translations.get('api_connection_error', 'Error connecting to the API'), 'danger')
    
    return render_template(
        'process_analysis/new_process.html',
        translations=translations
    )


@process_analysis_bp.route('/processes/<int:process_id>')
def view_process(process_id):
    """Affichage d'un processus spécifique."""
    translations = get_translations()
    lang = get_current_language()
    
    try:
        # Récupérer les détails du processus
        response = requests.get(
            f'{request.host_url.rstrip("/")}{API_ENDPOINT}/processes/{process_id}'
        )
        
        if response.status_code == 200:
            process = response.json()
            
            # Récupérer les optimisations
            opt_response = requests.get(
                f'{request.host_url.rstrip("/")}{API_ENDPOINT}/processes/{process_id}/optimizations'
            )
            
            if opt_response.status_code == 200:
                optimizations = opt_response.json().get('items', [])
            else:
                logger.error(f"Error retrieving optimizations: {opt_response.status_code} - {opt_response.text}")
                optimizations = []
                flash(translations.get('api_error', 'Error retrieving optimizations'), 'warning')
            
            return render_template(
                'process_analysis/view_process.html',
                translations=translations,
                process=process,
                optimizations=optimizations
            )
        else:
            logger.error(f"Error retrieving process: {response.status_code} - {response.text}")
            flash(translations.get('process_not_found', 'Process not found'), 'danger')
            return redirect(url_for('process_analysis.processes'))
    
    except Exception as e:
        logger.error(f"Error connecting to API: {e}")
        flash(translations.get('api_connection_error', 'Error connecting to the API'), 'danger')
        return redirect(url_for('process_analysis.processes'))


@process_analysis_bp.route('/processes/<int:process_id>/edit', methods=['GET', 'POST'])
def edit_process(process_id):
    """Édition d'un processus existant."""
    translations = get_translations()
    lang = get_current_language()
    
    # Récupérer les détails du processus
    try:
        response = requests.get(
            f'{request.host_url.rstrip("/")}{API_ENDPOINT}/processes/{process_id}'
        )
        
        if response.status_code != 200:
            logger.error(f"Error retrieving process: {response.status_code} - {response.text}")
            flash(translations.get('process_not_found', 'Process not found'), 'danger')
            return redirect(url_for('process_analysis.processes'))
        
        process = response.json()
    
    except Exception as e:
        logger.error(f"Error connecting to API: {e}")
        flash(translations.get('api_connection_error', 'Error connecting to the API'), 'danger')
        return redirect(url_for('process_analysis.processes'))
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        process_data = {
            'name': request.form.get('name'),
            'description': request.form.get('description'),
            'department': request.form.get('department')
        }
        
        # Récupérer les étapes du processus
        steps = []
        i = 0
        while request.form.get(f'step_name_{i}'):
            steps.append({
                'name': request.form.get(f'step_name_{i}'),
                'duration': int(request.form.get(f'step_duration_{i}', 0))
            })
            i += 1
        
        # Calculer la durée totale
        total_duration = sum(step['duration'] for step in steps)
        
        # Récupérer les goulots d'étranglement
        bottlenecks = [request.form.get(f'bottleneck_{i}') for i in range(10) if request.form.get(f'bottleneck_{i}')]
        
        # Construire l'état actuel
        process_data['current_state'] = {
            'steps': steps,
            'total_duration': total_duration,
            'bottlenecks': bottlenecks
        }
        
        # Récupérer les points de douleur
        pain_points = []
        i = 0
        while request.form.get(f'pain_point_name_{i}'):
            pain_points.append({
                'name': request.form.get(f'pain_point_name_{i}'),
                'impact': request.form.get(f'pain_point_impact_{i}', 'medium')
            })
            i += 1
        
        process_data['pain_points'] = pain_points
        
        # Récupérer les KPIs
        kpis = []
        i = 0
        while request.form.get(f'kpi_name_{i}'):
            try:
                value = float(request.form.get(f'kpi_value_{i}', 0))
                target = float(request.form.get(f'kpi_target_{i}', 0))
            except ValueError:
                value = 0
                target = 0
            
            kpis.append({
                'name': request.form.get(f'kpi_name_{i}'),
                'value': value,
                'unit': request.form.get(f'kpi_unit_{i}', ''),
                'target': target
            })
            i += 1
        
        process_data['kpis'] = kpis
        
        # Envoyer les données à l'API
        try:
            response = requests.put(
                f'{request.host_url.rstrip("/")}{API_ENDPOINT}/processes/{process_id}',
                json=process_data
            )
            
            if response.status_code == 200:
                result = response.json()
                flash(translations.get('process_updated', 'Process updated successfully'), 'success')
                
                # Si l'analyse a été démarrée automatiquement
                if result.get('analysis_started'):
                    flash(translations.get('analysis_started', 'Process analysis restarted automatically'), 'info')
                
                # Rediriger vers la vue du processus
                return redirect(url_for('process_analysis.view_process', process_id=process_id))
            else:
                logger.error(f"Error updating process: {response.status_code} - {response.text}")
                flash(translations.get('api_error', 'Error updating process'), 'danger')
        
        except Exception as e:
            logger.error(f"Error connecting to API: {e}")
            flash(translations.get('api_connection_error', 'Error connecting to the API'), 'danger')
    
    return render_template(
        'process_analysis/edit_process.html',
        translations=translations,
        process=process
    )


@process_analysis_bp.route('/processes/<int:process_id>/analyze', methods=['POST'])
def analyze_process(process_id):
    """Déclencher l'analyse d'un processus."""
    translations = get_translations()
    
    try:
        response = requests.post(
            f'{request.host_url.rstrip("/")}{API_ENDPOINT}/processes/{process_id}/analyze'
        )
        
        if response.status_code == 200:
            flash(translations.get('analysis_started', 'Process analysis started successfully'), 'success')
        else:
            logger.error(f"Error starting analysis: {response.status_code} - {response.text}")
            
            # Vérifier s'il s'agit d'une erreur de données insuffisantes
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    if 'message' in error_data and 'Insufficient data' in error_data.get('message', ''):
                        flash(translations.get('insufficient_data', 
                                              'Insufficient data for analysis. Please add current state and pain points.'), 
                              'warning')
                    else:
                        flash(translations.get('api_error', 'Error starting analysis'), 'danger')
                except:
                    flash(translations.get('api_error', 'Error starting analysis'), 'danger')
            else:
                flash(translations.get('api_error', 'Error starting analysis'), 'danger')
    
    except Exception as e:
        logger.error(f"Error connecting to API: {e}")
        flash(translations.get('api_connection_error', 'Error connecting to the API'), 'danger')
    
    return redirect(url_for('process_analysis.view_process', process_id=process_id))


@process_analysis_bp.route('/processes/<int:process_id>/delete', methods=['POST'])
def delete_process(process_id):
    """Supprimer un processus."""
    translations = get_translations()
    
    try:
        response = requests.delete(
            f'{request.host_url.rstrip("/")}{API_ENDPOINT}/processes/{process_id}'
        )
        
        if response.status_code == 200:
            flash(translations.get('process_deleted', 'Process deleted successfully'), 'success')
        else:
            logger.error(f"Error deleting process: {response.status_code} - {response.text}")
            flash(translations.get('api_error', 'Error deleting process'), 'danger')
    
    except Exception as e:
        logger.error(f"Error connecting to API: {e}")
        flash(translations.get('api_connection_error', 'Error connecting to the API'), 'danger')
    
    return redirect(url_for('process_analysis.processes'))


# Routes pour la gestion des optimisations

@process_analysis_bp.route('/optimizations/<int:optimization_id>')
def view_optimization(optimization_id):
    """Affichage d'une optimisation spécifique."""
    translations = get_translations()
    lang = get_current_language()
    
    try:
        # Récupérer les détails de l'optimisation
        response = requests.get(
            f'{request.host_url.rstrip("/")}{API_ENDPOINT}/optimizations/{optimization_id}'
        )
        
        if response.status_code == 200:
            optimization = response.json()
            
            # Récupérer les jalons
            milestone_response = requests.get(
                f'{request.host_url.rstrip("/")}{API_ENDPOINT}/optimizations/{optimization_id}/milestones'
            )
            
            if milestone_response.status_code == 200:
                milestones = milestone_response.json().get('items', [])
            else:
                logger.error(f"Error retrieving milestones: {milestone_response.status_code} - {milestone_response.text}")
                milestones = []
                flash(translations.get('api_error', 'Error retrieving milestones'), 'warning')
            
            # Récupérer les mesures de résultat
            result_response = requests.get(
                f'{request.host_url.rstrip("/")}{API_ENDPOINT}/optimizations/{optimization_id}/results'
            )
            
            if result_response.status_code == 200:
                results = result_response.json().get('items', [])
            else:
                logger.error(f"Error retrieving results: {result_response.status_code} - {result_response.text}")
                results = []
                flash(translations.get('api_error', 'Error retrieving result measurements'), 'warning')
            
            return render_template(
                'process_analysis/view_optimization.html',
                translations=translations,
                optimization=optimization,
                milestones=milestones,
                results=results
            )
        else:
            logger.error(f"Error retrieving optimization: {response.status_code} - {response.text}")
            flash(translations.get('optimization_not_found', 'Optimization not found'), 'danger')
            return redirect(url_for('process_analysis.processes'))
    
    except Exception as e:
        logger.error(f"Error connecting to API: {e}")
        flash(translations.get('api_connection_error', 'Error connecting to the API'), 'danger')
        return redirect(url_for('process_analysis.processes'))


@process_analysis_bp.route('/processes/<int:process_id>/optimizations/new', methods=['GET', 'POST'])
def new_optimization(process_id):
    """Création d'une nouvelle optimisation pour un processus."""
    translations = get_translations()
    lang = get_current_language()
    
    # Récupérer les détails du processus
    try:
        response = requests.get(
            f'{request.host_url.rstrip("/")}{API_ENDPOINT}/processes/{process_id}'
        )
        
        if response.status_code != 200:
            logger.error(f"Error retrieving process: {response.status_code} - {response.text}")
            flash(translations.get('process_not_found', 'Process not found'), 'danger')
            return redirect(url_for('process_analysis.processes'))
        
        process = response.json()
    
    except Exception as e:
        logger.error(f"Error connecting to API: {e}")
        flash(translations.get('api_connection_error', 'Error connecting to the API'), 'danger')
        return redirect(url_for('process_analysis.processes'))
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        optimization_data = {
            'title': request.form.get('title'),
            'description': request.form.get('description'),
            'priority': request.form.get('priority', 'medium')
        }
        
        # Récupérer les bénéfices
        benefits = {}
        time_saved = request.form.get('time_saved')
        if time_saved:
            try:
                benefits['time_saved'] = float(time_saved)
            except ValueError:
                pass
        
        cost_reduction = request.form.get('cost_reduction')
        if cost_reduction:
            try:
                benefits['cost_reduction'] = float(cost_reduction)
            except ValueError:
                pass
        
        quality_improvement = request.form.get('quality_improvement')
        if quality_improvement:
            benefits['quality_improvement'] = quality_improvement
        
        optimization_data['benefits'] = benefits
        
        # Récupérer le plan de mise en œuvre
        phases = []
        i = 0
        while request.form.get(f'phase_name_{i}'):
            try:
                duration = int(request.form.get(f'phase_duration_{i}', 0))
            except ValueError:
                duration = 0
            
            phases.append({
                'name': request.form.get(f'phase_name_{i}'),
                'duration': duration
            })
            i += 1
        
        optimization_data['implementation_plan'] = {
            'phases': phases
        }
        
        # Récupérer les ressources requises
        resources = {}
        budget = request.form.get('budget')
        if budget:
            try:
                resources['budget'] = float(budget)
            except ValueError:
                pass
        
        personnel = request.form.get('personnel')
        if personnel:
            resources['personnel'] = [p.strip() for p in personnel.split(',')]
        
        tools = request.form.get('tools')
        if tools:
            resources['tools'] = [t.strip() for t in tools.split(',')]
        
        optimization_data['resources_required'] = resources
        
        # Récupérer le ROI estimé
        roi = request.form.get('estimated_roi')
        if roi:
            try:
                optimization_data['estimated_roi'] = float(roi)
            except ValueError:
                pass
        
        # Envoyer les données à l'API
        try:
            response = requests.post(
                f'{request.host_url.rstrip("/")}{API_ENDPOINT}/processes/{process_id}/optimizations',
                json=optimization_data
            )
            
            if response.status_code == 201:
                result = response.json()
                flash(translations.get('optimization_created', 'Optimization created successfully'), 'success')
                
                # Rediriger vers la vue du processus
                return redirect(url_for('process_analysis.view_process', process_id=process_id))
            else:
                logger.error(f"Error creating optimization: {response.status_code} - {response.text}")
                flash(translations.get('api_error', 'Error creating optimization'), 'danger')
        
        except Exception as e:
            logger.error(f"Error connecting to API: {e}")
            flash(translations.get('api_connection_error', 'Error connecting to the API'), 'danger')
    
    return render_template(
        'process_analysis/new_optimization.html',
        translations=translations,
        process=process
    )


@process_analysis_bp.route('/optimizations/<int:optimization_id>/edit', methods=['GET', 'POST'])
def edit_optimization(optimization_id):
    """Édition d'une optimisation existante."""
    translations = get_translations()
    lang = get_current_language()
    
    # Récupérer les détails de l'optimisation
    try:
        response = requests.get(
            f'{request.host_url.rstrip("/")}{API_ENDPOINT}/optimizations/{optimization_id}'
        )
        
        if response.status_code != 200:
            logger.error(f"Error retrieving optimization: {response.status_code} - {response.text}")
            flash(translations.get('optimization_not_found', 'Optimization not found'), 'danger')
            return redirect(url_for('process_analysis.processes'))
        
        optimization = response.json()
    
    except Exception as e:
        logger.error(f"Error connecting to API: {e}")
        flash(translations.get('api_connection_error', 'Error connecting to the API'), 'danger')
        return redirect(url_for('process_analysis.processes'))
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        optimization_data = {
            'title': request.form.get('title'),
            'description': request.form.get('description'),
            'priority': request.form.get('priority', 'medium'),
            'status': request.form.get('status', 'proposed')
        }
        
        # Récupérer les bénéfices
        benefits = {}
        time_saved = request.form.get('time_saved')
        if time_saved:
            try:
                benefits['time_saved'] = float(time_saved)
            except ValueError:
                pass
        
        cost_reduction = request.form.get('cost_reduction')
        if cost_reduction:
            try:
                benefits['cost_reduction'] = float(cost_reduction)
            except ValueError:
                pass
        
        quality_improvement = request.form.get('quality_improvement')
        if quality_improvement:
            benefits['quality_improvement'] = quality_improvement
        
        optimization_data['benefits'] = benefits
        
        # Récupérer le plan de mise en œuvre
        phases = []
        i = 0
        while request.form.get(f'phase_name_{i}'):
            try:
                duration = int(request.form.get(f'phase_duration_{i}', 0))
            except ValueError:
                duration = 0
            
            phases.append({
                'name': request.form.get(f'phase_name_{i}'),
                'duration': duration
            })
            i += 1
        
        optimization_data['implementation_plan'] = {
            'phases': phases
        }
        
        # Récupérer les ressources requises
        resources = {}
        budget = request.form.get('budget')
        if budget:
            try:
                resources['budget'] = float(budget)
            except ValueError:
                pass
        
        personnel = request.form.get('personnel')
        if personnel:
            resources['personnel'] = [p.strip() for p in personnel.split(',')]
        
        tools = request.form.get('tools')
        if tools:
            resources['tools'] = [t.strip() for t in tools.split(',')]
        
        optimization_data['resources_required'] = resources
        
        # Récupérer le ROI estimé
        roi = request.form.get('estimated_roi')
        if roi:
            try:
                optimization_data['estimated_roi'] = float(roi)
            except ValueError:
                pass
        
        # Envoyer les données à l'API
        try:
            response = requests.put(
                f'{request.host_url.rstrip("/")}{API_ENDPOINT}/optimizations/{optimization_id}',
                json=optimization_data
            )
            
            if response.status_code == 200:
                flash(translations.get('optimization_updated', 'Optimization updated successfully'), 'success')
                
                # Rediriger vers la vue de l'optimisation
                return redirect(url_for('process_analysis.view_optimization', optimization_id=optimization_id))
            else:
                logger.error(f"Error updating optimization: {response.status_code} - {response.text}")
                flash(translations.get('api_error', 'Error updating optimization'), 'danger')
        
        except Exception as e:
            logger.error(f"Error connecting to API: {e}")
            flash(translations.get('api_connection_error', 'Error connecting to the API'), 'danger')
    
    return render_template(
        'process_analysis/edit_optimization.html',
        translations=translations,
        optimization=optimization
    )


@process_analysis_bp.route('/optimizations/<int:optimization_id>/delete', methods=['POST'])
def delete_optimization(optimization_id):
    """Supprimer une optimisation."""
    translations = get_translations()
    
    # Récupérer d'abord l'optimisation pour avoir le process_id
    try:
        response = requests.get(
            f'{request.host_url.rstrip("/")}{API_ENDPOINT}/optimizations/{optimization_id}'
        )
        
        if response.status_code != 200:
            logger.error(f"Error retrieving optimization: {response.status_code} - {response.text}")
            flash(translations.get('optimization_not_found', 'Optimization not found'), 'danger')
            return redirect(url_for('process_analysis.processes'))
        
        optimization = response.json()
        process_id = optimization.get('process_id')
        
        # Maintenant supprimer l'optimisation
        delete_response = requests.delete(
            f'{request.host_url.rstrip("/")}{API_ENDPOINT}/optimizations/{optimization_id}'
        )
        
        if delete_response.status_code == 200:
            flash(translations.get('optimization_deleted', 'Optimization deleted successfully'), 'success')
        else:
            logger.error(f"Error deleting optimization: {delete_response.status_code} - {delete_response.text}")
            flash(translations.get('api_error', 'Error deleting optimization'), 'danger')
        
        # Rediriger vers la vue du processus
        if process_id:
            return redirect(url_for('process_analysis.view_process', process_id=process_id))
        else:
            return redirect(url_for('process_analysis.processes'))
    
    except Exception as e:
        logger.error(f"Error connecting to API: {e}")
        flash(translations.get('api_connection_error', 'Error connecting to the API'), 'danger')
        return redirect(url_for('process_analysis.processes'))


# Routes pour la gestion des jalons

@process_analysis_bp.route('/optimizations/<int:optimization_id>/milestones/new', methods=['GET', 'POST'])
def new_milestone(optimization_id):
    """Création d'un nouveau jalon pour une optimisation."""
    translations = get_translations()
    lang = get_current_language()
    
    # Récupérer les détails de l'optimisation
    try:
        response = requests.get(
            f'{request.host_url.rstrip("/")}{API_ENDPOINT}/optimizations/{optimization_id}'
        )
        
        if response.status_code != 200:
            logger.error(f"Error retrieving optimization: {response.status_code} - {response.text}")
            flash(translations.get('optimization_not_found', 'Optimization not found'), 'danger')
            return redirect(url_for('process_analysis.processes'))
        
        optimization = response.json()
    
    except Exception as e:
        logger.error(f"Error connecting to API: {e}")
        flash(translations.get('api_connection_error', 'Error connecting to the API'), 'danger')
        return redirect(url_for('process_analysis.processes'))
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        milestone_data = {
            'title': request.form.get('title'),
            'description': request.form.get('description'),
            'status': request.form.get('status', 'pending')
        }
        
        # Récupérer la date planifiée
        planned_date = request.form.get('planned_date')
        if planned_date:
            milestone_data['planned_date'] = planned_date
        
        # Récupérer les notes
        notes = request.form.get('notes')
        if notes:
            milestone_data['notes'] = notes
        
        # Envoyer les données à l'API
        try:
            response = requests.post(
                f'{request.host_url.rstrip("/")}{API_ENDPOINT}/optimizations/{optimization_id}/milestones',
                json=milestone_data
            )
            
            if response.status_code == 201:
                flash(translations.get('milestone_created', 'Milestone created successfully'), 'success')
                
                # Rediriger vers la vue de l'optimisation
                return redirect(url_for('process_analysis.view_optimization', optimization_id=optimization_id))
            else:
                logger.error(f"Error creating milestone: {response.status_code} - {response.text}")
                flash(translations.get('api_error', 'Error creating milestone'), 'danger')
        
        except Exception as e:
            logger.error(f"Error connecting to API: {e}")
            flash(translations.get('api_connection_error', 'Error connecting to the API'), 'danger')
    
    return render_template(
        'process_analysis/new_milestone.html',
        translations=translations,
        optimization=optimization
    )


@process_analysis_bp.route('/milestones/<int:milestone_id>/edit', methods=['GET', 'POST'])
def edit_milestone(milestone_id):
    """Édition d'un jalon existant."""
    translations = get_translations()
    lang = get_current_language()
    
    # Récupérer le jalon et l'optimisation associée
    try:
        # Nous n'avons pas d'endpoint direct pour un jalon, nous devons donc récupérer tous les jalons de l'optimisation
        # et trouver celui qui correspond
        
        # D'abord, nous devons trouver l'optimisation à laquelle appartient le jalon
        # Dans une application réelle, cela devrait être stocké dans la session ou passé en paramètre
        
        # Pour notre exemple, nous allons parcourir toutes les optimisations
        # Ceci n'est pas optimal et devrait être amélioré dans une application réelle
        
        # Récupérer la liste des processus
        processes_response = requests.get(
            f'{request.host_url.rstrip("/")}{API_ENDPOINT}/processes'
        )
        
        if processes_response.status_code != 200:
            logger.error(f"Error retrieving processes: {processes_response.status_code} - {processes_response.text}")
            flash(translations.get('api_error', 'Error retrieving processes'), 'danger')
            return redirect(url_for('process_analysis.processes'))
        
        processes = processes_response.json().get('items', [])
        
        # Parcourir les processus pour trouver le jalon
        milestone = None
        optimization = None
        
        for process in processes:
            process_id = process.get('id')
            
            # Récupérer les optimisations du processus
            optimizations_response = requests.get(
                f'{request.host_url.rstrip("/")}{API_ENDPOINT}/processes/{process_id}/optimizations'
            )
            
            if optimizations_response.status_code != 200:
                continue
            
            optimizations = optimizations_response.json().get('items', [])
            
            for opt in optimizations:
                optimization_id = opt.get('id')
                
                # Récupérer les jalons de l'optimisation
                milestones_response = requests.get(
                    f'{request.host_url.rstrip("/")}{API_ENDPOINT}/optimizations/{optimization_id}/milestones'
                )
                
                if milestones_response.status_code != 200:
                    continue
                
                milestones = milestones_response.json().get('items', [])
                
                for m in milestones:
                    if m.get('id') == milestone_id:
                        milestone = m
                        
                        # Récupérer les détails complets de l'optimisation
                        opt_response = requests.get(
                            f'{request.host_url.rstrip("/")}{API_ENDPOINT}/optimizations/{optimization_id}'
                        )
                        
                        if opt_response.status_code == 200:
                            optimization = opt_response.json()
                        
                        break
                
                if milestone:
                    break
            
            if milestone:
                break
        
        if not milestone or not optimization:
            flash(translations.get('milestone_not_found', 'Milestone not found'), 'danger')
            return redirect(url_for('process_analysis.processes'))
    
    except Exception as e:
        logger.error(f"Error connecting to API: {e}")
        flash(translations.get('api_connection_error', 'Error connecting to the API'), 'danger')
        return redirect(url_for('process_analysis.processes'))
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        milestone_data = {
            'title': request.form.get('title'),
            'description': request.form.get('description'),
            'status': request.form.get('status', 'pending')
        }
        
        # Récupérer les dates
        planned_date = request.form.get('planned_date')
        if planned_date:
            milestone_data['planned_date'] = planned_date
        
        completed_date = request.form.get('completed_date')
        if completed_date:
            milestone_data['completed_date'] = completed_date
        
        # Récupérer le pourcentage d'achèvement
        completion_percentage = request.form.get('completion_percentage')
        if completion_percentage:
            try:
                milestone_data['completion_percentage'] = int(completion_percentage)
            except ValueError:
                pass
        
        # Récupérer les notes
        notes = request.form.get('notes')
        if notes:
            milestone_data['notes'] = notes
        
        # Envoyer les données à l'API
        try:
            response = requests.put(
                f'{request.host_url.rstrip("/")}{API_ENDPOINT}/milestones/{milestone_id}',
                json=milestone_data
            )
            
            if response.status_code == 200:
                flash(translations.get('milestone_updated', 'Milestone updated successfully'), 'success')
                
                # Rediriger vers la vue de l'optimisation
                return redirect(url_for('process_analysis.view_optimization', optimization_id=optimization.get('id')))
            else:
                logger.error(f"Error updating milestone: {response.status_code} - {response.text}")
                flash(translations.get('api_error', 'Error updating milestone'), 'danger')
        
        except Exception as e:
            logger.error(f"Error connecting to API: {e}")
            flash(translations.get('api_connection_error', 'Error connecting to the API'), 'danger')
    
    return render_template(
        'process_analysis/edit_milestone.html',
        translations=translations,
        milestone=milestone,
        optimization=optimization
    )


# Routes pour la gestion des mesures de résultats

@process_analysis_bp.route('/optimizations/<int:optimization_id>/results/new', methods=['GET', 'POST'])
def new_result(optimization_id):
    """Création d'une nouvelle mesure de résultat pour une optimisation."""
    translations = get_translations()
    lang = get_current_language()
    
    # Récupérer les détails de l'optimisation
    try:
        response = requests.get(
            f'{request.host_url.rstrip("/")}{API_ENDPOINT}/optimizations/{optimization_id}'
        )
        
        if response.status_code != 200:
            logger.error(f"Error retrieving optimization: {response.status_code} - {response.text}")
            flash(translations.get('optimization_not_found', 'Optimization not found'), 'danger')
            return redirect(url_for('process_analysis.processes'))
        
        optimization = response.json()
    
    except Exception as e:
        logger.error(f"Error connecting to API: {e}")
        flash(translations.get('api_connection_error', 'Error connecting to the API'), 'danger')
        return redirect(url_for('process_analysis.processes'))
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        result_data = {
            'metric_name': request.form.get('metric_name'),
            'unit': request.form.get('unit', '')
        }
        
        # Récupérer les valeurs
        baseline_value = request.form.get('baseline_value')
        if baseline_value:
            try:
                result_data['baseline_value'] = float(baseline_value)
            except ValueError:
                pass
        
        target_value = request.form.get('target_value')
        if target_value:
            try:
                result_data['target_value'] = float(target_value)
            except ValueError:
                pass
        
        current_value = request.form.get('current_value')
        if current_value:
            try:
                result_data['current_value'] = float(current_value)
            except ValueError:
                pass
        
        # Récupérer la date de mesure
        measurement_date = request.form.get('measurement_date')
        if measurement_date:
            result_data['measurement_date'] = measurement_date
        
        # Récupérer les notes
        notes = request.form.get('notes')
        if notes:
            result_data['notes'] = notes
        
        # Envoyer les données à l'API
        try:
            response = requests.post(
                f'{request.host_url.rstrip("/")}{API_ENDPOINT}/optimizations/{optimization_id}/results',
                json=result_data
            )
            
            if response.status_code == 201:
                flash(translations.get('result_created', 'Result measurement created successfully'), 'success')
                
                # Rediriger vers la vue de l'optimisation
                return redirect(url_for('process_analysis.view_optimization', optimization_id=optimization_id))
            else:
                logger.error(f"Error creating result: {response.status_code} - {response.text}")
                flash(translations.get('api_error', 'Error creating result measurement'), 'danger')
        
        except Exception as e:
            logger.error(f"Error connecting to API: {e}")
            flash(translations.get('api_connection_error', 'Error connecting to the API'), 'danger')
    
    return render_template(
        'process_analysis/new_result.html',
        translations=translations,
        optimization=optimization
    )


@process_analysis_bp.route('/results/<int:result_id>/edit', methods=['GET', 'POST'])
def edit_result(result_id):
    """Édition d'une mesure de résultat existante."""
    translations = get_translations()
    lang = get_current_language()
    
    # Récupérer la mesure de résultat et l'optimisation associée
    # Même problème que pour les jalons, nous n'avons pas d'endpoint direct
    
    # Pour simplifier, nous redirigeons vers la liste des processus
    flash(translations.get('feature_not_implemented', 'This feature is not yet implemented'), 'warning')
    return redirect(url_for('process_analysis.processes'))