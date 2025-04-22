import datetime
import logging
import os
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
    app.register_blueprint(finance_bp)

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

@finance_bp.route("/texts", methods=["GET"])
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

@finance_bp.route("/process_text/<int:text_id>", methods=["GET", "POST"])
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

@finance_bp.route("/categories", methods=["GET", "POST"])
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

@finance_bp.route("/transactions", methods=["GET"])
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

@finance_bp.route("/transaction/add", methods=["GET", "POST"])
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

@finance_bp.route("/reports", methods=["GET"])
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
    ).join(
        FinancialTransaction, 
        FinancialTransaction.category_id == Category.id
    ).filter(
        FinancialTransaction.user_id == user.id,
        FinancialTransaction.is_expense == True,
        FinancialTransaction.transaction_date.between(start_date, end_date)
    ).group_by(
        Category.id
    ).all()
    
    # Récupérer les revenus par catégorie
    income_by_category = db.session.query(
        Category.name,
        Category.color,
        func.sum(FinancialTransaction.amount).label('total')
    ).join(
        FinancialTransaction, 
        FinancialTransaction.category_id == Category.id
    ).filter(
        FinancialTransaction.user_id == user.id,
        FinancialTransaction.is_expense == False,
        FinancialTransaction.transaction_date.between(start_date, end_date)
    ).group_by(
        Category.id
    ).all()
    
    # Récupérer les dépenses par mois (pour l'année en cours)
    expenses_by_month = []
    incomes_by_month = []
    
    if period == 'year':
        for m in range(1, 13):
            # Définir le début et la fin du mois
            m_start = datetime.date(year, m, 1)
            if m == 12:
                m_end = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                m_end = datetime.date(year, m + 1, 1) - datetime.timedelta(days=1)
            
            # Dépenses du mois
            month_expense = db.session.query(func.sum(FinancialTransaction.amount)).filter(
                FinancialTransaction.user_id == user.id,
                FinancialTransaction.is_expense == True,
                FinancialTransaction.transaction_date.between(m_start, m_end)
            ).scalar() or 0
            
            # Revenus du mois
            month_income = db.session.query(func.sum(FinancialTransaction.amount)).filter(
                FinancialTransaction.user_id == user.id,
                FinancialTransaction.is_expense == False,
                FinancialTransaction.transaction_date.between(m_start, m_end)
            ).scalar() or 0
            
            expenses_by_month.append(float(month_expense))
            incomes_by_month.append(float(month_income))
    
    # Calculer les totaux pour la période
    total_income = db.session.query(func.sum(FinancialTransaction.amount)).filter(
        FinancialTransaction.user_id == user.id,
        FinancialTransaction.is_expense == False,
        FinancialTransaction.transaction_date.between(start_date, end_date)
    ).scalar() or Decimal('0.00')
    
    total_expenses = db.session.query(func.sum(FinancialTransaction.amount)).filter(
        FinancialTransaction.user_id == user.id,
        FinancialTransaction.is_expense == True,
        FinancialTransaction.transaction_date.between(start_date, end_date)
    ).scalar() or Decimal('0.00')
    
    balance = total_income - total_expenses
    
    # Préparer les données pour les graphiques
    expense_data = {
        'labels': [cat.name for cat in expense_by_category],
        'values': [float(cat.total) for cat in expense_by_category],
        'colors': [cat.color for cat in expense_by_category]
    }
    
    income_data = {
        'labels': [cat.name for cat in income_by_category],
        'values': [float(cat.total) for cat in income_by_category],
        'colors': [cat.color for cat in income_by_category]
    }
    
    # Calculer le total de TVA (taxe)
    total_tax = db.session.query(func.sum(FinancialTransaction.tax_amount)).filter(
        FinancialTransaction.user_id == user.id,
        FinancialTransaction.tax_amount.isnot(None),
        FinancialTransaction.transaction_date.between(start_date, end_date)
    ).scalar() or Decimal('0.00')
    
    # Calculer le profit net (revenu - dépenses)
    net_profit = total_income - total_expenses
    
    return render_template("finance/reports.html",
                          period=period,
                          year=year,
                          month=month,
                          start_date=start_date,
                          end_date=end_date,
                          total_income=total_income,
                          total_expenses=total_expenses,
                          total_tax=total_tax,
                          balance=balance,
                          net_profit=net_profit,
                          expense_data=expense_data,
                          income_data=income_data,
                          expenses_by_month=expenses_by_month,
                          incomes_by_month=incomes_by_month)

