import logging
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from enum import Enum
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from sqlalchemy import func, extract, desc
from models import User, db, ExtractedText, FinancialTransaction as Transaction, Category 
from models import Invoice, Quote, Customer
from models_business import BusinessReport
from dashboard_models import TransactionCategory, Transaction as DashboardTransaction, CashflowPrediction, FinancialAlert, DashboardSettings
from auth import login_required

# États des factures
class InvoiceStatus(Enum):
    DRAFT = 'draft'
    SENT = 'sent'
    PAID = 'paid'
    OVERDUE = 'overdue'
    CANCELLED = 'cancelled'

# Définir TransactionType comme une énumération
class TransactionType(Enum):
    INCOME = 'income'
    EXPENSE = 'expense'

# Configurer le logging
logger = logging.getLogger(__name__)

# Blueprint pour le tableau de bord
unified_dashboard_bp = Blueprint('unified_dashboard', __name__, url_prefix='/unified-dashboard')

def init_app(app):
    """Initialiser la route du tableau de bord unifié pour l'application Flask"""
    app.register_blueprint(unified_dashboard_bp)

@unified_dashboard_bp.route("/", methods=["GET"])
@login_required
def dashboard_home():
    """Page principale du tableau de bord unifié"""
    from models import User
    
    # Récupérer l'utilisateur actuel
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return redirect(url_for('login'))
    
    # Collecter les données du tableau de bord financier
    finance_data = get_finance_dashboard_data(user.id)
    
    # Collecter les données de la facturation
    invoicing_data = get_invoicing_dashboard_data(user.id)
    
    # Collecter les données des graphiques du tableau de bord avancé
    chart_data = get_dashboard_chart_data(user.id)
    
    # Fusionner toutes les données
    dashboard_data = {**finance_data, **invoicing_data}
    dashboard_data['chart_data'] = chart_data
    
    # Utiliser le template le plus simple avec des URL codées en dur
    # Change to simplified.html which uses direct URLs instead of url_for
    return render_template('unified_dashboard/simplified.html', 
                          username=username,
                          user=user,
                          **dashboard_data)

def get_finance_dashboard_data(user_id):
    """Récupérer les données pour le tableau de bord financier"""
    # Récupérer les totaux financiers
    total_income = Transaction.query.join(Category).filter(
        Transaction.user_id == user_id,
        Category.type == 'income'
    ).with_entities(func.sum(Transaction.amount)).scalar() or 0
    
    total_expenses = Transaction.query.join(Category).filter(
        Transaction.user_id == user_id,
        Category.type == 'expense'
    ).with_entities(func.sum(Transaction.amount)).scalar() or 0
    
    balance = total_income - total_expenses
    
    # Récupérer les textes extraits non traités
    unprocessed_texts = ExtractedText.query.filter_by(
        user_id=user_id, 
        is_processed=False
    ).order_by(ExtractedText.created_at.desc()).all()
    
    # Récupérer les transactions récentes
    recent_transactions = get_recent_transactions(user_id)
    
    # Date actuelle pour les calculs de période
    current_date = datetime.now()
    
    # Calculer le début et la fin du mois en cours
    current_month_start = datetime(current_date.year, current_date.month, 1)
    next_month_start = current_month_start + relativedelta(months=1)
    current_month_end = next_month_start - timedelta(days=1)
    
    # Calculer le début et la fin du mois précédent
    last_month_start = current_month_start - relativedelta(months=1)
    last_month_end = current_month_start - timedelta(days=1)
    
    # Récupérer les données mensuelles
    current_month_income = get_total_income_by_period(user_id, current_month_start, current_month_end)
    current_month_expense = get_total_expense_by_period(user_id, current_month_start, current_month_end)
    last_month_income = get_total_income_by_period(user_id, last_month_start, last_month_end)
    last_month_expense = get_total_expense_by_period(user_id, last_month_start, last_month_end)
    
    # Calcul de la tendance
    current_month_balance = current_month_income - current_month_expense
    last_month_balance = last_month_income - last_month_expense
    trend = current_month_balance - last_month_balance
    
    # Organiser les statistiques
    stats = {
        'total_income': total_income,
        'total_expenses': total_expenses,
        'balance': balance,
        'current_month_income': current_month_income,
        'current_month_expense': current_month_expense,
        'last_month_income': last_month_income,
        'last_month_expense': last_month_expense,
        'trend': trend,
        'transactions_count': Transaction.query.filter_by(user_id=user_id).count(),
        'categories_count': Category.query.filter_by(user_id=user_id).count()
    }
    
    return {
        'stats': stats,
        'transactions': recent_transactions,
        'unprocessed_texts': unprocessed_texts,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'balance': balance
    }

