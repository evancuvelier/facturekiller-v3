#!/usr/bin/env python3
"""
Routes pour la gestion des anomalies
"""

from flask import Blueprint, request, jsonify, render_template
from modules.anomaly_manager import anomaly_manager

anomalies_bp = Blueprint('anomalies', __name__)

@anomalies_bp.route('/anomalies')
def anomalies_page():
    """Page de gestion des anomalies"""
    return render_template('anomalies.html')

@anomalies_bp.route('/api/anomalies', methods=['GET'])
def get_anomalies():
    """Récupérer toutes les anomalies"""
    try:
        statut = request.args.get('statut')
        fournisseur = request.args.get('fournisseur')
        
        anomalies = anomaly_manager.get_anomalies(statut=statut, fournisseur=fournisseur)
        stats = anomaly_manager.get_anomaly_stats()
        
        return jsonify({
            'success': True,
            'anomalies': anomalies,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@anomalies_bp.route('/api/anomalies/detect', methods=['POST'])
def detect_anomalies():
    """Détecter les anomalies dans une facture"""
    try:
        data = request.get_json()
        products = data.get('products', [])
        facture_id = data.get('facture_id')
        
        # Détecter les anomalies
        anomalies_detectees = anomaly_manager.detect_price_anomalies(products)
        
        # Sauvegarder les anomalies trouvées
        anomalies_saved = []
        for anomalie in anomalies_detectees:
            anomalie_id = anomaly_manager.save_anomaly(anomalie, facture_id)
            anomalie['id'] = anomalie_id
            anomalies_saved.append(anomalie)
        
        return jsonify({
            'success': True,
            'anomalies_detectees': len(anomalies_saved),
            'anomalies': anomalies_saved
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@anomalies_bp.route('/api/anomalies/<anomalie_id>/send-mail', methods=['POST'])
def send_mail_supplier(anomalie_id):
    """Envoyer un mail au fournisseur"""
    try:
        # Générer le contenu de l'email
        email_content = anomaly_manager.generate_supplier_email_content(anomalie_id)
        
        if not email_content:
            return jsonify({
                'success': False,
                'error': 'Anomalie introuvable'
            }), 404
        
        # Marquer comme mail envoyé
        success = anomaly_manager.send_mail_to_supplier(anomalie_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Mail marqué comme envoyé',
                'email_content': email_content
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Impossible de mettre à jour l\'anomalie'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@anomalies_bp.route('/api/anomalies/<anomalie_id>/avoir-accepte', methods=['POST'])
def mark_avoir_accepted(anomalie_id):
    """Marquer un avoir comme accepté"""
    try:
        data = request.get_json() or {}
        commentaire = data.get('commentaire', '')
        
        success = anomaly_manager.mark_avoir_accepted(anomalie_id, commentaire)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Avoir marqué comme accepté'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Impossible de mettre à jour l\'anomalie'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@anomalies_bp.route('/api/anomalies/<anomalie_id>/avoir-refuse', methods=['POST'])
def mark_avoir_refused(anomalie_id):
    """Marquer un avoir comme refusé"""
    try:
        data = request.get_json() or {}
        commentaire = data.get('commentaire', '')
        
        success = anomaly_manager.mark_avoir_refused(anomalie_id, commentaire)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Avoir marqué comme refusé'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Impossible de mettre à jour l\'anomalie'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@anomalies_bp.route('/api/anomalies/<anomalie_id>', methods=['GET'])
def get_anomaly_details(anomalie_id):
    """Récupérer les détails d'une anomalie"""
    try:
        anomalie = anomaly_manager.get_anomaly_by_id(anomalie_id)
        
        if not anomalie:
            return jsonify({
                'success': False,
                'error': 'Anomalie introuvable'
            }), 404
        
        return jsonify({
            'success': True,
            'anomalie': anomalie
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@anomalies_bp.route('/api/anomalies/stats', methods=['GET'])
def get_anomaly_stats():
    """Récupérer les statistiques des anomalies"""
    try:
        stats = anomaly_manager.get_anomaly_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 