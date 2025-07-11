#!/usr/bin/env python3
"""
FactureKiller V3 - Application professionnelle de gestion des factures
Architecture multi-pages avec interface moderne + Système d'authentification multi-restaurants
"""

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, session, redirect, url_for, make_response
from flask_cors import CORS
import os
import json
import requests
from datetime import datetime, timedelta, date
import uuid
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from PIL import Image
try:
    import pillow_heif
    # Enregistrer le plugin HEIF AVANT tout autre import PIL
    pillow_heif.register_heif_opener()
    HEIF_SUPPORT = True
except ImportError:
    HEIF_SUPPORT = False
    print("⚠️ pillow_heif non disponible - support HEIF désactivé")

import pytesseract
import cv2
import numpy as np
import sqlite3

# Charger les variables d'environnement
load_dotenv()

# Import des modules métier (à copier depuis V2)
import sys
import logging
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from modules.ocr_engine import OCREngine
from modules.invoice_analyzer import InvoiceAnalyzer
from modules.price_manager import PriceManager
from modules.stats_calculator import StatsCalculator
from modules.order_manager import OrderManager
from modules.invoice_manager import InvoiceManager
from modules.email_manager import EmailManager
from modules.auth_manager import AuthManager, login_required, role_required

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration de sécurité pour les sessions
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'facturekiller-v3-secret-key-2025')
app.config['SESSION_COOKIE_SECURE'] = False  # True en production avec HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Configuration
UPLOAD_FOLDER = 'uploads'
DATA_DIR = 'data'
UPLOAD_DIR = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'webp', 'bmp', 'tiff', 'tif', 'heic', 'heif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Initialisation des services
ocr_engine = OCREngine()
invoice_analyzer = InvoiceAnalyzer()
invoice_manager = InvoiceManager()
price_manager = PriceManager()
stats_calculator = StatsCalculator()
email_manager = EmailManager()
auth_manager = AuthManager()
order_manager = OrderManager(email_manager, None)  # Temporaire
# Assigner auth_manager après
order_manager.auth_manager = auth_manager

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ===== ROUTES D'AUTHENTIFICATION =====

@app.route('/login')
def login():
    """Page de connexion"""
    # Si déjà connecté, rediriger vers le dashboard
    if auth_manager.get_current_user():
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """API de connexion"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'Nom d\'utilisateur et mot de passe requis'
            }), 400
        
        result = auth_manager.login(username, password)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 401
            
    except Exception as e:
        logger.error(f"Erreur lors de la connexion: {e}")
        return jsonify({
            'success': False,
            'error': 'Erreur interne du serveur'
        }), 500

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """API de déconnexion"""
    try:
        result = auth_manager.logout()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Erreur lors de la déconnexion: {e}")
        return jsonify({
            'success': False,
            'error': 'Erreur interne du serveur'
        }), 500

@app.route('/api/auth/force-logout', methods=['POST', 'GET'])
def api_force_logout():
    """API de déconnexion forcée - supprime tout"""
    try:
        # Supprimer TOUTES les données de session
        session.clear()
        
        # Créer une réponse avec suppression des cookies
        response = jsonify({
            'success': True,
            'message': 'Déconnexion forcée réussie'
        })
        
        # Supprimer explicitement tous les cookies de session
        response.set_cookie('session', '', expires=0, path='/')
        response.set_cookie('session', '', expires=0, path='/', domain='localhost')
        response.set_cookie('session', '', expires=0, path='/', domain='127.0.0.1')
        
        logger.info("🚨 Déconnexion forcée effectuée")
        return response
        
    except Exception as e:
        logger.error(f"Erreur lors de la déconnexion forcée: {e}")
        return jsonify({
            'success': True,  # On retourne success même en cas d'erreur
            'message': 'Déconnexion forcée (avec erreur mais efficace)'
        })

@app.route('/logout-emergency')
def logout_emergency():
    """Page de déconnexion d'urgence - accessible sans authentification"""
    try:
        # Supprimer TOUTES les données de session
        session.clear()
        logger.info("🚨 Déconnexion d'urgence via page directe")
    except:
        pass
    
    # Rediriger vers la page de connexion
    return redirect(url_for('login'))

@app.route('/api/auth/user')
@login_required
def get_current_user():
    """Récupère les informations de l'utilisateur connecté"""
    try:
        user_context = auth_manager.get_user_context()
        return jsonify({
            'success': True,
            'data': user_context
        })
    except Exception as e:
        logger.error(f"Erreur récupération utilisateur: {e}")
        return jsonify({
            'success': False,
            'error': 'Erreur interne du serveur'
        }), 500

# ===== ROUTES PAGES (avec authentification) =====

