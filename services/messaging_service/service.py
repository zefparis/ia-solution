"""
Service de messagerie - Microservice responsable de la gestion des messages avec RabbitMQ

Ce service expose une API REST pour publier et consommer des messages
via RabbitMQ, facilitant la communication asynchrone entre les différents
services de l'application.
"""

import os
import json
import logging
from datetime import datetime
import threading

from flask import Blueprint, request, jsonify, current_app, g

from cache.flask_integration import cached, rate_limited
from services.messaging_service.rabbitmq_client import RabbitMQClient

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Création du Blueprint pour le service de messagerie
messaging_service = Blueprint('messaging_service', __name__, url_prefix='/api/messaging')

# Client RabbitMQ - sera initialisé lors de l'enregistrement du service
rabbitmq_client = None

# Dictionnaire pour stocker les gestionnaires de messages (callbacks)
message_handlers = {}


@messaging_service.route('/health', methods=['GET'])
def health_check():
    """Endpoint de vérification de l'état du service de messagerie."""
    if rabbitmq_client is None:
        return jsonify({
            'service': 'messaging_service',
            'status': 'error',
            'message': 'Client RabbitMQ non initialisé',
            'timestamp': datetime.now().isoformat()
        }), 500
    
    # Vérifier l'état de RabbitMQ
    rabbitmq_health = rabbitmq_client.health_check()
    
    response = {
        'service': 'messaging_service',
        'status': 'healthy' if rabbitmq_health.get('status') == 'healthy' else 'unhealthy',
        'timestamp': datetime.now().isoformat(),
        'rabbitmq': rabbitmq_health,
        'active_handlers': len(message_handlers)
    }
    
    status_code = 200 if response['status'] == 'healthy' else 500
    return jsonify(response), status_code


@messaging_service.route('/queues', methods=['GET'])
@rate_limited(limit=20, period=60)
def list_queues():
    """Liste les files d'attente disponibles."""
    if rabbitmq_client is None:
        return jsonify({
            'error': 'Service unavailable',
            'message': 'Client RabbitMQ non initialisé'
        }), 503
    
    # Cette fonctionnalité nécessite l'API Management de RabbitMQ
    # qui n'est pas accessible via le client pika standard
    # Un proxy vers l'API HTTP de RabbitMQ serait nécessaire
    
    return jsonify({
        'status': 'not_implemented',
        'message': "Cette fonctionnalité n'est pas encore implémentée"
    }), 501


