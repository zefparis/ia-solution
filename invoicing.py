"""
Module pour la gestion des factures et devis
"""
import os
import datetime
import logging
import uuid
from decimal import Decimal
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session, abort
from markupsafe import Markup
from sqlalchemy import func, desc
from auth import login_required
from models import db, User, Customer, Invoice, InvoiceItem, Quote, QuoteItem, CompanyInfo

# Configuration du logger
logger = logging.getLogger(__name__)

# Créer un blueprint pour la facturation
invoicing_bp = Blueprint('invoicing', __name__, url_prefix='/invoicing')

# Ajout d'un filtre Jinja pour convertir les retours à la ligne en balises <br>
@invoicing_bp.app_template_filter('nl2br')
def nl2br_filter(s):
    if s is None:
        return ""
    return Markup(s.replace('\n', '<br>'))

def generate_invoice_number():
    """Générer un numéro de facture unique"""
    today = datetime.datetime.now()
    date_prefix = today.strftime('%Y%m')
    
    # Trouver le dernier numéro de facture avec ce préfixe
    last_invoice = Invoice.query.filter(
        Invoice.invoice_number.like(f"INV-{date_prefix}-%")
    ).order_by(desc(Invoice.id)).first()
    
    if last_invoice:
        try:
            # Extraire le numéro séquentiel
            seq_num = int(last_invoice.invoice_number.split('-')[-1])
            new_seq_num = seq_num + 1
        except (ValueError, IndexError):
            new_seq_num = 1
    else:
        new_seq_num = 1
    
    return f"INV-{date_prefix}-{new_seq_num:04d}"

def generate_quote_number():
    """Générer un numéro de devis unique"""
    today = datetime.datetime.now()
    date_prefix = today.strftime('%Y%m')
    
    # Trouver le dernier numéro de devis avec ce préfixe
    last_quote = Quote.query.filter(
        Quote.quote_number.like(f"DEVIS-{date_prefix}-%")
    ).order_by(desc(Quote.id)).first()
    
    if last_quote:
        try:
            # Extraire le numéro séquentiel
            seq_num = int(last_quote.quote_number.split('-')[-1])
            new_seq_num = seq_num + 1
        except (ValueError, IndexError):
            new_seq_num = 1
    else:
        new_seq_num = 1
    
    return f"DEVIS-{date_prefix}-{new_seq_num:04d}"

# Définition de toutes les routes du module de facturation
@invoicing_bp.route('/')
@login_required
def index():
    """Page d'accueil du module de facturation"""
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    # Vérifier s'il y a un paramètre 'type' pour rediriger vers la création de devis ou facture
    document_type = request.args.get('type', 'invoice')
    
    # Si le type est 'quote', rediriger vers la création de devis
    if document_type == 'quote':
        return redirect(url_for('invoicing.add_quote'))
    
    # Si le type est 'invoice', rediriger vers la création de facture
    if document_type == 'invoice':
        return redirect(url_for('invoicing.add_invoice'))
    
    # Statistiques
    invoices_count = Invoice.query.filter_by(user_id=user.id).count()
    quotes_count = Quote.query.filter_by(user_id=user.id).count()
    customers_count = Customer.query.filter_by(user_id=user.id).count()
    
    # Dernières factures
    latest_invoices = Invoice.query.filter_by(user_id=user.id).order_by(desc(Invoice.created_at)).limit(5).all()
    
    # Derniers devis
    latest_quotes = Quote.query.filter_by(user_id=user.id).order_by(desc(Quote.created_at)).limit(5).all()
    
    # Montant total des factures de l'année
    current_year = datetime.datetime.now().year
    total_invoiced = db.session.query(func.sum(Invoice.total)).filter(
        Invoice.user_id == user.id,
        func.extract('year', Invoice.issue_date) == current_year
    ).scalar() or 0
    
    # Montant total des factures payées
    total_paid = db.session.query(func.sum(Invoice.total)).filter(
        Invoice.user_id == user.id,
        Invoice.status == 'paid'
    ).scalar() or 0
    
    # Montant total des factures impayées
    total_unpaid = db.session.query(func.sum(Invoice.total)).filter(
        Invoice.user_id == user.id,
        Invoice.status.in_(['draft', 'sent', 'overdue'])
    ).scalar() or 0
    
    # Vérifier si les informations de l'entreprise sont configurées
    company_info = CompanyInfo.query.filter_by(user_id=user.id).first()
    
    return render_template(
        'invoicing/index.html',
        invoices_count=invoices_count,
        quotes_count=quotes_count,
        customers_count=customers_count,
        latest_invoices=latest_invoices,
        latest_quotes=latest_quotes,
        total_invoiced=total_invoiced,
        total_paid=total_paid,
        total_unpaid=total_unpaid,
        company_info=company_info
    )