def get_invoicing_dashboard_data(user_id):
    """Récupérer les données pour le tableau de bord de facturation"""
    # Compter les factures, devis et clients
    invoices_count = Invoice.query.filter_by(user_id=user_id).count()
    quotes_count = Quote.query.filter_by(user_id=user_id).count()
    customers_count = Customer.query.filter_by(user_id=user_id).count()
    
    # Calculer les totaux financiers pour les factures
    year_start = datetime(datetime.now().year, 1, 1)
    
    # Total facturé dans l'année
    total_invoiced = Invoice.query.filter(
        Invoice.user_id == user_id,
        Invoice.issue_date >= year_start
    ).with_entities(func.sum(Invoice.total)).scalar() or 0
    
    # Total payé
    total_paid = Invoice.query.filter(
        Invoice.user_id == user_id,
        Invoice.status == InvoiceStatus.PAID.value
    ).with_entities(func.sum(Invoice.total)).scalar() or 0
    
    # Total en attente
    total_unpaid = Invoice.query.filter(
        Invoice.user_id == user_id,
        Invoice.status.in_([InvoiceStatus.SENT.value, InvoiceStatus.OVERDUE.value])
    ).with_entities(func.sum(Invoice.total)).scalar() or 0
    
    # Récupérer les dernières factures
    latest_invoices = Invoice.query.filter_by(user_id=user_id).order_by(
        Invoice.issue_date.desc()
    ).limit(5).all()
    
    # Récupérer les derniers devis
    latest_quotes = Quote.query.filter_by(user_id=user_id).order_by(
        Quote.issue_date.desc()
    ).limit(5).all()
    
    return {
        'invoices_count': invoices_count,
        'quotes_count': quotes_count,
        'customers_count': customers_count,
        'total_invoiced': total_invoiced,
        'total_paid': total_paid,
        'total_unpaid': total_unpaid,
        'latest_invoices': latest_invoices,
        'latest_quotes': latest_quotes
    }

def get_dashboard_chart_data(user_id):
    """Récupérer les données pour les graphiques du tableau de bord avancé"""
    # Récupérer les données mensuelles pour les 6 derniers mois
    monthly_summary = get_monthly_summary(user_id)
    
    # Récupérer la répartition des dépenses par catégorie
    category_breakdown = get_category_breakdown(user_id)
    
    # Récupérer les données pour les prévisions de trésorerie
    cashflow_prediction = generate_cashflow_prediction(user_id)
    
    return {
        'monthly_summary': monthly_summary,
        'category_breakdown': category_breakdown,
        'cashflow_prediction': cashflow_prediction
    }

@unified_dashboard_bp.route("/data/monthly-summary", methods=["GET"])
@login_required
def monthly_summary_data():
    """API endpoint pour récupérer les données mensuelles"""
    from models import User
    
    # Récupérer l'utilisateur actuel
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Récupérer les données
    data = get_monthly_summary(user.id)
    
    return jsonify(data)

@unified_dashboard_bp.route("/data/category-breakdown", methods=["GET"])
@login_required
def category_breakdown_data():
    """API endpoint pour récupérer la répartition par catégorie"""
    from models import User
    
    # Récupérer l'utilisateur actuel
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Type de transaction (income ou expense)
    transaction_type = request.args.get('type', 'expense')
    
    # Récupérer les données
    data = get_category_breakdown(user.id, transaction_type)
    
    return jsonify(data)

