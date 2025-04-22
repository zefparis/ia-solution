"""
Script pour initialiser des données de test pour le module de formation
"""
import logging
from datetime import datetime

from models import db, User
from models_training import (
    Course, Lesson, Quiz, QuizQuestion, KnowledgeBase
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_training_data():
    """Initialiser des données de test pour le module de formation"""
    logger.info("Initialisation des données de formation...")
    
    # Vérifier si les données existent déjà
    if Course.query.count() > 0:
        logger.info("Des données de formation existent déjà. Annulation de l'initialisation.")
        return
    
    # Création des cours
    courses = [
        {
            'title': 'Introduction à l\'IA pour les entrepreneurs',
            'description': 'Découvrez comment l\'intelligence artificielle peut transformer votre entreprise.',
            'difficulty_level': 'beginner',
            'category': 'business',
            'is_public': True,
            'is_certified': True,
            'duration_minutes': 120,
            'status': 'published'
        },
        {
            'title': 'Gestion financière avec IA',
            'description': 'Apprenez à utiliser l\'IA pour optimiser la gestion financière de votre entreprise.',
            'difficulty_level': 'intermediate',
            'category': 'finance',
            'is_public': True,
            'is_certified': True,
            'duration_minutes': 180,
            'status': 'published'
        },
        {
            'title': 'Marketing digital avancé',
            'description': 'Stratégies avancées de marketing digital pour augmenter la visibilité de votre entreprise.',
            'difficulty_level': 'advanced',
            'category': 'marketing',
            'is_public': True,
            'is_certified': True,
            'duration_minutes': 240,
            'status': 'published'
        }
    ]
    
    created_courses = []
    for course_data in courses:
        course = Course(**course_data)
        db.session.add(course)
        created_courses.append(course)
    
    # Création des leçons
    lessons = [
        # Cours 1: Introduction à l'IA
        {
            'course_index': 0,
            'lessons': [
                {
                    'title': 'Qu\'est-ce que l\'IA ?',
                    'content': 'Cette leçon explique les bases de l\'intelligence artificielle et son importance pour les entreprises modernes.',
                    'order_index': 0,
                    'duration_minutes': 20,
                    'lesson_type': 'text'
                },
                {
                    'title': 'Types d\'IA pour les entreprises',
                    'content': 'Découvrez les différents types d\'IA et comment ils peuvent être appliqués à votre secteur d\'activité.',
                    'order_index': 1,
                    'duration_minutes': 25,
                    'lesson_type': 'text'
                },
                {
                    'title': 'Études de cas d\'IA réussies',
                    'content': 'Exemples concrets d\'entreprises qui ont réussi à implémenter l\'IA et les bénéfices qu\'elles en ont tirés.',
                    'order_index': 2,
                    'duration_minutes': 30,
                    'lesson_type': 'text'
                },
                {
                    'title': 'Mise en pratique : Analyse de votre entreprise',
                    'content': 'Exercice pratique pour identifier les opportunités d\'intégration de l\'IA dans votre propre entreprise.',
                    'order_index': 3,
                    'duration_minutes': 45,
                    'lesson_type': 'interactive'
                }
            ]
        },
        # Cours 2: Gestion financière avec IA
        {
            'course_index': 1,
            'lessons': [
                {
                    'title': 'IA et prévisions financières',
                    'content': 'Comment l\'IA peut améliorer la précision de vos prévisions financières et faciliter la prise de décision.',
                    'order_index': 0,
                    'duration_minutes': 30,
                    'lesson_type': 'text'
                },
                {
                    'title': 'Automatisation des processus comptables',
                    'content': 'Utilisez l\'IA pour automatiser les tâches comptables répétitives et réduire les erreurs.',
                    'order_index': 1,
                    'duration_minutes': 40,
                    'lesson_type': 'text'
                },
                {
                    'title': 'Analyse prédictive pour les finances',
                    'content': 'Exploitez les données historiques pour prévoir les tendances futures et optimiser vos décisions financières.',
                    'order_index': 2,
                    'duration_minutes': 45,
                    'lesson_type': 'text'
                },
                {
                    'title': 'Étude de cas : Transformation financière par l\'IA',
                    'content': 'Analyse détaillée d\'une entreprise qui a révolutionné sa gestion financière grâce à l\'IA.',
                    'order_index': 3,
                    'duration_minutes': 35,
                    'lesson_type': 'text'
                },
                {
                    'title': 'Quiz: Gestion financière et IA',
                    'content': 'Testez vos connaissances sur l\'application de l\'IA dans la gestion financière.',
                    'order_index': 4,
                    'duration_minutes': 30,
                    'lesson_type': 'quiz'
                }
            ]
        },
        # Cours 3: Marketing digital avancé
        {
            'course_index': 2,
            'lessons': [
                {
                    'title': 'IA et personnalisation marketing',
                    'content': 'Comment utiliser l\'IA pour créer des expériences marketing hautement personnalisées.',
                    'order_index': 0,
                    'duration_minutes': 40,
                    'lesson_type': 'text'
                },
                {
                    'title': 'Génération de contenu avec l\'IA',
                    'content': 'Optimisez votre production de contenu marketing en utilisant des outils d\'IA génératives.',
                    'order_index': 1,
                    'duration_minutes': 50,
                    'lesson_type': 'text'
                },
                {
                    'title': 'Analyse prédictive des comportements clients',
                    'content': 'Anticipez les besoins et comportements de vos clients grâce à l\'IA prédictive.',
                    'order_index': 2,
                    'duration_minutes': 45,
                    'lesson_type': 'text'
                },
                {
                    'title': 'Optimisation multicanale avec l\'IA',
                    'content': 'Créez des stratégies marketing omnicanales optimisées par l\'IA pour maximiser votre impact.',
                    'order_index': 3,
                    'duration_minutes': 60,
                    'lesson_type': 'text'
                },
                {
                    'title': 'Projet final: Stratégie marketing IA',
                    'content': 'Élaborez une stratégie marketing complète intégrant l\'IA pour votre entreprise.',
                    'order_index': 4,
                    'duration_minutes': 45,
                    'lesson_type': 'interactive'
                }
            ]
        }
    ]
    
    # Création des leçons
    for course_lessons in lessons:
        course = created_courses[course_lessons['course_index']]
        for lesson_data in course_lessons['lessons']:
            lesson = Lesson(course_id=course.id, **lesson_data)
            db.session.add(lesson)
    
    # Ajouter un quiz d'exemple
    finance_course = created_courses[1]  # Gestion financière avec IA
    finance_lessons = Lesson.query.filter_by(course_id=finance_course.id).all()
    quiz_lesson = next((l for l in finance_lessons if l.lesson_type == 'quiz'), None)
    
    if quiz_lesson:
        quiz = Quiz(
            lesson_id=quiz_lesson.id,
            title='Évaluation: Gestion financière et IA',
            description='Testez vos connaissances sur les concepts clés de l\'IA appliquée à la gestion financière.',
            time_limit_minutes=20,
            passing_score=70,
            is_required=True
        )
        db.session.add(quiz)
        db.session.flush()  # Pour obtenir l'ID du quiz
        
        # Ajouter des questions au quiz
        questions = [
            {
                'question_text': 'Quelle technique d\'IA est la plus adaptée pour prédire les tendances financières futures ?',
                'question_type': 'multiple_choice',
                'options': ['Traitement du langage naturel', 'Vision par ordinateur', 'Apprentissage supervisé', 'Robotique'],
                'correct_answer': '2',  # Index de l'option correcte (Apprentissage supervisé)
                'explanation': 'L\'apprentissage supervisé est particulièrement efficace pour analyser les données historiques et identifier des modèles pour prédire les tendances futures.',
                'points': 2,
                'order_index': 0
            },
            {
                'question_text': 'L\'IA peut complètement remplacer les comptables et les analystes financiers.',
                'question_type': 'true_false',
                'correct_answer': 'false',
                'explanation': 'Bien que l\'IA puisse automatiser de nombreuses tâches, les professionnels financiers restent essentiels pour l\'interprétation, la supervision et les décisions stratégiques.',
                'points': 1,
                'order_index': 1
            },
            {
                'question_text': 'Citez trois avantages de l\'automatisation des processus comptables par l\'IA.',
                'question_type': 'text',
                'correct_answer': 'reduction erreurs;gain temps;couts reduits',
                'explanation': 'Parmi les avantages clés figurent: la réduction des erreurs humaines, le gain de temps sur les tâches répétitives, la réduction des coûts opérationnels, l\'amélioration de la conformité, et l\'analyse en temps réel.',
                'points': 3,
                'order_index': 2
            }
        ]
        
        for question_data in questions:
            options = question_data.pop('options', None)
            question = QuizQuestion(quiz_id=quiz.id, **question_data)
            if options:
                question.set_options(options)
            db.session.add(question)
    
    # Ajouter des articles à la base de connaissances
    knowledge_articles = [
        {
            'title': 'Comprendre le Machine Learning dans le contexte business',
            'content': 'Le machine learning est une technologie qui permet aux ordinateurs d\'apprendre à partir de données sans être explicitement programmés. Pour les entreprises, cela signifie pouvoir automatiser des décisions complexes, prédire des tendances et personnaliser des expériences à grande échelle...',
            'category': 'fundamentals',
            'tags': ['machinelearning', 'ia', 'business'],
            'status': 'published'
        },
        {
            'title': 'Comment démarrer avec l\'IA dans une petite entreprise',
            'content': 'Même avec des ressources limitées, les petites entreprises peuvent bénéficier de l\'IA. Commencez par identifier un problème spécifique que l\'IA pourrait résoudre, comme l\'automatisation du service client ou l\'optimisation des stocks. Utilisez ensuite des solutions SaaS existantes qui intègrent déjà l\'IA plutôt que de développer vos propres algorithmes...',
            'category': 'getting_started',
            'tags': ['pme', 'debutant', 'implementation'],
            'status': 'published'
        },
        {
            'title': 'Éthique et IA: Considérations pour les entreprises',
            'content': 'L\'adoption de l\'IA soulève des questions éthiques importantes que toute entreprise doit considérer. La transparence algorithmique, l\'équité des décisions automatisées, la confidentialité des données et l\'impact sur l\'emploi sont des préoccupations majeures. Établissez un cadre éthique clair avant de déployer des solutions d\'IA...',
            'category': 'ethics',
            'tags': ['ethique', 'conformite', 'responsabilite'],
            'status': 'published'
        }
    ]
    
    for article_data in knowledge_articles:
        tags = article_data.pop('tags', [])
        article = KnowledgeBase(**article_data)
        article.set_tags(tags)
        db.session.add(article)
    
    # Valider les changements
    db.session.commit()
    logger.info("Données de formation initialisées avec succès!")

if __name__ == '__main__':
    # Import app seulement si on exécute directement ce script
    from main import app
    with app.app_context():
        init_training_data()