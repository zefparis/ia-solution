"""
Script pour initialiser les données de démo pour le système de modules
"""
import os
import logging
from datetime import datetime, timedelta
from flask import Flask
from sqlalchemy.exc import IntegrityError

from models import db, User
from models_modules import ModuleCategory, BusinessModule, ModuleVersion, ModuleReview

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_modules_data():
    """Initialiser les données de démo pour le système de modules"""
    
    # Vérifier si des catégories existent déjà
    if ModuleCategory.query.count() > 0:
        logger.info("Des données existent déjà dans le système de modules.")
        return

    try:
        # Créer quelques catégories
        categories = [
            ModuleCategory(name="Finance", description="Modules pour la gestion financière", icon="fa-dollar-sign", color="#28a745"),
            ModuleCategory(name="Marketing", description="Modules pour le marketing et la communication", icon="fa-bullhorn", color="#17a2b8"),
            ModuleCategory(name="Production", description="Modules pour la gestion de production", icon="fa-industry", color="#6610f2"),
            ModuleCategory(name="RH", description="Modules pour la gestion des ressources humaines", icon="fa-users", color="#fd7e14"),
            ModuleCategory(name="Ventes", description="Modules pour la gestion commerciale", icon="fa-shopping-cart", color="#dc3545")
        ]
        
        for category in categories:
            db.session.add(category)
        
        logger.info("Catégories créées")
        db.session.commit()

        # Créer des modules de finance
        finance_category = ModuleCategory.query.filter_by(name="Finance").first()
        
        accounting_module = BusinessModule(
            name="Comptabilité Avancée",
            description="""
            <p>Module complet de comptabilité avancée avec gestion des bilans, comptes de résultat et liasses fiscales automatisées.</p>
            <h4>Fonctionnalités</h4>
            <ul>
                <li>Gestion automatisée des écritures comptables</li>
                <li>Génération des bilans et comptes de résultat</li>
                <li>Préparation des liasses fiscales</li>
                <li>Tableaux de bord financiers personnalisables</li>
                <li>Export aux formats standards</li>
            </ul>
            <p>Ce module s'intègre parfaitement avec les modules de facturation et de trésorerie existants.</p>
            """,
            short_description="Gestion comptable complète pour PME",
            version="1.2.0",
            category_id=finance_category.id if finance_category else None,
            icon="fa-calculator",
            author="IA-Solutions",
            website="https://ia-solutions.com",
            is_official=True,
            is_featured=True,
            price=19.99,
            currency="EUR",
            requirements="Nécessite un abonnement Pro ou supérieur",
            installation_script="# Installation simulée\nprint('Module de comptabilité installé')",
            uninstallation_script="# Désinstallation simulée\nprint('Module de comptabilité désinstallé')",
            status="published",
            publish_date=datetime.utcnow() - timedelta(days=90),
            last_updated=datetime.utcnow() - timedelta(days=15),
            download_count=127
        )
        
        cash_flow_module = BusinessModule(
            name="Prévisions de Trésorerie",
            description="""
            <p>Un outil puissant pour prévoir et gérer votre trésorerie avec des projections basées sur l'IA.</p>
            <h4>Fonctionnalités</h4>
            <ul>
                <li>Prévisions de trésorerie sur 12 mois</li>
                <li>Scénarios multiples (optimiste, pessimiste, réaliste)</li>
                <li>Alertes de trésorerie personnalisables</li>
                <li>Intégration avec vos données bancaires</li>
                <li>Tableaux de bord visuels</li>
            </ul>
            <p>Prenez des décisions éclairées grâce à une visibilité claire sur vos flux de trésorerie futurs.</p>
            """,
            short_description="Prévisions de trésorerie basées sur l'IA",
            version="2.1.0",
            category_id=finance_category.id if finance_category else None,
            icon="fa-chart-line",
            author="IA-Solutions",
            website="https://ia-solutions.com",
            is_official=True,
            is_featured=False,
            price=14.99,
            currency="EUR",
            requirements="Compatible avec tous les abonnements",
            status="published",
            publish_date=datetime.utcnow() - timedelta(days=60),
            last_updated=datetime.utcnow() - timedelta(days=5),
            download_count=86
        )
        
        budget_module = BusinessModule(
            name="Budget Manager",
            description="""
            <p>Gérez facilement vos budgets d'entreprise avec des outils de suivi en temps réel.</p>
            <h4>Fonctionnalités</h4>
            <ul>
                <li>Création de budgets par département</li>
                <li>Suivi des dépenses en temps réel</li>
                <li>Comparaison budget vs réel</li>
                <li>Alertes de dépassement</li>
                <li>Rapports d'analyse budgétaire</li>
            </ul>
            <p>Simple à configurer et à utiliser, ce module vous permet de garder le contrôle sur vos finances.</p>
            """,
            short_description="Gestion budgétaire simple et efficace",
            version="1.0.3",
            category_id=finance_category.id if finance_category else None,
            icon="fa-wallet",
            author="BudgetPro",
            website="https://budgetpro.io",
            is_official=False,
            is_featured=False,
            price=None,  # Gratuit
            currency="EUR",
            requirements="Compatible avec tous les abonnements",
            status="published",
            publish_date=datetime.utcnow() - timedelta(days=45),
            download_count=204
        )
        
        # Créer des modules de marketing
        marketing_category = ModuleCategory.query.filter_by(name="Marketing").first()
        
        marketing_automation_module = BusinessModule(
            name="Marketing Automation Pro",
            description="""
            <p>Automatisez vos campagnes marketing avec des workflows intelligents, segmentation avancée et analyses prédictives.</p>
            <h4>Fonctionnalités</h4>
            <ul>
                <li>Workflows marketing automatisés</li>
                <li>Segmentation avancée des clients</li>
                <li>Email marketing personnalisé</li>
                <li>Analyse prédictive des résultats</li>
                <li>Intégration avec les réseaux sociaux</li>
                <li>Rapports de performance détaillés</li>
            </ul>
            <p>Augmentez significativement l'efficacité de vos campagnes marketing et le ROI de vos actions.</p>
            """,
            short_description="Automatisation marketing intelligente",
            version="2.0.1",
            category_id=marketing_category.id if marketing_category else None,
            icon="fa-robot",
            author="MarketingAI",
            website="https://marketingai.com",
            is_official=False,
            is_featured=True,
            price=24.99,
            currency="EUR",
            requirements="Compatible avec tous les abonnements",
            status="published",
            publish_date=datetime.utcnow() - timedelta(days=75),
            last_updated=datetime.utcnow() - timedelta(days=10),
            download_count=89
        )
        
        social_media_module = BusinessModule(
            name="Social Media Master",
            description="""
            <p>Gérez tous vos réseaux sociaux en un seul endroit avec planification avancée et analyses.</p>
            <h4>Fonctionnalités</h4>
            <ul>
                <li>Publication sur plusieurs plateformes</li>
                <li>Planification des posts</li>
                <li>Suggestions de contenu par IA</li>
                <li>Analyses de performance</li>
                <li>Gestion des commentaires centralisée</li>
            </ul>
            <p>Maximisez votre présence sur les réseaux sociaux sans y passer des heures.</p>
            """,
            short_description="Gestion efficace des réseaux sociaux",
            version="1.5.2",
            category_id=marketing_category.id if marketing_category else None,
            icon="fa-hashtag",
            author="SocialPro",
            website="https://socialpro.io",
            is_official=False,
            is_featured=False,
            price=12.99,
            currency="EUR",
            requirements="Compatible avec tous les abonnements",
            status="published",
            publish_date=datetime.utcnow() - timedelta(days=120),
            last_updated=datetime.utcnow() - timedelta(days=30),
            download_count=156
        )
        
        # Créer des modules de ventes
        sales_category = ModuleCategory.query.filter_by(name="Ventes").first()
        
        quotes_module = BusinessModule(
            name="Devis Pro",
            description="""
            <p>Créez des devis professionnels personnalisés avec suivi de conversion et relances automatiques.</p>
            <h4>Fonctionnalités</h4>
            <ul>
                <li>Modèles de devis personnalisables</li>
                <li>Catalogue de produits/services intégré</li>
                <li>Calculs automatiques des taxes</li>
                <li>Suivi de conversion des devis</li>
                <li>Système de relance automatique</li>
                <li>Signature électronique</li>
            </ul>
            <p>Transformez plus facilement vos prospects en clients grâce à des devis professionnels et un suivi efficace.</p>
            """,
            short_description="Gestion de devis efficace et professionnelle",
            version="1.5.3",
            category_id=sales_category.id if sales_category else None,
            icon="fa-file-invoice-dollar",
            author="IA-Solutions",
            website="https://ia-solutions.com",
            is_official=True,
            is_featured=False,
            price=None,  # Gratuit
            currency="EUR",
            requirements="Compatible avec tous les abonnements",
            status="published",
            publish_date=datetime.utcnow() - timedelta(days=180),
            last_updated=datetime.utcnow() - timedelta(days=45),
            download_count=215
        )
        
        crm_module = BusinessModule(
            name="CRM Avancé",
            description="""
            <p>Un CRM complet pour gérer vos clients, prospects et opportunités commerciales.</p>
            <h4>Fonctionnalités</h4>
            <ul>
                <li>Gestion des contacts et entreprises</li>
                <li>Suivi des opportunités de vente</li>
                <li>Pipeline commercial personnalisable</li>
                <li>Historique des interactions client</li>
                <li>Intégration avec le module d'emails</li>
                <li>Rapports et tableaux de bord</li>
            </ul>
            <p>Améliorez la gestion de vos relations clients et augmentez vos ventes.</p>
            """,
            short_description="Gestion complète de la relation client",
            version="3.0.0",
            category_id=sales_category.id if sales_category else None,
            icon="fa-user-tie",
            author="IA-Solutions",
            website="https://ia-solutions.com",
            is_official=True,
            is_featured=True,
            price=29.99,
            currency="EUR",
            requirements="Nécessite un abonnement Pro ou supérieur",
            status="published",
            publish_date=datetime.utcnow() - timedelta(days=100),
            last_updated=datetime.utcnow() - timedelta(days=7),
            download_count=178
        )
        
        # Créer des modules de RH
        hr_category = ModuleCategory.query.filter_by(name="RH").first()
        
        hr_module = BusinessModule(
            name="Gestion RH Simplifiée",
            description="""
            <p>Module complet pour faciliter la gestion des ressources humaines de votre entreprise.</p>
            <h4>Fonctionnalités</h4>
            <ul>
                <li>Dossiers employés digitalisés</li>
                <li>Gestion des congés et absences</li>
                <li>Suivi du temps de travail</li>
                <li>Évaluations et objectifs</li>
                <li>Gestion des formations</li>
                <li>Organigramme dynamique</li>
            </ul>
            <p>Simplifiez vos processus RH et concentrez-vous sur le développement de vos talents.</p>
            """,
            short_description="Gestion complète des ressources humaines",
            version="2.1.0",
            category_id=hr_category.id if hr_category else None,
            icon="fa-id-card",
            author="HRSolutions",
            website="https://hrsolutions.io",
            is_official=False,
            is_featured=False,
            price=19.99,
            currency="EUR",
            requirements="Compatible avec tous les abonnements",
            status="published",
            publish_date=datetime.utcnow() - timedelta(days=150),
            last_updated=datetime.utcnow() - timedelta(days=20),
            download_count=67
        )
        
        # Ajouter tous les modules à la session
        for module in [accounting_module, cash_flow_module, budget_module, marketing_automation_module, 
                      social_media_module, quotes_module, crm_module, hr_module]:
            db.session.add(module)
        
        logger.info("Modules créés")
        db.session.flush()  # Pour obtenir les IDs
        
        # Créer des versions pour chaque module
        for module in BusinessModule.query.all():
            # Version actuelle
            current_version = ModuleVersion(
                module_id=module.id,
                version_number=module.version,
                release_notes="Version actuelle avec toutes les fonctionnalités",
                is_latest=True,
                created_at=datetime.utcnow() - timedelta(days=15)
            )
            db.session.add(current_version)
            
            # Version précédente
            if '.' in module.version:
                parts = module.version.split('.')
                if len(parts) >= 3 and int(parts[2]) > 0:
                    prev_version = parts.copy()
                    prev_version[2] = str(int(prev_version[2]) - 1)
                    prev_version = '.'.join(prev_version)
                    
                    old_version = ModuleVersion(
                        module_id=module.id,
                        version_number=prev_version,
                        release_notes="Version précédente avec corrections de bugs mineurs",
                        is_latest=False,
                        created_at=datetime.utcnow() - timedelta(days=45)
                    )
                    db.session.add(old_version)
                
                # Version plus ancienne
                if len(parts) >= 3 and int(parts[2]) > 1:
                    older_version = parts.copy()
                    older_version[2] = str(int(older_version[2]) - 2)
                    older_version = '.'.join(older_version)
                    
                    oldest_version = ModuleVersion(
                        module_id=module.id,
                        version_number=older_version,
                        release_notes="Version initiale avec fonctionnalités de base",
                        is_latest=False,
                        created_at=datetime.utcnow() - timedelta(days=90)
                    )
                    db.session.add(oldest_version)
        
        logger.info("Versions des modules créées")
        
        # Créer quelques avis utilisateurs (si des utilisateurs existent)
        users = User.query.limit(5).all()
        if users:
            ratings = [5, 4, 5, 3, 4, 5, 2, 4, 5]
            titles = [
                "Excellent module !",
                "Très satisfait",
                "Pratique et intuitif",
                "Quelques améliorations possibles",
                "Bon rapport qualité-prix",
                "Indispensable",
                "Des bugs à corriger",
                "Bonne solution",
                "Recommandé"
            ]
            comments = [
                "Ce module a révolutionné notre façon de travailler. Simple, efficace et puissant.",
                "Très bonne intégration avec le reste de l'application. Facile à prendre en main.",
                "Les fonctionnalités sont exactement ce dont nous avions besoin. Interface claire et intuitive.",
                "Globalement satisfait mais quelques fonctionnalités manquent encore.",
                "Pour ce prix, difficile de trouver mieux. Répond parfaitement à nos besoins.",
                "Nous utilisons ce module quotidiennement. Il est devenu indispensable pour notre entreprise.",
                "Le concept est bon mais il y a encore trop de bugs à corriger.",
                "Une solution efficace qui nous fait gagner beaucoup de temps.",
                "Je recommande vivement ce module à toutes les entreprises qui veulent optimiser ce processus."
            ]
            
            for module in BusinessModule.query.all():
                # Nombre aléatoire d'avis par module (1 à 3)
                num_reviews = min(len(users), 3)
                for i in range(num_reviews):
                    if i < len(users):
                        idx = (module.id + i) % len(ratings)
                        review = ModuleReview(
                            module_id=module.id,
                            user_id=users[i].id,
                            rating=ratings[idx],
                            title=titles[idx],
                            comment=comments[idx],
                            created_at=datetime.utcnow() - timedelta(days=i*5 + 1)
                        )
                        db.session.add(review)
            
            logger.info("Avis utilisateurs créés")
        
        db.session.commit()
        logger.info("Données du système de modules initialisées avec succès")

    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Erreur d'intégrité lors de l'initialisation des données: {str(e)}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'initialisation des données: {str(e)}")

if __name__ == "__main__":
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    
    with app.app_context():
        init_modules_data()