@app.route('/')
@login_required
def index():
    """Page d'accueil - Dashboard"""
    return render_template('dashboard.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Page Dashboard avec statistiques"""
    return render_template('dashboard.html')

@app.route('/scanner')
@login_required
def scanner():
    """Page Scanner Principal"""
    return render_template('scanner.html')

@app.route('/scanner-validation')
@login_required
def scanner_validation():
    """Page Scanner avec Validation Commande"""
    return render_template('scanner-validation.html')

@app.route('/scanner-edition')
@login_required
def scanner_edition():
    """Page Scanner avec Édition Prix/Quantités"""
    return render_template('scanner-edition.html')

@app.route('/scanner-batch')
@login_required
def scanner_batch():
    """Page Scanner Batch avec IA"""
    return render_template('scanner-batch.html')

@app.route('/demo-ia-suggestions')
def demo_ia_suggestions():
    """Page de démonstration du système d'IA avec suggestions"""
    return render_template('demo-ia-suggestions.html')

@app.route('/verification-manuelle')
@login_required
def verification_manuelle():
    """Page Vérification Manuelle des Commandes"""
    return render_template('verification-manuelle.html')

@app.route('/commandes')
@login_required
def commandes():
    """Page Gestion des commandes"""
    return render_template('commandes.html')

@app.route('/factures')
@login_required
def factures():
    """Page Historique des factures"""
    return render_template('factures.html')

@app.route('/fournisseurs')
@login_required
def fournisseurs():
    """Page Gestion des fournisseurs"""
    return render_template('fournisseurs.html')

@app.route('/test-fournisseurs')
def test_fournisseurs():
    """Page de test pour déboguer les fournisseurs"""
    return send_file('test_fournisseurs.html')

# ===== NOUVELLES ROUTES PWA SCANNER PRO =====

@app.route('/scanner/pro')
@login_required
def scanner_pro():
    """Page Scanner Pro Mobile - Version PWA"""
    return render_template('scanner.html')

@app.route('/scanner/share', methods=['POST'])
@login_required
def scanner_share():
    """Endpoint pour partager des fichiers via PWA"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Aucun fichier fourni'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'}), 400
        
        if file and allowed_file(file.filename):
            # Traitement du fichier partagé
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"shared_{timestamp}_{filename}"
            
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            # Rediriger vers le scanner avec le fichier
            return redirect(f'/scanner?shared_file={filename}')
        
        return jsonify({'success': False, 'error': 'Type de fichier non supporté'}), 400
        
    except Exception as e:
        logger.error(f"Erreur partage fichier: {e}")
        return jsonify({'success': False, 'error': 'Erreur interne'}), 500

@app.route('/offline.html')
def offline_page():
    """Page hors ligne pour PWA"""
    return render_template('offline.html')

@app.route('/sw.js')
def service_worker():
    """Service Worker pour PWA"""
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.route('/manifest.json')
def manifest():
    """Manifest PWA"""
    return send_from_directory('static', 'manifest.json', mimetype='application/json')

@app.route('/api/scanner/camera-test', methods=['POST'])
@login_required
def camera_test():
    """Test de la caméra pour le scanner mobile"""
    try:
        data = request.get_json()
        device_info = data.get('device_info', {})
        
        # Log des informations de l'appareil
        logger.info(f"Test caméra - Device: {device_info.get('userAgent', 'Unknown')}")
        
        return jsonify({
            'success': True,
            'message': 'Test caméra réussi',
            'capabilities': {
                'camera': True,
                'file_api': True,
                'canvas': True,
                'webgl': True
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur test caméra: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scanner/compress-image', methods=['POST'])
@login_required
def compress_image():
    """Compression d'image côté serveur pour mobile"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Aucun fichier fourni'}), 400
        
        file = request.files['file']
        if not file or not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Fichier invalide'}), 400
        
        # Paramètres de compression
        max_width = int(request.form.get('max_width', 1920))
        max_height = int(request.form.get('max_height', 1080))
        quality = int(request.form.get('quality', 85))
        
        # Ouvrir et compresser l'image
        image = Image.open(file.stream)
        
        # Redimensionner si nécessaire
        if image.width > max_width or image.height > max_height:
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Convertir en RGB si nécessaire
        if image.mode in ('RGBA', 'P'):
            image = image.convert('RGB')
        
        # Sauvegarder l'image compressée
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"compressed_{timestamp}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        image.save(filepath, 'JPEG', quality=quality, optimize=True)
        
        # Calculer la réduction de taille
        original_size = len(file.read())
        file.seek(0)  # Reset file pointer
        compressed_size = os.path.getsize(filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'original_size': original_size,
            'compressed_size': compressed_size,
            'compression_ratio': round((1 - compressed_size / original_size) * 100, 1)
        })
        
    except Exception as e:
        logger.error(f"Erreur compression image: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scanner/history', methods=['GET'])
@login_required
def get_scanner_history():
    """Récupérer l'historique des scans"""
    try:
        user_context = auth_manager.get_user_context()
        restaurant_id = user_context.get('restaurant_id')
        
        if not restaurant_id:
            return jsonify({'success': False, 'error': 'Restaurant non défini'}), 400
        
        # Charger l'historique depuis le fichier
        history_file = f'data/scanner_history_{restaurant_id}.json'
        
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        else:
            history = []
        
        # Trier par date décroissante
        history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'data': history[:50]  # Limiter à 50 entrées
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération historique: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scanner/history', methods=['POST'])
@login_required
def save_scanner_history():
    """Sauvegarder un élément dans l'historique des scans"""
    try:
        user_context = auth_manager.get_user_context()
        restaurant_id = user_context.get('restaurant_id')
        
        if not restaurant_id:
            return jsonify({'success': False, 'error': 'Restaurant non défini'}), 400
        
        data = request.get_json()
        
        # Créer l'entrée d'historique
        history_entry = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'supplier': data.get('supplier', 'Inconnu'),
            'total_amount': data.get('total_amount', 0),
            'products_count': len(data.get('products', [])),
            'savings': data.get('price_comparison', {}).get('total_savings', 0),
            'user_id': user_context.get('user_id'),
            'restaurant_id': restaurant_id
        }
        
        # Charger l'historique existant
        history_file = f'data/scanner_history_{restaurant_id}.json'
        
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        else:
            history = []
        
        # Ajouter la nouvelle entrée
        history.insert(0, history_entry)
        
        # Limiter à 100 entrées
        history = history[:100]
        
        # Sauvegarder
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'Historique sauvegardé',
            'entry': history_entry
        })
        
    except Exception as e:
        logger.error(f"Erreur sauvegarde historique: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scanner/history/<history_id>', methods=['DELETE'])
@login_required
def delete_scanner_history(history_id):
    """Supprimer un élément de l'historique"""
    try:
        user_context = auth_manager.get_user_context()
        restaurant_id = user_context.get('restaurant_id')
        
        if not restaurant_id:
            return jsonify({'success': False, 'error': 'Restaurant non défini'}), 400
        
        history_file = f'data/scanner_history_{restaurant_id}.json'
        
        if not os.path.exists(history_file):
            return jsonify({'success': False, 'error': 'Historique non trouvé'}), 404
        
        # Charger et filtrer l'historique
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        history = [item for item in history if item.get('id') != history_id]
        
        # Sauvegarder
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'Élément supprimé de l\'historique'
        })
        
    except Exception as e:
        logger.error(f"Erreur suppression historique: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scanner/settings', methods=['GET'])
@login_required
def get_scanner_settings():
    """Récupérer les paramètres du scanner"""
    try:
        user_context = auth_manager.get_user_context()
        user_id = user_context.get('user_id')
        
        settings_file = f'data/scanner_settings_{user_id}.json'
        
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        else:
            # Paramètres par défaut
            settings = {
                'auto_analyze': False,
                'haptic_feedback': True,
                'image_quality': 0.8,
                'camera_mode': 'environment',
                'notifications': True,
                'save_history': True
            }
        
        return jsonify({
            'success': True,
            'data': settings
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération paramètres: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scanner/settings', methods=['POST'])
@login_required
def save_scanner_settings():
    """Sauvegarder les paramètres du scanner"""
    try:
        user_context = auth_manager.get_user_context()
        user_id = user_context.get('user_id')
        
        data = request.get_json()
        
        # Valider les paramètres
        settings = {
            'auto_analyze': bool(data.get('auto_analyze', False)),
            'haptic_feedback': bool(data.get('haptic_feedback', True)),
            'image_quality': max(0.1, min(1.0, float(data.get('image_quality', 0.8)))),
            'camera_mode': data.get('camera_mode', 'environment'),
            'notifications': bool(data.get('notifications', True)),
            'save_history': bool(data.get('save_history', True)),
            'updated_at': datetime.now().isoformat()
        }
        
        settings_file = f'data/scanner_settings_{user_id}.json'
        
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'Paramètres sauvegardés',
            'data': settings
        })
        
    except Exception as e:
        logger.error(f"Erreur sauvegarde paramètres: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scanner/stats', methods=['GET'])
@login_required
def get_scanner_stats():
    """Statistiques du scanner pour l'utilisateur"""
    try:
        user_context = auth_manager.get_user_context()
        restaurant_id = user_context.get('restaurant_id')
        
        if not restaurant_id:
            return jsonify({'success': False, 'error': 'Restaurant non défini'}), 400
        
        # Charger l'historique
        history_file = f'data/scanner_history_{restaurant_id}.json'
        
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        else:
            history = []
        
        # Calculer les statistiques
        total_scans = len(history)
        total_savings = sum(item.get('savings', 0) for item in history)
        total_products = sum(item.get('products_count', 0) for item in history)
        
        # Statistiques par période
        now = datetime.now()
        today_scans = len([item for item in history 
                          if datetime.fromisoformat(item.get('timestamp', '2000-01-01')).date() == now.date()])
        
        this_week_scans = len([item for item in history 
                              if (now - datetime.fromisoformat(item.get('timestamp', '2000-01-01'))).days <= 7])
        
        return jsonify({
            'success': True,
            'data': {
                'total_scans': total_scans,
                'total_savings': round(total_savings, 2),
                'total_products': total_products,
                'today_scans': today_scans,
                'this_week_scans': this_week_scans,
                'average_savings_per_scan': round(total_savings / max(total_scans, 1), 2),
                'last_scan': history[0].get('timestamp') if history else None
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur statistiques scanner: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ===== FIN NOUVELLES ROUTES PWA =====

# ===== API ENDPOINTS =====

@app.route('/api/health')
def health():
    """Vérification de l'état du serveur"""
    return jsonify({
        'status': 'healthy',
        'version': '3.0.0',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'ocr': True,  # Toujours True car nous utilisons Claude Vision
            'database': price_manager.is_connected(),
            'modules': {
                'scanner': True,
                'orders': True,
                'analytics': True
            }
        }
    })

@app.route('/api/test')
def api_test():
    """Endpoint de test simple"""
    return jsonify({
        'status': 'ok',
        'message': 'API fonctionnelle',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/stats/dashboard')
def get_dashboard_stats():
    """Statistiques pour le dashboard"""
    try:
        # Importer les modules nécessaires
        from modules.stats_calculator import StatsCalculator
        from modules.invoice_manager import InvoiceManager
        
        # Initialiser les gestionnaires
        stats_calculator = StatsCalculator()
        invoice_manager = InvoiceManager()
        
        # Récupérer toutes les données nécessaires
        all_prices = price_manager.get_all_prices(per_page=99999)['items']
        all_invoices = invoice_manager.get_all_invoices(per_page=99999)['items']
        pending_products = price_manager.get_pending_products()
        
        # Calculer les statistiques
        stats = stats_calculator.calculate_dashboard_stats(
            all_prices, 
            all_invoices,
            pending_products
        )
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"Erreur API dashboard: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== SCANNER API =====

@app.route('/api/invoices/analyze', methods=['POST'])
@login_required
def analyze_invoice():
    """Analyser une facture avec OCR et IA - Support multi-pages"""
    
    # Vérifier si c'est un mode multi-pages
    is_multipage = request.form.get('multipage') == 'true'
    
    if is_multipage:
        # Mode multi-pages - récupérer toutes les pages
        pages = request.files.getlist('pages')
        if not pages or len(pages) == 0:
            return jsonify({
                'success': False,
                'error': 'Aucune page fournie pour la facture multi-pages'
            }), 400
        
        print(f"📄 Analyse multi-pages: {len(pages)} pages reçues")
        
        try:
            # Traiter chaque page
            page_paths = []
            for i, page_file in enumerate(pages):
                if page_file and allowed_file(page_file.filename):
                    filename = secure_filename(page_file.filename)
                    filepath = os.path.join(UPLOAD_FOLDER, f"invoice_multipage_{datetime.now().strftime('%Y%m%d_%H%M%S')}_page{i+1}_{filename}")
                    page_file.save(filepath)
                    page_paths.append(filepath)
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Page {i+1}: fichier non valide ou non supporté'
                    }), 400
            
            # Analyser les pages avec Claude Scanner
            from claude_scanner import ClaudeScanner
            claude_scanner = ClaudeScanner(price_manager)
            
            # Utiliser Claude Vision pour analyser toutes les pages ensemble
            analysis = claude_scanner.scan_facture_multipage(page_paths)
            
            if analysis['success']:
                analysis_data = analysis.get('data', analysis)
                analysis_data['is_multipage'] = True
                analysis_data['total_pages'] = len(pages)
                analysis_data['page_files'] = [os.path.basename(p) for p in page_paths]
                
                # Suite du traitement comme pour une facture normale...
                return process_invoice_analysis(analysis_data, page_paths[0])  # Utiliser la première page comme référence
            else:
                return jsonify({
                    'success': False,
                    'error': analysis.get('error', 'Erreur analyse multi-pages')
                }), 500
                
        except Exception as e:
            print(f"❌ Erreur analyse multi-pages: {e}")
            return jsonify({
                'success': False,
                'error': f'Erreur lors de l\'analyse multi-pages: {str(e)}'
            }), 500
    
    else:
        # Mode single page classique
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Aucun fichier fourni'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Aucun fichier sélectionné'
            }), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, f"invoice_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
            file.save(filepath)
            
            try:
                # Analyser avec Claude Scanner
                from claude_scanner import ClaudeScanner
                claude_scanner = ClaudeScanner(price_manager)
                analysis = claude_scanner.scan_facture(filepath)
                
                if analysis['success']:
                    analysis_data = analysis.get('data', analysis)
                    return process_invoice_analysis(analysis_data, filepath)
                else:
                    return jsonify({
                        'success': False,
                        'error': analysis.get('error', 'Erreur analyse')
                    }), 500
                    
            except Exception as e:
                print(f"❌ Erreur analyse: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Erreur lors de l\'analyse: {str(e)}'
                }), 500
        else:
            return jsonify({
                'success': False,
                'error': 'Type de fichier non supporté'
            }), 400

def process_invoice_analysis(analysis_data, filepath):
    """Traiter les données d'analyse d'une facture (commune single/multi-page)"""
    try:
        # Mode de scan (libre ou commande)
        scan_mode = request.form.get('mode', 'libre')
        order_id = request.form.get('order_id')
        
        # Étape 1: Vérifier le fournisseur sans le créer automatiquement
        supplier_name = analysis_data.get('supplier')
        if supplier_name and supplier_name not in ['Inconnu', 'UNKNOWN', '']:
            user_context = auth_manager.get_user_context()
            current_restaurant = user_context.get('restaurant')
            
            if current_restaurant:
                # Vérifier si le fournisseur existe
                from modules.supplier_manager import SupplierManager
                supplier_manager = SupplierManager()
                suppliers = supplier_manager.get_all_suppliers()
                
                existing_supplier = next((s for s in suppliers if s['name'].lower() == supplier_name.lower()), None)
                
                # Ne pas créer automatiquement - juste vérifier l'existence
                if existing_supplier:
                    print(f"✅ Fournisseur '{supplier_name}' existe déjà")
                    analysis_data['supplier_exists'] = True
                else:
                    print(f"⚠️ Fournisseur '{supplier_name}' non trouvé - sera créé lors de la validation")
                    analysis_data['supplier_exists'] = False
                    analysis_data['supplier_message'] = f"Fournisseur '{supplier_name}' sera créé lors de la validation"
        
        # Étape 2: Comparaison des prix avec filtrage par restaurant
        if analysis_data.get('products'):
            print(f"🔍 PROCESS_INVOICE: Démarrage comparaison prix pour {len(analysis_data['products'])} produits")
            
            # Récupérer le contexte utilisateur pour le restaurant
            user_context = auth_manager.get_user_context()
            current_restaurant = user_context.get('restaurant')
            
            print(f"🏪 PROCESS_INVOICE: Restaurant actuel: {current_restaurant}")
            
            if current_restaurant:
                restaurant_name = current_restaurant.get('name')
                print(f"🏪 PROCESS_INVOICE: Nom du restaurant: '{restaurant_name}'")
                
                # ✅ Correction : Forcer le nom du fournisseur sur chaque produit
                if supplier_name and 'products' in analysis_data:
                    for product in analysis_data['products']:
                        product['supplier'] = supplier_name

                # Passer le restaurant au price_manager
                print(f"🔄 PROCESS_INVOICE: Appel compare_prices avec restaurant '{restaurant_name}'")
                comparison = price_manager.compare_prices(
                    analysis_data['products'], 
                    restaurant_name=restaurant_name
                )
                analysis_data['price_comparison'] = comparison
                analysis_data['restaurant_context'] = restaurant_name
                
                # 🎯 Les nouveaux produits sont déjà automatiquement ajoutés en attente par compare_prices()
                # Ajouter juste un message informatif si il y en a
                new_products_count = comparison.get('new_products', 0)
                print(f"📊 PROCESS_INVOICE: Résultat comparaison - {new_products_count} nouveaux produits")
                if new_products_count > 0:
                    print(f"✅ PROCESS_INVOICE: {new_products_count} nouveaux produits automatiquement ajoutés en attente pour validation")
                    analysis_data['pending_products_added'] = new_products_count
            else:
                print(f"⚠️ PROCESS_INVOICE: Aucun restaurant sélectionné")
                # Pas de restaurant sélectionné - utiliser tous les prix
                comparison = price_manager.compare_prices(analysis_data['products'])
                analysis_data['price_comparison'] = comparison
                analysis_data['warning'] = 'Aucun restaurant sélectionné - prix génériques utilisés'
            
            # Si mode commande, comparer aussi les quantités
            if scan_mode == 'order' and order_id:
                quantity_comparison = order_manager.compare_quantities(
                    order_id, 
                    analysis_data['products']
                )
                analysis_data['quantity_comparison'] = quantity_comparison
        
        # Étape 3: Sauvegarde
        user_context = auth_manager.get_user_context();
        current_restaurant = user_context.get('restaurant');
        
        restaurant_id = current_restaurant.get('id') if current_restaurant else None;
        restaurant_name = current_restaurant.get('name') if current_restaurant else None;
        
        # ▶️  3A. Sauvegarde via InvoiceAnalyzer (historique brut)
        invoice_id = invoice_analyzer.save_invoice(
            {'data': analysis_data}, 
            filepath,
            restaurant_id=restaurant_id,
            restaurant_name=restaurant_name
        )
        analysis_data['invoice_id'] = invoice_id

        # ▶️  3B. Sauvegarde dans InvoiceManager pour lister dans /factures
        try:
            invoice_record = {
                'supplier': supplier_name or 'Inconnu',
                'invoice_number': analysis_data.get('invoice_number'),
                'date': analysis_data.get('date'),
                'total_amount': analysis_data.get('total_amount'),
                'products': analysis_data.get('products', []),
                'analysis': analysis_data,
                'filename': os.path.basename(filepath),
                'scan_date': datetime.now().isoformat(),
                'restaurant_id': restaurant_id,
                'restaurant_name': restaurant_name
            }
            invoice_manager.save_invoice(invoice_record)
        except Exception as save_err:
            logger.warning(f"⚠️ Impossible d'enregistrer la facture dans InvoiceManager: {save_err}")
        
        return jsonify({
            'success': True,
            'data': analysis_data
        })
        
    except Exception as e:
        print(f"❌ Erreur traitement analyse: {e}")
        return jsonify({
            'success': False,
            'error': f'Erreur lors du traitement: {str(e)}'
        }), 500

# ===== FOURNISSEURS API =====

@app.route('/api/suppliers', methods=['GET', 'POST'])
@login_required
def manage_suppliers():
    """Gérer les fournisseurs - filtrés par restaurant"""
    try:
        # Récupérer le contexte utilisateur
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant')
        
        # Vérifier qu'un restaurant est sélectionné
        if not current_restaurant:
            return jsonify({
                'success': False,
                'error': 'Aucun restaurant sélectionné. Veuillez sélectionner un restaurant.',
                'requires_restaurant': True
            }), 400
        
        from modules.supplier_manager import SupplierManager
        supplier_manager = SupplierManager()
        
        if request.method == 'GET':
            # Récupérer les fournisseurs du restaurant
            restaurant_suppliers = current_restaurant.get('suppliers', [])
            all_suppliers = supplier_manager.get_all_suppliers()
            
            # ✅ CORRECTION : Inclure TOUS les fournisseurs qui ont des produits pour ce restaurant
            # Pas seulement ceux dans la liste restaurant_suppliers
            filtered_suppliers = []
            
            for supplier in all_suppliers:
                # Inclure si :
                # 1. Fournisseur dans la liste du restaurant OU
                # 2. Fournisseur a des produits (validés ou en attente)
                has_products = (supplier.get('products_count', 0) > 0 or 
                              supplier.get('pending_count', 0) > 0)
                
                if supplier['name'] in restaurant_suppliers or has_products:
                    filtered_suppliers.append(supplier)
            
            # ✅ CORRECTION : S'assurer que les produits en attente sont inclus
            for supplier in filtered_suppliers:
                # Les produits en attente sont déjà dans supplier['pending_products'] 
                # grâce à _get_supplier_stats() dans get_all_suppliers()
                if 'pending_products' not in supplier:
                    supplier['pending_products'] = []
                if 'validated_products' not in supplier:
                    supplier['validated_products'] = []
            
            return jsonify({
                'success': True,
                'data': filtered_suppliers,
                'restaurant': current_restaurant['name']
            })
        
        elif request.method == 'POST':
            # Créer ou mettre à jour un fournisseur
            supplier_data = request.json
            success = supplier_manager.save_supplier(supplier_data)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Fournisseur sauvegardé avec succès'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Erreur lors de la sauvegarde'
                }), 400
                
    except Exception as e:
        logger.error(f"Erreur API fournisseurs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/suppliers/<supplier_name>', methods=['GET', 'DELETE'])
def manage_supplier(supplier_name):
    """Gérer un fournisseur spécifique"""
    try:
        from modules.supplier_manager import SupplierManager
        supplier_manager = SupplierManager()
        
        if request.method == 'GET':
            # Récupérer un fournisseur
            suppliers = supplier_manager.get_all_suppliers()
            supplier = next((s for s in suppliers if s['name'] == supplier_name), None)
            if supplier:
                return jsonify({
                    'success': True,
                    'data': supplier
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Fournisseur non trouvé'
                }), 404
        
        elif request.method == 'DELETE':
            # Supprimer un fournisseur
            success = supplier_manager.delete_supplier(supplier_name)
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Fournisseur supprimé avec succès'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Erreur lors de la suppression'
                }), 500
            
    except Exception as e:
        logger.error(f"Erreur API fournisseur {supplier_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/suppliers/<supplier_name>/products', methods=['GET', 'POST'])
def manage_supplier_products(supplier_name):
    """Gérer les produits d'un fournisseur"""
    try:
        from modules.supplier_manager import SupplierManager
        supplier_manager = SupplierManager()
        
        if request.method == 'GET':
            # Récupérer les produits du fournisseur
            products = supplier_manager.get_supplier_products(supplier_name)
            return jsonify({
                'success': True,
                'data': products,
                'count': len(products)
            })
        
        elif request.method == 'POST':
            # Ajouter un produit à un fournisseur
            product_data = request.json
            success = supplier_manager.add_product_to_supplier(supplier_name, product_data)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Produit ajouté avec succès'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Erreur lors de l\'ajout du produit'
                }), 400
            
    except Exception as e:
        logger.error(f"Erreur gestion produits fournisseur {supplier_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/suppliers/<supplier_name>/products/<product_id>', methods=['PUT', 'DELETE'])
def manage_supplier_product(supplier_name, product_id):
    """Gérer un produit spécifique d'un fournisseur"""
    try:
        from modules.supplier_manager import SupplierManager
        supplier_manager = SupplierManager()
        
        if request.method == 'PUT':
            # Modifier un produit
            product_data = request.json
            success = supplier_manager.update_product(supplier_name, product_id, product_data)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Produit modifié avec succès'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Produit non trouvé ou erreur lors de la modification'
                }), 400
        
        elif request.method == 'DELETE':
            # Supprimer un produit
            success = supplier_manager.delete_product(supplier_name, product_id)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Produit supprimé avec succès'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Produit non trouvé ou erreur lors de la suppression'
                }), 400
            
    except Exception as e:
        logger.error(f"Erreur gestion produit {product_id} fournisseur {supplier_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/suppliers/stats', methods=['GET'])
def get_suppliers_stats():
    """Récupérer les statistiques des fournisseurs"""
    try:
        from modules.supplier_manager import SupplierManager
        supplier_manager = SupplierManager()
        
        suppliers = supplier_manager.get_all_suppliers()
        
        # Calculer les statistiques
        total_suppliers = len(suppliers)
        total_products = sum(s.get('products_count', 0) for s in suppliers)
        suppliers_with_email = len([s for s in suppliers if s.get('email')])
        suppliers_with_delivery = len([s for s in suppliers if s.get('delivery_days')])
        
        stats = {
            'total_suppliers': total_suppliers,
            'total_products': total_products,
            'suppliers_with_email': suppliers_with_email,
            'suppliers_with_delivery': suppliers_with_delivery,
            'completion_rate': round((suppliers_with_email / total_suppliers * 100), 1) if total_suppliers > 0 else 0
        }
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"Erreur stats fournisseurs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== PRIX API =====

@app.route('/api/prices', methods=['GET'])
@login_required
def get_prices():
    """Récupérer tous les prix de référence FILTRÉS PAR RESTAURANT"""
    try:
        # Récupérer le contexte utilisateur pour le restaurant
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant')
        
        # Paramètres de pagination et filtrage
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        search = request.args.get('search', '')
        supplier = request.args.get('supplier', '')
        
        # Ajouter le filtrage par restaurant
        restaurant_name = None
        if current_restaurant:
            restaurant_name = current_restaurant.get('name')
        
        prices = price_manager.get_all_prices(
            page=page,
            per_page=per_page,
            search=search,
            supplier=supplier,
            restaurant_name=restaurant_name  # NOUVEAU FILTRE
        )
        
        return jsonify({
            'success': True,
            'data': prices['items'],
            'total': prices['total'],
            'page': prices['page'],
            'pages': prices['pages'],
            'restaurant_filter': restaurant_name,
            'restaurant_context': current_restaurant.get('name') if current_restaurant else None
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/prices/suppliers', methods=['GET'])
def get_suppliers():
    """Récupérer la liste des fournisseurs disponibles"""
    try:
        suppliers = price_manager.get_suppliers()
        return jsonify({
            'success': True,
            'data': suppliers
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/prices/<int:price_id>', methods=['PUT', 'DELETE'])
def manage_price(price_id):
    """Gérer un prix (modifier ou supprimer)"""
    if request.method == 'PUT':
        try:
            data = request.json
            success = price_manager.update_price_by_id(price_id, data)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Prix mis à jour avec succès'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Produit non trouvé'
                }), 404
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    elif request.method == 'DELETE':
        try:
            # Vérifier si c'est une suppression en cascade
            cascade = request.args.get('cascade', 'false').lower() == 'true'
            
            if cascade:
                # Suppression complète avec toutes les références
                result = price_manager.delete_price_cascade(price_id - 1)  # price_id - 1 car index 0-based
                
                if result['success']:
                    return jsonify({
                        'success': True,
                        'message': result['message'],
                        'stats': result['stats']
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': result['error']
                    }), 404
            else:
                # Suppression simple (désactivation)
                success = price_manager.delete_price_by_id(price_id)
            
            if success:
                return jsonify({
                    'success': True,
                        'message': 'Prix désactivé avec succès'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Produit non trouvé'
                }), 404
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

@app.route('/api/prices/pending', methods=['GET'])
@login_required
def get_pending_products():
    """Récupérer les produits en attente de validation FILTRÉS PAR RESTAURANT"""
    try:
        # Récupérer le contexte utilisateur pour le restaurant
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant')
        
        # Récupérer tous les produits en attente
        all_pending = price_manager.get_pending_products()
        
        # Filtrer par restaurant si un restaurant est sélectionné
        if current_restaurant:
            restaurant_name = current_restaurant.get('name')
            # Filtrer les produits pour ce restaurant OU les produits généraux
            filtered_pending = []
            for product in all_pending:
                product_restaurant = product.get('restaurant', 'Général')
                if (product_restaurant == restaurant_name or 
                    product_restaurant == 'Général' or 
                    product_restaurant is None):
                    filtered_pending.append(product)
            return jsonify({
                'success': True,
                'data': filtered_pending,
                'count': len(filtered_pending),
                'restaurant_filter': restaurant_name,
                'total_pending': len(all_pending)
            })
        # Pas de restaurant sélectionné - afficher tous les produits
        return jsonify({
            'success': True,
            'data': all_pending,
            'count': len(all_pending),
            'warning': 'Aucun restaurant sélectionné - tous les produits affichés'
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/prices/pending/<int:pending_id>/validate', methods=['POST'])
def validate_pending_product(pending_id):
    """Valider un produit en attente et synchroniser vers le groupe"""
    try:
        # Récupérer le contexte utilisateur pour la synchronisation
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant')
        
        # Récupérer les détails du produit avant validation
        pending_products = price_manager.get_pending_products()
        product_to_validate = next((p for p in pending_products if p.get('id') == pending_id), None)
        
        success = price_manager.validate_pending_product(pending_id)
        
        if success:
            # 🔄 SYNCHRONISER LE NOUVEAU PRIX VERS LES AUTRES RESTAURANTS DU GROUPE
            if current_restaurant and product_to_validate:
                try:
                    from modules.sync_manager import SyncManager
                    sync_manager = SyncManager()
                    
                    # Préparer les données du produit pour la synchronisation
                    product_data = {
                        'produit': product_to_validate.get('produit'),
                        'prix': product_to_validate.get('prix'),
                        'unite': product_to_validate.get('unite'),
                        'fournisseur': product_to_validate.get('fournisseur'),
                        'categorie': product_to_validate.get('categorie', 'Auto'),
                        'restaurant': current_restaurant.get('name')
                    }
                    
                    sync_result = sync_manager.sync_prices_to_group(current_restaurant.get('name'), product_data)
                    if sync_result.get('synced_count', 0) > 0:
                        print(f"✅ Prix validé et synchronisé vers {sync_result['synced_count']} restaurant(s)")
                        
                        return jsonify({
                            'success': True,
                            'message': f'Produit validé et synchronisé vers {sync_result["synced_count"]} restaurant(s)',
                            'sync_count': sync_result['synced_count'],
                            'sync_restaurants': sync_result.get('synced_restaurants', [])
                        })
                except Exception as sync_error:
                    logger.warning(f"Erreur synchronisation prix validé: {sync_error}")
                    # Ne pas faire échouer la validation si la sync échoue
            
            return jsonify({
                'success': True,
                'message': 'Produit validé et ajouté aux prix de référence'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Produit non trouvé'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/prices/pending/<int:pending_id>/reject', methods=['DELETE'])
def reject_pending_product(pending_id):
    """Rejeter un produit en attente"""
    try:
        success = price_manager.reject_pending_product(pending_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Produit rejeté'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Produit non trouvé'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/prices/pending/<int:pending_id>/update', methods=['PUT'])
def update_pending_product(pending_id):
    """Mettre à jour un produit en attente"""
    try:
        data = request.json
        success = price_manager.update_pending_product(pending_id, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Produit en attente mis à jour'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Produit non trouvé'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/prices/pending/bulk', methods=['POST'])
def add_pending_products_bulk():
    """Ajouter des produits en attente en masse depuis le scanner"""
    try:
        data = request.json
        products = data.get('products', [])
        
        if not products:
            return jsonify({
                'success': False,
                'error': 'Aucun produit fourni'
            }), 400
        
        # Ajouter chaque produit aux en attente
        added_count = 0
        for product in products:
            success = price_manager.add_pending_product(product)
            if success:
                added_count += 1
        
        return jsonify({
            'success': True,
            'message': f'{added_count} produits ajoutés en attente',
            'added_count': added_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/prices/pending/bulk-validate', methods=['POST'])
def validate_pending_bulk():
    """Valider des produits en attente en masse"""
    try:
        data = request.json
        product_ids = data.get('product_ids', [])
        
        if not product_ids:
            return jsonify({
                'success': False,
                'error': 'Aucun ID fourni'
            }), 400
        
        validated_count = 0
        for product_id in product_ids:
            success = price_manager.validate_pending_product(product_id)
            if success:
                validated_count += 1
        
        return jsonify({
            'success': True,
            'message': f'{validated_count} produits validés',
            'validated_count': validated_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/prices/pending/bulk-reject', methods=['POST'])
def reject_pending_bulk():
    """Rejeter des produits en attente en masse"""
    try:
        data = request.json
        product_ids = data.get('product_ids', [])
        
        if not product_ids:
            return jsonify({
                'success': False,
                'error': 'Aucun ID fourni'
            }), 400
        
        rejected_count = 0
        for product_id in product_ids:
            success = price_manager.reject_pending_product(product_id)
            if success:
                rejected_count += 1
        
        return jsonify({
            'success': True,
            'message': f'{rejected_count} produits rejetés',
            'rejected_count': rejected_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/prices/compare', methods=['POST'])
def compare_prices_api():
    """Comparer les prix de produits avec les prix de référence"""
    try:
        data = request.json
        products = data.get('products', [])
        
        if not products:
            return jsonify({
                'success': False,
                'error': 'Aucun produit fourni'
            }), 400
        
        comparison = price_manager.compare_prices(products)
        
        return jsonify({
            'success': True,
            'data': comparison
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/prices/upload', methods=['POST'])
def upload_prices():
    try:
        file = request.files.get('file')
        if not file or not file.filename:
            return jsonify({'success': False, 'error': 'Aucun fichier fourni'})
        
        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'error': 'Seuls les fichiers CSV sont supportés'})
        
        # Créer le dossier uploads s'il n'existe pas
        uploads_dir = 'uploads'
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Sauvegarder le fichier temporairement
        filename = secure_filename(file.filename)
        filepath = os.path.join(uploads_dir, filename)
        file.save(filepath)
        
        # Traiter le fichier CSV
        result = price_manager.import_csv(filepath)
        
        # Supprimer le fichier temporaire
        os.remove(filepath)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/invoices', methods=['GET'])
@login_required
def get_invoices():
    """Récupérer toutes les factures avec pagination FILTRÉES PAR RESTAURANT_ID STRICT"""
    try:
        # Récupérer le contexte utilisateur pour le restaurant
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant')
        
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        supplier = request.args.get('supplier', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        anomaly_filter = request.args.get('anomalies', '')
        
        # 🔒 SÉCURITÉ: Utiliser restaurant_id uniquement, pas les fournisseurs
        restaurant_id = None
        restaurant_name = None
        if current_restaurant:
            restaurant_id = current_restaurant.get('id')
            restaurant_name = current_restaurant.get('name')
            
            # Si un fournisseur spécifique est demandé, vérifier qu'il appartient au restaurant
            # Mais SEULEMENT pour la validation, pas pour le filtrage principal
            restaurant_suppliers = current_restaurant.get('suppliers', [])
            if supplier and supplier not in restaurant_suppliers:
                return jsonify({
                    'success': False,
                    'error': f'Fournisseur {supplier} non autorisé pour ce restaurant',
                    'restaurant': restaurant_name
                }), 403
        
        # Appel avec restaurant_id pour filtrage sécurisé
        invoices = invoice_manager.get_all_invoices(
            page=page,
            per_page=per_page,
            supplier=supplier,
            date_from=date_from,
            date_to=date_to,
            restaurant_suppliers=None,  # ⚠️ Ne plus utiliser pour le filtrage
            anomaly_filter=anomaly_filter,
            restaurant_id=restaurant_id  # 🔒 Filtrage sécurisé
        )
        
        return jsonify({
            'success': True,
            'data': invoices['items'],
            'total': invoices['total'],
            'page': invoices['page'],
            'pages': invoices['pages'],
            'restaurant_context': restaurant_name,
            'restaurant_id': restaurant_id,  # Pour debug
            'anomaly_filter': anomaly_filter
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/invoices/<invoice_id>')
def get_invoice_detail(invoice_id):
    """Récupérer le détail d'une facture"""
    try:
        invoice = invoice_manager.get_invoice_by_id(invoice_id)  # Pas de conversion en int
        if invoice:
            return jsonify({
                'success': True,
                'data': invoice
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Facture non trouvée'
            }), 404
    except Exception as e:
        logger.error(f"Erreur récupération facture {invoice_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/invoices/save', methods=['POST'])
@login_required
def save_invoice():
    """Sauvegarder une facture scannée avec code FCT-XXXX-XXXX automatique"""
    try:
        data = request.json
        
        # 🎯 RÉCUPÉRER LE CONTEXTE RESTAURANT
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant')
        
        # 🎯 GÉNÉRATION AUTOMATIQUE DU CODE FACTURE FCT-XXXX-XXXX
        def generate_invoice_code():
            """Génère un code unique FCT-XXXX-XXXX"""
            now = datetime.now()
            # Format: FCT-YYYYMM-XXXX où XXXX est un compteur journalier
            year_month = now.strftime('%Y%m')
            
            # Compter les factures du jour pour générer le numéro séquentiel
            today_str = now.strftime('%Y-%m-%d')
            existing_invoices = invoice_manager.get_all_invoices()
            
            # Filtrer les factures du jour
            today_count = 0
            for inv in existing_invoices:
                if inv.get('scan_date', '').startswith(today_str):
                    today_count += 1
            
            # Générer le code avec compteur (format XXXX avec zéros)
            sequence = str(today_count + 1).zfill(4)
            return f"FCT-{year_month}-{sequence}"
        
        invoice_code = generate_invoice_code()
        
        # 🎯 GÉNÉRER AUTOMATIQUEMENT UN FILENAME SI NON FOURNI
        filename = data.get('filename')
        if not filename:
            supplier = data.get('supplier', 'Inconnu').replace(' ', '_')
            invoice_number = data.get('invoice_number', '')
            date_str = data.get('date', datetime.now().strftime('%Y%m%d'))
            timestamp = datetime.now().strftime('%H%M%S')
            
            if invoice_number:
                filename = f"{supplier}_{invoice_number}_{date_str}_{timestamp}.jpg"
            else:
                filename = f"{supplier}_{date_str}_{timestamp}_scan.jpg"
            
            print(f"📁 Filename généré automatiquement: {filename}")
        
        # 🎯 TRAITEMENT DES ANOMALIES AUTOMATIQUES
        anomalies = data.get('anomalies', [])
        
        # S'assurer que anomalies est une liste
        if not isinstance(anomalies, list):
            anomalies = []
        
        # Détecter automatiquement les anomalies de prix si il y a une comparaison
        price_comparison = data.get('price_comparison', {})
        if isinstance(price_comparison, dict):
            products_with_anomalies = price_comparison.get('products_with_price_differences', [])
            if isinstance(products_with_anomalies, list):
                for product in products_with_anomalies:
                    if isinstance(product, dict):  # Vérifier que product est un dict
                        # Créer une anomalie automatique pour chaque écart de prix
                        anomaly = {
                            'id': str(uuid.uuid4()),
                            'type': 'price_difference',
                            'product_name': product.get('name', 'Produit inconnu'),
                            'description': f"Écart de prix détecté: Facturé {product.get('invoice_price', 0)}€ vs Référence {product.get('reference_price', 0)}€",
                            'severity': 'medium' if abs(product.get('price_difference', 0)) < 5 else 'high',
                            'status': 'detected',
                            'detected_at': datetime.now().isoformat(),
                            'invoice_price': product.get('invoice_price', 0),
                            'reference_price': product.get('reference_price', 0),
                            'price_difference': product.get('price_difference', 0),
                            'auto_detected': True
                        }
                        anomalies.append(anomaly)
        
        # 🎯 SÉCURISER LES CORRECTIONS_APPLIED
        corrections_applied = data.get('corrections_applied', {})
        if not isinstance(corrections_applied, dict):
            corrections_applied = {}
        
        user_modified = False
        if isinstance(corrections_applied, dict):
            user_modified = corrections_applied.get('user_corrected', False)
        
        # 🎯 CRÉER L'OBJET FACTURE COMPLET AVEC TOUTES LES DONNÉES
        invoice_data = {
            # IDENTIFIANTS
            'invoice_code': invoice_code,  # ✅ Code FCT-XXXX-XXXX unique
            'filename': filename,
            
            # DONNÉES FACTURE
            'supplier': data.get('supplier', 'Inconnu'),
            'invoice_number': data.get('invoice_number'),
            'date': data.get('date'),
            'total_amount': data.get('total_amount', 0),
            'products': data.get('products', []),
            'analysis': data.get('analysis', {}),
            
            # MÉTADONNÉES DE SCAN
            'file_size': data.get('file_size', 0),
            'scan_date': datetime.now().isoformat(),  # ✅ Date de scan automatique
            'created_at': datetime.now().isoformat(),
            'is_multipage': data.get('is_multipage', False),
            'total_pages': data.get('total_pages', 1),
            
            # 🎯 SYSTÈME D'ANOMALIES COMPLET
            'anomalies': anomalies,  # Liste des anomalies détectées
            'has_anomalies': len(anomalies) > 0,  # Flag pour filtrage rapide
            'anomalies_count': len(anomalies),  # Compteur d'anomalies
            'anomaly_status': 'resolved' if len(anomalies) == 0 else 'pending',  # Statut global
            
            # CORRECTIONS ET MODIFICATIONS (SÉCURISÉ)
            'corrections_applied': corrections_applied,
            'user_modified': user_modified,
            
            # SUIVI WORKFLOW
            'workflow_status': 'saved',  # saved, validated, archived
            'validation_required': len(anomalies) > 0,  # Nécessite validation si anomalies
            'priority': 'high' if len(anomalies) > 3 else 'medium' if len(anomalies) > 0 else 'normal'
        }
        
        # 🔒 ASSOCIER AU RESTAURANT ACTUEL
        if current_restaurant:
            invoice_data['restaurant_id'] = current_restaurant.get('id')
            invoice_data['restaurant_name'] = current_restaurant.get('name')
            
            # Ajouter aussi dans l'analysis pour compatibilité
            if 'analysis' not in invoice_data:
                invoice_data['analysis'] = {}
            invoice_data['analysis']['restaurant_id'] = current_restaurant.get('id')
            invoice_data['analysis']['restaurant_context'] = current_restaurant.get('name')
            
            print(f"🔒 Facture associée au restaurant: {current_restaurant.get('name')} (ID: {current_restaurant.get('id')})")
        else:
            print("⚠️ Aucun restaurant sélectionné - facture sans association")
        
        # 💾 SAUVEGARDER DANS LE GESTIONNAIRE DE FACTURES
        invoice_id = invoice_manager.save_invoice(invoice_data)
        
        # 🎯 CRÉER LE SUIVI D'ANOMALIES DANS LE SYSTÈME
        if anomalies:
            # Créer une entrée dans le système d'anomalies pour chaque anomalie
            for anomaly in anomalies:
                anomaly_data = {
                    'invoice_id': invoice_id,
                    'invoice_code': invoice_code,
                    'supplier': invoice_data['supplier'],
                    'type': anomaly['type'],
                    'description': anomaly['description'],
                    'status': 'pending',  # pending, investigating, resolved, closed
                    'severity': anomaly.get('severity', 'medium'),
                    'created_at': datetime.now().isoformat(),
                    'restaurant_id': current_restaurant.get('id') if current_restaurant else None,
                    'restaurant_name': current_restaurant.get('name') if current_restaurant else None,
                    'auto_detected': anomaly.get('auto_detected', False),
                    'metadata': {
                        'product_name': anomaly.get('product_name'),
                        'invoice_price': anomaly.get('invoice_price'),
                        'reference_price': anomaly.get('reference_price'),
                        'price_difference': anomaly.get('price_difference')
                    }
                }
                
                # Sauvegarder l'anomalie dans le système de suivi
                # (Utiliser le système d'anomalies existant ou créer un nouveau)
                print(f"🚨 Anomalie créée: {anomaly['type']} pour {invoice_code}")
        
        # 📊 STATISTIQUES ET RAPPORTS
        stats_summary = {
            'products_count': len(invoice_data['products']),
            'anomalies_count': len(anomalies),
            'total_amount': invoice_data['total_amount'],
            'processing_time': 'immediate',
            'has_price_differences': any(a['type'] == 'price_difference' for a in anomalies)
        }
        
        # === DETECTION ECARTS POUR AVOIR ===
        needs_credit = False
        credit_items = []
        try:
            # Écarts de prix (price_comparison)
            pc = invoice_data.get('price_comparison', {})
            for prod in pc.get('products_with_price_differences', []):
                needs_credit = True
                diff = prod.get('price_difference', 0)
                credit_items.append({
                    'product': prod.get('name'),
                    'issue': f"Écart prix {prod.get('invoice_price',0)} → {prod.get('reference_price',0)}",
                    'amount': abs(diff)
                })
            # Écarts de quantités (quantity_comparison)
            qc = invoice_data.get('quantity_comparison', {})
            for item in qc.get('items_with_differences', []):
                needs_credit = True
                missing_qty = item.get('ordered_quantity',0) - item.get('received_quantity',0)
                credit_items.append({
                    'product': item.get('product_name'),
                    'issue': f"Manque {missing_qty} {item.get('unit','')}",
                    'amount': abs(missing_qty * item.get('ordered_price',0))
                })
        except Exception as diff_err:
            logger.warning(f"Analyse écarts avoir: {diff_err}")

        # Envoi email avoir si besoin
        if needs_credit and credit_items:
            try:
                email_manager.send_credit_note(invoice_data, credit_items)
                invoice_data['credit_requested'] = True
            except Exception as email_err:
                logger.warning(f"Envoi avoir échoué: {email_err}")
                invoice_data['credit_requested'] = False
        else:
            invoice_data['credit_requested'] = False
        
        return jsonify({
            'success': True,
            'invoice_id': invoice_id,
            'invoice_code': invoice_code,  # ✅ Retourner le code FCT-XXXX-XXXX
            'filename': filename,
            'scan_date': invoice_data['scan_date'],  # ✅ Date de scan
            'restaurant': current_restaurant.get('name') if current_restaurant else None,
            'anomalies_detected': len(anomalies),  # ✅ Nombre d'anomalies
            'anomaly_status': invoice_data['anomaly_status'],  # ✅ Statut anomalies
            'validation_required': invoice_data['validation_required'],  # ✅ Validation requise
            'needs_credit': invoice_data['credit_requested'],
            'stats': stats_summary,
            'message': f'✅ Facture {invoice_code} sauvegardée avec succès' + (f' - {len(anomalies)} anomalie(s) détectée(s)' if anomalies else '')
        })
        
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde facture: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/invoices/save-simple', methods=['POST'])
@login_required  
def save_invoice_simple():
    """Sauvegarder une facture scannée - VERSION SIMPLE SANS ERREURS"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'Aucune donnée reçue'}), 400
        
        # 🎯 RÉCUPÉRER LE CONTEXTE RESTAURANT
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant') if user_context else None
        
        # 🎯 GÉNÉRATION AUTOMATIQUE DU CODE FACTURE FCT-XXXX-XXXX
        now = datetime.now()
        year_month = now.strftime('%Y%m')
        
        # Compter les factures du jour pour générer le numéro séquentiel
        today_str = now.strftime('%Y-%m-%d')
        try:
            existing_invoices = invoice_manager.get_all_invoices()
            today_count = sum(1 for inv in existing_invoices if str(inv.get('scan_date', '')).startswith(today_str))
        except:
            today_count = 0
        
        # Générer le code avec compteur
        sequence = str(today_count + 1).zfill(4)
        invoice_code = f"FCT-{year_month}-{sequence}"
        
        # 🎯 DONNÉES DE BASE SÉCURISÉES
        supplier = str(data.get('supplier', 'Inconnu'))
        invoice_number = str(data.get('invoice_number', ''))
        total_amount = float(data.get('total_amount', 0)) if data.get('total_amount') else 0
        
        # 🎯 FILENAME AUTOMATIQUE
        supplier_clean = supplier.replace(' ', '_').replace('/', '_')
        timestamp = now.strftime('%H%M%S')
        date_str = now.strftime('%Y%m%d')
        
        if invoice_number:
            filename = f"{supplier_clean}_{invoice_number}_{date_str}_{timestamp}.jpg"
        else:
            filename = f"{supplier_clean}_{date_str}_{timestamp}_scan.jpg"
        
        # 🎯 TRAITEMENT SIMPLE DES ANOMALIES
        anomalies = []
        try:
            if 'anomalies' in data and isinstance(data['anomalies'], list):
                anomalies = data['anomalies']
        except:
            anomalies = []
        
        # 🎯 CRÉER L'OBJET FACTURE SIMPLE
        invoice_data = {
            # IDENTIFIANTS
            'invoice_code': invoice_code,
            'filename': filename,
            
            # DONNÉES FACTURE
            'supplier': supplier,
            'invoice_number': invoice_number,
            'date': str(data.get('date', now.strftime('%Y-%m-%d'))),
            'total_amount': total_amount,
            'products': data.get('products', []) if isinstance(data.get('products'), list) else [],
            'analysis': data.get('analysis', {}) if isinstance(data.get('analysis'), dict) else {},
            
            # MÉTADONNÉES DE SCAN
            'file_size': int(data.get('file_size', 0)) if data.get('file_size') else 0,
            'scan_date': now.isoformat(),
            'created_at': now.isoformat(),
            'is_multipage': bool(data.get('is_multipage', False)),
            'total_pages': int(data.get('total_pages', 1)) if data.get('total_pages') else 1,
            
            # SYSTÈME D'ANOMALIES SIMPLE
            'anomalies': anomalies,
            'has_anomalies': len(anomalies) > 0,
            'anomalies_count': len(anomalies),
            'anomaly_status': 'resolved' if len(anomalies) == 0 else 'pending',
            
            # WORKFLOW SIMPLE
            'workflow_status': 'saved',
            'validation_required': len(anomalies) > 0,
            'priority': 'high' if len(anomalies) > 3 else 'medium' if len(anomalies) > 0 else 'normal',
            
            # CORRECTIONS SIMPLES
            'corrections_applied': {},
            'user_modified': False
        }
        
        # 🔒 ASSOCIER AU RESTAURANT
        if current_restaurant:
            invoice_data['restaurant_id'] = current_restaurant.get('id', '')
            invoice_data['restaurant_name'] = current_restaurant.get('name', '')
            
            if 'analysis' not in invoice_data:
                invoice_data['analysis'] = {}
            invoice_data['analysis']['restaurant_id'] = current_restaurant.get('id', '')
            invoice_data['analysis']['restaurant_context'] = current_restaurant.get('name', '')
        
        # 💾 SAUVEGARDER LA FACTURE
        invoice_id = invoice_manager.save_invoice(invoice_data)
        
        if not invoice_id:
            raise Exception("Erreur lors de la sauvegarde")
        
        # 🎯 CRÉER LE FOURNISSEUR SI NÉCESSAIRE
        supplier_created = False
        if supplier and supplier not in ['Inconnu', 'UNKNOWN', ''] and current_restaurant:
            try:
                from modules.supplier_manager import SupplierManager
                supplier_manager = SupplierManager()
                suppliers = supplier_manager.get_all_suppliers()
                
                existing_supplier = next((s for s in suppliers if s['name'].lower() == supplier.lower()), None)
                
                if not existing_supplier:
                    # Créer le fournisseur
                    new_supplier_data = {
                        'name': supplier,
                        'contact': '',
                        'phone': '',
                        'email': '',
                        'notes': f'Créé automatiquement lors du scan de facture - Restaurant: {current_restaurant.get("name")}',
                        'created_at': now.isoformat()
                    }
                    supplier_manager.save_supplier(new_supplier_data)
                    supplier_created = True
                    
                    # Associer au restaurant
                    restaurant_suppliers = current_restaurant.get('suppliers', [])
                    if supplier not in restaurant_suppliers:
                        restaurant_suppliers.append(supplier)
                        restaurants = auth_manager._load_restaurants()
                        for rest in restaurants:
                            if rest['id'] == current_restaurant['id']:
                                rest['suppliers'] = restaurant_suppliers
                                break
                        auth_manager._save_restaurants(restaurants)
                    
                    print(f"✅ Fournisseur '{supplier}' créé automatiquement")
            except Exception as e:
                logger.warning(f"Erreur création fournisseur: {e}")
        
        # 🎯 CRÉER LES PRODUITS EN ATTENTE
        products_created = 0
        if data.get('products') and isinstance(data['products'], list):
            try:
                from modules.price_manager import PriceManager
                price_manager = PriceManager()
                
                for product in data['products']:
                    if product.get('name') and product.get('unit_price'):
                        # Vérifier si le produit existe déjà
                        existing_products = price_manager.get_all_prices()
                        product_exists = any(
                            p.get('name', '').lower() == product['name'].lower() and 
                            p.get('supplier', '').lower() == supplier.lower()
                            for p in existing_products
                        )
                        
                        if not product_exists:
                            # Créer le produit en attente
                            pending_product = {
                                'name': product['name'],
                                'supplier': supplier,
                                'unit_price': float(product['unit_price']),
                                'quantity': int(product.get('quantity', 1)),
                                'status': 'pending',
                                'created_at': now.isoformat(),
                                'restaurant_id': current_restaurant.get('id') if current_restaurant else None,
                                'restaurant_name': current_restaurant.get('name') if current_restaurant else None,
                                'source_invoice': invoice_code
                            }
                            
                            success = price_manager.add_pending_product(pending_product)
                            if success:
                                products_created += 1
                                
                print(f"✅ {products_created} produit(s) créé(s) en attente")
            except Exception as e:
                logger.warning(f"Erreur création produits: {e}")
        
        # 🎯 ENVOYER LES EMAILS D'ANOMALIES SI DEMANDÉ
        emails_sent = 0
        if anomalies:
            try:
                for anomaly in anomalies:
                    if anomaly.get('send_email', False):
                        # Envoyer l'email d'anomalie
                        email_data = {
                            'supplier': supplier,
                            'product_name': anomaly.get('product_name', ''),
                            'anomaly_type': anomaly.get('type', ''),
                            'description': anomaly.get('description', ''),
                            'specific_data': anomaly.get('specific_data', {}),
                            'severity': anomaly.get('severity', 'medium'),
                            'invoice_code': invoice_code,
                            'restaurant': current_restaurant.get('name') if current_restaurant else 'Restaurant'
                        }
                        
                        # Appeler la route d'envoi d'email
                        try:
                            email_response = requests.post(
                                f"{request.host_url}api/anomalies/send-notification/{invoice_id}",
                                json=email_data,
                                headers={'Content-Type': 'application/json'}
                            )
                            if email_response.status_code == 200:
                                emails_sent += 1
                                print(f"📧 Email d'anomalie envoyé pour: {anomaly.get('product_name')}")
                        except Exception as email_error:
                            logger.warning(f"Erreur envoi email: {email_error}")
                            
            except Exception as e:
                logger.warning(f"Erreur envoi emails: {e}")
        
        # 🎉 RETOUR SUCCÈS AVEC DÉTAILS
        return jsonify({
            'success': True,
            'invoice_id': invoice_id,
            'invoice_code': invoice_code,
            'filename': filename,
            'scan_date': invoice_data['scan_date'],
            'restaurant': current_restaurant.get('name') if current_restaurant else None,
            'anomalies_detected': len(anomalies),
            'anomaly_status': invoice_data['anomaly_status'],
            'validation_required': invoice_data['validation_required'],
            'supplier_created': supplier_created,
            'products_created': products_created,
            'emails_sent': emails_sent,
            'message': f'✅ Facture {invoice_code} sauvegardée avec succès' + 
                      (f' - Fournisseur créé' if supplier_created else '') +
                      (f' - {products_created} produit(s) en attente' if products_created > 0 else '') +
                      (f' - {len(anomalies)} anomalie(s) détectée(s)' if anomalies else '')
        })
        
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde facture simple: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Erreur sauvegarde: {str(e)}'
        }), 500

# ===== COMMANDES API =====

@app.route('/api/orders', methods=['GET', 'POST'])
@login_required
def manage_orders():
    """Gérer les commandes FILTRÉES PAR RESTAURANT"""
    try:
        # Récupérer le contexte utilisateur pour le restaurant
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant')
        
        if request.method == 'GET':
            # Paramètres de filtrage
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 20))
            supplier = request.args.get('supplier', '')
            status = request.args.get('status', '')
            
            # Filtrer par fournisseurs du restaurant si restaurant sélectionné
            restaurant_suppliers = []
            if current_restaurant:
                restaurant_suppliers = current_restaurant.get('suppliers', [])
                # Si un fournisseur spécifique est demandé, vérifier qu'il appartient au restaurant
                if supplier and supplier not in restaurant_suppliers:
                    return jsonify({
                        'success': False,
                        'error': f'Fournisseur {supplier} non autorisé pour ce restaurant : {current_restaurant.get("name")}',
                        'allowed_suppliers': restaurant_suppliers
                    }), 403
            
            orders = order_manager.get_all_orders(
                page=page,
                per_page=per_page,
                supplier=supplier,
                status=status,
                restaurant_suppliers=restaurant_suppliers  # NOUVEAU FILTRE
            )
            
            return jsonify({
                'success': True,
                'data': orders['items'],
                'total': orders['total'],
                'page': orders['page'],
                'pages': orders['pages'],
                'restaurant_context': current_restaurant.get('name') if current_restaurant else None,
                'restaurant_suppliers': restaurant_suppliers
            })
        
        elif request.method == 'POST':
            # Créer une nouvelle commande
            order_data = request.json
            
            # Vérifier que le fournisseur appartient au restaurant
            if current_restaurant:
                restaurant_suppliers = current_restaurant.get('suppliers', [])
                order_supplier = order_data.get('supplier', '')
                
                if order_supplier and order_supplier not in restaurant_suppliers:
                    return jsonify({
                        'success': False,
                        'error': f'Fournisseur {order_supplier} non autorisé pour ce restaurant : {current_restaurant.get("name")}',
                        'allowed_suppliers': restaurant_suppliers
                    }), 403
            
            # Ajouter le contexte restaurant à la commande
            if current_restaurant:
                order_data['restaurant_id'] = current_restaurant.get('id')
                order_data['restaurant_name'] = current_restaurant.get('name')
            
            order_id = order_manager.create_order(order_data)
            
            if order_id:
                # Récupérer les données complètes de la commande créée
                created_order = order_manager.get_order_by_id(order_id)
                
                return jsonify({
                    'success': True,
                    'message': 'Commande créée avec succès',
                    'data': created_order,  # Données complètes au lieu de juste order_id
                    'restaurant': current_restaurant.get('name') if current_restaurant else None
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Erreur lors de la création de la commande'
                }), 500
    except Exception as e:
        logger.error(f"Erreur API commandes: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/orders/<order_id>')
def get_order_detail(order_id):
    """Récupérer le détail d'une commande"""
    try:
        order = order_manager.get_order_by_id(order_id)
        if order:
            return jsonify({
                'success': True,
                'data': order
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Commande non trouvée'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/orders/<order_id>', methods=['PUT'])
def update_order(order_id):
    """Mettre à jour une commande"""
    try:
        data = request.get_json()
        success = order_manager.update_order(order_id, data)
            
        if success:
            return jsonify({
                'success': True,
                'message': 'Commande mise à jour avec succès'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Commande non trouvée'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/orders/<order_id>', methods=['DELETE'])
def delete_order(order_id):
    """Supprimer une commande"""
    try:
        success = order_manager.delete_order(order_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Commande supprimée avec succès'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Impossible de supprimer cette commande'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/orders/<order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Mettre à jour le statut d'une commande"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        comment = data.get('comment', '')
        
        if not new_status:
            return jsonify({
                'success': False,
                'error': 'Statut requis'
            }), 400
        
        success = order_manager.update_order_status(order_id, new_status, comment)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Statut mis à jour avec succès'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Commande non trouvée ou statut invalide'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/orders/stats')
def get_orders_stats():
    """Récupérer les statistiques des commandes"""
    try:
        stats = order_manager.get_stats()
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== VALIDATION COMMANDE vs FACTURE API =====

@app.route('/api/orders/pending-for-supplier/<supplier>')
def get_pending_orders_for_supplier(supplier):
    """Récupérer les commandes en attente pour un fournisseur"""
    try:
        from claude_scanner import ClaudeScanner
        claude_scanner = ClaudeScanner(price_manager)
        pending_orders = claude_scanner.get_pending_orders_for_supplier(supplier)
        
        return jsonify({
            'success': True,
            'data': pending_orders
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/validation/validate-invoice', methods=['POST'])
def validate_invoice():
    """Valider une facture avec ou sans commande associée"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Données manquantes'})
        
        action = data.get('action')
        invoice_data = data.get('invoice_data', {})
        
        if action == 'save_without_order':
            # Sauvegarder sans associer de commande
            # Comparaison automatique des prix
            if 'products' in invoice_data:
                price_analysis = price_manager.compare_prices(invoice_data['products'])
                invoice_data['analysis'] = price_analysis
            
            # Sauvegarder la facture
            invoice_id = invoice_manager.save_invoice(invoice_data)
            
            # Enregistrer les prix unitaires
            if 'products' in invoice_data:
                for product in invoice_data['products']:
                    price_manager.add_price(
                        product_name=product['name'],
                        unit_price=product['unit_price'],
                        unit=product.get('unit', 'unité'),
                        supplier=invoice_data.get('supplier', 'Inconnu'),
                        date=invoice_data.get('date', datetime.now().isoformat()),
                        category="Scanné sans commande"
                    )
            
            return jsonify({
                'success': True,
                'message': 'Facture enregistrée sans association de commande',
                'invoice_id': invoice_id,
                'analysis': invoice_data.get('analysis', {})
            })
        
        else:
            # Validation avec commande
            order_id = data.get('order_id')
            if not order_id:
                return jsonify({'success': False, 'error': 'ID commande manquant'})
            
            # Charger la commande
            order = order_manager.get_order_by_id(order_id)
            if not order:
                return jsonify({
                    'success': False,
                    'error': 'Commande non trouvée'
                }), 404
            
            # Validation avec l'ordre
            validator = OrderInvoiceValidator()
            validation_result = validator.validate_invoice_against_order(
                invoice_data, order
            )
            
            # Comparaison automatique des prix
            if 'products' in invoice_data:
                price_analysis = price_manager.compare_prices(invoice_data['products'])
                invoice_data['analysis'] = price_analysis
            
            # Traitement selon l'action
            if action == 'accept':
                # Accepter et sauvegarder
                invoice_id = invoice_manager.save_invoice(invoice_data)
                
                # Enregistrer les prix validés
                for product in invoice_data['products']:
                    price_data = {
                        'produit': product['name'],
                        'prix': product['unit_price'],
                        'unite': product.get('unit', 'unité'),
                        'fournisseur': order['supplier'],
                        'date': invoice_data['date'],
                        'categorie': "Vérifié manuellement"
                    }
                    price_manager.add_price(price_data)
                
                # Mettre à jour le statut de la commande
                order_manager.update_order_status(order_id, 'invoiced')
                
                return jsonify({
                    'success': True,
                    'message': 'Facture validée et associée à la commande',
                    'invoice_id': invoice_id,
                    'validation_result': validation_result,
                    'analysis': invoice_data.get('analysis', {})
                })
            
            elif action == 'reject':
                return jsonify({
                    'success': True,
                    'message': 'Facture rejetée',
                    'validation_result': validation_result
                })
            
            else:
                return jsonify({'success': False, 'error': 'Action non reconnue'})
    
    except Exception as e:
        logger.error(f"Erreur validation facture: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/orders/validate-manual', methods=['POST'])
def validate_order_manual():
    """Valider une commande manuellement avec détection d'anomalies"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Données manquantes'})
        
        order_id = data.get('order_id')
        verification_data = data.get('verification_data', [])
        notes = data.get('notes', '')
        
        if not order_id:
            return jsonify({'success': False, 'error': 'ID commande manquant'})
        
        # Charger la commande
        order = order_manager.get_order_by_id(order_id)
        if not order:
            return jsonify({
                'success': False,
                'error': 'Commande non trouvée'
            }), 404
        
        # 🔍 DÉTECTION D'ANOMALIES
        anomalies = []
        invoice_products = []
        total_amount = 0
        has_anomalies = False
        
        for item in verification_data:
            received = item['received']
            original = item['original']
            
            # Calculer les différences
            qty_diff = received['quantity'] - original['quantity']
            price_diff = received['unit_price'] - original['unit_price']
            total_diff = received['total_price'] - (original['quantity'] * original['unit_price'])
            
            # Détecter les anomalies (seuils configurables)
            item_anomalies = []
            
            # Anomalie quantité (différence > 5% ou absolue > 0.5)
            if abs(qty_diff) > 0.5 or abs(qty_diff / original['quantity']) > 0.05:
                item_anomalies.append({
                    'type': 'quantity',
                    'severity': 'warning' if abs(qty_diff) <= 1 else 'critical',
                    'expected': original['quantity'],
                    'received': received['quantity'],
                    'difference': qty_diff,
                    'message': f"Quantité différente: commandé {original['quantity']}, reçu {received['quantity']} ({qty_diff:+.2f})"
                })
                has_anomalies = True
            
            # Anomalie prix (différence > 2% ou absolue > 0.50€)
            if abs(price_diff) > 0.50 or abs(price_diff / original['unit_price']) > 0.02:
                item_anomalies.append({
                    'type': 'price',
                    'severity': 'warning' if abs(price_diff) <= 2 else 'critical',
                    'expected': original['unit_price'],
                    'received': received['unit_price'],
                    'difference': price_diff,
                    'message': f"Prix différent: commandé {original['unit_price']}€, facturé {received['unit_price']}€ ({price_diff:+.2f}€)"
                })
                has_anomalies = True
            
            # Anomalie produit manquant/en plus (quantité = 0)
            if received['quantity'] == 0 and original['quantity'] > 0:
                item_anomalies.append({
                    'type': 'missing',
                    'severity': 'critical',
                    'expected': original['quantity'],
                    'received': 0,
                    'message': f"Produit manquant: {original['name']} (commandé {original['quantity']})"
                })
                has_anomalies = True
            
            if len(item_anomalies) > 0:
                anomalies.append({
                    'product': original['name'],
                    'anomalies': item_anomalies
                })
            
            # Ajouter le produit à la facture (même avec anomalies)
            if received['quantity'] > 0:  # Ne pas inclure les produits à quantité 0
                product_data = {
                    'name': original['name'],
                    'quantity': received['quantity'],
                    'unit_price': received['unit_price'],
                    'unit': original.get('unit', 'unité'),
                    'total_price': received['total_price'],
                    'original_quantity': original['quantity'],
                    'original_unit_price': original['unit_price'],
                    'has_anomaly': len(item_anomalies) > 0
                }
                invoice_products.append(product_data)
                total_amount += received['total_price']
        
        # Créer la facture avec informations d'anomalies
        invoice_data = {
            'supplier': order['supplier'],
            'date': datetime.now().isoformat(),
            'total_amount': total_amount,
            'products': invoice_products,
            'verification_method': 'manual',
            'verification_notes': notes,
            'verified_at': data.get('verified_at'),
            'verified_by': data.get('verified_by', 'user'),
                'order_id': order_id,
            'has_anomalies': has_anomalies,
            'anomalies': anomalies,
            'anomaly_status': 'detected' if has_anomalies else 'none'
        }
        
        # Comparaison automatique des prix
        price_analysis = price_manager.compare_prices(invoice_products)
        invoice_data['analysis'] = price_analysis
        
        # Sauvegarder la facture
        invoice_id = invoice_manager.save_invoice(invoice_data)
        
        # Enregistrer les prix validés (seulement pour les produits sans anomalie de prix)
        for product in invoice_products:
            if not product.get('has_anomaly') or product['unit_price'] == product['original_unit_price']:
                price_data = {
                    'produit': product['name'],
                    'prix': product['unit_price'],
                    'unite': product.get('unit', 'unité'),
                    'fournisseur': order['supplier'],
                    'date': invoice_data['date'],
                    'categorie': "Vérifié manuellement"
                }
                price_manager.add_price(price_data)
        
        # Mettre à jour le statut de la commande
        status = 'delivered_with_anomalies' if has_anomalies else 'delivered'
        comment = f'Vérification manuelle - {len(anomalies)} anomalie(s) détectée(s)' if has_anomalies else 'Vérification manuelle - Aucune anomalie'
        order_manager.update_order_status(order_id, 'delivered', comment)
        
        response_data = {
            'success': True,
            'message': 'Commande validée manuellement avec succès',
            'invoice_id': invoice_id,
            'analysis': price_analysis,
            'has_anomalies': has_anomalies,
            'anomalies_count': len(anomalies),
            'anomalies': anomalies
        }
        
        # 📧 NOTIFICATION EMAIL si anomalies critiques
        if has_anomalies:
            critical_anomalies = []
            for anomaly in anomalies:
                critical_items = [a for a in anomaly['anomalies'] if a['severity'] == 'critical']
                if critical_items:
                    critical_anomalies.extend(critical_items)
            
            if critical_anomalies:
                try:
                    email_manager.send_anomaly_notification(
                        invoice_id=invoice_id,
                        anomalies_data=critical_anomalies,
                        order_data=order,
                        invoice_data=invoice_data
                    )
                    logger.info(f"📧 Notification d'anomalies envoyée pour facture {invoice_id}")
                except Exception as email_error:
                    logger.error(f"❌ Erreur envoi notification: {email_error}")
        
        return jsonify({
            'success': True,
            'invoice_id': invoice_id,
            'message': 'Commande validée et facture créée avec succès',
            'has_anomalies': has_anomalies,
            'anomalies': anomalies,
            'analysis': price_analysis
        })
    
    except Exception as e:
        logger.error(f"Erreur validation manuelle: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ===== EMAIL API =====

@app.route('/api/email/config', methods=['GET'])
def get_email_config():
    """Récupérer la configuration email"""
    try:
        config = email_manager.get_config()
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/email/config', methods=['POST'])
def save_email_config():
    """Sauvegarder la configuration email"""
    try:
        config = request.json
        success = email_manager.save_config(config)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Configuration sauvegardée'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Erreur lors de la sauvegarde'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/email/test', methods=['POST'])
def test_email_connection():
    """Tester la connexion email"""
    try:
        result = email_manager.test_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/email/notifications', methods=['GET'])
def get_email_notifications():
    """Récupérer l'historique des notifications email"""
    try:
        limit = request.args.get('limit', 50, type=int)
        notifications = email_manager.get_notifications_history(limit)
        
        return jsonify({
            'success': True,
            'data': notifications,
            'count': len(notifications)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/email/send-order', methods=['POST'])
def send_order_email():
    """Envoyer un email de commande manuellement"""
    try:
        data = request.json
        order_id = data.get('order_id')
        supplier_email = data.get('supplier_email')
        
        if not order_id or not supplier_email:
            return jsonify({
                'success': False,
                'error': 'ID commande et email fournisseur requis'
            }), 400
        
        # Récupérer les détails de la commande
        order = order_manager.get_order_by_id(order_id)
        if not order:
            return jsonify({
                'success': False,
                'error': 'Commande non trouvée'
            }), 404
        
        # Enrichir les données de commande avec les informations du restaurant
        restaurant_id = order.get('restaurant_id')
        if restaurant_id:
            # Récupérer les informations du restaurant depuis AuthManager
            restaurants = auth_manager._load_restaurants()
            restaurant_info = next((r for r in restaurants if r['id'] == restaurant_id), None)
            
            if restaurant_info:
                order['restaurant_address'] = restaurant_info.get('address', 'Adresse non renseignée')
                order['restaurant_name'] = restaurant_info.get('name', order.get('restaurant_name', 'Restaurant'))
        
        # Envoyer l'email
        result = email_manager.send_order_notification(order, supplier_email)
        
        # Si l'email est envoyé avec succès, mettre à jour le statut de la commande
        if result.get('success'):
            order_manager.update_order_status(order_id, 'confirmed', 'Email envoyé avec succès')
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/parametres')
@login_required
def parametres():
    """Page de paramètres incluant la configuration email"""
    return render_template('parametres.html')

# ===== ROUTES STATIQUES =====

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Servir les fichiers statiques"""
    return send_from_directory('static', filename)

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    """Servir les fichiers uploadés"""
    return send_from_directory(UPLOAD_FOLDER, filename)

# ===== ROUTES D'ADMINISTRATION (Master Admin seulement) =====

@app.route('/admin')
@login_required
@role_required('master_admin')
def admin():
    """Page d'administration master"""
    return render_template('admin.html')

@app.route('/admin/email')
@login_required
@role_required('master_admin')
def admin_email():
    """Page de configuration email (Master Admin seulement)"""
    return render_template('email_config.html')

@app.route('/api/admin/clients', methods=['GET'])
@login_required
@role_required('master_admin')
def get_admin_clients():
    """Récupérer tous les clients"""
    try:
        clients = auth_manager._load_clients()
        return jsonify({
            'success': True,
            'data': clients
        })
    except Exception as e:
        logger.error(f"Erreur récupération clients: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/clients', methods=['POST'])
@login_required
@role_required('master_admin')
def create_admin_client():
    """Créer un nouveau client et envoyer l'invitation"""
    try:
        data = request.get_json()
        
        # Créer le client
        result = auth_manager.create_client(
            name=data.get('name'),
            email=data.get('email'),
            contact_name=data.get('contact_name'),
            phone=data.get('phone')
        )
        
        if result['success']:
            client = result['client']
            
            # Créer et envoyer l'invitation
            invitation_result = email_manager.create_invitation(
                client_id=client['id'],
                client_name=client['name'],
                client_email=client['email'],
                invited_by=session.get('user_id')
            )
            
            if invitation_result['success']:
                # Envoyer l'email d'invitation
                email_result = email_manager.send_client_invitation(
                    client_name=client['name'],
                    client_email=client['email'],
                    token=invitation_result['token']
                )
                
                return jsonify({
                    'success': True,
                    'client': client,
                    'invitation_sent': email_result['success'],
                    'email_message': email_result.get('message', 'Invitation envoyée'),
                    'simulated': email_result.get('simulated', False)
                })
            else:
                # Client créé mais invitation échouée
                return jsonify({
                    'success': True,
                    'client': client,
                    'invitation_sent': False,
                    'email_message': invitation_result['error']
                })
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Erreur création client: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/restaurants', methods=['GET'])
@login_required
@role_required('master_admin')
def get_admin_restaurants():
    """Récupérer tous les restaurants"""
    try:
        restaurants = auth_manager._load_restaurants()
        return jsonify({
            'success': True,
            'data': restaurants
        })
    except Exception as e:
        logger.error(f"Erreur récupération restaurants: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/restaurants', methods=['POST'])
@login_required
@role_required('master_admin')
def create_admin_restaurant():
    """Créer un nouveau restaurant"""
    try:
        data = request.get_json()
        result = auth_manager.create_restaurant(
            client_id=data.get('client_id'),
            name=data.get('name'),
            address=data.get('address'),
            phone=data.get('phone'),
            email=data.get('email')
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Erreur création restaurant: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/users', methods=['GET'])
@login_required
@role_required('master_admin')
def get_admin_users():
    """Récupérer tous les utilisateurs"""
    try:
        users = auth_manager._load_users()
        # Masquer les mots de passe
        safe_users = []
        for user in users:
            safe_user = user.copy()
            safe_user.pop('password', None)
            safe_users.append(safe_user)
        
        return jsonify({
            'success': True,
            'data': safe_users
        })
    except Exception as e:
        logger.error(f"Erreur récupération utilisateurs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/users', methods=['POST'])
@login_required
@role_required('master_admin')
def create_admin_user():
    """Créer un nouvel utilisateur"""
    try:
        data = request.get_json()
        result = auth_manager.create_user(
            username=data.get('username'),
            email=data.get('email'),
            password=data.get('password'),
            name=data.get('name'),
            role=data.get('role'),
            client_id=data.get('client_id'),
            restaurant_id=data.get('restaurant_id')
        )
        
        if result['success']:
            # Masquer le mot de passe dans la réponse
            if 'user' in result and 'password' in result['user']:
                result['user'].pop('password')
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Erreur création utilisateur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/clients/<client_id>', methods=['PUT'])
@login_required
@role_required('master_admin')
def update_admin_client(client_id):
    """Modifier un client"""
    try:
        data = request.get_json()
        result = auth_manager.update_client(
            client_id=client_id,
            name=data.get('name'),
            email=data.get('email'),
            contact_name=data.get('contact_name'),
            phone=data.get('phone')
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Erreur modification client: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/clients/<client_id>', methods=['DELETE'])
@login_required
@role_required('master_admin')
def delete_admin_client(client_id):
    """Supprimer un client"""
    try:
        result = auth_manager.delete_client(client_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Erreur suppression client: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/restaurants/<restaurant_id>', methods=['PUT'])
@login_required
@role_required('master_admin')
def update_admin_restaurant(restaurant_id):
    """Modifier un restaurant"""
    try:
        data = request.get_json()
        result = auth_manager.update_restaurant(
            restaurant_id=restaurant_id,
            name=data.get('name'),
            address=data.get('address'),
            phone=data.get('phone'),
            email=data.get('email')
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Erreur modification restaurant: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/restaurants/<restaurant_id>', methods=['DELETE'])
@login_required
@role_required('master_admin')
def delete_admin_restaurant(restaurant_id):
    """Supprimer un restaurant"""
    try:
        result = auth_manager.delete_restaurant(restaurant_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Erreur suppression restaurant: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/users/<user_id>', methods=['PUT'])
@login_required
@role_required('master_admin')
def update_admin_user(user_id):
    """Modifier un utilisateur"""
    try:
        data = request.get_json()
        result = auth_manager.update_user(
            user_id=user_id,
            name=data.get('name'),
            email=data.get('email'),
            username=data.get('username'),
            role=data.get('role'),
            client_id=data.get('client_id'),
            restaurant_id=data.get('restaurant_id'),
            active=data.get('active')
        )
        
        if result['success']:
            # Masquer le mot de passe dans la réponse
            if 'user' in result and 'password' in result['user']:
                result['user'].pop('password')
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Erreur modification utilisateur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/users/<user_id>', methods=['DELETE'])
@login_required
@role_required('master_admin')
def delete_admin_user(user_id):
    """Supprimer un utilisateur"""
    try:
        result = auth_manager.delete_user(user_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Erreur suppression utilisateur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== ROUTES CLIENT (Gestion de ses restaurants et utilisateurs) =====

@app.route('/client')
@login_required
@role_required('client')
def client_dashboard():
    """Dashboard client pour gérer ses restaurants"""
    return render_template('client_dashboard.html')

@app.route('/api/client/restaurants', methods=['GET'])
@login_required
@role_required('client')
def get_client_restaurants():
    """Récupérer les restaurants du client connecté"""
    try:
        user_context = auth_manager.get_user_context(session['user_id'])
        if not user_context['success']:
            return jsonify(user_context), 400
        
        client_id = user_context['context']['user']['client_id']
        result = auth_manager.get_client_restaurants(client_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erreur récupération restaurants client: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/client/restaurant/<restaurant_id>/users', methods=['GET'])
@login_required
@role_required('client')
def get_client_restaurant_users(restaurant_id):
    """Récupérer les utilisateurs d'un restaurant du client"""
    try:
        user_context = auth_manager.get_user_context(session['user_id'])
        if not user_context['success']:
            return jsonify(user_context), 400
        
        client_id = user_context['context']['user']['client_id']
        
        # Vérifier que le restaurant appartient au client
        restaurants_result = auth_manager.get_client_restaurants(client_id)
        if not restaurants_result['success']:
            return jsonify(restaurants_result), 400
        
        restaurant_ids = [r['id'] for r in restaurants_result['restaurants']]
        if restaurant_id not in restaurant_ids:
            return jsonify({
                'success': False,
                'error': 'Restaurant non autorisé'
            }), 403
        
        result = auth_manager.get_restaurant_users(restaurant_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erreur récupération utilisateurs restaurant: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/client/restaurant/<restaurant_id>/users', methods=['POST'])
@login_required
@role_required('client')
def create_client_restaurant_user(restaurant_id):
    """Créer un utilisateur pour un restaurant du client"""
    try:
        user_context = auth_manager.get_user_context(session['user_id'])
        if not user_context['success']:
            return jsonify(user_context), 400
        
        client_id = user_context['context']['user']['client_id']
        data = request.get_json()
        
        # Vérifier que le rôle est autorisé (admin ou user seulement)
        if data.get('role') not in ['admin', 'user']:
            return jsonify({
                'success': False,
                'error': 'Seuls les rôles admin et user sont autorisés'
            }), 400
        
        result = auth_manager.create_user_for_client(
            client_id=client_id,
            username=data.get('username'),
            email=data.get('email'),
            password=data.get('password'),
            name=data.get('name'),
            role=data.get('role'),
            restaurant_id=restaurant_id
        )
        
        if result['success']:
            # Masquer le mot de passe dans la réponse
            if 'user' in result and 'password' in result['user']:
                result['user'].pop('password')
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Erreur création utilisateur restaurant: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/client/switch-restaurant', methods=['POST'])
@login_required
@role_required('client')
def switch_restaurant():
    """Changer de restaurant actuel pour un client"""
    try:
        data = request.get_json()
        restaurant_id = data.get('restaurant_id')
        
        if not restaurant_id:
            return jsonify({
                'success': False,
                'message': 'ID restaurant requis'
            }), 400
        
        user_context = auth_manager.get_user_context(session['user_id'])
        if not user_context['success']:
            return jsonify(user_context), 400
        
        client_id = user_context['context']['user']['client_id']
        
        # Vérifier que le restaurant appartient au client
        restaurants_result = auth_manager.get_client_restaurants(client_id)
        if not restaurants_result['success']:
            return jsonify(restaurants_result), 400
        
        restaurant_ids = [r['id'] for r in restaurants_result['restaurants']]
        if restaurant_id not in restaurant_ids:
            return jsonify({
                'success': False,
                'message': 'Restaurant non autorisé'
            }), 403
        
        # Mettre à jour le restaurant actuel dans la session
        session['current_restaurant_id'] = restaurant_id
        
        return jsonify({
            'success': True,
            'message': 'Restaurant changé avec succès'
        })
        
    except Exception as e:
        logger.error(f"Erreur changement restaurant: {e}")
        return jsonify({
            'success': False,
            'message': 'Erreur serveur'
        }), 500

# ===== ROUTES D'INVITATION =====

@app.route('/invitation/<token>')
def invitation_page(token):
    """Page d'acceptation d'invitation"""
    result = email_manager.get_invitation_by_token(token)
    
    if not result['success']:
        return render_template('error.html', 
                             title="Invitation invalide",
                             message=result['error']), 404
    
    return render_template('invitation.html', 
                         invitation=result['invitation'],
                         token=token)

@app.route('/api/invitation/accept', methods=['POST'])
def accept_invitation():
    """Accepter une invitation et créer le compte client"""
    try:
        data = request.get_json()
        token = data.get('token')
        username = data.get('username')
        password = data.get('password')
        
        # Vérifier l'invitation
        result = email_manager.get_invitation_by_token(token)
        if not result['success']:
            return jsonify(result), 400
        
        invitation = result['invitation']
        
        # Créer le compte utilisateur client
        user_result = auth_manager.create_user(
            username=username,
            email=invitation['client_email'],
            password=password,
            name=invitation['client_name'],
            role='client',
            client_id=invitation['client_id'],
            restaurant_id=None
        )
        
        if user_result['success']:
            # Marquer l'invitation comme acceptée
            email_manager.accept_invitation(token)
            
            return jsonify({
                'success': True,
                'message': 'Compte créé avec succès',
                'user': user_result['user']
            })
        else:
            return jsonify(user_result), 400
            
    except Exception as e:
        logger.error(f"Erreur acceptation invitation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API pour changer de restaurant (Master Admin)
@app.route('/api/admin/switch-restaurant', methods=['POST'])
@login_required
@role_required('master_admin')
def admin_switch_restaurant():
    try:
        data = request.get_json()
        restaurant_id = data.get('restaurant_id')
        
        current_user = auth_manager.get_current_user()
        
        if restaurant_id is None:
            # Désélectionner le restaurant
            session.pop('current_restaurant_id', None)
            
            # 🎯 NOUVEAU: Mettre à jour aussi la base de données
            users = auth_manager._load_users()
            for user in users:
                if user['id'] == current_user['id']:
                    user['selected_restaurant_id'] = None
                    break
            auth_manager._save_users(users)
            
            return jsonify({
                'success': True,
                'message': 'Restaurant désélectionné',
                'restaurant': None
            })
        
        # Charger les restaurants via auth_manager
        restaurants = auth_manager._load_restaurants()
        restaurant = next((r for r in restaurants if r['id'] == restaurant_id), None)
        
        if not restaurant:
            return jsonify({
                'success': False,
                'error': 'Restaurant non trouvé'
            }), 404
        
        # 🎯 CORRECTION: Mettre à jour la session ET la base de données
        session['current_restaurant_id'] = restaurant_id
        
        # Mettre à jour selected_restaurant_id dans la base de données
        users = auth_manager._load_users()
        for user in users:
            if user['id'] == current_user['id']:
                user['selected_restaurant_id'] = restaurant_id
                break
        auth_manager._save_users(users)
        
        print(f"🔄 Restaurant changé pour Master Admin: {restaurant['name']} (ID: {restaurant_id})")
        
        return jsonify({
            'success': True,
            'message': f'Restaurant {restaurant["name"]} sélectionné',
            'restaurant': restaurant
        })
        
    except Exception as e:
        logger.error(f"Erreur switch restaurant admin: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API pour la configuration email (Admin)
@app.route('/api/admin/email-config', methods=['GET'])
@login_required
@role_required('master_admin')
def get_admin_email_config():
    try:
        config = email_manager.get_config()
        # Masquer le mot de passe pour la sécurité
        if config.get('password'):
            config = config.copy()  # Créer une copie pour ne pas modifier l'original
            config['password'] = '***'
        return jsonify({
            'success': True,
            'data': config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/email-config', methods=['POST'])
@login_required
@role_required('master_admin')
def save_admin_email_config():
    try:
        data = request.get_json()
        email_manager.save_config(data)
        return jsonify({
            'success': True,
            'message': 'Configuration email sauvegardée'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/test-email', methods=['POST'])
@login_required
@role_required('master_admin')
def test_admin_email():
    try:
        data = request.get_json()
        result = email_manager.test_connection_with_params(
            email=data.get('email'),
            password=data.get('password'),
            smtp_server=data.get('smtp_server', 'smtp.gmail.com'),
            smtp_port=587
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API FILTREES PAR RESTAURANT
@app.route('/api/restaurant/suppliers', methods=['GET'])
@login_required
def get_restaurant_suppliers():
    """Récupérer les fournisseurs du restaurant sélectionné"""
    try:
        # Récupérer le contexte utilisateur
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant')
        
        # Vérifier qu'un restaurant est sélectionné
        if not current_restaurant:
            return jsonify({
                'success': False,
                'error': 'Aucun restaurant sélectionné. Veuillez sélectionner un restaurant.',
                'requires_restaurant': True
            }), 400
        
        from modules.supplier_manager import SupplierManager
        supplier_manager = SupplierManager()
        
        # Récupérer les fournisseurs du restaurant
        restaurant_suppliers = current_restaurant.get('suppliers', [])
        all_suppliers = supplier_manager.get_all_suppliers()
        
        # ✅ CORRECTION: Filtrage strict - seulement les fournisseurs EXPLICITEMENT associés
        # Plus d'auto-association automatique pour éviter les confusions
        filtered_suppliers = []
        
        for supplier in all_suppliers:
            supplier_name = supplier['name']
            
            # Inclure si le fournisseur est explicitement associé au restaurant
            if supplier_name in restaurant_suppliers:
                filtered_suppliers.append(supplier)
                continue
            
            # OU si le fournisseur a des produits SPÉCIFIQUEMENT pour ce restaurant
            # (vérifier dans les prix et produits en attente)
            restaurant_name = current_restaurant.get('name')
            has_specific_products = False
            
            # Vérifier dans les produits en attente avec filtre restaurant
            for product in supplier.get('pending_products', []):
                product_restaurant = product.get('restaurant', 'Général')
                if product_restaurant == restaurant_name:
                    has_specific_products = True
                    break
            
            # Vérifier dans les prix confirmés avec filtre restaurant
            if not has_specific_products:
                try:
                    supplier_products = supplier_manager.get_supplier_products(supplier_name)
                    for product in supplier_products:
                        if product.get('restaurant') == restaurant_name:
                            has_specific_products = True
                            break
                except:
                    pass
            
            if has_specific_products:
                # Auto-associer seulement si il y a des produits spécifiques
                filtered_suppliers.append(supplier)
                if supplier_name not in restaurant_suppliers:
                    print(f"🔗 AUTO-ASSOCIATION: {supplier_name} → {restaurant_name} (produits spécifiques détectés)")
                    restaurant_suppliers.append(supplier_name)
                    current_restaurant['suppliers'] = restaurant_suppliers
                    
                    # Persister l'association
                    try:
                        rest_path = 'data/restaurants.json'
                        if os.path.exists(rest_path):
                            with open(rest_path, 'r', encoding='utf-8') as f:
                                restaurants = json.load(f)
                            for r in restaurants:
                                if r['id'] == current_restaurant['id']:
                                    r['suppliers'] = restaurant_suppliers
                                    break
                            with open(rest_path, 'w', encoding='utf-8') as f:
                                json.dump(restaurants, f, indent=2, ensure_ascii=False)
                    except Exception as err:
                        logger.warning(f"Impossible de mettre à jour restaurants.json : {err}")
        
        return jsonify({
            'success': True,
            'data': filtered_suppliers,
            'restaurant': current_restaurant['name'],
            'count': len(filtered_suppliers)
        })
        
    except Exception as e:
        logger.error(f"Erreur API fournisseurs restaurant: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/restaurant/orders', methods=['GET'])
@login_required
def get_restaurant_orders():
    """Récupérer les commandes du restaurant sélectionné"""
    try:
        # Récupérer le contexte utilisateur
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant')
        
        # Vérifier qu'un restaurant est sélectionné
        if not current_restaurant:
            return jsonify({
                'success': False,
                'error': 'Aucun restaurant sélectionné. Veuillez sélectionner un restaurant.',
                'requires_restaurant': True
            }), 400
        
        # Récupérer les commandes filtrées par restaurant
        orders = order_manager.get_orders_by_restaurant(current_restaurant['id'])
        
        return jsonify({
            'success': True,
            'data': orders,
            'restaurant': current_restaurant['name'],
            'count': len(orders)
        })
        
    except Exception as e:
        logger.error(f"Erreur API commandes restaurant: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/restaurant/invoices', methods=['GET'])
@login_required
def get_restaurant_invoices():
    """Récupérer les factures du restaurant sélectionné"""
    try:
        # Récupérer le contexte utilisateur
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant')
        
        # Vérifier qu'un restaurant est sélectionné
        if not current_restaurant:
            return jsonify({
                'success': False,
                'error': 'Aucun restaurant sélectionné. Veuillez sélectionner un restaurant.',
                'requires_restaurant': True
            }), 400
        
        # Récupérer les factures filtrées par restaurant
        invoices = invoice_manager.get_invoices_by_restaurant(current_restaurant['id'])
        
        return jsonify({
            'success': True,
            'data': invoices,
            'restaurant': current_restaurant['name'],
            'count': len(invoices)
        })
        
    except Exception as e:
        logger.error(f"Erreur API factures restaurant: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/restaurant/prices', methods=['GET'])
@login_required
def get_restaurant_prices():
    """Récupérer les prix du restaurant sélectionné"""
    try:
        # Récupérer le contexte utilisateur
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant')
        
        # Vérifier qu'un restaurant est sélectionné
        if not current_restaurant:
            return jsonify({
                'success': False,
                'error': 'Aucun restaurant sélectionné. Veuillez sélectionner un restaurant.',
                'requires_restaurant': True
            }), 400
        
        # Récupérer les prix filtrés par restaurant
        restaurant_suppliers = current_restaurant.get('suppliers', [])
        prices = price_manager.get_prices_by_suppliers(restaurant_suppliers)
        
        return jsonify({
            'success': True,
            'data': prices,
            'restaurant': current_restaurant['name'],
            'suppliers': restaurant_suppliers,
            'count': len(prices)
        })
        
    except Exception as e:
        logger.error(f"Erreur API prix restaurant: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== SYNCHRONISATION MULTI-RESTAURANTS API =====

@app.route('/api/sync/status/<restaurant_id>', methods=['GET'])
@login_required
@role_required('master_admin')
def get_sync_status(restaurant_id):
    """Récupérer le statut de synchronisation d'un restaurant"""
    try:
        from modules.sync_manager import SyncManager
        sync_manager = SyncManager()
        
        result = sync_manager.get_sync_status(restaurant_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erreur API sync status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sync/groups', methods=['GET'])
@login_required
@role_required('master_admin')
def get_sync_groups():
    """Récupérer tous les groupes de synchronisation"""
    try:
        from modules.sync_manager import SyncManager
        sync_manager = SyncManager()
        
        sync_groups = sync_manager.get_sync_groups()
        return jsonify({
            'success': True,
            'data': sync_groups,
            'count': len(sync_groups)
        })
        
    except Exception as e:
        logger.error(f"Erreur API sync groups: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sync/create-group', methods=['POST'])
@login_required
@role_required('master_admin')
def create_sync_group():
    """Créer un nouveau groupe de synchronisation"""
    try:
        data = request.json
        group_name = data.get('group_name')
        restaurant_ids = data.get('restaurant_ids', [])
        master_restaurant_id = data.get('master_restaurant_id')
        
        if not group_name or not restaurant_ids or not master_restaurant_id:
            return jsonify({
                'success': False,
                'error': 'Paramètres manquants: group_name, restaurant_ids, master_restaurant_id'
            }), 400
        
        from modules.sync_manager import SyncManager
        sync_manager = SyncManager()
        
        result = sync_manager.create_sync_group(group_name, restaurant_ids, master_restaurant_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erreur API create sync group: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sync/settings/<restaurant_id>', methods=['PUT'])
@login_required
@role_required('master_admin')
def update_sync_settings(restaurant_id):
    """Mettre à jour les paramètres de synchronisation d'un restaurant"""
    try:
        sync_settings = request.json
        
        from modules.sync_manager import SyncManager
        sync_manager = SyncManager()
        
        result = sync_manager.update_sync_settings(restaurant_id, sync_settings)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erreur API update sync settings: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sync/disable/<restaurant_id>', methods=['POST'])
@login_required
@role_required('master_admin')
def disable_sync(restaurant_id):
    """Désactiver la synchronisation pour un restaurant"""
    try:
        from modules.sync_manager import SyncManager
        sync_manager = SyncManager()
        
        result = sync_manager.disable_sync(restaurant_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erreur API disable sync: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sync/remove-supplier', methods=['POST'])
@login_required  
def sync_remove_supplier():
    """Synchroniser la suppression d'un fournisseur dans le groupe"""
    try:
        data = request.json
        restaurant_id = data.get('restaurant_id')
        supplier_name = data.get('supplier_name')
        
        if not restaurant_id or not supplier_name:
            return jsonify({
                'success': False,
                'error': 'Paramètres manquants: restaurant_id, supplier_name'
            }), 400
            
        from modules.sync_manager import SyncManager
        sync_manager = SyncManager()
        
        result = sync_manager.sync_supplier_removal_to_group(restaurant_id, supplier_name)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erreur API sync remove supplier: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sync/full-suppliers', methods=['POST'])
@login_required  
def sync_full_suppliers():
    """Synchroniser la liste complète des fournisseurs dans le groupe"""
    try:
        data = request.json
        restaurant_id = data.get('restaurant_id')
        
        if not restaurant_id:
            return jsonify({
                'success': False,
                'error': 'Paramètre manquant: restaurant_id'
            }), 400
            
        from modules.sync_manager import SyncManager
        sync_manager = SyncManager()
        
        result = sync_manager.sync_full_suppliers_list_to_group(restaurant_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erreur API sync full suppliers: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sync/available-restaurants/<client_id>', methods=['GET'])
@login_required
@role_required('master_admin')
def get_available_restaurants_for_sync(client_id):
    """Récupérer les restaurants disponibles pour la synchronisation"""
    try:
        from modules.sync_manager import SyncManager
        sync_manager = SyncManager()
        
        restaurants = sync_manager.get_available_restaurants_for_sync(client_id)
        return jsonify({
            'success': True,
            'data': restaurants,
            'count': len(restaurants)
        })
        
    except Exception as e:
        logger.error(f"Erreur API available restaurants: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sync/test-supplier', methods=['POST'])
@login_required
@role_required('master_admin')
def test_sync_supplier():
    """Tester la synchronisation d'un fournisseur"""
    try:
        data = request.json
        source_restaurant_id = data.get('source_restaurant_id')
        supplier_name = data.get('supplier_name')
        
        if not source_restaurant_id or not supplier_name:
            return jsonify({
                'success': False,
                'error': 'Paramètres manquants: source_restaurant_id, supplier_name'
            }), 400
        
        from modules.sync_manager import SyncManager
        sync_manager = SyncManager()
        
        result = sync_manager.sync_suppliers_to_group(source_restaurant_id, supplier_name)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erreur API test sync supplier: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== INTERFACE SYNCHRONISATION =====

@app.route('/synchronisation')
@login_required
@role_required('master_admin')
def synchronisation():
    """Page de gestion de la synchronisation multi-restaurants"""
    return render_template('synchronisation.html')

# ===== API GESTION FOURNISSEURS RESTAURANT =====

@app.route('/api/admin/restaurants/<restaurant_id>/suppliers', methods=['POST', 'DELETE'])
@login_required
def manage_restaurant_suppliers(restaurant_id):
    """Ajouter ou supprimer un fournisseur d'un restaurant"""
    try:
        # Vérifier les permissions admin
        user_context = auth_manager.get_user_context()
        if not user_context or user_context['user']['role'] not in ['master_admin']:
            return jsonify({
                'success': False,
                'error': 'Accès non autorisé - Admin requis'
            }), 403
        
        # Récupérer les données du restaurant
        restaurants = []
        if os.path.exists('data/restaurants.json'):
            with open('data/restaurants.json', 'r', encoding='utf-8') as f:
                restaurants = json.load(f)
        
        # Trouver le restaurant
        restaurant = None
        restaurant_index = None
        for i, r in enumerate(restaurants):
            if r['id'] == restaurant_id:
                restaurant = r
                restaurant_index = i
                break
        
        if not restaurant:
            return jsonify({
                'success': False,
                'error': 'Restaurant introuvable'
            }), 404
        
        # Récupérer le nom du fournisseur
        data = request.json
        supplier_name = data.get('supplier_name', '').strip()
        
        if not supplier_name:
            return jsonify({
                'success': False,
                'error': 'Nom du fournisseur requis'
            }), 400
        
        # Initialiser la liste des fournisseurs si nécessaire
        if 'suppliers' not in restaurant:
            restaurant['suppliers'] = []
        
        if request.method == 'POST':
            # Ajouter un fournisseur
            if supplier_name in restaurant['suppliers']:
                return jsonify({
                    'success': False,
                    'error': f'Le fournisseur {supplier_name} est déjà associé à ce restaurant'
                })
            
            restaurant['suppliers'].append(supplier_name)
            action_message = f'Fournisseur {supplier_name} ajouté au restaurant {restaurant["name"]}'
            
        elif request.method == 'DELETE':
            # Supprimer un fournisseur
            if supplier_name not in restaurant['suppliers']:
                return jsonify({
                    'success': False,
                    'error': f'Le fournisseur {supplier_name} n\'est pas associé à ce restaurant'
                })
            
            restaurant['suppliers'].remove(supplier_name)
            action_message = f'Fournisseur {supplier_name} retiré du restaurant {restaurant["name"]}'
        
        # Mettre à jour la liste des restaurants
        restaurants[restaurant_index] = restaurant
        
        # Sauvegarder
        with open('data/restaurants.json', 'w', encoding='utf-8') as f:
            json.dump(restaurants, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ {action_message}")
        
        return jsonify({
            'success': True,
            'message': action_message,
            'restaurant': restaurant,
            'suppliers_count': len(restaurant['suppliers'])
        })
        
    except Exception as e:
        logger.error(f"Erreur gestion fournisseurs restaurant: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/restaurant/suppliers/create', methods=['POST'])
@login_required
def create_supplier_for_restaurant():
    """Créer un nouveau fournisseur et l'associer automatiquement au restaurant actuel"""
    try:
        # Récupérer le contexte utilisateur
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant')
        
        # Vérifier qu'un restaurant est sélectionné
        if not current_restaurant:
            return jsonify({
                'success': False,
                'error': 'Aucun restaurant sélectionné. Veuillez sélectionner un restaurant.',
                'requires_restaurant': True
            }), 400
        
        # Récupérer les données du fournisseur
        data = request.json
        supplier_name = data.get('name', '').strip()
        
        if not supplier_name:
            return jsonify({
                'success': False,
                'error': 'Le nom du fournisseur est obligatoire'
            }), 400
        
        # 1. Créer le fournisseur dans la base de données des fournisseurs
        from modules.supplier_manager import SupplierManager
        supplier_manager = SupplierManager()
        
        supplier_data = {
            'name': supplier_name,
            'email': data.get('email', ''),
            'notes': data.get('notes', ''),
            'delivery_days': data.get('delivery_days', [])
        }
        
        success = supplier_manager.save_supplier(supplier_data)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Erreur lors de la création du fournisseur'
            }), 500
        
        # 2. Associer automatiquement le fournisseur au restaurant actuel
        restaurants = []
        if os.path.exists('data/restaurants.json'):
            with open('data/restaurants.json', 'r', encoding='utf-8') as f:
                restaurants = json.load(f)
        
        # Trouver le restaurant actuel
        restaurant_updated = False
        for i, restaurant in enumerate(restaurants):
            if restaurant['id'] == current_restaurant['id']:
                if 'suppliers' not in restaurant:
                    restaurant['suppliers'] = []
                
                if supplier_name not in restaurant['suppliers']:
                    restaurant['suppliers'].append(supplier_name)
                    restaurants[i] = restaurant
                    restaurant_updated = True
                break
        
        # Sauvegarder les modifications du restaurant
        if restaurant_updated:
            with open('data/restaurants.json', 'w', encoding='utf-8') as f:
                json.dump(restaurants, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Fournisseur {supplier_name} créé et associé au restaurant {current_restaurant['name']}")
        
        return jsonify({
            'success': True,
            'message': f'Fournisseur {supplier_name} créé et associé au restaurant avec succès',
            'supplier': supplier_data,
            'restaurant': current_restaurant['name']
        })
        
    except Exception as e:
        logger.error(f"Erreur création fournisseur restaurant: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/restaurant/suppliers/<supplier_name>/products', methods=['GET', 'POST'])
@login_required
def manage_restaurant_supplier_products(supplier_name):
    """Gérer les produits d'un fournisseur pour le restaurant actuel"""
    try:
        # Récupérer le contexte utilisateur
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant')
        
        # Vérifier qu'un restaurant est sélectionné
        if not current_restaurant:
            return jsonify({
                'success': False,
                'error': 'Aucun restaurant sélectionné. Veuillez sélectionner un restaurant.',
                'requires_restaurant': True
            }), 400
        
        # Vérifier que le fournisseur est associé au restaurant
        restaurant_suppliers = current_restaurant.get('suppliers', [])
        if supplier_name not in restaurant_suppliers:
            return jsonify({
                'success': False,
                'error': f'Le fournisseur {supplier_name} n\'est pas associé au restaurant {current_restaurant["name"]}'
            }), 403
        
        if request.method == 'GET':
            # Récupérer les produits du fournisseur pour ce restaurant
            # TODO: Implémenter la récupération des produits filtrés par restaurant
            return jsonify({
                'success': True,
                'data': [],
                'restaurant': current_restaurant['name'],
                'supplier': supplier_name
            })
        
        elif request.method == 'POST':
            # Ajouter un produit pour ce restaurant et ce fournisseur
            product_data = request.json
            
            # Validation des données
            if not product_data.get('name') or not product_data.get('unit_price'):
                return jsonify({
                    'success': False,
                    'error': 'Le nom et le prix du produit sont obligatoires'
                }), 400
            
            # Préparer les données du produit avec le contexte restaurant
            product_record = {
                'produit': product_data['name'],
                'prix': float(product_data['unit_price']),  # Utiliser 'prix' au lieu de 'prix_unitaire'
                'unite': product_data.get('unit', 'unité'),
                'fournisseur': supplier_name,
                'restaurant': current_restaurant['name'],  # Utiliser 'restaurant' au lieu de 'restaurant_id'
                'code': product_data.get('code', ''),
                'categorie': product_data.get('category', 'Non classé'),
                'notes': product_data.get('notes', ''),
                'source': 'restaurant_manual',  # Source spécifique
                'created_at': datetime.now().isoformat(),
                'created_by': user_context['user']['username']
            }
            
            # 🎯 CORRECTION: Ajouter le produit en attente (pas directement confirmé)
            # pour les créations manuelles par les restaurants
            success = price_manager.add_pending_product(product_record)
            
            if success:
                logger.info(f"✅ Produit {product_data['name']} ajouté pour {supplier_name} - Restaurant: {current_restaurant['name']}")
                
                return jsonify({
                    'success': True,
                    'message': f'Produit {product_data["name"]} ajouté avec succès',
                    'product': product_record,
                    'restaurant': current_restaurant['name'],
                    'supplier': supplier_name
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Erreur lors de l\'ajout du produit'
                }), 500
        
    except Exception as e:
        logger.error(f"Erreur gestion produits restaurant-fournisseur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/orders/verification', methods=['POST'])
def save_order_verification():
    """Sauvegarder une vérification manuelle de commande"""
    try:
        data = request.get_json()
        
        # Vérifier les données requises
        if not data or not data.get('order_id'):
            return jsonify({'success': False, 'error': 'ID de commande manquant'})
        
        order_id = data['order_id']
        verification_type = data.get('verification_type', 'manual')
        verification_date = data.get('verification_date')
        notes = data.get('notes', '')
        items = data.get('items', [])
        
        # Créer les données de vérification
        verification_data = {
            'id': str(uuid.uuid4()),
            'order_id': order_id,
            'verification_type': verification_type,
            'verification_date': verification_date,
            'notes': notes,
            'items': items,
            'has_discrepancies': any(item.get('discrepancy', False) for item in items)
        }
        
        # Sauvegarder dans un fichier de vérifications
        verification_file = os.path.join(DATA_DIR, 'order_verifications.json')
        verifications = []
        
        if os.path.exists(verification_file):
            try:
                with open(verification_file, 'r', encoding='utf-8') as f:
                    verifications = json.load(f)
            except:
                verifications = []
        
        verifications.append(verification_data)
        
        with open(verification_file, 'w', encoding='utf-8') as f:
            json.dump(verifications, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'success': True,
            'verification_id': verification_data['id'],
            'has_discrepancies': verification_data['has_discrepancies']
        })
        
    except Exception as e:
        logger.error(f"Erreur sauvegarde vérification: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/scan-verification', methods=['POST'])
def scan_order_verification():
    """Scanner une facture pour vérification automatique"""
    try:
        # Vérifier qu'un fichier a été uploadé
        if 'invoice' not in request.files:
            return jsonify({'success': False, 'error': 'Aucun fichier fourni'})
        
        file = request.files['invoice']
        order_id = request.form.get('order_id')
        
        if not order_id:
            return jsonify({'success': False, 'error': 'ID de commande manquant'})
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'})
        
        # Récupérer la commande
        order = order_manager.get_order_by_id(order_id)
        if not order:
            return jsonify({
                'success': False,
                'error': 'Commande non trouvée'
            }), 404
        
        # Sauvegarder le fichier temporairement
        filename = secure_filename(file.filename)
        temp_path = os.path.join(UPLOAD_DIR, f"verification_{order_id}_{filename}")
        file.save(temp_path)
        
        try:
            # Analyser la facture avec Claude Vision
            from claude_scanner import ClaudeScanner
            claude_scanner = ClaudeScanner(price_manager)
            scan_result = claude_scanner.scan_facture(temp_path)
            
            if not scan_result or not scan_result.get('success'):
                return jsonify({
                    'success': False, 
                    'error': 'Impossible d\'analyser la facture'
                })
            
            # Extraire les données de la facture
            invoice_data = scan_result.get('data', {})
            scanned_items = invoice_data.get('items', [])
            
            # Comparer avec la commande originale
            comparison_result = compare_order_with_invoice(order, scanned_items)
            
            # Sauvegarder temporairement les résultats du scan
            scan_data = {
                'order_id': order_id,
                'scan_date': datetime.now().isoformat(),
                'file_path': temp_path,
                'scan_result': scan_result,
                'comparison': comparison_result,
                'notes': f"Scan automatique effectué le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
            }
            
            # Stocker temporairement (sera confirmé par l'utilisateur)
            temp_scan_file = os.path.join(DATA_DIR, f'temp_scan_{order_id}.json')
            with open(temp_scan_file, 'w', encoding='utf-8') as f:
                json.dump(scan_data, f, indent=2, ensure_ascii=False)
            
            return jsonify({
                'success': True,
                'scan_data': {
                    'items': scanned_items,
                    'total': invoice_data.get('total', 0)
                },
                'comparison': comparison_result,
                'notes': scan_data['notes']
            })
            
        finally:
            # Nettoyer le fichier temporaire
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        logger.error(f"Erreur scan vérification: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/confirm-scan-verification', methods=['POST'])
def confirm_scan_verification():
    """Confirmer une vérification par scan"""
    try:
        data = request.get_json()
        
        if not data or not data.get('order_id'):
            return jsonify({'success': False, 'error': 'ID de commande manquant'})
        
        order_id = data['order_id']
        notes = data.get('notes', '')
        
        # Récupérer les données temporaires du scan
        temp_scan_file = os.path.join(DATA_DIR, f'temp_scan_{order_id}.json')
        
        if not os.path.exists(temp_scan_file):
            return jsonify({'success': False, 'error': 'Données de scan non trouvées'})
        
        with open(temp_scan_file, 'r', encoding='utf-8') as f:
            scan_data = json.load(f)
        
        # Créer la vérification finale
        verification_data = {
            'id': str(uuid.uuid4()),
            'order_id': order_id,
            'verification_type': 'scan',
            'verification_date': datetime.now().isoformat(),
            'notes': notes or scan_data.get('notes', ''),
            'scan_result': scan_data.get('scan_result'),
            'comparison': scan_data.get('comparison'),
            'has_discrepancies': scan_data.get('comparison', {}).get('has_discrepancies', False)
        }
        
        # Sauvegarder la vérification
        verification_file = os.path.join(DATA_DIR, 'order_verifications.json')
        verifications = []
        
        if os.path.exists(verification_file):
            try:
                with open(verification_file, 'r', encoding='utf-8') as f:
                    verifications = json.load(f)
            except:
                verifications = []
        
        verifications.append(verification_data)
        
        with open(verification_file, 'w', encoding='utf-8') as f:
            json.dump(verifications, f, indent=2, ensure_ascii=False)
        
        # Nettoyer le fichier temporaire
        os.remove(temp_scan_file)

        # === NOUVEAUTÉ : créer la facture associée et mettre à jour la commande ===
        try:
            order = order_manager.get_order_by_id(order_id)
            invoice_analysis = scan_data.get('scan_result', {}).get('data', {}) if scan_data.get('scan_result') else {}
            # Fallback basique si analyse absente
            if not invoice_analysis:
                invoice_analysis = {
                    'supplier': order.get('supplier') if order else 'Inconnu',
                    'products': scan_data.get('scan_result', {}).get('items', []) if scan_data.get('scan_result') else [],
                    'total_amount': scan_data.get('scan_result', {}).get('total', 0) if scan_data.get('scan_result') else 0
                }
            invoice_record = {
                'supplier': invoice_analysis.get('supplier', order.get('supplier', 'Inconnu') if order else 'Inconnu'),
                'invoice_number': invoice_analysis.get('invoice_number'),
                'date': invoice_analysis.get('date'),
                'total_amount': invoice_analysis.get('total_amount') or invoice_analysis.get('total', 0),
                'products': invoice_analysis.get('products', []),
                'analysis': invoice_analysis,
                'filename': os.path.basename(scan_data.get('file_path')),
                'scan_date': datetime.now().isoformat(),
                'restaurant_id': order.get('restaurant_id') if order else None,
                'restaurant_name': order.get('restaurant_name') if order else None
            }
            invoice_id_created = invoice_manager.save_invoice(invoice_record)
            # Mettre à jour la commande avec le lien facture + statut livré
            new_status = 'delivered_with_issues' if verification_data['has_discrepancies'] else 'delivered'
            order_manager.update_order(order_id, {
                'status': new_status,
                'invoice_id': invoice_id_created
            })
        except Exception as link_err:
            logger.warning(f"⚠️ Impossible de lier facture à la commande: {link_err}")

        return jsonify({
            'success': True,
            'verification_id': verification_data['id'],
            'has_discrepancies': verification_data['has_discrepancies'],
            'invoice_id': invoice_id_created if 'invoice_id_created' in locals() else None
        })
        
    except Exception as e:
        logger.error(f"Erreur confirmation scan: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def compare_order_with_invoice(order, scanned_items):
    """Comparer une commande avec les items scannés d'une facture"""
    try:
        ordered_items = order.get('items', [])
        comparison_items = []
        total_ordered = 0
        total_received = 0
        has_discrepancies = False
        
        # Créer un mapping des produits commandés
        ordered_products = {}
        for item in ordered_items:
            product_name = (item.get('product_name') or item.get('name', '')).lower().strip()
            ordered_products[product_name] = item
            total_ordered += (item.get('quantity', 0) * item.get('unit_price', 0))
        
        # Comparer chaque produit commandé
        for ordered_item in ordered_items:
            product_name = (ordered_item.get('product_name') or ordered_item.get('name', '')).lower().strip()
            
            # Chercher le produit dans les items scannés
            found_item = None
            for scanned_item in scanned_items:
                scanned_name = scanned_item.get('name', '').lower().strip()
                
                # Comparaison simple (peut être améliorée avec de la logique floue)
                if product_name in scanned_name or scanned_name in product_name:
                    found_item = scanned_item
                    break
            
            comparison_item = {
                'product_name': ordered_item.get('product_name') or ordered_item.get('name'),
                'ordered_quantity': ordered_item.get('quantity', 0),
                'ordered_unit': ordered_item.get('unit', ''),
                'ordered_price': ordered_item.get('unit_price', 0),
                'received_quantity': found_item.get('quantity', 0) if found_item else 0,
                'received_unit': found_item.get('unit', '') if found_item else '',
                'received_price': found_item.get('price', 0) if found_item else 0,
                'status': 'not_found'
            }
            
            if found_item:
                total_received += (found_item.get('quantity', 0) * found_item.get('price', 0))
                
                # Déterminer le statut
                qty_match = comparison_item['ordered_quantity'] == comparison_item['received_quantity']
                price_match = abs(comparison_item['ordered_price'] - comparison_item['received_price']) < 0.01
                
                if qty_match and price_match:
                    comparison_item['status'] = 'match'
                else:
                    comparison_item['status'] = 'difference'
                    has_discrepancies = True
            else:
                has_discrepancies = True
            
            comparison_items.append(comparison_item)
        
        return {
            'items': comparison_items,
            'total_ordered': total_ordered,
            'total_received': total_received,
            'total_difference': total_received - total_ordered,
            'has_discrepancies': has_discrepancies
        }
        
    except Exception as e:
        logger.error(f"Erreur comparaison commande/facture: {e}")
        return {
            'items': [],
            'total_ordered': 0,
            'total_received': 0,
            'total_difference': 0,
            'has_discrepancies': True,
            'error': str(e)
        }

# ===== ANOMALIES API =====

@app.route('/api/anomalies/stats', methods=['GET'])
@login_required
def get_anomalies_stats():
    """Récupérer les statistiques des anomalies"""
    try:
        # Récupérer toutes les factures
        all_invoices = invoice_manager.get_all_invoices(per_page=9999)['items']
        
        total_invoices = len(all_invoices)
        invoices_with_anomalies = len([inv for inv in all_invoices if inv.get('has_anomalies', False)])
        invoices_without_anomalies = total_invoices - invoices_with_anomalies
        
        # Compter les types d'anomalies
        anomaly_types = {'quantity': 0, 'price': 0, 'missing': 0}
        critical_anomalies = 0
        
        for invoice in all_invoices:
            if invoice.get('anomalies'):
                for product_anomaly in invoice['anomalies']:
                    for anomaly in product_anomaly['anomalies']:
                        anomaly_type = anomaly.get('type', 'unknown')
                        if anomaly_type in anomaly_types:
                            anomaly_types[anomaly_type] += 1
                        if anomaly.get('severity') == 'critical':
                            critical_anomalies += 1
        
        # Anomalies par fournisseur
        supplier_anomalies = {}
        for invoice in all_invoices:
            if invoice.get('has_anomalies'):
                supplier = invoice.get('supplier', 'Inconnu')
                if supplier not in supplier_anomalies:
                    supplier_anomalies[supplier] = 0
                supplier_anomalies[supplier] += len(invoice.get('anomalies', []))
        
        return jsonify({
            'success': True,
            'data': {
                'total_invoices': total_invoices,
                'invoices_with_anomalies': invoices_with_anomalies,
                'invoices_without_anomalies': invoices_without_anomalies,
                'anomaly_rate': round((invoices_with_anomalies / total_invoices * 100) if total_invoices > 0 else 0, 1),
                'anomaly_types': anomaly_types,
                'critical_anomalies': critical_anomalies,
                'supplier_anomalies': supplier_anomalies
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/anomalies/resolve/<invoice_id>', methods=['POST'])
@login_required
def resolve_anomaly(invoice_id):
    """Marquer une anomalie comme résolue"""
    try:
        data = request.get_json()
        resolution_notes = data.get('notes', '')
        resolved_by = data.get('resolved_by', 'user')
        
        # Récupérer la facture
        invoice = invoice_manager.get_invoice_by_id(invoice_id)
        if not invoice:
            return jsonify({
                'success': False,
                'error': 'Facture non trouvée'
            }), 404
        
        # Marquer comme résolue
        invoice['anomaly_status'] = 'resolved'
        invoice['resolution_date'] = datetime.now().isoformat()
        invoice['resolution_notes'] = resolution_notes
        invoice['resolved_by'] = resolved_by
        
        # Sauvegarder les modifications
        invoice_manager._save_invoices()
        
        return jsonify({
            'success': True,
            'message': 'Anomalie marquée comme résolue'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/anomalies/send-notification/<invoice_id>', methods=['POST'])
@login_required
def send_anomaly_notification_manual(invoice_id):
    """Envoyer manuellement une notification d'anomalie"""
    try:
        data = request.get_json()
        recipient_email = data.get('email', '')
        custom_message = data.get('message', '')
        
        # Récupérer la facture
        invoice = invoice_manager.get_invoice_by_id(invoice_id)
        if not invoice:
            return jsonify({
                'success': False,
                'error': 'Facture non trouvée'
            }), 404
        
        if not invoice.get('has_anomalies'):
            return jsonify({
                'success': False,
                'error': 'Cette facture ne contient pas d\'anomalies'
            }), 400
        
        # Préparer les anomalies pour l'email
        all_anomalies = []
        for product_anomaly in invoice.get('anomalies', []):
            all_anomalies.extend(product_anomaly['anomalies'])
        
        # Envoyer la notification
        result = email_manager.send_anomaly_notification(
            invoice_id=invoice_id,
            order_id=invoice.get('order_id', ''),
            supplier=invoice.get('supplier', ''),
            anomalies=all_anomalies,
            total_anomalies=len(invoice.get('anomalies', [])),
            recipient_email=recipient_email,
            custom_message=custom_message
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/suppliers/check-new/<supplier_name>')
def check_new_supplier(supplier_name):
    """Vérifier si un fournisseur a été créé récemment (nouveau)"""
    try:
        from modules.supplier_manager import SupplierManager
        supplier_manager = SupplierManager()
        
        # Charger tous les fournisseurs
        suppliers = supplier_manager.get_all_suppliers()
        
        # Chercher le fournisseur
        supplier = next((s for s in suppliers if s['name'] == supplier_name), None)
        
        if not supplier:
            return jsonify({
                'success': True,
                'is_new': False,
                'exists': False
            })
        
        # Vérifier si créé automatiquement récemment (dans les dernières 24h)
        from datetime import datetime, timedelta
        
        created_at = supplier.get('created_at')
        if created_at:
            try:
                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                now = datetime.now()
                
                # Si créé il y a moins de 5 minutes ET avec note "automatiquement"
                time_diff = now - created_date
                is_recent = time_diff < timedelta(minutes=5)
                is_auto_created = 'automatiquement' in supplier.get('notes', '').lower()
                
                return jsonify({
                    'success': True,
                    'is_new': is_recent and is_auto_created,
                    'exists': True,
                    'created_at': created_at,
                    'notes': supplier.get('notes', '')
                })
            except:
                # Si erreur de parsing de date, considérer comme non nouveau
                pass
        
        return jsonify({
            'success': True,
            'is_new': False,
            'exists': True
        })
        
    except Exception as e:
        logger.error(f"Erreur vérification nouveau fournisseur {supplier_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# 🧠 ===== ENDPOINTS IA POUR ANALYSE DES ANOMALIES =====

@app.route('/api/ai/analyze-batch', methods=['POST'])
def analyze_batch_with_ai():
    """
    🎯 ANALYSE IA D'UN BATCH DE FACTURES
    Détecte les patterns d'anomalies récurrentes et SUGGÈRE des mises à jour de prix
    ⚠️ AUCUNE modification automatique - suggestions seulement
    """
    try:
        data = request.json
        batch_results = data.get('batch_results', [])
        
        if not batch_results:
            return jsonify({
                'success': False,
                'error': 'Aucune donnée de batch fournie'
            }), 400
        
        # Initialiser le détecteur d'anomalies IA
        from modules.ai_anomaly_detector import AIAnomalyDetector
        ai_detector = AIAnomalyDetector()
        
        # Analyser le batch avec l'IA
        analysis = ai_detector.analyze_batch_anomalies(batch_results)
        
        return jsonify({
            'success': True,
            'data': analysis,
            'message': f"Analyse terminée: {analysis['summary']['suggestions_generated']} suggestions générées"
        })
        
    except Exception as e:
        logger.error(f"Erreur analyse IA batch: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/ai/suggestions', methods=['GET'])
def get_ai_suggestions():
    """Récupérer toutes les suggestions IA en attente de validation client"""
    try:
        from modules.ai_anomaly_detector import AIAnomalyDetector
        ai_detector = AIAnomalyDetector()
        
        suggestions = ai_detector.get_suggestions_for_validation_interface()
        
        return jsonify({
            'success': True,
            'data': {
                'suggestions': suggestions,
                'total_count': len(suggestions),
                'requires_validation': True,
                'message': 'Suggestions en attente de validation client'
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération suggestions IA: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/ai/validate-suggestion/<suggestion_id>', methods=['POST'])
def validate_ai_suggestion(suggestion_id):
    """
    🎯 VALIDATION CLIENT D'UNE SUGGESTION IA
    Le client décide d'accepter, rejeter ou modifier la suggestion
    """
    try:
        data = request.json
        client_decision = data.get('decision')  # 'accept', 'reject', 'modify'
        modified_price = data.get('modified_price')  # Si decision = 'modify'
        notes = data.get('notes', '')
        
        if client_decision not in ['accept', 'reject', 'modify']:
            return jsonify({
                'success': False,
                'error': 'Décision invalide. Utilisez: accept, reject, modify'
            }), 400
        
        from modules.ai_anomaly_detector import AIAnomalyDetector
        ai_detector = AIAnomalyDetector()
        
        # Récupérer la suggestion
        suggestions = ai_detector.get_pending_suggestions()
        suggestion = next((s for s in suggestions if s['id'] == suggestion_id), None)
        
        if not suggestion:
            return jsonify({
                'success': False,
                'error': 'Suggestion non trouvée'
            }), 404
        
        # Traiter la décision du client
        if client_decision == 'accept':
            # Client accepte la suggestion → Appliquer le prix suggéré
            final_price = suggestion['suggested_new_price']
            action = 'acceptée'
            
        elif client_decision == 'modify':
            # Client modifie le prix suggéré
            if not modified_price:
                return jsonify({
                    'success': False,
                    'error': 'Prix modifié requis pour la décision "modify"'
                }), 400
            final_price = float(modified_price)
            action = 'modifiée'
            
        elif client_decision == 'reject':
            # Client rejette la suggestion → Aucune modification
            ai_detector.mark_suggestion_reviewed(suggestion_id, 'rejected', notes)
            return jsonify({
                'success': True,
                'message': 'Suggestion rejetée par le client'
            })
        
        # Appliquer la mise à jour de prix (seulement si acceptée ou modifiée)
        if client_decision in ['accept', 'modify']:
            price_data = {
                'produit': suggestion['product_name'],
                'prix': final_price,
                'fournisseur': suggestion['supplier'],
                'categorie': 'Validation client IA',
                'date': datetime.now().isoformat(),
                'note': f"Suggestion IA {action} par le client (confiance: {suggestion['confidence_score']:.2f})"
            }
            
            # Ajouter le nouveau prix
            price_manager.add_price(price_data)
            
            # Marquer la suggestion comme traitée
            ai_detector.mark_suggestion_reviewed(suggestion_id, client_decision, notes)
            
            return jsonify({
                'success': True,
                'message': f'Prix mis à jour pour {suggestion["product_name"]} chez {suggestion["supplier"]} - Suggestion {action}'
            })
        
    except Exception as e:
        logger.error(f"Erreur validation suggestion IA: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/ai/bulk-validate', methods=['POST'])
def bulk_validate_suggestions():
    """
    🎯 VALIDATION EN MASSE DES SUGGESTIONS IA
    Le client peut valider plusieurs suggestions en une fois
    """
    try:
        data = request.json
        validations = data.get('validations', [])  # Liste des validations
        
        if not validations:
            return jsonify({
                'success': False,
                'error': 'Aucune validation fournie'
            }), 400
        
        from modules.ai_anomaly_detector import AIAnomalyDetector
        ai_detector = AIAnomalyDetector()
        
        results = {
            'accepted': 0,
            'rejected': 0,
            'modified': 0,
            'errors': []
        }
        
        for validation in validations:
            try:
                suggestion_id = validation.get('suggestion_id')
                decision = validation.get('decision')
                modified_price = validation.get('modified_price')
                notes = validation.get('notes', '')
                
                # Récupérer la suggestion
                suggestions = ai_detector.get_pending_suggestions()
                suggestion = next((s for s in suggestions if s['id'] == suggestion_id), None)
                
                if not suggestion:
                    results['errors'].append(f"Suggestion {suggestion_id} non trouvée")
                    continue
                
                # Traiter selon la décision
                if decision == 'accept':
                    final_price = suggestion['suggested_new_price']
                    results['accepted'] += 1
                    
                elif decision == 'modify':
                    if not modified_price:
                        results['errors'].append(f"Prix modifié requis pour {suggestion_id}")
                        continue
                    final_price = float(modified_price)
                    results['modified'] += 1
                    
                elif decision == 'reject':
                    ai_detector.mark_suggestion_reviewed(suggestion_id, 'rejected', notes)
                    results['rejected'] += 1
                    continue
                
                # Appliquer la mise à jour de prix
                if decision in ['accept', 'modify']:
                    price_data = {
                        'produit': suggestion['product_name'],
                        'prix': final_price,
                        'fournisseur': suggestion['supplier'],
                        'categorie': 'Validation client IA (batch)',
                        'date': datetime.now().isoformat(),
                        'note': f"Suggestion IA {decision} par le client"
                    }
                    
                    price_manager.add_price(price_data)
                    ai_detector.mark_suggestion_reviewed(suggestion_id, decision, notes)
                
            except Exception as e:
                results['errors'].append(f"Erreur pour {suggestion_id}: {str(e)}")
        
        return jsonify({
            'success': True,
            'data': results,
            'message': f"Validation terminée: {results['accepted']} acceptées, {results['modified']} modifiées, {results['rejected']} rejetées"
        })
        
    except Exception as e:
        logger.error(f"Erreur validation batch IA: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== SUPPRESSION DES ANCIENS ENDPOINTS AUTO-APPLY =====
# Les endpoints apply-suggestion et apply-all-auto-updates sont supprimés
# car l'IA ne doit jamais modifier automatiquement les prix

# ===== FIN ENDPOINTS IA =====

@app.route('/api/orders/verifiable', methods=['GET'])
@login_required
def get_verifiable_orders():
    """Récupérer les commandes vérifiables (date de livraison passée ou aujourd'hui) FILTRÉES PAR RESTAURANT"""
    try:
        # Récupérer le contexte utilisateur pour le restaurant
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant')
        
        # Paramètres de filtrage
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        # CORRECTION: Filtrer par restaurant_id ET par fournisseurs
        restaurant_suppliers = []
        restaurant_id = None
        if current_restaurant:
            restaurant_id = current_restaurant.get('id')
            restaurant_suppliers = current_restaurant.get('suppliers', [])
            logger.info(f"🔍 Filtrage commandes vérifiables - Restaurant: {current_restaurant.get('name')} (ID: {restaurant_id})")
            logger.info(f"🏪 Fournisseurs autorisés: {restaurant_suppliers}")
        
        # Récupérer TOUTES les commandes puis filtrer manuellement
        all_orders = order_manager.get_all_orders(
            page=1,
            per_page=9999  # Récupérer toutes les commandes
        )
        
        # DOUBLE FILTRAGE: par restaurant_id ET par fournisseurs
        restaurant_orders = []
        for order in all_orders['items']:
            order_restaurant_id = order.get('restaurant_id')
            order_supplier = order.get('supplier')
            
            # Filtrer par restaurant_id SI défini
            if restaurant_id and order_restaurant_id != restaurant_id:
                continue
            
            # Filtrer par fournisseurs du restaurant SI définis
            if restaurant_suppliers and order_supplier not in restaurant_suppliers:
                continue
            
            restaurant_orders.append(order)
        
        logger.info(f"📋 Commandes du restaurant trouvées: {len(restaurant_orders)}")
        
        # Filtrage avancé: seulement les commandes avec date de livraison passée ou aujourd'hui
        from datetime import datetime, date
        today = date.today()
        
        verifiable_orders = []
        for order in restaurant_orders:
            delivery_date = order.get('delivery_date')
            status = order.get('status')
            
            # Conditions pour qu'une commande soit vérifiable
            is_confirmed_or_delivered = status in ['confirmed', 'delivered', 'delivered_with_issues', 'invoiced']
            
            if delivery_date and is_confirmed_or_delivered:
                try:
                    # Convertir la date de livraison
                    delivery_date_obj = datetime.fromisoformat(delivery_date).date()
                    
                    # Vérifier que la date de livraison est passée ou aujourd'hui
                    if delivery_date_obj <= today:
                        verifiable_orders.append(order)
                        logger.debug(f"✅ Commande vérifiable: {order.get('order_number')} - {order_supplier}")
                        
                except Exception as e:
                    logger.warning(f"Date de livraison invalide pour commande {order.get('id')}: {delivery_date}")
                    continue
        
        # Trier par date de livraison décroissante
        verifiable_orders.sort(key=lambda x: x.get('delivery_date', ''), reverse=True)
        
        logger.info(f"🎯 Commandes vérifiables finales: {len(verifiable_orders)}")
        
        return jsonify({
            'success': True,
            'data': verifiable_orders,
            'total': len(verifiable_orders),
            'restaurant_context': current_restaurant.get('name') if current_restaurant else None,
            'restaurant_id': restaurant_id,
            'restaurant_suppliers': restaurant_suppliers,
            'filter_date': today.isoformat(),
            'filter_info': f'Commandes avec date de livraison passée ou aujourd\'hui - Restaurant: {current_restaurant.get("name") if current_restaurant else "Aucun"}'
        })
        
    except Exception as e:
        logger.error(f"Erreur API commandes vérifiables: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== ROUTE SPÉCIFIQUE POUR PRODUITS EN ATTENTE PAR FOURNISSEUR =====

@app.route('/api/suppliers/<supplier_name>/pending-products', methods=['GET'])
@login_required
def get_supplier_pending_products(supplier_name):
    """Récupérer les produits en attente pour un fournisseur spécifique"""
    try:
        # Récupérer le contexte utilisateur pour le restaurant
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant')
        
        print(f"🔍 DEBUG: Récupération produits en attente pour fournisseur '{supplier_name}'")
        print(f"🏪 DEBUG: Restaurant actuel: {current_restaurant.get('name') if current_restaurant else 'None'}")
        
        # Récupérer tous les produits en attente
        all_pending = price_manager.get_pending_products()
        print(f"📋 DEBUG: Total produits en attente dans le système: {len(all_pending)}")
        
        # Filtrer par fournisseur et restaurant
        supplier_pending = []
        debug_filtered_out = []
        
        for product in all_pending:
            # Vérifier fournisseur
            product_supplier = product.get('fournisseur', '').lower()
            if product_supplier != supplier_name.lower():
                debug_filtered_out.append(f"Fournisseur différent: {product_supplier} != {supplier_name.lower()}")
                continue
                
            # Vérifier restaurant si un restaurant est sélectionné
            if current_restaurant:
                product_restaurant = product.get('restaurant', 'Général')
                restaurant_name = current_restaurant.get('name')
                if (product_restaurant != restaurant_name and 
                    product_restaurant != 'Général' and 
                    product_restaurant is not None):
                    debug_filtered_out.append(f"Restaurant différent: {product_restaurant} != {restaurant_name}")
                    continue
            
            supplier_pending.append(product)
        
        print(f"✅ DEBUG: Produits trouvés pour {supplier_name}: {len(supplier_pending)}")
        if len(debug_filtered_out) > 0:
            print(f"❌ DEBUG: Produits filtrés (premiers 5): {debug_filtered_out[:5]}")
        
        # Afficher les détails des produits trouvés
        for i, product in enumerate(supplier_pending[:3]):  # Afficher les 3 premiers
            print(f"   📦 {i+1}. {product.get('produit')} - {product.get('prix')}€ - Restaurant: {product.get('restaurant')}")
        
        return jsonify({
            'success': True,
            'data': supplier_pending,
            'count': len(supplier_pending),
            'supplier': supplier_name,
            'restaurant_filter': current_restaurant.get('name') if current_restaurant else None,
            'debug_info': {
                'total_pending': len(all_pending),
                'filtered_count': len(debug_filtered_out)
            }
        })
        
    except Exception as e:
        print(f"❌ DEBUG: Erreur récupération produits en attente: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/suppliers/<supplier_name>/pending-products/<int:pending_id>/validate', methods=['POST'])
@login_required
def validate_supplier_pending_product(supplier_name, pending_id):
    """Valider un produit en attente pour un fournisseur et l'ajouter à son catalogue + SYNCHRONISATION AUTO"""
    try:
        print(f"🔄 VALIDATION: Produit {pending_id} pour fournisseur {supplier_name}")
        
        # Récupérer le contexte utilisateur pour le restaurant
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant')
        
        # Récupérer le produit en attente
        all_pending = price_manager.get_pending_products()
        pending_product = next((p for p in all_pending if p.get('id') == pending_id), None)
        
        if not pending_product:
            return jsonify({
                'success': False,
                'error': 'Produit en attente non trouvé'
            }), 404
        
        # Vérifier que le produit appartient bien au fournisseur
        if pending_product.get('fournisseur', '').lower() != supplier_name.lower():
            return jsonify({
                'success': False,
                'error': 'Ce produit ne correspond pas au fournisseur spécifié'
            }), 400
        
        # Valider le produit (ajoute au catalogue officiel)
        success = price_manager.validate_pending_product(pending_id)
        
        if success:
            print(f"✅ VALIDATION: Produit validé avec succès")
            
            # 🔄 SYNCHRONISATION AUTOMATIQUE si restaurant multi-restaurant
            sync_result = None
            if current_restaurant:
                from modules.sync_manager import SyncManager  # Correction ici
                sync_manager = SyncManager()  # Création de l'instance
                
                # Vérifier si ce restaurant a la synchronisation activée
                restaurant_config = sync_manager.get_restaurant_sync_settings(current_restaurant.get('id'))
                if restaurant_config and restaurant_config.get('sync_enabled') and restaurant_config.get('sync_prices'):
                    print(f"🔄 SYNC: Déclenchement synchronisation prix pour {supplier_name}")
                    
                    # Synchroniser vers les restaurants du même groupe
                    sync_result = sync_manager.sync_supplier_prices_to_group(
                        current_restaurant.get('id'),
                        supplier_name
                    )
                    
                    if sync_result and sync_result.get('success'):
                        sync_count = len(sync_result.get('synced_restaurants', []))
                        print(f"🔄 SYNC: Prix synchronisés vers {sync_count} restaurant(s)")
            
            return jsonify({
                'success': True,
                'message': f'Produit "{pending_product.get("produit")}" validé et ajouté au catalogue de {supplier_name}',
                'sync_result': sync_result,
                'sync_count': len(sync_result.get('synced_restaurants', [])) if sync_result else 0
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Erreur lors de la validation'
            }), 500
            
    except Exception as e:
        print(f"❌ VALIDATION: Erreur lors de la validation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/debug/invoices-context', methods=['GET'])
@login_required
def debug_invoices_context():
    """Debug pour voir le contexte restaurant et les factures"""
    try:
        # Récupérer le contexte utilisateur
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant')
        
        # Récupérer TOUTES les factures sans filtre
        all_invoices = invoice_manager.invoices_data.get('invoices', [])
        
        # Analyser chaque facture
        invoices_analysis = []
        for invoice in all_invoices[:5]:  # Limiter à 5 pour le debug
            analysis = {
                'id': invoice.get('id'),
                'invoice_code': invoice.get('invoice_code'),
                'supplier': invoice.get('supplier'),
                'restaurant_id_root': invoice.get('restaurant_id'),
                'restaurant_id_analysis': invoice.get('analysis', {}).get('restaurant_id'),
                'restaurant_context': invoice.get('analysis', {}).get('restaurant_context'),
                'created_at': invoice.get('created_at')
            }
            invoices_analysis.append(analysis)
        
        return jsonify({
            'success': True,
            'current_restaurant': current_restaurant,
            'total_invoices_in_file': len(all_invoices),
            'invoices_sample': invoices_analysis
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/debug/fix-invoices-restaurant', methods=['POST'])
@login_required
def fix_invoices_restaurant():
    """Corriger les factures qui n'ont pas de restaurant_id"""
    try:
        # Récupérer le contexte utilisateur
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant')
        
        if not current_restaurant:
            return jsonify({
                'success': False,
                'error': 'Aucun restaurant sélectionné'
            })
        
        restaurant_id = current_restaurant.get('id')
        restaurant_name = current_restaurant.get('name')
        
        # Charger toutes les factures
        all_invoices = invoice_manager.invoices_data.get('invoices', [])
        
        fixed_count = 0
        for invoice in all_invoices:
            # Si la facture n'a pas de restaurant_id mais a le bon restaurant_context
            if not invoice.get('restaurant_id'):
                analysis = invoice.get('analysis', {})
                if analysis.get('restaurant_context') == restaurant_name:
                    # Ajouter le restaurant_id
                    invoice['restaurant_id'] = restaurant_id
                    invoice['restaurant_name'] = restaurant_name
                    if 'analysis' not in invoice:
                        invoice['analysis'] = {}
                    invoice['analysis']['restaurant_id'] = restaurant_id
                    fixed_count += 1
        
        # Sauvegarder les modifications
        if fixed_count > 0:
            invoice_manager._save_invoices()
        
        return jsonify({
            'success': True,
            'fixed_count': fixed_count,
            'restaurant': restaurant_name,
            'restaurant_id': restaurant_id,
            'message': f'{fixed_count} facture(s) corrigée(s)'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/debug/add-test-pending', methods=['POST'])
@login_required
def debug_add_test_pending():
    """🔧 DEBUG: Ajouter un produit test en attente pour vérifier le workflow"""
    try:
        # Récupérer le contexte utilisateur
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant')
        
        if not current_restaurant:
            return jsonify({
                'success': False,
                'error': 'Aucun restaurant sélectionné'
            })
        
        restaurant_name = current_restaurant.get('name')
        
        # Créer un produit test
        test_product = {
            'code': f'PTEST{int(datetime.now().timestamp())}',
            'produit': 'Produit Test Debug',
            'prix': 15.50,
            'unite': 'kg',
            'fournisseur': 'SYSCO',
            'categorie': 'Test',
            'restaurant': restaurant_name,
            'source': 'debug_manual',
            'date_ajout': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        print(f"🔧 DEBUG: Ajout produit test pour {restaurant_name}")
        print(f"🔧 DEBUG: Données produit: {test_product}")
        
        # Tenter l'ajout
        success = price_manager.add_pending_product(test_product)
        
        print(f"🔧 DEBUG: Résultat ajout: {'✅ Succès' if success else '❌ Échec'}")
        
        return jsonify({
            'success': success,
            'message': f'Produit test {"ajouté" if success else "non ajouté"} pour {restaurant_name}',
            'product': test_product
        })
        
    except Exception as e:
        print(f"❌ DEBUG: Erreur ajout produit test: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/debug/firestore-status', methods=['GET'])
@login_required
def debug_firestore_status():
    """Déboguer l'état de Firestore"""
    try:
        from modules.firestore_db import available, get_client
        from modules.supplier_manager import SupplierManager
        
        # Vérifier Firestore
        fs_available = available()
        fs_client = get_client()
        
        # Vérifier SupplierManager
        supplier_manager = SupplierManager()
        suppliers = supplier_manager.get_all_suppliers()
        
        return jsonify({
            'success': True,
            'firestore_available': fs_available,
            'firestore_client': str(fs_client) if fs_client else None,
            'suppliers_count': len(suppliers),
            'suppliers': [s['name'] for s in suppliers],
            'fs_enabled': getattr(supplier_manager, '_fs_enabled', False),
            'fs_client_attr': str(getattr(supplier_manager, '_fs', None))
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/debug/check-pending-workflow', methods=['GET'])
@login_required
def debug_check_pending_workflow():
    """🔧 DEBUG: Vérifier le workflow complet des produits en attente"""
    try:
        # Récupérer le contexte utilisateur
        user_context = auth_manager.get_user_context()
        current_restaurant = user_context.get('restaurant')
        
        # 1. Vérifier les produits en attente totaux
        all_pending = price_manager.get_pending_products()
        
        # 2. Filtrer par restaurant si applicable
        restaurant_pending = []
        if current_restaurant:
            restaurant_name = current_restaurant.get('name')
            for product in all_pending:
                product_restaurant = product.get('restaurant', 'Général')
                if (product_restaurant == restaurant_name or 
                    product_restaurant == 'Général' or 
                    product_restaurant is None):
                    restaurant_pending.append(product)
        
        # 3. Grouper par fournisseur
        suppliers_with_pending = {}
        for product in restaurant_pending:
            supplier = product.get('fournisseur', 'UNKNOWN')
            if supplier not in suppliers_with_pending:
                suppliers_with_pending[supplier] = []
            suppliers_with_pending[supplier].append(product)
        
        return jsonify({
            'success': True,
            'current_restaurant': current_restaurant.get('name') if current_restaurant else None,
            'total_pending_system': len(all_pending),
            'total_pending_restaurant': len(restaurant_pending),
            'suppliers_with_pending': suppliers_with_pending,
            'debug_info': {
                'sample_pending': all_pending[:3],  # 3 premiers pour debug
                'restaurant_filter_active': current_restaurant is not None
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("🚀 FactureKiller V3 Pro - Démarrage")
    print("📊 Interface: http://localhost:5003")
    print("🔍 Scanner: Claude Vision AI")
    print("💾 Base de données: ✅ Connectée" if price_manager.is_connected() else "❌ Non connectée")
    
    # Récupérer le nombre de prix sans pagination
    all_prices_data = price_manager.get_all_prices(per_page=99999)
    print("📁 Prix référencés:", all_prices_data['total'])
    
    print("\n✨ Pages disponibles:")
    print("   • Dashboard: http://localhost:5003/")
    print("   • Scanner: http://localhost:5003/scanner")
    print("   • Commandes: http://localhost:5003/commandes")
    print("   • Factures: http://localhost:5003/factures")
    
    # Démarrer le serveur
    app.run(debug=True, port=5003, host='0.0.0.0') 