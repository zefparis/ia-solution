"""
Service d'analyse des processus d'entreprise - Microservice responsable de l'analyse
des processus existants, l'identification des points d'optimisation, et la proposition
de solutions sur mesure

Ce service expose une API REST pour l'analyse des processus d'entreprise, la proposition
d'optimisations, et le suivi des résultats.
"""

import os
import json
import logging
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app, g
from sqlalchemy.exc import SQLAlchemyError

from models_process import (
    BusinessProcess, ProcessOptimization, 
    ImplementationMilestone, ResultMeasurement, db
)
from services.openai_service.client import OpenAIClient
from cache.flask_integration import cached, rate_limited

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Création du Blueprint pour le service d'analyse des processus
process_analysis_service = Blueprint('process_analysis_service', __name__, url_prefix='/api/process-analysis')

# Client OpenAI - sera initialisé lors de l'enregistrement du service
openai_client = None


@process_analysis_service.route('/health', methods=['GET'])
def health_check():
    """Endpoint de vérification de l'état du service d'analyse des processus."""
    return jsonify({
        'service': 'process_analysis_service',
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'dependencies': {
            'database': check_database_connection(),
            'openai_api': check_openai_connection()
        }
    })


def check_database_connection():
    """Vérifie la connexion à la base de données."""
    try:
        # Exécuter une requête simple pour vérifier la connexion
        db.session.execute('SELECT 1').fetchall()
        return {
            'status': 'healthy',
            'message': 'Database connection successful'
        }
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return {
            'status': 'unhealthy',
            'message': str(e)
        }


def check_openai_connection():
    """Vérifie la connexion à l'API OpenAI."""
    if not openai_client:
        return {
            'status': 'unhealthy',
            'message': 'OpenAI client not initialized'
        }
    
    try:
        models = openai_client.list_models()
        if models:
            return {
                'status': 'healthy',
                'message': 'OpenAI API connection successful'
            }
        else:
            return {
                'status': 'unhealthy',
                'message': 'No models returned from OpenAI API'
            }
    except Exception as e:
        logger.error(f"OpenAI API connection error: {e}")
        return {
            'status': 'unhealthy',
            'message': str(e)
        }


# Routes pour les processus d'entreprise

@process_analysis_service.route('/processes', methods=['GET'])
@cached(ttl=300, key_prefix='process_list')
def get_processes():
    """
    Récupère la liste des processus d'entreprise.
    
    Paramètres de requête:
    - user_id: ID de l'utilisateur
    - company_id: ID de l'entreprise
    - department: Département
    - limit: Nombre maximum de résultats (défaut: 50)
    - offset: Décalage pour la pagination (défaut: 0)
    """
    user_id = request.args.get('user_id')
    company_id = request.args.get('company_id')
    department = request.args.get('department')
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))
    
    # Construire la requête
    query = BusinessProcess.query
    
    if user_id:
        query = query.filter(BusinessProcess.user_id == user_id)
    if company_id:
        query = query.filter(BusinessProcess.company_id == company_id)
    if department:
        query = query.filter(BusinessProcess.department == department)
    
    # Exécuter la requête avec pagination
    processes = query.order_by(BusinessProcess.created_at.desc()).limit(limit).offset(offset).all()
    total = query.count()
    
    # Formatter les résultats
    result = {
        'items': [{
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'department': p.department,
            'created_at': p.created_at.isoformat(),
            'updated_at': p.updated_at.isoformat(),
            'pain_points_count': len(p.pain_points) if p.pain_points else 0,
            'optimizations_count': len(p.optimizations)
        } for p in processes],
        'total': total,
        'limit': limit,
        'offset': offset
    }
    
    return jsonify(result)