@messaging_service.route('/queues/<queue_name>', methods=['PUT'])
@rate_limited(limit=10, period=60)
def create_queue(queue_name):
    """
    Crée une nouvelle file d'attente.
    
    Requête JSON attendue:
    {
        "durable": true,
        "exclusive": false,
        "auto_delete": false,
        "arguments": {
            "x-max-length": 1000,
            "x-dead-letter-exchange": "my_dlx"
        }
    }
    """
    if rabbitmq_client is None:
        return jsonify({
            'error': 'Service unavailable',
            'message': 'Client RabbitMQ non initialisé'
        }), 503
    
    data = request.get_json() or {}
    
    durable = data.get('durable', True)
    exclusive = data.get('exclusive', False)
    auto_delete = data.get('auto_delete', False)
    arguments = data.get('arguments')
    
    try:
        result_queue_name = rabbitmq_client.declare_queue(
            queue_name=queue_name,
            durable=durable,
            exclusive=exclusive,
            auto_delete=auto_delete,
            arguments=arguments
        )
        
        if result_queue_name:
            return jsonify({
                'status': 'success',
                'message': f"File d'attente {result_queue_name} créée avec succès",
                'queue_name': result_queue_name
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f"Échec de création de la file d'attente {queue_name}"
            }), 500
    except Exception as e:
        logger.error(f"Erreur lors de la création de la file {queue_name}: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@messaging_service.route('/exchanges/<exchange_name>', methods=['PUT'])
@rate_limited(limit=10, period=60)
def create_exchange(exchange_name):
    """
    Crée un nouvel exchange.
    
    Requête JSON attendue:
    {
        "exchange_type": "direct",
        "durable": true,
        "auto_delete": false,
        "arguments": {
            "alternate-exchange": "my_alt_exchange"
        }
    }
    """
    if rabbitmq_client is None:
        return jsonify({
            'error': 'Service unavailable',
            'message': 'Client RabbitMQ non initialisé'
        }), 503
    
    data = request.get_json() or {}
    
    exchange_type = data.get('exchange_type', 'direct')
    durable = data.get('durable', True)
    auto_delete = data.get('auto_delete', False)
    arguments = data.get('arguments')
    
    try:
        result = rabbitmq_client.declare_exchange(
            exchange_name=exchange_name,
            exchange_type=exchange_type,
            durable=durable,
            auto_delete=auto_delete,
            arguments=arguments
        )
        
        if result:
            return jsonify({
                'status': 'success',
                'message': f"Exchange {exchange_name} créé avec succès",
                'exchange_name': exchange_name,
                'exchange_type': exchange_type
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f"Échec de création de l'exchange {exchange_name}"
            }), 500
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'exchange {exchange_name}: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@messaging_service.route('/bindings', methods=['POST'])
@rate_limited(limit=15, period=60)
def bind_queue_to_exchange():
    """
    Lie une file d'attente à un exchange.
    
    Requête JSON attendue:
    {
        "queue_name": "my_queue",
        "exchange_name": "my_exchange",
        "routing_key": "my_routing_key"
    }
    """
    if rabbitmq_client is None:
        return jsonify({
            'error': 'Service unavailable',
            'message': 'Client RabbitMQ non initialisé'
        }), 503
    
    data = request.get_json()
    if not data or 'queue_name' not in data or 'exchange_name' not in data:
        return jsonify({
            'error': 'Bad request',
            'message': "Les paramètres 'queue_name' et 'exchange_name' sont requis"
        }), 400
    
    queue_name = data['queue_name']
    exchange_name = data['exchange_name']
    routing_key = data.get('routing_key', '')
    
    try:
        result = rabbitmq_client.bind_queue(
            queue_name=queue_name,
            exchange_name=exchange_name,
            routing_key=routing_key
        )
        
        if result:
            return jsonify({
                'status': 'success',
                'message': f"File {queue_name} liée à l'exchange {exchange_name} avec la clé {routing_key}",
                'queue_name': queue_name,
                'exchange_name': exchange_name,
                'routing_key': routing_key
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f"Échec de liaison de la file {queue_name} à l'exchange {exchange_name}"
            }), 500
    except Exception as e:
        logger.error(f"Erreur lors de la liaison de la file {queue_name} à l'exchange {exchange_name}: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@messaging_service.route('/messages', methods=['POST'])
@rate_limited(limit=100, period=60)
def publish_message():
    """
    Publie un message dans un exchange.
    
    Requête JSON attendue:
    {
        "exchange_name": "my_exchange",
        "routing_key": "my_routing_key",
        "message": {
            "key1": "value1",
            "key2": "value2"
        },
        "properties": {
            "content_type": "application/json",
            "delivery_mode": 2,
            "headers": {
                "custom_header": "value"
            }
        }
    }
    
    OU directement dans une file:
    
    {
        "queue_name": "my_queue",
        "message": "Hello world!",
        "properties": {
            "content_type": "text/plain",
            "delivery_mode": 2
        }
    }
    """
    if rabbitmq_client is None:
        return jsonify({
            'error': 'Service unavailable',
            'message': 'Client RabbitMQ non initialisé'
        }), 503
    
    data = request.get_json()
    if not data or ('exchange_name' not in data and 'queue_name' not in data) or 'message' not in data:
        return jsonify({
            'error': 'Bad request',
            'message': "Le corps de la requête doit contenir 'exchange_name' ou 'queue_name', et 'message'"
        }), 400
    
    message = data['message']
    properties_dict = data.get('properties', {})
    
    # Convertir le dictionnaire des propriétés en propriétés pika
    import pika
    properties = pika.BasicProperties(
        content_type=properties_dict.get('content_type', 'application/json'),
        content_encoding=properties_dict.get('content_encoding', 'utf-8'),
        headers=properties_dict.get('headers', {}),
        delivery_mode=properties_dict.get('delivery_mode', 2),
        priority=properties_dict.get('priority'),
        correlation_id=properties_dict.get('correlation_id'),
        reply_to=properties_dict.get('reply_to'),
        expiration=properties_dict.get('expiration'),
        message_id=properties_dict.get('message_id'),
        timestamp=properties_dict.get('timestamp', int(datetime.now().timestamp())),
        type=properties_dict.get('type'),
        user_id=properties_dict.get('user_id'),
        app_id=properties_dict.get('app_id', 'ia-solution-api')
    )
    
    try:
        # Publication dans un exchange ou directement dans une file
        if 'exchange_name' in data:
            exchange_name = data['exchange_name']
            routing_key = data.get('routing_key', '')
            mandatory = data.get('mandatory', False)
            
            result = rabbitmq_client.publish_message(
                exchange_name=exchange_name,
                routing_key=routing_key,
                message=message,
                properties=properties,
                mandatory=mandatory
            )
            
            if result:
                return jsonify({
                    'status': 'success',
                    'message': f"Message publié dans l'exchange {exchange_name} avec la clé {routing_key}",
                    'exchange_name': exchange_name,
                    'routing_key': routing_key
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': f"Échec de publication du message dans l'exchange {exchange_name}"
                }), 500
        else:
            queue_name = data['queue_name']
            
            result = rabbitmq_client.publish_to_queue(
                queue_name=queue_name,
                message=message,
                properties=properties
            )
            
            if result:
                return jsonify({
                    'status': 'success',
                    'message': f"Message publié dans la file {queue_name}",
                    'queue_name': queue_name
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': f"Échec de publication du message dans la file {queue_name}"
                }), 500
    except Exception as e:
        logger.error(f"Erreur lors de la publication du message: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@messaging_service.route('/messages/<queue_name>', methods=['GET'])
@rate_limited(limit=60, period=60)
def get_message(queue_name):
    """
    Récupère un message d'une file d'attente.
    
    Paramètres de requête:
    - auto_ack: Si true, acquitte automatiquement le message (défaut: false)
    """
    if rabbitmq_client is None:
        return jsonify({
            'error': 'Service unavailable',
            'message': 'Client RabbitMQ non initialisé'
        }), 503
    
    auto_ack = request.args.get('auto_ack', 'false').lower() == 'true'
    
    try:
        result = rabbitmq_client.get_message(
            queue_name=queue_name,
            auto_ack=auto_ack
        )
        
        if result:
            method_frame, properties, body = result
            
            # Préparer les informations sur les propriétés
            properties_dict = {}
            if properties:
                for key, value in properties.__dict__.items():
                    if key != '_body' and value is not None:
                        properties_dict[key] = value
            
            response = {
                'status': 'success',
                'message': "Message récupéré avec succès",
                'queue_name': queue_name,
                'delivery_tag': method_frame.delivery_tag,
                'body': body,
                'properties': properties_dict
            }
            
            return jsonify(response)
        else:
            return jsonify({
                'status': 'empty',
                'message': f"Aucun message disponible dans la file {queue_name}",
                'queue_name': queue_name
            }), 204
    except Exception as e:
        logger.error(f"Erreur lors de la récupération d'un message de la file {queue_name}: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@messaging_service.route('/ack', methods=['POST'])
@rate_limited(limit=100, period=60)
def acknowledge_message():
    """
    Acquitte un message.
    
    Requête JSON attendue:
    {
        "delivery_tag": 123
    }
    """
    if rabbitmq_client is None:
        return jsonify({
            'error': 'Service unavailable',
            'message': 'Client RabbitMQ non initialisé'
        }), 503
    
    data = request.get_json()
    if not data or 'delivery_tag' not in data:
        return jsonify({
            'error': 'Bad request',
            'message': "Le paramètre 'delivery_tag' est requis"
        }), 400
    
    delivery_tag = data['delivery_tag']
    
    try:
        result = rabbitmq_client.ack_message(delivery_tag=delivery_tag)
        
        if result:
            return jsonify({
                'status': 'success',
                'message': f"Message {delivery_tag} acquitté avec succès",
                'delivery_tag': delivery_tag
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f"Échec d'acquittement du message {delivery_tag}"
            }), 500
    except Exception as e:
        logger.error(f"Erreur lors de l'acquittement du message {delivery_tag}: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@messaging_service.route('/nack', methods=['POST'])
@rate_limited(limit=50, period=60)
def reject_message():
    """
    Rejette un message.
    
    Requête JSON attendue:
    {
        "delivery_tag": 123,
        "requeue": true
    }
    """
    if rabbitmq_client is None:
        return jsonify({
            'error': 'Service unavailable',
            'message': 'Client RabbitMQ non initialisé'
        }), 503
    
    data = request.get_json()
    if not data or 'delivery_tag' not in data:
        return jsonify({
            'error': 'Bad request',
            'message': "Le paramètre 'delivery_tag' est requis"
        }), 400
    
    delivery_tag = data['delivery_tag']
    requeue = data.get('requeue', True)
    
    try:
        result = rabbitmq_client.nack_message(
            delivery_tag=delivery_tag,
            requeue=requeue
        )
        
        if result:
            return jsonify({
                'status': 'success',
                'message': f"Message {delivery_tag} rejeté avec succès" + (" et remis dans la file" if requeue else ""),
                'delivery_tag': delivery_tag,
                'requeue': requeue
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f"Échec de rejet du message {delivery_tag}"
            }), 500
    except Exception as e:
        logger.error(f"Erreur lors du rejet du message {delivery_tag}: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@messaging_service.route('/queues/<queue_name>/purge', methods=['POST'])
@rate_limited(limit=5, period=60)
def purge_queue(queue_name):
    """Vide une file d'attente."""
    if rabbitmq_client is None:
        return jsonify({
            'error': 'Service unavailable',
            'message': 'Client RabbitMQ non initialisé'
        }), 503
    
    try:
        message_count = rabbitmq_client.purge_queue(queue_name=queue_name)
        
        if message_count is not None:
            return jsonify({
                'status': 'success',
                'message': f"File {queue_name} vidée avec succès",
                'queue_name': queue_name,
                'purged_messages': message_count
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f"Échec de purge de la file {queue_name}"
            }), 500
    except Exception as e:
        logger.error(f"Erreur lors de la purge de la file {queue_name}: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@messaging_service.route('/queues/<queue_name>', methods=['DELETE'])
@rate_limited(limit=5, period=60)
def delete_queue(queue_name):
    """
    Supprime une file d'attente.
    
    Paramètres de requête:
    - if_unused: Supprime seulement si la file n'est pas utilisée (défaut: false)
    - if_empty: Supprime seulement si la file est vide (défaut: false)
    """
    if rabbitmq_client is None:
        return jsonify({
            'error': 'Service unavailable',
            'message': 'Client RabbitMQ non initialisé'
        }), 503
    
    if_unused = request.args.get('if_unused', 'false').lower() == 'true'
    if_empty = request.args.get('if_empty', 'false').lower() == 'true'
    
    try:
        message_count = rabbitmq_client.delete_queue(
            queue_name=queue_name,
            if_unused=if_unused,
            if_empty=if_empty
        )
        
        if message_count is not None:
            return jsonify({
                'status': 'success',
                'message': f"File {queue_name} supprimée avec succès",
                'queue_name': queue_name,
                'undelivered_messages': message_count
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f"Échec de suppression de la file {queue_name}"
            }), 500
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de la file {queue_name}: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@messaging_service.route('/exchanges/<exchange_name>', methods=['DELETE'])
@rate_limited(limit=5, period=60)
def delete_exchange(exchange_name):
    """
    Supprime un exchange.
    
    Paramètres de requête:
    - if_unused: Supprime seulement si l'exchange n'est pas utilisé (défaut: false)
    """
    if rabbitmq_client is None:
        return jsonify({
            'error': 'Service unavailable',
            'message': 'Client RabbitMQ non initialisé'
        }), 503
    
    if_unused = request.args.get('if_unused', 'false').lower() == 'true'
    
    try:
        result = rabbitmq_client.delete_exchange(
            exchange_name=exchange_name,
            if_unused=if_unused
        )
        
        if result:
            return jsonify({
                'status': 'success',
                'message': f"Exchange {exchange_name} supprimé avec succès",
                'exchange_name': exchange_name
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f"Échec de suppression de l'exchange {exchange_name}"
            }), 500
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de l'exchange {exchange_name}: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@messaging_service.route('/queues/<queue_name>/info', methods=['GET'])
@cached(ttl=10, key_prefix='rabbitmq_queue_info')
@rate_limited(limit=30, period=60)
def get_queue_info(queue_name):
    """Récupère des informations sur une file d'attente."""
    if rabbitmq_client is None:
        return jsonify({
            'error': 'Service unavailable',
            'message': 'Client RabbitMQ non initialisé'
        }), 503
    
    try:
        info = rabbitmq_client.get_queue_info(queue_name=queue_name)
        
        if info:
            return jsonify({
                'status': 'success',
                'queue_info': info
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f"File {queue_name} non trouvée"
            }), 404
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des informations de la file {queue_name}: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


# Fonction pour enregistrer un gestionnaire de messages (handler)
def register_message_handler(queue_name, callback, exclusive=False):
    """
    Enregistre un gestionnaire pour consommer des messages d'une file d'attente.
    
    Args:
        queue_name (str): Nom de la file d'attente
        callback (function): Fonction de rappel pour traiter les messages
        exclusive (bool, optional): Si True, seule cette connexion peut consommer de cette file
        
    Returns:
        str or None: Tag de consommation si succès, None sinon
    """
    if rabbitmq_client is None:
        logger.error("Impossible d'enregistrer un gestionnaire de messages: Client RabbitMQ non initialisé")
        return None
    
    # Wrapper pour le callback qui gère automatiquement l'acquittement
    def message_handler(ch, method, properties, body):
        try:
            # Convertir le corps en JSON si possible
            message_body = body
            if isinstance(body, bytes):
                try:
                    message_body = body.decode('utf-8')
                    try:
                        message_body = json.loads(message_body)
                    except json.JSONDecodeError:
                        pass  # Conserver comme chaîne
                except UnicodeDecodeError:
                    pass  # Conserver comme bytes
            
            # Appeler le callback utilisateur
            result = callback(message_body, properties)
            
            # Acquitter le message si le callback a réussi
            if result is not False:
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                # Si le callback retourne explicitement False, rejeter le message
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        except Exception as e:
            logger.error(f"Erreur dans le gestionnaire de messages pour la file '{queue_name}': {e}")
            # Rejeter le message et le remettre dans la file
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    # Démarrer la consommation asynchrone
    consumer_tag = rabbitmq_client.consume_messages_async(
        queue_name=queue_name,
        callback=message_handler,
        auto_ack=False,
        exclusive=exclusive
    )
    
    if consumer_tag:
        message_handlers[queue_name] = consumer_tag
        logger.info(f"Gestionnaire de messages enregistré pour la file '{queue_name}'")
    
    return consumer_tag


# Fonction pour désinscrire un gestionnaire de messages
def unregister_message_handler(queue_name):
    """
    Désinscrit un gestionnaire de messages pour une file d'attente.
    
    Args:
        queue_name (str): Nom de la file d'attente
        
    Returns:
        bool: True si désinscrit avec succès, False sinon
    """
    if rabbitmq_client is None or queue_name not in message_handlers:
        return False
    
    result = rabbitmq_client.stop_consumer(queue_name)
    
    if result:
        # Supprimer le gestionnaire de la liste
        del message_handlers[queue_name]
        logger.info(f"Gestionnaire de messages désinscrit pour la file '{queue_name}'")
    
    return result


def register_service(app):
    """
    Enregistre le service de messagerie auprès de l'application Flask.
    
    Args:
        app: L'application Flask
    """
    global rabbitmq_client
    
    # Récupérer les paramètres de configuration pour RabbitMQ
    host = app.config.get('RABBITMQ_HOST', 'localhost')
    port = int(app.config.get('RABBITMQ_PORT', 5672))
    username = app.config.get('RABBITMQ_USERNAME', 'guest')
    password = app.config.get('RABBITMQ_PASSWORD', 'guest')
    virtual_host = app.config.get('RABBITMQ_VHOST', '/')
    
    # Initialiser le client RabbitMQ
    try:
        rabbitmq_client = RabbitMQClient(
            host=host,
            port=port,
            username=username,
            password=password,
            virtual_host=virtual_host
        )
        
        # Stocker le client dans l'application
        app.extensions['rabbitmq_client'] = rabbitmq_client
        
        # Enregistrer le blueprint
        app.register_blueprint(messaging_service)
        
        logger.info("Service de messagerie enregistré avec succès")
        
        # Déclarer les exchanges et files d'attente par défaut
        setup_default_messaging_infrastructure()
        
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du service de messagerie: {e}")
        # Ne pas bloquer le démarrage de l'application en cas d'erreur


def setup_default_messaging_infrastructure():
    """Configure les exchanges et files d'attente par défaut pour l'application."""
    if rabbitmq_client is None:
        logger.error("Impossible de configurer l'infrastructure de messagerie: Client RabbitMQ non initialisé")
        return
    
    try:
        # Déclarer les exchanges principaux
        rabbitmq_client.declare_exchange(
            exchange_name="ia_solution.events",
            exchange_type="topic",
            durable=True
        )
        
        rabbitmq_client.declare_exchange(
            exchange_name="ia_solution.dlx",
            exchange_type="fanout",
            durable=True
        )
        
        # Déclarer les files d'attente principales avec leurs files d'attente de lettres mortes
        for service in ["business", "marketing", "training", "finance", "notification"]:
            # File principale
            queue_name = f"ia_solution.{service}.tasks"
            rabbitmq_client.declare_queue(
                queue_name=queue_name,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": "ia_solution.dlx",
                    "x-message-ttl": 1000 * 60 * 60 * 24,  # 24 heures
                    "x-max-length": 10000
                }
            )
            
            # Lier la file à l'exchange d'événements avec les clés de routage appropriées
            rabbitmq_client.bind_queue(
                queue_name=queue_name,
                exchange_name="ia_solution.events",
                routing_key=f"{service}.#"
            )
        
        # File des lettres mortes
        rabbitmq_client.declare_queue(
            queue_name="ia_solution.dead_letters",
            durable=True
        )
        
        # Lier la file des lettres mortes à l'exchange DLX
        rabbitmq_client.bind_queue(
            queue_name="ia_solution.dead_letters",
            exchange_name="ia_solution.dlx",
            routing_key=""  # Toutes les clés de routage pour fanout
        )
        
        logger.info("Infrastructure de messagerie par défaut configurée avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors de la configuration de l'infrastructure de messagerie: {e}")


# Configuration des hooks de teardown pour fermer proprement les connexions RabbitMQ
def close_rabbitmq_connections():
    """Ferme toutes les connexions RabbitMQ lors de la fermeture de l'application."""
    if rabbitmq_client is not None:
        rabbitmq_client.close()
        logger.info("Connexions RabbitMQ fermées")