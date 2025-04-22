import json
import logging
import traceback
import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import current_user
from auth import login_required
from forms import BusinessConsultationForm
from models_business import BusinessReport, db
import openai_integration
import email_service

# Configurer le logging
logger = logging.getLogger(__name__)
debug_logger = logging.getLogger("business_debug")

# Blueprint pour les fonctionnalités business
business_bp = Blueprint('business', __name__, url_prefix='/business')

def init_app(app):
    """Initialiser les routes business pour l'application Flask"""
    app.register_blueprint(business_bp)
    
@business_bp.route("/test", methods=["GET"])
def test_page():
    """Page de test du blueprint business"""
    # Page de test simplifiée pour éviter les erreurs
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Business Blueprint</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
    </head>
    <body class="bg-dark text-light">
        <div class="container py-5">
            <div class="card bg-dark border-primary">
                <div class="card-body">
                    <h1 class="text-center">Test Business Blueprint</h1>
                    <p class="text-center mb-4">Le blueprint business est correctement chargé.</p>
                    
                    <div class="list-group mb-4">
                        <a href="/business/test_direct_report/1" class="list-group-item list-group-item-action">
                            Test d'affichage direct d'un rapport (HTML direct)
                        </a>
                        <a href="/business/test-business" class="list-group-item list-group-item-action">
                            Test de la consultation business simplifiée
                        </a>
                    </div>
                    
                    <div class="mt-4 text-center">
                        <a href="/" class="btn btn-secondary">Retour à l'accueil</a>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@business_bp.route("/test_redirect/<path:destination>", methods=["GET"])
def test_redirect(destination):
    """Test de redirection vers différentes pages"""
    print(f"Test de redirection vers: {destination}")
    if destination == "home":
        target = url_for('home')
    elif destination.startswith("report/"):
        report_id = int(destination.split('/')[1])
        target = url_for('business.business_report', report_id=report_id)
    else:
        target = url_for('home')
    
    print(f"URL cible: {target}")
    flash("Test de redirection en cours...", "info")
    return redirect(target)

@business_bp.route("/test_direct_report/<int:report_id>", methods=["GET"])
def test_direct_report(report_id):
    """Test d'affichage direct d'un rapport"""
    print(f"Test d'affichage direct du rapport {report_id}")
    
    try:
        # Créer des données fictives pour le rapport
        company_data = {
            'company_name': "Entreprise Test",
            'industry': "Technologie",
            'company_size': "Petite",
            'company_age': "3-5 ans",
            'annual_revenue': "100k-500k€"
        }
        
        analysis = {
            'summary': "Ceci est un rapport de test pour vérifier le fonctionnement des templates.",
            'strengths': ["Force de test 1", "Force de test 2", "Force de test 3"],
            'weaknesses': ["Faiblesse de test 1", "Faiblesse de test 2", "Faiblesse de test 3"],
            'opportunities': ["Opportunité de test 1", "Opportunité de test 2", "Opportunité de test 3"],
            'threats': ["Menace de test 1", "Menace de test 2", "Menace de test 3"],
            'recommendations': {
                "Test": [
                    {
                        "title": "Recommandation de test",
                        "description": "Description de test",
                        "priority": "Haute",
                        "priority_color": "danger",
                        "impact": "Impact de test"
                    }
                ]
            },
            'action_plan': [
                {
                    "title": "Action de test",
                    "icon": "fa-check",
                    "timeframe": "Court terme",
                    "description": "Description de l'action de test"
                }
            ]
        }
        
        analysis_date = "17/04/2025"
        
        # Créons une page de test simple pour vérifier si le problème est lié au template spécifique
        simple_response = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Page de test simplifiée</title>
            <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        </head>
        <body class="bg-dark text-light">
            <div class="container py-5">
                <div class="card bg-dark">
                    <div class="card-body">
                        <h1>Test d'affichage d'un rapport</h1>
                        <p>Cette page s'affiche correctement, ce qui signifie que la route fonctionne.</p>
                        <div class="alert alert-success">
                            <p>ID du rapport: {}</p>
                            <p>Entreprise: {}</p>
                        </div>
                        <div class="mt-4">
                            <a href="/business/test" class="btn btn-secondary">Retour à la page de test</a>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """.format(report_id, company_data['company_name'])
        
        # Essayons d'afficher cette réponse directe au lieu du template
        return simple_response
        
    except Exception as e:
        print(f"Erreur lors de l'affichage du rapport de test: {str(e)}")
        print(traceback.format_exc())
        flash(f"Erreur de test: {str(e)}", "danger")
        return redirect(url_for('home'))

@business_bp.route("/consultation", methods=["GET", "POST"])
def business_consultation():
    """Page de formulaire pour la consultation business personnalisée accessible sans connexion"""
    # Vérifier si l'utilisateur est connecté
    if session.get('username'):
        # Rediriger vers la page de chat avec le topic business
        return redirect(url_for('chat_page', topic='business'))
    else:
        # Créer une page d'information pour les utilisateurs non connectés
        return render_template("business/business_info.html")

@business_bp.route("/transition/<int:report_id>")
@login_required
def business_transition(report_id):
    """Page de transition montrant l'analyse en cours"""
    from models import User
    
    debug_logger.debug(f"Affichage de la page de transition pour le rapport #{report_id}")
    
    user = User.query.filter_by(username=session.get('username')).first()
    if not user:
        flash("Veuillez vous connecter pour accéder à cette fonctionnalité.", "warning")
        return redirect(url_for('login'))
    
    # Récupérer le rapport
    report = BusinessReport.query.get_or_404(report_id)
    
    # Vérifier que le rapport appartient à l'utilisateur ou que l'utilisateur est admin
    if report.user_id != user.id and not session.get('is_admin'):
        flash("Vous n'êtes pas autorisé à accéder à ce rapport.", "danger")
        return redirect(url_for('home'))
    
    debug_logger.debug(f"Rendu du template de transition pour {report.company_name}")
    
    # Rendre le template de la page de transition
    return render_template("business_transition.html", 
                          report_id=report_id, 
                          company_name=report.company_name)