@process_analysis_service.route('/processes/<int:process_id>', methods=['GET'])
@cached(ttl=300, key_prefix='process_detail')
def get_process(process_id):
    """Récupère les détails d'un processus d'entreprise."""
    process = BusinessProcess.query.get_or_404(process_id)
    
    # Récupérer les optimisations liées
    optimizations = [{
        'id': opt.id,
        'title': opt.title,
        'description': opt.description,
        'priority': opt.priority,
        'status': opt.status,
        'estimated_roi': opt.estimated_roi,
        'created_at': opt.created_at.isoformat()
    } for opt in process.optimizations]
    
    # Formatter le résultat
    result = {
        'id': process.id,
        'user_id': process.user_id,
        'company_id': process.company_id,
        'name': process.name,
        'description': process.description,
        'department': process.department,
        'current_state': process.current_state,
        'pain_points': process.pain_points,
        'kpis': process.kpis,
        'created_at': process.created_at.isoformat(),
        'updated_at': process.updated_at.isoformat(),
        'optimizations': optimizations
    }
    
    return jsonify(result)


@process_analysis_service.route('/processes', methods=['POST'])
@rate_limited(limit=20, period=60)
def create_process():
    """
    Crée un nouveau processus d'entreprise.
    
    Requête JSON attendue:
    {
        "user_id": "user123",
        "company_id": 1,
        "name": "Processus de recrutement",
        "description": "Processus complet de recrutement des nouveaux employés",
        "department": "Ressources Humaines",
        "current_state": {
            "steps": [
                {"name": "Publication offre", "duration": 7},
                {"name": "Tri des CV", "duration": 3},
                {"name": "Entretiens", "duration": 14},
                {"name": "Décision", "duration": 5},
                {"name": "Intégration", "duration": 30}
            ],
            "total_duration": 59,
            "bottlenecks": ["Tri des CV", "Entretiens"]
        },
        "pain_points": [
            {"name": "Lenteur de décision", "impact": "high"},
            {"name": "Manque de candidats qualifiés", "impact": "medium"}
        ],
        "kpis": [
            {"name": "Délai de recrutement", "value": 59, "unit": "jours", "target": 30},
            {"name": "Coût par recrutement", "value": 2500, "unit": "EUR", "target": 1800}
        ]
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Valider les données requises
    required_fields = ['user_id', 'company_id', 'name']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    try:
        # Créer le nouveau processus
        process = BusinessProcess(
            user_id=data['user_id'],
            company_id=data['company_id'],
            name=data['name'],
            description=data.get('description'),
            department=data.get('department'),
            current_state=data.get('current_state'),
            pain_points=data.get('pain_points'),
            kpis=data.get('kpis')
        )
        
        db.session.add(process)
        db.session.commit()
        
        # Une fois le processus créé, lancer l'analyse automatique si des données suffisantes sont disponibles
        if data.get('current_state') and data.get('pain_points'):
            analyze_process.delay(process.id)
        
        return jsonify({
            'id': process.id,
            'message': 'Process created successfully',
            'analysis_started': bool(data.get('current_state') and data.get('pain_points'))
        }), 201
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error creating process: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500


@process_analysis_service.route('/processes/<int:process_id>', methods=['PUT'])
@rate_limited(limit=20, period=60)
def update_process(process_id):
    """
    Met à jour un processus d'entreprise existant.
    
    Requête JSON attendue: même structure que pour la création
    """
    process = BusinessProcess.query.get_or_404(process_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        # Mettre à jour les champs modifiables
        if 'name' in data:
            process.name = data['name']
        if 'description' in data:
            process.description = data['description']
        if 'department' in data:
            process.department = data['department']
        if 'current_state' in data:
            process.current_state = data['current_state']
        if 'pain_points' in data:
            process.pain_points = data['pain_points']
        if 'kpis' in data:
            process.kpis = data['kpis']
        
        db.session.commit()
        
        # Lancer une nouvelle analyse si les données critiques ont été mises à jour
        if 'current_state' in data or 'pain_points' in data:
            analyze_process.delay(process.id)
        
        return jsonify({
            'id': process.id,
            'message': 'Process updated successfully',
            'analysis_started': bool('current_state' in data or 'pain_points' in data)
        })
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error updating process: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500


@process_analysis_service.route('/processes/<int:process_id>', methods=['DELETE'])
@rate_limited(limit=10, period=60)
def delete_process(process_id):
    """Supprime un processus d'entreprise."""
    process = BusinessProcess.query.get_or_404(process_id)
    
    try:
        db.session.delete(process)
        db.session.commit()
        return jsonify({'message': 'Process deleted successfully'})
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error deleting process: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500