# Routes pour les clients
@invoicing_bp.route('/customers')
@login_required
def customers():
    """Liste des clients"""
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    customers_list = Customer.query.filter_by(user_id=user.id).order_by(Customer.name).all()
    
    return render_template(
        'invoicing/customers.html',
        customers=customers_list
    )

@invoicing_bp.route('/customers/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    """Ajouter un nouveau client"""
    if request.method == 'POST':
        username = session.get('username')
        user = User.query.filter_by(username=username).first()
        
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        city = request.form.get('city')
        postal_code = request.form.get('postal_code')
        country = request.form.get('country')
        tax_id = request.form.get('tax_id')
        is_company = request.form.get('is_company') == 'on'
        contact_name = request.form.get('contact_name')
        notes = request.form.get('notes')
        
        if not name:
            flash('Le nom du client est obligatoire', 'danger')
            return render_template('invoicing/add_customer.html')
        
        # Créer un nouveau client
        customer = Customer(
            user_id=user.id,
            name=name,
            email=email,
            phone=phone,
            address=address,
            city=city,
            postal_code=postal_code,
            country=country,
            tax_id=tax_id,
            is_company=is_company,
            contact_name=contact_name,
            notes=notes
        )
        
        db.session.add(customer)
        db.session.commit()
        
        flash(f'Client "{name}" ajouté avec succès', 'success')
        return redirect(url_for('invoicing.customers'))
    
    return render_template('invoicing/add_customer.html')

@invoicing_bp.route('/customers/<int:customer_id>')
@login_required
def view_customer(customer_id):
    """Afficher les détails d'un client"""
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    customer = Customer.query.filter_by(id=customer_id, user_id=user.id).first_or_404()
    
    # Récupérer les factures associées à ce client
    invoices = Invoice.query.filter_by(customer_id=customer.id).order_by(desc(Invoice.issue_date)).all()
    
    # Récupérer les devis associés à ce client
    quotes = Quote.query.filter_by(customer_id=customer.id).order_by(desc(Quote.issue_date)).all()
    
    return render_template(
        'invoicing/view_customer.html',
        customer=customer,
        invoices=invoices,
        quotes=quotes
    )

@invoicing_bp.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    """Modifier un client"""
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    customer = Customer.query.filter_by(id=customer_id, user_id=user.id).first_or_404()
    
    if request.method == 'POST':
        customer.name = request.form.get('name')
        customer.email = request.form.get('email')
        customer.phone = request.form.get('phone')
        customer.address = request.form.get('address')
        customer.city = request.form.get('city')
        customer.postal_code = request.form.get('postal_code')
        customer.country = request.form.get('country')
        customer.tax_id = request.form.get('tax_id')
        customer.is_company = request.form.get('is_company') == 'on'
        customer.contact_name = request.form.get('contact_name')
        customer.notes = request.form.get('notes')
        
        if not customer.name:
            flash('Le nom du client est obligatoire', 'danger')
            return render_template('invoicing/edit_customer.html', customer=customer)
        
        db.session.commit()
        
        flash(f'Client "{customer.name}" modifié avec succès', 'success')
        return redirect(url_for('invoicing.view_customer', customer_id=customer.id))
    
    return render_template('invoicing/edit_customer.html', customer=customer)

# Routes pour les factures
@invoicing_bp.route('/invoices')
@login_required
def invoices():
    """Liste des factures"""
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    status_filter = request.args.get('status')
    
    invoices_query = Invoice.query.filter_by(user_id=user.id)
    
    if status_filter:
        invoices_query = invoices_query.filter_by(status=status_filter)
    
    invoices_list = invoices_query.order_by(desc(Invoice.issue_date)).all()
    
    # Statistiques par statut
    status_counts = {
        'draft': Invoice.query.filter_by(user_id=user.id, status='draft').count(),
        'sent': Invoice.query.filter_by(user_id=user.id, status='sent').count(),
        'paid': Invoice.query.filter_by(user_id=user.id, status='paid').count(),
        'overdue': Invoice.query.filter_by(user_id=user.id, status='overdue').count(),
        'cancelled': Invoice.query.filter_by(user_id=user.id, status='cancelled').count(),
    }
    
    return render_template(
        'invoicing/invoices.html',
        invoices=invoices_list,
        status_counts=status_counts,
        active_status=status_filter
    )

@invoicing_bp.route('/invoices/add', methods=['GET', 'POST'])
@login_required
def add_invoice():
    """Ajouter une nouvelle facture"""
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    # Vérifier si l'utilisateur a configuré ses informations d'entreprise
    company_info = CompanyInfo.query.filter_by(user_id=user.id).first()
    if not company_info:
        flash('Veuillez configurer vos informations d\'entreprise avant de créer une facture', 'warning')
        return redirect(url_for('invoicing.company_settings'))
    
    # Récupérer la liste des clients
    customers = Customer.query.filter_by(user_id=user.id).order_by(Customer.name).all()
    if not customers:
        flash('Veuillez ajouter au moins un client avant de créer une facture', 'warning')
        return redirect(url_for('invoicing.add_customer'))
    
    # Pré-sélectionner un client s'il est passé en paramètre
    selected_customer_id = request.args.get('customer_id')
    
    if request.method == 'POST':
        # Créer une nouvelle facture
        customer_id = request.form.get('customer_id')
        issue_date_str = request.form.get('issue_date')
        due_date_str = request.form.get('due_date')
        notes = request.form.get('notes')
        terms = request.form.get('terms')
        payment_info = request.form.get('payment_info')
        
        # Vérifier si le client existe
        customer = Customer.query.filter_by(id=customer_id, user_id=user.id).first()
        if not customer:
            flash('Client non valide', 'danger')
            return redirect(url_for('invoicing.add_invoice'))
        
        # Convertir les dates
        try:
            issue_date = datetime.datetime.strptime(issue_date_str, '%Y-%m-%d').date()
            due_date = datetime.datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
        except ValueError:
            flash('Format de date invalide', 'danger')
            return redirect(url_for('invoicing.add_invoice'))
        
        # Générer un numéro de facture unique
        invoice_number = generate_invoice_number()
        
        invoice = Invoice(
            user_id=user.id,
            customer_id=customer.id,
            invoice_number=invoice_number,
            issue_date=issue_date,
            due_date=due_date,
            notes=notes,
            terms=terms,
            payment_info=payment_info,
            status='draft'
        )
        
        db.session.add(invoice)
        db.session.flush()  # Pour obtenir l'ID de la facture
        
        # Traiter les lignes de facture
        item_descriptions = request.form.getlist('item_description[]')
        item_quantities = request.form.getlist('item_quantity[]')
        item_unit_prices = request.form.getlist('item_unit_price[]')
        item_tax_rates = request.form.getlist('item_tax_rate[]')
        
        if not item_descriptions:
            flash('Veuillez ajouter au moins une ligne à la facture', 'danger')
            db.session.rollback()
            return redirect(url_for('invoicing.add_invoice'))
        
        for i in range(len(item_descriptions)):
            try:
                description = item_descriptions[i]
                quantity = Decimal(item_quantities[i])
                unit_price = Decimal(item_unit_prices[i])
                tax_rate = Decimal(item_tax_rates[i])
                
                # Vérifier que les valeurs sont positives
                if quantity <= 0 or unit_price < 0 or tax_rate < 0:
                    raise ValueError("Les valeurs doivent être positives")
                
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=description,
                    quantity=quantity,
                    unit_price=unit_price,
                    tax_rate=tax_rate
                )
                
                # Calculer les montants
                item.calculate()
                
                db.session.add(item)
            except (ValueError, IndexError) as e:
                flash(f'Erreur dans la ligne {i+1}: {str(e)}', 'danger')
                db.session.rollback()
                return redirect(url_for('invoicing.add_invoice'))
        
        # Calculer les totaux de la facture
        invoice.calculate_totals()
        
        db.session.commit()
        
        flash(f'Facture {invoice_number} créée avec succès', 'success')
        return redirect(url_for('invoicing.view_invoice', invoice_id=invoice.id))
    
    # Utiliser la date du jour comme date par défaut
    today = datetime.datetime.now().date()
    due_date = today + datetime.timedelta(days=30)  # Échéance par défaut à 30 jours
    
    # Texte par défaut pour les conditions de paiement
    default_terms = "Paiement à 30 jours à compter de la date de facture. Tout retard de paiement entraînera des pénalités."
    
    # Texte par défaut pour les informations de paiement
    default_payment_info = ""
    if company_info:
        default_payment_info = f"Coordonnées bancaires:\n{company_info.bank_name or ''}\nIBAN: {company_info.bank_iban or ''}\nBIC: {company_info.bank_bic or ''}"
    
    return render_template(
        'invoicing/add_invoice.html',
        customers=customers,
        today=today,
        due_date=due_date,
        default_terms=default_terms,
        default_payment_info=default_payment_info,
        selected_customer_id=selected_customer_id
    )

