#!/usr/bin/env python3
"""
Script pour mettre à jour automatiquement toutes les classes Meta
dans le fichier dynamo_models.py afin qu'elles héritent de BaseModel.Meta
"""

import re

# Lire le contenu du fichier
with open('dynamo_models.py', 'r') as f:
    content = f.read()

# Pattern pour trouver toutes les déclarations de classe Meta
pattern = r'class Meta:\s+table_name = \'([^\']+)\'\s+region = AWS_REGION'

# Remplacer par la version qui hérite de BaseModel.Meta
replacement = r'class Meta(BaseModel.Meta):\n        table_name = \'\1\''

# Effectuer le remplacement
new_content = re.sub(pattern, replacement, content)

# Écrire le résultat dans le fichier
with open('dynamo_models.py', 'w') as f:
    f.write(new_content)

print("Mise à jour des classes Meta terminée avec succès.")