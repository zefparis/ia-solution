# IA-Solution - Instructions de déploiement

Ce dossier contient tous les fichiers nécessaires pour déployer l'application IA-Solution.

## Prérequis

- Docker et Docker Compose
- Serveur Linux (Ubuntu recommandé)
- Connexion Internet

## Configuration

1. Copiez le fichier `.env.example` en `.env` et complétez les variables d'environnement :
   ```
   cp .env.example .env
   ```

2. Assurez-vous de remplir les informations suivantes dans le fichier `.env` :
   - FLASK_SECRET_KEY (clé secrète pour Flask)
   - POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB (informations de la base de données)
   - OPENAI_API_KEY (clé API OpenAI)
   - AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, etc. (informations AWS)

## Déploiement

Pour déployer l'application avec Docker Compose :

```bash
# Construction et démarrage des conteneurs
docker-compose up -d

# Vérifier les logs
docker-compose logs -f app
```

## Structure des fichiers

- `/templates` : Templates HTML pour le frontend
- `/static` : Fichiers statiques (CSS, JS, images)
- `/services` : Services microservices (API, elasticsearch, etc.)
- `/nginx` : Configuration Nginx

## Accès à l'application

Une fois déployée, l'application sera accessible à l'adresse :

- http://votre-serveur (port 80 par défaut)
- https://votre-serveur (si vous configurez SSL/TLS)

## Contact

En cas de problème ou de question, contactez : support@ia-solution.com
