#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Point d'entrée principal pour FactureKiller V3
Compatible Railway, Render, Heroku, etc.
"""

import os
import sys
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Import du module principal FactureKiller
try:
    from app.facturekiller_v3.main import app as facturekiller_app
    logger.info("✅ FactureKiller V3 importé avec succès")
except ImportError as e:
    logger.error(f"❌ Erreur import FactureKiller V3: {e}")
    # Créer une app Flask basique en cas d'erreur
    facturekiller_app = Flask(__name__)
    CORS(facturekiller_app)

# Route de test pour diagnostiquer les variables d'environnement
@facturekiller_app.route('/api/debug/env', methods=['GET'])
def debug_env():
    """Route de debug pour vérifier les variables d'environnement"""
    try:
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        anthropic_alt = os.getenv('ANTHROPIC_KEY')
        
        # Ne pas exposer la vraie clé, juste le statut
        result = {
            'ANTHROPIC_API_KEY_exists': anthropic_key is not None,
            'ANTHROPIC_API_KEY_length': len(anthropic_key) if anthropic_key else 0,
            'ANTHROPIC_API_KEY_starts_with': anthropic_key[:10] if anthropic_key else None,
            'ANTHROPIC_KEY_alternative': anthropic_alt is not None,
            'timestamp': datetime.now().isoformat(),
            'environment_vars': list(os.environ.keys())[:10]  # Premiers 10 pour debug
        }
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Route de test Claude Vision
@facturekiller_app.route('/api/debug/claude', methods=['GET'])
def debug_claude():
    """Route de debug pour tester Claude Vision"""
    try:
        from app.facturekiller_v3.modules.claude_vision import ClaudeVision
        
        claude = ClaudeVision()
        
        result = {
            'claude_client_exists': claude.client is not None,
            'claude_model': claude.model,
            'timestamp': datetime.now().isoformat()
        }
        
        # Test basique de connexion
        if claude.client:
            try:
                test_result = claude.test_api_connection()
                result['api_connection_test'] = test_result
            except Exception as e:
                result['api_connection_error'] = str(e)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500

# Utiliser l'app FactureKiller
app = facturekiller_app

if __name__ == '__main__':
    # Pour Railway et autres plateformes cloud
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Démarrage sur le port {port}")
    app.run(host='0.0.0.0', port=port, debug=False) 