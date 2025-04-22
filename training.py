"""
Module pour la fonctionnalité Formation Interactive
"""
import logging
import os
import json
import uuid
from datetime import datetime
import random
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

from models import User, db
from models_training import (
    Course, Lesson, Quiz, QuizQuestion,
    Enrollment, ProgressRecord, QuizAttempt, QuizAnswer, KnowledgeBase
)
from language import get_text as _
from s3_storage import S3Storage

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Création du blueprint
training_bp = Blueprint('training', __name__, url_prefix='/training')

# Configuration des dossiers
TEMP_FOLDER = os.path.join('static', 'temp', 'training')
os.makedirs(TEMP_FOLDER, exist_ok=True)

# Configuration S3
BUCKET_NAME_PREFIX = os.environ.get('BUCKET_NAME_PREFIX', 'ia-solution')


def init_app(app):
    """Initialiser les routes de formation pour l'application Flask"""
    app.register_blueprint(training_bp)
    
    # Ajout des modèles au contexte de l'application
    with app.app_context():
        db.create_all()


@training_bp.route('/')
def training_dashboard():
    """Page principale du tableau de bord de formation"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first() if username else None
    
    # Récupération des données pour l'utilisateur connecté ou le contenu public
    if user:
        # Cours populaires (publics)
        popular_courses = Course.query.filter_by(is_public=True, status='published').order_by(
            Course.id.desc()).limit(3).all()
        
        # Cours en progression pour l'utilisateur
        enrollments = Enrollment.query.filter_by(user_id=user.id).all()
        in_progress_courses = []
        for enrollment in enrollments:
            if enrollment.status == 'in_progress' or enrollment.status == 'enrolled':
                in_progress_courses.append({
                    'course': enrollment.course,
                    'progress': enrollment.completion_percentage
                })
        
        # Certifications obtenues
        certifications = Enrollment.query.filter_by(
            user_id=user.id, status='certified').all()
        
        # Articles récents de la base de connaissances
        knowledge_articles = KnowledgeBase.query.filter_by(
            status='published').order_by(KnowledgeBase.created_at.desc()).limit(5).all()
        
        return render_template(
            'training/dashboard.html',
            popular_courses=popular_courses,
            in_progress_courses=in_progress_courses[:3],  # Limiter à 3
            certifications=certifications,
            knowledge_articles=knowledge_articles,
            is_authenticated=True,
            _=_
        )
    else:
        # Version non authentifiée : uniquement contenu public
        popular_courses = Course.query.filter_by(is_public=True, status='published').order_by(
            Course.id.desc()).limit(6).all()
        
        knowledge_articles = KnowledgeBase.query.filter_by(
            status='published').order_by(KnowledgeBase.view_count.desc()).limit(5).all()
        
        return render_template(
            'training/dashboard.html',
            popular_courses=popular_courses,
            in_progress_courses=[],
            certifications=[],
            knowledge_articles=knowledge_articles,
            is_authenticated=False,
            _=_
        )


@training_bp.route('/courses')
def list_courses():
    """Liste des cours disponibles"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first() if username else None
    
    # Paramètres de filtrage
    category = request.args.get('category')
    difficulty = request.args.get('difficulty')
    search_query = request.args.get('q')
    
    # Construction de la requête de base
    query = Course.query.filter_by(status='published')
    
    # Si l'utilisateur n'est pas connecté, montrer uniquement les cours publics
    if not user:
        query = query.filter_by(is_public=True)
    
    # Appliquer les filtres
    if category:
        query = query.filter_by(category=category)
    if difficulty:
        query = query.filter_by(difficulty_level=difficulty)
    if search_query:
        query = query.filter(Course.title.ilike(f'%{search_query}%'))
    
    # Exécuter la requête et obtenir les résultats
    courses = query.order_by(Course.title).all()
    
    # Obtenir les catégories distinctes pour le filtre
    categories = db.session.query(Course.category).distinct().filter(
        Course.category.isnot(None)).order_by(Course.category).all()
    categories = [cat[0] for cat in categories]
    
    # Obtenir les niveaux de difficulté pour le filtre
    difficulty_levels = [
        {'value': 'beginner', 'label': _('training_difficulty_beginner')},
        {'value': 'intermediate', 'label': _('training_difficulty_intermediate')},
        {'value': 'advanced', 'label': _('training_difficulty_advanced')}
    ]
    
    # Si l'utilisateur est connecté, ajouter les informations d'inscription
    enrollments_map = {}
    if user:
        enrollments = Enrollment.query.filter_by(user_id=user.id).all()
        for enrollment in enrollments:
            enrollments_map[enrollment.course_id] = enrollment
    
    return render_template(
        'training/courses/list.html',
        courses=courses,
        categories=categories,
        difficulty_levels=difficulty_levels,
        current_category=category,
        current_difficulty=difficulty,
        search_query=search_query,
        enrollments_map=enrollments_map,
        is_authenticated=user is not None,
        _=_
    )


