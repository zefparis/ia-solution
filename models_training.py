"""
Module pour les modèles de données du système de formation interactive
"""
from datetime import datetime
import json
from sqlalchemy.dialects.postgresql import JSON
from models import db


class Course(db.Model):
    """Modèle pour les cours de formation"""
    __tablename__ = 'training_course'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # NULL pour cours publics
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    difficulty_level = db.Column(db.String(20), nullable=False, default='beginner')  # beginner, intermediate, advanced
    category = db.Column(db.String(50), nullable=True)
    tags = db.Column(db.Text, nullable=True)  # Stocké en JSON
    is_public = db.Column(db.Boolean, default=False)
    is_certified = db.Column(db.Boolean, default=False)
    certification_criteria = db.Column(db.Text, nullable=True)  # Stocké en JSON
    duration_minutes = db.Column(db.Integer, nullable=True)
    prerequisites = db.Column(db.Text, nullable=True)  # Stocké en JSON
    cover_image = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = db.Column(db.String(20), default='draft')  # draft, published, archived
    
    # Relations
    lessons = db.relationship('Lesson', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    enrollments = db.relationship('Enrollment', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Course {self.title}>'
    
    def get_tags(self):
        """Retourne les tags sous forme de liste"""
        if not self.tags:
            return []
        return json.loads(self.tags)
    
    def set_tags(self, tag_list):
        """Enregistre les tags à partir d'une liste"""
        self.tags = json.dumps(tag_list)
    
    def get_prerequisites(self):
        """Retourne les prérequis sous forme de liste"""
        if not self.prerequisites:
            return []
        return json.loads(self.prerequisites)
    
    def set_prerequisites(self, prereq_list):
        """Enregistre les prérequis à partir d'une liste"""
        self.prerequisites = json.dumps(prereq_list)
    
    def get_certification_criteria(self):
        """Retourne les critères de certification sous forme de dictionnaire"""
        if not self.certification_criteria:
            return {}
        return json.loads(self.certification_criteria)
    
    def set_certification_criteria(self, criteria_dict):
        """Enregistre les critères de certification à partir d'un dictionnaire"""
        self.certification_criteria = json.dumps(criteria_dict)


class Lesson(db.Model):
    """Modèle pour les leçons d'un cours"""
    __tablename__ = 'training_lesson'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('training_course.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    order_index = db.Column(db.Integer, nullable=False, default=0)
    duration_minutes = db.Column(db.Integer, nullable=True)
    lesson_type = db.Column(db.String(20), default='text')  # text, video, quiz, interactive
    media_url = db.Column(db.String(255), nullable=True)
    additional_resources = db.Column(db.Text, nullable=True)  # Stocké en JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    quizzes = db.relationship('Quiz', backref='lesson', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Lesson {self.title}>'
    
    def get_additional_resources(self):
        """Retourne les ressources additionnelles sous forme de liste"""
        if not self.additional_resources:
            return []
        return json.loads(self.additional_resources)
    
    def set_additional_resources(self, resources_list):
        """Enregistre les ressources additionnelles à partir d'une liste"""
        self.additional_resources = json.dumps(resources_list)


class Quiz(db.Model):
    """Modèle pour les quiz d'évaluation"""
    __tablename__ = 'training_quiz'
    
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('training_lesson.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    time_limit_minutes = db.Column(db.Integer, nullable=True)
    passing_score = db.Column(db.Integer, default=70)  # Pourcentage pour réussir
    is_required = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    questions = db.relationship('QuizQuestion', backref='quiz', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Quiz {self.title}>'


class QuizQuestion(db.Model):
    """Modèle pour les questions de quiz"""
    __tablename__ = 'training_quiz_question'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('training_quiz.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), default='multiple_choice')  # multiple_choice, true_false, text
    options = db.Column(db.Text, nullable=True)  # Stocké en JSON pour multiple_choice
    correct_answer = db.Column(db.Text, nullable=False)  # Index pour multiple_choice, "true"/"false" pour true_false, texte pour text
    explanation = db.Column(db.Text, nullable=True)
    points = db.Column(db.Integer, default=1)
    order_index = db.Column(db.Integer, nullable=False, default=0)
    
    def __repr__(self):
        return f'<QuizQuestion {self.id}>'
    
    def get_options(self):
        """Retourne les options sous forme de liste"""
        if not self.options:
            return []
        return json.loads(self.options)
    
    def set_options(self, options_list):
        """Enregistre les options à partir d'une liste"""
        self.options = json.dumps(options_list)


class Enrollment(db.Model):
    """Modèle pour les inscriptions aux cours"""
    __tablename__ = 'training_enrollment'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('training_course.id'), nullable=False)
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_accessed = db.Column(db.DateTime, nullable=True)
    completion_percentage = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='enrolled')  # enrolled, in_progress, completed, certified
    certification_date = db.Column(db.DateTime, nullable=True)
    certificate_id = db.Column(db.String(50), nullable=True, unique=True)
    
    # Relations
    progress_records = db.relationship('ProgressRecord', backref='enrollment', lazy='dynamic', cascade='all, delete-orphan')
    quiz_attempts = db.relationship('QuizAttempt', backref='enrollment', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Enrollment {self.id}>'


class ProgressRecord(db.Model):
    """Modèle pour suivre la progression dans les leçons"""
    __tablename__ = 'training_progress_record'
    
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('training_enrollment.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('training_lesson.id'), nullable=False)
    status = db.Column(db.String(20), default='not_started')  # not_started, in_progress, completed
    last_accessed = db.Column(db.DateTime, nullable=True)
    time_spent_seconds = db.Column(db.Integer, default=0)
    completion_date = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<ProgressRecord {self.id}>'


class QuizAttempt(db.Model):
    """Modèle pour les tentatives de quiz"""
    __tablename__ = 'training_quiz_attempt'
    
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('training_enrollment.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('training_quiz.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    score = db.Column(db.Integer, nullable=True)  # Pourcentage
    passed = db.Column(db.Boolean, nullable=True)
    attempt_number = db.Column(db.Integer, default=1)
    
    # Relations
    answers = db.relationship('QuizAnswer', backref='attempt', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<QuizAttempt {self.id}>'


class QuizAnswer(db.Model):
    """Modèle pour les réponses aux questions de quiz"""
    __tablename__ = 'training_quiz_answer'
    
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('training_quiz_attempt.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('training_quiz_question.id'), nullable=False)
    user_answer = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, nullable=True)
    points_earned = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<QuizAnswer {self.id}>'


class KnowledgeBase(db.Model):
    """Modèle pour la base de connaissances évolutive"""
    __tablename__ = 'training_knowledge_base'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    tags = db.Column(db.Text, nullable=True)  # Stocké en JSON
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = db.Column(db.String(20), default='published')  # draft, published, archived
    view_count = db.Column(db.Integer, default=0)
    helpful_votes = db.Column(db.Integer, default=0)
    unhelpful_votes = db.Column(db.Integer, default=0)
    related_courses = db.Column(db.Text, nullable=True)  # Stocké en JSON
    
    def __repr__(self):
        return f'<KnowledgeBase {self.title}>'
    
    def get_tags(self):
        """Retourne les tags sous forme de liste"""
        if not self.tags:
            return []
        return json.loads(self.tags)
    
    def set_tags(self, tag_list):
        """Enregistre les tags à partir d'une liste"""
        self.tags = json.dumps(tag_list)
    
    def get_related_courses(self):
        """Retourne les cours liés sous forme de liste"""
        if not self.related_courses:
            return []
        return json.loads(self.related_courses)
    
    def set_related_courses(self, course_id_list):
        """Enregistre les cours liés à partir d'une liste d'IDs"""
        self.related_courses = json.dumps(course_id_list)