@business_bp.route("/report/<int:report_id>")
def business_report(report_id):
    """Afficher le rapport d'analyse business"""
    from models import User
    
    # Récupérer le rapport
    report = BusinessReport.query.get_or_404(report_id)
    
    # Vérifier si l'utilisateur est connecté
    user = User.query.filter_by(username=session.get('username')).first()
    
    # Si le rapport a un propriétaire (user_id non null)
    if report.user_id is not None:
        # Vérifier que l'utilisateur est connecté et est le propriétaire ou un admin
        if not user:
            flash("Veuillez vous connecter pour accéder à ce rapport.", "warning")
            return redirect(url_for('login'))
        if report.user_id != user.id and not session.get('is_admin'):
            flash("Vous n'êtes pas autorisé à accéder à ce rapport.", "danger")
            return redirect(url_for('home'))
        
    # Vérifier si le rapport contient des placeholders "Analyse en cours..."
    # Si oui, générer l'analyse complète maintenant
    if report.analysis_summary == "Analyse en cours...":
        try:
            # Récupérer les données de l'entreprise
            company_data = {
                'company_name': report.company_name,
                'industry': report.industry,
                'company_size': report.company_size,
                'company_age': report.company_age,
                'annual_revenue': report.annual_revenue or "Non spécifié",
                'business_challenges': report.business_challenges,
                'growth_goals': report.growth_goals,
                'current_strengths': report.current_strengths or "Non spécifié",
                'improvement_areas': json.loads(report.improvement_areas) if report.improvement_areas else [],
                'additional_info': report.additional_info or "Non spécifié"
            }
            
            # Générer l'analyse SWOT avec OpenAI
            analysis_result = generate_business_analysis(company_data)
            
            # Mettre à jour le rapport avec les résultats
            report.analysis_summary = analysis_result['summary']
            report.strengths = json.dumps(analysis_result['strengths'])
            report.weaknesses = json.dumps(analysis_result['weaknesses'])
            report.opportunities = json.dumps(analysis_result['opportunities'])
            report.threats = json.dumps(analysis_result['threats'])
            report.recommendations = json.dumps(analysis_result['recommendations'])
            report.action_plan = json.dumps(analysis_result['action_plan'])
            
            # Sauvegarder le rapport mis à jour
            from main import db
            db.session.commit()
            
            logger.info(f"Analyse complète générée pour le rapport #{report_id}")
        except Exception as e:
            logger.error(f"Erreur lors de la génération de l'analyse complète: {str(e)}")
            logger.error(traceback.format_exc())
    
    # Convertir les données JSON en objets Python
    company_data = {
        'company_name': report.company_name,
        'industry': report.industry,
        'company_size': report.company_size,
        'company_age': report.company_age,
        'annual_revenue': report.annual_revenue or "Non spécifié"
    }
    
    analysis = {
        'summary': report.analysis_summary,
        'strengths': json.loads(report.strengths) if report.strengths else [],
        'weaknesses': json.loads(report.weaknesses) if report.weaknesses else [],
        'opportunities': json.loads(report.opportunities) if report.opportunities else [],
        'threats': json.loads(report.threats) if report.threats else [],
        'recommendations': json.loads(report.recommendations) if report.recommendations else {},
        'action_plan': json.loads(report.action_plan) if report.action_plan else []
    }
    
    analysis_date = report.updated_at.strftime("%d/%m/%Y")
    
    # Créer les éléments HTML pour chaque force
    strengths_html = ""
    for item in analysis['strengths']:
        strengths_html += '<li class="swot-item"><i class="bi bi-check-circle-fill text-success me-2"></i>' + item + '</li>'
        
    # Créer les éléments HTML pour chaque faiblesse
    weaknesses_html = ""
    for item in analysis['weaknesses']:
        weaknesses_html += '<li class="swot-item"><i class="bi bi-exclamation-triangle-fill text-danger me-2"></i>' + item + '</li>'
        
    # Créer les éléments HTML pour chaque opportunité
    opportunities_html = ""
    for item in analysis['opportunities']:
        opportunities_html += '<li class="swot-item"><i class="bi bi-lightbulb-fill text-info me-2"></i>' + item + '</li>'
        
    # Créer les éléments HTML pour chaque menace
    threats_html = ""
    for item in analysis['threats']:
        threats_html += '<li class="swot-item"><i class="bi bi-shield-exclamation text-warning me-2"></i>' + item + '</li>'
    
    # Vérifier si ce rapport a été généré récemment (moins de 5 minutes)
    is_new_report = (datetime.utcnow() - report.updated_at).total_seconds() < 300
    
    # Passer le statut d'envoi d'email au template
    email_sent = hasattr(report, 'email_sent') and report.email_sent
    
    # Plus d'informations de débogage
    debug_logger.debug(f"Rendu du rapport d'analyse business #{report_id}")
    debug_logger.debug(f"Rapport pour: {company_data['company_name']}")
    
    return render_template("business_report.html",
                          company_data=company_data,
                          analysis=analysis,
                          analysis_date=analysis_date,
                          report_id=report_id,
                          strengths_html=strengths_html,
                          weaknesses_html=weaknesses_html,
                          opportunities_html=opportunities_html,
                          threats_html=threats_html,
                          is_new_report=is_new_report,
                          email_sent=email_sent)