@training_bp.route('/courses/<int:course_id>')
def view_course(course_id):
    """Afficher les détails d'un cours"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first() if username else None
    
    course = Course.query.get_or_404(course_id)
    
    # Vérifier si l'utilisateur peut accéder à ce cours
    if not course.is_public and not user:
        flash(_('training_course_access_denied'), 'danger')
        return redirect(url_for('training.list_courses'))
    
    # Informations d'inscription pour utilisateur connecté
    enrollment = None
    if user:
        enrollment = Enrollment.query.filter_by(
            user_id=user.id, course_id=course.id).first()
    
    # Récupérer les leçons triées par ordre
    lessons = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.order_index).all()
    
    # Obtenir les données de progression si l'utilisateur est inscrit
    lesson_progress = {}
    if enrollment:
        progress_records = ProgressRecord.query.filter_by(enrollment_id=enrollment.id).all()
        for record in progress_records:
            lesson_progress[record.lesson_id] = record.status
    
    # Calculer la durée totale du cours
    total_duration = sum(lesson.duration_minutes or 0 for lesson in lessons)
    
    # Obtenir des cours similaires recommandés
    similar_courses = []
    if course.category:
        similar_courses = Course.query.filter(
            Course.category == course.category,
            Course.id != course.id,
            Course.status == 'published'
        ).order_by(db.func.random()).limit(3).all()
    
    return render_template(
        'training/courses/view.html',
        course=course,
        lessons=lessons,
        enrollment=enrollment,
        lesson_progress=lesson_progress,
        total_duration=total_duration,
        similar_courses=similar_courses,
        tags=course.get_tags(),
        prerequisites=course.get_prerequisites(),
        is_authenticated=user is not None,
        _=_
    )


@training_bp.route('/courses/<int:course_id>/enroll', methods=['POST'])
@login_required
def enroll_course(course_id):
    """Inscrire l'utilisateur à un cours"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    course = Course.query.get_or_404(course_id)
    
    # Vérifier si l'utilisateur est déjà inscrit
    existing_enrollment = Enrollment.query.filter_by(
        user_id=user.id, course_id=course.id).first()
    
    if existing_enrollment:
        flash(_('training_already_enrolled'), 'info')
        return redirect(url_for('training.view_course', course_id=course.id))
    
    try:
        # Créer une nouvelle inscription
        enrollment = Enrollment(
            user_id=user.id,
            course_id=course.id,
            enrollment_date=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            status='enrolled'
        )
        db.session.add(enrollment)
        
        # Créer des enregistrements de progression pour chaque leçon
        lessons = Lesson.query.filter_by(course_id=course.id).all()
        for lesson in lessons:
            progress = ProgressRecord(
                enrollment_id=enrollment.id,
                lesson_id=lesson.id,
                status='not_started'
            )
            db.session.add(progress)
        
        db.session.commit()
        flash(_('training_enrollment_success'), 'success')
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'inscription au cours: {str(e)}")
        flash(_('training_enrollment_error'), 'danger')
    
    return redirect(url_for('training.view_course', course_id=course.id))


@training_bp.route('/lessons/<int:lesson_id>')
@login_required
def view_lesson(lesson_id):
    """Afficher une leçon spécifique"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    lesson = Lesson.query.get_or_404(lesson_id)
    course = Course.query.get_or_404(lesson.course_id)
    
    # Vérifier si l'utilisateur est inscrit au cours
    enrollment = Enrollment.query.filter_by(
        user_id=user.id, course_id=course.id).first()
    
    if not enrollment:
        flash(_('training_not_enrolled'), 'warning')
        return redirect(url_for('training.view_course', course_id=course.id))
    
    # Mettre à jour le statut de progression
    progress = ProgressRecord.query.filter_by(
        enrollment_id=enrollment.id, lesson_id=lesson.id).first()
    
    if progress:
        if progress.status == 'not_started':
            progress.status = 'in_progress'
        
        progress.last_accessed = datetime.utcnow()
        # Incrémenter le temps passé (à améliorer avec une mesure plus précise côté client)
        if progress.time_spent_seconds is None:
            progress.time_spent_seconds = 0
        
        # Mettre à jour l'état de l'inscription
        enrollment.last_accessed = datetime.utcnow()
        if enrollment.status == 'enrolled':
            enrollment.status = 'in_progress'
            
        db.session.commit()
    
    # Récupérer toutes les leçons pour la navigation
    all_lessons = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.order_index).all()
    
    # Trouver les leçons précédente et suivante
    prev_lesson = None
    next_lesson = None
    for i, current_lesson in enumerate(all_lessons):
        if current_lesson.id == lesson.id:
            if i > 0:
                prev_lesson = all_lessons[i-1]
            if i < len(all_lessons) - 1:
                next_lesson = all_lessons[i+1]
            break
    
    # Récupérer les quiz associés à cette leçon
    quizzes = Quiz.query.filter_by(lesson_id=lesson.id).all()
    
    # Déterminer si l'utilisateur a réussi les quiz requis
    quiz_status = {}
    for quiz in quizzes:
        # Rechercher la dernière tentative
        latest_attempt = QuizAttempt.query.filter_by(
            enrollment_id=enrollment.id, quiz_id=quiz.id
        ).order_by(QuizAttempt.attempt_number.desc()).first()
        
        if latest_attempt and latest_attempt.passed:
            quiz_status[quiz.id] = 'passed'
        elif latest_attempt:
            quiz_status[quiz.id] = 'failed'
        else:
            quiz_status[quiz.id] = 'not_attempted'
    
    return render_template(
        'training/lessons/view.html',
        lesson=lesson,
        course=course,
        prev_lesson=prev_lesson,
        next_lesson=next_lesson,
        all_lessons=all_lessons,
        progress=progress,
        quizzes=quizzes,
        quiz_status=quiz_status,
        additional_resources=lesson.get_additional_resources() if lesson.additional_resources else [],
        _=_
    )


@training_bp.route('/lessons/<int:lesson_id>/complete', methods=['POST'])
@login_required
def complete_lesson(lesson_id):
    """Marquer une leçon comme terminée"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    lesson = Lesson.query.get_or_404(lesson_id)
    course = Course.query.get_or_404(lesson.course_id)
    
    # Vérifier si l'utilisateur est inscrit au cours
    enrollment = Enrollment.query.filter_by(
        user_id=user.id, course_id=course.id).first()
    
    if not enrollment:
        flash(_('training_not_enrolled'), 'warning')
        return redirect(url_for('training.view_course', course_id=course.id))
    
    try:
        # Mettre à jour le statut de progression
        progress = ProgressRecord.query.filter_by(
            enrollment_id=enrollment.id, lesson_id=lesson.id).first()
        
        if progress:
            progress.status = 'completed'
            progress.completion_date = datetime.utcnow()
            
            # Mettre à jour la progression globale du cours
            total_lessons = Lesson.query.filter_by(course_id=course.id).count()
            completed_lessons = ProgressRecord.query.filter_by(
                enrollment_id=enrollment.id, status='completed').count()
            
            if total_lessons > 0:
                enrollment.completion_percentage = int((completed_lessons / total_lessons) * 100)
                
                # Si toutes les leçons sont complétées, marquer le cours comme terminé
                if completed_lessons == total_lessons:
                    enrollment.status = 'completed'
                    
                    # Vérifier si le cours offre une certification
                    if course.is_certified:
                        # Vérifier les critères de certification (à implémenter de façon plus robuste)
                        all_quizzes_passed = True
                        required_quizzes = Quiz.query.join(Lesson).filter(
                            Lesson.course_id == course.id,
                            Quiz.is_required == True
                        ).all()
                        
                        for quiz in required_quizzes:
                            # Vérifier si le quiz a été réussi
                            passed_attempt = QuizAttempt.query.filter_by(
                                enrollment_id=enrollment.id,
                                quiz_id=quiz.id,
                                passed=True
                            ).first()
                            
                            if not passed_attempt:
                                all_quizzes_passed = False
                                break
                        
                        # Si tous les quiz requis sont réussis, délivrer le certificat
                        if all_quizzes_passed:
                            enrollment.status = 'certified'
                            enrollment.certification_date = datetime.utcnow()
                            enrollment.certificate_id = f"CERT-{uuid.uuid4().hex[:8].upper()}"
                            flash(_('training_certification_granted'), 'success')
            
            db.session.commit()
            flash(_('training_lesson_completed'), 'success')
            
            # Rediriger vers la leçon suivante s'il y en a une
            next_lesson = Lesson.query.filter(
                Lesson.course_id == course.id,
                Lesson.order_index > lesson.order_index
            ).order_by(Lesson.order_index).first()
            
            if next_lesson:
                return redirect(url_for('training.view_lesson', lesson_id=next_lesson.id))
            else:
                return redirect(url_for('training.view_course', course_id=course.id))
            
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la completion de la leçon: {str(e)}")
        flash(_('training_lesson_completion_error'), 'danger')
    
    return redirect(url_for('training.view_lesson', lesson_id=lesson_id))