@process_analysis_service.route('/processes/<int:process_id>/analyze', methods=['POST'])
@rate_limited(limit=5, period=300)  # Limite stricte car c'est une opération coûteuse
def trigger_process_analysis(process_id):
    """
    Déclenche une analyse automatique d'un processus pour identifier des optimisations.
    """
    process = BusinessProcess.query.get_or_404(process_id)
    
    # Vérifier que les données nécessaires sont disponibles
    if not process.current_state or not process.pain_points:
        return jsonify({
            'error': 'Insufficient data',
            'message': 'Current state and pain points are required for analysis'
        }), 400
    
    # Lancer l'analyse en tâche de fond
    analyze_process.delay(process_id)
    
    return jsonify({
        'message': 'Process analysis started',
        'process_id': process_id,
        'status': 'processing'
    })


# Routes pour les optimisations

@process_analysis_service.route('/processes/<int:process_id>/optimizations', methods=['GET'])
@cached(ttl=300, key_prefix='optimization_list')
def get_optimizations(process_id):
    """Récupère les optimisations proposées pour un processus."""
    process = BusinessProcess.query.get_or_404(process_id)
    optimizations = process.optimizations
    
    result = {
        'process_id': process_id,
        'process_name': process.name,
        'items': [{
            'id': opt.id,
            'title': opt.title,
            'description': opt.description,
            'benefits': opt.benefits,
            'estimated_roi': opt.estimated_roi,
            'priority': opt.priority,
            'status': opt.status,
            'created_at': opt.created_at.isoformat(),
            'milestones_count': len(opt.milestones)
        } for opt in optimizations],
        'count': len(optimizations)
    }
    
    return jsonify(result)


@process_analysis_service.route('/optimizations/<int:optimization_id>', methods=['GET'])
@cached(ttl=300, key_prefix='optimization_detail')
def get_optimization(optimization_id):
    """Récupère les détails d'une optimisation."""
    optimization = ProcessOptimization.query.get_or_404(optimization_id)
    
    # Récupérer les jalons liés
    milestones = [{
        'id': m.id,
        'title': m.title,
        'description': m.description,
        'planned_date': m.planned_date.isoformat() if m.planned_date else None,
        'completed_date': m.completed_date.isoformat() if m.completed_date else None,
        'status': m.status,
        'completion_percentage': m.completion_percentage
    } for m in optimization.milestones]
    
    # Récupérer les mesures de résultats
    measurements = ResultMeasurement.query.filter_by(optimization_id=optimization_id).all()
    results = [{
        'id': m.id,
        'metric_name': m.metric_name,
        'baseline_value': m.baseline_value,
        'target_value': m.target_value,
        'current_value': m.current_value,
        'unit': m.unit,
        'measurement_date': m.measurement_date.isoformat() if m.measurement_date else None
    } for m in measurements]
    
    # Formatter le résultat
    result = {
        'id': optimization.id,
        'process_id': optimization.process_id,
        'title': optimization.title,
        'description': optimization.description,
        'benefits': optimization.benefits,
        'implementation_plan': optimization.implementation_plan,
        'resources_required': optimization.resources_required,
        'estimated_roi': optimization.estimated_roi,
        'priority': optimization.priority,
        'status': optimization.status,
        'created_at': optimization.created_at.isoformat(),
        'updated_at': optimization.updated_at.isoformat(),
        'milestones': milestones,
        'results': results
    }
    
    return jsonify(result)


