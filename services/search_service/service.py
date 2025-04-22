"""
Service de recherche - Microservice responsable de la recherche avec Elasticsearch

Ce service expose une API REST pour indexer et rechercher des documents 
dans différents domaines de l'application.
"""

import os
import json
import logging
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app, g
from elasticsearch.exceptions import ElasticsearchException

from cache.flask_integration import cached, rate_limited
from services.search_service.elasticsearch_client import ElasticsearchClient

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Création du Blueprint pour le service de recherche
search_service = Blueprint('search_service', __name__, url_prefix='/api/search')

# Client Elasticsearch - sera initialisé lors de l'enregistrement du service
es_client = None


@search_service.route('/health', methods=['GET'])
def health_check():
    """Endpoint de vérification de l'état du service de recherche."""
    if es_client is None:
        return jsonify({
            'service': 'search_service',
            'status': 'error',
            'message': 'Client Elasticsearch non initialisé',
            'timestamp': datetime.now().isoformat()
        }), 500
    
    # Vérifier l'état d'Elasticsearch
    es_health = es_client.health_check()
    
    response = {
        'service': 'search_service',
        'status': 'healthy' if es_health.get('status') == 'healthy' else 'unhealthy',
        'timestamp': datetime.now().isoformat(),
        'elasticsearch': es_health
    }
    
    status_code = 200 if response['status'] == 'healthy' else 500
    return jsonify(response), status_code


@search_service.route('/indices', methods=['GET'])
@rate_limited(limit=20, period=60)
def list_indices():
    """Liste les indices disponibles."""
    try:
        indices = es_client.client.indices.get('*')
        result = {}
        
        for index_name, index_info in indices.items():
            # Filtrer les informations pertinentes
            result[index_name] = {
                'mappings': index_info.get('mappings', {}),
                'settings': {
                    'number_of_shards': index_info.get('settings', {}).get('index', {}).get('number_of_shards'),
                    'number_of_replicas': index_info.get('settings', {}).get('index', {}).get('number_of_replicas')
                }
            }
        
        return jsonify({
            'indices': result,
            'count': len(result)
        })
    except ElasticsearchException as e:
        logger.error(f"Erreur lors de la récupération des indices: {e}")
        return jsonify({
            'error': 'Elasticsearch error',
            'message': str(e)
        }), 500


@search_service.route('/indices/<index_name>', methods=['PUT'])
@rate_limited(limit=10, period=60)
def create_index(index_name):
    """
    Crée un nouvel index.
    
    Requête JSON attendue:
    {
        "mappings": {
            "properties": {
                "field1": {"type": "text"},
                "field2": {"type": "keyword"},
                ...
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 1,
            ...
        }
    }
    """
    data = request.get_json() or {}
    mappings = data.get('mappings')
    settings = data.get('settings')
    
    try:
        result = es_client.create_index(index_name, mappings, settings)
        if result:
            return jsonify({
                'status': 'success',
                'message': f"Index {index_name} créé avec succès"
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f"Échec de création de l'index {index_name}"
            }), 500
    except ElasticsearchException as e:
        logger.error(f"Erreur lors de la création de l'index {index_name}: {e}")
        return jsonify({
            'error': 'Elasticsearch error',
            'message': str(e)
        }), 500


@search_service.route('/indices/<index_name>', methods=['DELETE'])
@rate_limited(limit=5, period=60)
def delete_index(index_name):
    """Supprime un index existant."""
    try:
        result = es_client.delete_index(index_name)
        if result:
            return jsonify({
                'status': 'success',
                'message': f"Index {index_name} supprimé avec succès"
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f"Échec de suppression de l'index {index_name}"
            }), 500
    except ElasticsearchException as e:
        logger.error(f"Erreur lors de la suppression de l'index {index_name}: {e}")
        return jsonify({
            'error': 'Elasticsearch error',
            'message': str(e)
        }), 500


