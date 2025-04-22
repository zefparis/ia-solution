"""
Blueprint pour la gestion du système de modules métier
"""
import os
import json
import logging
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, jsonify, session, flash, abort
from werkzeug.utils import secure_filename

from models import db, User
from models_modules import ModuleCategory, BusinessModule, ModuleVersion, ModuleReview, UserModuleInstallation
from language import get_text
from auth import login_required, get_user_info
from s3_storage import S3Storage

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

modules_bp = Blueprint('modules', __name__, url_prefix='/modules')

# Instance de S3Storage pour gérer les uploads d'icônes et bannières
s3_storage = S3Storage()

def get_translations():
    """
    Fonction d'aide pour les templates - encapsule get_text pour rester compatible
    avec le style de code utilisé dans les autres modules
    """
    def _(key, default=None):
        return get_text(key, default)
    return _

def get_user_id():
    """Récupère l'ID de l'utilisateur depuis la session"""
    if 'access_token' not in session:
        return None
    
    try:
        # Récupérer les informations utilisateur depuis le token
        user_info = get_user_info(session['access_token'])
        if not user_info or 'email' not in user_info:
            return None
            
        # Trouver l'utilisateur par email
        user = User.query.filter_by(email=user_info['email']).first()
        if user:
            return user.id
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'ID utilisateur: {str(e)}")
        return None

def init_app(app):
    """Initialiser le blueprint modules pour l'application Flask"""
    app.register_blueprint(modules_bp)
    logger.info("Blueprint des modules initialisé")
    
    # Créer les tables au démarrage
    with app.app_context():
        db.create_all()

@modules_bp.route('/')
def modules_home():
    """Page d'accueil du système de modules"""
    _ = get_translations()
    user_id = get_user_id()
    
    # Récupérer les catégories de modules
    categories = ModuleCategory.query.filter_by(parent_id=None).all()
    
    # Récupérer les modules les plus populaires
    popular_modules = BusinessModule.query.filter_by(status='published').order_by(BusinessModule.download_count.desc()).limit(6).all()
    
    # Récupérer les modules mis en avant
    featured_modules = BusinessModule.query.filter_by(is_featured=True, status='published').limit(4).all()
    
    # Si l'utilisateur est connecté, récupérer ses modules installés
    user_modules = []
    if user_id:
        user_modules = UserModuleInstallation.query.filter_by(user_id=user_id, status='active').all()
    
    return render_template('modules/index_test.html', 
                          categories=categories,
                          popular_modules=popular_modules,
                          featured_modules=featured_modules,
                          user_modules=user_modules,
                          _=_)

@modules_bp.route('/marketplace')
def modules_marketplace():
    """Page du marché de modules"""
    _ = get_translations()
    user_id = get_user_id()
    
    # Récupérer toutes les catégories
    categories = ModuleCategory.query.all()
    
    # Récupérer les modules filtrés par catégorie si spécifié
    category_id = request.args.get('category', None, type=int)
    
    query = BusinessModule.query.filter_by(status='published')
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    # Filtrer par critères supplémentaires
    is_free = request.args.get('free', None)
    if is_free == '1':
        query = query.filter(BusinessModule.price.is_(None) | (BusinessModule.price == 0))
    
    is_official = request.args.get('official', None)
    if is_official == '1':
        query = query.filter_by(is_official=True)
    
    # Tri
    sort_by = request.args.get('sort', 'popular')
    if sort_by == 'newest':
        query = query.order_by(BusinessModule.created_at.desc())
    elif sort_by == 'top_rated':
        # Tri plus complexe, nous utilisons une sous-requête pour calculer la note moyenne
        # (Simplifié pour l'exemple, idéalement on ferait une requête plus optimisée)
        modules = query.all()
        modules.sort(key=lambda m: m.average_rating, reverse=True)
    else:  # popular (default)
        query = query.order_by(BusinessModule.download_count.desc())
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    if sort_by == 'top_rated':
        # Cas spécial pour le tri par note moyenne
        modules = modules[(page-1)*per_page:page*per_page]
        has_next = len(modules) >= per_page
        has_prev = page > 1
    else:
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        modules = pagination.items
        has_next = pagination.has_next
        has_prev = pagination.has_prev
    
    return render_template('modules/marketplace_test.html',
                          modules=modules,
                          categories=categories,
                          current_category=category_id,
                          sort_by=sort_by,
                          is_free=is_free,
                          is_official=is_official,
                          page=page,
                          has_next=has_next,
                          has_prev=has_prev,
                          _=_)