def generate_business_analysis(company_data):
    """
    Génère une analyse SWOT et des recommandations en utilisant OpenAI
    """
    try:
        # Création du prompt pour OpenAI
        prompt = f"""
        En tant que consultant business expérimenté, réalise une analyse complète pour cette entreprise :
        
        Nom : {company_data['company_name']}
        Secteur : {company_data['industry']}
        Taille : {company_data['company_size']}
        Âge : {company_data['company_age']}
        Chiffre d'affaires : {company_data['annual_revenue']}
        
        Défis actuels : {company_data['business_challenges']}
        Objectifs de croissance : {company_data['growth_goals']}
        Forces perçues : {company_data['current_strengths']}
        Domaines d'amélioration prioritaires : {', '.join(company_data['improvement_areas'])}
        Informations supplémentaires : {company_data['additional_info']}
        
        Fournis une analyse SWOT structurée et des recommandations stratégiques au format JSON avec ces éléments :
        
        1. Un résumé de l'analyse (summary) en 3-4 phrases
        2. 3-5 forces (strengths)
        3. 3-5 faiblesses (weaknesses)
        4. 3-5 opportunités (opportunities)
        5. 3-5 menaces (threats)
        6. Des recommandations (recommendations) organisées par catégorie, chacune avec:
           - title: titre de la recommandation
           - description: explication détaillée
           - priority: priorité (Haute, Moyenne, Basse)
           - priority_color: couleur Bootstrap (danger, warning, info)
           - impact: impact attendu sur l'entreprise
        7. Un plan d'action (action_plan) avec 3-5 actions concrètes, chacune avec:
           - title: nom de l'action
           - icon: icône FontAwesome (fa-chart-line, fa-users, fa-money-bill, etc.)
           - timeframe: période (Court terme, Moyen terme, Long terme)
           - description: description détaillée de l'action
           
        Réponds UNIQUEMENT au format JSON sans explications supplémentaires.
        """
        
        # Appel à l'API OpenAI
        result = openai_integration.get_openai_response(prompt)
        logger.debug(f"Résultat OpenAI reçu, taille: {len(result)}")
        print(f"Résultat OpenAI reçu, taille: {len(result)}")
        
        try:
            # Tenter de charger la réponse en tant que JSON
            analysis_result = json.loads(result)
            
            # Validation des clés requises
            required_keys = ['summary', 'strengths', 'weaknesses', 'opportunities', 'threats', 'recommendations', 'action_plan']
            for key in required_keys:
                if key not in analysis_result:
                    analysis_result[key] = [] if key != 'summary' and key != 'recommendations' else ("" if key == 'summary' else {})
            
            print("Analyse SWOT générée avec succès")
            
            return analysis_result
            
        except json.JSONDecodeError:
            logger.error(f"Réponse JSON invalide: {result}")
            print(f"ERREUR: Réponse JSON invalide: {result[:100]}...")
            
            # Réponse de secours en cas d'erreur de format
            return {
                'summary': "Analyse générée avec succès, mais une erreur est survenue lors du formatage des résultats.",
                'strengths': ["Force identifiée par l'analyse"],
                'weaknesses': ["Faiblesse identifiée par l'analyse"],
                'opportunities': ["Opportunité identifiée par l'analyse"],
                'threats': ["Menace identifiée par l'analyse"],
                'recommendations': {
                    "Général": [
                        {
                            "title": "Consulter un expert",
                            "description": "Une analyse plus approfondie par un expert serait bénéfique.",
                            "priority": "Haute",
                            "priority_color": "danger",
                            "impact": "Amélioration significative des performances"
                        }
                    ]
                },
                'action_plan': [
                    {
                        "title": "Réexécuter l'analyse",
                        "icon": "fa-sync",
                        "timeframe": "Court terme",
                        "description": "Réessayer l'analyse avec plus de détails."
                    }
                ]
            }
            
    except Exception as e:
        logger.error(f"Erreur lors de la génération de l'analyse business: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Réponse de secours en cas d'erreur générale
        return {
            'summary': f"Une erreur est survenue lors de l'analyse: {str(e)}",
            'strengths': ["Forces non disponibles en raison d'une erreur"],
            'weaknesses': ["Faiblesses non disponibles en raison d'une erreur"],
            'opportunities': ["Opportunités non disponibles en raison d'une erreur"],
            'threats': ["Menaces non disponibles en raison d'une erreur"],
            'recommendations': {
                "Erreur": [
                    {
                        "title": "Réessayer ultérieurement",
                        "description": f"Une erreur technique est survenue: {str(e)}",
                        "priority": "Haute",
                        "priority_color": "danger",
                        "impact": "Non disponible"
                    }
                ]
            },
            'action_plan': [
                {
                    "title": "Contacter le support",
                    "icon": "fa-exclamation-circle",
                    "timeframe": "Immédiat",
                    "description": "Contactez le support technique en mentionnant cette erreur."
                }
            ]
        }
        
@business_bp.route("/test-business", methods=["GET", "POST"])
def business_test():
    """Formulaire de consultation business ultra-simplifié"""
    # Récupérer le formulaire de la requête s'il est soumis
    if request.method == "POST":
        try:
            company_name = request.form.get('company_name', 'Entreprise Test')
            industry = request.form.get('industry', 'Technologie')
            
            # Créer un rapport de test
            from models_business import BusinessReport
            from main import db
            import json
            
            # Créer un nouveau rapport anonyme 
            report = BusinessReport(
                user_id=None,
                company_name=company_name,
                industry=industry,
                company_size="Petite",
                company_age="1-3 ans",
                annual_revenue="100k-500k€",
                business_challenges="Test de débogage",
                growth_goals="Tester le fonctionnement",
                current_strengths="Page de test simplifiée",
                improvement_areas=json.dumps(["Débogage", "Simplicité"]),
                additional_info="Test créé via le formulaire simplifié"
            )
            
            # Initialiser avec des données de test
            report.analysis_summary = "Ceci est un rapport de test généré à partir du formulaire simplifié."
            report.strengths = json.dumps(["Force de test 1", "Force de test 2"])
            report.weaknesses = json.dumps(["Faiblesse de test 1", "Faiblesse de test 2"])
            report.opportunities = json.dumps(["Opportunité de test 1", "Opportunité de test 2"])
            report.threats = json.dumps(["Menace de test 1", "Menace de test 2"])
            report.recommendations = json.dumps({"Test": [{"title": "Recommandation de test", "description": "Description de test", "priority": "Haute", "priority_color": "danger", "impact": "Impact de test"}]})
            report.action_plan = json.dumps([{"title": "Action de test", "icon": "fa-check", "timeframe": "Court terme", "description": "Description de l'action de test"}])
            report.updated_at = datetime.utcnow()
            report.email_sent = True
            
            # Sauvegarder le rapport
            db.session.add(report)
            db.session.commit()
            
            # Rediriger vers le rapport
            return redirect(url_for('business.business_report', report_id=report.id))
        except Exception as e:
            logger.error(f"Erreur dans business_test: {str(e)}")
            logger.error(traceback.format_exc())
            flash(f"Erreur: {str(e)}", "danger")
    
    # Afficher le formulaire
    return render_template("business_test.html")