@unified_dashboard_bp.route("/data/cashflow-prediction", methods=["GET"])
@login_required
def cashflow_prediction_data():
    """API endpoint pour récupérer les prédictions de flux de trésorerie"""
    from models import User
    
    # Récupérer l'utilisateur actuel
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Nombre de mois à prédire
    months = int(request.args.get('months', 6))
    
    # Récupérer les prédictions
    data = generate_cashflow_prediction(user.id, months)
    
    return jsonify(data)

@unified_dashboard_bp.route("/settings", methods=["POST"])
@login_required
def update_settings():
    """Mettre à jour les paramètres du tableau de bord"""
    from models import User
    
    # Récupérer l'utilisateur actuel
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Récupérer les paramètres JSON
    settings = request.json
    
    # Sauvegarder ou mettre à jour les paramètres dans la base de données
    dashboard_settings = DashboardSettings.query.filter_by(user_id=user.id).first()
    
    if not dashboard_settings:
        dashboard_settings = DashboardSettings(user_id=user.id)
        db.session.add(dashboard_settings)
    
    # Mettre à jour les préférences
    widgets_visibility = {
        'monthly_trends': settings.get('showMonthlyTrends', True),
        'category_breakdown': settings.get('showCategoryBreakdown', True),
        'recent_transactions': settings.get('showRecentTransactions', True),
        'recent_invoices': settings.get('showRecentInvoices', True)
    }
    
    dashboard_settings.widgets_visibility = json.dumps(widgets_visibility)
    dashboard_settings.period_days = int(settings.get('dataRange', 6)) * 30  # Convertir en jours
    dashboard_settings.prediction_months = int(settings.get('predictionsRange', 6))
    dashboard_settings.updated_at = datetime.now()
    
    db.session.commit()
    
    return jsonify({"success": True})

def get_total_income_by_period(user_id, start_date=None, end_date=None):
    """Récupérer le total des revenus pour une période donnée"""
    query = DashboardTransaction.query.join(TransactionCategory).filter(
        DashboardTransaction.user_id == user_id,
        TransactionCategory.type == 'income'
    )
    
    if start_date:
        query = query.filter(DashboardTransaction.date >= start_date)
    
    if end_date:
        query = query.filter(DashboardTransaction.date <= end_date)
    
    result = query.with_entities(func.sum(DashboardTransaction.amount)).scalar()
    
    return float(result) if result else 0.0

def get_total_expense_by_period(user_id, start_date=None, end_date=None):
    """Récupérer le total des dépenses pour une période donnée"""
    query = DashboardTransaction.query.join(TransactionCategory).filter(
        DashboardTransaction.user_id == user_id,
        TransactionCategory.type == 'expense'
    )
    
    if start_date:
        query = query.filter(DashboardTransaction.date >= start_date)
    
    if end_date:
        query = query.filter(DashboardTransaction.date <= end_date)
    
    result = query.with_entities(func.sum(DashboardTransaction.amount)).scalar()
    
    return float(result) if result else 0.0

def get_recent_transactions(user_id, limit=5):
    """Récupérer les transactions récentes"""
    transactions = DashboardTransaction.query.filter_by(user_id=user_id).order_by(
        DashboardTransaction.date.desc()
    ).limit(limit).all()
    
    result = []
    for transaction in transactions:
        result.append({
            'id': transaction.id,
            'date': transaction.date.strftime('%d/%m/%Y'),
            'description': transaction.description or "Sans description",
            'amount': float(transaction.amount),
            'category': transaction.category.name if transaction.category else "Non catégorisée",
            'type': 'income' if transaction.category and transaction.category.type == 'income' else 'expense'
        })
    
    return result

