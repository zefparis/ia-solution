import datetime
import logging
import re
from decimal import Decimal
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from sqlalchemy import func, extract

from models import db, User, ExtractedText, Category, FinancialTransaction, Vendor, TaxReport, vendor_transaction
from auth import login_required, admin_required

# Configure logging
logger = logging.getLogger(__name__)

# Blueprint pour les fonctionnalités financières
finance_bp = Blueprint('finance', __name__, url_prefix='/finance')

def init_app(app):
    """Initialiser les routes financières pour l'application Flask"""
    app.register_blueprint(finance_bp, name='finance_original')
    
@finance_bp.route("/", methods=["GET"])
@login_required
def finance_dashboard():
    """Page principale de la comptabilité"""
    # Récupérer l'utilisateur actuel
    user = User.query.filter_by(username=session.get('username')).first()
    
    # Vérifier que l'utilisateur existe
    if not user:
        flash("Utilisateur non trouvé. Veuillez vous reconnecter.", "danger")
        return redirect(url_for('login'))
    
    # Récupérer les données financières
    transactions = FinancialTransaction.query.filter_by(user_id=user.id).order_by(FinancialTransaction.transaction_date.desc()).limit(5).all()
    categories = Category.query.filter_by(user_id=user.id).all()
    
    # Calcul des totaux
    total_income = db.session.query(func.sum(FinancialTransaction.amount)).filter(
        FinancialTransaction.user_id == user.id,
        FinancialTransaction.is_expense == False
    ).scalar() or Decimal('0.00')
    
    total_expenses = db.session.query(func.sum(FinancialTransaction.amount)).filter(
        FinancialTransaction.user_id == user.id,
        FinancialTransaction.is_expense == True
    ).scalar() or Decimal('0.00')
    
    balance = total_income - total_expenses
    
    # Récupérer les textes extraits non traités
    unprocessed_texts = ExtractedText.query.filter_by(
        user_id=user.id,
        is_processed=False
    ).order_by(ExtractedText.created_at.desc()).all()
    
    return render_template("finance/dashboard.html", 
                          transactions=transactions,
                          categories=categories,
                          total_income=total_income,
                          total_expenses=total_expenses,
                          balance=balance,
                          unprocessed_texts=unprocessed_texts)

    @app.route("/finance/texts", methods=["GET"])
    @login_required
    def finance_texts():
        """Afficher tous les textes extraits pour classification"""
        user = User.query.filter_by(username=session.get('username')).first()
        
        # Vérifier que l'utilisateur existe
        if not user:
            flash("Utilisateur non trouvé. Veuillez vous reconnecter.", "danger")
            return redirect(url_for('login'))
        
        texts = ExtractedText.query.filter_by(user_id=user.id).order_by(ExtractedText.created_at.desc()).all()
        
        return render_template("finance/texts.html", texts=texts)

    @app.route("/finance/process_text/<int:text_id>", methods=["GET", "POST"])
    @login_required
    def process_text(text_id):
        """Classifier et traiter un texte extrait"""
        user = User.query.filter_by(username=session.get('username')).first()
        
        # Vérifier que l'utilisateur existe
        if not user:
            flash("Utilisateur non trouvé. Veuillez vous reconnecter.", "danger")
            return redirect(url_for('login'))
            
        text = ExtractedText.query.filter_by(id=text_id, user_id=user.id).first_or_404()
        
        if request.method == "POST":
            # Récupérer les données du formulaire
            document_type = request.form.get('document_type')
            amount = request.form.get('amount')
            description = request.form.get('description')
            transaction_date = request.form.get('transaction_date')
            vendor_name = request.form.get('vendor_name')
            category_id = request.form.get('category_id')
            is_expense = request.form.get('is_expense') == 'expense'
            
            try:
                # Convertir la date
                transaction_date = datetime.datetime.strptime(transaction_date, '%Y-%m-%d').date()
                
                # Traiter le montant
                amount = Decimal(amount.replace(',', '.'))
                
                # Vérifier si le vendor existe déjà
                vendor = Vendor.query.filter_by(user_id=user.id, name=vendor_name).first()
                
                if not vendor and vendor_name:
                    # Créer un nouveau vendor
                    vendor = Vendor(
                        user_id=user.id,
                        name=vendor_name
                    )
                    db.session.add(vendor)
                    db.session.flush()  # Pour obtenir l'ID sans commit
                
                # Créer la transaction
                transaction = FinancialTransaction(
                    user_id=user.id,
                    amount=amount,
                    description=description,
                    transaction_date=transaction_date,
                    is_expense=is_expense,
                    category_id=category_id if category_id else None
                )
                
                db.session.add(transaction)
                db.session.flush()  # Pour obtenir l'ID sans commit
                
                # Lier la transaction au vendor si existant
                if vendor:
                    # Utiliser la table d'association
                    db.session.execute(
                        vendor_transaction.insert().values(
                            vendor_id=vendor.id,
                            transaction_id=transaction.id
                        )
                    )
                
                # Mettre à jour le texte comme traité
                text.is_processed = True
                text.document_type = document_type
                text.transaction_id = transaction.id
                
                db.session.commit()
                flash("Transaction créée avec succès !", "success")
                return redirect(url_for('finance.finance_dashboard'))
            
            except Exception as e:
                db.session.rollback()
                flash(f"Erreur lors du traitement : {str(e)}", "danger")
                logger.error(f"Error processing text {text_id}: {str(e)}")
        
        # GET request - afficher le formulaire
        categories = Category.query.filter_by(user_id=user.id).all()
        vendors = Vendor.query.filter_by(user_id=user.id).all()
        
        # Analyser le texte pour extraire des suggestions
        suggested_data = analyze_document_text(text.content)
        
        return render_template("finance/process_text.html", 
                              text=text, 
                              categories=categories,
                              vendors=vendors,
                              suggested_data=suggested_data)

    @app.route("/finance/categories", methods=["GET", "POST"])
    @login_required
    def manage_categories():
        """Gérer les catégories de dépenses et revenus"""
        user = User.query.filter_by(username=session.get('username')).first()
        
        # Vérifier que l'utilisateur existe
        if not user:
            flash("Utilisateur non trouvé. Veuillez vous reconnecter.", "danger")
            return redirect(url_for('login'))
        
        if request.method == "POST":
            action = request.form.get('action', 'create')
            
            if action == 'create':
                name = request.form.get('name')
                type = request.form.get('type')
                color = request.form.get('color', '#6c757d')
                icon = request.form.get('icon', 'tag')
                
                if name and type:
                    try:
                        category = Category(
                            user_id=user.id,
                            name=name,
                            type=type,
                            color=color,
                            icon=icon
                        )
                        db.session.add(category)
                        db.session.commit()
                        flash("Catégorie créée avec succès !", "success")
                    except Exception as e:
                        db.session.rollback()
                        flash(f"Erreur lors de la création : {str(e)}", "danger")
                else:
                    flash("Nom et type sont requis", "warning")
            
            elif action == 'delete':
                category_id = request.form.get('category_id')
                if category_id:
                    try:
                        category = Category.query.filter_by(id=category_id, user_id=user.id).first()
                        if category:
                            db.session.delete(category)
                            db.session.commit()
                            flash("Catégorie supprimée avec succès !", "success")
                    except Exception as e:
                        db.session.rollback()
                        flash(f"Erreur lors de la suppression : {str(e)}", "danger")
        
        # Charger toutes les catégories
        categories = Category.query.filter_by(user_id=user.id).all()
        return render_template("finance/categories.html", categories=categories)

    @app.route("/finance/transactions", methods=["GET"])
    @login_required
    def view_transactions():
        """Afficher toutes les transactions"""
        user = User.query.filter_by(username=session.get('username')).first()
        
        # Vérifier que l'utilisateur existe
        if not user:
            flash("Utilisateur non trouvé. Veuillez vous reconnecter.", "danger")
            return redirect(url_for('login'))
        
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        transactions = FinancialTransaction.query.filter_by(user_id=user.id).order_by(
            FinancialTransaction.transaction_date.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return render_template("finance/transactions.html", transactions=transactions)

    @app.route("/finance/transaction/add", methods=["GET", "POST"])
    @login_required
    def add_transaction():
        """Ajouter une nouvelle transaction"""
        user = User.query.filter_by(username=session.get('username')).first()
        
        # Vérifier que l'utilisateur existe
        if not user:
            flash("Utilisateur non trouvé. Veuillez vous reconnecter.", "danger")
            return redirect(url_for('login'))
        
        if request.method == "POST":
            amount = request.form.get('amount')
            description = request.form.get('description')
            transaction_date = request.form.get('transaction_date')
            vendor_name = request.form.get('vendor_name')
            category_id = request.form.get('category_id')
            is_expense = request.form.get('is_expense') == 'expense'
            payment_method = request.form.get('payment_method')
            tax_rate = request.form.get('tax_rate', '0')
            
            try:
                # Convertir la date
                transaction_date = datetime.datetime.strptime(transaction_date, '%Y-%m-%d').date()
                
                # Traiter le montant
                amount = Decimal(amount.replace(',', '.'))
                
                # Calculer la TVA si applicable
                tax_rate = Decimal(tax_rate.replace(',', '.') or '0')
                tax_amount = (amount * tax_rate / 100) if tax_rate else None
                
                # Vérifier si le vendor existe déjà
                vendor = Vendor.query.filter_by(user_id=user.id, name=vendor_name).first()
                
                if not vendor and vendor_name:
                    # Créer un nouveau vendor
                    vendor = Vendor(
                        user_id=user.id,
                        name=vendor_name
                    )
                    db.session.add(vendor)
                    db.session.flush()  # Pour obtenir l'ID sans commit
                
                # Créer la transaction
                transaction = FinancialTransaction(
                    user_id=user.id,
                    amount=amount,
                    description=description,
                    transaction_date=transaction_date,
                    is_expense=is_expense,
                    category_id=category_id if category_id else None,
                    payment_method=payment_method,
                    tax_rate=tax_rate,
                    tax_amount=tax_amount
                )
                
                db.session.add(transaction)
                db.session.flush()  # Pour obtenir l'ID sans commit
                
                # Lier la transaction au vendor si existant
                if vendor:
                    # Utiliser la table d'association
                    db.session.execute(
                        vendor_transaction.insert().values(
                            vendor_id=vendor.id,
                            transaction_id=transaction.id
                        )
                    )
                
                db.session.commit()
                flash("Transaction ajoutée avec succès !", "success")
                return redirect(url_for('finance.view_transactions'))
            
            except Exception as e:
                db.session.rollback()
                flash(f"Erreur lors de l'ajout : {str(e)}", "danger")
                logger.error(f"Error adding transaction: {str(e)}")
        
        # GET request - afficher le formulaire
        categories = Category.query.filter_by(user_id=user.id).all()
        vendors = Vendor.query.filter_by(user_id=user.id).all()
        
        return render_template("finance/add_transaction.html", 
                              categories=categories,
                              vendors=vendors)

    @app.route("/finance/reports", methods=["GET"])
    @login_required
    def financial_reports():
        """Afficher les rapports financiers"""
        user = User.query.filter_by(username=session.get('username')).first()
        
        # Vérifier que l'utilisateur existe
        if not user:
            flash("Utilisateur non trouvé. Veuillez vous reconnecter.", "danger")
            return redirect(url_for('login'))
        
        # Paramètres de période
        period = request.args.get('period', 'month')
        year = request.args.get('year', datetime.datetime.now().year, type=int)
        month = request.args.get('month', datetime.datetime.now().month, type=int)
        
        # Définir la période de temps
        if period == 'month':
            start_date = datetime.date(year, month, 1)
            if month == 12:
                end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                end_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
        elif period == 'quarter':
            quarter = (month - 1) // 3 + 1
            start_date = datetime.date(year, 3 * quarter - 2, 1)
            if quarter == 4:
                end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                end_date = datetime.date(year, 3 * quarter + 1, 1) - datetime.timedelta(days=1)
        elif period == 'year':
            start_date = datetime.date(year, 1, 1)
            end_date = datetime.date(year, 12, 31)
        else:
            # Défaut: mois courant
            start_date = datetime.date(year, month, 1)
            if month == 12:
                end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                end_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
        
        # Récupérer les dépenses par catégorie
        expense_by_category = db.session.query(
            Category.name,
            Category.color,
            func.sum(FinancialTransaction.amount).label('total')
        ).join(FinancialTransaction, FinancialTransaction.category_id == Category.id)\
         .filter(
            FinancialTransaction.user_id == user.id,
            FinancialTransaction.is_expense == True,
            FinancialTransaction.transaction_date >= start_date,
            FinancialTransaction.transaction_date <= end_date
        ).group_by(Category.id).all()
        
        # Récupérer les revenus par catégorie
        income_by_category = db.session.query(
            Category.name,
            Category.color,
            func.sum(FinancialTransaction.amount).label('total')
        ).join(FinancialTransaction, FinancialTransaction.category_id == Category.id)\
         .filter(
            FinancialTransaction.user_id == user.id,
            FinancialTransaction.is_expense == False,
            FinancialTransaction.transaction_date >= start_date,
            FinancialTransaction.transaction_date <= end_date
        ).group_by(Category.id).all()
        
        # Récupérer les totaux
        total_income = db.session.query(func.sum(FinancialTransaction.amount)).filter(
            FinancialTransaction.user_id == user.id,
            FinancialTransaction.is_expense == False,
            FinancialTransaction.transaction_date >= start_date,
            FinancialTransaction.transaction_date <= end_date
        ).scalar() or Decimal('0.00')
        
        total_expenses = db.session.query(func.sum(FinancialTransaction.amount)).filter(
            FinancialTransaction.user_id == user.id,
            FinancialTransaction.is_expense == True,
            FinancialTransaction.transaction_date >= start_date,
            FinancialTransaction.transaction_date <= end_date
        ).scalar() or Decimal('0.00')
        
        total_tax = db.session.query(func.sum(FinancialTransaction.tax_amount)).filter(
            FinancialTransaction.user_id == user.id,
            FinancialTransaction.tax_amount != None,
            FinancialTransaction.transaction_date >= start_date,
            FinancialTransaction.transaction_date <= end_date
        ).scalar() or Decimal('0.00')
        
        # Calculer le bénéfice net
        net_profit = total_income - total_expenses
        
        # Créer des listes pour le graphique
        expense_labels = [c[0] for c in expense_by_category]
        expense_data = [float(c[2]) for c in expense_by_category]
        expense_colors = [c[1] for c in expense_by_category]
        
        income_labels = [c[0] for c in income_by_category]
        income_data = [float(c[2]) for c in income_by_category]
        income_colors = [c[1] for c in income_by_category]
        
        # Récupérer les rapports fiscaux déjà générés par l'utilisateur
        reports = TaxReport.query.filter_by(user_id=user.id).order_by(TaxReport.created_at.desc()).all()
        
        # Vérifier si la clé API OpenAI est disponible
        import os
        has_openai_key = bool(os.environ.get("OPENAI_API_KEY"))
        
        return render_template("finance/reports.html",
                              period=period,
                              year=year,
                              month=month,
                              start_date=start_date,
                              end_date=end_date,
                              expense_by_category=expense_by_category,
                              income_by_category=income_by_category,
                              total_income=total_income,
                              total_expenses=total_expenses,
                              total_tax=total_tax,
                              net_profit=net_profit,
                              expense_labels=expense_labels,
                              expense_data=expense_data,
                              expense_colors=expense_colors,
                              income_labels=income_labels,
                              income_data=income_data,
                              income_colors=income_colors,
                              reports=reports,
                              has_openai_key=has_openai_key)

    @app.route("/finance/tax-report/generate", methods=["POST"])
    @login_required
    def generate_tax_report():
        """Générer un rapport fiscal pour une période donnée"""
        import os
        user = User.query.filter_by(username=session.get('username')).first()
        
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        report_type = request.form.get('report_type')
        title = request.form.get('title')
        
        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            # Récupérer toutes les transactions pour la période
            transactions = FinancialTransaction.query.filter(
                FinancialTransaction.user_id == user.id,
                FinancialTransaction.transaction_date >= start_date,
                FinancialTransaction.transaction_date <= end_date
            ).order_by(FinancialTransaction.transaction_date).all()
            
            # Préparer les données à sauvegarder dans la base
            total_income = db.session.query(func.sum(FinancialTransaction.amount)).filter(
                FinancialTransaction.user_id == user.id,
                FinancialTransaction.is_expense == False,
                FinancialTransaction.transaction_date >= start_date,
                FinancialTransaction.transaction_date <= end_date
            ).scalar() or Decimal('0.00')
            
            total_expenses = db.session.query(func.sum(FinancialTransaction.amount)).filter(
                FinancialTransaction.user_id == user.id,
                FinancialTransaction.is_expense == True,
                FinancialTransaction.transaction_date >= start_date,
                FinancialTransaction.transaction_date <= end_date
            ).scalar() or Decimal('0.00')
            
            total_tax = db.session.query(func.sum(FinancialTransaction.tax_amount)).filter(
                FinancialTransaction.user_id == user.id,
                FinancialTransaction.tax_amount != None,
                FinancialTransaction.transaction_date >= start_date,
                FinancialTransaction.transaction_date <= end_date
            ).scalar() or Decimal('0.00')
            
            # Calculer le bénéfice net
            net_profit = total_income - total_expenses
            
            # Générer le contenu du rapport amélioré si OpenAI est disponible
            report_content = None
            if os.environ.get("OPENAI_API_KEY") and transactions:
                try:
                    import openai_integration
                    
                    # Convertir les transactions en format compatible avec l'API
                    transactions_data = []
                    for transaction in transactions:
                        category_name = transaction.category.name if transaction.category else "Non catégorisé"
                        
                        # Obtenir les noms des vendeurs pour cette transaction
                        vendor_names = [vendor.name for vendor in transaction.vendors]
                        vendor_name = vendor_names[0] if vendor_names else "Inconnu"
                        
                        transactions_data.append({
                            "id": transaction.id,
                            "date": transaction.transaction_date.strftime('%Y-%m-%d'),
                            "amount": float(transaction.amount),
                            "description": transaction.description,
                            "is_expense": transaction.is_expense,
                            "category": category_name,
                            "vendor": vendor_name,
                            "payment_method": transaction.payment_method,
                            "tax_rate": float(transaction.tax_rate) if transaction.tax_rate else None,
                            "tax_amount": float(transaction.tax_amount) if transaction.tax_amount else None
                        })
                    
                    # Informations sur l'utilisateur pour personnaliser le rapport
                    user_info = {
                        "name": user.display_name or user.username,
                        "email": user.email,
                        "date_format": "DD/MM/YYYY",  # Format français par défaut
                        "currency": "EUR",
                        "language": "fr"
                    }
                    
                    # Générer le rapport avec l'IA
                    report_content = openai_integration.generate_tax_report(
                        transactions_data, 
                        start_date_str, 
                        end_date_str,
                        user_info
                    )
                    
                    # Le contenu sera sauvegardé dans report_html ci-dessous
                    
                except Exception as e:
                    logger.error(f"Erreur lors de la génération du rapport avec OpenAI: {e}")
                    # On continue avec le rapport basique
            
            # Créer le rapport dans la base de données
            tax_report = TaxReport(
                user_id=user.id,
                title=title,
                start_date=start_date,
                end_date=end_date,
                report_type=report_type,
                total_income=total_income,
                total_expenses=total_expenses,
                total_tax=total_tax,
                net_profit=net_profit,
                status='draft',
                report_html=report_content  # Si None, le rapport sera généré de manière basique à l'affichage
            )
            
            db.session.add(tax_report)
            db.session.commit()
            
            flash("Rapport fiscal généré avec succès !", "success")
            return redirect(url_for('financial_reports'))
        
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de la génération du rapport : {str(e)}", "danger")
            logger.error(f"Error generating tax report: {str(e)}")
            return redirect(url_for('financial_reports'))


def analyze_document_text(text):
    """Analyser le texte d'un document et essayer d'extraire les informations pertinentes"""
    import os
    
    # Si la clé API OpenAI est disponible, utiliser l'IA avancée
    if os.environ.get("OPENAI_API_KEY"):
        try:
            # Importer le module OpenAI (importation tardive pour éviter les erreurs si le module n'est pas disponible)
            import openai_integration
            
            # Utiliser OpenAI pour une analyse complète et précise
            result = openai_integration.analyze_document(text)
            
            # Ajouter un message pour indiquer que l'analyse a été faite par IA
            result['analyzed_by'] = 'openai'
            
            # Vérifier que les champs requis sont présents et ajouter des valeurs par défaut si nécessaire
            if not result.get('amount'):
                result['amount'] = None
            if not result.get('date'):
                result['date'] = None
            if not result.get('vendor'):
                result['vendor'] = None
            if not result.get('document_type'):
                result['document_type'] = 'inconnu'
            if not result.get('confidence'):
                result['confidence'] = 0.5
                
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse OpenAI: {e}")
            # En cas d'erreur, on utilise l'ancienne méthode
            return analyze_document_text_legacy(text)
    else:
        # Si pas de clé API, utiliser l'ancienne méthode
        return analyze_document_text_legacy(text)

def analyze_document_text_legacy(text):
    """Analyser le texte d'un document avec des expressions régulières (méthode traditionnelle)"""
    # Initialiser les valeurs par défaut
    suggested_data = {
        'amount': None,
        'date': None,
        'vendor': None,
        'document_type': None,
        'confidence': 0.3,  # Confiance plus faible pour cette méthode
        'analyzed_by': 'regex'
    }
    
    try:
        # Rechercher un montant (pattern: nombres avec virgule/point)
        amount_patterns = [
            r'montant\s*(?:total)?\s*:?\s*(\d+[.,]\d{2})',  # montant 123,45
            r'total\s*:?\s*(\d+[.,]\d{2})',                # total: 123,45
            r'(?:€|EUR)\s*(\d+[.,]\d{2})',                  # EUR 123,45
            r'(\d+[.,]\d{2})\s*(?:€|EUR)',                  # 123,45 €
            r'(?<!\d)(\d+[.,]\d{2})(?!\d)'                  # 123,45 isolé
        ]
        
        for pattern in amount_patterns:
            amount_match = re.search(pattern, text, re.IGNORECASE)
            if amount_match:
                suggested_data['amount'] = amount_match.group(1).replace(',', '.')
                break
        
        # Rechercher une date (formats communs)
        date_patterns = [
            r'date\s*:?\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',  # date: 31/12/2023
            r'(?<!\d)(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})(?!\d)',  # 31/12/2023 isolé
            r'(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{2,4})' # 31 décembre 2023
        ]
        
        for pattern in date_patterns:
            date_match = re.search(pattern, text, re.IGNORECASE)
            if date_match:
                date_str = date_match.group(1)
                # On ne convertit pas encore, juste on suggère le format trouvé
                suggested_data['date'] = date_str
                break
        
        # Rechercher un nom de vendeur (souvent en haut des factures)
        # C'est plus complexe et moins précis, on prend les premières lignes
        lines = text.split('\n')
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        
        if non_empty_lines:
            # Souvent, le nom du vendeur est dans les premières lignes non vides
            potential_vendor = non_empty_lines[0]
            # Ignorer les lignes trop courtes ou trop longues
            if 3 < len(potential_vendor) < 50:
                suggested_data['vendor'] = potential_vendor
        
        # Deviner le type de document
        doc_type_keywords = {
            'facture': ['facture', 'invoice', 'numéro de facture'],
            'reçu': ['reçu', 'ticket', 'caisse', 'receipt'],
            'devis': ['devis', 'estimation', 'quote'],
            'relevé': ['relevé', 'bancaire', 'statement']
        }
        
        for doc_type, keywords in doc_type_keywords.items():
            for keyword in keywords:
                if re.search(r'\b' + keyword + r'\b', text, re.IGNORECASE):
                    suggested_data['document_type'] = doc_type
                    break
            if suggested_data['document_type']:
                break
        
        # Si aucun type détecté, considérer comme inconnu
        if not suggested_data['document_type']:
            suggested_data['document_type'] = 'inconnu'
        
        # Si on a trouvé au moins deux informations, augmenter la confiance
        if (suggested_data['amount'] and suggested_data['date']) or \
           (suggested_data['amount'] and suggested_data['vendor']) or \
           (suggested_data['date'] and suggested_data['vendor']):
            suggested_data['confidence'] = 0.6
        
        # Si on a trouvé toutes les informations clés, confiance plus élevée
        if suggested_data['amount'] and suggested_data['date'] and suggested_data['vendor']:
            suggested_data['confidence'] = 0.8
        
    except Exception as e:
        logger.error(f"Error analyzing document text with regex: {str(e)}")
    
    return suggested_data