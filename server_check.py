#!/usr/bin/env python3
"""
Script de vérification de la configuration du serveur pour IA-Solution
Ce script vérifie que toutes les dépendances et configurations nécessaires sont présentes.
"""

import sys
import os
import platform
import subprocess
import importlib
import socket
import json

# Couleurs pour la sortie console
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(message):
    """Affiche un en-tête formaté"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")

def print_result(test_name, status, message=""):
    """Affiche le résultat d'un test"""
    status_color = Colors.GREEN if status else Colors.RED
    status_text = "OK" if status else "ÉCHEC"
    print(f"{test_name.ljust(35)} [{status_color}{status_text}{Colors.ENDC}]")
    if message and not status:
        print(f"  {Colors.YELLOW}→ {message}{Colors.ENDC}")

def check_python_version():
    """Vérifie que la version de Python est au moins 3.8"""
    current_version = platform.python_version()
    is_valid = tuple(map(int, current_version.split('.'))) >= (3, 8)
    print_result(
        "Version Python",
        is_valid,
        f"Version {current_version} détectée, 3.8+ requise"
    )
    return is_valid

def check_required_packages():
    """Vérifie que les packages Python requis sont installés"""
    required_packages = [
        "flask", "gunicorn", "psycopg2", "openai", "redis", 
        "elasticsearch", "pika", "boto3", "pynamodb", "sqlalchemy"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            importlib.import_module(package)
        except ImportError:
            missing_packages.append(package)
    
    is_valid = len(missing_packages) == 0
    message = f"Packages manquants: {', '.join(missing_packages)}" if not is_valid else ""
    print_result("Packages Python requis", is_valid, message)
    return is_valid

def check_environment_variables():
    """Vérifie que les variables d'environnement requises sont définies"""
    required_vars = [
        "FLASK_SECRET_KEY", "DATABASE_URL", "OPENAI_API_KEY",
        "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"
    ]
    
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    is_valid = len(missing_vars) == 0
    message = f"Variables manquantes: {', '.join(missing_vars)}" if not is_valid else ""
    print_result("Variables d'environnement", is_valid, message)
    return is_valid

def check_database_connection():
    """Vérifie la connexion à la base de données"""
    try:
        import psycopg2
        conn_string = os.environ.get("DATABASE_URL")
        if not conn_string:
            print_result("Connexion à la base de données", False, "Variable DATABASE_URL non définie")
            return False
        
        conn = psycopg2.connect(conn_string)
        conn.close()
        print_result("Connexion à la base de données", True)
        return True
    except ImportError:
        print_result("Connexion à la base de données", False, "Module psycopg2 non installé")
        return False
    except Exception as e:
        print_result("Connexion à la base de données", False, str(e))
        return False

def check_aws_credentials():
    """Vérifie les identifiants AWS"""
    try:
        import boto3
        
        # Vérifie si les variables d'environnement sont définies
        aws_key = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
        aws_region = os.environ.get("AWS_REGION")
        
        if not (aws_key and aws_secret and aws_region):
            print_result("Identifiants AWS", False, "Variables d'environnement AWS manquantes")
            return False
        
        # Teste la connexion à S3
        s3 = boto3.client('s3')
        s3.list_buckets()
        
        print_result("Identifiants AWS", True)
        return True
    except ImportError:
        print_result("Identifiants AWS", False, "Module boto3 non installé")
        return False
    except Exception as e:
        print_result("Identifiants AWS", False, str(e))
        return False

def check_ports():
    """Vérifie que les ports requis sont disponibles"""
    required_ports = [5000, 8000]  # Ports Flask et Gunicorn
    
    unavailable_ports = []
    for port in required_ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        if result == 0:  # Port est déjà utilisé
            unavailable_ports.append(port)
        sock.close()
    
    is_valid = len(unavailable_ports) == 0
    message = f"Ports déjà utilisés: {', '.join(map(str, unavailable_ports))}" if not is_valid else ""
    print_result("Ports disponibles", is_valid, message)
    return is_valid

def check_file_permissions():
    """Vérifie les permissions des fichiers et dossiers critiques"""
    required_dirs = ["./templates", "./static", "./uploads"]
    required_files = ["./main.py", "./main_dynamo.py"]
    
    permission_issues = []
    
    # Vérifier les dossiers
    for directory in required_dirs:
        if os.path.exists(directory):
            if not os.access(directory, os.R_OK | os.W_OK | os.X_OK):
                permission_issues.append(f"{directory} (lecture/écriture/exécution requis)")
        else:
            permission_issues.append(f"{directory} (dossier manquant)")
    
    # Vérifier les fichiers
    for file in required_files:
        if os.path.exists(file):
            if not os.access(file, os.R_OK | os.X_OK):
                permission_issues.append(f"{file} (lecture/exécution requis)")
        else:
            permission_issues.append(f"{file} (fichier manquant)")
    
    is_valid = len(permission_issues) == 0
    message = f"Problèmes de permissions: {', '.join(permission_issues)}" if not is_valid else ""
    print_result("Permissions des fichiers", is_valid, message)
    return is_valid

def check_ssl_certificates():
    """Vérifie si des certificats SSL sont présents"""
    cert_path = "/etc/letsencrypt/live"
    cert_files = ["cert.pem", "privkey.pem", "fullchain.pem"]
    
    # Vérifie si le chemin existe
    if not os.path.exists(cert_path):
        print_result("Certificats SSL", False, "Aucun certificat Let's Encrypt trouvé")
        return False
    
    # Liste les domaines avec des certificats
    domains = []
    try:
        domains = [d for d in os.listdir(cert_path) if os.path.isdir(os.path.join(cert_path, d))]
    except:
        print_result("Certificats SSL", False, "Impossible d'accéder au dossier des certificats")
        return False
    
    if not domains:
        print_result("Certificats SSL", False, "Aucun domaine avec certificat trouvé")
        return False
    
    # Vérifie si les fichiers de certificat existent
    domain_path = os.path.join(cert_path, domains[0])
    missing_files = []
    for cert_file in cert_files:
        if not os.path.exists(os.path.join(domain_path, cert_file)):
            missing_files.append(cert_file)
    
    if missing_files:
        print_result("Certificats SSL", False, f"Fichiers manquants pour {domains[0]}: {', '.join(missing_files)}")
        return False
    
    print_result("Certificats SSL", True, f"Certificats trouvés pour: {', '.join(domains)}")
    return True

def generate_report():
    """Génère un rapport détaillé de la configuration du serveur"""
    report = {
        "system": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "hostname": socket.gethostname(),
            "ip_address": socket.gethostbyname(socket.gethostname()),
        },
        "environment": {
            "FLASK_ENV": os.environ.get("FLASK_ENV", "non défini"),
            "FLASK_DEBUG": os.environ.get("FLASK_DEBUG", "non défini"),
            "APP_ENV": os.environ.get("APP_ENV", "non défini"),
            "DATABASE_URL": "***" if os.environ.get("DATABASE_URL") else "non défini",
            "AWS_REGION": os.environ.get("AWS_REGION", "non défini"),
            "AWS_ACCESS_KEY_ID": "***" if os.environ.get("AWS_ACCESS_KEY_ID") else "non défini",
            "AWS_SECRET_ACCESS_KEY": "***" if os.environ.get("AWS_SECRET_ACCESS_KEY") else "non défini",
            "OPENAI_API_KEY": "***" if os.environ.get("OPENAI_API_KEY") else "non défini",
        },
        "installed_packages": []
    }
    
    # Récupérer la liste des packages installés
    try:
        import pkg_resources
        report["installed_packages"] = [
            {"name": pkg.key, "version": pkg.version}
            for pkg in pkg_resources.working_set
        ]
    except:
        report["installed_packages"] = ["Impossible de récupérer la liste des packages"]
    
    # Sauvegarder le rapport
    with open("server_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n{Colors.GREEN}Rapport détaillé généré dans server_report.json{Colors.ENDC}")

