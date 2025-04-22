"""
Module de gestion des langues pour l'application
"""
import sys
from flask import session, request, g


def init_app(app):
    """Initialiser le système de gestion de langues pour l'application Flask"""
    
    @app.before_request
    def set_language():
        """Définir la langue avant chaque requête"""
        # Si l'utilisateur a explicitement défini une langue via le paramètre "lang"
        if request.args.get('lang'):
            lang = request.args.get('lang')
            if lang in ['fr', 'en']:
                session['lang'] = lang
        
        # Utiliser la langue de la session, ou par défaut le français
        g.lang = session.get('lang', 'fr')
    
    @app.context_processor
    def inject_language():
        """Injecter la langue et le module de traduction dans tous les templates"""
        return {
            'lang': getattr(g, 'lang', 'fr'),
            'language': sys.modules[__name__]  # Rendre le module language disponible dans les templates
        }


def get_text(key, default=None, lang=None):
    """
    Récupérer un texte dans la langue spécifiée
    
    Args:
        key (str): Clé du texte à récupérer
        default (str, optional): Valeur par défaut si la clé n'existe pas
        lang (str, optional): Code de langue (fr, en). Si None, utilise g.lang
        
    Returns:
        str: Texte traduit
    """
    if lang is None:
        from flask import g
        lang = getattr(g, 'lang', 'fr')
    
    # Si la clé existe dans le dictionnaire, retourne la traduction
    # Sinon, retourne la valeur par défaut si fournie, ou la clé elle-même
    translation = TRANSLATIONS.get(key, {}).get(lang)
    if translation is not None:
        return translation
    else:
        return default if default is not None else key


def get_current_lang():
    """
    Récupère la langue actuelle de l'application
    
    Returns:
        str: Code de langue (fr, en)
    """
    from flask import g
    return getattr(g, 'lang', 'fr')


def url_with_lang(endpoint, **kwargs):
    """
    Génère une URL pour un endpoint en préservant le paramètre de langue actuel.
    
    Args:
        endpoint (str): L'endpoint pour générer l'URL
        **kwargs: Arguments additionnels à passer à url_for
        
    Returns:
        str: URL avec le paramètre de langue préservé
    """
    from flask import url_for, g
    
    # Récupérer la langue actuelle
    lang = getattr(g, 'lang', 'fr')
    
    # Ajouter le paramètre de langue aux arguments
    if 'lang' not in kwargs:
        kwargs['lang'] = lang
        
    # Générer l'URL avec le paramètre de langue
    return url_for(endpoint, **kwargs)