@finance_bp.route("/tax_report", methods=["GET", "POST"])
@login_required
def generate_tax_report():
    """Générer un rapport fiscal pour une période donnée"""
    user = User.query.filter_by(username=session.get('username')).first()
    
    # Vérifier que l'utilisateur existe
    if not user:
        flash("Utilisateur non trouvé. Veuillez vous reconnecter.", "danger")
        return redirect(url_for('login'))
    
    if request.method == "POST":
        report_name = request.form.get('report_name')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        try:
            # Convertir les dates
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            # Calculer les totaux
            total_income = db.session.query(func.sum(FinancialTransaction.amount)).filter(
                FinancialTransaction.user_id == user.id,
                FinancialTransaction.is_expense == False,
                FinancialTransaction.transaction_date.between(start_date, end_date)
            ).scalar() or Decimal('0.00')
            
            total_expenses = db.session.query(func.sum(FinancialTransaction.amount)).filter(
                FinancialTransaction.user_id == user.id,
                FinancialTransaction.is_expense == True,
                FinancialTransaction.transaction_date.between(start_date, end_date)
            ).scalar() or Decimal('0.00')
            
            # Calculer le total de TVA (taxe)
            total_tax = db.session.query(func.sum(FinancialTransaction.tax_amount)).filter(
                FinancialTransaction.user_id == user.id,
                FinancialTransaction.tax_amount.isnot(None),
                FinancialTransaction.transaction_date.between(start_date, end_date)
            ).scalar() or Decimal('0.00')
            
            # Profit avant impôts
            profit = total_income - total_expenses
            
            # Créer l'objet TaxReport en utilisant le modèle existant
            tax_report = TaxReport(
                user_id=user.id,
                title=report_name,  # Utiliser title qui est obligatoire
                name=report_name,   # Ajouter aussi name pour notre nouvelle interface
                start_date=start_date,
                end_date=end_date,
                total_income=total_income,
                total_expenses=total_expenses,
                total_tax=total_tax,
                profit=profit,
                net_profit=profit,  # Pour la compatibilité avec le modèle existant
                report_type='fiscal'  # Type spécifique pour les rapports fiscaux
            )
            
            db.session.add(tax_report)
            db.session.commit()
            
            flash("Rapport fiscal généré avec succès!", "success")
            return redirect(url_for('finance.view_tax_report', report_id=tax_report.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de la génération du rapport: {str(e)}", "danger")
            logger.error(f"Error generating tax report: {str(e)}")
    
    # GET request - afficher le formulaire
    reports = TaxReport.query.filter_by(user_id=user.id).order_by(TaxReport.created_at.desc()).all()
    
    return render_template("finance/tax_report.html", reports=reports)

@finance_bp.route("/tax_report/<int:report_id>", methods=["GET"])
@login_required
def view_tax_report(report_id):
    """Voir un rapport fiscal spécifique"""
    user = User.query.filter_by(username=session.get('username')).first()
    
    # Vérifier que l'utilisateur existe
    if not user:
        flash("Utilisateur non trouvé. Veuillez vous reconnecter.", "danger")
        return redirect(url_for('login'))
    
    # Récupérer le rapport
    report = TaxReport.query.filter_by(id=report_id, user_id=user.id).first_or_404()
    
    # Vérifier si on demande un format spécifique (PDF)
    if request.args.get('format') == 'pdf':
        return generate_tax_report_pdf(report)
    
    # Récupérer les détails des transactions pour ce rapport
    transactions = FinancialTransaction.query.filter(
        FinancialTransaction.user_id == user.id,
        FinancialTransaction.transaction_date.between(report.start_date, report.end_date)
    ).order_by(FinancialTransaction.transaction_date).all()
    
    # Grouper par type (dépense/revenu)
    expenses = [t for t in transactions if t.is_expense]
    incomes = [t for t in transactions if not t.is_expense]
    
    # Obtenir les catégories de dépenses avec les montants totaux
    expense_by_category = db.session.query(
        Category.name,
        Category.color,
        func.sum(FinancialTransaction.amount).label('total')
    ).join(
        FinancialTransaction, 
        FinancialTransaction.category_id == Category.id
    ).filter(
        FinancialTransaction.user_id == user.id,
        FinancialTransaction.is_expense == True,
        FinancialTransaction.transaction_date.between(report.start_date, report.end_date)
    ).group_by(
        Category.id
    ).all()
    
    # Obtenir les catégories de revenus avec les montants totaux
    income_by_category = db.session.query(
        Category.name,
        Category.color,
        func.sum(FinancialTransaction.amount).label('total')
    ).join(
        FinancialTransaction, 
        FinancialTransaction.category_id == Category.id
    ).filter(
        FinancialTransaction.user_id == user.id,
        FinancialTransaction.is_expense == False,
        FinancialTransaction.transaction_date.between(report.start_date, report.end_date)
    ).group_by(
        Category.id
    ).all()
    
    # Préparer les données pour les graphiques
    expense_data = {
        'labels': [cat.name for cat in expense_by_category],
        'data': [float(cat.total) for cat in expense_by_category],
        'colors': [cat.color for cat in expense_by_category]
    }
    
    income_data = {
        'labels': [cat.name for cat in income_by_category],
        'data': [float(cat.total) for cat in income_by_category],
        'colors': [cat.color for cat in income_by_category]
    }
    
    return render_template("finance/view_tax_report.html", 
                          report=report,
                          expenses=expenses,
                          incomes=incomes,
                          expense_by_category=expense_by_category,
                          income_by_category=income_by_category,
                          expense_data=expense_data,
                          income_data=income_data)

@finance_bp.route("/tax_report/<int:report_id>/notes", methods=["POST"])
@login_required
def save_tax_report_notes(report_id):
    """Enregistrer les notes d'un rapport fiscal"""
    user = User.query.filter_by(username=session.get('username')).first()
    
    if not user:
        return jsonify({"success": False, "error": "Utilisateur non authentifié"}), 401
    
    # Récupérer le rapport
    report = TaxReport.query.filter_by(id=report_id, user_id=user.id).first_or_404()
    
    # Récupérer les notes depuis les données JSON
    data = request.get_json()
    notes = data.get('notes', '')
    
    try:
        # Mise à jour des notes
        report.notes = notes
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving tax report notes: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
        
@finance_bp.route("/tax_report/<int:report_id>/generate_ai", methods=["POST"])
@login_required
def generate_tax_report_ai_analysis(report_id):
    """Générer une analyse IA pour un rapport fiscal"""
    user = User.query.filter_by(username=session.get('username')).first()
    
    if not user:
        return jsonify({"success": False, "error": "Utilisateur non authentifié"}), 401
    
    # Récupérer le rapport
    report = TaxReport.query.filter_by(id=report_id, user_id=user.id).first_or_404()
    
    try:
        # Récupérer les transactions pour ce rapport
        transactions = FinancialTransaction.query.filter(
            FinancialTransaction.user_id == user.id,
            FinancialTransaction.transaction_date.between(report.start_date, report.end_date)
        ).order_by(FinancialTransaction.transaction_date).all()
        
        # Préparer les données pour l'analyse
        financial_data = {
            "total_income": float(report.total_income),
            "total_expenses": float(report.total_expenses),
            "total_tax": float(report.total_tax),
            "profit": float(report.profit),
            "start_date": report.start_date.strftime('%d/%m/%Y'),
            "end_date": report.end_date.strftime('%d/%m/%Y'),
            "expenses_by_category": {},
            "income_by_category": {}
        }
        
        # Calculer les dépenses par catégorie
        for t in [t for t in transactions if t.is_expense]:
            category_name = t.category.name if t.category else "Non classé"
            if category_name not in financial_data["expenses_by_category"]:
                financial_data["expenses_by_category"][category_name] = 0.0
            financial_data["expenses_by_category"][category_name] += float(t.amount)
        
        # Calculer les revenus par catégorie
        for t in [t for t in transactions if not t.is_expense]:
            category_name = t.category.name if t.category else "Non classé"
            if category_name not in financial_data["income_by_category"]:
                financial_data["income_by_category"][category_name] = 0.0
            financial_data["income_by_category"][category_name] += float(t.amount)
        
        # Appeler l'API OpenAI pour l'analyse
        analysis_html = generate_financial_analysis(financial_data)
        
        if analysis_html:
            # Mise à jour du rapport avec l'analyse
            report.ai_analysis = analysis_html
            db.session.commit()
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Impossible de générer l'analyse IA"}), 500
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error generating AI analysis: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

def generate_tax_report_pdf(report):
    """Générer un PDF pour un rapport fiscal"""
    # TODO: Implémenter la génération de PDF
    # Pour l'instant, on redirige vers la page web avec un message
    flash("La génération de PDF n'est pas encore disponible.", "info")
    return redirect(url_for('finance.view_tax_report', report_id=report.id))

# Fonctions utilitaires (à garder en dehors des routes)
def analyze_document_text(text):
    """Analyser le texte d'un document et essayer d'extraire les informations pertinentes"""
    try:
        # Utiliser une IA pour extraire les informations
        # TODO: Intégrer avec le modèle OpenAI pour une analyse plus intelligente
        
        # En attendant, utiliser des expressions régulières basiques
        result = analyze_document_text_legacy(text)
        
        return result
    except Exception as e:
        logger.error(f"Error analyzing document text: {str(e)}")
        return {}

def generate_financial_analysis(financial_data):
    """
    Génère une analyse financière en utilisant l'API OpenAI
    
    Args:
        financial_data (dict): Données financières à analyser
        
    Returns:
        str: Analyse HTML formatée ou None en cas d'erreur
    """
    try:
        # Vérifier si la clé API OpenAI est disponible
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        if not openai_api_key:
            return "<div class='alert alert-warning'>Clé API OpenAI non configurée. Veuillez configurer une clé API pour obtenir une analyse détaillée.</div>"
        
        # Préparer le prompt pour OpenAI
        prompt = f"""
        Je suis un analyste financier professionnel. Je vais analyser les données financières suivantes pour la période du {financial_data['start_date']} au {financial_data['end_date']} :
        
        Revenus totaux: {financial_data['total_income']} €
        Dépenses totales: {financial_data['total_expenses']} €
        TVA collectée: {financial_data['total_tax']} €
        Bénéfice net: {financial_data['profit']} €
        
        Dépenses par catégorie:
        {", ".join([f"{cat}: {amount} €" for cat, amount in financial_data['expenses_by_category'].items()])}
        
        Revenus par catégorie:
        {", ".join([f"{cat}: {amount} €" for cat, amount in financial_data['income_by_category'].items()])}
        
        Merci de me fournir:
        1. Une analyse SWOT (forces, faiblesses, opportunités, menaces) basée sur ces données
        2. Des recommandations concrètes pour améliorer la situation financière
        3. Une évaluation de la santé financière globale
        4. Des conseils fiscaux pertinents
        
        Format ta réponse en HTML avec des sections séparées, des titres h3, des listes à puces et des paragraphes. Utilise des classes Bootstrap pour le formatage (par exemple, text-success, text-danger, alert alert-info).
        """
        
        # Appeler l'API OpenAI
        from openai import OpenAI
        client = OpenAI(api_key=openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4",  # Utiliser gpt-4 car notre compte n'a pas accès à gpt-4o
            messages=[
                {"role": "system", "content": "Tu es un expert en analyse financière qui fournit des conseils précis et pratiques."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1200,
            temperature=0.5
        )
        
        analysis_html = response.choices[0].message.content
        return analysis_html
    
    except Exception as e:
        logger.error(f"Error generating financial analysis: {str(e)}")
        return f"<div class='alert alert-danger'>Erreur lors de l'analyse: {str(e)}</div>"

def analyze_document_text_legacy(text):
    """Analyser le texte d'un document avec des expressions régulières (méthode traditionnelle)"""
    result = {}
    
    # Détection de montants - recherche de patterns comme "123,45 €" ou "123.45€"
    amount_patterns = [
        r'(\d+[,.]\d+)\s*€',  # 123,45 €
        r'(\d+[,.]\d+)€',    # 123,45€
        r'€\s*(\d+[,.]\d+)',  # € 123,45
        r'TOTAL\s*:?\s*(\d+[,.]\d+)',  # TOTAL: 123,45
        r'MONTANT\s*:?\s*(\d+[,.]\d+)'  # MONTANT: 123,45
    ]
    
    for pattern in amount_patterns:
        match = re.search(pattern, text)
        if match:
            result['amount'] = match.group(1).replace(',', '.')
            break
    
    # Détection de date - recherche de patterns comme "01/01/2025" ou "2025-01-01"
    date_patterns = [
        r'(\d{2}/\d{2}/\d{4})',  # 01/01/2025
        r'(\d{2}-\d{2}-\d{4})',  # 01-01-2025
        r'(\d{4}-\d{2}-\d{2})',  # 2025-01-01
        r'Date\s*:?\s*(\d{2}[/-]\d{2}[/-]\d{4})',  # Date: 01/01/2025
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            # Convertir en format YYYY-MM-DD pour le formulaire
            if '/' in date_str:
                parts = date_str.split('/')
                if len(parts[2]) == 4:  # Format DD/MM/YYYY
                    result['date'] = f"{parts[2]}-{parts[1]}-{parts[0]}"
                else:  # Format MM/DD/YYYY ou autre
                    result['date'] = datetime.datetime.now().strftime('%Y-%m-%d')
            elif '-' in date_str:
                parts = date_str.split('-')
                if len(parts[0]) == 4:  # Format YYYY-MM-DD
                    result['date'] = date_str
                else:  # Format DD-MM-YYYY
                    result['date'] = f"{parts[2]}-{parts[1]}-{parts[0]}"
            break
    
    # Si pas de date trouvée, utiliser la date du jour
    if 'date' not in result:
        result['date'] = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # Détection de vendeur/fournisseur
    vendor_patterns = [
        r'VENDEUR\s*:?\s*([A-Za-z0-9\s]+)',
        r'FOURNISSEUR\s*:?\s*([A-Za-z0-9\s]+)',
        r'MAGASIN\s*:?\s*([A-Za-z0-9\s]+)',
        r'BOUTIQUE\s*:?\s*([A-Za-z0-9\s]+)',
    ]
    
    for pattern in vendor_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['vendor'] = match.group(1).strip()
            break
    
    # Détection de taux de TVA
    tax_patterns = [
        r'TVA\s+(\d+[,.]\d+)%',  # TVA 20,00%
        r'TVA\s*:?\s*(\d+[,.]\d+)%',  # TVA: 20,00%
        r'T\.V\.A\.\s*(\d+[,.]\d+)%',  # T.V.A. 20,00%
    ]
    
    for pattern in tax_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['tax_rate'] = match.group(1).replace(',', '.')
            break
    
    # Type de document (facture, reçu, ticket)
    if 'FACTURE' in text.upper():
        result['document_type'] = 'invoice'
    elif 'REÇU' in text.upper() or 'RECU' in text.upper():
        result['document_type'] = 'receipt'
    elif 'TICKET' in text.upper():
        result['document_type'] = 'receipt'
    else:
        result['document_type'] = 'unknown'
    
    return result