@training_bp.route('/quizzes/<int:quiz_id>/start')
@login_required
def start_quiz(quiz_id):
    """Démarrer un quiz"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    lesson = Lesson.query.get_or_404(quiz.lesson_id)
    course = Course.query.get_or_404(lesson.course_id)
    
    # Vérifier si l'utilisateur est inscrit au cours
    enrollment = Enrollment.query.filter_by(
        user_id=user.id, course_id=course.id).first()
    
    if not enrollment:
        flash(_('training_not_enrolled'), 'warning')
        return redirect(url_for('training.view_course', course_id=course.id))
    
    # Vérifier combien de tentatives ont déjà été faites
    attempt_count = QuizAttempt.query.filter_by(
        enrollment_id=enrollment.id, quiz_id=quiz.id).count()
    
    # Créer une nouvelle tentative
    attempt = QuizAttempt(
        enrollment_id=enrollment.id,
        quiz_id=quiz.id,
        start_time=datetime.utcnow(),
        attempt_number=attempt_count + 1
    )
    
    db.session.add(attempt)
    db.session.commit()
    
    # Récupérer les questions et les mélanger
    questions = QuizQuestion.query.filter_by(quiz_id=quiz.id).order_by(QuizQuestion.order_index).all()
    
    return render_template(
        'training/quizzes/take_quiz.html',
        quiz=quiz,
        lesson=lesson,
        course=course,
        questions=questions,
        attempt=attempt,
        _=_
    )


@training_bp.route('/quizzes/submit/<int:attempt_id>', methods=['POST'])
@login_required
def submit_quiz(attempt_id):
    """Soumettre les réponses d'un quiz"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    quiz = Quiz.query.get_or_404(attempt.quiz_id)
    
    # Vérifier que l'utilisateur est bien le propriétaire de la tentative
    enrollment = Enrollment.query.get_or_404(attempt.enrollment_id)
    if enrollment.user_id != user.id:
        flash(_('unauthorized_action'), 'danger')
        return redirect(url_for('training.list_courses'))
    
    # Marquer la fin de la tentative
    attempt.end_time = datetime.utcnow()
    
    # Récupérer toutes les questions
    questions = QuizQuestion.query.filter_by(quiz_id=quiz.id).all()
    
    # Initialiser le score
    total_points = 0
    earned_points = 0
    
    # Traiter chaque réponse
    for question in questions:
        answer_key = f'question_{question.id}'
        user_answer = request.form.get(answer_key, '')
        
        # Déterminer si la réponse est correcte
        is_correct = False
        
        if question.question_type == 'multiple_choice':
            is_correct = str(user_answer) == str(question.correct_answer)
        elif question.question_type == 'true_false':
            is_correct = user_answer.lower() == question.correct_answer.lower()
        elif question.question_type == 'text':
            # Pour les réponses textuelles, on pourrait implémenter une logique plus sophistiquée
            # Par exemple, vérifier les mots-clés ou utiliser un modèle d'IA pour l'évaluation
            is_correct = user_answer.lower() == question.correct_answer.lower()
        
        # Calculer les points
        points_earned = question.points if is_correct else 0
        total_points += question.points
        earned_points += points_earned
        
        # Enregistrer la réponse
        answer = QuizAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            user_answer=user_answer,
            is_correct=is_correct,
            points_earned=points_earned
        )
        db.session.add(answer)
    
    # Calculer le score en pourcentage
    if total_points > 0:
        attempt.score = int((earned_points / total_points) * 100)
    else:
        attempt.score = 0
    
    # Déterminer si le quiz est réussi
    attempt.passed = attempt.score >= quiz.passing_score
    
    db.session.commit()
    
    return redirect(url_for('training.quiz_results', attempt_id=attempt.id))


