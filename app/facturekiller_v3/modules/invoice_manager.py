"""
Gestionnaire de factures pour FactureKiller V3
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class InvoiceManager:
    def __init__(self):
        self.invoices_file = 'data/invoices.json'
        self.invoices_data = self._load_invoices()
    
    def _load_invoices(self) -> Dict[str, Any]:
        """Charger les factures depuis le fichier JSON"""
        try:
            if os.path.exists(self.invoices_file):
                with open(self.invoices_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Gérer les différents formats
                if isinstance(data, dict):
                    if 'invoices' in data:
                        return data
                    else:
                        # Format ancien - convertir
                        return {
                            'invoices': [data] if data else [],
                            'last_updated': datetime.now().isoformat()
                        }
                elif isinstance(data, list):
                    return {
                        'invoices': data,
                        'last_updated': datetime.now().isoformat()
                    }
                else:
                    return {'invoices': [], 'last_updated': datetime.now().isoformat()}
            else:
                return {'invoices': [], 'last_updated': datetime.now().isoformat()}
                
        except Exception as e:
            logger.error(f"Erreur chargement factures: {e}")
            return {'invoices': [], 'last_updated': datetime.now().isoformat()}
    
    def get_all_invoices(self, page: int = 1, per_page: int = 50, 
                        supplier: str = '', date_from: str = '', date_to: str = '',
                        restaurant_suppliers: List[str] = None, anomaly_filter: str = '', 
                        restaurant_id: str = None) -> Dict[str, Any]:
        """Récupérer toutes les factures avec pagination et filtres SÉCURISÉS PAR RESTAURANT_ID"""
        try:
            invoices = self.invoices_data.get('invoices', [])
            
            # 🔒 SÉCURITÉ CRITIQUE: Filtrage strict par restaurant_id
            if restaurant_id:
                filtered_invoices = []
                for invoice in invoices:
                    # Méthode 1: Vérifier le restaurant_id direct
                    if invoice.get('restaurant_id') == restaurant_id:
                        filtered_invoices.append(invoice)
                        continue
                    
                    # Méthode 2: Vérifier dans l'analyse (fallback pour anciennes données)
                    analysis = invoice.get('analysis', {})
                    if analysis.get('restaurant_id') == restaurant_id:
                        filtered_invoices.append(invoice)
                        continue
                        
                    # NE PAS utiliser les fournisseurs pour filtrer - SÉCURITÉ
                    # Les restaurants avec les mêmes fournisseurs doivent rester isolés
                
                invoices = filtered_invoices
                logger.info(f"🔒 Filtrage sécurisé restaurant {restaurant_id}: {len(filtered_invoices)} factures")
            
            # ANCIEN FILTRAGE PAR FOURNISSEURS - SUPPRIMÉ POUR SÉCURITÉ
            # Ne plus utiliser restaurant_suppliers car cela créait des fuites entre restaurants
            
            # 🚨 FILTRE: Par anomalies
            if anomaly_filter == 'with':
                invoices = [inv for inv in invoices if inv.get('has_anomalies', False)]
            elif anomaly_filter == 'without':
                invoices = [inv for inv in invoices if not inv.get('has_anomalies', False)]
            
            # Filtre par fournisseur spécifique (dans les factures déjà filtrées par restaurant)
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
                'restaurant_filter': restaurant_id,  # Maintenant basé sur l'ID
                'anomaly_filter': anomaly_filter
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération factures: {e}")
            return {
                'items': [],
                'total': 0,
                'page': 1,
                'pages': 0,
                'restaurant_filter': restaurant_id,
                'anomaly_filter': anomaly_filter
            }
    
    def save_invoice(self, invoice_data: Dict[str, Any]) -> str:
        """Sauvegarder une facture et retourner son ID"""
        try:
            # Générer un ID unique
            invoice_id = f"INV_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.invoices_data.get('invoices', [])) + 1}"
            
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
            
            # Ajouter à la liste des factures
            self.invoices_data['invoices'].append(invoice_data)
            self.invoices_data['last_updated'] = datetime.now().isoformat()
            
            # Sauvegarder dans le fichier
            self._save_invoices()
            
            logger.info(f"Facture sauvegardée avec ID: {invoice_id}")
            return invoice_id
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde facture: {e}")
            raise
    
    def _save_invoices(self):
        """Sauvegarder les factures dans le fichier JSON"""
        try:
            os.makedirs(os.path.dirname(self.invoices_file), exist_ok=True)
            with open(self.invoices_file, 'w', encoding='utf-8') as f:
                json.dump(self.invoices_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur écriture factures: {e}")
            raise
    
    def get_invoice_by_id(self, invoice_id: str) -> Dict[str, Any]:
        """Récupérer une facture par son ID"""
        try:
            invoices = self.invoices_data.get('invoices', [])
            for invoice in invoices:
                if invoice.get('id') == invoice_id:
                    return invoice
            return None
        except Exception as e:
            logger.error(f"Erreur récupération facture {invoice_id}: {e}")
            return None

    def get_invoices_by_restaurant(self, restaurant_id: str) -> List[Dict[str, Any]]:
        """Récupérer les factures d'un restaurant spécifique"""
        try:
            invoices = self.invoices_data.get('invoices', [])
            
            # Filtrer les factures par restaurant_id ET par fournisseurs autorisés
            restaurant_invoices = []
            
            for invoice in invoices:
                # Méthode 1: Vérifier si la facture a directement le restaurant_id
                if invoice.get('restaurant_id') == restaurant_id:
                    restaurant_invoices.append(invoice)
                    continue
                
                # Méthode 2: Vérifier via le contexte d'analyse
                analysis = invoice.get('analysis', {})
                if analysis.get('restaurant_id') == restaurant_id:
                    restaurant_invoices.append(invoice)
                    continue
                
                # Méthode 3: Vérifier via le restaurant_context dans l'analyse
                if analysis.get('restaurant_context'):
                    # Récupérer le restaurant par nom depuis auth_manager
                    try:
                        from modules.auth_manager import AuthManager
                        auth_manager = AuthManager()
                        restaurant = auth_manager.get_restaurant_by_id(restaurant_id)
                        if restaurant and restaurant.get('name') == analysis.get('restaurant_context'):
                            restaurant_invoices.append(invoice)
                    except:
                        pass
            
            # Trier par date de création décroissante
            restaurant_invoices.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return restaurant_invoices
            
        except Exception as e:
            logger.error(f"Erreur récupération factures restaurant {restaurant_id}: {e}")
            return [] 