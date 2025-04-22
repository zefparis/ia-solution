import logging
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from sqlalchemy import func, extract, desc
from models import User, db
from models_business import BusinessReport
from dashboard_models import TransactionCategory, Transaction, CashflowPrediction, FinancialAlert, DashboardSettings
from auth import login_required

# Configurer le logging
logger = logging.getLogger(__name__)

# Blueprint pour le tableau de bord
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

def init_app(app):
    """Initialiser les routes du tableau de bord pour l'application Flask"""
    app.register_blueprint(dashboard_bp)

@dashboard_bp.route("/", methods=["GET"])
@login_required
def dashboard_home():
    """Page principale du tableau de bord personnalisé"""
    from models import User
    
    # Récupérer l'utilisateur actuel
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return redirect(url_for('login'))
    
    # Date actuelle pour les calculs de période
    current_date = datetime.now()
    
    # Calculer le début et la fin du mois en cours
    current_month_start = datetime(current_date.year, current_date.month, 1)
    next_month_start = current_month_start + relativedelta(months=1)
    current_month_end = next_month_start - timedelta(days=1)
    
    # Calculer le début et la fin du mois précédent
    last_month_start = current_month_start - relativedelta(months=1)
    last_month_end = current_month_start - timedelta(days=1)
    
    # Récupérer les statistiques générales
    stats = {
        'total_income': get_total_by_type(user.id, 'income'),
        'total_expense': get_total_by_type(user.id, 'expense'),
        'current_month_income': get_total_by_type(user.id, 'income', current_month_start, current_month_end),
        'current_month_expense': get_total_by_type(user.id, 'expense', current_month_start, current_month_end),
        'last_month_income': get_total_by_type(user.id, 'income', last_month_start, last_month_end),
        'last_month_expense': get_total_by_type(user.id, 'expense', last_month_start, last_month_end),
        'balance': get_total_by_type(user.id, 'income') - get_total_by_type(user.id, 'expense'),
        'transactions_count': get_transactions_count(user.id),
        'categories_count': get_categories_count(user.id)
    }
    
    # Calcul de la tendance par rapport au mois précédent
    if stats['last_month_income'] > 0 and stats['last_month_expense'] > 0:
        last_month_balance = stats['last_month_income'] - stats['last_month_expense']
        current_month_balance = stats['current_month_income'] - stats['current_month_expense']
        stats['trend'] = current_month_balance - last_month_balance
    else:
        stats['trend'] = 0
    
    # Récupérer les données pour les graphiques
    chart_data = {
        'monthly_summary': get_monthly_summary(user.id),
        'category_breakdown': get_category_breakdown(user.id),
        'income_vs_expense': get_income_vs_expense_trend(user.id)
    }
    
    # Récupérer les transactions récentes
    recent_transactions = get_recent_transactions(user.id, limit=5)
    
    # Récupérer les résumés des derniers rapports business
    business_reports = get_recent_business_reports(user.id, limit=3)
    
    return render_template('dashboard_simple.html',
                        username=username,
                        user=user,
                        stats=stats,
                        chart_data=chart_data,
                        transactions=recent_transactions,
                        business_reports=business_reports)

@dashboard_bp.route("/data/monthly-summary", methods=["GET"])
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

@dashboard_bp.route("/data/category-breakdown", methods=["GET"])
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

@dashboard_bp.route("/data/cashflow-prediction", methods=["GET"])
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

def get_total_by_type(user_id, transaction_type, start_date=None, end_date=None):
    """Récupérer le total des transactions par type et période"""
    query = Transaction.query.join(TransactionCategory).filter(
        Transaction.user_id == user_id,
        TransactionCategory.type == transaction_type
    )
    
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    
    result = query.with_entities(func.sum(Transaction.amount)).scalar()
    
    return float(result) if result else 0.0

def get_transactions_count(user_id):
    """Récupérer le nombre total de transactions"""
    return Transaction.query.filter_by(user_id=user_id).count()

def get_categories_count(user_id):
    """Récupérer le nombre de catégories utilisées"""
    return TransactionCategory.query.filter_by(user_id=user_id).count()