def get_monthly_summary(user_id, months=6):
    """Récupérer les revenus et dépenses mensuels des derniers mois"""
    # Date actuelle
    current_date = datetime.now()
    
    # Initialiser les données vides pour les X derniers mois
    labels = []
    income_data = []
    expense_data = []
    
    # Calculer les données pour chaque mois
    for i in range(months - 1, -1, -1):
        # Calculer le mois
        target_date = current_date - relativedelta(months=i)
        month_start = datetime(target_date.year, target_date.month, 1)
        
        # Si c'est le mois actuel, utiliser la date actuelle comme fin
        if i == 0:
            month_end = current_date
        else:
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
        
        # Formatage de l'étiquette du mois
        month_label = month_start.strftime('%b %Y')
        labels.append(month_label)
        
        # Récupérer les revenus et dépenses
        income = get_total_income_by_period(user_id, month_start, month_end)
        expense = get_total_expense_by_period(user_id, month_start, month_end)
        
        income_data.append(income)
        expense_data.append(expense)
    
    return {
        'labels': labels,
        'income': income_data,
        'expense': expense_data
    }

def get_category_breakdown(user_id, transaction_type='expense'):
    """Récupérer la répartition des dépenses par catégorie"""
    # Déterminer le type de transaction en fonction du paramètre
    type_name = 'expense' if transaction_type == 'expense' else 'income'
    
    # Récupérer les transactions par catégorie
    query = db.session.query(
        TransactionCategory.name,
        func.sum(DashboardTransaction.amount).label('total')
    ).join(
        DashboardTransaction, DashboardTransaction.category_id == TransactionCategory.id
    ).filter(
        DashboardTransaction.user_id == user_id,
        TransactionCategory.type == type_name
    ).group_by(
        TransactionCategory.name
    ).order_by(
        desc('total')
    )
    
    results = query.all()
    
    # Formater les données pour un graphique circulaire
    labels = [result[0] for result in results]
    values = [float(result[1]) for result in results]
    
    return {
        'labels': labels,
        'values': values
    }

def generate_cashflow_prediction(user_id, months=6):
    """Générer des prédictions de flux de trésorerie basées sur les données historiques"""
    # Date actuelle
    current_date = datetime.now()
    
    # Récupérer les données historiques des 12 derniers mois pour l'analyse
    historical_summary = get_monthly_summary(user_id, 12)
    
    # Calculer les tendances moyennes pour les revenus et dépenses
    income_trend = calculate_trend(historical_summary['income'])
    expense_trend = calculate_trend(historical_summary['expense'])
    
    # Initialiser les données de prédiction
    labels = []
    income_prediction = []
    expense_prediction = []
    balance_prediction = []
    
    # Dernières valeurs connues (du mois actuel)
    last_income = historical_summary['income'][-1] if historical_summary['income'] else 0
    last_expense = historical_summary['expense'][-1] if historical_summary['expense'] else 0
    
    # Générer les prédictions pour les mois à venir
    for i in range(1, months + 1):
        # Calculer le mois de prédiction
        target_date = current_date + relativedelta(months=i)
        month_label = target_date.strftime('%b %Y')
        labels.append(month_label)
        
        # Appliquer les tendances pour prédire les valeurs
        predicted_income = max(0, last_income * (1 + income_trend * i))
        predicted_expense = max(0, last_expense * (1 + expense_trend * i))
        predicted_balance = predicted_income - predicted_expense
        
        income_prediction.append(predicted_income)
        expense_prediction.append(predicted_expense)
        balance_prediction.append(predicted_balance)
    
    return {
        'labels': labels,
        'income': income_prediction,
        'expense': expense_prediction,
        'balance': balance_prediction
    }

def calculate_trend(data):
    """Calculer la tendance à partir d'une série de données"""
    if not data or len(data) < 2:
        return 0
    
    # Éviter la division par zéro
    if data[0] == 0:
        return 0
    
    # Calculer le taux de croissance moyen
    total_growth_rate = 0
    count = 0
    
    for i in range(1, len(data)):
        if data[i-1] > 0:  # Éviter la division par zéro
            growth_rate = (data[i] - data[i-1]) / data[i-1]
            total_growth_rate += growth_rate
            count += 1
    
    # Retourner le taux de croissance moyen
    return total_growth_rate / count if count > 0 else 0