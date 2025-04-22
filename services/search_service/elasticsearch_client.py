"""
Module client Elasticsearch

Ce module fournit une interface pour interagir avec Elasticsearch,
permettant l'indexation et la recherche de contenu dans l'application.
"""

import os
import json
import logging
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ElasticsearchException, NotFoundError

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ElasticsearchClient:
    """Client pour interagir avec Elasticsearch."""
    
    def __init__(self, hosts=None, cloud_id=None, api_key=None, basic_auth=None):
        """
        Initialise le client Elasticsearch.
        
        Args:
            hosts (list or str, optional): Liste des hôtes Elasticsearch ou URL unique
            cloud_id (str, optional): Cloud ID pour Elastic Cloud
            api_key (str or tuple, optional): Clé API pour l'authentification
            basic_auth (tuple, optional): Tuple (username, password) pour l'auth HTTP Basic
        """
        # Configuration par défaut depuis les variables d'environnement
        if hosts is None:
            hosts = os.environ.get('ELASTICSEARCH_HOSTS', 'http://localhost:9200')
            if ',' in hosts:
                hosts = hosts.split(',')
                
        # Configuration de l'authentification
        if cloud_id is None and os.environ.get('ELASTICSEARCH_CLOUD_ID'):
            cloud_id = os.environ.get('ELASTICSEARCH_CLOUD_ID')
            
        if api_key is None and os.environ.get('ELASTICSEARCH_API_KEY'):
            api_key = os.environ.get('ELASTICSEARCH_API_KEY')
            
        if basic_auth is None and os.environ.get('ELASTICSEARCH_USERNAME'):
            username = os.environ.get('ELASTICSEARCH_USERNAME')
            password = os.environ.get('ELASTICSEARCH_PASSWORD', '')
            basic_auth = (username, password)
            
        # Initialiser le client Elasticsearch
        client_kwargs = {}
        if cloud_id:
            client_kwargs['cloud_id'] = cloud_id
        else:
            client_kwargs['hosts'] = hosts
            
        if api_key:
            client_kwargs['api_key'] = api_key
        elif basic_auth:
            client_kwargs['basic_auth'] = basic_auth
            
        self.client = Elasticsearch(**client_kwargs)
        
        # Vérifier la connexion
        try:
            info = self.client.info()
            logger.info(f"Connecté à Elasticsearch version {info['version']['number']}")
        except ElasticsearchException as e:
            logger.error(f"Erreur de connexion à Elasticsearch: {e}")
            
    def create_index(self, index, mappings=None, settings=None):
        """
        Crée un nouvel index avec des mappings et settings optionnels.
        
        Args:
            index (str): Nom de l'index
            mappings (dict, optional): Mappings pour les champs de l'index
            settings (dict, optional): Paramètres de configuration de l'index
            
        Returns:
            bool: True si l'index a été créé avec succès, False sinon
        """
        try:
            # Vérifier si l'index existe déjà
            if self.client.indices.exists(index=index):
                logger.info(f"L'index {index} existe déjà")
                return True
                
            # Créer l'index avec les mappings et settings spécifiés
            create_params = {}
            if mappings:
                create_params['mappings'] = mappings
            if settings:
                create_params['settings'] = settings
                
            response = self.client.indices.create(index=index, **create_params)
            
            if response.get('acknowledged', False):
                logger.info(f"Index {index} créé avec succès")
                return True
            else:
                logger.warning(f"Création de l'index {index} non confirmée")
                return False
                
        except ElasticsearchException as e:
            logger.error(f"Erreur lors de la création de l'index {index}: {e}")
            return False
            
    def delete_index(self, index):
        """
        Supprime un index existant.
        
        Args:
            index (str): Nom de l'index
            
        Returns:
            bool: True si l'index a été supprimé avec succès, False sinon
        """
        try:
            # Vérifier si l'index existe
            if not self.client.indices.exists(index=index):
                logger.info(f"L'index {index} n'existe pas")
                return True
                
            # Supprimer l'index
            response = self.client.indices.delete(index=index)
            
            if response.get('acknowledged', False):
                logger.info(f"Index {index} supprimé avec succès")
                return True
            else:
                logger.warning(f"Suppression de l'index {index} non confirmée")
                return False
                
        except ElasticsearchException as e:
            logger.error(f"Erreur lors de la suppression de l'index {index}: {e}")
            return False
            
    def index_document(self, index, document, doc_id=None, refresh=False):
        """
        Indexe un document dans Elasticsearch.
        
        Args:
            index (str): Nom de l'index
            document (dict): Document à indexer
            doc_id (str, optional): ID du document. Si None, un ID sera généré.
            refresh (bool, optional): Si True, l'index sera rafraîchi immédiatement
            
        Returns:
            str or None: ID du document indexé, ou None en cas d'erreur
        """
        try:
            # Ajouter un timestamp si non présent
            if 'timestamp' not in document:
                document['timestamp'] = datetime.now().isoformat()
                
            # Indexer le document
            response = self.client.index(
                index=index,
                document=document,
                id=doc_id,
                refresh=refresh
            )
            
            logger.info(f"Document indexé avec succès, ID: {response['_id']}")
            return response['_id']
            
        except ElasticsearchException as e:
            logger.error(f"Erreur lors de l'indexation du document: {e}")
            return None
            
    def bulk_index(self, index, documents, id_field=None, refresh=False):
        """
        Indexe plusieurs documents en masse.
        
        Args:
            index (str): Nom de l'index
            documents (list): Liste de dictionnaires représentant les documents
            id_field (str, optional): Nom du champ à utiliser comme ID
            refresh (bool, optional): Si True, l'index sera rafraîchi immédiatement
            
        Returns:
            tuple: (Nombre de documents indexés avec succès, nombre d'erreurs)
        """
        try:
            operations = []
            for doc in documents:
                # Ajouter un timestamp si non présent
                if 'timestamp' not in doc:
                    doc['timestamp'] = datetime.now().isoformat()
                    
                # Créer l'opération d'indexation
                op_dict = {
                    "_index": index,
                    "_source": doc
                }
                
                # Ajouter l'ID si le champ id_field est spécifié et présent
                if id_field and id_field in doc:
                    op_dict["_id"] = doc[id_field]
                    
                operations.append({"index": op_dict})
                
            # Exécuter l'indexation en masse
            if not operations:
                logger.warning("Aucun document à indexer")
                return 0, 0
                
            response = self.client.bulk(operations=operations, refresh=refresh)
            
            # Analyser les résultats
            total = len(operations)
            errors = 0
            if response.get('errors', False):
                for item in response['items']:
                    if 'error' in item.get('index', {}):
                        errors += 1
                        error_info = item['index']['error']
                        logger.error(f"Erreur d'indexation: {error_info['type']} - {error_info['reason']}")
                        
            success = total - errors
            logger.info(f"Indexation en masse: {success} succès, {errors} erreurs sur {total} documents")
            return success, errors
            
        except ElasticsearchException as e:
            logger.error(f"Erreur lors de l'indexation en masse: {e}")
            return 0, len(documents)
            
    def get_document(self, index, doc_id):
        """
        Récupère un document par son ID.
        
        Args:
            index (str): Nom de l'index
            doc_id (str): ID du document
            
        Returns:
            dict or None: Document si trouvé, None sinon
        """
        try:
            response = self.client.get(index=index, id=doc_id)
            return response['_source']
        except NotFoundError:
            logger.info(f"Document non trouvé: {index}/{doc_id}")
            return None
        except ElasticsearchException as e:
            logger.error(f"Erreur lors de la récupération du document {index}/{doc_id}: {e}")
            return None
            
    def delete_document(self, index, doc_id, refresh=False):
        """
        Supprime un document par son ID.
        
        Args:
            index (str): Nom de l'index
            doc_id (str): ID du document
            refresh (bool, optional): Si True, l'index sera rafraîchi immédiatement
            
        Returns:
            bool: True si le document a été supprimé, False sinon
        """
        try:
            response = self.client.delete(index=index, id=doc_id, refresh=refresh)
            result = response.get('result', '')
            
            if result == 'deleted':
                logger.info(f"Document {index}/{doc_id} supprimé avec succès")
                return True
            elif result == 'not_found':
                logger.info(f"Document {index}/{doc_id} non trouvé")
                return False
            else:
                logger.warning(f"Résultat inattendu lors de la suppression: {result}")
                return False
                
        except NotFoundError:
            logger.info(f"Document non trouvé lors de la suppression: {index}/{doc_id}")
            return False
        except ElasticsearchException as e:
            logger.error(f"Erreur lors de la suppression du document {index}/{doc_id}: {e}")
            return False
            
    def update_document(self, index, doc_id, update_data, doc_as_upsert=False, refresh=False):
        """
        Met à jour un document existant.
        
        Args:
            index (str): Nom de l'index
            doc_id (str): ID du document
            update_data (dict): Données à mettre à jour
            doc_as_upsert (bool, optional): Si True, crée le document s'il n'existe pas
            refresh (bool, optional): Si True, l'index sera rafraîchi immédiatement
            
        Returns:
            bool: True si mise à jour réussie, False sinon
        """
        try:
            # Ajouter un timestamp de mise à jour
            update_data['updated_at'] = datetime.now().isoformat()
            
            response = self.client.update(
                index=index,
                id=doc_id,
                doc=update_data,
                doc_as_upsert=doc_as_upsert,
                refresh=refresh
            )
            
            result = response.get('result', '')
            
            if result in ['updated', 'created', 'noop']:
                logger.info(f"Document {index}/{doc_id} mis à jour avec succès (résultat: {result})")
                return True
            else:
                logger.warning(f"Résultat inattendu lors de la mise à jour: {result}")
                return False
                
        except NotFoundError:
            logger.info(f"Document non trouvé lors de la mise à jour: {index}/{doc_id}")
            return False
        except ElasticsearchException as e:
            logger.error(f"Erreur lors de la mise à jour du document {index}/{doc_id}: {e}")
            return False
            
    def search(self, index, query, from_=0, size=10, sort=None, _source=None, highlight=None):
        """
        Effectue une recherche dans Elasticsearch.
        
        Args:
            index (str): Nom de l'index
            query (dict): Requête Elasticsearch
            from_ (int, optional): Offset pour la pagination
            size (int, optional): Nombre de résultats à retourner
            sort (list, optional): Liste de champs pour le tri
            _source (list, optional): Liste de champs à retourner
            highlight (dict, optional): Configuration pour la mise en surbrillance
            
        Returns:
            dict: Résultats de la recherche avec métadonnées
        """
        try:
            search_params = {
                "from_": from_,
                "size": size,
                "query": query
            }
            
            if sort:
                search_params["sort"] = sort
                
            if _source is not None:
                search_params["_source"] = _source
                
            if highlight:
                search_params["highlight"] = highlight
                
            response = self.client.search(index=index, **search_params)
            
            # Formater les résultats
            results = {
                "total": response["hits"]["total"]["value"],
                "max_score": response["hits"]["max_score"],
                "took_ms": response["took"],
                "hits": []
            }
            
            for hit in response["hits"]["hits"]:
                result = {
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "source": hit["_source"]
                }
                
                # Ajouter les extraits mis en surbrillance si présents
                if "highlight" in hit:
                    result["highlight"] = hit["highlight"]
                    
                results["hits"].append(result)
                
            return results
            
        except ElasticsearchException as e:
            logger.error(f"Erreur lors de la recherche: {e}")
            return {
                "total": 0,
                "max_score": None,
                "took_ms": 0,
                "hits": [],
                "error": str(e)
            }
            
    def full_text_search(self, index, query_text, fields=None, operator="or", from_=0, size=10,
                          highlight_fields=None, fuzziness=None):
        """
        Effectue une recherche en texte intégral.
        
        Args:
            index (str): Nom de l'index
            query_text (str): Texte à rechercher
            fields (list, optional): Champs dans lesquels chercher
            operator (str, optional): Opérateur logique ("and" ou "or")
            from_ (int, optional): Offset pour la pagination
            size (int, optional): Nombre de résultats à retourner
            highlight_fields (list, optional): Champs à mettre en surbrillance
            fuzziness (str, optional): Niveau de tolérance aux fautes ("AUTO", "0", "1", "2")
            
        Returns:
            dict: Résultats de la recherche avec métadonnées
        """
        try:
            # Construire la requête
            if not fields:
                fields = ["*"]
                
            query_params = {
                "query": query_text,
                "fields": fields,
                "operator": operator
            }
            
            if fuzziness:
                query_params["fuzziness"] = fuzziness
                
            query = {
                "multi_match": query_params
            }
            
            # Configuration de la mise en surbrillance
            highlight = None
            if highlight_fields:
                highlight = {
                    "fields": {field: {} for field in highlight_fields},
                    "pre_tags": ["<em>"],
                    "post_tags": ["</em>"],
                    "fragment_size": 150,
                    "number_of_fragments": 3
                }
                
            # Exécuter la recherche
            return self.search(
                index=index,
                query=query,
                from_=from_,
                size=size,
                highlight=highlight
            )
            
        except ElasticsearchException as e:
            logger.error(f"Erreur lors de la recherche en texte intégral: {e}")
            return {
                "total": 0,
                "max_score": None,
                "took_ms": 0,
                "hits": [],
                "error": str(e)
            }
            
    def health_check(self):
        """
        Vérifie l'état de santé d'Elasticsearch.
        
        Returns:
            dict: État de santé d'Elasticsearch
        """
        try:
            # Vérifier la connexion avec un ping
            ping_result = self.client.ping()
            
            if not ping_result:
                return {
                    "status": "error",
                    "message": "Le serveur Elasticsearch ne répond pas au ping"
                }
                
            # Récupérer l'info du cluster
            info = self.client.info()
            health = self.client.cluster.health()
            
            return {
                "status": "healthy",
                "cluster_name": health["cluster_name"],
                "cluster_status": health["status"],
                "number_of_nodes": health["number_of_nodes"],
                "active_shards": health["active_shards"],
                "es_version": info["version"]["number"],
                "active_primary_shards": health["active_primary_shards"],
                "relocating_shards": health["relocating_shards"],
                "initializing_shards": health["initializing_shards"],
                "unassigned_shards": health["unassigned_shards"]
            }
            
        except ElasticsearchException as e:
            logger.error(f"Erreur lors de la vérification de l'état d'Elasticsearch: {e}")
            return {
                "status": "error",
                "message": str(e)
            }