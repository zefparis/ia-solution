# IA-Solution - Documentation Technique

## Architecture de l'Application

IA-Solution est une application web construite avec une architecture microservices, utilisant les technologies suivantes :

- **Backend** : Flask (Python 3.11)
- **Base de données** : PostgreSQL (migration vers DynamoDB en cours)
- **Cache** : Redis
- **Recherche** : Elasticsearch
- **Messagerie** : RabbitMQ
- **Stockage** : AWS S3
- **Authentification** : AWS Cognito
- **Déploiement** : Docker et Docker Compose
- **Proxy Inverse** : Nginx

## Structure des Fichiers

L'application suit une structure modulaire avec les composants principaux suivants :

### Fichiers Principaux

- `main.py` : Point d'entrée principal de l'application (version SQLAlchemy)
- `main_dynamo.py` : Point d'entrée alternatif utilisant DynamoDB
- `main_microservices.py` : Point d'entrée optimisé pour l'architecture microservices

### Modules de Base de Données

- `models.py` : Modèles SQLAlchemy pour la base de données relationnelle
- `dynamo_models.py` : Modèles pour DynamoDB (en cours d'implémentation)
- `migrate_to_dynamodb.py` : Script de migration des données de PostgreSQL vers DynamoDB

### Blueprints Principaux

- `finance.py` / `finance_blueprint.py` : Fonctionnalités financières
- `business.py` / `business_dynamo.py` : Analyse commerciale et rapports
- `marketing.py` : Marketing et génération de contenu avec IA
- `modules.py` : Système de modules extensibles
- `marketplace.py` : Marketplace d'extensions et d'API
- `process_analysis.py` : Analyse et optimisation des processus d'entreprise
- `predictive_intelligence.py` : Intelligence prédictive et analyses commerciales
- `training.py` : Système de formation et d'apprentissage interactif

### Services et Intégrations

- `auth.py` / `dynamo_auth.py` : Authentification avec AWS Cognito
- `dynamo_s3_service.py` : Service de stockage S3
- `openai_integration.py` : Intégration avec l'API OpenAI
- `aws_textract.py` : Extraction de texte à partir d'images
- `currency_converter.py` : Conversion entre différentes devises
- `email_service.py` : Envoi d'emails via SendGrid
- `unipesa_payment.py` : Intégration de paiement mobile pour la RDC

### Frontend

- `/templates` : Templates HTML (utilisant Jinja2)
- `/static` : Fichiers statiques (CSS, JavaScript, images)

## Fonctionnalités Principales

1. **Assistant IA** : Conversation contextuelle avec l'assistant IA
2. **Analyse Financière** : Tableaux de bord et analyses financières
3. **Gestion Documentaire** : Traitement et analyse de documents avec OCR
4. **Facturation** : Génération de factures et devis
5. **Analyse Business** : Rapports d'analyse SWOT et recommandations
6. **Marketing IA** : Génération de contenu marketing
7. **Marketplace** : Extensions et intégrations tiers
8. **Système de Modules** : Installation de modules métier à la demande
9. **Formation Interactive** : Apprentissage personnalisé
10. **Intelligence Prédictive** : Prévisions commerciales et analyses

## Déploiement

### Prérequis

1. Serveur Linux (Ubuntu recommandé)
2. Docker et Docker Compose installés
3. Clés API nécessaires:
   - AWS (Access Key, Secret Key)
   - AWS Cognito (User Pool, App Client)
   - OpenAI
   - SendGrid (optionnel)
   - Autres services selon les besoins

### Étapes de Déploiement

1. **Préparation du Serveur**

   ```bash
   # Mise à jour du système
   sudo apt update && sudo apt upgrade -y
   
   # Installation de Docker et Docker Compose
   sudo apt install -y docker.io docker-compose
   
   # Démarrage de Docker
   sudo systemctl enable docker
   sudo systemctl start docker
   ```

2. **Configuration des Variables d'Environnement**

   Créez un fichier `.env` à partir du modèle `.env.example` et configurez les variables nécessaires:

   ```bash
   cp .env.example .env
   nano .env  # Éditez le fichier avec vos valeurs
   ```

3. **Lancement de l'Application**

   ```bash
   # Construire et démarrer les containers
   docker-compose up -d
   
   # Vérifier les logs
   docker-compose logs -f app
   ```

4. **Migration de la Base de Données (si nécessaire)**

   Si vous déployez une nouvelle instance, assurez-vous que la base de données est correctement initialisée:

   ```bash
   # Pour PostgreSQL
   docker-compose exec app python init_database.py
   
   # Pour DynamoDB
   docker-compose exec app python init_dynamodb.py
   ```

### Configuration Nginx

Le fichier `nginx/nginx.conf` contient la configuration Nginx pour servir l'application. Assurez-vous que la configuration correspond à votre domaine.

### SSL/TLS

Pour configurer HTTPS, utilisez Let's Encrypt:

```bash
# Installation de Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtention du certificat
sudo certbot --nginx -d votre-domaine.com
```

## Migration vers DynamoDB

La migration de PostgreSQL vers DynamoDB est en cours. Pour effectuer cette migration:

1. Assurez-vous que les variables AWS sont correctement configurées dans `.env`
2. Exécutez le script de migration:
   ```bash
   docker-compose exec app python migrate_to_dynamodb.py
   ```
3. Vérifiez les données migrées
4. Basculez vers l'application DynamoDB:
   ```bash
   # Modifiez docker-compose.yml pour utiliser main_dynamo:app au lieu de main:app
   ```

## Support Multilingue

L'application prend en charge les langues suivantes:
- Français (par défaut)
- Anglais

La configuration linguistique est gérée par le module `language.py`.

## Maintenance

### Sauvegardes

Configurez des sauvegardes régulières:

```bash
# Sauvegarde de la base de données PostgreSQL
docker-compose exec postgres pg_dump -U postgres ia_solution > backup.sql

# Sauvegarde des volumes Docker
docker run --rm -v ia-solution_postgres-data:/volume -v $(pwd):/backup alpine tar -czvf /backup/postgres-data.tar.gz /volume
```

### Mise à Jour de l'Application

```bash
# Arrêter les containers
docker-compose down

# Mettre à jour les fichiers
git pull  # Si vous utilisez Git

# Reconstruire et redémarrer
docker-compose up -d --build
```

## Contact et Support

Pour toute question ou assistance technique, contactez:
- Email: support@ia-solution.com

---

Documentation préparée le 21 avril 2025