@invoicing_bp.route('/invoices/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    """Afficher une facture"""
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=user.id).first_or_404()
    company = CompanyInfo.query.filter_by(user_id=user.id).first()
    
    return render_template(
        'invoicing/view_invoice.html',
        invoice=invoice,
        company=company
    )

@invoicing_bp.route('/invoices/<int:invoice_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_invoice(invoice_id):
    """Modifier une facture"""
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=user.id).first_or_404()
    
    # Vérifier si la facture peut être modifiée
    if invoice.status not in ['draft', 'sent']:
        flash('Cette facture ne peut plus être modifiée', 'danger')
        return redirect(url_for('invoicing.view_invoice', invoice_id=invoice.id))
    
    customers = Customer.query.filter_by(user_id=user.id).order_by(Customer.name).all()
    
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        issue_date_str = request.form.get('issue_date')
        due_date_str = request.form.get('due_date')
        notes = request.form.get('notes')
        terms = request.form.get('terms')
        payment_info = request.form.get('payment_info')
        
        # Vérifier si le client existe
        customer = Customer.query.filter_by(id=customer_id, user_id=user.id).first()
        if not customer:
            flash('Client non valide', 'danger')
            return redirect(url_for('invoicing.edit_invoice', invoice_id=invoice.id))
        
        # Convertir les dates
        try:
            issue_date = datetime.datetime.strptime(issue_date_str, '%Y-%m-%d').date()
            due_date = datetime.datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
        except ValueError:
            flash('Format de date invalide', 'danger')
            return redirect(url_for('invoicing.edit_invoice', invoice_id=invoice.id))
        
        # Mettre à jour la facture
        invoice.customer_id = customer.id
        invoice.issue_date = issue_date
        invoice.due_date = due_date
        invoice.notes = notes
        invoice.terms = terms
        invoice.payment_info = payment_info
        
        # Supprimer toutes les lignes existantes
        InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()
        
        # Traiter les nouvelles lignes
        item_descriptions = request.form.getlist('item_description[]')
        item_quantities = request.form.getlist('item_quantity[]')
        item_unit_prices = request.form.getlist('item_unit_price[]')
        item_tax_rates = request.form.getlist('item_tax_rate[]')
        
        if not item_descriptions:
            flash('Veuillez ajouter au moins une ligne à la facture', 'danger')
            db.session.rollback()
            return redirect(url_for('invoicing.edit_invoice', invoice_id=invoice.id))
        
        for i in range(len(item_descriptions)):
            try:
                description = item_descriptions[i]
                quantity = Decimal(item_quantities[i])
                unit_price = Decimal(item_unit_prices[i])
                tax_rate = Decimal(item_tax_rates[i])
                
                # Vérifier que les valeurs sont positives
                if quantity <= 0 or unit_price < 0 or tax_rate < 0:
                    raise ValueError("Les valeurs doivent être positives")
                
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=description,
                    quantity=quantity,
                    unit_price=unit_price,
                    tax_rate=tax_rate
                )
                
                # Calculer les montants
                item.calculate()
                
                db.session.add(item)
            except (ValueError, IndexError) as e:
                flash(f'Erreur dans la ligne {i+1}: {str(e)}', 'danger')
                db.session.rollback()
                return redirect(url_for('invoicing.edit_invoice', invoice_id=invoice.id))
        
        # Calculer les totaux de la facture
        invoice.calculate_totals()
        
        db.session.commit()
        
        flash(f'Facture {invoice.invoice_number} modifiée avec succès', 'success')
        return redirect(url_for('invoicing.view_invoice', invoice_id=invoice.id))
    
    return render_template(
        'invoicing/edit_invoice.html',
        invoice=invoice,
        customers=customers
    )