@search_service.route('/<index_name>/_doc', methods=['POST'])
@search_service.route('/<index_name>/_doc/<doc_id>', methods=['POST', 'PUT'])
@rate_limited(limit=30, period=60)
def index_document(index_name, doc_id=None):
    """
    Indexe un document.
    
    Requête JSON attendue:
    {
        "field1": "value1",
        "field2": "value2",
        ...
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({
            'error': 'Invalid request',
            'message': 'Corps de requête JSON requis'
        }), 400
    
    # Paramètres optionnels
    refresh = request.args.get('refresh', 'false').lower() == 'true'
    
    try:
        # Si c'est une mise à jour (PUT)
        if request.method == 'PUT' and doc_id:
            result = es_client.update_document(
                index=index_name,
                doc_id=doc_id,
                update_data=data,
                doc_as_upsert=True,
                refresh=refresh
            )
            
            if result:
                return jsonify({
                    'status': 'success',
                    'message': f"Document {doc_id} mis à jour avec succès",
                    'id': doc_id
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': f"Échec de mise à jour du document {doc_id}"
                }), 500
        # Si c'est une création (POST)
        else:
            doc_id = es_client.index_document(
                index=index_name,
                document=data,
                doc_id=doc_id,
                refresh=refresh
            )
            
            if doc_id:
                return jsonify({
                    'status': 'success',
                    'message': "Document indexé avec succès",
                    'id': doc_id
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': "Échec d'indexation du document"
                }), 500
    except ElasticsearchException as e:
        logger.error(f"Erreur lors de l'indexation du document: {e}")
        return jsonify({
            'error': 'Elasticsearch error',
            'message': str(e)
        }), 500


@search_service.route('/<index_name>/_bulk', methods=['POST'])
@rate_limited(limit=10, period=60)
def bulk_index(index_name):
    """
    Indexe plusieurs documents en masse.
    
    Requête JSON attendue:
    {
        "documents": [
            {"field1": "value1", "field2": "value2", ...},
            {"field1": "value3", "field2": "value4", ...},
            ...
        ],
        "id_field": "optional_field_to_use_as_id"
    }
    """
    data = request.get_json()
    if not data or 'documents' not in data:
        return jsonify({
            'error': 'Invalid request',
            'message': 'Corps de requête JSON requis avec le champ "documents"'
        }), 400
    
    documents = data['documents']
    id_field = data.get('id_field')
    refresh = request.args.get('refresh', 'false').lower() == 'true'
    
    if not documents:
        return jsonify({
            'status': 'warning',
            'message': 'Aucun document à indexer'
        })
    
    try:
        success, errors = es_client.bulk_index(
            index=index_name,
            documents=documents,
            id_field=id_field,
            refresh=refresh
        )
        
        return jsonify({
            'status': 'success' if errors == 0 else 'partial',
            'message': f"{success} documents indexés avec succès, {errors} erreurs",
            'success_count': success,
            'error_count': errors,
            'total': len(documents)
        })
    except ElasticsearchException as e:
        logger.error(f"Erreur lors de l'indexation en masse: {e}")
        return jsonify({
            'error': 'Elasticsearch error',
            'message': str(e)
        }), 500


@search_service.route('/<index_name>/_doc/<doc_id>', methods=['GET'])
@cached(ttl=300, key_prefix='es_get_doc')
def get_document(index_name, doc_id):
    """Récupère un document par son ID."""
    try:
        doc = es_client.get_document(index_name, doc_id)
        if doc:
            return jsonify(doc)
        else:
            return jsonify({
                'error': 'Not found',
                'message': f"Document {doc_id} non trouvé dans l'index {index_name}"
            }), 404
    except ElasticsearchException as e:
        logger.error(f"Erreur lors de la récupération du document: {e}")
        return jsonify({
            'error': 'Elasticsearch error',
            'message': str(e)
        }), 500


@search_service.route('/<index_name>/_doc/<doc_id>', methods=['DELETE'])
@rate_limited(limit=20, period=60)
def delete_document(index_name, doc_id):
    """Supprime un document par son ID."""
    refresh = request.args.get('refresh', 'false').lower() == 'true'
    
    try:
        result = es_client.delete_document(index_name, doc_id, refresh)
        if result:
            return jsonify({
                'status': 'success',
                'message': f"Document {doc_id} supprimé avec succès"
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f"Document {doc_id} non trouvé ou non supprimé"
            }), 404
    except ElasticsearchException as e:
        logger.error(f"Erreur lors de la suppression du document: {e}")
        return jsonify({
            'error': 'Elasticsearch error',
            'message': str(e)
        }), 500


@search_service.route('/<index_name>/_search', methods=['POST'])
@cached(ttl=60, key_prefix='es_search', unless=lambda: request.args.get('cache') == 'false')
@rate_limited(limit=60, period=60)
def search(index_name):
    """
    Effectue une recherche dans l'index spécifié.
    
    Requête JSON attendue:
    {
        "query": {
            "match": {
                "field": "value"
            }
        },
        "from": 0,
        "size": 10,
        "sort": [
            {"field1": {"order": "asc"}},
            "_score"
        ],
        "_source": ["field1", "field2"],
        "highlight": {
            "fields": {
                "field1": {}
            }
        }
    }
    """
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({
            'error': 'Invalid request',
            'message': 'Corps de requête JSON requis avec le champ "query"'
        }), 400
    
    try:
        # Extraire les paramètres de recherche
        query = data['query']
        from_ = data.get('from', 0)
        size = data.get('size', 10)
        sort = data.get('sort')
        _source = data.get('_source')
        highlight = data.get('highlight')
        
        # Valider size et from
        if not isinstance(size, int) or size < 0 or size > 1000:
            return jsonify({
                'error': 'Invalid parameter',
                'message': 'Le paramètre "size" doit être un entier entre 0 et 1000'
            }), 400
            
        if not isinstance(from_, int) or from_ < 0:
            return jsonify({
                'error': 'Invalid parameter',
                'message': 'Le paramètre "from" doit être un entier positif'
            }), 400
        
        # Effectuer la recherche
        results = es_client.search(
            index=index_name,
            query=query,
            from_=from_,
            size=size,
            sort=sort,
            _source=_source,
            highlight=highlight
        )
        
        return jsonify(results)
    except ElasticsearchException as e:
        logger.error(f"Erreur lors de la recherche: {e}")
        return jsonify({
            'error': 'Elasticsearch error',
            'message': str(e)
        }), 500


@search_service.route('/<index_name>/_search/text', methods=['GET'])
@cached(ttl=60, key_prefix='es_text_search', unless=lambda: request.args.get('cache') == 'false')
@rate_limited(limit=60, period=60)
def text_search(index_name):
    """
    Effectue une recherche en texte intégral.
    
    Paramètres de requête:
    - q: Texte à rechercher (requis)
    - fields: Champs dans lesquels chercher, séparés par des virgules (optionnel)
    - operator: Opérateur logique ("and" ou "or", défaut: "or")
    - from: Offset pour la pagination (défaut: 0)
    - size: Nombre de résultats à retourner (défaut: 10)
    - highlight: Champs à mettre en surbrillance, séparés par des virgules (optionnel)
    - fuzziness: Niveau de tolérance aux fautes ("AUTO", "0", "1", "2") (optionnel)
    """
    query_text = request.args.get('q')
    if not query_text:
        return jsonify({
            'error': 'Invalid request',
            'message': 'Paramètre de requête "q" requis'
        }), 400
    
    # Extraire les paramètres de recherche
    fields_str = request.args.get('fields')
    fields = fields_str.split(',') if fields_str else None
    
    highlight_str = request.args.get('highlight')
    highlight_fields = highlight_str.split(',') if highlight_str else None
    
    operator = request.args.get('operator', 'or').lower()
    if operator not in ['and', 'or']:
        operator = 'or'
    
    try:
        from_ = int(request.args.get('from', 0))
        size = int(request.args.get('size', 10))
        
        # Valider size et from
        if size < 0 or size > 1000:
            return jsonify({
                'error': 'Invalid parameter',
                'message': 'Le paramètre "size" doit être un entier entre 0 et 1000'
            }), 400
            
        if from_ < 0:
            return jsonify({
                'error': 'Invalid parameter',
                'message': 'Le paramètre "from" doit être un entier positif'
            }), 400
    except ValueError:
        return jsonify({
            'error': 'Invalid parameter',
            'message': 'Les paramètres "from" et "size" doivent être des entiers'
        }), 400
    
    fuzziness = request.args.get('fuzziness')
    
    try:
        # Effectuer la recherche
        results = es_client.full_text_search(
            index=index_name,
            query_text=query_text,
            fields=fields,
            operator=operator,
            from_=from_,
            size=size,
            highlight_fields=highlight_fields,
            fuzziness=fuzziness
        )
        
        return jsonify(results)
    except ElasticsearchException as e:
        logger.error(f"Erreur lors de la recherche en texte intégral: {e}")
        return jsonify({
            'error': 'Elasticsearch error',
            'message': str(e)
        }), 500


def register_service(app):
    """
    Enregistre le service de recherche auprès de l'application Flask.
    
    Args:
        app: L'application Flask
    """
    global es_client
    
    # Initialiser le client Elasticsearch
    es_client = ElasticsearchClient()
    
    # Stocker le client dans l'application
    app.extensions['elasticsearch_client'] = es_client
    
    # Enregistrer le blueprint
    app.register_blueprint(search_service)
    
    logger.info("Service de recherche enregistré avec succès")