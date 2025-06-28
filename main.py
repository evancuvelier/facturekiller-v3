#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Point d'entrée principal pour FactureKiller V3
Compatible Railway, Render, Heroku, etc.
"""

import os
import sys

# Ajouter le chemin de l'application
current_dir = os.path.dirname(os.path.abspath(__file__))
app_path = os.path.join(current_dir, 'app', 'facturekiller_v3')

# Ajouter au PYTHONPATH
if app_path not in sys.path:
    sys.path.insert(0, app_path)

# Changer le répertoire de travail vers l'app
os.chdir(app_path)

# Importer l'application Flask
from main import app

if __name__ == '__main__':
    # Pour Railway et autres plateformes cloud
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 