@training_bp.route('/quizzes/results/<int:attempt_id>')
@login_required
def quiz_results(attempt_id):
    """Afficher les résultats d'une tentative de quiz"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    quiz = Quiz.query.get_or_404(attempt.quiz_id)
    lesson = Lesson.query.get_or_404(quiz.lesson_id)
    course = Course.query.get_or_404(lesson.course_id)
    
    # Vérifier que l'utilisateur est bien le propriétaire de la tentative
    enrollment = Enrollment.query.get_or_404(attempt.enrollment_id)
    if enrollment.user_id != user.id:
        flash(_('unauthorized_action'), 'danger')
        return redirect(url_for('training.list_courses'))
    
    # Récupérer les réponses avec les questions
    answers = QuizAnswer.query.filter_by(attempt_id=attempt.id).all()
    questions_map = {}
    for answer in answers:
        question = QuizQuestion.query.get(answer.question_id)
        questions_map[answer.question_id] = question
    
    # Calculer des statistiques
    correct_answers = sum(1 for answer in answers if answer.is_correct)
    total_questions = len(answers)
    
    return render_template(
        'training/quizzes/results.html',
        attempt=attempt,
        quiz=quiz,
        lesson=lesson,
        course=course,
        answers=answers,
        questions_map=questions_map,
        correct_answers=correct_answers,
        total_questions=total_questions,
        _=_
    )


@training_bp.route('/certificates')
@login_required
def list_certificates():
    """Liste des certificats obtenus par l'utilisateur"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    # Récupérer les certifications
    certifications = Enrollment.query.filter_by(
        user_id=user.id, status='certified').order_by(Enrollment.certification_date.desc()).all()
    
    return render_template(
        'training/certificates/list.html',
        certifications=certifications,
        _=_
    )


@training_bp.route('/certificates/<string:certificate_id>')
def view_certificate(certificate_id):
    """Afficher un certificat spécifique (accessible publiquement pour vérification)"""
    # Rechercher le certificat
    enrollment = Enrollment.query.filter_by(certificate_id=certificate_id).first_or_404()
    course = Course.query.get_or_404(enrollment.course_id)
    user = User.query.get_or_404(enrollment.user_id)
    
    # Vérifier que c'est bien un certificat
    if enrollment.status != 'certified':
        flash(_('certificate_invalid'), 'danger')
        return redirect(url_for('training.list_courses'))
    
    return render_template(
        'training/certificates/view.html',
        enrollment=enrollment,
        course=course,
        user=user,
        _=_
    )


@training_bp.route('/knowledge')
def knowledge_base():
    """Afficher la base de connaissances"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first() if username else None
    
    # Paramètres de filtrage
    category = request.args.get('category')
    search_query = request.args.get('q')
    
    # Construction de la requête de base
    query = KnowledgeBase.query.filter_by(status='published')
    
    # Appliquer les filtres
    if category:
        query = query.filter_by(category=category)
    if search_query:
        query = query.filter(KnowledgeBase.title.ilike(f'%{search_query}%') | 
                            KnowledgeBase.content.ilike(f'%{search_query}%'))
    
    # Exécuter la requête et obtenir les résultats
    articles = query.order_by(KnowledgeBase.created_at.desc()).all()
    
    # Obtenir les catégories distinctes pour le filtre
    categories = db.session.query(KnowledgeBase.category).distinct().order_by(
        KnowledgeBase.category).all()
    categories = [cat[0] for cat in categories]
    
    # Articles les plus populaires
    popular_articles = KnowledgeBase.query.filter_by(
        status='published').order_by(KnowledgeBase.view_count.desc()).limit(5).all()
    
    return render_template(
        'training/knowledge/list.html',
        articles=articles,
        categories=categories,
        current_category=category,
        search_query=search_query,
        popular_articles=popular_articles,
        is_authenticated=user is not None,
        _=_
    )


@training_bp.route('/knowledge/<int:article_id>')
def view_knowledge_article(article_id):
    """Afficher un article de la base de connaissances"""
    article = KnowledgeBase.query.get_or_404(article_id)
    
    # Incrémenter le compteur de vues
    article.view_count += 1
    db.session.commit()
    
    # Récupérer les cours liés
    related_course_ids = article.get_related_courses()
    related_courses = []
    if related_course_ids:
        related_courses = Course.query.filter(Course.id.in_(related_course_ids)).all()
    
    # Articles liés (même catégorie)
    related_articles = KnowledgeBase.query.filter(
        KnowledgeBase.category == article.category,
        KnowledgeBase.id != article.id,
        KnowledgeBase.status == 'published'
    ).order_by(db.func.random()).limit(3).all()
    
    return render_template(
        'training/knowledge/view.html',
        article=article,
        related_courses=related_courses,
        related_articles=related_articles,
        tags=article.get_tags(),
        _=_
    )


@training_bp.route('/knowledge/<int:article_id>/vote', methods=['POST'])
def vote_knowledge_article(article_id):
    """Voter pour un article (utile ou non)"""
    article = KnowledgeBase.query.get_or_404(article_id)
    vote_type = request.form.get('vote_type')
    
    if vote_type == 'helpful':
        article.helpful_votes += 1
    elif vote_type == 'unhelpful':
        article.unhelpful_votes += 1
    
    db.session.commit()
    flash(_('training_thank_you_feedback'), 'success')
    
    return redirect(url_for('training.view_knowledge_article', article_id=article.id))


# Routes d'administration des cours (accessibles uniquement aux administrateurs)
@training_bp.route('/admin/courses')
@login_required
def admin_courses():
    """Interface d'administration des cours"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    # Vérifier que l'utilisateur est un administrateur
    if not user.role == 'admin':
        flash(_('unauthorized_action'), 'danger')
        return redirect(url_for('training.training_dashboard'))
    
    # Récupérer tous les cours
    courses = Course.query.order_by(Course.created_at.desc()).all()
    
    return render_template(
        'training/admin/courses/list.html',
        courses=courses,
        _=_
    )