def main():
    """Fonction principale exécutant tous les tests"""
    print_header("Vérification de la Configuration du Serveur IA-Solution")
    
    all_tests_passed = True
    
    # Exécution des tests
    all_tests_passed &= check_python_version()
    all_tests_passed &= check_required_packages()
    all_tests_passed &= check_environment_variables()
    all_tests_passed &= check_database_connection()
    all_tests_passed &= check_aws_credentials()
    all_tests_passed &= check_ports()
    all_tests_passed &= check_file_permissions()
    
    # Test optionnel pour SSL
    try:
        check_ssl_certificates()
    except:
        print_result("Certificats SSL", False, "Test ignoré (droits insuffisants)")
    
    # Affichage du résultat final
    print("\n" + "=" * 60)
    if all_tests_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}Toutes les vérifications ont réussi !{Colors.ENDC}")
        print("Le serveur est correctement configuré pour IA-Solution.")
    else:
        print(f"{Colors.RED}{Colors.BOLD}Des problèmes ont été détectés dans la configuration.{Colors.ENDC}")
        print("Veuillez résoudre les problèmes signalés avant de déployer l'application.")
    print("=" * 60 + "\n")
    
    # Génération du rapport détaillé
    generate_report()
    
    return 0 if all_tests_passed else 1

if __name__ == "__main__":
    sys.exit(main())