@modules_bp.route('/module/<int:module_id>')
def module_details(module_id):
    """Page de détails d'un module"""
    _ = get_translations()
    user_id = get_user_id()
    
    module = BusinessModule.query.get_or_404(module_id)
    
    # Vérifier si l'utilisateur a installé ce module
    is_installed = False
    user_installation = None
    if user_id:
        user_installation = UserModuleInstallation.query.filter_by(
            user_id=user_id, 
            module_id=module_id,
            status='active'
        ).first()
        
        is_installed = user_installation is not None
    
    # Récupérer les versions du module
    versions = ModuleVersion.query.filter_by(module_id=module_id).order_by(ModuleVersion.created_at.desc()).all()
    
    # Récupérer les avis sur le module
    reviews = ModuleReview.query.filter_by(module_id=module_id).order_by(ModuleReview.created_at.desc()).all()
    
    # Trouver des modules similaires
    similar_modules = BusinessModule.query.filter(
        BusinessModule.category_id == module.category_id,
        BusinessModule.id != module.id,
        BusinessModule.status == 'published'
    ).limit(4).all()
    
    return render_template('modules/module_details.html',
                          module=module,
                          versions=versions,
                          reviews=reviews,
                          similar_modules=similar_modules,
                          is_installed=is_installed,
                          user_installation=user_installation,
                          _=_)