@training_bp.route('/admin/courses/create', methods=['GET', 'POST'])
@login_required
def admin_create_course():
    """Créer un nouveau cours"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    # Vérifier que l'utilisateur est un administrateur
    if not user.role == 'admin':
        flash(_('unauthorized_action'), 'danger')
        return redirect(url_for('training.training_dashboard'))
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            title = request.form.get('title')
            description = request.form.get('description')
            difficulty_level = request.form.get('difficulty_level')
            category = request.form.get('category')
            is_public = 'is_public' in request.form
            is_certified = 'is_certified' in request.form
            
            # Traitement des tags (séparés par des virgules)
            tags = request.form.get('tags', '').split(',')
            tags = [tag.strip() for tag in tags if tag.strip()]
            
            # Traitement des prérequis (séparés par des virgules)
            prerequisites = request.form.get('prerequisites', '').split(',')
            prerequisites = [prereq.strip() for prereq in prerequisites if prereq.strip()]
            
            # Traitement de l'image de couverture
            cover_image_url = None
            if 'cover_image' in request.files and request.files['cover_image'].filename:
                file = request.files['cover_image']
                filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
                filepath = os.path.join(TEMP_FOLDER, filename)
                file.save(filepath)
                
                # Upload vers S3
                s3_key = f"users/{user.id}/training/courses/{filename}"
                s3 = S3Storage()
                with open(filepath, 'rb') as file_obj:
                    s3.upload_file(user.id, file_obj, s3_key)
                
                # Générer URL
                cover_image_url = s3.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': BUCKET_NAME_PREFIX, 'Key': s3_key},
                    ExpiresIn=3600 * 24 * 30  # URL valide 30 jours
                )
                
                # Supprimer le fichier temporaire
                os.remove(filepath)
            
            # Créer le cours
            course = Course(
                user_id=user.id,
                title=title,
                description=description,
                difficulty_level=difficulty_level,
                category=category,
                duration_minutes=int(request.form.get('duration_minutes', 0)),
                is_public=is_public,
                is_certified=is_certified,
                cover_image=cover_image_url,
                status='published'  # Ou 'draft' si on veut une étape de validation
            )
            
            # Ajouter les tags et prérequis
            course.set_tags(tags)
            course.set_prerequisites(prerequisites)
            
            # Si le cours est certifié, ajouter des critères de certification
            if is_certified:
                certification_criteria = {
                    'min_quiz_score': 80,
                    'all_lessons_completed': True,
                    'final_assessment_required': True
                }
                course.set_certification_criteria(certification_criteria)
            
            db.session.add(course)
            db.session.commit()
            
            flash(_('training_course_created'), 'success')
            return redirect(url_for('training.admin_edit_course', course_id=course.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la création du cours: {str(e)}")
            flash(_('training_course_creation_error'), 'danger')
    
    return render_template(
        'training/admin/courses/create.html',
        _=_
    )


@training_bp.route('/admin/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_course(course_id):
    """Modifier un cours existant"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    # Vérifier que l'utilisateur est un administrateur
    if not user.role == 'admin':
        flash(_('unauthorized_action'), 'danger')
        return redirect(url_for('training.training_dashboard'))
    
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        try:
            # Mettre à jour les données du cours
            course.title = request.form.get('title')
            course.description = request.form.get('description')
            course.difficulty_level = request.form.get('difficulty_level')
            course.category = request.form.get('category')
            course.is_public = 'is_public' in request.form
            course.is_certified = 'is_certified' in request.form
            course.duration_minutes = int(request.form.get('duration_minutes', 0))
            course.status = request.form.get('status')
            
            # Traitement des tags
            tags = request.form.get('tags', '').split(',')
            tags = [tag.strip() for tag in tags if tag.strip()]
            course.set_tags(tags)
            
            # Traitement des prérequis
            prerequisites = request.form.get('prerequisites', '').split(',')
            prerequisites = [prereq.strip() for prereq in prerequisites if prereq.strip()]
            course.set_prerequisites(prerequisites)
            
            # Traitement de l'image de couverture
            if 'cover_image' in request.files and request.files['cover_image'].filename:
                file = request.files['cover_image']
                filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
                filepath = os.path.join(TEMP_FOLDER, filename)
                file.save(filepath)
                
                # Upload vers S3
                s3_key = f"users/{user.id}/training/courses/{filename}"
                s3 = S3Storage()
                with open(filepath, 'rb') as file_obj:
                    s3.upload_file(user.id, file_obj, s3_key)
                
                # Générer URL
                cover_image_url = s3.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': BUCKET_NAME_PREFIX, 'Key': s3_key},
                    ExpiresIn=3600 * 24 * 30  # URL valide 30 jours
                )
                
                # Supprimer le fichier temporaire
                os.remove(filepath)
                
                # Mettre à jour l'URL de l'image
                course.cover_image = cover_image_url
            
            # Si le cours est certifié, mettre à jour des critères de certification
            if course.is_certified:
                certification_criteria = {
                    'min_quiz_score': int(request.form.get('min_quiz_score', 80)),
                    'all_lessons_completed': True,
                    'final_assessment_required': 'final_assessment_required' in request.form
                }
                course.set_certification_criteria(certification_criteria)
            
            db.session.commit()
            flash(_('training_course_updated'), 'success')
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la modification du cours: {str(e)}")
            flash(_('training_course_update_error'), 'danger')
    
    # Récupérer les leçons
    lessons = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.order_index).all()
    
    return render_template(
        'training/admin/courses/edit.html',
        course=course,
        lessons=lessons,
        tags=', '.join(course.get_tags()),
        prerequisites=', '.join(course.get_prerequisites()),
        certification_criteria=course.get_certification_criteria(),
        _=_
    )