@invoicing_bp.route('/invoices/<int:invoice_id>/update-status', methods=['POST'])
@login_required
def update_invoice_status(invoice_id):
    """Mettre à jour le statut d'une facture"""
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=user.id).first_or_404()
    
    status = request.form.get('status')
    if status not in ['draft', 'sent', 'paid', 'overdue', 'cancelled']:
        flash('Statut non valide', 'danger')
        return redirect(url_for('invoicing.view_invoice', invoice_id=invoice.id))
    
    invoice.status = status
    
    # Si la facture est payée, enregistrer la date de paiement
    if status == 'paid':
        invoice.paid_at = datetime.datetime.now()
    else:
        invoice.paid_at = None
    
    db.session.commit()
    
    flash(f'Statut de la facture mis à jour avec succès', 'success')
    return redirect(url_for('invoicing.view_invoice', invoice_id=invoice.id))

@invoicing_bp.route('/invoices/<int:invoice_id>/pdf')
@login_required
def generate_invoice_pdf(invoice_id):
    """Générer le PDF d'une facture"""
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=user.id).first_or_404()
    company = CompanyInfo.query.filter_by(user_id=user.id).first()
    
    # TODO: Implémenter la génération de PDF
    flash('La génération de PDF sera implémentée prochainement', 'info')
    return redirect(url_for('invoicing.view_invoice', invoice_id=invoice.id))

