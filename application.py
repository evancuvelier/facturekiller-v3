#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Point d'entrée pour AWS Elastic Beanstalk
"""

import os
import sys

# Ajouter le chemin de l'application
current_dir = os.path.dirname(os.path.abspath(__file__))
app_path = os.path.join(current_dir, 'app', 'facturekiller_v3')

# Ajouter au PYTHONPATH
if app_path not in sys.path:
    sys.path.insert(0, app_path)

# Changer le répertoire de travail
os.chdir(app_path)

# Importer l'application Flask
try:
    from main import app
    # AWS Elastic Beanstalk cherche 'application'
    application = app
    
    if __name__ == '__main__':
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)
        
except ImportError as e:
    print(f"Erreur d'import: {e}")
    raise 