# Dictionnaire de traductions
TRANSLATIONS = {
    # Navigation
    'nav.home': {
        'fr': 'Accueil',
        'en': 'Home'
    },
    'nav.dashboard': {
        'fr': 'Tableau principal',
        'en': 'Main Dashboard'
    },
    'nav.dashboard_main': {
        'fr': 'Tableau de bord',
        'en': 'Dashboard'
    },
    'nav.finance': {
        'fr': 'Tableau financier',
        'en': 'Financial Dashboard'
    },
    'nav.finance_section': {
        'fr': 'Finance',
        'en': 'Finance'
    },
    'nav.business_section': {
        'fr': 'Business',
        'en': 'Business'
    },
    'nav.modules_section': {
        'fr': 'Modules et Formation',
        'en': 'Modules & Training'
    },
    'nav.tools': {
        'fr': 'Outils',
        'en': 'Tools'
    },
    'nav.invoicing': {
        'fr': 'Facturation',
        'en': 'Invoicing'
    },
    'nav.marketing': {
        'fr': 'Marketing IA',
        'en': 'AI Marketing'
    },
    'nav.training': {
        'fr': 'Formation',
        'en': 'Training'
    },
    'nav.marketplace': {
        'fr': 'Marketplace API',
        'en': 'API Marketplace'
    },
    'nav.modules': {
        'fr': 'Mes modules',
        'en': 'My Modules'
    },
    'nav.modules_store': {
        'fr': 'Marketplace',
        'en': 'Marketplace'
    },
    'nav.my_modules': {
        'fr': 'Mes Modules',
        'en': 'My Modules'
    },
    'nav.ocr': {
        'fr': 'Scanner',
        'en': 'Scanner'
    },
    'nav.business': {
        'fr': 'Consultation',
        'en': 'Consultation'
    },
    'nav.business_tools': {
        'fr': 'Business',
        'en': 'Business'
    },
    'nav.business_reports': {
        'fr': 'Mes rapports',
        'en': 'My reports'
    },
    'nav.account': {
        'fr': 'Compte',
        'en': 'Account'
    },
    'nav.pricing': {
        'fr': 'Tarifs',
        'en': 'Pricing'
    },
    'nav.export': {
        'fr': 'Export',
        'en': 'Export'
    },
    'nav.profile': {
        'fr': 'Profil',
        'en': 'Profile'
    },
    'nav.subscription': {
        'fr': 'Abonnement',
        'en': 'Subscription'
    },
    
    # Calendrier éditorial
    'editorial_calendar': {
        'fr': 'Calendrier éditorial',
        'en': 'Editorial Calendar'
    },
    'calendar_statistics': {
        'fr': 'Statistiques du calendrier',
        'en': 'Calendar Statistics'
    },
    'generate_calendar': {
        'fr': 'Générer un calendrier',
        'en': 'Generate Calendar'
    },
    'export': {
        'fr': 'Exporter',
        'en': 'Export'
    },
    'total_content_items': {
        'fr': 'Total des contenus',
        'en': 'Total Content Items'
    },
    'email_campaigns': {
        'fr': 'Campagnes email',
        'en': 'Email Campaigns'
    },
    'social_posts': {
        'fr': 'Publications sociales',
        'en': 'Social Posts'
    },
    'blog_articles': {
        'fr': 'Articles de blog',
        'en': 'Blog Articles'
    },
    'ad_campaigns': {
        'fr': 'Campagnes publicitaires',
        'en': 'Ad Campaigns'
    },
    'most_active_platform': {
        'fr': 'Plateforme la plus active',
        'en': 'Most Active Platform'
    },
    'upcoming_content': {
        'fr': 'Contenus à venir',
        'en': 'Upcoming Content'
    },
    'view': {
        'fr': 'Voir',
        'en': 'View'
    },
    'no_upcoming_content': {
        'fr': 'Aucun contenu à venir dans votre calendrier.',
        'en': 'No upcoming content in your calendar.'
    },
    'generate_editorial_calendar': {
        'fr': 'Générer un calendrier éditorial',
        'en': 'Generate Editorial Calendar'
    },
    'business_sector': {
        'fr': 'Secteur d\'activité',
        'en': 'Business Sector'
    },
    'post_frequency': {
        'fr': 'Fréquence de publication',
        'en': 'Post Frequency'
    },
    'select_frequency': {
        'fr': 'Sélectionner une fréquence',
        'en': 'Select Frequency'
    },
    'daily': {
        'fr': 'Quotidien',
        'en': 'Daily'
    },
    'weekly': {
        'fr': 'Hebdomadaire',
        'en': 'Weekly'
    },
    'biweekly': {
        'fr': 'Bimensuel',
        'en': 'Biweekly'
    },
    'monthly': {
        'fr': 'Mensuel',
        'en': 'Monthly'
    },
    'custom': {
        'fr': 'Personnalisé',
        'en': 'Custom'
    },
    'start_date': {
        'fr': 'Date de début',
        'en': 'Start Date'
    },
    'end_date': {
        'fr': 'Date de fin',
        'en': 'End Date'
    },
    'platforms': {
        'fr': 'Plateformes',
        'en': 'Platforms'
    },
    'blog': {
        'fr': 'Blog',
        'en': 'Blog'
    },
    'email': {
        'fr': 'Email',
        'en': 'Email'
    },
    'key_topics': {
        'fr': 'Sujets clés',
        'en': 'Key Topics'
    },
    'topics_placeholder': {
        'fr': 'Saisissez vos sujets séparés par des virgules',
        'en': 'Enter your topics separated by commas'
    },
    'topics_help_text': {
        'fr': 'Ex: nouveaux produits, conseils pratiques, actualités du secteur',
        'en': 'Ex: new products, practical tips, industry news'
    },
    'additional_notes': {
        'fr': 'Notes additionnelles',
        'en': 'Additional Notes'
    },
    'notes_placeholder': {
        'fr': 'Toute information supplémentaire pour personnaliser votre calendrier',
        'en': 'Any additional information to customize your calendar'
    },
    'cancel': {
        'fr': 'Annuler',
        'en': 'Cancel'
    },
    'generate': {
        'fr': 'Générer',
        'en': 'Generate'
    },
    'content_details': {
        'fr': 'Détails du contenu',
        'en': 'Content Details'
    },
    'title': {
        'fr': 'Titre',
        'en': 'Title'
    },
    'description': {
        'fr': 'Description',
        'en': 'Description'
    },
    'date': {
        'fr': 'Date',
        'en': 'Date'
    },
    'time': {
        'fr': 'Heure',
        'en': 'Time'
    },
    'platform': {
        'fr': 'Plateforme',
        'en': 'Platform'
    },
    'delete': {
        'fr': 'Supprimer',
        'en': 'Delete'
    },
    'save': {
        'fr': 'Enregistrer',
        'en': 'Save'
    },
    'add_content': {
        'fr': 'Ajouter un contenu',
        'en': 'Add Content'
    },
    'add': {
        'fr': 'Ajouter',
        'en': 'Add'
    },
    'today': {
        'fr': 'Aujourd\'hui',
        'en': 'Today'
    },
    'month': {
        'fr': 'Mois',
        'en': 'Month'
    },
    'week': {
        'fr': 'Semaine',
        'en': 'Week'
    },
    'list': {
        'fr': 'Liste',
        'en': 'List'
    },
    'generating_calendar': {
        'fr': 'Génération en cours...',
        'en': 'Generating...'
    },
    'error_occurred': {
        'fr': 'Une erreur est survenue',
        'en': 'An error occurred'
    },
    'calendar_generation_error': {
        'fr': 'Erreur lors de la génération du calendrier',
        'en': 'Calendar generation error'
    },
    'content_update_error': {
        'fr': 'Erreur lors de la mise à jour du contenu',
        'en': 'Content update error'
    },
    'confirm_delete_content': {
        'fr': 'Êtes-vous sûr de vouloir supprimer ce contenu ?',
        'en': 'Are you sure you want to delete this content?'
    },
    'content_deletion_error': {
        'fr': 'Erreur lors de la suppression du contenu',
        'en': 'Content deletion error'
    },
    'content_addition_error': {
        'fr': 'Erreur lors de l\'ajout du contenu',
        'en': 'Content addition error'
    },
    'none': {
        'fr': 'Aucune',
        'en': 'None'
    },
    'nav.chat': {
        'fr': 'Discuter',
        'en': 'Chat'
    },
    'nav.business_consultation': {
        'fr': 'Consultation Business',
        'en': 'Business Consultation'
    },
    'Export': {
        'fr': 'Exportation',
        'en': 'Export'
    },
    'nav.legal': {
        'fr': 'Informations Légales',
        'en': 'Legal Information'
    },
    'nav.login': {
        'fr': 'Connexion',
        'en': 'Login'
    },
    'nav.register': {
        'fr': 'Inscription',
        'en': 'Register'
    },
    'nav.logout': {
        'fr': 'Déconnexion',
        'en': 'Logout'
    },
    'nav.account': {
        'fr': 'Mon Compte',
        'en': 'My Account'
    },
    'nav.subscription': {
        'fr': 'Abonnement',
        'en': 'Subscription'
    },
    
    # Boutons et actions communes
    'action.submit': {
        'fr': 'Soumettre',
        'en': 'Submit'
    },
    'action.cancel': {
        'fr': 'Annuler',
        'en': 'Cancel'
    },
    'action.save': {
        'fr': 'Enregistrer',
        'en': 'Save'
    },
    'action.edit': {
        'fr': 'Modifier',
        'en': 'Edit'
    },
    'action.delete': {
        'fr': 'Supprimer',
        'en': 'Delete'
    },
    'action.back': {
        'fr': 'Retour',
        'en': 'Back'
    },
    'navigation.back': {
        'fr': 'Retour',
        'en': 'Back'
    },
    'action.next': {
        'fr': 'Suivant',
        'en': 'Next'
    },
    'action.search': {
        'fr': 'Rechercher',
        'en': 'Search'
    },
    
    # Messages communs
    'msg.welcome': {
        'fr': 'Bienvenue sur IA-Solution',
        'en': 'Welcome to IA-Solution'
    },
    'msg.success': {
        'fr': 'Opération réussie',
        'en': 'Operation successful'
    },
    'msg.error': {
        'fr': 'Une erreur est survenue',
        'en': 'An error occurred'
    },
    'msg.confirm_delete': {
        'fr': 'Êtes-vous sûr de vouloir supprimer cet élément ?',
        'en': 'Are you sure you want to delete this item?'
    },
    
    # Page d'accueil
    'home.title': {
        'fr': 'IA-Solution - Assistant intelligent pour votre business',
        'en': 'IA-Solution - Intelligent Assistant for your business'
    },
    'home.subtitle': {
        'fr': 'Optimisez votre gestion financière et obtenez des conseils business personnalisés',
        'en': 'Optimize your financial management and get personalized business advice'
    },
    'home.get_started': {
        'fr': 'Commencer',
        'en': 'Get Started'
    },
    'home.platform_title': {
        'fr': 'IA-Solution, votre plateforme intelligente',
        'en': 'IA-Solution, your intelligent platform'
    },
    'home.platform_description': {
        'fr': 'La solution tout-en-un qui révolutionne la gestion de vos documents financiers, simplifie votre comptabilité, optimise votre marketing et vous guide vers les meilleures décisions stratégiques pour votre entreprise.',
        'en': 'The all-in-one solution that revolutionizes your financial document management, simplifies accounting, optimizes marketing, and guides you towards the best strategic decisions for your business.'
    },
    'home.new_cloud_files': {
        'fr': 'Nouveau : Gestion de fichiers cloud',
        'en': 'New: Cloud file management'
    },
    'home.feature1': {
        'fr': 'Numérisation intelligente de documents avec l\'IA',
        'en': 'Intelligent document scanning with AI'
    },
    'home.feature2': {
        'fr': 'Analyse automatique des dépenses et revenus',
        'en': 'Automatic expense and income analysis'
    },
    'home.feature3': {
        'fr': 'Rapports fiscaux personnalisés prêts à l\'emploi',
        'en': 'Custom tax reports ready to use'
    },
    'home.feature4': {
        'fr': 'Stockage sécurisé dans le cloud',
        'en': 'Secure cloud storage'
    },
    'home.start_free': {
        'fr': 'Commencer gratuitement',
        'en': 'Start for free'
    },
    'home.dashboard': {
        'fr': 'Mon tableau de bord',
        'en': 'My dashboard'
    },
    'home.manage_files': {
        'fr': 'Gérer mes fichiers',
        'en': 'Manage my files'
    },
    'home.how_it_works': {
        'fr': 'Comment ça marche ?',
        'en': 'How it works?'
    },
    'home.import_docs': {
        'fr': 'Importez vos documents',
        'en': 'Import your documents'
    },
    'home.import_docs_desc': {
        'fr': 'Capturez des photos de vos factures et reçus avec OCR ou importez vos fichiers.',
        'en': 'Capture photos of your invoices and receipts with OCR or import your files.'
    },
    'home.try': {
        'fr': 'Essayer',
        'en': 'Try it'
    },
    'home.advanced_ai': {
        'fr': 'IA avancée',
        'en': 'Advanced AI'
    },
    'home.advanced_ai_desc': {
        'fr': 'Notre IA analyse vos documents pour extraire montants, dates et types de dépenses.',
        'en': 'Our AI analyzes your documents to extract amounts, dates and expense types.'
    },
    'home.discover_ai': {
        'fr': 'Découvrir l\'IA',
        'en': 'Discover AI'
    },
    'home.dashboard_title': {
        'fr': 'Tableau de bord',
        'en': 'Dashboard'
    },
    'home.dashboard_desc': {
        'fr': 'Visualisez vos finances avec des graphiques et catégories personnalisables.',
        'en': 'Visualize your finances with customizable charts and categories.'
    },
    'home.stats': {
        'fr': 'Statistiques',
        'en': 'Statistics'
    },
    'home.reports_title': {
        'fr': 'Rapports fiscaux',
        'en': 'Tax reports'
    },
    'home.reports_desc': {
        'fr': 'Générez des rapports fiscaux et financiers pour vos déclarations d\'impôts.',
        'en': 'Generate tax and financial reports for your tax returns.'
    },
    'home.reports': {
        'fr': 'Rapports',
        'en': 'Reports'
    },
    'home.main_features_title': {
        'fr': 'Fonctionnalités principales',
        'en': 'Main Features'
    },
    'home.main_features_subtitle': {
        'fr': 'Découvrez tous les outils qui transformeront votre gestion d\'entreprise',
        'en': 'Discover all the tools that will transform your business management'
    },
    'home.all_features': {
        'fr': 'Toutes',
        'en': 'All'
    },
    'home.finance_category': {
        'fr': 'Finance',
        'en': 'Finance'
    },
    'home.business_category': {
        'fr': 'Business',
        'en': 'Business'
    },
    'home.modules_category': {
        'fr': 'Modules',
        'en': 'Modules'
    },
    'home.ai_assistant_title': {
        'fr': 'Assistant IA',
        'en': 'AI Assistant'
    },
    'home.ai_assistant_description': {
        'fr': 'Communiquez avec notre IA pour obtenir des informations, des conseils et de l\'aide.',
        'en': 'Communicate with our AI to get information, advice, and assistance.'
    },
    'home.document_scan_title': {
        'fr': 'Scanner OCR',
        'en': 'OCR Scanner'
    },
    'home.document_scan_description': {
        'fr': 'Numérisez et extrayez automatiquement les données de vos documents financiers.',
        'en': 'Scan and automatically extract data from your financial documents.'
    },
    'home.finance_dashboard_title': {
        'fr': 'Tableau Financier',
        'en': 'Financial Dashboard'
    },
    'home.finance_dashboard_description': {
        'fr': 'Visualisez et analysez vos données financières avec des graphiques interactifs.',
        'en': 'Visualize and analyze your financial data with interactive charts.'
    },
    'home.invoicing_title': {
        'fr': 'Facturation',
        'en': 'Invoicing'
    },
    'home.invoicing_description': {
        'fr': 'Créez des factures et des devis professionnels en quelques clics avec calculs automatiques.',
        'en': 'Create professional invoices and quotes in a few clicks with automatic calculations.'
    },
    'home.business_consultation_title': {
        'fr': 'Consultation Business',
        'en': 'Business Consultation'
    },
    'home.business_consultation_description': {
        'fr': 'Obtenez une analyse SWOT et des recommandations stratégiques personnalisées pour votre entreprise.',
        'en': 'Get a SWOT analysis and personalized strategic recommendations for your business.'
    },
    'home.marketing_title': {
        'fr': 'Marketing IA',
        'en': 'AI Marketing'
    },
    'home.marketing_description': {
        'fr': 'Générez des contenus marketing, planifiez vos campagnes et créez un calendrier éditorial.',
        'en': 'Generate marketing content, plan your campaigns, and create an editorial calendar.'
    },
    'home.process_analysis_title': {
        'fr': 'Analyse de Processus',
        'en': 'Process Analysis'
    },
    'home.process_analysis_description': {
        'fr': 'Optimisez vos processus métier avec une analyse détaillée et des recommandations personnalisées.',
        'en': 'Optimize your business processes with detailed analysis and personalized recommendations.'
    },
    'home.predictive_title': {
        'fr': 'Intelligence Prédictive',
        'en': 'Predictive Intelligence'
    },
    'home.predictive_description': {
        'fr': 'Prévoyez vos ventes, analysez le potentiel client et optimisez votre catalogue avec l\'IA.',
        'en': 'Forecast your sales, analyze customer potential, and optimize your catalog with AI.'
    },
    'home.training_title': {
        'fr': 'Formation Interactive',
        'en': 'Interactive Training'
    },
    'home.training_description': {
        'fr': 'Suivez des formations personnalisées, avec parcours adaptatifs et certification.',
        'en': 'Take personalized training courses with adaptive paths and certification.'
    },
    'home.marketplace_title': {
        'fr': 'Marketplace API',
        'en': 'API Marketplace'
    },
    'home.marketplace_description': {
        'fr': 'Accédez à des extensions, connecteurs et modèles d\'automatisation pour votre entreprise.',
        'en': 'Access extensions, connectors, and automation templates for your business.'
    },
    'home.modules_system_title': {
        'fr': 'Système de Modules',
        'en': 'Modules System'
    },
    'home.modules_system_description': {
        'fr': 'Installez des modules métier à la volée avec notes, avis et gestion des versions.',
        'en': 'Install business modules on the fly with ratings, reviews, and version management.'
    },
    'home.export_title': {
        'fr': 'Export Multi-formats',
        'en': 'Multi-format Export'
    },
    'home.export_description': {
        'fr': 'Exportez vos données dans différents formats (PDF, Excel, CSV, JSON) avec aperçu intégré.',
        'en': 'Export your data in different formats (PDF, Excel, CSV, JSON) with integrated preview.'
    },
    'home.try_now': {
        'fr': 'Essayer maintenant',
        'en': 'Try now'
    },
    # Section démo interactive
    'nav.demo': {
        'fr': 'Démonstration interactive',
        'en': 'Interactive Demo'
    },
    'home.interactive_demo_title': {
        'fr': 'Découvrez notre plateforme en action',
        'en': 'Discover our platform in action'
    },
    'home.interactive_demo_desc': {
        'fr': 'Explorez toutes les fonctionnalités à travers notre présentation interactive et animée. Visualisez comment IA-Solution peut transformer votre gestion documentaire et financière.',
        'en': 'Explore all features through our interactive and animated presentation. See how IA-Solution can transform your document and financial management.'
    },
    'home.launch_demo': {
        'fr': 'Lancer la démo',
        'en': 'Launch demo'
    },
    'home.english_version': {
        'fr': 'Version anglaise',
        'en': 'English version'
    },
    'home.testimonials': {
        'fr': 'Ce que nos utilisateurs disent',
        'en': 'What our users say'
    },
    'home.testimonial1': {
        'fr': '"IA-Solution a complètement transformé ma façon de gérer mes finances. La numérisation des factures est incroyablement précise et le classement automatique me fait gagner des heures chaque mois !"',
        'en': '"IA-Solution has completely transformed how I manage my finances. The invoice scanning is incredibly accurate and the automatic classification saves me hours every month!"'
    },
    'home.testimonial2': {
        'fr': '"L\'interface est intuitive et l\'IA est vraiment intelligente. J\'apprécie particulièrement les rapports fiscaux qui m\'ont fait économiser beaucoup de temps lors de ma déclaration d\'impôts."',
        'en': '"The interface is intuitive and the AI is truly intelligent. I particularly appreciate the tax reports which saved me a lot of time when filing my taxes."'
    },
    'home.testimonial3': {
        'fr': '"Le stockage sécurisé dans le cloud est un vrai plus, et j\'adore pouvoir discuter directement avec l\'assistant IA. Il comprend vraiment mes besoins et me donne des conseils personnalisés."',
        'en': '"The secure cloud storage is a real plus, and I love being able to chat directly with the AI assistant. It truly understands my needs and gives me personalized advice."'
    },
    'home.subscription_title': {
        'fr': 'Nos formules d\'abonnement',
        'en': 'Our subscription plans'
    },
    'home.business_need': {
        'fr': 'Vous avez un besoin spécifique pour votre entreprise ? Notre assistant IA peut vous aider à trouver des solutions adaptées à votre situation.',
        'en': 'Do you have a specific need for your business? Our AI assistant can help you find solutions tailored to your situation.'
    },
    'home.login_required': {
        'fr': 'Cette fonctionnalité nécessite une connexion à votre compte',
        'en': 'This feature requires logging into your account'
    },
    'home.business_consultation': {
        'fr': 'Consultation business personnalisée',
        'en': 'Personalized business consultation'
    },
    'home.subscription_subtitle': {
        'fr': 'Choisissez le plan qui correspond à vos besoins et évoluez à votre rythme',
        'en': 'Choose the plan that fits your needs and evolve at your own pace'
    },
    'home.free': {
        'fr': 'Gratuit',
        'en': 'Free'
    },
    'home.trial': {
        'fr': 'Essai',
        'en': 'Trial'
    },
    'home.days': {
        'fr': 'jours',
        'en': 'days'
    },
    'home.per_month': {
        'fr': 'par mois',
        'en': 'per month'
    },
    'home.storage': {
        'fr': 'Stockage',
        'en': 'Storage'
    },
    'home.scans_per_day': {
        'fr': 'scans par jour',
        'en': 'scans per day'
    },
    'home.unlimited_scans': {
        'fr': 'Scans illimités',
        'en': 'Unlimited scans'
    },
    'home.basic_ai': {
        'fr': 'Accès chat IA basique',
        'en': 'Basic AI chat access'
    },
    'home.advanced_ai_access': {
        'fr': 'Accès chat IA avancé',
        'en': 'Advanced AI chat access'
    },
    'home.premium_ai': {
        'fr': 'Accès chat IA premium',
        'en': 'Premium AI chat access'
    },
    'home.full_access': {
        'fr': 'Accès complet à toutes les fonctions',
        'en': 'Full access to all features'
    },
    'home.limited_support': {
        'fr': 'Support limité',
        'en': 'Limited support'
    },
    'home.email_support': {
        'fr': 'Support par email',
        'en': 'Email support'
    },
    'home.priority_support': {
        'fr': 'Support prioritaire',
        'en': 'Priority support'
    },
    'home.dedicated_support': {
        'fr': 'Support dédié 24/7',
        'en': '24/7 dedicated support'
    },
    'home.tax_reports': {
        'fr': 'Rapports fiscaux',
        'en': 'Tax reports'
    },
    'home.advanced_tax_reports': {
        'fr': 'Rapports fiscaux avancés',
        'en': 'Advanced tax reports'
    },
    'home.custom_tax_reports': {
        'fr': 'Rapports fiscaux personnalisés',
        'en': 'Custom tax reports'
    },
    'home.popular': {
        'fr': 'Populaire',
        'en': 'Popular'
    },
    'home.choose': {
        'fr': 'Choisir',
        'en': 'Choose'
    },
    'home.sign_up': {
        'fr': 'S\'inscrire',
        'en': 'Sign up'
    },
    
    # Tableau de bord
    'dashboard.title': {
        'fr': 'Tableau de bord',
        'en': 'Dashboard'
    },
    'dashboard.summary': {
        'fr': 'Résumé',
        'en': 'Summary'
    },
    'dashboard.income': {
        'fr': 'Revenus',
        'en': 'Income'
    },
    'dashboard.expenses': {
        'fr': 'Dépenses',
        'en': 'Expenses'
    },
    'dashboard.balance': {
        'fr': 'Solde',
        'en': 'Balance'
    },
    'dashboard.recent_transactions': {
        'fr': 'Transactions récentes',
        'en': 'Recent Transactions'
    },
    'dashboard.cashflow': {
        'fr': 'Flux de trésorerie',
        'en': 'Cash Flow'
    },
    'dashboard.predictions': {
        'fr': 'Prédictions',
        'en': 'Predictions'
    },
    'dashboard.welcome': {
        'fr': 'Bienvenue',
        'en': 'Welcome'
    },
    'dashboard.monthly_evolution': {
        'fr': 'Évolution mensuelle',
        'en': 'Monthly Evolution'
    },
    'dashboard.category_breakdown': {
        'fr': 'Répartition par catégorie',
        'en': 'Category Breakdown'
    },
    'dashboard.predicted_income': {
        'fr': 'Revenus prévus',
        'en': 'Predicted Income'
    },
    'dashboard.predicted_expenses': {
        'fr': 'Dépenses prévues',
        'en': 'Predicted Expenses'
    },
    'dashboard.predicted_balance': {
        'fr': 'Solde prévu',
        'en': 'Predicted Balance'
    },
    'dashboard.months': {
        'fr': 'mois',
        'en': 'months'
    },
    'dashboard.view_all': {
        'fr': 'Voir tout',
        'en': 'View all'
    },
    'dashboard.settings': {
        'fr': 'Paramètres du tableau de bord',
        'en': 'Dashboard Settings'
    },
    'dashboard.data_range': {
        'fr': 'Période de données',
        'en': 'Data Range'
    },
    'dashboard.predictions_range': {
        'fr': 'Période de prévisions',
        'en': 'Predictions Range'
    },
    'dashboard.show_balance': {
        'fr': 'Afficher le solde',
        'en': 'Show Balance'
    },
    'dashboard.show_monthly_trends': {
        'fr': 'Afficher les tendances mensuelles',
        'en': 'Show Monthly Trends'
    },
    'dashboard.show_category_breakdown': {
        'fr': 'Afficher la répartition par catégorie',
        'en': 'Show Category Breakdown'
    },
    'dashboard.show_predictions': {
        'fr': 'Afficher les prévisions',
        'en': 'Show Predictions'
    },
    'dashboard.show_transactions': {
        'fr': 'Afficher les transactions récentes',
        'en': 'Show Recent Transactions'
    },
    'dashboard.show_business_reports': {
        'fr': 'Afficher les rapports business',
        'en': 'Show Business Reports'
    },
    'dashboard.save_settings': {
        'fr': 'Enregistrer',
        'en': 'Save Settings'
    },
    'invoicing.amount_invoiced': {
        'fr': 'Montant facturé cette année',
        'en': 'Amount invoiced this year'
    },
    'invoicing.documents_issued': {
        'fr': 'Documents émis',
        'en': 'Documents issued'
    },
    'business.recent_reports': {
        'fr': 'Rapports business récents',
        'en': 'Recent Business Reports'
    },
    'business.new_consultation': {
        'fr': 'Nouvelle consultation',
        'en': 'New Consultation'
    },
    'business.view_report': {
        'fr': 'Voir le rapport',
        'en': 'View Report'
    },
    'business.consultation': {
        'fr': 'Consultation Business',
        'en': 'Business Consultation'
    },
    'business.ai_ready': {
        'fr': 'Notre assistant IA est prêt à vous aider avec votre entreprise',
        'en': 'Our AI assistant is ready to help you with your business'
    },
    'business.login_required': {
        'fr': 'Connexion requise',
        'en': 'Login required'
    },
    'business.login_message': {
        'fr': 'Pour accéder à notre consultant IA business et bénéficier de ses conseils personnalisés, veuillez vous connecter ou créer un compte.',
        'en': 'To access our business AI consultant and benefit from its personalized advice, please log in or create an account.'
    },
    'business.can_help_with': {
        'fr': 'Notre consultant IA peut vous aider à :',
        'en': 'Our AI consultant can help you with:'
    },
    'business.market_analysis': {
        'fr': 'Analyser votre marché et votre concurrence',
        'en': 'Analyzing your market and competition'
    },
    'business.strengths_weaknesses': {
        'fr': 'Identifier vos forces et faiblesses',
        'en': 'Identifying your strengths and weaknesses'
    },
    'business.growth_opportunities': {
        'fr': 'Trouver des opportunités de croissance',
        'en': 'Finding growth opportunities'
    },
    'business.strategy': {
        'fr': 'Élaborer une stratégie adaptée',
        'en': 'Developing an adapted strategy'
    },
    'business.advantages': {
        'fr': 'Avantages :',
        'en': 'Advantages:'
    },
    'business.quick_consultation': {
        'fr': 'Consultation rapide et personnalisée',
        'en': 'Quick and personalized consultation'
    },
    'business.best_practices': {
        'fr': 'Recommandations basées sur les meilleures pratiques',
        'en': 'Recommendations based on best practices'
    },
    'business.precise_analysis': {
        'fr': 'Analyses sectorielles précises',
        'en': 'Precise industry analysis'
    },
    'business.available_24_7': {
        'fr': 'Disponible 24/7 pour vous assister',
        'en': 'Available 24/7 to assist you'
    },
    'general.back_to_home': {
        'fr': 'Retour à l\'accueil',
        'en': 'Back to home'
    },
    'chat.description': {
        'fr': 'Discutez avec Benji, votre assistant IA personnel',
        'en': 'Chat with Benji, your personal AI assistant'
    },
    'finance.add_transaction.description': {
        'fr': 'Ajoutez une nouvelle transaction à votre historique financier',
        'en': 'Add a new transaction to your financial history'
    },
    'finance.tax_report.description': {
        'fr': 'Générez un rapport fiscal pour une période donnée',
        'en': 'Generate a tax report for a given period'
    },
    'finance.categories.description': {
        'fr': 'Gérez les catégories de transactions pour mieux organiser vos finances',
        'en': 'Manage transaction categories to better organize your finances'
    },
    'invoicing.create_invoice': {
        'fr': 'Créer une facture',
        'en': 'Create Invoice'
    },
    'invoicing.create_invoice_desc': {
        'fr': 'Créez des factures professionnelles pour vos clients',
        'en': 'Create professional invoices for your clients'
    },
    'invoicing.create_quote': {
        'fr': 'Créer un devis',
        'en': 'Create Quote'
    },
    'invoicing.create_quote_desc': {
        'fr': 'Préparez des devis détaillés pour vos prospects',
        'en': 'Prepare detailed quotes for your prospects'
    },
    # Formulaires de facturation
    'invoicing.general_info': {
        'fr': 'Informations générales',
        'en': 'General Information'
    },
    'invoicing.company_info': {
        'fr': 'Informations de l\'entreprise',
        'en': 'Company Information'
    },
    'invoicing.company_settings': {
        'fr': 'Paramètres de l\'entreprise',
        'en': 'Company Settings'
    },
    'invoicing.back_to_invoicing': {
        'fr': 'Retour à la facturation',
        'en': 'Back to Invoicing'
    },
    'invoicing.general_information': {
        'fr': 'Informations générales',
        'en': 'General Information'
    },
    'invoicing.select_client': {
        'fr': 'Sélectionner un client',
        'en': 'Select a client'
    },
    'invoicing.issue_date': {
        'fr': 'Date d\'émission',
        'en': 'Issue Date'
    },
    'invoicing.due_date': {
        'fr': 'Date d\'échéance',
        'en': 'Due Date'
    },
    'invoicing.expiry_date': {
        'fr': 'Date de validité',
        'en': 'Expiry Date'
    },
    'invoicing.invoice_items': {
        'fr': 'Éléments de la facture',
        'en': 'Invoice Items'
    },
    'invoicing.quote_items': {
        'fr': 'Éléments du devis',
        'en': 'Quote Items'
    },
    'invoicing.description': {
        'fr': 'Description',
        'en': 'Description'
    },
    'invoicing.unit_price': {
        'fr': 'Prix unitaire',
        'en': 'Unit Price'
    },
    'invoicing.quantity': {
        'fr': 'Quantité',
        'en': 'Quantity'
    },
    'invoicing.tax': {
        'fr': 'TVA (%)',
        'en': 'VAT (%)'
    },
    'invoicing.amount': {
        'fr': 'Montant',
        'en': 'Amount'
    },
    'invoicing.add_line': {
        'fr': 'Ajouter une ligne',
        'en': 'Add Line'
    },
    'invoicing.subtotal': {
        'fr': 'Sous-total',
        'en': 'Subtotal'
    },
    'invoicing.tax_amount': {
        'fr': 'Montant TVA',
        'en': 'Tax Amount'
    },
    'invoicing.total': {
        'fr': 'Total',
        'en': 'Total'
    },
    'invoicing.notes': {
        'fr': 'Notes (visibles sur la facture)',
        'en': 'Notes (visible on invoice)'
    },
    'invoicing.terms': {
        'fr': 'Conditions',
        'en': 'Terms'
    },
    'invoicing.payment_info': {
        'fr': 'Informations de paiement',
        'en': 'Payment Information'
    },
    'invoicing.back_to_invoices': {
        'fr': 'Retour aux factures',
        'en': 'Back to Invoices'
    },
    'invoicing.back_to_quotes': {
        'fr': 'Retour aux devis',
        'en': 'Back to Quotes'
    },
    'invoicing.create_invoice_submit': {
        'fr': 'Créer la facture',
        'en': 'Create Invoice'
    },
    'invoicing.create_quote_submit': {
        'fr': 'Créer le devis',
        'en': 'Create Quote'
    },
    'invoicing.manage_clients': {
        'fr': 'Gérer les clients',
        'en': 'Manage Clients'
    },
    'invoicing.manage_clients_desc': {
        'fr': 'Gérez votre base de clients et leurs informations',
        'en': 'Manage your client database and their information'
    },
    'invoicing.manage_products': {
        'fr': 'Gérer les produits',
        'en': 'Manage Products'
    },
    'invoicing.manage_products_desc': {
        'fr': 'Gérez votre catalogue de produits et services',
        'en': 'Manage your catalog of products and services'
    },
    
    # Finance
    'finance.title': {
        'fr': 'Gestion Financière',
        'en': 'Financial Management'
    },
    'finance.transactions': {
        'fr': 'Transactions',
        'en': 'Transactions'
    },
    'finance.categories': {
        'fr': 'Catégories',
        'en': 'Categories'
    },
    'finance.reports': {
        'fr': 'Rapports',
        'en': 'Reports'
    },
    'finance.tax': {
        'fr': 'Fiscalité',
        'en': 'Tax'
    },
    
    # Facturation - Section Entreprise
    'invoicing.address': {
        'fr': 'Adresse',
        'en': 'Address'
    },
    'invoicing.bank_details': {
        'fr': 'Coordonnées bancaires',
        'en': 'Bank Details'
    },
    'invoicing.company_logo': {
        'fr': 'Logo de l\'entreprise',
        'en': 'Company Logo'
    },
    'invoicing.current_logo': {
        'fr': 'Logo actuel',
        'en': 'Current Logo'
    },
    'invoicing.upload_logo': {
        'fr': 'Télécharger un logo',
        'en': 'Upload Logo'
    },
    'invoicing.supported_formats': {
        'fr': 'Formats supportés : PNG, JPG, JPEG, GIF, SVG. Taille recommandée : 300x100 pixels.',
        'en': 'Supported formats: PNG, JPG, JPEG, GIF, SVG. Recommended size: 300x100 pixels.'
    },
    'invoicing.preview': {
        'fr': 'Prévisualisation',
        'en': 'Preview'
    },
    'invoicing.preview_info': {
        'fr': 'Ces informations apparaîtront sur vos factures et devis. Veillez à fournir des informations correctes et à jour.',
        'en': 'This information will appear on your invoices and quotes. Please provide accurate and up-to-date information.'
    },
    'invoicing.changes_note': {
        'fr': 'Note : Les modifications apportées n\'affecteront pas les factures et devis déjà créés.',
        'en': 'Note: Changes made will not affect existing invoices and quotes.'
    },
    'invoicing.save_changes': {
        'fr': 'Enregistrer les modifications',
        'en': 'Save Changes'
    },
    
    # Facturation - Champs formulaire entreprise
    'invoicing.company_name': {
        'fr': 'Nom / Raison sociale',
        'en': 'Company Name / Business Name'
    },
    'invoicing.company_email': {
        'fr': 'Email',
        'en': 'Email'
    },
    'invoicing.company_phone': {
        'fr': 'Téléphone',
        'en': 'Phone'
    },
    'invoicing.company_website': {
        'fr': 'Site web',
        'en': 'Website'
    },
    'invoicing.registration_number': {
        'fr': 'Numéro SIRET',
        'en': 'Registration Number'
    },
    'invoicing.tax_id': {
        'fr': 'Numéro de TVA',
        'en': 'VAT Number'
    },
    'invoicing.address_line': {
        'fr': 'Adresse',
        'en': 'Address'
    },
    'invoicing.postal_code': {
        'fr': 'Code postal',
        'en': 'Postal Code'
    },
    'invoicing.city': {
        'fr': 'Ville',
        'en': 'City'
    },
    'invoicing.country': {
        'fr': 'Pays',
        'en': 'Country'
    },
    'invoicing.bank_name': {
        'fr': 'Nom de la banque',
        'en': 'Bank Name'
    },
    'invoicing.account_number': {
        'fr': 'Numéro de compte',
        'en': 'Account Number'
    },
    'invoicing.iban': {
        'fr': 'IBAN',
        'en': 'IBAN'
    },
    'invoicing.bic_swift': {
        'fr': 'BIC/SWIFT',
        'en': 'BIC/SWIFT'
    },
    
    # Facturation - Général
    'invoicing.title': {
        'fr': 'Facturation',
        'en': 'Invoicing'
    },
    'invoicing.invoices': {
        'fr': 'Factures',
        'en': 'Invoices'
    },
    'invoicing.quotes': {
        'fr': 'Devis',
        'en': 'Quotes'
    },
    'invoicing.clients': {
        'fr': 'Clients',
        'en': 'Clients'
    },
    'invoicing.products': {
        'fr': 'Produits et Services',
        'en': 'Products and Services'
    },
    
    # Marketing IA
    'marketing.title': {
        'fr': 'Marketing IA',
        'en': 'AI Marketing'
    },
    'marketing.dashboard': {
        'fr': 'Tableau de bord Marketing',
        'en': 'Marketing Dashboard'
    },
    'marketing.campaigns': {
        'fr': 'Campagnes',
        'en': 'Campaigns'
    },
    'marketing.content_generator': {
        'fr': 'Générateur de contenu',
        'en': 'Content Generator'
    },
    'marketing.email': {
        'fr': 'Emails',
        'en': 'Emails'
    },
    'marketing.social': {
        'fr': 'Réseaux Sociaux',
        'en': 'Social Media'
    },
    'marketing.influencer': {
        'fr': 'Influenceurs',
        'en': 'Influencers'
    },
    'marketing.analytics': {
        'fr': 'Analytiques',
        'en': 'Analytics'
    },
    'campaign_created_success': {
        'fr': 'Campagne créée avec succès',
        'en': 'Campaign created successfully'
    },
    'campaign_creation_error': {
        'fr': 'Erreur lors de la création de la campagne',
        'en': 'Error creating campaign'
    },
    'campaign_updated_success': {
        'fr': 'Campagne mise à jour avec succès',
        'en': 'Campaign updated successfully'
    },
    'campaign_update_error': {
        'fr': 'Erreur lors de la mise à jour de la campagne',
        'en': 'Error updating campaign'
    },
    'campaign_deleted_success': {
        'fr': 'Campagne supprimée avec succès',
        'en': 'Campaign deleted successfully'
    },
    'campaign_deletion_error': {
        'fr': 'Erreur lors de la suppression de la campagne',
        'en': 'Error deleting campaign'
    },
    'campaign_type_mismatch': {
        'fr': 'Type de campagne incompatible',
        'en': 'Campaign type mismatch'
    },
    'email_content_created_success': {
        'fr': 'Contenu email créé avec succès',
        'en': 'Email content created successfully'
    },
    'email_content_creation_error': {
        'fr': 'Erreur lors de la création du contenu email',
        'en': 'Error creating email content'
    },
    
    # OCR
    'ocr.title': {
        'fr': 'Numérisation de documents',
        'en': 'Document Scanning'
    },
    'ocr.heading': {
        'fr': 'Scanner vos documents',
        'en': 'Scan Your Documents'
    },
    'ocr.subtitle': {
        'fr': 'Capturez une image ou importez un document pour extraire le texte et le traiter',
        'en': 'Capture an image or import a document to extract and process text'
    },
    'ocr.camera': {
        'fr': 'Caméra',
        'en': 'Camera'
    },
    'ocr.upload_image': {
        'fr': 'Importer une image',
        'en': 'Upload an image'
    },
    'ocr.document': {
        'fr': 'PDF/Word',
        'en': 'PDF/Word'
    },
    'ocr.capture': {
        'fr': 'Capturer',
        'en': 'Capture'
    },
    'ocr.switch_camera': {
        'fr': 'Changer de caméra',
        'en': 'Switch camera'
    },
    'ocr.select_image': {
        'fr': 'Sélectionnez une image contenant du texte',
        'en': 'Select an image containing text'
    },
    'ocr.supported_formats': {
        'fr': 'Formats supportés: JPG, PNG, GIF, BMP',
        'en': 'Supported formats: JPG, PNG, GIF, BMP'
    },
    'ocr.extract_text': {
        'fr': 'Extraire le texte',
        'en': 'Extract text'
    },
    'ocr.select_document': {
        'fr': 'Sélectionnez un document PDF ou Word',
        'en': 'Select a PDF or Word document'
    },
    'ocr.supported_doc_formats': {
        'fr': 'Formats supportés: PDF (.pdf), Microsoft Word (.docx)',
        'en': 'Supported formats: PDF (.pdf), Microsoft Word (.docx)'
    },
    'ocr.doc_name': {
        'fr': 'Nom du document',
        'en': 'Document name'
    },
    'ocr.doc_details': {
        'fr': 'Type: PDF - Taille: 1.2 MB',
        'en': 'Type: PDF - Size: 1.2 MB'
    },
    'ocr.clear': {
        'fr': 'Effacer',
        'en': 'Clear'
    },
    'ocr.metadata': {
        'fr': 'Métadonnées du document',
        'en': 'Document metadata'
    },
    'ocr.processing': {
        'fr': 'Extraction du texte en cours...',
        'en': 'Extracting text...'
    },
    'ocr.extracted_text': {
        'fr': 'Texte extrait',
        'en': 'Extracted text'
    },
    'ocr.confidence': {
        'fr': 'Confiance',
        'en': 'Confidence'
    },
    'ocr.title_placeholder': {
        'fr': 'Titre (optionnel)',
        'en': 'Title (optional)'
    },
    'ocr.text_placeholder': {
        'fr': 'Le texte extrait apparaîtra ici',
        'en': 'Extracted text will appear here'
    },
    'ocr.save': {
        'fr': 'Sauvegarder',
        'en': 'Save'
    },
    'ocr.send_to_chat': {
        'fr': 'Envoyer à Benji',
        'en': 'Send to Benji'
    },
    'ocr.saved_texts': {
        'fr': 'Textes sauvegardés',
        'en': 'Saved texts'
    },
    'ocr.no_saved_texts': {
        'fr': 'Aucun texte sauvegardé pour le moment.',
        'en': 'No saved texts yet.'
    },
    'ocr.confirm_delete': {
        'fr': 'Confirmer la suppression',
        'en': 'Confirm deletion'
    },
    'ocr.delete_confirmation': {
        'fr': 'Êtes-vous sûr de vouloir supprimer ce texte ? Cette action est irréversible.',
        'en': 'Are you sure you want to delete this text? This action cannot be undone.'
    },
    'ocr.cancel': {
        'fr': 'Annuler',
        'en': 'Cancel'
    },
    'ocr.delete': {
        'fr': 'Supprimer',
        'en': 'Delete'
    },
    'ocr.scan_document': {
        'fr': 'Scanner un document',
        'en': 'Scan a document'
    },
    'ocr.browse_files': {
        'fr': 'Parcourir les fichiers',
        'en': 'Browse Files'
    },
    
    # Chat
    'chat.title': {
        'fr': 'Discussion avec l\'assistant',
        'en': 'Chat with Assistant'
    },
    'chat.header': {
        'fr': 'Discutez avec Benji',
        'en': 'Chat with Benji'
    },
    'chat.assistant_name': {
        'fr': 'Assistant Intelligent',
        'en': 'Intelligent Assistant'
    },
    'chat.placeholder': {
        'fr': 'Message à Benji...',
        'en': 'Message to Benji...'
    },
    'chat.send': {
        'fr': 'Envoyer',
        'en': 'Send'
    },
    'chat.clear': {
        'fr': 'Effacer',
        'en': 'Clear'
    },
    'chat.voice_note': {
        'fr': 'Note: Vous pouvez activer la synthèse vocale pour les réponses et utiliser le microphone pour parler à l\'assistant.',
        'en': 'Note: You can enable voice synthesis for responses and use the microphone to speak to the assistant.'
    },
    'chat.listening': {
        'fr': 'En écoute...',
        'en': 'Listening...'
    },
    'chat.thinking': {
        'fr': 'Benji réfléchit...',
        'en': 'Benji is thinking...'
    },
    'chat.business_consultation': {
        'fr': 'Consultation Business',
        'en': 'Business Consultation'
    },
    'chat.business_description': {
        'fr': 'Obtenez une analyse SWOT et des recommandations stratégiques personnalisées pour votre entreprise.',
        'en': 'Get a personalized SWOT analysis and strategic recommendations for your business.'
    },
    'chat.start_analysis': {
        'fr': 'Démarrer l\'analyse',
        'en': 'Start Analysis'
    },
    'chat.business_type_general': {
        'fr': 'Tout type d\'entreprise',
        'en': 'Any type of business'
    },
    'chat.business_type_tech': {
        'fr': 'Entreprise technologique',
        'en': 'Technology company'
    },
    'chat.business_type_retail': {
        'fr': 'Commerce de détail',
        'en': 'Retail business'
    },
    'chat.business_type_service': {
        'fr': 'Entreprise de services',
        'en': 'Service business'
    },
    'chat.business_type_manufacturing': {
        'fr': 'Industrie/Production',
        'en': 'Manufacturing/Production'
    },
    
    # Business Consultation
    'business.title': {
        'fr': 'Consultation Business',
        'en': 'Business Consultation'
    },
    'business.description': {
        'fr': 'Obtenez des conseils personnalisés pour votre entreprise',
        'en': 'Get personalized advice for your business'
    },
    'business.company_name': {
        'fr': 'Nom de l\'entreprise',
        'en': 'Company Name'
    },
    'business.sector': {
        'fr': 'Secteur d\'activité',
        'en': 'Business Sector'
    },
    'business.employees': {
        'fr': 'Nombre d\'employés',
        'en': 'Number of Employees'
    },
    'business.revenue': {
        'fr': 'Chiffre d\'affaires annuel',
        'en': 'Annual Revenue'
    },
    'business.challenges': {
        'fr': 'Défis actuels',
        'en': 'Current Challenges'
    },
    
    # Compte utilisateur
    'account.title': {
        'fr': 'Mon Compte',
        'en': 'My Account'
    },
    'account.profile': {
        'fr': 'Profil',
        'en': 'Profile'
    },
    'account.settings': {
        'fr': 'Paramètres',
        'en': 'Settings'
    },
    'account.security': {
        'fr': 'Sécurité',
        'en': 'Security'
    },
    'account.subscription': {
        'fr': 'Abonnement',
        'en': 'Subscription'
    },
    'account.billing': {
        'fr': 'Facturation',
        'en': 'Billing'
    },
    
    # Abonnement
    'subscription.title': {
        'fr': 'Gestion de l\'abonnement',
        'en': 'Subscription Management'
    },
    'subscription.current_plan': {
        'fr': 'Plan actuel',
        'en': 'Current Plan'
    },
    'subscription.upgrade': {
        'fr': 'Mettre à niveau',
        'en': 'Upgrade'
    },
    'subscription.cancel': {
        'fr': 'Annuler l\'abonnement',
        'en': 'Cancel Subscription'
    },
    'subscription.history': {
        'fr': 'Historique de paiement',
        'en': 'Payment History'
    },
    
    # Authentification
    'auth.login': {
        'fr': 'Connexion',
        'en': 'Login'
    },
    'auth.register': {
        'fr': 'Créer un compte',
        'en': 'Create Account'
    },
    'auth.forgot_password': {
        'fr': 'Mot de passe oublié',
        'en': 'Forgot Password'
    },
    'auth.reset_password': {
        'fr': 'Réinitialiser le mot de passe',
        'en': 'Reset Password'
    },
    'auth.email': {
        'fr': 'Email',
        'en': 'Email'
    },
    'auth.password': {
        'fr': 'Mot de passe',
        'en': 'Password'
    },
    'auth.confirm_password': {
        'fr': 'Confirmer le mot de passe',
        'en': 'Confirm Password'
    },
    'auth.username': {
        'fr': 'Nom d\'utilisateur',
        'en': 'Username'
    },
    
    # Footer
    'footer.tagline': {
        'fr': 'Transformez la gestion de vos finances avec l\'intelligence artificielle.',
        'en': 'Transform your financial management with artificial intelligence.'
    },
    'footer.links': {
        'fr': 'Liens',
        'en': 'Links'
    },
    'footer.services': {
        'fr': 'Services',
        'en': 'Services'
    },
    'footer.copyright': {
        'fr': 'Tous droits réservés',
        'en': 'All rights reserved'
    },
    'footer.terms': {
        'fr': 'Conditions d\'utilisation',
        'en': 'Terms of Use'
    },
    'footer.privacy': {
        'fr': 'Politique de confidentialité',
        'en': 'Privacy Policy'
    },
    'footer.contact': {
        'fr': 'Contact',
        'en': 'Contact'
    },
    'footer.home': {
        'fr': 'Accueil',
        'en': 'Home'
    },
    'footer.ai_assistant': {
        'fr': 'Assistant IA',
        'en': 'AI Assistant'
    },
    'footer.scanning': {
        'fr': 'Numérisation',
        'en': 'Scanning'
    },
    'footer.login': {
        'fr': 'Connexion',
        'en': 'Login'
    },
    'footer.register': {
        'fr': 'Inscription',
        'en': 'Register'
    },
    'footer.pocket_accountant': {
        'fr': 'Comptable de poche',
        'en': 'Pocket Accountant'
    },
    'footer.tax_reports': {
        'fr': 'Rapports fiscaux',
        'en': 'Tax Reports'
    },
    'footer.subscriptions': {
        'fr': 'Abonnements',
        'en': 'Subscriptions'
    },
    
    # Finance dashboard translations
    'finance.dashboard.title': {
        'fr': 'Tableau de bord financier',
        'en': 'Financial Dashboard'
    },
    'finance.dashboard.heading': {
        'fr': 'Mon comptable de poche',
        'en': 'My Pocket Accountant'
    },
    'finance.dashboard.welcome': {
        'fr': 'Bienvenue dans votre espace financier personnel. Gérez vos factures, suivez vos dépenses et analysez vos finances en toute simplicité.',
        'en': 'Welcome to your personal financial space. Manage invoices, track expenses, and analyze your finances with ease.'
    },
    'finance.dashboard.total_income': {
        'fr': 'Revenus totaux',
        'en': 'Total Income'
    },
    'finance.dashboard.income_desc': {
        'fr': 'Total des entrées d\'argent',
        'en': 'Total money incoming'
    },
    'finance.dashboard.total_expenses': {
        'fr': 'Dépenses totales',
        'en': 'Total Expenses'
    },
    'finance.dashboard.expenses_desc': {
        'fr': 'Total des sorties d\'argent',
        'en': 'Total money outgoing'
    },
    'finance.dashboard.current_balance': {
        'fr': 'Solde actuel',
        'en': 'Current Balance'
    },
    'finance.dashboard.balance_desc': {
        'fr': 'Balance revenus - dépenses',
        'en': 'Income - expenses balance'
    },
    'finance.dashboard.quick_actions': {
        'fr': 'Actions rapides',
        'en': 'Quick Actions'
    },
    'finance.dashboard.scan_document': {
        'fr': 'Scanner un document',
        'en': 'Scan a Document'
    },
    'finance.dashboard.add_transaction': {
        'fr': 'Ajouter une transaction',
        'en': 'Add a Transaction'
    },
    'finance.dashboard.manage_categories': {
        'fr': 'Gérer les catégories',
        'en': 'Manage Categories'
    },
    'finance.dashboard.view_reports': {
        'fr': 'Voir les rapports',
        'en': 'View Reports'
    },
    'finance.dashboard.documents_to_process': {
        'fr': 'Documents à traiter',
        'en': 'Documents to Process'
    },
    'finance.dashboard.untitled_document': {
        'fr': 'Document sans titre',
        'en': 'Untitled Document'
    },
    'finance.dashboard.extracted_on': {
        'fr': 'Extrait le',
        'en': 'Extracted on'
    },
    'finance.dashboard.process': {
        'fr': 'Traiter',
        'en': 'Process'
    },
    'finance.dashboard.no_pending_documents': {
        'fr': 'Aucun document en attente de traitement',
        'en': 'No documents pending processing'
    },
    'finance.dashboard.recent_transactions': {
        'fr': 'Transactions récentes',
        'en': 'Recent Transactions'
    },
    'finance.dashboard.view_all': {
        'fr': 'Voir tout',
        'en': 'View all'
    },
    
    # Finance - Rapports fiscaux
    'finance.tax_report.title': {
        'fr': 'Rapports fiscaux',
        'en': 'Tax Reports'
    },
    'finance.tax_report.generate': {
        'fr': 'Générer un rapport fiscal',
        'en': 'Generate a Tax Report'
    },
    'finance.tax_report.name': {
        'fr': 'Nom du rapport',
        'en': 'Report Name'
    },
    'finance.tax_report.period': {
        'fr': 'Période du rapport',
        'en': 'Report Period'
    },
    'finance.tax_report.start_date': {
        'fr': 'Date de début',
        'en': 'Start Date'
    },
    'finance.tax_report.end_date': {
        'fr': 'Date de fin',
        'en': 'End Date'
    },
    'finance.tax_report.create': {
        'fr': 'Créer le rapport',
        'en': 'Create Report'
    },
    'finance.tax_report.my_reports': {
        'fr': 'Mes rapports fiscaux',
        'en': 'My Tax Reports'
    },
    'finance.tax_report.report_name': {
        'fr': 'Nom du rapport',
        'en': 'Report Name'
    },
    'finance.tax_report.period_label': {
        'fr': 'Période',
        'en': 'Period'
    },
    'finance.tax_report.income': {
        'fr': 'Revenus',
        'en': 'Income'
    },
    'finance.tax_report.expenses': {
        'fr': 'Dépenses',
        'en': 'Expenses'
    },
    'finance.tax_report.profit': {
        'fr': 'Bénéfice net',
        'en': 'Net Profit'
    },
    'finance.tax_report.actions': {
        'fr': 'Actions',
        'en': 'Actions'
    },
    'finance.tax_report.download_pdf': {
        'fr': 'Télécharger en PDF',
        'en': 'Download as PDF'
    },
    'finance.tax_report.no_reports': {
        'fr': 'Aucun rapport fiscal généré',
        'en': 'No tax reports generated'
    },
    'finance.tax_report.create_first': {
        'fr': 'Créez votre premier rapport fiscal pour faciliter votre déclaration d\'impôts.',
        'en': 'Create your first tax report to make your tax filing easier.'
    },
    'finance.tax_report.about': {
        'fr': 'À propos des rapports fiscaux',
        'en': 'About Tax Reports'
    },
    'finance.tax_report.feature1_title': {
        'fr': 'Calculs automatiques',
        'en': 'Automatic Calculations'
    },
    'finance.tax_report.feature1_desc': {
        'fr': 'Tous vos revenus et dépenses sont automatiquement calculés pour la période sélectionnée.',
        'en': 'All your income and expenses are automatically calculated for the selected period.'
    },
    'finance.tax_report.feature2_title': {
        'fr': 'Exportation facile',
        'en': 'Easy Export'
    },
    'finance.tax_report.feature2_desc': {
        'fr': 'Exportez vos rapports au format PDF pour les partager avec votre comptable.',
        'en': 'Export your reports as PDF to share with your accountant.'
    },
    'finance.tax_report.feature3_title': {
        'fr': 'Analyse IA',
        'en': 'AI Analysis'
    },
    'finance.tax_report.feature3_desc': {
        'fr': 'Obtenez des conseils personnalisés grâce à notre analyse intelligente de vos données financières.',
        'en': 'Get personalized advice through our intelligent analysis of your financial data.'
    },
    'finance.tax_report.summary': {
        'fr': 'Résumé financier',
        'en': 'Financial Summary'
    },
    'finance.tax_report.tax': {
        'fr': 'TVA collectée',
        'en': 'Collected VAT'
    },
    'finance.tax_report.income_by_category': {
        'fr': 'Revenus par catégorie',
        'en': 'Income by Category'
    },
    'finance.tax_report.expenses_by_category': {
        'fr': 'Dépenses par catégorie',
        'en': 'Expenses by Category'
    },
    'finance.tax_report.incomes': {
        'fr': 'Revenus',
        'en': 'Income'
    },
    'finance.tax_report.expenses': {
        'fr': 'Dépenses',
        'en': 'Expenses'
    },
    'finance.tax_report.date': {
        'fr': 'Date',
        'en': 'Date'
    },
    'finance.tax_report.description': {
        'fr': 'Description',
        'en': 'Description'
    },
    'finance.tax_report.category': {
        'fr': 'Catégorie',
        'en': 'Category'
    },
    'finance.tax_report.client': {
        'fr': 'Client',
        'en': 'Client'
    },
    'finance.tax_report.vendor': {
        'fr': 'Fournisseur',
        'en': 'Vendor'
    },
    'finance.tax_report.amount': {
        'fr': 'Montant',
        'en': 'Amount'
    },
    'finance.tax_report.tax_amount': {
        'fr': 'TVA',
        'en': 'VAT'
    },
    'finance.tax_report.total': {
        'fr': 'Total',
        'en': 'Total'
    },
    'finance.tax_report.no_incomes': {
        'fr': 'Aucun revenu enregistré pour cette période',
        'en': 'No income recorded for this period'
    },
    'finance.tax_report.no_expenses': {
        'fr': 'Aucune dépense enregistrée pour cette période',
        'en': 'No expenses recorded for this period'
    },
    'finance.tax_report.notes': {
        'fr': 'Notes personnelles',
        'en': 'Personal Notes'
    },
    'finance.tax_report.save_notes': {
        'fr': 'Enregistrer les notes',
        'en': 'Save Notes'
    },
    'finance.tax_report.notes_saved': {
        'fr': 'Notes enregistrées avec succès',
        'en': 'Notes saved successfully'
    },
    'finance.tax_report.ai_analysis': {
        'fr': 'Analyse intelligente',
        'en': 'Intelligent Analysis'
    },
    'finance.tax_report.generate_analysis': {
        'fr': 'Générer une analyse IA',
        'en': 'Generate AI Analysis'
    },
    'finance.tax_report.analysis_loading': {
        'fr': 'Génération de l\'analyse en cours...',
        'en': 'Generating analysis...'
    },
    'finance.tax_report.analysis_success': {
        'fr': 'Analyse générée avec succès',
        'en': 'Analysis generated successfully'
    },
    'finance.tax_report.period_prefix': {
        'fr': 'Période du',
        'en': 'Period from'
    },
    'finance.tax_report.period_to': {
        'fr': 'au',
        'en': 'to'
    },
    
    # Finance transactions table
    'finance.transactions.date': {
        'fr': 'Date',
        'en': 'Date'
    },
    'finance.transactions.description': {
        'fr': 'Description',
        'en': 'Description'
    },
    'finance.transactions.category': {
        'fr': 'Catégorie',
        'en': 'Category'
    },
    'finance.transactions.amount': {
        'fr': 'Montant',
        'en': 'Amount'
    },
    'finance.transactions.no_description': {
        'fr': 'Sans description',
        'en': 'No description'
    },
    'finance.transactions.uncategorized': {
        'fr': 'Non classée',
        'en': 'Uncategorized'
    },
    'finance.transactions.no_transactions': {
        'fr': 'Aucune transaction enregistrée',
        'en': 'No recorded transactions'
    },
    'finance.transactions.vendor': {
        'fr': 'Fournisseur',
        'en': 'Vendor'
    },
    'finance.transactions.tax': {
        'fr': 'TVA',
        'en': 'Tax'
    },
    'finance.transactions.actions': {
        'fr': 'Actions',
        'en': 'Actions'
    },
    'finance.transactions.view_details': {
        'fr': 'Voir détails',
        'en': 'View details'
    },
    'finance.transactions.edit': {
        'fr': 'Modifier',
        'en': 'Edit'
    },
    'finance.transactions.delete': {
        'fr': 'Supprimer',
        'en': 'Delete'
    },
    'finance.transactions.unclassified': {
        'fr': 'Non classée',
        'en': 'Unclassified'
    },
    'finance.transactions.title': {
        'fr': 'Transactions',
        'en': 'Transactions'
    },
    'finance.transactions.my_transactions': {
        'fr': 'Mes transactions',
        'en': 'My transactions'
    },
    'finance.transactions.add_button': {
        'fr': 'Ajouter',
        'en': 'Add'
    },
    'finance.transactions.description': {
        'fr': 'Consultez et gérez toutes vos transactions financières.',
        'en': 'View and manage all your financial transactions.'
    },
    'finance.transactions.list': {
        'fr': 'Liste des transactions',
        'en': 'Transactions list'
    },
    'finance.transactions.add_transaction': {
        'fr': 'Ajouter une transaction',
        'en': 'Add a transaction'
    },
    
    # Finance categories management 
    'finance.categories.name': {
        'fr': 'Nom',
        'en': 'Name'
    },
    'finance.categories.type': {
        'fr': 'Type',
        'en': 'Type'
    },
    'finance.categories.expense': {
        'fr': 'Dépense',
        'en': 'Expense'
    },
    'finance.categories.income': {
        'fr': 'Revenu',
        'en': 'Income'
    },
    'finance.categories.color': {
        'fr': 'Couleur',
        'en': 'Color'
    },
    'finance.categories.icon': {
        'fr': 'Icône',
        'en': 'Icon'
    },
    'finance.categories.actions': {
        'fr': 'Actions',
        'en': 'Actions'
    },
    'finance.categories.add': {
        'fr': 'Ajouter une catégorie',
        'en': 'Add Category'
    },
    'finance.categories.edit': {
        'fr': 'Modifier',
        'en': 'Edit'
    },
    'finance.categories.delete': {
        'fr': 'Supprimer',
        'en': 'Delete'
    },
    'finance.categories.manage': {
        'fr': 'Gestion des catégories',
        'en': 'Category Management'
    },
    'finance.categories.description': {
        'fr': 'Personnalisez vos catégories de dépenses et revenus pour un meilleur suivi de vos finances.',
        'en': 'Customize your expense and income categories for better tracking of your finances.'
    },
    'finance.categories.my_categories': {
        'fr': 'Mes catégories',
        'en': 'My Categories'
    },
    'finance.categories.expenses': {
        'fr': 'Dépenses',
        'en': 'Expenses'
    },
    'finance.categories.new': {
        'fr': 'Nouvelle catégorie',
        'en': 'New Category'
    },
    'finance.categories.name_placeholder': {
        'fr': 'Ex: Alimentation, Salaire...',
        'en': 'Ex: Food, Salary...'
    },
    'finance.categories.icon_tag': {
        'fr': 'Étiquette (par défaut)',
        'en': 'Tag (default)'
    },
    'finance.categories.icon_shopping': {
        'fr': 'Courses',
        'en': 'Shopping'
    },
    'finance.categories.icon_home': {
        'fr': 'Logement',
        'en': 'Housing'
    },
    'finance.categories.icon_car': {
        'fr': 'Transport',
        'en': 'Transportation'
    },
    'finance.categories.icon_restaurant': {
        'fr': 'Restaurant',
        'en': 'Restaurant'
    },
    'finance.categories.icon_clothes': {
        'fr': 'Vêtements',
        'en': 'Clothing'
    },
    'finance.categories.icon_health': {
        'fr': 'Santé',
        'en': 'Healthcare'
    },
    'finance.categories.icon_education': {
        'fr': 'Éducation',
        'en': 'Education'
    },
    'finance.categories.icon_travel': {
        'fr': 'Voyages',
        'en': 'Travel'
    },
    'finance.categories.icon_leisure': {
        'fr': 'Loisirs',
        'en': 'Entertainment'
    },
    'finance.categories.icon_salary': {
        'fr': 'Salaire',
        'en': 'Salary'
    },
    'finance.categories.icon_gift': {
        'fr': 'Cadeaux',
        'en': 'Gifts'
    },
    'finance.categories.icon_investment': {
        'fr': 'Investissements',
        'en': 'Investments'
    },
    'finance.categories.icon_refund': {
        'fr': 'Remboursements',
        'en': 'Refunds'
    },
    'finance.categories.confirm_delete': {
        'fr': 'Êtes-vous sûr de vouloir supprimer cette catégorie?',
        'en': 'Are you sure you want to delete this category?'
    },
    'finance.categories.no_expense_category': {
        'fr': 'Aucune catégorie de dépenses définie',
        'en': 'No expense category defined'
    },
    'finance.categories.no_income_category': {
        'fr': 'Aucune catégorie de revenus définie',
        'en': 'No income category defined'
    },
    
    # Formulaire ajout de transaction
    'finance.add_transaction.tax_rate': {
        'fr': 'Taux de TVA (%)',
        'en': 'VAT Rate (%)'
    },
    'finance.add_transaction.tax_rate_placeholder': {
        'fr': 'Ex: 20',
        'en': 'Ex: 20'
    },
    'finance.add_transaction.tax_rate_help': {
        'fr': 'Laissez vide si non applicable',
        'en': 'Leave empty if not applicable'
    },
    'finance.add_transaction.calculated_tax': {
        'fr': 'Montant de TVA calculé',
        'en': 'Calculated VAT amount'
    },
    
    # Finance add transaction form
    'finance.transaction.add.title': {
        'fr': 'Ajouter une transaction',
        'en': 'Add Transaction'
    },
    'finance.transaction.add.type': {
        'fr': 'Type de transaction',
        'en': 'Transaction Type'
    },
    'finance.transaction.add.expense': {
        'fr': 'Dépense',
        'en': 'Expense'
    },
    'finance.transaction.add.income': {
        'fr': 'Revenu',
        'en': 'Income'
    },
    'finance.transaction.add.amount': {
        'fr': 'Montant',
        'en': 'Amount'
    },
    'finance.transaction.add.description': {
        'fr': 'Description',
        'en': 'Description'
    },
    'finance.transaction.add.date': {
        'fr': 'Date de transaction',
        'en': 'Transaction Date'
    },
    'finance.transaction.add.vendor': {
        'fr': 'Fournisseur / Client',
        'en': 'Vendor / Client'
    },
    'finance.transaction.add.category': {
        'fr': 'Catégorie',
        'en': 'Category'
    },
    'finance.transaction.add.select_category': {
        'fr': 'Sélectionnez une catégorie',
        'en': 'Select a category'
    },
    'finance.transaction.add.payment_method': {
        'fr': 'Moyen de paiement',
        'en': 'Payment Method'
    },
    'finance.transaction.add.cash': {
        'fr': 'Espèces',
        'en': 'Cash'
    },
    'finance.transaction.add.card': {
        'fr': 'Carte bancaire',
        'en': 'Credit/Debit Card'
    },
    'finance.transaction.add.transfer': {
        'fr': 'Virement',
        'en': 'Transfer'
    },
    'finance.transaction.add.check': {
        'fr': 'Chèque',
        'en': 'Check'
    },
    'finance.transaction.add.tax_rate': {
        'fr': 'Taux de TVA (%)',
        'en': 'Tax Rate (%)'
    },
    'finance.transaction.add.submit': {
        'fr': 'Enregistrer la transaction',
        'en': 'Save Transaction'
    },
    'finance.transaction.add.cancel': {
        'fr': 'Annuler',
        'en': 'Cancel'
    },
    
    # Finance processing document
    'finance.process.title': {
        'fr': 'Traiter le document',
        'en': 'Process Document'
    },
    'finance.process.extracted_content': {
        'fr': 'Contenu extrait',
        'en': 'Extracted Content'
    },
    'finance.process.document_type': {
        'fr': 'Type de document',
        'en': 'Document Type'
    },
    'finance.process.invoice': {
        'fr': 'Facture',
        'en': 'Invoice'
    },
    'finance.process.receipt': {
        'fr': 'Reçu',
        'en': 'Receipt'
    },
    'finance.process.contract': {
        'fr': 'Contrat',
        'en': 'Contract'
    },
    'finance.process.other': {
        'fr': 'Autre',
        'en': 'Other'
    },

    # Marketing Module
    'nav.marketing': {
        'fr': 'Marketing IA',
        'en': 'AI Marketing'
    },
    'campaign_create_title': {
        'fr': 'Créer une nouvelle campagne',
        'en': 'Create a new campaign'
    },
    'campaigns_list_title': {
        'fr': 'Campagnes Marketing',
        'en': 'Marketing Campaigns'
    },
    'content_generator': {
        'fr': 'Générateur de Contenu',
        'en': 'Content Generator'
    },
    'ai_content_generator': {
        'fr': 'Générateur de Contenu IA',
        'en': 'AI Content Generator'
    },
    'generate_new_content': {
        'fr': 'Générer un nouveau contenu',
        'en': 'Generate New Content'
    },
    'content_type': {
        'fr': 'Type de contenu',
        'en': 'Content Type'
    },
    'select_content_type': {
        'fr': 'Sélectionnez un type de contenu',
        'en': 'Select Content Type'
    },
    'email_marketing': {
        'fr': 'Email Marketing',
        'en': 'Email Marketing'
    },
    'social_media_post': {
        'fr': 'Publication sur les réseaux sociaux',
        'en': 'Social Media Post'
    },
    'blog_article': {
        'fr': 'Article de blog',
        'en': 'Blog Article'
    },
    'advertisement': {
        'fr': 'Publicité',
        'en': 'Advertisement'
    },
    'platform': {
        'fr': 'Plateforme',
        'en': 'Platform'
    },
    'select_platform': {
        'fr': 'Sélectionnez une plateforme',
        'en': 'Select Platform'
    },
    'business_sector': {
        'fr': 'Secteur d\'activité',
        'en': 'Business Sector'
    },
    'select_sector': {
        'fr': 'Sélectionnez un secteur',
        'en': 'Select Sector'
    },
    'retail': {
        'fr': 'Commerce de détail',
        'en': 'Retail'
    },
    'technology': {
        'fr': 'Technologie',
        'en': 'Technology'
    },
    'healthcare': {
        'fr': 'Santé',
        'en': 'Healthcare'
    },
    'education': {
        'fr': 'Éducation',
        'en': 'Education'
    },
    'finance': {
        'fr': 'Finance',
        'en': 'Finance'
    },
    'food_restaurant': {
        'fr': 'Alimentation et Restauration',
        'en': 'Food & Restaurant'
    },
    'travel_tourism': {
        'fr': 'Voyage et Tourisme',
        'en': 'Travel & Tourism'
    },
    'real_estate': {
        'fr': 'Immobilier',
        'en': 'Real Estate'
    },
    'manufacturing': {
        'fr': 'Fabrication',
        'en': 'Manufacturing'
    },
    'consulting': {
        'fr': 'Conseil',
        'en': 'Consulting'
    },
    'specific_instructions': {
        'fr': 'Instructions spécifiques',
        'en': 'Specific Instructions'
    },
    'specific_instructions_placeholder': {
        'fr': 'Décrivez la cible, le ton, les objectifs ou d\'autres détails...',
        'en': 'Describe target audience, tone, goals, or other details...'
    },
    'language': {
        'fr': 'Langue',
        'en': 'Language'
    },
    'french': {
        'fr': 'Français',
        'en': 'French'
    },
    'english': {
        'fr': 'Anglais',
        'en': 'English'
    },
    'generate_content': {
        'fr': 'Générer le contenu',
        'en': 'Generate Content'
    },
    'generated_content': {
        'fr': 'Contenu généré',
        'en': 'Generated Content'
    },
    'copy': {
        'fr': 'Copier',
        'en': 'Copy'
    },
    'variations': {
        'fr': 'Variations',
        'en': 'Variations'
    },
    'use_in_campaign': {
        'fr': 'Utiliser dans une campagne',
        'en': 'Use in Campaign'
    },
    'save_to_favorites': {
        'fr': 'Enregistrer comme favori',
        'en': 'Save to Favorites'
    },
    'content_will_appear_here': {
        'fr': 'Le contenu généré apparaîtra ici',
        'en': 'Generated content will appear here'
    },
    'recent_generated_content': {
        'fr': 'Contenus générés récemment',
        'en': 'Recently Generated Content'
    },
    'type': {
        'fr': 'Type',
        'en': 'Type'
    },
    'sector': {
        'fr': 'Secteur',
        'en': 'Sector'
    },
    'date': {
        'fr': 'Date',
        'en': 'Date'
    },
    'preview': {
        'fr': 'Aperçu',
        'en': 'Preview'
    },
    'actions': {
        'fr': 'Actions',
        'en': 'Actions'
    },
    'no_content_generated_yet': {
        'fr': 'Aucun contenu généré pour l\'instant',
        'en': 'No content generated yet'
    },
    'content_variations': {
        'fr': 'Variations de contenu',
        'en': 'Content Variations'
    },
    'number_of_variations': {
        'fr': 'Nombre de variations',
        'en': 'Number of Variations'
    },
    'loading': {
        'fr': 'Chargement',
        'en': 'Loading'
    },
    'generating_variations': {
        'fr': 'Génération des variations en cours...',
        'en': 'Generating variations...'
    },
    'close': {
        'fr': 'Fermer',
        'en': 'Close'
    },
    'generate_variations': {
        'fr': 'Générer des variations',
        'en': 'Generate Variations'
    },
    'error_generating_content': {
        'fr': 'Erreur lors de la génération du contenu',
        'en': 'Error generating content'
    },
    'editorial_calendar': {
        'fr': 'Calendrier Éditorial',
        'en': 'Editorial Calendar'
    },
    'content_calendar': {
        'fr': 'Calendrier de Contenu',
        'en': 'Content Calendar'
    },
    'generate_calendar': {
        'fr': 'Générer un calendrier',
        'en': 'Generate Calendar'
    },
    'export': {
        'fr': 'Exporter',
        'en': 'Export'
    },
    'email': {
        'fr': 'Email',
        'en': 'Email'
    },
    'social_media': {
        'fr': 'Réseaux Sociaux',
        'en': 'Social Media'
    },
    'blog': {
        'fr': 'Blog',
        'en': 'Blog'
    },
    'ad': {
        'fr': 'Publicité',
        'en': 'Ad'
    },
    'upcoming_content': {
        'fr': 'Contenus à venir',
        'en': 'Upcoming Content'
    },
    'view': {
        'fr': 'Voir',
        'en': 'View'
    },
    'no_upcoming_content': {
        'fr': 'Aucun contenu à venir',
        'en': 'No upcoming content'
    },
    'calendar_statistics': {
        'fr': 'Statistiques du calendrier',
        'en': 'Calendar Statistics'
    },
    'total_content_items': {
        'fr': 'Total des contenus',
        'en': 'Total Content Items'
    },
    'email_campaigns': {
        'fr': 'Campagnes email',
        'en': 'Email Campaigns'
    },
    'social_posts': {
        'fr': 'Publications sociales',
        'en': 'Social Posts'
    },
    'blog_articles': {
        'fr': 'Articles de blog',
        'en': 'Blog Articles'
    },
    'ad_campaigns': {
        'fr': 'Campagnes publicitaires',
        'en': 'Ad Campaigns'
    },
    'most_active_platform': {
        'fr': 'Plateforme la plus active',
        'en': 'Most Active Platform'
    },
    'generate_editorial_calendar': {
        'fr': 'Générer un calendrier éditorial',
        'en': 'Generate Editorial Calendar'
    },
    'post_frequency': {
        'fr': 'Fréquence de publication',
        'en': 'Post Frequency'
    },
    'select_frequency': {
        'fr': 'Sélectionnez une fréquence',
        'en': 'Select Frequency'
    },
    'daily': {
        'fr': 'Quotidienne',
        'en': 'Daily'
    },
    'weekly': {
        'fr': 'Hebdomadaire',
        'en': 'Weekly'
    },
    'biweekly': {
        'fr': 'Bi-hebdomadaire',
        'en': 'Biweekly'
    },
    'monthly': {
        'fr': 'Mensuelle',
        'en': 'Monthly'
    },
    'custom': {
        'fr': 'Personnalisée',
        'en': 'Custom'
    },
    'platforms': {
        'fr': 'Plateformes',
        'en': 'Platforms'
    },
    'key_topics': {
        'fr': 'Sujets clés',
        'en': 'Key Topics'
    },
    'topics_placeholder': {
        'fr': 'Séparés par des virgules: produits, conseils, promotions...',
        'en': 'Comma separated: products, tips, promotions...'
    },
    'topics_help_text': {
        'fr': 'Listez les thèmes que vous souhaitez aborder dans votre calendrier éditorial.',
        'en': 'List the themes you want to cover in your editorial calendar.'
    },
    'additional_notes': {
        'fr': 'Notes additionnelles',
        'en': 'Additional Notes'
    },
    'notes_placeholder': {
        'fr': 'Événements spéciaux, promotions, lancements de produits...',
        'en': 'Special events, promotions, product launches...'
    },
    'generating_calendar': {
        'fr': 'Génération du calendrier en cours...',
        'en': 'Generating calendar...'
    },
    'cancel': {
        'fr': 'Annuler',
        'en': 'Cancel'
    },
    'generate': {
        'fr': 'Générer',
        'en': 'Generate'
    },
    'content_details': {
        'fr': 'Détails du contenu',
        'en': 'Content Details'
    },
    'title': {
        'fr': 'Titre',
        'en': 'Title'
    },
    'description': {
        'fr': 'Description',
        'en': 'Description'
    },
    'time': {
        'fr': 'Heure',
        'en': 'Time'
    },
    'delete': {
        'fr': 'Supprimer',
        'en': 'Delete'
    },
    'save': {
        'fr': 'Enregistrer',
        'en': 'Save'
    },
    'add_content': {
        'fr': 'Ajouter un contenu',
        'en': 'Add Content'
    },
    'add': {
        'fr': 'Ajouter',
        'en': 'Add'
    },
    'today': {
        'fr': 'Aujourd\'hui',
        'en': 'Today'
    },
    'month': {
        'fr': 'Mois',
        'en': 'Month'
    },
    'week': {
        'fr': 'Semaine',
        'en': 'Week'
    },
    'list': {
        'fr': 'Liste',
        'en': 'List'
    },
    'calendar_generated_success': {
        'fr': 'Calendrier généré avec succès !',
        'en': 'Calendar generated successfully!'
    },
    'calendar_generation_error': {
        'fr': 'Erreur lors de la génération du calendrier',
        'en': 'Error generating calendar'
    },
    'error_occurred': {
        'fr': 'Une erreur s\'est produite',
        'en': 'An error occurred'
    },
    'content_updated_success': {
        'fr': 'Contenu mis à jour avec succès',
        'en': 'Content updated successfully'
    },
    'content_update_error': {
        'fr': 'Erreur lors de la mise à jour du contenu',
        'en': 'Error updating content'
    },
    'confirm_delete_content': {
        'fr': 'Êtes-vous sûr de vouloir supprimer ce contenu ?',
        'en': 'Are you sure you want to delete this content?'
    },
    'content_deleted_success': {
        'fr': 'Contenu supprimé avec succès',
        'en': 'Content deleted successfully'
    },
    'content_deletion_error': {
        'fr': 'Erreur lors de la suppression du contenu',
        'en': 'Error deleting content'
    },
    'content_added_success': {
        'fr': 'Contenu ajouté avec succès',
        'en': 'Content added successfully'
    },
    'content_addition_error': {
        'fr': 'Erreur lors de l\'ajout du contenu',
        'en': 'Error adding content'
    },
    'content_generation_error': {
        'fr': 'Erreur lors de la génération du contenu',
        'en': 'Error generating content'
    },
    'marketing_dashboard': {
        'fr': 'Tableau de Bord Marketing',
        'en': 'Marketing Dashboard'
    },
    'error_user_not_found': {
        'fr': 'Utilisateur non trouvé',
        'en': 'User not found'
    },
    'campaign_created_success': {
        'fr': 'Campagne créée avec succès',
        'en': 'Campaign created successfully'
    },
    'campaign_creation_error': {
        'fr': 'Erreur lors de la création de la campagne',
        'en': 'Error creating campaign'
    },
    'campaign_updated_success': {
        'fr': 'Campagne mise à jour avec succès',
        'en': 'Campaign updated successfully'
    },
    'campaign_update_error': {
        'fr': 'Erreur lors de la mise à jour de la campagne',
        'en': 'Error updating campaign'
    },
    'campaign_deleted_success': {
        'fr': 'Campagne supprimée avec succès',
        'en': 'Campaign deleted successfully'
    },
    'campaign_deletion_error': {
        'fr': 'Erreur lors de la suppression de la campagne',
        'en': 'Error deleting campaign'
    },
    'campaign_type_mismatch': {
        'fr': 'Type de campagne incorrect',
        'en': 'Campaign type mismatch'
    },
    'email_content_created_success': {
        'fr': 'Contenu email créé avec succès',
        'en': 'Email content created successfully'
    },
    'email_content_creation_error': {
        'fr': 'Erreur lors de la création du contenu email',
        'en': 'Error creating email content'
    },
    'social_post_created_success': {
        'fr': 'Publication sociale créée avec succès',
        'en': 'Social post created successfully'
    },
    'social_post_creation_error': {
        'fr': 'Erreur lors de la création de la publication sociale',
        'en': 'Error creating social post'
    },
    'influencer_brief_created_success': {
        'fr': 'Brief influenceur créé avec succès',
        'en': 'Influencer brief created successfully'
    },
    'influencer_brief_creation_error': {
        'fr': 'Erreur lors de la création du brief influenceur',
        'en': 'Error creating influencer brief'
    },
    
    # Module API Marketplace
    'marketplace_title': {
        'fr': 'API Marketplace',
        'en': 'API Marketplace'
    },
    'marketplace_subtitle': {
        'fr': 'Étendez les fonctionnalités de votre application avec des extensions et intégrations',
        'en': 'Extend your application capabilities with extensions and integrations'
    },
    'marketplace_featured_extensions': {
        'fr': 'Extensions à la une',
        'en': 'Featured Extensions'
    },
    'marketplace_my_extensions': {
        'fr': 'Mes extensions',
        'en': 'My Extensions'
    },
    'marketplace_api_connections': {
        'fr': 'Connexions API',
        'en': 'API Connections'
    },
    'marketplace_automation_templates': {
        'fr': 'Templates d\'automatisation',
        'en': 'Automation Templates'
    },
    'marketplace_discover': {
        'fr': 'Découvrir',
        'en': 'Discover'
    },
    'marketplace_install': {
        'fr': 'Installer',
        'en': 'Install'
    },
    'marketplace_uninstall': {
        'fr': 'Désinstaller',
        'en': 'Uninstall'
    },
    'marketplace_by': {
        'fr': 'Par',
        'en': 'By'
    },
    'marketplace_free': {
        'fr': 'Gratuit',
        'en': 'Free'
    },
    'marketplace_paid': {
        'fr': 'Payant',
        'en': 'Paid'
    },
    'marketplace_version': {
        'fr': 'Version',
        'en': 'Version'
    },
    'marketplace_installed': {
        'fr': 'Installé',
        'en': 'Installed'
    },
    'marketplace_not_installed': {
        'fr': 'Non installé',
        'en': 'Not installed'
    },
    'marketplace_details': {
        'fr': 'Détails',
        'en': 'Details'
    },
    'marketplace_reviews': {
        'fr': 'Avis',
        'en': 'Reviews'
    },
    'marketplace_documentation': {
        'fr': 'Documentation',
        'en': 'Documentation'
    },
    'marketplace_support': {
        'fr': 'Support',
        'en': 'Support'
    },
    'marketplace_similar_extensions': {
        'fr': 'Extensions similaires',
        'en': 'Similar extensions'
    },
    'marketplace_add_review': {
        'fr': 'Ajouter un avis',
        'en': 'Add a review'
    },
    'marketplace_your_rating': {
        'fr': 'Votre note',
        'en': 'Your rating'
    },
    'marketplace_review_title': {
        'fr': 'Titre de l\'avis',
        'en': 'Review title'
    },
    'marketplace_review_comment': {
        'fr': 'Commentaire',
        'en': 'Comment'
    },
    'marketplace_submit_review': {
        'fr': 'Soumettre l\'avis',
        'en': 'Submit review'
    },
    'marketplace_extension_installed': {
        'fr': 'Extension installée avec succès!',
        'en': 'Extension installed successfully!'
    },
    'marketplace_extension_uninstalled': {
        'fr': 'Extension désinstallée avec succès.',
        'en': 'Extension uninstalled successfully.'
    },
    'marketplace_extension_already_installed': {
        'fr': 'Cette extension est déjà installée.',
        'en': 'This extension is already installed.'
    },
    'marketplace_extension_not_installed': {
        'fr': 'Cette extension n\'est pas installée.',
        'en': 'This extension is not installed.'
    },
    'marketplace_no_versions_available': {
        'fr': 'Aucune version disponible pour cette extension.',
        'en': 'No versions available for this extension.'
    },
    'marketplace_installation_error': {
        'fr': 'Une erreur est survenue lors de l\'installation.',
        'en': 'An error occurred during installation.'
    },
    'marketplace_uninstallation_error': {
        'fr': 'Une erreur est survenue lors de la désinstallation.',
        'en': 'An error occurred during uninstallation.'
    },
    'marketplace_review_submitted': {
        'fr': 'Votre avis a été soumis avec succès.',
        'en': 'Your review has been submitted successfully.'
    },
    'marketplace_review_error': {
        'fr': 'Une erreur est survenue lors de la soumission de votre avis.',
        'en': 'An error occurred while submitting your review.'
    },
    'marketplace_invalid_rating': {
        'fr': 'Veuillez fournir une note valide (1-5).',
        'en': 'Please provide a valid rating (1-5).'
    },
    'marketplace_create_connection': {
        'fr': 'Créer une connexion',
        'en': 'Create a connection'
    },
    'marketplace_edit_connection': {
        'fr': 'Modifier la connexion',
        'en': 'Edit connection'
    },
    'marketplace_delete_connection': {
        'fr': 'Supprimer la connexion',
        'en': 'Delete connection'
    },
    'marketplace_test_connection': {
        'fr': 'Tester la connexion',
        'en': 'Test connection'
    },
    'marketplace_connection_name': {
        'fr': 'Nom de la connexion',
        'en': 'Connection name'
    },
    'marketplace_connection_description': {
        'fr': 'Description de la connexion',
        'en': 'Connection description'
    },
    'marketplace_api_key': {
        'fr': 'Clé API',
        'en': 'API key'
    },
    'marketplace_endpoint_url': {
        'fr': 'URL du endpoint',
        'en': 'Endpoint URL'
    },
    'marketplace_connection_status': {
        'fr': 'Statut de la connexion',
        'en': 'Connection status'
    },
    'marketplace_active': {
        'fr': 'Active',
        'en': 'Active'
    },
    'marketplace_pending': {
        'fr': 'En attente',
        'en': 'Pending'
    },
    'marketplace_error': {
        'fr': 'Erreur',
        'en': 'Error'
    },
    'marketplace_last_connected': {
        'fr': 'Dernière connexion',
        'en': 'Last connected'
    },
    'marketplace_required_fields': {
        'fr': 'Veuillez remplir tous les champs obligatoires.',
        'en': 'Please fill in all required fields.'
    },
    'marketplace_invalid_extension': {
        'fr': 'Extension invalide.',
        'en': 'Invalid extension.'
    },
    'marketplace_extension_not_found': {
        'fr': 'Extension introuvable.',
        'en': 'Extension not found.'
    },
    'marketplace_connection_created': {
        'fr': 'Connexion API créée avec succès.',
        'en': 'API connection created successfully.'
    },
    'marketplace_connection_error': {
        'fr': 'Une erreur est survenue lors de la création de la connexion.',
        'en': 'An error occurred while creating the connection.'
    },
    'marketplace_connection_updated': {
        'fr': 'Connexion API mise à jour avec succès.',
        'en': 'API connection updated successfully.'
    },
    'marketplace_connection_update_error': {
        'fr': 'Une erreur est survenue lors de la mise à jour de la connexion.',
        'en': 'An error occurred while updating the connection.'
    },
    'marketplace_connection_deleted': {
        'fr': 'Connexion API supprimée avec succès.',
        'en': 'API connection deleted successfully.'
    },
    'marketplace_connection_delete_error': {
        'fr': 'Une erreur est survenue lors de la suppression de la connexion.',
        'en': 'An error occurred while deleting the connection.'
    },
    'marketplace_connection_test_success': {
        'fr': 'Test de connexion réussi.',
        'en': 'Connection test successful.'
    },
    'marketplace_connection_test_error': {
        'fr': 'Échec du test de connexion. Vérifiez vos identifiants.',
        'en': 'Connection test failed. Check your credentials.'
    },
    'marketplace_connection_test_db_error': {
        'fr': 'Une erreur est survenue lors du test.',
        'en': 'An error occurred during the test.'
    },
    'marketplace_category': {
        'fr': 'Catégorie',
        'en': 'Category'
    },
    'marketplace_type': {
        'fr': 'Type',
        'en': 'Type'
    },
    'marketplace_difficulty': {
        'fr': 'Difficulté',
        'en': 'Difficulty'
    },
    'marketplace_sort_by': {
        'fr': 'Trier par',
        'en': 'Sort by'
    },
    'marketplace_popular': {
        'fr': 'Populaire',
        'en': 'Popular'
    },
    'marketplace_recent': {
        'fr': 'Récent',
        'en': 'Recent'
    },
    'marketplace_rating': {
        'fr': 'Note',
        'en': 'Rating'
    },
    'marketplace_filters': {
        'fr': 'Filtres',
        'en': 'Filters'
    },
    'marketplace_apply_filters': {
        'fr': 'Appliquer les filtres',
        'en': 'Apply filters'
    },
    'marketplace_clear_filters': {
        'fr': 'Effacer les filtres',
        'en': 'Clear filters'
    },
    'marketplace_search_placeholder': {
        'fr': 'Rechercher des extensions...',
        'en': 'Search extensions...'
    },
    'marketplace_no_results': {
        'fr': 'Aucun résultat trouvé.',
        'en': 'No results found.'
    },
    'marketplace_create_instance': {
        'fr': 'Créer une instance',
        'en': 'Create instance'
    },
    'marketplace_instance_name': {
        'fr': 'Nom de l\'instance',
        'en': 'Instance name'
    },
    'marketplace_instance_description': {
        'fr': 'Description de l\'instance',
        'en': 'Instance description'
    },
    'marketplace_instance_configuration': {
        'fr': 'Configuration de l\'instance',
        'en': 'Instance configuration'
    },
    'marketplace_instance_created': {
        'fr': 'Instance d\'automatisation créée avec succès.',
        'en': 'Automation instance created successfully.'
    },
    'marketplace_instance_error': {
        'fr': 'Une erreur est survenue lors de la création de l\'instance.',
        'en': 'An error occurred while creating the instance.'
    },
    'marketplace_instance_updated': {
        'fr': 'Instance d\'automatisation mise à jour avec succès.',
        'en': 'Automation instance updated successfully.'
    },
    'marketplace_instance_update_error': {
        'fr': 'Une erreur est survenue lors de la mise à jour de l\'instance.',
        'en': 'An error occurred while updating the instance.'
    },
    'marketplace_instance_deleted': {
        'fr': 'Instance d\'automatisation supprimée avec succès.',
        'en': 'Automation instance deleted successfully.'
    },
    'marketplace_instance_delete_error': {
        'fr': 'Une erreur est survenue lors de la suppression de l\'instance.',
        'en': 'An error occurred while deleting the instance.'
    },
    'marketplace_instance_paused': {
        'fr': 'Instance d\'automatisation mise en pause.',
        'en': 'Automation instance paused.'
    },
    'marketplace_instance_activated': {
        'fr': 'Instance d\'automatisation activée.',
        'en': 'Automation instance activated.'
    },
    'marketplace_instance_toggle_error': {
        'fr': 'Une erreur est survenue lors du changement de statut.',
        'en': 'An error occurred while changing the status.'
    },
    
    # Module de formation
    'training_dashboard_title': {
        'fr': 'Formation Interactive',
        'en': 'Interactive Training'
    },
    'training_dashboard_subtitle': {
        'fr': 'Développez vos compétences avec nos formations personnalisées',
        'en': 'Develop your skills with our personalized training courses'
    },
    'training_welcome': {
        'fr': 'Bienvenue dans notre centre de formation',
        'en': 'Welcome to our training center'
    },
    'training_login_message': {
        'fr': 'Connectez-vous pour accéder à toutes nos formations et suivre votre progression',
        'en': 'Log in to access all our training courses and track your progress'
    },
    'training_in_progress_courses': {
        'fr': 'Mes formations en cours',
        'en': 'My courses in progress'
    },
    'training_popular_courses': {
        'fr': 'Formations populaires',
        'en': 'Popular courses'
    },
    'training_my_certifications': {
        'fr': 'Mes certifications',
        'en': 'My certifications'
    },
    'training_knowledge_base': {
        'fr': 'Base de connaissances',
        'en': 'Knowledge base'
    },
    'training_recent_articles': {
        'fr': 'Articles récents',
        'en': 'Recent articles'
    },
    'training_no_courses': {
        'fr': 'Aucun cours en cours. Inscrivez-vous à un cours pour commencer.',
        'en': 'No courses in progress. Enroll in a course to get started.'
    },
    'training_no_certifications': {
        'fr': 'Vous n\'avez pas encore de certification. Terminez un cours certifié pour en obtenir une.',
        'en': 'You don\'t have any certifications yet. Complete a certified course to get one.'
    },
    'training_view_all': {
        'fr': 'Voir tout',
        'en': 'View all'
    },
    'training_course_duration': {
        'fr': 'Durée',
        'en': 'Duration'
    },
    'training_course_lessons': {
        'fr': 'Leçons',
        'en': 'Lessons'
    },
    'training_certified': {
        'fr': 'Certifié',
        'en': 'Certified'
    },
    'training_difficulty_beginner': {
        'fr': 'Débutant',
        'en': 'Beginner'
    },
    'training_difficulty_intermediate': {
        'fr': 'Intermédiaire',
        'en': 'Intermediate'
    },
    'training_difficulty_advanced': {
        'fr': 'Avancé',
        'en': 'Advanced'
    },
    'training_continue': {
        'fr': 'Continuer',
        'en': 'Continue'
    },
    'training_start': {
        'fr': 'Commencer',
        'en': 'Start'
    },
    'training_enroll': {
        'fr': 'S\'inscrire',
        'en': 'Enroll'
    },
    'training_course_progress': {
        'fr': 'Progression',
        'en': 'Progress'
    },
    'training_browse_all_courses': {
        'fr': 'Parcourir tous les cours',
        'en': 'Browse all courses'
    },
    'training_dashboard': {
        'fr': 'Formation',
        'en': 'Training'
    },
    'training_courses': {
        'fr': 'Cours',
        'en': 'Courses'
    },
    'training_admin_courses_title': {
        'fr': 'Gestion des cours',
        'en': 'Course Management'
    },
    
    # Traductions pour le module API Marketplace
    'nav.marketplace': {
        'fr': 'API Marketplace',
        'en': 'API Marketplace'
    },
    'marketplace_title': {
        'fr': 'API Marketplace',
        'en': 'API Marketplace'
    },
    'marketplace_subtitle': {
        'fr': 'Intégrations, extensions et automatisations pour votre entreprise',
        'en': 'Integrations, extensions and automations for your business'
    },
    'marketplace_search_placeholder': {
        'fr': 'Rechercher des extensions, API, templates...',
        'en': 'Search for extensions, APIs, templates...'
    },
    'marketplace_extensions': {
        'fr': 'Extensions API',
        'en': 'API Extensions'
    },
    'marketplace_extensions_desc': {
        'fr': 'Étendez les fonctionnalités de votre IA-Solution avec des extensions métier spécialisées.',
        'en': 'Extend the capabilities of your IA-Solution with specialized business extensions.'
    },
    'marketplace_explore_extensions': {
        'fr': 'Explorer les extensions',
        'en': 'Explore extensions'
    },
    'marketplace_api_connections': {
        'fr': 'Connexions API',
        'en': 'API Connections'
    },
    'marketplace_api_connections_desc': {
        'fr': 'Connectez IA-Solution à vos outils et services externes préférés.',
        'en': 'Connect IA-Solution to your favorite external tools and services.'
    },
    'marketplace_manage_connections': {
        'fr': 'Gérer les connexions',
        'en': 'Manage connections'
    },
    'marketplace_automation_templates': {
        'fr': 'Templates d\'automatisation',
        'en': 'Automation Templates'
    },
    'marketplace_automation_templates_desc': {
        'fr': 'Automatisez vos processus métier grâce à des templates prêts à l\'emploi.',
        'en': 'Automate your business processes with ready-to-use templates.'
    },
    'marketplace_explore_templates': {
        'fr': 'Explorer les templates',
        'en': 'Explore templates'
    },
    'marketplace_popular_categories': {
        'fr': 'Catégories populaires',
        'en': 'Popular Categories'
    },
    'marketplace_view_category': {
        'fr': 'Voir la catégorie',
        'en': 'View category'
    },
    'marketplace_featured_extensions': {
        'fr': 'Extensions mises en avant',
        'en': 'Featured Extensions'
    },
    'marketplace_view_all': {
        'fr': 'Voir tout',
        'en': 'View all'
    },
    'marketplace_by': {
        'fr': 'Par',
        'en': 'By'
    },
    'marketplace_details': {
        'fr': 'Détails',
        'en': 'Details'
    },
    'marketplace_popular_templates': {
        'fr': 'Templates populaires',
        'en': 'Popular Templates'
    },
    'marketplace_difficulty_beginner': {
        'fr': 'Débutant',
        'en': 'Beginner'
    },
    'marketplace_difficulty_intermediate': {
        'fr': 'Intermédiaire',
        'en': 'Intermediate'
    },
    'marketplace_difficulty_advanced': {
        'fr': 'Avancé',
        'en': 'Advanced'
    },
    'marketplace_minutes': {
        'fr': 'minutes',
        'en': 'minutes'
    },
    'marketplace_hours': {
        'fr': 'heures',
        'en': 'hours'
    },
    'marketplace_cta_title': {
        'fr': 'Étendez les capacités de votre entreprise',
        'en': 'Extend your business capabilities'
    },
    'marketplace_cta_desc': {
        'fr': 'Découvrez comment les extensions et automatisations peuvent transformer votre workflow et booster votre productivité.',
        'en': 'Discover how extensions and automations can transform your workflow and boost your productivity.'
    },
    'marketplace_developer_title': {
        'fr': 'Vous êtes développeur ?',
        'en': 'Are you a developer?'
    },
    'marketplace_developer_desc': {
        'fr': 'Créez et publiez vos propres extensions et templates sur le marketplace IA-Solution.',
        'en': 'Create and publish your own extensions and templates on the IA-Solution marketplace.'
    },
    'marketplace_developer_portal': {
        'fr': 'Portail développeur',
        'en': 'Developer Portal'
    },
    'marketplace_filters': {
        'fr': 'Filtres',
        'en': 'Filters'
    },
    'marketplace_all_categories': {
        'fr': 'Toutes les catégories',
        'en': 'All categories'
    },
    'marketplace_all_types': {
        'fr': 'Tous les types',
        'en': 'All types'
    },
    'marketplace_sort_by': {
        'fr': 'Trier par',
        'en': 'Sort by'
    },
    'marketplace_popular': {
        'fr': 'Populaire',
        'en': 'Popular'
    },
    'marketplace_recent': {
        'fr': 'Récent',
        'en': 'Recent'
    },
    'marketplace_rating': {
        'fr': 'Note',
        'en': 'Rating'
    },
    'marketplace_apply_filters': {
        'fr': 'Appliquer les filtres',
        'en': 'Apply filters'
    },
    'marketplace_clear_filters': {
        'fr': 'Effacer les filtres',
        'en': 'Clear filters'
    },
    'marketplace_search_results': {
        'fr': 'Résultats de recherche',
        'en': 'Search results'
    },
    'marketplace_all_extensions': {
        'fr': 'Toutes les extensions',
        'en': 'All extensions'
    },
    'marketplace_free': {
        'fr': 'Gratuit',
        'en': 'Free'
    },
    'marketplace_no_results': {
        'fr': 'Aucun résultat trouvé.',
        'en': 'No results found.'
    },
    'marketplace_try_different_filters': {
        'fr': 'Essayez de modifier vos filtres de recherche.',
        'en': 'Try modifying your search filters.'
    },
    'marketplace_view_all_extensions': {
        'fr': 'Voir toutes les extensions',
        'en': 'View all extensions'
    },
    'marketplace_category': {
        'fr': 'Catégorie',
        'en': 'Category'
    },
    'marketplace_type': {
        'fr': 'Type',
        'en': 'Type'
    },
    'marketplace_connection_name': {
        'fr': 'Nom',
        'en': 'Name'
    },
    'marketplace_extension': {
        'fr': 'Extension',
        'en': 'Extension'
    },
    'marketplace_connection_status': {
        'fr': 'Statut',
        'en': 'Status'
    },
    'marketplace_last_connected': {
        'fr': 'Dernière connexion',
        'en': 'Last connected'
    },
    'marketplace_active': {
        'fr': 'Active',
        'en': 'Active'
    },
    'marketplace_pending': {
        'fr': 'En attente',
        'en': 'Pending'
    },
    'marketplace_error': {
        'fr': 'Erreur',
        'en': 'Error'
    },
    'marketplace_never_connected': {
        'fr': 'Jamais connecté',
        'en': 'Never connected'
    },
    'marketplace_test_connection': {
        'fr': 'Tester',
        'en': 'Test'
    },
    'marketplace_edit_connection': {
        'fr': 'Modifier',
        'en': 'Edit'
    },
    'marketplace_delete_connection': {
        'fr': 'Supprimer',
        'en': 'Delete'
    },
    'marketplace_confirm_delete': {
        'fr': 'Confirmer la suppression',
        'en': 'Confirm deletion'
    },
    'marketplace_delete_connection_confirm': {
        'fr': 'Êtes-vous sûr de vouloir supprimer la connexion',
        'en': 'Are you sure you want to delete the connection'
    },
    'marketplace_no_connections': {
        'fr': 'Aucune connexion API configurée',
        'en': 'No API connections configured'
    },
    'marketplace_connections_desc': {
        'fr': 'Gérez vos connexions aux API externes et intégrations tierces.',
        'en': 'Manage your connections to external APIs and third-party integrations.'
    },
    'marketplace_create_connection': {
        'fr': 'Créer une connexion',
        'en': 'Create a connection'
    },
    'marketplace_connections_empty_state': {
        'fr': 'Créez votre première connexion pour intégrer des API externes.',
        'en': 'Create your first connection to integrate external APIs.'
    },
    
    # Nouvelles fonctionnalités pour la page d'accueil
    'home.feature_marketing': {
        'fr': 'Automatisation du marketing digital',
        'en': 'Digital marketing automation'
    },
    'home.feature_training': {
        'fr': 'Formation et tutoriels interactifs',
        'en': 'Interactive training and tutorials'
    },
    'home.feature_marketplace': {
        'fr': 'Marketplace d\'extensions métier',
        'en': 'Business extensions marketplace'
    },
    'home.feature_export': {
        'fr': 'Exports multi-formats en un clic',
        'en': 'One-click multi-format exports'
    },
    'home.feature_marketing_desc': {
        'fr': 'Générateur de contenu IA, campagnes automatisées, calendrier éditorial',
        'en': 'AI content generator, automated campaigns, editorial calendar'
    },
    'home.feature_training_desc': {
        'fr': 'Parcours personnalisés, certifications, base de connaissances évolutive',
        'en': 'Custom learning paths, certifications, evolving knowledge base'
    },
    'home.feature_marketplace_desc': {
        'fr': 'Extensions métier, connecteurs personnalisés, intégrations tierces',
        'en': 'Business extensions, custom connectors, third-party integrations'
    },
    'home.feature_export_desc': {
        'fr': 'Export vers PDF, Excel, CSV, JSON avec aperçu instantané',
        'en': 'Export to PDF, Excel, CSV, JSON with instant preview'
    },
    'nav.predictive': {
        'fr': 'Intelligence Prédictive',
        'en': 'Predictive Intelligence'
    },
    'home.feature_predictive_desc': {
        'fr': 'Prévisions de ventes, analyse clients, optimisation catalogues',
        'en': 'Sales forecasting, customer analysis, catalog optimization'
    },
    'home.feature_modules': {
        'fr': 'Modules Métiers',
        'en': 'Business Modules'
    },
    'home.feature_modules_desc': {
        'fr': 'Catalogue extensible de modules spécialisés pour développer votre entreprise',
        'en': 'Extensible catalog of specialized modules to grow your business'
    },
    'Système de Modules': {
        'fr': 'Système de Modules',
        'en': 'Modules System'
    },
    'Système de Modules Métiers': {
        'fr': 'Système de Modules Métiers',
        'en': 'Business Modules System'
    },
    
    # Système de Modules - Textes spécifiques
    'modules.title': {
        'fr': 'Système de Modules Métiers',
        'en': 'Business Modules System'
    },
    'modules.subtitle': {
        'fr': 'Étendez les fonctionnalités de votre application avec des modules personnalisés',
        'en': 'Extend your application capabilities with custom modules'
    },
    'modules.explore_store': {
        'fr': 'Explorer la Boutique',
        'en': 'Explore Store'
    },
    'modules.my_modules': {
        'fr': 'Mes Modules',
        'en': 'My Modules'
    },
    'modules.login_to_install': {
        'fr': 'Se connecter pour installer des modules',
        'en': 'Login to install modules'
    },
    'modules.categories': {
        'fr': 'Catégories',
        'en': 'Categories'
    },
    'modules.explore': {
        'fr': 'Explorer',
        'en': 'Explore'
    },
    'modules.popular': {
        'fr': 'Modules populaires',
        'en': 'Popular Modules'
    },
    'modules.featured': {
        'fr': 'À découvrir',
        'en': 'Featured'
    },
    'modules.view_all': {
        'fr': 'Voir tous',
        'en': 'View all'
    },
    'modules.free': {
        'fr': 'Gratuit',
        'en': 'Free'
    },
    'modules.details': {
        'fr': 'Détails',
        'en': 'Details'
    },
    'modules.official': {
        'fr': 'Officiel',
        'en': 'Official'
    },
    'modules.installed': {
        'fr': 'Installé',
        'en': 'Installed'
    },
    'modules.marketplace': {
        'fr': 'Marché de Modules',
        'en': 'Modules Marketplace'
    },
    'modules.back': {
        'fr': 'Retour',
        'en': 'Back'
    },
    'modules.filters': {
        'fr': 'Filtres',
        'en': 'Filters'
    },
    'modules.sort_by': {
        'fr': 'Trier par',
        'en': 'Sort by'
    },
    'modules.sort_popular': {
        'fr': 'Populaires',
        'en': 'Popular'
    },
    'modules.sort_newest': {
        'fr': 'Nouveautés',
        'en': 'Newest'
    },
    'modules.sort_top_rated': {
        'fr': 'Mieux notés',
        'en': 'Top rated'
    },
    'modules.free_only': {
        'fr': 'Modules gratuits uniquement',
        'en': 'Free modules only'
    },
    'modules.official_only': {
        'fr': 'Modules officiels uniquement',
        'en': 'Official modules only'
    },
    'modules.previous': {
        'fr': 'Précédent',
        'en': 'Previous'
    },
    'modules.next': {
        'fr': 'Suivant',
        'en': 'Next'
    },
    'Étendez les fonctionnalités de votre application avec des modules personnalisés': {
        'fr': 'Étendez les fonctionnalités de votre application avec des modules personnalisés',
        'en': 'Extend your application features with custom modules'
    },
    'Explorer la Boutique': {
        'fr': 'Explorer la Boutique',
        'en': 'Explore the Store'
    },
    'Mes Modules': {
        'fr': 'Mes Modules',
        'en': 'My Modules'
    },
    'Se connecter pour installer des modules': {
        'fr': 'Se connecter pour installer des modules',
        'en': 'Log in to install modules'
    },
    'Catalogue de modules': {
        'fr': 'Catalogue de modules',
        'en': 'Module catalog'
    },
    'Notation et avis utilisateurs': {
        'fr': 'Notation et avis utilisateurs',
        'en': 'Ratings and user reviews'
    },
    'Gestion des versions': {
        'fr': 'Gestion des versions',
        'en': 'Version management'
    },
    'Installation à la volée': {
        'fr': 'Installation à la volée',
        'en': 'On-the-fly installation'
    },
    'Marché de Modules': {
        'fr': 'Marché de Modules',
        'en': 'Module Marketplace'
    },
    'Retour': {
        'fr': 'Retour',
        'en': 'Back'
    },
    'Filtres': {
        'fr': 'Filtres',
        'en': 'Filters'
    },
    'Explorer les modules': {
        'fr': 'Explorer les modules',
        'en': 'Explore modules'
    },
}