# Routes pour les devis
@invoicing_bp.route('/quotes')
@login_required
def quotes():
    """Liste des devis"""
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    status_filter = request.args.get('status')
    
    quotes_query = Quote.query.filter_by(user_id=user.id)
    
    if status_filter:
        quotes_query = quotes_query.filter_by(status=status_filter)
    
    quotes_list = quotes_query.order_by(desc(Quote.issue_date)).all()
    
    # Statistiques par statut
    status_counts = {
        'draft': Quote.query.filter_by(user_id=user.id, status='draft').count(),
        'sent': Quote.query.filter_by(user_id=user.id, status='sent').count(),
        'accepted': Quote.query.filter_by(user_id=user.id, status='accepted').count(),
        'rejected': Quote.query.filter_by(user_id=user.id, status='rejected').count(),
        'expired': Quote.query.filter_by(user_id=user.id, status='expired').count(),
    }
    
    return render_template(
        'invoicing/quotes.html',
        quotes=quotes_list,
        status_counts=status_counts,
        active_status=status_filter
    )

@invoicing_bp.route('/quotes/add', methods=['GET', 'POST'])
@login_required
def add_quote():
    """Ajouter un nouveau devis"""
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    # Vérifier si l'utilisateur a configuré ses informations d'entreprise
    company_info = CompanyInfo.query.filter_by(user_id=user.id).first()
    if not company_info:
        flash('Veuillez configurer vos informations d\'entreprise avant de créer un devis', 'warning')
        return redirect(url_for('invoicing.company_settings'))
    
    # Récupérer la liste des clients
    customers = Customer.query.filter_by(user_id=user.id).order_by(Customer.name).all()
    if not customers:
        flash('Veuillez ajouter au moins un client avant de créer un devis', 'warning')
        return redirect(url_for('invoicing.add_customer'))
    
    # Pré-sélectionner un client s'il est passé en paramètre
    selected_customer_id = request.args.get('customer_id')
    
    if request.method == 'POST':
        # Créer un nouveau devis
        customer_id = request.form.get('customer_id')
        issue_date_str = request.form.get('issue_date')
        expiry_date_str = request.form.get('expiry_date')
        notes = request.form.get('notes')
        terms = request.form.get('terms')
        
        # Vérifier si le client existe
        customer = Customer.query.filter_by(id=customer_id, user_id=user.id).first()
        if not customer:
            flash('Client non valide', 'danger')
            return redirect(url_for('invoicing.add_quote'))
        
        # Convertir les dates
        try:
            issue_date = datetime.datetime.strptime(issue_date_str, '%Y-%m-%d').date()
            expiry_date = datetime.datetime.strptime(expiry_date_str, '%Y-%m-%d').date() if expiry_date_str else None
        except ValueError:
            flash('Format de date invalide', 'danger')
            return redirect(url_for('invoicing.add_quote'))
        
        # Générer un numéro de devis unique
        quote_number = generate_quote_number()
        
        quote = Quote(
            user_id=user.id,
            customer_id=customer.id,
            quote_number=quote_number,
            issue_date=issue_date,
            expiry_date=expiry_date,
            notes=notes,
            terms=terms,
            status='draft'
        )
        
        db.session.add(quote)
        db.session.flush()  # Pour obtenir l'ID du devis
        
        # Traiter les lignes de devis
        item_descriptions = request.form.getlist('item_description[]')
        item_quantities = request.form.getlist('item_quantity[]')
        item_unit_prices = request.form.getlist('item_unit_price[]')
        item_tax_rates = request.form.getlist('item_tax_rate[]')
        
        if not item_descriptions:
            flash('Veuillez ajouter au moins une ligne au devis', 'danger')
            db.session.rollback()
            return redirect(url_for('invoicing.add_quote'))
        
        for i in range(len(item_descriptions)):
            try:
                description = item_descriptions[i]
                quantity = Decimal(item_quantities[i])
                unit_price = Decimal(item_unit_prices[i])
                tax_rate = Decimal(item_tax_rates[i])
                
                # Vérifier que les valeurs sont positives
                if quantity <= 0 or unit_price < 0 or tax_rate < 0:
                    raise ValueError("Les valeurs doivent être positives")
                
                item = QuoteItem(
                    quote_id=quote.id,
                    description=description,
                    quantity=quantity,
                    unit_price=unit_price,
                    tax_rate=tax_rate
                )
                
                # Calculer les montants
                item.calculate()
                
                db.session.add(item)
            except (ValueError, IndexError) as e:
                flash(f'Erreur dans la ligne {i+1}: {str(e)}', 'danger')
                db.session.rollback()
                return redirect(url_for('invoicing.add_quote'))
        
        # Calculer les totaux du devis
        quote.calculate_totals()
        
        db.session.commit()
        
        flash(f'Devis {quote_number} créé avec succès', 'success')
        return redirect(url_for('invoicing.view_quote', quote_id=quote.id))
    
    # Utiliser la date du jour comme date par défaut
    today = datetime.datetime.now().date()
    expiry_date = today + datetime.timedelta(days=30)  # Validité par défaut à 30 jours
    
    # Texte par défaut pour les conditions du devis
    default_terms = "Ce devis est valable 30 jours à compter de sa date d'émission. Toute acceptation donnera lieu à l'établissement d'une facture."
    
    return render_template(
        'invoicing/add_quote.html',
        customers=customers,
        today=today,
        expiry_date=expiry_date,
        default_terms=default_terms,
        selected_customer_id=selected_customer_id
    )

