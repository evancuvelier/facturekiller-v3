"""
Gestionnaire de factures pour FactureKiller V3
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any
import logging
from modules.firestore_db import available as _fs_available, get_client as _fs_client

logger = logging.getLogger(__name__)

class InvoiceManager:
    def __init__(self):
        """Initialiser le gestionnaire de factures (Firestore uniquement)"""
        # 🔥 FIRESTORE UNIQUEMENT - Plus de fichiers locaux
        self._fs_enabled = False
        self._fs = None
        
        # Initialiser Firestore
        try:
            from modules.firestore_db import FirestoreDB
            firestore_db = FirestoreDB()
            self._fs = firestore_db.db
            self._fs_enabled = True
            print("✅ Firestore initialisé pour InvoiceManager")
        except Exception as e:
            print(f"❌ Erreur initialisation Firestore InvoiceManager: {e}")
            self._fs_enabled = False
            self._fs = None
    
    def get_all_invoices(self, page: int = 1, per_page: int = 50, 
                        supplier: str = '', date_from: str = '', date_to: str = '',
                        restaurant_suppliers: List[str] = None, anomaly_filter: str = '', 
                        restaurant_id: str = None) -> Dict[str, Any]:
        """Récupérer toutes les factures depuis Firestore uniquement avec filtres sécurisés"""
        try:
            if not self._fs_enabled:
                return {
                    'items': [],
                    'total': 0,
                    'page': page,
                    'pages': 0,
                    'restaurant_filter': restaurant_id,
                    'anomaly_filter': anomaly_filter,
                    'error': 'Firestore non disponible'
                }
            
            # Construire la requête Firestore
            query = self._fs.collection('invoices')
            
            # 🔒 SÉCURITÉ CRITIQUE: Filtrage strict par restaurant_id
            if restaurant_id:
                query = query.where('restaurant_id', '==', restaurant_id)
            
            # Récupérer tous les documents
            docs = list(query.stream())
            invoices = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                invoices.append(data)
            
            # 🚨 FILTRE: Par anomalies
            if anomaly_filter == 'with':
                invoices = [inv for inv in invoices if inv.get('has_anomalies', False)]
            elif anomaly_filter == 'without':
                invoices = [inv for inv in invoices if not inv.get('has_anomalies', False)]
            
            # Filtre par fournisseur spécifique
            if supplier:
                filtered_invoices = []
                for invoice in invoices:
                    invoice_supplier = (
                        invoice.get('supplier') or 
                        invoice.get('analysis', {}).get('supplier', '') or
                        invoice.get('supplier_name', '')
                    )
                    if invoice_supplier and invoice_supplier.upper() == supplier.upper():
                        filtered_invoices.append(invoice)
                invoices = filtered_invoices
            
            # Filtre par date
            if date_from or date_to:
                filtered_invoices = []
                for invoice in invoices:
                    invoice_date = invoice.get('date') or invoice.get('analysis', {}).get('date', '')
                    if invoice_date:
                        if date_from and invoice_date < date_from:
                            continue
                        if date_to and invoice_date > date_to:
                            continue
                    filtered_invoices.append(invoice)
                invoices = filtered_invoices
            
            # Trier par date décroissante
            sorted_invoices = sorted(invoices, 
                key=lambda x: x.get('date') or x.get('analysis', {}).get('date', '') or x.get('created_at', ''), 
                reverse=True)
            
            # Pagination
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            
            paginated_invoices = sorted_invoices[start_idx:end_idx]
            
            return {
                'items': paginated_invoices,
                'total': len(sorted_invoices),
                'page': page,
                'pages': (len(sorted_invoices) + per_page - 1) // per_page,
                'restaurant_filter': restaurant_id,
                'anomaly_filter': anomaly_filter
            }
            
        except Exception as e:
            print(f"❌ Erreur get_all_invoices Firestore: {e}")
            return {
                'items': [],
                'total': 0,
                'page': page,
                'pages': 0,
                'restaurant_filter': restaurant_id,
                'anomaly_filter': anomaly_filter,
                'error': str(e)
            }
    
    def save_invoice(self, invoice_data: Dict[str, Any]) -> str:
        """Sauvegarder une facture dans Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return None
            
            # Générer un ID unique
            invoice_id = f"INV_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{int(datetime.now().timestamp())}"
            
            # Ajouter l'ID et la date de création
            invoice_data['id'] = invoice_id
            invoice_data['created_at'] = datetime.now().isoformat()
            
            # Structurer les données d'analyse
            if 'analysis' not in invoice_data:
                invoice_data['analysis'] = {}
            
            # Migrer les données vers analysis si nécessaire
            analysis_fields = ['supplier', 'invoice_number', 'date', 'total_amount', 'products']
            for field in analysis_fields:
                if field in invoice_data and field not in invoice_data['analysis']:
                    invoice_data['analysis'][field] = invoice_data[field]
            
            # Sauvegarder dans Firestore
            self._fs.collection('invoices').document(invoice_id).set(invoice_data)
            
            print(f"✅ Facture sauvegardée avec ID: {invoice_id}")
            return invoice_id
            
        except Exception as e:
            print(f"❌ Erreur save_invoice Firestore: {e}")
            return None
    
    def get_invoice_by_id(self, invoice_id: str) -> Dict[str, Any]:
        """Récupérer une facture par son ID depuis Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return None
            
            doc = self._fs.collection('invoices').document(invoice_id).get()
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id
                return data
            return None
            
        except Exception as e:
            print(f"❌ Erreur get_invoice_by_id Firestore: {e}")
            return None
    
    def get_invoices_by_restaurant(self, restaurant_id: str) -> List[Dict[str, Any]]:
        """Récupérer toutes les factures d'un restaurant depuis Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return []
            
            docs = list(self._fs.collection('invoices').where('restaurant_id', '==', restaurant_id).stream())
            invoices = []
            
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                invoices.append(data)
            
            print(f"📊 Firestore invoices for restaurant {restaurant_id}: {len(invoices)}")
            return invoices
            
        except Exception as e:
            print(f"❌ Erreur get_invoices_by_restaurant Firestore: {e}")
            return [] 