@training_bp.route('/admin/courses/<int:course_id>/lessons/create', methods=['GET', 'POST'])
@login_required
def admin_create_lesson(course_id):
    """Créer une nouvelle leçon pour un cours"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    # Vérifier que l'utilisateur est un administrateur
    if not user.role == 'admin':
        flash(_('unauthorized_action'), 'danger')
        return redirect(url_for('training.training_dashboard'))
    
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        try:
            # Calcul de l'index d'ordre
            max_order = db.session.query(db.func.max(Lesson.order_index)).filter_by(course_id=course.id).scalar()
            order_index = 0 if max_order is None else max_order + 1
            
            # Création de la leçon
            lesson = Lesson(
                course_id=course.id,
                title=request.form.get('title'),
                content=request.form.get('content'),
                order_index=order_index,
                duration_minutes=int(request.form.get('duration_minutes', 0)),
                lesson_type=request.form.get('lesson_type')
            )
            
            # Traitement des ressources additionnelles
            resources = []
            resource_titles = request.form.getlist('resource_title')
            resource_urls = request.form.getlist('resource_url')
            
            for i in range(len(resource_titles)):
                if resource_titles[i] and resource_urls[i]:
                    resources.append({
                        'title': resource_titles[i],
                        'url': resource_urls[i]
                    })
            
            lesson.set_additional_resources(resources)
            
            # Traitement du média
            if lesson.lesson_type == 'video' and 'media_file' in request.files and request.files['media_file'].filename:
                file = request.files['media_file']
                filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
                filepath = os.path.join(TEMP_FOLDER, filename)
                file.save(filepath)
                
                # Upload vers S3
                s3_key = f"users/{user.id}/training/lessons/{filename}"
                s3 = S3Storage()
                with open(filepath, 'rb') as file_obj:
                    s3.upload_file(user.id, file_obj, s3_key)
                
                # Générer URL
                media_url = s3.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': BUCKET_NAME_PREFIX, 'Key': s3_key},
                    ExpiresIn=3600 * 24 * 30  # URL valide 30 jours
                )
                
                # Supprimer le fichier temporaire
                os.remove(filepath)
                
                # Mettre à jour l'URL du média
                lesson.media_url = media_url
            elif lesson.lesson_type == 'video':
                # URL externe (YouTube, Vimeo, etc.)
                lesson.media_url = request.form.get('external_media_url')
            
            db.session.add(lesson)
            db.session.commit()
            
            flash(_('training_lesson_created'), 'success')
            return redirect(url_for('training.admin_edit_course', course_id=course.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la création de la leçon: {str(e)}")
            flash(_('training_lesson_creation_error'), 'danger')
    
    return render_template(
        'training/admin/lessons/create.html',
        course=course,
        _=_
    )


@training_bp.route('/admin/lessons/<int:lesson_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_lesson(lesson_id):
    """Modifier une leçon existante"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    # Vérifier que l'utilisateur est un administrateur
    if not user.role == 'admin':
        flash(_('unauthorized_action'), 'danger')
        return redirect(url_for('training.training_dashboard'))
    
    lesson = Lesson.query.get_or_404(lesson_id)
    course = Course.query.get_or_404(lesson.course_id)
    
    if request.method == 'POST':
        try:
            # Mise à jour de la leçon
            lesson.title = request.form.get('title')
            lesson.content = request.form.get('content')
            lesson.duration_minutes = int(request.form.get('duration_minutes', 0))
            lesson.lesson_type = request.form.get('lesson_type')
            
            # Traitement des ressources additionnelles
            resources = []
            resource_titles = request.form.getlist('resource_title')
            resource_urls = request.form.getlist('resource_url')
            
            for i in range(len(resource_titles)):
                if resource_titles[i] and resource_urls[i]:
                    resources.append({
                        'title': resource_titles[i],
                        'url': resource_urls[i]
                    })
            
            lesson.set_additional_resources(resources)
            
            # Traitement du média
            if lesson.lesson_type == 'video' and 'media_file' in request.files and request.files['media_file'].filename:
                file = request.files['media_file']
                filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
                filepath = os.path.join(TEMP_FOLDER, filename)
                file.save(filepath)
                
                # Upload vers S3
                s3_key = f"users/{user.id}/training/lessons/{filename}"
                s3 = S3Storage()
                with open(filepath, 'rb') as file_obj:
                    s3.upload_file(user.id, file_obj, s3_key)
                
                # Générer URL
                media_url = s3.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': BUCKET_NAME_PREFIX, 'Key': s3_key},
                    ExpiresIn=3600 * 24 * 30  # URL valide 30 jours
                )
                
                # Supprimer le fichier temporaire
                os.remove(filepath)
                
                # Mettre à jour l'URL du média
                lesson.media_url = media_url
            elif lesson.lesson_type == 'video' and request.form.get('external_media_url'):
                # URL externe (YouTube, Vimeo, etc.)
                lesson.media_url = request.form.get('external_media_url')
            
            db.session.commit()
            flash(_('training_lesson_updated'), 'success')
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la modification de la leçon: {str(e)}")
            flash(_('training_lesson_update_error'), 'danger')
    
    # Récupérer les quiz associés
    quizzes = Quiz.query.filter_by(lesson_id=lesson.id).all()
    
    return render_template(
        'training/admin/lessons/edit.html',
        lesson=lesson,
        course=course,
        quizzes=quizzes,
        additional_resources=lesson.get_additional_resources(),
        _=_
    )


