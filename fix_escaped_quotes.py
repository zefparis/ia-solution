#!/usr/bin/env python3
"""
Script pour corriger les apostrophes échappées dans le fichier dynamo_models.py
"""

# Lire le contenu du fichier
with open('dynamo_models.py', 'r') as f:
    content = f.read()

# Remplacer les apostrophes échappées par des apostrophes simples
content = content.replace("\\'", "'")

# Écrire le résultat dans le fichier
with open('dynamo_models.py', 'w') as f:
    f.write(content)

print("Correction des apostrophes échappées terminée avec succès.")