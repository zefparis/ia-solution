"""
Module client RabbitMQ

Ce module fournit une interface pour interagir avec RabbitMQ,
permettant la gestion de files de message et la communication asynchrone
entre les différents services de l'application.
"""

import os
import json
import logging
import threading
import time
from datetime import datetime
import pika
from pika.exceptions import AMQPConnectionError, ChannelClosedByBroker

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RabbitMQClient:
    """Client pour interagir avec RabbitMQ."""
    
    def __init__(self, host=None, port=None, username=None, password=None, virtual_host=None):
        """
        Initialise le client RabbitMQ.
        
        Args:
            host (str, optional): Hôte RabbitMQ
            port (int, optional): Port RabbitMQ
            username (str, optional): Nom d'utilisateur pour l'authentification
            password (str, optional): Mot de passe pour l'authentification
            virtual_host (str, optional): Hôte virtuel RabbitMQ
        """
        # Configuration par défaut depuis les variables d'environnement
        self.host = host or os.environ.get('RABBITMQ_HOST', 'localhost')
        self.port = port or int(os.environ.get('RABBITMQ_PORT', 5672))
        self.username = username or os.environ.get('RABBITMQ_USERNAME', 'guest')
        self.password = password or os.environ.get('RABBITMQ_PASSWORD', 'guest')
        self.virtual_host = virtual_host or os.environ.get('RABBITMQ_VHOST', '/')
        
        # État de la connexion
        self.connection = None
        self.channel = None
        self.is_connected = False
        
        # Pour les consommateurs
        self.consumer_threads = {}
        self.should_stop = False
        
        # Tentative de connexion initiale
        self._connect()
        
    def _connect(self):
        """
        Établit une connexion à RabbitMQ.
        
        Returns:
            bool: True si la connexion est établie avec succès, False sinon
        """
        try:
            # Paramètres de connexion
            credentials = pika.PlainCredentials(self.username, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                virtual_host=self.virtual_host,
                credentials=credentials,
                heartbeat=600,  # Heartbeat toutes les 10 minutes
                blocked_connection_timeout=300  # Timeout de 5 minutes
            )
            
            # Établir la connexion
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            self.is_connected = True
            
            logger.info(f"Connexion établie à RabbitMQ sur {self.host}:{self.port}")
            return True
            
        except AMQPConnectionError as e:
            logger.error(f"Erreur de connexion à RabbitMQ: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la connexion à RabbitMQ: {e}")
            self.is_connected = False
            return False
            
    def _ensure_connection(self):
        """
        S'assure que la connexion à RabbitMQ est active, tente de se reconnecter si nécessaire.
        
        Returns:
            bool: True si la connexion est active, False sinon
        """
        if not self.is_connected or self.connection is None or self.connection.is_closed:
            return self._connect()
        return True
        
    def _ensure_channel(self):
        """
        S'assure qu'un canal est ouvert pour la communication avec RabbitMQ.
        
        Returns:
            bool: True si le canal est actif, False sinon
        """
        if not self._ensure_connection():
            return False
            
        if self.channel is None or self.channel.is_closed:
            try:
                self.channel = self.connection.channel()
                return True
            except Exception as e:
                logger.error(f"Erreur lors de la création du canal: {e}")
                return False
                
        return True
        
    def close(self):
        """
        Ferme la connexion à RabbitMQ.
        """
        # Arrêter tous les consommateurs
        self.should_stop = True
        
        # Attendre que tous les threads de consommation se terminent
        for thread in self.consumer_threads.values():
            if thread.is_alive():
                thread.join(timeout=5)
                
        # Fermer le canal et la connexion
        if self.channel is not None and self.channel.is_open:
            self.channel.close()
            
        if self.connection is not None and self.connection.is_open:
            self.connection.close()
            
        self.is_connected = False
        logger.info("Connexion à RabbitMQ fermée")
        
    def declare_queue(self, queue_name, durable=True, exclusive=False, auto_delete=False, arguments=None):
        """
        Déclare une file d'attente.
        
        Args:
            queue_name (str): Nom de la file d'attente
            durable (bool, optional): Si True, la file d'attente survivra aux redémarrages du broker
            exclusive (bool, optional): Si True, la file sera utilisée par une seule connexion
            auto_delete (bool, optional): Si True, la file sera supprimée quand le dernier consommateur se déconnecte
            arguments (dict, optional): Arguments supplémentaires pour la file d'attente
            
        Returns:
            str or None: Nom de la file d'attente si déclarée avec succès, None sinon
        """
        if not self._ensure_channel():
            return None
            
        try:
            result = self.channel.queue_declare(
                queue=queue_name,
                durable=durable,
                exclusive=exclusive,
                auto_delete=auto_delete,
                arguments=arguments
            )
            
            # Si queue_name était vide, RabbitMQ génère un nom
            actual_queue_name = result.method.queue
            logger.info(f"File d'attente '{actual_queue_name}' déclarée avec succès")
            return actual_queue_name
            
        except ChannelClosedByBroker as e:
            logger.error(f"Erreur lors de la déclaration de la file '{queue_name}': {e}")
            self._ensure_channel()  # Réouvrir le canal
            return None
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la déclaration de la file '{queue_name}': {e}")
            return None
            
    def declare_exchange(self, exchange_name, exchange_type='direct', durable=True, auto_delete=False, arguments=None):
        """
        Déclare un exchange.
        
        Args:
            exchange_name (str): Nom de l'exchange
            exchange_type (str, optional): Type de l'exchange ('direct', 'topic', 'fanout', 'headers')
            durable (bool, optional): Si True, l'exchange survivra aux redémarrages du broker
            auto_delete (bool, optional): Si True, l'exchange sera supprimé quand la dernière file liée est supprimée
            arguments (dict, optional): Arguments supplémentaires pour l'exchange
            
        Returns:
            bool: True si l'exchange est déclaré avec succès, False sinon
        """
        if not self._ensure_channel():
            return False
            
        try:
            self.channel.exchange_declare(
                exchange=exchange_name,
                exchange_type=exchange_type,
                durable=durable,
                auto_delete=auto_delete,
                arguments=arguments
            )
            
            logger.info(f"Exchange '{exchange_name}' de type '{exchange_type}' déclaré avec succès")
            return True
            
        except ChannelClosedByBroker as e:
            logger.error(f"Erreur lors de la déclaration de l'exchange '{exchange_name}': {e}")
            self._ensure_channel()  # Réouvrir le canal
            return False
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la déclaration de l'exchange '{exchange_name}': {e}")
            return False
            
    def bind_queue(self, queue_name, exchange_name, routing_key=''):
        """
        Lie une file d'attente à un exchange.
        
        Args:
            queue_name (str): Nom de la file d'attente
            exchange_name (str): Nom de l'exchange
            routing_key (str, optional): Clé de routage
            
        Returns:
            bool: True si la liaison est établie avec succès, False sinon
        """
        if not self._ensure_channel():
            return False
            
        try:
            self.channel.queue_bind(
                queue=queue_name,
                exchange=exchange_name,
                routing_key=routing_key
            )
            
            logger.info(f"File '{queue_name}' liée à l'exchange '{exchange_name}' avec la clé '{routing_key}'")
            return True
            
        except ChannelClosedByBroker as e:
            logger.error(f"Erreur lors de la liaison de la file '{queue_name}' à l'exchange '{exchange_name}': {e}")
            self._ensure_channel()  # Réouvrir le canal
            return False
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la liaison de la file '{queue_name}' à l'exchange '{exchange_name}': {e}")
            return False
            
    def publish_message(self, exchange_name, routing_key, message, properties=None, mandatory=False):
        """
        Publie un message dans un exchange.
        
        Args:
            exchange_name (str): Nom de l'exchange
            routing_key (str): Clé de routage
            message (str or dict): Message à publier (sera converti en JSON si c'est un dict)
            properties (pika.BasicProperties, optional): Propriétés du message
            mandatory (bool, optional): Si True, génère une exception si le message ne peut pas être routé
            
        Returns:
            bool: True si le message est publié avec succès, False sinon
        """
        if not self._ensure_channel():
            return False
            
        try:
            # Préparer le corps du message
            if isinstance(message, dict):
                message_body = json.dumps(message).encode('utf-8')
            elif isinstance(message, str):
                message_body = message.encode('utf-8')
            else:
                message_body = str(message).encode('utf-8')
                
            # Propriétés par défaut pour le message
            if properties is None:
                properties = pika.BasicProperties(
                    delivery_mode=2,  # Message persistant
                    timestamp=int(time.time()),
                    content_type='application/json',
                    headers={'created_at': datetime.now().isoformat()}
                )
                
            # Publier le message
            self.channel.basic_publish(
                exchange=exchange_name,
                routing_key=routing_key,
                body=message_body,
                properties=properties,
                mandatory=mandatory
            )
            
            logger.debug(f"Message publié sur l'exchange '{exchange_name}' avec la clé '{routing_key}'")
            return True
            
        except ChannelClosedByBroker as e:
            logger.error(f"Erreur lors de la publication du message: {e}")
            self._ensure_channel()  # Réouvrir le canal
            return False
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la publication du message: {e}")
            return False
            
    def publish_to_queue(self, queue_name, message, properties=None):
        """
        Publie un message directement dans une file d'attente (sans passer par un exchange).
        
        Args:
            queue_name (str): Nom de la file d'attente
            message (str or dict): Message à publier (sera converti en JSON si c'est un dict)
            properties (pika.BasicProperties, optional): Propriétés du message
            
        Returns:
            bool: True si le message est publié avec succès, False sinon
        """
        # La publication dans une file se fait via l'exchange par défaut (exchange vide)
        return self.publish_message('', queue_name, message, properties)
        
    def consume_messages(self, queue_name, callback, auto_ack=False, exclusive=False):
        """
        Consomme des messages d'une file d'attente de manière synchrone (bloquant).
        
        Args:
            queue_name (str): Nom de la file d'attente
            callback (function): Fonction de rappel pour traiter les messages
            auto_ack (bool, optional): Si True, les messages sont automatiquement acquittés
            exclusive (bool, optional): Si True, seule cette connexion peut consommer de cette file
            
        Returns:
            str or None: Tag de consommation si succès, None sinon
        """
        if not self._ensure_channel():
            return None
            
        try:
            # Configurer la qualité de service (prefetch)
            self.channel.basic_qos(prefetch_count=1)
            
            # Démarrer la consommation
            consumer_tag = self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=auto_ack,
                exclusive=exclusive
            )
            
            logger.info(f"Consommation démarrée sur la file '{queue_name}' avec le tag '{consumer_tag}'")
            
            # Démarrer la boucle de consommation
            logger.info(f"En attente de messages sur la file '{queue_name}'...")
            self.channel.start_consuming()
            
            return consumer_tag
            
        except ChannelClosedByBroker as e:
            logger.error(f"Erreur lors de la consommation de la file '{queue_name}': {e}")
            self._ensure_channel()  # Réouvrir le canal
            return None
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la consommation de la file '{queue_name}': {e}")
            return None
            
    def consume_messages_async(self, queue_name, callback, auto_ack=False, exclusive=False):
        """
        Consomme des messages d'une file d'attente de manière asynchrone (non bloquant).
        
        Args:
            queue_name (str): Nom de la file d'attente
            callback (function): Fonction de rappel pour traiter les messages
            auto_ack (bool, optional): Si True, les messages sont automatiquement acquittés
            exclusive (bool, optional): Si True, seule cette connexion peut consommer de cette file
            
        Returns:
            str or None: Tag de consommation si le thread est démarré avec succès, None sinon
        """
        if queue_name in self.consumer_threads and self.consumer_threads[queue_name].is_alive():
            logger.warning(f"Un consommateur est déjà actif sur la file '{queue_name}'")
            return None
            
        def consumer_thread():
            """Fonction exécutée dans un thread dédié pour la consommation."""
            # Créer une nouvelle connexion pour ce thread
            thread_client = RabbitMQClient(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                virtual_host=self.virtual_host
            )
            
            try:
                # Démarrer la consommation
                thread_client.consume_messages(queue_name, callback, auto_ack, exclusive)
            except Exception as e:
                logger.error(f"Erreur dans le thread de consommation pour la file '{queue_name}': {e}")
            finally:
                # Fermer la connexion du thread
                thread_client.close()
                
        # Créer et démarrer le thread
        consumer_thread_obj = threading.Thread(
            target=consumer_thread,
            name=f"consumer-{queue_name}",
            daemon=True  # Le thread s'arrêtera automatiquement si le programme principal se termine
        )
        
        self.consumer_threads[queue_name] = consumer_thread_obj
        consumer_thread_obj.start()
        
        logger.info(f"Thread de consommation démarré pour la file '{queue_name}'")
        return f"consumer-{queue_name}"
        
    def stop_consumer(self, queue_name):
        """
        Arrête un consommateur asynchrone.
        
        Args:
            queue_name (str): Nom de la file d'attente associée au consommateur
            
        Returns:
            bool: True si le consommateur est arrêté avec succès, False sinon
        """
        if queue_name not in self.consumer_threads:
            logger.warning(f"Aucun consommateur actif sur la file '{queue_name}'")
            return False
            
        thread = self.consumer_threads[queue_name]
        if not thread.is_alive():
            logger.warning(f"Le thread de consommation pour la file '{queue_name}' n'est pas actif")
            del self.consumer_threads[queue_name]
            return False
            
        # Attendre que le thread se termine (avec timeout)
        thread.join(timeout=5)
        
        # Vérifier si le thread s'est terminé
        if thread.is_alive():
            logger.warning(f"Le thread de consommation pour la file '{queue_name}' n'a pas pu être arrêté proprement")
            return False
            
        # Supprimer le thread de la liste
        del self.consumer_threads[queue_name]
        logger.info(f"Consommateur sur la file '{queue_name}' arrêté avec succès")
        return True
        
    def get_message(self, queue_name, auto_ack=False):
        """
        Récupère un seul message d'une file d'attente (non bloquant).
        
        Args:
            queue_name (str): Nom de la file d'attente
            auto_ack (bool, optional): Si True, le message est automatiquement acquitté
            
        Returns:
            tuple or None: (method, properties, body) si un message est disponible, None sinon
        """
        if not self._ensure_channel():
            return None
            
        try:
            # Récupérer un message de la file
            method_frame, header_frame, body = self.channel.basic_get(queue=queue_name, auto_ack=auto_ack)
            
            if method_frame:
                # Un message a été récupéré
                if isinstance(body, bytes):
                    # Tenter de décoder le corps du message
                    try:
                        body = body.decode('utf-8')
                        # Tenter de parser en JSON si c'est un objet JSON
                        if body.startswith('{') or body.startswith('['):
                            try:
                                body = json.loads(body)
                            except json.JSONDecodeError:
                                pass  # Conserver le corps comme une chaîne
                    except UnicodeDecodeError:
                        pass  # Conserver le corps comme des octets
                        
                return method_frame, header_frame, body
            else:
                # Aucun message n'est disponible
                return None
                
        except ChannelClosedByBroker as e:
            logger.error(f"Erreur lors de la récupération d'un message de la file '{queue_name}': {e}")
            self._ensure_channel()  # Réouvrir le canal
            return None
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la récupération d'un message de la file '{queue_name}': {e}")
            return None
            
    def ack_message(self, delivery_tag):
        """
        Acquitte un message.
        
        Args:
            delivery_tag (int): Tag de livraison du message
            
        Returns:
            bool: True si le message est acquitté avec succès, False sinon
        """
        if not self._ensure_channel():
            return False
            
        try:
            self.channel.basic_ack(delivery_tag=delivery_tag)
            return True
        except ChannelClosedByBroker as e:
            logger.error(f"Erreur lors de l'acquittement du message {delivery_tag}: {e}")
            self._ensure_channel()  # Réouvrir le canal
            return False
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'acquittement du message {delivery_tag}: {e}")
            return False
            
    def nack_message(self, delivery_tag, requeue=True):
        """
        Rejette un message.
        
        Args:
            delivery_tag (int): Tag de livraison du message
            requeue (bool, optional): Si True, le message est remis dans la file
            
        Returns:
            bool: True si le message est rejeté avec succès, False sinon
        """
        if not self._ensure_channel():
            return False
            
        try:
            self.channel.basic_nack(delivery_tag=delivery_tag, requeue=requeue)
            return True
        except ChannelClosedByBroker as e:
            logger.error(f"Erreur lors du rejet du message {delivery_tag}: {e}")
            self._ensure_channel()  # Réouvrir le canal
            return False
        except Exception as e:
            logger.error(f"Erreur inattendue lors du rejet du message {delivery_tag}: {e}")
            return False
            
    def purge_queue(self, queue_name):
        """
        Vide une file d'attente.
        
        Args:
            queue_name (str): Nom de la file d'attente
            
        Returns:
            int or None: Nombre de messages purgés si succès, None sinon
        """
        if not self._ensure_channel():
            return None
            
        try:
            response = self.channel.queue_purge(queue=queue_name)
            message_count = response.method.message_count
            logger.info(f"File '{queue_name}' purgée, {message_count} messages supprimés")
            return message_count
        except ChannelClosedByBroker as e:
            logger.error(f"Erreur lors de la purge de la file '{queue_name}': {e}")
            self._ensure_channel()  # Réouvrir le canal
            return None
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la purge de la file '{queue_name}': {e}")
            return None
            
    def delete_queue(self, queue_name, if_unused=False, if_empty=False):
        """
        Supprime une file d'attente.
        
        Args:
            queue_name (str): Nom de la file d'attente
            if_unused (bool, optional): Si True, la file est supprimée seulement si elle n'est pas utilisée
            if_empty (bool, optional): Si True, la file est supprimée seulement si elle est vide
            
        Returns:
            int or None: Nombre de messages non délivrés si succès, None sinon
        """
        if not self._ensure_channel():
            return None
            
        try:
            response = self.channel.queue_delete(
                queue=queue_name,
                if_unused=if_unused,
                if_empty=if_empty
            )
            
            message_count = response.method.message_count
            logger.info(f"File '{queue_name}' supprimée, {message_count} messages non délivrés")
            return message_count
        except ChannelClosedByBroker as e:
            logger.error(f"Erreur lors de la suppression de la file '{queue_name}': {e}")
            self._ensure_channel()  # Réouvrir le canal
            return None
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la suppression de la file '{queue_name}': {e}")
            return None
            
    def delete_exchange(self, exchange_name, if_unused=False):
        """
        Supprime un exchange.
        
        Args:
            exchange_name (str): Nom de l'exchange
            if_unused (bool, optional): Si True, l'exchange est supprimé seulement s'il n'est pas utilisé
            
        Returns:
            bool: True si l'exchange est supprimé avec succès, False sinon
        """
        if not self._ensure_channel():
            return False
            
        try:
            self.channel.exchange_delete(
                exchange=exchange_name,
                if_unused=if_unused
            )
            
            logger.info(f"Exchange '{exchange_name}' supprimé avec succès")
            return True
        except ChannelClosedByBroker as e:
            logger.error(f"Erreur lors de la suppression de l'exchange '{exchange_name}': {e}")
            self._ensure_channel()  # Réouvrir le canal
            return False
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la suppression de l'exchange '{exchange_name}': {e}")
            return False
            
    def get_queue_info(self, queue_name):
        """
        Récupère des informations sur une file d'attente.
        
        Args:
            queue_name (str): Nom de la file d'attente
            
        Returns:
            dict or None: Informations sur la file d'attente si elle existe, None sinon
        """
        if not self._ensure_channel():
            return None
            
        try:
            # La méthode queue_declare avec passive=True permet de vérifier si la file existe
            # sans la créer si elle n'existe pas
            response = self.channel.queue_declare(queue=queue_name, passive=True)
            
            return {
                'name': queue_name,
                'message_count': response.method.message_count,
                'consumer_count': response.method.consumer_count
            }
        except ChannelClosedByBroker:
            # La file n'existe pas
            logger.warning(f"La file '{queue_name}' n'existe pas")
            self._ensure_channel()  # Réouvrir le canal
            return None
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la récupération des informations de la file '{queue_name}': {e}")
            return None
            
    def health_check(self):
        """
        Vérifie l'état de santé de la connexion RabbitMQ.
        
        Returns:
            dict: État de santé de la connexion RabbitMQ
        """
        health_status = {
            'status': 'healthy' if self.is_connected else 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'connection': {
                'host': self.host,
                'port': self.port,
                'virtual_host': self.virtual_host,
                'is_connected': self.is_connected
            },
            'active_consumers': len(self.consumer_threads),
            'channel_open': self.channel is not None and self.channel.is_open if self.channel else False
        }
        
        # Tenter de se reconnecter si déconnecté
        if not self.is_connected:
            reconnect_success = self._connect()
            health_status['reconnect_attempted'] = True
            health_status['reconnect_success'] = reconnect_success
            
        return health_status