def get_recent_transactions(user_id, limit=5):
    """Récupérer les transactions récentes"""
    transactions = Transaction.query.filter_by(user_id=user_id).order_by(
        Transaction.date.desc()
    ).limit(limit).all()
    
    result = []
    for transaction in transactions:
        category = TransactionCategory.query.get(transaction.category_id)
        result.append({
            'id': transaction.id,
            'date': transaction.date.strftime('%d/%m/%Y'),
            'description': transaction.description,
            'amount': transaction.amount,
            'category': category.name if category else 'Non catégorisé',
            'type': category.type if category else 'unknown'
        })
    
    return result

def get_monthly_summary(user_id, months=6):
    """Récupérer les revenus et dépenses mensuels des derniers mois"""
    # Date actuelle
    current_date = datetime.now()
    
    # Initialiser les données vides pour les X derniers mois
    months_data = []
    labels = []
    income_data = []
    expense_data = []
    
    # Calculer les données pour chaque mois
    for i in range(months - 1, -1, -1):
        # Calculer le mois
        target_date = current_date - relativedelta(months=i)
        month_start = datetime(target_date.year, target_date.month, 1)
        
        # Si c'est le mois suivant, utiliser la date actuelle
        if i == 0:
            month_end = current_date
        else:
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
        
        # Formatage de l'étiquette du mois
        month_label = month_start.strftime('%b %Y')
        labels.append(month_label)
        
        # Récupérer les revenus et dépenses
        income = get_total_by_type(user_id, 'income', month_start, month_end)
        expense = get_total_by_type(user_id, 'expense', month_start, month_end)
        
        income_data.append(income)
        expense_data.append(expense)
    
    return {
        'labels': labels,
        'income': income_data,
        'expense': expense_data
    }

def get_category_breakdown(user_id, transaction_type='expense'):
    """Récupérer la répartition des dépenses par catégorie"""
    # Récupérer toutes les transactions de l'utilisateur pour un type donné
    query = db.session.query(
        TransactionCategory.name,
        func.sum(Transaction.amount).label('total')
    ).join(
        Transaction, Transaction.category_id == TransactionCategory.id
    ).filter(
        Transaction.user_id == user_id,
        TransactionCategory.type == transaction_type
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

def get_income_vs_expense_trend(user_id, months=12):
    """Récupérer la tendance des revenus vs dépenses sur une période"""
    # Date actuelle
    current_date = datetime.now()
    
    # Initialiser les données
    labels = []
    income_data = []
    expense_data = []
    balance_data = []
    
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
        income = get_total_by_type(user_id, 'income', month_start, month_end)
        expense = get_total_by_type(user_id, 'expense', month_start, month_end)
        balance = income - expense
        
        income_data.append(income)
        expense_data.append(expense)
        balance_data.append(balance)
    
    return {
        'labels': labels,
        'income': income_data,
        'expense': expense_data,
        'balance': balance_data
    }

def get_recent_business_reports(user_id, limit=3):
    """Récupérer les rapports business récents"""
    reports = BusinessReport.query.filter_by(user_id=user_id).order_by(
        BusinessReport.updated_at.desc()
    ).limit(limit).all()
    
    result = []
    for report in reports:
        # Extraire le résumé de l'analyse
        summary = report.analysis_summary
        
        # Extraire un maximum de 3 forces
        strengths = json.loads(report.strengths) if report.strengths else []
        strengths = strengths[:3]
        
        result.append({
            'id': report.id,
            'company_name': report.company_name,
            'industry': report.industry,
            'date': report.updated_at.strftime('%d/%m/%Y'),
            'summary': summary,
            'strengths': strengths
        })
    
    return result

def generate_cashflow_prediction(user_id, months=6):
    """Générer des prédictions de flux de trésorerie basées sur les données historiques"""
    # Date actuelle
    current_date = datetime.now()
    
    # Récupérer les données historiques des 12 derniers mois
    historical_data = get_income_vs_expense_trend(user_id, 12)
    
    # Calculer les tendances moyennes
    income_trend = calculate_trend(historical_data['income'])
    expense_trend = calculate_trend(historical_data['expense'])
    
    # Initialiser les données de prédiction
    labels = []
    income_prediction = []
    expense_prediction = []
    balance_prediction = []
    
    # Dernières valeurs connues (du mois actuel)
    last_income = historical_data['income'][-1]
    last_expense = historical_data['expense'][-1]
    
    # Générer les prédictions pour les mois à venir
    for i in range(1, months + 1):
        # Calculer le mois
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