@invoicing_bp.route('/quotes/<int:quote_id>')
@login_required
def view_quote(quote_id):
    """Afficher un devis"""
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    quote = Quote.query.filter_by(id=quote_id, user_id=user.id).first_or_404()
    company = CompanyInfo.query.filter_by(user_id=user.id).first()
    
    return render_template(
        'invoicing/view_quote.html',
        quote=quote,
        company=company
    )

@invoicing_bp.route('/quotes/<int:quote_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_quote(quote_id):
    """Modifier un devis"""
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    quote = Quote.query.filter_by(id=quote_id, user_id=user.id).first_or_404()
    
    # Vérifier si le devis peut être modifié
    if quote.status not in ['draft', 'sent']:
        flash('Ce devis ne peut plus être modifié', 'danger')
        return redirect(url_for('invoicing.view_quote', quote_id=quote.id))
    
    customers = Customer.query.filter_by(user_id=user.id).order_by(Customer.name).all()
    
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        issue_date_str = request.form.get('issue_date')
        expiry_date_str = request.form.get('expiry_date')
        notes = request.form.get('notes')
        terms = request.form.get('terms')
        
        # Vérifier si le client existe
        customer = Customer.query.filter_by(id=customer_id, user_id=user.id).first()
        if not customer:
            flash('Client non valide', 'danger')
            return redirect(url_for('invoicing.edit_quote', quote_id=quote.id))
        
        # Convertir les dates
        try:
            issue_date = datetime.datetime.strptime(issue_date_str, '%Y-%m-%d').date()
            expiry_date = datetime.datetime.strptime(expiry_date_str, '%Y-%m-%d').date() if expiry_date_str else None
        except ValueError:
            flash('Format de date invalide', 'danger')
            return redirect(url_for('invoicing.edit_quote', quote_id=quote.id))
        
        # Mettre à jour le devis
        quote.customer_id = customer.id
        quote.issue_date = issue_date
        quote.expiry_date = expiry_date
        quote.notes = notes
        quote.terms = terms
        
        # Supprimer toutes les lignes existantes
        QuoteItem.query.filter_by(quote_id=quote.id).delete()
        
        # Traiter les nouvelles lignes
        item_descriptions = request.form.getlist('item_description[]')
        item_quantities = request.form.getlist('item_quantity[]')
        item_unit_prices = request.form.getlist('item_unit_price[]')
        item_tax_rates = request.form.getlist('item_tax_rate[]')
        
        if not item_descriptions:
            flash('Veuillez ajouter au moins une ligne au devis', 'danger')
            db.session.rollback()
            return redirect(url_for('invoicing.edit_quote', quote_id=quote.id))
        
        for i in range(len(item_descriptions)):
            try:
                description = item_descriptions[i]
                quantity = Decimal(item_quantities[i])
                unit_price = Decimal(item_unit_prices[i])
                tax_rate = Decimal(item_tax_rates[i])
                
                # Vérifier que les valeurs sont positives
                if quantity <= 0 or unit_price < 0 or tax_rate < 0:
                    raise ValueError("Les valeurs doivent être positives")
                
                item = QuoteItem(
                    quote_id=quote.id,
                    description=description,
                    quantity=quantity,
                    unit_price=unit_price,
                    tax_rate=tax_rate
                )
                
                # Calculer les montants
                item.calculate()
                
                db.session.add(item)
            except (ValueError, IndexError) as e:
                flash(f'Erreur dans la ligne {i+1}: {str(e)}', 'danger')
                db.session.rollback()
                return redirect(url_for('invoicing.edit_quote', quote_id=quote.id))
        
        # Calculer les totaux du devis
        quote.calculate_totals()
        
        db.session.commit()
        
        flash(f'Devis {quote.quote_number} modifié avec succès', 'success')
        return redirect(url_for('invoicing.view_quote', quote_id=quote.id))
    
    return render_template(
        'invoicing/edit_quote.html',
        quote=quote,
        customers=customers
    )

@invoicing_bp.route('/quotes/<int:quote_id>/update-status', methods=['POST'])
@login_required
def update_quote_status(quote_id):
    """Mettre à jour le statut d'un devis"""
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    quote = Quote.query.filter_by(id=quote_id, user_id=user.id).first_or_404()
    
    status = request.form.get('status')
    if status not in ['draft', 'sent', 'accepted', 'rejected', 'expired']:
        flash('Statut non valide', 'danger')
        return redirect(url_for('invoicing.view_quote', quote_id=quote.id))
    
    quote.status = status
    
    # Si le devis est accepté, enregistrer la date d'acceptation
    if status == 'accepted':
        quote.accepted_at = datetime.datetime.now()
    else:
        quote.accepted_at = None
    
    db.session.commit()
    
    flash(f'Statut du devis mis à jour avec succès', 'success')
    return redirect(url_for('invoicing.view_quote', quote_id=quote.id))

@invoicing_bp.route('/quotes/<int:quote_id>/convert', methods=['POST'])
@login_required
def convert_quote_to_invoice(quote_id):
    """Convertir un devis en facture"""
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    quote = Quote.query.filter_by(id=quote_id, user_id=user.id).first_or_404()
    
    # Vérifier si le devis peut être converti
    if quote.status != 'accepted':
        flash('Seuls les devis acceptés peuvent être convertis en facture', 'danger')
        return redirect(url_for('invoicing.view_quote', quote_id=quote.id))
    
    # Si le devis est déjà lié à une facture
    if quote.invoice_id:
        flash('Ce devis a déjà été converti en facture', 'warning')
        return redirect(url_for('invoicing.view_invoice', invoice_id=quote.invoice_id))
    
    # Convertir le devis en facture
    invoice = quote.convert_to_invoice()
    
    if not invoice:
        flash('Erreur lors de la conversion du devis en facture', 'danger')
        return redirect(url_for('invoicing.view_quote', quote_id=quote.id))
    
    db.session.commit()
    
    flash(f'Devis converti en facture {invoice.invoice_number} avec succès', 'success')
    return redirect(url_for('invoicing.view_invoice', invoice_id=invoice.id))

@invoicing_bp.route('/quotes/<int:quote_id>/pdf')
@login_required
def generate_quote_pdf(quote_id):
    """Générer le PDF d'un devis"""
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    quote = Quote.query.filter_by(id=quote_id, user_id=user.id).first_or_404()
    company = CompanyInfo.query.filter_by(user_id=user.id).first()
    
    # TODO: Implémenter la génération de PDF
    flash('La génération de PDF sera implémentée prochainement', 'info')
    return redirect(url_for('invoicing.view_quote', quote_id=quote.id))

# Paramètres de l'entreprise
@invoicing_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def company_settings():
    """Configurer les informations de l'entreprise"""
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    company = CompanyInfo.query.filter_by(user_id=user.id).first()
    
    if request.method == 'POST':
        if not company:
            company = CompanyInfo(user_id=user.id)
        
        company.name = request.form.get('name')
        company.address = request.form.get('address')
        company.city = request.form.get('city')
        company.postal_code = request.form.get('postal_code')
        company.country = request.form.get('country')
        company.phone = request.form.get('phone')
        company.email = request.form.get('email')
        company.website = request.form.get('website')
        company.tax_id = request.form.get('tax_id')
        company.registration_number = request.form.get('registration_number')
        company.bank_name = request.form.get('bank_name')
        company.bank_account = request.form.get('bank_account')
        company.bank_iban = request.form.get('bank_iban')
        company.bank_bic = request.form.get('bank_bic')
        
        # Traiter le logo s'il est fourni
        if 'logo' in request.files and request.files['logo'].filename:
            logo_file = request.files['logo']
            
            # Vérifier le type de fichier
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
            if '.' in logo_file.filename and logo_file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                # Créer un nom de fichier unique
                logo_filename = f"logo_{user.id}_{uuid.uuid4()}.{logo_file.filename.rsplit('.', 1)[1].lower()}"
                
                # Sauvegarder le fichier
                logo_path = os.path.join('static', 'uploads', logo_filename)
                os.makedirs(os.path.dirname(logo_path), exist_ok=True)
                logo_file.save(logo_path)
                
                # Enregistrer le chemin dans la base de données
                company.logo = logo_path
            else:
                flash('Format de fichier non supporté pour le logo. Utilisez PNG, JPG, JPEG, GIF ou SVG.', 'danger')
        
        # Vérifier que le nom de l'entreprise est fourni
        if not company.name:
            flash('Le nom de l\'entreprise est obligatoire', 'danger')
            return render_template('invoicing/company_settings.html', company=company)
        
        if not company.id:
            db.session.add(company)
        
        db.session.commit()
        
        flash('Informations de l\'entreprise mises à jour avec succès', 'success')
        return redirect(url_for('invoicing.company_settings'))
    
    return render_template('invoicing/company_settings.html', company=company)

def init_app(app):
    """Initialiser les routes de facturation pour l'application Flask"""
    app.register_blueprint(invoicing_bp)