@training_bp.route('/admin/lessons/<int:lesson_id>/quizzes/create', methods=['GET', 'POST'])
@login_required
def admin_create_quiz(lesson_id):
    """Créer un nouveau quiz pour une leçon"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    # Vérifier que l'utilisateur est un administrateur
    if not user.role == 'admin':
        flash(_('unauthorized_action'), 'danger')
        return redirect(url_for('training.training_dashboard'))
    
    lesson = Lesson.query.get_or_404(lesson_id)
    course = Course.query.get_or_404(lesson.course_id)
    
    if request.method == 'POST':
        try:
            # Création du quiz
            quiz = Quiz(
                lesson_id=lesson.id,
                title=request.form.get('title'),
                description=request.form.get('description'),
                time_limit_minutes=int(request.form.get('time_limit_minutes', 0)) or None,
                passing_score=int(request.form.get('passing_score', 70)),
                is_required='is_required' in request.form
            )
            
            db.session.add(quiz)
            db.session.commit()
            
            flash(_('training_quiz_created'), 'success')
            return redirect(url_for('training.admin_edit_quiz', quiz_id=quiz.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la création du quiz: {str(e)}")
            flash(_('training_quiz_creation_error'), 'danger')
    
    return render_template(
        'training/admin/quizzes/create.html',
        lesson=lesson,
        course=course,
        _=_
    )


@training_bp.route('/admin/quizzes/<int:quiz_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_quiz(quiz_id):
    """Modifier un quiz existant"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    # Vérifier que l'utilisateur est un administrateur
    if not user.role == 'admin':
        flash(_('unauthorized_action'), 'danger')
        return redirect(url_for('training.training_dashboard'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    lesson = Lesson.query.get_or_404(quiz.lesson_id)
    course = Course.query.get_or_404(lesson.course_id)
    
    if request.method == 'POST':
        try:
            # Mise à jour du quiz
            quiz.title = request.form.get('title')
            quiz.description = request.form.get('description')
            quiz.time_limit_minutes = int(request.form.get('time_limit_minutes', 0)) or None
            quiz.passing_score = int(request.form.get('passing_score', 70))
            quiz.is_required = 'is_required' in request.form
            
            db.session.commit()
            flash(_('training_quiz_updated'), 'success')
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la modification du quiz: {str(e)}")
            flash(_('training_quiz_update_error'), 'danger')
    
    # Récupérer les questions
    questions = QuizQuestion.query.filter_by(quiz_id=quiz.id).order_by(QuizQuestion.order_index).all()
    
    return render_template(
        'training/admin/quizzes/edit.html',
        quiz=quiz,
        lesson=lesson,
        course=course,
        questions=questions,
        _=_
    )


@training_bp.route('/admin/quizzes/<int:quiz_id>/questions/create', methods=['GET', 'POST'])
@login_required
def admin_create_question(quiz_id):
    """Créer une nouvelle question pour un quiz"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    # Vérifier que l'utilisateur est un administrateur
    if not user.role == 'admin':
        flash(_('unauthorized_action'), 'danger')
        return redirect(url_for('training.training_dashboard'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if request.method == 'POST':
        try:
            # Calcul de l'index d'ordre
            max_order = db.session.query(db.func.max(QuizQuestion.order_index)).filter_by(quiz_id=quiz.id).scalar()
            order_index = 0 if max_order is None else max_order + 1
            
            question_type = request.form.get('question_type')
            
            # Traitement des options pour les questions à choix multiple
            options = []
            correct_answer = ''
            
            if question_type == 'multiple_choice':
                option_texts = request.form.getlist('option_text')
                is_correct = request.form.getlist('is_correct')
                
                for i, option_text in enumerate(option_texts):
                    if option_text:
                        options.append(option_text)
                        if str(i) in is_correct:
                            correct_answer = str(i)
            elif question_type == 'true_false':
                correct_answer = request.form.get('true_false_answer')
            else:  # text
                correct_answer = request.form.get('text_answer')
            
            # Création de la question
            question = QuizQuestion(
                quiz_id=quiz.id,
                question_text=request.form.get('question_text'),
                question_type=question_type,
                explanation=request.form.get('explanation'),
                points=int(request.form.get('points', 1)),
                order_index=order_index,
                correct_answer=correct_answer
            )
            
            if options:
                question.set_options(options)
            
            db.session.add(question)
            db.session.commit()
            
            flash(_('training_question_created'), 'success')
            return redirect(url_for('training.admin_edit_quiz', quiz_id=quiz.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la création de la question: {str(e)}")
            flash(_('training_question_creation_error'), 'danger')
    
    return render_template(
        'training/admin/questions/create.html',
        quiz=quiz,
        _=_
    )


@training_bp.route('/admin/questions/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_question(question_id):
    """Modifier une question existante"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    # Vérifier que l'utilisateur est un administrateur
    if not user.role == 'admin':
        flash(_('unauthorized_action'), 'danger')
        return redirect(url_for('training.training_dashboard'))
    
    question = QuizQuestion.query.get_or_404(question_id)
    quiz = Quiz.query.get_or_404(question.quiz_id)
    
    if request.method == 'POST':
        try:
            # Mise à jour de la question
            question.question_text = request.form.get('question_text')
            question.explanation = request.form.get('explanation')
            question.points = int(request.form.get('points', 1))
            
            # Le type de question ne change pas, mais on met à jour les options et réponses
            if question.question_type == 'multiple_choice':
                option_texts = request.form.getlist('option_text')
                is_correct = request.form.getlist('is_correct')
                
                options = []
                correct_answer = ''
                
                for i, option_text in enumerate(option_texts):
                    if option_text:
                        options.append(option_text)
                        if str(i) in is_correct:
                            correct_answer = str(i)
                
                question.set_options(options)
                question.correct_answer = correct_answer
                
            elif question.question_type == 'true_false':
                question.correct_answer = request.form.get('true_false_answer')
            else:  # text
                question.correct_answer = request.form.get('text_answer')
            
            db.session.commit()
            flash(_('training_question_updated'), 'success')
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la modification de la question: {str(e)}")
            flash(_('training_question_update_error'), 'danger')
    
    return render_template(
        'training/admin/questions/edit.html',
        question=question,
        quiz=quiz,
        options=question.get_options() if question.question_type == 'multiple_choice' else [],
        _=_
    )


@training_bp.route('/admin/knowledge')
@login_required
def admin_knowledge():
    """Interface d'administration de la base de connaissances"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    # Vérifier que l'utilisateur est un administrateur
    if not user.role == 'admin':
        flash(_('unauthorized_action'), 'danger')
        return redirect(url_for('training.training_dashboard'))
    
    # Récupérer tous les articles
    articles = KnowledgeBase.query.order_by(KnowledgeBase.created_at.desc()).all()
    
    return render_template(
        'training/admin/knowledge/list.html',
        articles=articles,
        _=_
    )


@training_bp.route('/admin/knowledge/create', methods=['GET', 'POST'])
@login_required
def admin_create_knowledge():
    """Créer un nouvel article de la base de connaissances"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    # Vérifier que l'utilisateur est un administrateur
    if not user.role == 'admin':
        flash(_('unauthorized_action'), 'danger')
        return redirect(url_for('training.training_dashboard'))
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            title = request.form.get('title')
            content = request.form.get('content')
            category = request.form.get('category')
            
            # Traitement des tags (séparés par des virgules)
            tags = request.form.get('tags', '').split(',')
            tags = [tag.strip() for tag in tags if tag.strip()]
            
            # Traitement des cours liés
            related_courses = request.form.getlist('related_courses')
            related_courses = [int(course_id) for course_id in related_courses if course_id]
            
            # Créer l'article
            article = KnowledgeBase(
                title=title,
                content=content,
                category=category,
                created_by=user.id,
                status='published'  # Ou 'draft' si on veut une étape de validation
            )
            
            # Ajouter les tags et cours liés
            article.set_tags(tags)
            article.set_related_courses(related_courses)
            
            db.session.add(article)
            db.session.commit()
            
            flash(_('training_knowledge_created'), 'success')
            return redirect(url_for('training.admin_knowledge'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la création de l'article: {str(e)}")
            flash(_('training_knowledge_creation_error'), 'danger')
    
    # Récupérer tous les cours pour les liens
    courses = Course.query.filter_by(status='published').order_by(Course.title).all()
    
    # Récupérer les catégories existantes
    categories = db.session.query(KnowledgeBase.category).distinct().order_by(
        KnowledgeBase.category).all()
    
    return render_template(
        'training/admin/knowledge/create.html',
        courses=courses,
        categories=[cat[0] for cat in categories],
        _=_
    )


@training_bp.route('/admin/knowledge/<int:article_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_knowledge(article_id):
    """Modifier un article existant de la base de connaissances"""
    # Récupérer l'utilisateur depuis la session
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(_('error_user_not_found'), 'danger')
        return redirect(url_for('login'))
    
    # Vérifier que l'utilisateur est un administrateur
    if not user.role == 'admin':
        flash(_('unauthorized_action'), 'danger')
        return redirect(url_for('training.training_dashboard'))
    
    article = KnowledgeBase.query.get_or_404(article_id)
    
    if request.method == 'POST':
        try:
            # Mettre à jour les données de l'article
            article.title = request.form.get('title')
            article.content = request.form.get('content')
            article.category = request.form.get('category')
            article.status = request.form.get('status')
            
            # Traitement des tags
            tags = request.form.get('tags', '').split(',')
            tags = [tag.strip() for tag in tags if tag.strip()]
            article.set_tags(tags)
            
            # Traitement des cours liés
            related_courses = request.form.getlist('related_courses')
            related_courses = [int(course_id) for course_id in related_courses if course_id]
            article.set_related_courses(related_courses)
            
            db.session.commit()
            flash(_('training_knowledge_updated'), 'success')
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la modification de l'article: {str(e)}")
            flash(_('training_knowledge_update_error'), 'danger')
    
    # Récupérer tous les cours pour les liens
    courses = Course.query.filter_by(status='published').order_by(Course.title).all()
    
    # Récupérer les catégories existantes
    categories = db.session.query(KnowledgeBase.category).distinct().order_by(
        KnowledgeBase.category).all()
    
    return render_template(
        'training/admin/knowledge/edit.html',
        article=article,
        courses=courses,
        categories=[cat[0] for cat in categories],
        tags=', '.join(article.get_tags()),
        related_courses=article.get_related_courses(),
        _=_
    )


# API endpoints pour AJAX
@training_bp.route('/api/lessons/reorder', methods=['POST'])
@login_required
def api_reorder_lessons():
    """Réorganiser les leçons d'un cours"""
    data = request.get_json()
    
    if not data or 'lessonOrder' not in data:
        return jsonify({'success': False, 'message': 'Données invalides'}), 400
    
    try:
        # Récupérer l'utilisateur depuis la session
        username = session.get('username')
        user = User.query.filter_by(username=username).first()
        
        if not user or user.role != 'admin':
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
        lesson_order = data['lessonOrder']
        
        for order_data in lesson_order:
            lesson_id = order_data.get('id')
            new_order = order_data.get('order')
            
            if lesson_id and new_order is not None:
                lesson = Lesson.query.get(lesson_id)
                if lesson:
                    lesson.order_index = new_order
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la réorganisation des leçons: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@training_bp.route('/api/questions/reorder', methods=['POST'])
@login_required
def api_reorder_questions():
    """Réorganiser les questions d'un quiz"""
    data = request.get_json()
    
    if not data or 'questionOrder' not in data:
        return jsonify({'success': False, 'message': 'Données invalides'}), 400
    
    try:
        # Récupérer l'utilisateur depuis la session
        username = session.get('username')
        user = User.query.filter_by(username=username).first()
        
        if not user or user.role != 'admin':
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
        question_order = data['questionOrder']
        
        for order_data in question_order:
            question_id = order_data.get('id')
            new_order = order_data.get('order')
            
            if question_id and new_order is not None:
                question = QuizQuestion.query.get(question_id)
                if question:
                    question.order_index = new_order
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la réorganisation des questions: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500