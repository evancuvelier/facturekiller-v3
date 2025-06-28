#!/usr/bin/env python3
"""
Routes pour la gestion des factures avec scanner multi-factures
"""

from flask import Blueprint, request, jsonify, render_template
from werkzeug.utils import secure_filename
import os
from modules.invoice_processor import invoice_processor
from modules.anomaly_manager import anomaly_manager

factures_bp = Blueprint('factures', __name__)

@factures_bp.route('/scanner')
def scanner():
    """Page de scan de factures classique"""
    return render_template('scanner.html')

@factures_bp.route('/scanner-multi')
def scanner_multi():
    """Page de scan multi-factures"""
    return render_template('scanner-multi-invoices.html')

@factures_bp.route('/api/process-invoice', methods=['POST'])
def process_invoice():
    """Traitement d'une facture simple ou multi-pages"""
    try:
        # Récupérer les fichiers
        files = request.files.getlist('image') or request.files.getlist('pages')
        
        if not files:
            return jsonify({
                'success': False,
                'error': 'Aucun fichier fourni'
            }), 400
        
        # Traiter les fichiers
        results = []
        for file in files:
            if file.filename:
                # Sauvegarder temporairement
                filename = secure_filename(file.filename)
                temp_path = os.path.join('uploads', filename)
                file.save(temp_path)
                
                # Analyser avec l'IA
                result = invoice_processor.process_invoice_file(temp_path)
                results.append(result)
                
                # Nettoyer
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        # Combiner les résultats si multi-pages
        if len(results) == 1:
            final_result = results[0]
        else:
            final_result = combine_multi_page_results(results)
        
        # Détecter les anomalies si extraction réussie
        if final_result.get('success') and final_result.get('products'):
            try:
                anomalies = anomaly_manager.detect_price_anomalies(
                    final_result['products'],
                    seuil_pourcent=10,
                    seuil_euros=0.50
                )
                
                # Sauvegarder les anomalies détectées
                for anomalie in anomalies:
                    anomalie_id = anomaly_manager.save_anomaly(anomalie, f"SCAN_{int(time.time())}")
                    anomalie['id'] = anomalie_id
                
                final_result['anomalies'] = anomalies
                final_result['anomalies_count'] = len(anomalies)
                
            except Exception as e:
                print(f"Erreur détection anomalies: {e}")
                final_result['anomalies'] = []
                final_result['anomalies_count'] = 0
        
        return jsonify(final_result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@factures_bp.route('/api/process-multi-page-invoice', methods=['POST'])
def process_multi_page_invoice():
    """Traitement spécifique pour factures multi-pages du scanner hybride"""
    try:
        import time
        
        # Récupérer les pages
        pages = request.files.getlist('pages')
        
        if not pages:
            return jsonify({
                'success': False,
                'error': 'Aucune page fournie'
            }), 400
        
        print(f"📄 Traitement de {len(pages)} page(s)")
        
        # Traiter chaque page
        page_results = []
        temp_files = []
        
        for i, page_file in enumerate(pages):
            if page_file.filename:
                # Sauvegarder temporairement
                filename = secure_filename(f"page_{i+1}_{page_file.filename}")
                temp_path = os.path.join('uploads', filename)
                page_file.save(temp_path)
                temp_files.append(temp_path)
                
                print(f"🔍 Analyse page {i+1}: {filename}")
                
                # Analyser avec l'IA
                page_result = invoice_processor.process_invoice_file(temp_path)
                page_result['page_number'] = i + 1
                page_result['filename'] = filename
                page_results.append(page_result)
        
        # Combiner les résultats multi-pages
        combined_result = combine_multi_page_results(page_results)
        combined_result['pages_count'] = len(pages)
        combined_result['pages_processed'] = len(page_results)
        
        # Détecter les anomalies
        if combined_result.get('success') and combined_result.get('products'):
            try:
                print("🔍 Détection d'anomalies...")
                
                anomalies = anomaly_manager.detect_price_anomalies(
                    combined_result['products'],
                    seuil_pourcent=10,
                    seuil_euros=0.50
                )
                
                # Sauvegarder les anomalies
                invoice_id = f"MULTI_{int(time.time())}"
                for anomalie in anomalies:
                    anomalie_id = anomaly_manager.save_anomaly(anomalie, invoice_id)
                    anomalie['id'] = anomalie_id
                
                combined_result['anomalies'] = anomalies
                combined_result['anomalies_count'] = len(anomalies)
                combined_result['invoice_id'] = invoice_id
                
                print(f"⚠️ {len(anomalies)} anomalie(s) détectée(s)")
                
            except Exception as e:
                print(f"Erreur détection anomalies: {e}")
                combined_result['anomalies'] = []
                combined_result['anomalies_count'] = 0
        
        # Nettoyer les fichiers temporaires
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                print(f"Erreur suppression fichier temporaire: {e}")
        
        print(f"✅ Traitement terminé: {combined_result.get('success', False)}")
        
        return jsonify(combined_result)
        
    except Exception as e:
        print(f"❌ Erreur traitement multi-page: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@factures_bp.route('/api/save-invoice', methods=['POST'])
def save_invoice():
    """Sauvegarder une facture analysée"""
    try:
        data = request.get_json()
        invoice_id = data.get('invoice_id')
        result = data.get('result')
        
        if not result:
            return jsonify({
                'success': False,
                'error': 'Aucun résultat à sauvegarder'
            }), 400
        
        # Ici vous pouvez ajouter la logique de sauvegarde
        # selon votre système (base de données, fichiers, etc.)
        
        # Pour l'instant, simulation
        success = True
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Facture {invoice_id} sauvegardée avec succès'
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

def combine_multi_page_results(page_results):
    """Combiner les résultats de plusieurs pages en un seul résultat"""
    try:
        if not page_results:
            return {'success': False, 'error': 'Aucun résultat à combiner'}
        
        # Si une seule page, retourner directement
        if len(page_results) == 1:
            return page_results[0]
        
        # Combiner les résultats
        combined = {
            'success': True,
            'pages_analyzed': len(page_results),
            'supplier': None,
            'date': None,
            'invoice_number': None,
            'total': None,
            'products': [],
            'confidence': 0,
            'analysis_method': 'multi-page-combination'
        }
        
        # Extraire les informations communes de la première page réussie
        for page_result in page_results:
            if page_result.get('success'):
                if not combined['supplier'] and page_result.get('supplier'):
                    combined['supplier'] = page_result['supplier']
                if not combined['date'] and page_result.get('date'):
                    combined['date'] = page_result['date']
                if not combined['invoice_number'] and page_result.get('invoice_number'):
                    combined['invoice_number'] = page_result['invoice_number']
                if not combined['total'] and page_result.get('total'):
                    combined['total'] = page_result['total']
        
        # Combiner tous les produits
        all_products = []
        total_confidence = 0
        successful_pages = 0
        
        for page_result in page_results:
            if page_result.get('success') and page_result.get('products'):
                all_products.extend(page_result['products'])
                total_confidence += page_result.get('confidence', 0)
                successful_pages += 1
        
        # Dédupliquer les produits similaires (optionnel)
        combined['products'] = deduplicate_products(all_products)
        
        # Calculer la confiance moyenne
        if successful_pages > 0:
            combined['confidence'] = total_confidence / successful_pages
        
        # Vérifier si au moins une page a été traitée avec succès
        combined['success'] = successful_pages > 0
        
        return combined
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Erreur lors de la combinaison: {str(e)}'
        }

def deduplicate_products(products):
    """Supprimer les doublons de produits basés sur le nom"""
    seen = set()
    unique_products = []
    
    for product in products:
        product_key = product.get('name', '').lower().strip()
        if product_key and product_key not in seen:
            seen.add(product_key)
            unique_products.append(product)
    
    return unique_products 