@modules_bp.route('/install/<int:module_id>', methods=['POST'])
@login_required
def install_module(module_id):
    """Installer un module pour l'utilisateur courant"""
    user_id = get_user_id()
    if not user_id:
        return jsonify({'success': False, 'message': 'Vous devez être connecté pour installer des modules'}), 401
    
    module = BusinessModule.query.get_or_404(module_id)
    
    # Vérifier si le module est déjà installé
    existing_installation = UserModuleInstallation.query.filter_by(
        user_id=user_id,
        module_id=module_id
    ).first()
    
    # Si une installation existe mais est désactivée, la réactiver
    if existing_installation and existing_installation.status != 'active':
        existing_installation.status = 'active'
        existing_installation.installation_date = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Module réactivé avec succès'})
    
    # Si le module est déjà installé et actif
    if existing_installation:
        return jsonify({'success': False, 'message': 'Ce module est déjà installé'})
    
    # Trouver la dernière version du module
    latest_version = ModuleVersion.query.filter_by(
        module_id=module_id,
        is_latest=True
    ).first()
    
    # Créer une nouvelle installation
    new_installation = UserModuleInstallation(
        user_id=user_id,
        module_id=module_id,
        version_id=latest_version.id if latest_version else None,
        installation_date=datetime.utcnow(),
        status='active'
    )
    
    try:
        db.session.add(new_installation)
        
        # Incrémenter le compteur de téléchargements
        module.download_count += 1
        
        db.session.commit()
        
        # Exécuter le script d'installation si présent
        if module.installation_script:
            # Pour l'instant, nous simulons l'exécution du script
            logger.info(f"Exécution du script d'installation pour le module {module.name}")
            # TODO: Implémenter la logique d'exécution du script
        
        return jsonify({'success': True, 'message': 'Module installé avec succès'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'installation du module: {str(e)}")
        return jsonify({'success': False, 'message': f"Erreur lors de l'installation: {str(e)}"}), 500

@modules_bp.route('/uninstall/<int:module_id>', methods=['POST'])
@login_required
def uninstall_module(module_id):
    """Désinstaller un module pour l'utilisateur courant"""
    user_id = get_user_id()
    if not user_id:
        return jsonify({'success': False, 'message': 'Vous devez être connecté pour désinstaller des modules'}), 401
    
    # Vérifier si le module est installé
    installation = UserModuleInstallation.query.filter_by(
        user_id=user_id,
        module_id=module_id,
        status='active'
    ).first()
    
    if not installation:
        return jsonify({'success': False, 'message': 'Ce module n\'est pas installé'}), 404
    
    try:
        # Marquer comme désinstallé plutôt que de supprimer l'enregistrement
        installation.status = 'uninstalled'
        
        db.session.commit()
        
        # Exécuter le script de désinstallation si présent
        module = BusinessModule.query.get(module_id)
        if module and module.uninstallation_script:
            # Pour l'instant, nous simulons l'exécution du script
            logger.info(f"Exécution du script de désinstallation pour le module {module.name}")
            # TODO: Implémenter la logique d'exécution du script
        
        return jsonify({'success': True, 'message': 'Module désinstallé avec succès'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la désinstallation du module: {str(e)}")
        return jsonify({'success': False, 'message': f"Erreur lors de la désinstallation: {str(e)}"}), 500

@modules_bp.route('/review/<int:module_id>', methods=['POST'])
@login_required
def add_review(module_id):
    """Ajouter un avis sur un module"""
    user_id = get_user_id()
    if not user_id:
        return jsonify({'success': False, 'message': 'Vous devez être connecté pour laisser un avis'}), 401
    
    # Vérifier si le module existe
    module = BusinessModule.query.get_or_404(module_id)
    
    # Vérifier si l'utilisateur a déjà laissé un avis
    existing_review = ModuleReview.query.filter_by(
        user_id=user_id,
        module_id=module_id
    ).first()
    
    # Récupérer les données du formulaire
    rating = request.form.get('rating', type=int)
    title = request.form.get('title')
    comment = request.form.get('comment')
    
    # Valider les données
    if not rating or rating < 1 or rating > 5:
        return jsonify({'success': False, 'message': 'La note doit être comprise entre 1 et 5'}), 400
    
    try:
        if existing_review:
            # Mettre à jour l'avis existant
            existing_review.rating = rating
            existing_review.title = title
            existing_review.comment = comment
            existing_review.updated_at = datetime.utcnow()
        else:
            # Créer un nouvel avis
            new_review = ModuleReview(
                user_id=user_id,
                module_id=module_id,
                rating=rating,
                title=title,
                comment=comment
            )
            db.session.add(new_review)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Avis ajouté avec succès',
            'average_rating': module.average_rating,
            'review_count': module.review_count
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'ajout de l'avis: {str(e)}")
        return jsonify({'success': False, 'message': f"Erreur lors de l'ajout de l'avis: {str(e)}"}), 500

@modules_bp.route('/my-modules')
@login_required
def my_modules():
    """Page des modules installés par l'utilisateur"""
    _ = get_translations()
    user_id = get_user_id()
    
    # Récupérer les modules installés
    installed_modules = UserModuleInstallation.query.filter_by(
        user_id=user_id,
        status='active'
    ).all()
    
    return render_template('modules/my_modules.html',
                          installed_modules=installed_modules,
                          _=_)

@modules_bp.route('/update/<int:module_id>/<int:version_id>', methods=['POST'])
@login_required
def update_module(module_id, version_id):
    """Mettre à jour un module vers une version spécifique"""
    user_id = get_user_id()
    
    # Vérifier si le module est installé
    installation = UserModuleInstallation.query.filter_by(
        user_id=user_id,
        module_id=module_id,
        status='active'
    ).first()
    
    if not installation:
        return jsonify({'success': False, 'message': 'Ce module n\'est pas installé'}), 404
    
    # Vérifier si la version existe
    version = ModuleVersion.query.get_or_404(version_id)
    if version.module_id != module_id:
        return jsonify({'success': False, 'message': 'Version invalide pour ce module'}), 400
    
    try:
        # Mettre à jour la version installée
        installation.version_id = version_id
        installation.installation_date = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Module mis à jour avec succès'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la mise à jour du module: {str(e)}")
        return jsonify({'success': False, 'message': f"Erreur lors de la mise à jour: {str(e)}"}), 500

# Routes administratives (nécessitent des droits admin)
@modules_bp.route('/admin')
@login_required
def admin_dashboard():
    """Tableau de bord administratif pour gérer les modules"""
    _ = get_translations()
    user_id = get_user_id()
    
    # Vérifier si l'utilisateur est administrateur
    user = User.query.get(user_id)
    if not user or not user.is_admin:
        flash(_('Vous n\'avez pas les droits d\'accès à cette page'), 'danger')
        return redirect(url_for('modules.modules_home'))
    
    # Récupérer les statistiques
    total_modules = BusinessModule.query.count()
    active_modules = BusinessModule.query.filter_by(status='published').count()
    total_categories = ModuleCategory.query.count()
    total_installations = UserModuleInstallation.query.filter_by(status='active').count()
    
    # Récupérer les modules récents
    recent_modules = BusinessModule.query.order_by(BusinessModule.created_at.desc()).limit(5).all()
    
    return render_template('modules/admin/dashboard.html',
                          total_modules=total_modules,
                          active_modules=active_modules,
                          total_categories=total_categories,
                          total_installations=total_installations,
                          recent_modules=recent_modules,
                          _=_)

@modules_bp.route('/admin/modules')
@login_required
def admin_modules():
    """Liste des modules pour l'administration"""
    _ = get_translations()
    user_id = get_user_id()
    
    # Vérifier si l'utilisateur est administrateur
    user = User.query.get(user_id)
    if not user or not user.is_admin:
        flash(_('Vous n\'avez pas les droits d\'accès à cette page'), 'danger')
        return redirect(url_for('modules.modules_home'))
    
    # Récupérer tous les modules avec filtrage
    status = request.args.get('status', 'all')
    category_id = request.args.get('category', None, type=int)
    
    query = BusinessModule.query
    
    if status != 'all':
        query = query.filter_by(status=status)
        
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    modules = pagination.items
    
    # Récupérer les catégories pour le filtre
    categories = ModuleCategory.query.all()
    
    return render_template('modules/admin/modules.html',
                          modules=modules,
                          pagination=pagination,
                          categories=categories,
                          current_status=status,
                          current_category=category_id,
                          _=_)

@modules_bp.route('/admin/module/new', methods=['GET', 'POST'])
@login_required
def admin_new_module():
    """Créer un nouveau module"""
    _ = get_translations()
    user_id = get_user_id()
    
    # Vérifier si l'utilisateur est administrateur
    user = User.query.get(user_id)
    if not user or not user.is_admin:
        flash(_('Vous n\'avez pas les droits d\'accès à cette page'), 'danger')
        return redirect(url_for('modules.modules_home'))
    
    # Récupérer les catégories pour le formulaire
    categories = ModuleCategory.query.all()
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        name = request.form.get('name')
        description = request.form.get('description')
        short_description = request.form.get('short_description')
        category_id = request.form.get('category_id', type=int)
        author = request.form.get('author')
        website = request.form.get('website')
        is_official = 'is_official' in request.form
        is_featured = 'is_featured' in request.form
        price = request.form.get('price', type=float)
        currency = request.form.get('currency', 'EUR')
        version = request.form.get('version', '1.0.0')
        requirements = request.form.get('requirements')
        installation_script = request.form.get('installation_script')
        uninstallation_script = request.form.get('uninstallation_script')
        
        # Valider les données requises
        if not name:
            flash(_('Le nom du module est requis'), 'danger')
            return render_template('modules/admin/module_form.html',
                                categories=categories,
                                form_data=request.form,
                                _=_)
        
        # Créer un nouveau module
        new_module = BusinessModule(
            name=name,
            description=description,
            short_description=short_description,
            category_id=category_id,
            author=author,
            website=website,
            is_official=is_official,
            is_featured=is_featured,
            price=price if price else None,
            currency=currency,
            version=version,
            requirements=requirements,
            installation_script=installation_script,
            uninstallation_script=uninstallation_script,
            status='draft'
        )
        
        # Gérer l'upload d'icône si présent
        if 'icon' in request.files and request.files['icon'].filename:
            icon_file = request.files['icon']
            try:
                icon_filename = secure_filename(f"module_icon_{datetime.now().strftime('%Y%m%d%H%M%S')}_{icon_file.filename}")
                icon_url = s3_storage.upload_file(icon_file, icon_filename, is_public=True)
                new_module.icon = icon_url
            except Exception as e:
                logger.error(f"Erreur lors de l'upload de l'icône: {str(e)}")
                flash(_('Erreur lors de l\'upload de l\'icône. Le module sera créé sans icône.'), 'warning')
        
        # Gérer l'upload de bannière si présent
        if 'banner_image' in request.files and request.files['banner_image'].filename:
            banner_file = request.files['banner_image']
            try:
                banner_filename = secure_filename(f"module_banner_{datetime.now().strftime('%Y%m%d%H%M%S')}_{banner_file.filename}")
                banner_url = s3_storage.upload_file(banner_file, banner_filename, is_public=True)
                new_module.banner_image = banner_url
            except Exception as e:
                logger.error(f"Erreur lors de l'upload de la bannière: {str(e)}")
                flash(_('Erreur lors de l\'upload de la bannière. Le module sera créé sans bannière.'), 'warning')
        
        try:
            db.session.add(new_module)
            db.session.flush()  # Pour obtenir l'ID du module
            
            # Créer la première version
            initial_version = ModuleVersion(
                module_id=new_module.id,
                version_number=version,
                release_notes=_('Version initiale'),
                installation_script=installation_script,
                is_latest=True
            )
            db.session.add(initial_version)
            
            db.session.commit()
            flash(_('Module créé avec succès'), 'success')
            return redirect(url_for('modules.admin_modules'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la création du module: {str(e)}")
            flash(_('Erreur lors de la création du module: {}').format(str(e)), 'danger')
    
    # GET request - afficher le formulaire
    return render_template('modules/admin/module_form.html',
                          categories=categories,
                          form_data={},
                          _=_)

# Routes supplémentaires admin pour éditer/supprimer des modules, gérer les catégories, etc.
# ...

# Route pour initialiser les données de démo
@modules_bp.route('/init-demo-data')
@login_required
def init_demo_data():
    """Initialiser des données de démo pour le système de modules"""
    user_id = get_user_id()
    
    # Vérifier si l'utilisateur est administrateur
    user = User.query.get(user_id)
    if not user or not user.is_admin:
        flash('Vous n\'avez pas les droits d\'accès à cette fonctionnalité', 'danger')
        return redirect(url_for('modules.modules_home'))
    
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
            existing = ModuleCategory.query.filter_by(name=category.name).first()
            if not existing:
                db.session.add(category)
        
        db.session.flush()  # Pour obtenir les IDs
        
        # Créer quelques modules de démo
        finance_cat = ModuleCategory.query.filter_by(name="Finance").first()
        marketing_cat = ModuleCategory.query.filter_by(name="Marketing").first()
        sales_cat = ModuleCategory.query.filter_by(name="Ventes").first()
        
        # Module de comptabilité avancée
        accounting_module = BusinessModule(
            name="Comptabilité Avancée",
            description="Module complet de comptabilité avancée avec gestion des bilans, comptes de résultat et liasses fiscales automatisées.",
            short_description="Gestion comptable complète pour PME",
            version="1.2.0",
            category_id=finance_cat.id if finance_cat else None,
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
            publish_date=datetime.utcnow(),
            download_count=127
        )
        
        # Module de marketing automation
        marketing_module = BusinessModule(
            name="Marketing Automation Pro",
            description="Automatisez vos campagnes marketing avec des workflows intelligents, segmentation avancée et analyses prédictives.",
            short_description="Automatisation marketing intelligente",
            version="2.0.1",
            category_id=marketing_cat.id if marketing_cat else None,
            icon="fa-robot",
            author="MarketingAI",
            website="https://marketingai.com",
            is_official=False,
            is_featured=True,
            price=24.99,
            currency="EUR",
            requirements="Compatible avec tous les abonnements",
            installation_script="# Installation simulée\nprint('Module de marketing automation installé')",
            uninstallation_script="# Désinstallation simulée\nprint('Module de marketing automation désinstallé')",
            status="published",
            publish_date=datetime.utcnow(),
            download_count=89
        )
        
        # Module de gestion de devis
        quotes_module = BusinessModule(
            name="Devis Pro",
            description="Créez des devis professionnels personnalisés avec suivi de conversion et relances automatiques.",
            short_description="Gestion de devis efficace et professionnelle",
            version="1.5.3",
            category_id=sales_cat.id if sales_cat else None,
            icon="fa-file-invoice-dollar",
            author="IA-Solutions",
            website="https://ia-solutions.com",
            is_official=True,
            is_featured=False,
            price=None,  # Gratuit
            currency="EUR",
            requirements="Compatible avec tous les abonnements",
            installation_script="# Installation simulée\nprint('Module de devis installé')",
            uninstallation_script="# Désinstallation simulée\nprint('Module de devis désinstallé')",
            status="published",
            publish_date=datetime.utcnow(),
            download_count=215
        )
        
        # Vérifier si les modules existent déjà
        for module in [accounting_module, marketing_module, quotes_module]:
            existing = BusinessModule.query.filter_by(name=module.name).first()
            if not existing:
                db.session.add(module)
        
        db.session.flush()  # Pour obtenir les IDs
        
        # Ajouter des versions pour chaque module
        for module in BusinessModule.query.all():
            # Vérifier si des versions existent déjà
            if ModuleVersion.query.filter_by(module_id=module.id).count() == 0:
                # Version actuelle
                current_version = ModuleVersion(
                    module_id=module.id,
                    version_number=module.version,
                    release_notes="Version actuelle avec toutes les fonctionnalités",
                    is_latest=True,
                    created_at=datetime.utcnow()
                )
                db.session.add(current_version)
                
                # Version précédente (si le numéro de version le permet)
                if '.' in module.version:
                    parts = module.version.split('.')
                    if len(parts) >= 3 and int(parts[2]) > 0:
                        prev_version = parts.copy()
                        prev_version[2] = str(int(prev_version[2]) - 1)
                        prev_version = '.'.join(prev_version)
                        
                        old_version = ModuleVersion(
                            module_id=module.id,
                            version_number=prev_version,
                            release_notes="Version précédente avec corrections de bugs",
                            is_latest=False,
                            created_at=datetime.utcnow() - timedelta(days=30)
                        )
                        db.session.add(old_version)
        
        db.session.commit()
        flash('Données de démo initialisées avec succès', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'initialisation des données de démo: {str(e)}")
        flash(f'Erreur lors de l\'initialisation des données de démo: {str(e)}', 'danger')
    
    return redirect(url_for('modules.modules_home'))