@process_analysis_service.route('/processes/<int:process_id>/optimizations', methods=['POST'])
@rate_limited(limit=20, period=60)
def create_optimization(process_id):
    """
    Crée une nouvelle optimisation pour un processus.
    
    Requête JSON attendue:
    {
        "title": "Automatisation du tri des CV",
        "description": "Mettre en place un système d'analyse automatique des CV pour présélectionner les candidats",
        "benefits": {
            "time_saved": 15,
            "cost_reduction": 800,
            "quality_improvement": "Meilleure présélection des candidats"
        },
        "implementation_plan": {
            "phases": [
                {"name": "Analyse", "duration": 10},
                {"name": "Développement", "duration": 30},
                {"name": "Test", "duration": 15},
                {"name": "Déploiement", "duration": 5}
            ]
        },
        "resources_required": {
            "budget": 12000,
            "personnel": ["Développeur", "RH"],
            "tools": ["Outil d'IA pour l'analyse de CV"]
        },
        "estimated_roi": 2.5,
        "priority": "high"
    }
    """
    process = BusinessProcess.query.get_or_404(process_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Valider les données requises
    required_fields = ['title', 'description']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    try:
        # Créer la nouvelle optimisation
        optimization = ProcessOptimization(
            process_id=process_id,
            title=data['title'],
            description=data['description'],
            benefits=data.get('benefits'),
            implementation_plan=data.get('implementation_plan'),
            resources_required=data.get('resources_required'),
            estimated_roi=data.get('estimated_roi'),
            priority=data.get('priority', 'medium'),
            status='proposed'
        )
        
        db.session.add(optimization)
        
        # Créer les jalons si fournis
        if 'implementation_plan' in data and 'phases' in data['implementation_plan']:
            for idx, phase in enumerate(data['implementation_plan']['phases']):
                milestone = ImplementationMilestone(
                    title=phase['name'],
                    description=f"Phase {idx+1}: {phase['name']}",
                    planned_date=None,  # À définir ultérieurement
                    status='pending',
                    completion_percentage=0
                )
                optimization.milestones.append(milestone)
        
        db.session.commit()
        
        return jsonify({
            'id': optimization.id,
            'message': 'Optimization created successfully'
        }), 201
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error creating optimization: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500


@process_analysis_service.route('/optimizations/<int:optimization_id>', methods=['PUT'])
@rate_limited(limit=20, period=60)
def update_optimization(optimization_id):
    """
    Met à jour une optimisation existante.
    
    Requête JSON attendue: même structure que pour la création
    """
    optimization = ProcessOptimization.query.get_or_404(optimization_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        # Mettre à jour les champs modifiables
        if 'title' in data:
            optimization.title = data['title']
        if 'description' in data:
            optimization.description = data['description']
        if 'benefits' in data:
            optimization.benefits = data['benefits']
        if 'implementation_plan' in data:
            optimization.implementation_plan = data['implementation_plan']
        if 'resources_required' in data:
            optimization.resources_required = data['resources_required']
        if 'estimated_roi' in data:
            optimization.estimated_roi = data['estimated_roi']
        if 'priority' in data:
            optimization.priority = data['priority']
        if 'status' in data:
            optimization.status = data['status']
        
        db.session.commit()
        
        return jsonify({
            'id': optimization.id,
            'message': 'Optimization updated successfully'
        })
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error updating optimization: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500


@process_analysis_service.route('/optimizations/<int:optimization_id>', methods=['DELETE'])
@rate_limited(limit=10, period=60)
def delete_optimization(optimization_id):
    """Supprime une optimisation."""
    optimization = ProcessOptimization.query.get_or_404(optimization_id)
    
    try:
        db.session.delete(optimization)
        db.session.commit()
        return jsonify({'message': 'Optimization deleted successfully'})
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error deleting optimization: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500


# Routes pour les jalons de mise en œuvre

@process_analysis_service.route('/optimizations/<int:optimization_id>/milestones', methods=['GET'])
@cached(ttl=300, key_prefix='milestone_list')
def get_milestones(optimization_id):
    """Récupère les jalons de mise en œuvre d'une optimisation."""
    optimization = ProcessOptimization.query.get_or_404(optimization_id)
    milestones = optimization.milestones
    
    result = {
        'optimization_id': optimization_id,
        'optimization_title': optimization.title,
        'items': [{
            'id': m.id,
            'title': m.title,
            'description': m.description,
            'planned_date': m.planned_date.isoformat() if m.planned_date else None,
            'completed_date': m.completed_date.isoformat() if m.completed_date else None,
            'status': m.status,
            'completion_percentage': m.completion_percentage,
            'notes': m.notes
        } for m in milestones],
        'count': len(milestones)
    }
    
    return jsonify(result)


@process_analysis_service.route('/optimizations/<int:optimization_id>/milestones', methods=['POST'])
@rate_limited(limit=20, period=60)
def create_milestone(optimization_id):
    """
    Crée un nouveau jalon pour une optimisation.
    
    Requête JSON attendue:
    {
        "title": "Sélection de l'outil d'analyse de CV",
        "description": "Évaluer et sélectionner l'outil d'IA pour l'analyse automatique des CV",
        "planned_date": "2025-06-15",
        "status": "pending",
        "notes": "Prévoir des démos avec 3 fournisseurs"
    }
    """
    optimization = ProcessOptimization.query.get_or_404(optimization_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Valider les données requises
    if 'title' not in data:
        return jsonify({'error': 'Missing required field: title'}), 400
    
    try:
        # Créer le nouveau jalon
        milestone = ImplementationMilestone(
            optimization_id=optimization_id,
            title=data['title'],
            description=data.get('description'),
            planned_date=datetime.fromisoformat(data['planned_date']).date() if 'planned_date' in data else None,
            completed_date=datetime.fromisoformat(data['completed_date']).date() if 'completed_date' in data else None,
            status=data.get('status', 'pending'),
            completion_percentage=data.get('completion_percentage', 0),
            notes=data.get('notes')
        )
        
        db.session.add(milestone)
        db.session.commit()
        
        return jsonify({
            'id': milestone.id,
            'message': 'Milestone created successfully'
        }), 201
    
    except ValueError as e:
        return jsonify({'error': 'Invalid date format', 'details': str(e)}), 400
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error creating milestone: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500


@process_analysis_service.route('/milestones/<int:milestone_id>', methods=['PUT'])
@rate_limited(limit=20, period=60)
def update_milestone(milestone_id):
    """
    Met à jour un jalon existant.
    
    Requête JSON attendue: même structure que pour la création
    """
    milestone = ImplementationMilestone.query.get_or_404(milestone_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        # Mettre à jour les champs modifiables
        if 'title' in data:
            milestone.title = data['title']
        if 'description' in data:
            milestone.description = data['description']
        if 'planned_date' in data:
            milestone.planned_date = datetime.fromisoformat(data['planned_date']).date() if data['planned_date'] else None
        if 'completed_date' in data:
            milestone.completed_date = datetime.fromisoformat(data['completed_date']).date() if data['completed_date'] else None
        if 'status' in data:
            milestone.status = data['status']
            
            # Si le statut devient "completed", mettre à jour automatiquement d'autres champs
            if data['status'] == 'completed' and not milestone.completed_date:
                milestone.completed_date = datetime.now().date()
                milestone.completion_percentage = 100
                
        if 'completion_percentage' in data:
            milestone.completion_percentage = data['completion_percentage']
        if 'notes' in data:
            milestone.notes = data['notes']
        
        db.session.commit()
        
        return jsonify({
            'id': milestone.id,
            'message': 'Milestone updated successfully'
        })
    
    except ValueError as e:
        return jsonify({'error': 'Invalid date format', 'details': str(e)}), 400
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error updating milestone: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500


# Routes pour les mesures de résultats

@process_analysis_service.route('/optimizations/<int:optimization_id>/results', methods=['GET'])
@cached(ttl=300, key_prefix='result_list')
def get_results(optimization_id):
    """Récupère les mesures de résultats d'une optimisation."""
    optimization = ProcessOptimization.query.get_or_404(optimization_id)
    measurements = ResultMeasurement.query.filter_by(optimization_id=optimization_id).all()
    
    result = {
        'optimization_id': optimization_id,
        'optimization_title': optimization.title,
        'items': [{
            'id': m.id,
            'metric_name': m.metric_name,
            'baseline_value': m.baseline_value,
            'target_value': m.target_value,
            'current_value': m.current_value,
            'unit': m.unit,
            'measurement_date': m.measurement_date.isoformat() if m.measurement_date else None,
            'notes': m.notes
        } for m in measurements],
        'count': len(measurements)
    }
    
    return jsonify(result)


@process_analysis_service.route('/optimizations/<int:optimization_id>/results', methods=['POST'])
@rate_limited(limit=20, period=60)
def create_result(optimization_id):
    """
    Crée une nouvelle mesure de résultat pour une optimisation.
    
    Requête JSON attendue:
    {
        "metric_name": "Temps de tri des CV",
        "baseline_value": 180,
        "target_value": 30,
        "current_value": 120,
        "unit": "minutes",
        "measurement_date": "2025-07-01",
        "notes": "Première mesure après la mise en place de l'outil"
    }
    """
    optimization = ProcessOptimization.query.get_or_404(optimization_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Valider les données requises
    if 'metric_name' not in data:
        return jsonify({'error': 'Missing required field: metric_name'}), 400
    
    try:
        # Créer la nouvelle mesure
        measurement = ResultMeasurement(
            optimization_id=optimization_id,
            metric_name=data['metric_name'],
            baseline_value=data.get('baseline_value'),
            target_value=data.get('target_value'),
            current_value=data.get('current_value'),
            unit=data.get('unit'),
            measurement_date=datetime.fromisoformat(data['measurement_date']).date() if 'measurement_date' in data else datetime.now().date(),
            notes=data.get('notes')
        )
        
        db.session.add(measurement)
        db.session.commit()
        
        return jsonify({
            'id': measurement.id,
            'message': 'Result measurement created successfully'
        }), 201
    
    except ValueError as e:
        return jsonify({'error': 'Invalid date format', 'details': str(e)}), 400
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error creating result measurement: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500


@process_analysis_service.route('/results/<int:result_id>', methods=['PUT'])
@rate_limited(limit=20, period=60)
def update_result(result_id):
    """
    Met à jour une mesure de résultat existante.
    
    Requête JSON attendue: même structure que pour la création
    """
    measurement = ResultMeasurement.query.get_or_404(result_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        # Mettre à jour les champs modifiables
        if 'metric_name' in data:
            measurement.metric_name = data['metric_name']
        if 'baseline_value' in data:
            measurement.baseline_value = data['baseline_value']
        if 'target_value' in data:
            measurement.target_value = data['target_value']
        if 'current_value' in data:
            measurement.current_value = data['current_value']
        if 'unit' in data:
            measurement.unit = data['unit']
        if 'measurement_date' in data:
            measurement.measurement_date = datetime.fromisoformat(data['measurement_date']).date() if data['measurement_date'] else None
        if 'notes' in data:
            measurement.notes = data['notes']
        
        db.session.commit()
        
        return jsonify({
            'id': measurement.id,
            'message': 'Result measurement updated successfully'
        })
    
    except ValueError as e:
        return jsonify({'error': 'Invalid date format', 'details': str(e)}), 400
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error updating result measurement: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500


# Tâche de fond pour l'analyse des processus

def analyze_process(process_id):
    """
    Analyse un processus et génère des optimisations via l'IA.
    Cette fonction est conçue pour être exécutée en tâche de fond.
    
    Args:
        process_id (int): ID du processus à analyser
    """
    logger.info(f"Starting AI analysis for process ID: {process_id}")
    
    # Importer des modèles et créer une session de base de données
    from flask import Flask
    from models_process import BusinessProcess, ProcessOptimization, db
    
    # Créer une application Flask minimale pour le contexte
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        try:
            # Récupérer le processus
            process = BusinessProcess.query.get(process_id)
            if not process:
                logger.error(f"Process ID {process_id} not found")
                return
            
            # Préparation des données pour l'analyse
            process_data = {
                "name": process.name,
                "description": process.description,
                "department": process.department,
                "current_state": process.current_state,
                "pain_points": process.pain_points,
                "kpis": process.kpis
            }
            
            # Création du prompt pour l'API OpenAI
            prompt = f"""
            Analyser le processus d'entreprise suivant et identifier 3 à 5 optimisations potentielles.
            
            # Processus
            Nom: {process_data['name']}
            Description: {process_data['description']}
            Département: {process_data['department']}
            
            # État actuel
            {json.dumps(process_data['current_state'], indent=2)}
            
            # Points de douleur identifiés
            {json.dumps(process_data['pain_points'], indent=2)}
            
            # KPIs
            {json.dumps(process_data['kpis'], indent=2)}
            
            Pour chaque optimisation, fournir:
            1. Un titre concis
            2. Une description détaillée
            3. Les bénéfices attendus
            4. Un plan de mise en œuvre
            5. Les ressources requises
            6. Une estimation du ROI
            7. Une priorité (haute, moyenne, basse)
            
            Réponds sous format JSON avec un tableau "optimizations" contenant les optimisations proposées.
            """
            
            # Appel à l'API OpenAI
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                logger.error("OPENAI_API_KEY not configured")
                return
            
            client = OpenAIClient(api_key=api_key)
            response = client.generate_text(
                prompt=prompt,
                model="gpt-4o",
                max_tokens=2000,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            # Traitement de la réponse
            try:
                # Parsage de la réponse JSON
                optimization_data = json.loads(response.choices[0].message.content)
                optimizations = optimization_data.get('optimizations', [])
                
                # Créer les optimisations dans la base de données
                for opt_data in optimizations:
                    optimization = ProcessOptimization(
                        process_id=process_id,
                        title=opt_data.get('title', 'Sans titre'),
                        description=opt_data.get('description', ''),
                        benefits=opt_data.get('benefits'),
                        implementation_plan=opt_data.get('implementation_plan'),
                        resources_required=opt_data.get('resources_required'),
                        estimated_roi=float(opt_data.get('estimated_roi', 0)),
                        priority=opt_data.get('priority', 'medium'),
                        status='proposed'
                    )
                    
                    db.session.add(optimization)
                
                db.session.commit()
                logger.info(f"Analysis completed for process ID {process_id}. Generated {len(optimizations)} optimizations.")
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error processing OpenAI response: {e}")
                logger.error(f"Response content: {response.choices[0].message.content}")
                return
                
        except Exception as e:
            logger.error(f"Error during process analysis: {e}")
            db.session.rollback()


def register_service(app):
    """
    Enregistre le service d'analyse des processus auprès de l'application Flask.
    
    Args:
        app: L'application Flask
    """
    global openai_client
    
    # Initialiser le client OpenAI
    openai_api_key = os.environ.get('OPENAI_API_KEY')
    if openai_api_key:
        from services.openai_service.client import OpenAIClient
        openai_client = OpenAIClient(api_key=openai_api_key)
    else:
        logger.warning("OPENAI_API_KEY not configured for process analysis service")
    
    # Enregistrer le blueprint
    app.register_blueprint(process_analysis_service)
    
    logger.info("Process Analysis Service registered successfully")