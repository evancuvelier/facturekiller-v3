#!/usr/bin/env python3
"""
Module de validation commande vs facture
Compare les quantités commandées avec les quantités facturées
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import difflib

logger = logging.getLogger(__name__)

class OrderInvoiceValidator:
    """Validateur commande vs facture"""
    
    def __init__(self, order_manager):
        self.order_manager = order_manager
        
    def compare_order_with_invoice(self, order_id: str, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comparer une commande avec une facture scannée
        
        Args:
            order_id: ID de la commande
            invoice_data: Données de la facture scannée
            
        Returns:
            Dict avec résultats de comparaison
        """
        logger.info(f"🔍 Comparaison commande {order_id} vs facture")
        
        # Récupérer la commande
        order = self.order_manager.get_order_by_id(order_id)
        if not order:
            return {
                'success': False,
                'error': f'Commande {order_id} non trouvée'
            }
        
        # Données facture
        invoice_products = invoice_data.get('products', [])
        invoice_supplier = invoice_data.get('supplier', '').upper()
        order_supplier = order.get('supplier', '').upper()
        
        # Vérifier fournisseur
        if invoice_supplier != order_supplier:
            logger.warning(f"⚠️ Fournisseur différent: commande={order_supplier}, facture={invoice_supplier}")
        
        # Comparer produits
        comparison_results = self._compare_products(order.get('items', []), invoice_products)
        
        # Calculer totaux
        order_total = order.get('total_amount', 0)
        invoice_total = invoice_data.get('total_amount', 0)
        total_diff = abs(order_total - invoice_total)
        
        # Résumé
        summary = self._generate_summary(comparison_results, order_total, invoice_total)
        
        return {
            'success': True,
            'order_id': order_id,
            'order_number': order.get('order_number'),
            'supplier_match': invoice_supplier == order_supplier,
            'order_supplier': order_supplier,
            'invoice_supplier': invoice_supplier,
            'total_order': order_total,
            'total_invoice': invoice_total,
            'total_difference': total_diff,
            'products_comparison': comparison_results,
            'summary': summary,
            'validation_timestamp': datetime.now().isoformat(),
            'requires_validation': summary['requires_attention']
        }
    
    def _compare_products(self, order_items: List[Dict], invoice_products: List[Dict]) -> List[Dict]:
        """Comparer les produits de la commande avec ceux de la facture"""
        results = []
        
        # Créer index des produits facture pour matching
        invoice_index = {self._normalize_product_name(p['name']): p for p in invoice_products}
        
        # Produits utilisés (pour détecter les extras)
        used_invoice_products = set()
        
        # Comparer chaque item de commande
        for order_item in order_items:
            order_name = order_item.get('product_name', '')
            order_qty = order_item.get('quantity', 0)
            order_price = order_item.get('unit_price', 0)
            
            # Chercher correspondance dans facture
            match_result = self._find_best_match(order_name, invoice_index)
            
            if match_result['match']:
                invoice_product = match_result['product']
                used_invoice_products.add(match_result['normalized_name'])
                
                # Comparer quantités
                invoice_qty = invoice_product.get('quantity', 0)
                qty_diff = invoice_qty - order_qty
                
                # Comparer prix
                invoice_price = invoice_product.get('unit_price', 0)
                price_diff = invoice_price - order_price
                
                status = self._determine_status(qty_diff, price_diff)
                
                results.append({
                    'order_product': order_name,
                    'invoice_product': invoice_product['name'],
                    'match_confidence': match_result['confidence'],
                    'order_quantity': order_qty,
                    'invoice_quantity': invoice_qty,
                    'quantity_difference': qty_diff,
                    'order_unit_price': order_price,
                    'invoice_unit_price': invoice_price,
                    'price_difference': price_diff,
                    'status': status,
                    'order_total': order_qty * order_price,
                    'invoice_total': invoice_qty * invoice_price
                })
            else:
                # Produit commandé mais pas trouvé dans facture
                results.append({
                    'order_product': order_name,
                    'invoice_product': None,
                    'match_confidence': 0,
                    'order_quantity': order_qty,
                    'invoice_quantity': 0,
                    'quantity_difference': -order_qty,
                    'order_unit_price': order_price,
                    'invoice_unit_price': 0,
                    'price_difference': -order_price,
                    'status': 'missing_in_invoice',
                    'order_total': order_qty * order_price,
                    'invoice_total': 0
                })
        
        # Ajouter produits facturés mais pas commandés
        for normalized_name, invoice_product in invoice_index.items():
            if normalized_name not in used_invoice_products:
                results.append({
                    'order_product': None,
                    'invoice_product': invoice_product['name'],
                    'match_confidence': 0,
                    'order_quantity': 0,
                    'invoice_quantity': invoice_product.get('quantity', 0),
                    'quantity_difference': invoice_product.get('quantity', 0),
                    'order_unit_price': 0,
                    'invoice_unit_price': invoice_product.get('unit_price', 0),
                    'price_difference': invoice_product.get('unit_price', 0),
                    'status': 'extra_in_invoice',
                    'order_total': 0,
                    'invoice_total': invoice_product.get('quantity', 0) * invoice_product.get('unit_price', 0)
                })
        
        return results
    
    def _normalize_product_name(self, name: str) -> str:
        """Normaliser nom de produit pour matching"""
        import re
        
        # Nettoyer et normaliser
        normalized = name.upper()
        normalized = re.sub(r'[^\w\s]', ' ', normalized)  # Supprimer ponctuation
        normalized = re.sub(r'\s+', ' ', normalized).strip()  # Espaces multiples
        
        # Supprimer mots courants qui perturbent matching
        stop_words = ['DE', 'DU', 'LA', 'LE', 'LES', 'ET', 'AVEC', 'SANS', 'POUR']
        words = [w for w in normalized.split() if w not in stop_words and len(w) > 2]
        
        return ' '.join(words)
    
    def _find_best_match(self, order_name: str, invoice_index: Dict) -> Dict:
        """Trouver la meilleure correspondance pour un produit"""
        normalized_order = self._normalize_product_name(order_name)
        
        # Recherche exacte
        if normalized_order in invoice_index:
            return {
                'match': True,
                'product': invoice_index[normalized_order],
                'normalized_name': normalized_order,
                'confidence': 1.0
            }
        
        # Recherche par similarité
        best_match = None
        best_confidence = 0
        best_name = None
        
        for invoice_name, product in invoice_index.items():
            # Calculer similarité
            similarity = difflib.SequenceMatcher(None, normalized_order, invoice_name).ratio()
            
            # Bonus si mots clés communs
            order_words = set(normalized_order.split())
            invoice_words = set(invoice_name.split())
            common_words = order_words.intersection(invoice_words)
            
            if common_words:
                word_bonus = len(common_words) / max(len(order_words), len(invoice_words))
                similarity = (similarity + word_bonus) / 2
            
            if similarity > best_confidence and similarity > 0.6:  # Seuil minimum
                best_confidence = similarity
                best_match = product
                best_name = invoice_name
        
        if best_match:
            return {
                'match': True,
                'product': best_match,
                'normalized_name': best_name,
                'confidence': best_confidence
            }
        
        return {'match': False, 'confidence': 0}
    
    def _determine_status(self, qty_diff: float, price_diff: float) -> str:
        """Déterminer le statut de comparaison"""
        if abs(qty_diff) < 0.01 and abs(price_diff) < 0.01:
            return 'perfect_match'
        elif abs(qty_diff) < 0.01 and abs(price_diff) > 0.01:
            return 'price_difference'
        elif abs(qty_diff) > 0.01 and abs(price_diff) < 0.01:
            return 'quantity_difference'
        else:
            return 'both_different'
    
    def _generate_summary(self, comparison_results: List[Dict], order_total: float, invoice_total: float) -> Dict:
        """Générer résumé de la comparaison"""
        total_items = len(comparison_results)
        
        # Compter par statut
        status_counts = {}
        for result in comparison_results:
            status = result['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Déterminer si validation requise
        requires_attention = (
            status_counts.get('missing_in_invoice', 0) > 0 or
            status_counts.get('extra_in_invoice', 0) > 0 or
            status_counts.get('quantity_difference', 0) > 0 or
            status_counts.get('both_different', 0) > 0 or
            abs(order_total - invoice_total) > 1.0  # Différence > 1€
        )
        
        return {
            'total_items_compared': total_items,
            'perfect_matches': status_counts.get('perfect_match', 0),
            'price_differences': status_counts.get('price_difference', 0),
            'quantity_differences': status_counts.get('quantity_difference', 0),
            'missing_in_invoice': status_counts.get('missing_in_invoice', 0),
            'extra_in_invoice': status_counts.get('extra_in_invoice', 0),
            'both_different': status_counts.get('both_different', 0),
            'requires_attention': requires_attention,
            'match_rate': status_counts.get('perfect_match', 0) / max(total_items, 1),
            'total_difference_amount': abs(order_total - invoice_total)
        } 