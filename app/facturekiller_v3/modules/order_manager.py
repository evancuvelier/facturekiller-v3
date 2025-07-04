"""
Gestionnaire de commandes pour FactureKiller V3
"""

import json
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
import uuid
from modules.firestore_db import available as _fs_available, get_client as _fs_client

logger = logging.getLogger(__name__)

class OrderManager:
    def __init__(self, email_manager=None, auth_manager=None):
        self.orders_file = 'data/orders.json'
        self.prices_file = 'data/prices.csv'
        
        # Firestore
        self._fs_enabled = _fs_available()
        self._fs = _fs_client() if self._fs_enabled else None
        
        self.orders_data = self._load_orders()
        self.email_manager = email_manager  # Injecter EmailManager
        self.auth_manager = auth_manager  # Injecter AuthManager (optionnel)
        
        # Statuts possibles d'une commande
        self.ORDER_STATUSES = {
            'draft': {'label': 'Brouillon', 'color': 'secondary', 'icon': 'pencil'},
            'pending': {'label': 'En attente', 'color': 'warning', 'icon': 'clock'},
            'sent': {'label': 'Envoyée', 'color': 'info', 'icon': 'send'},
            'confirmed': {'label': 'Confirmée', 'color': 'primary', 'icon': 'check-circle'},
            'preparing': {'label': 'En préparation', 'color': 'warning', 'icon': 'gear'},
            'shipped': {'label': 'Expédiée', 'color': 'info', 'icon': 'truck'},
            'delivered': {'label': 'Livrée', 'color': 'success', 'icon': 'box-seam'},
            'invoiced': {'label': 'Facturée', 'color': 'success', 'icon': 'receipt'},
            'paid': {'label': 'Payée', 'color': 'success', 'icon': 'check-all'},
            'cancelled': {'label': 'Annulée', 'color': 'danger', 'icon': 'x-circle'}
        }
    
    def _load_orders(self) -> Dict[str, Any]:
        """Charger les commandes : Firestore d'abord, sinon fichier JSON"""
        # 1️⃣ Firestore
        if getattr(self, '_fs_enabled', False):
            try:
                docs = list(self._fs.collection('orders').stream())
                if docs:
                    return {
                        'orders': [d.to_dict() for d in docs],
                        'last_updated': datetime.now().isoformat(),
                        'next_order_number': 1,  # recalculé ci-dessous
                        'restaurant_counters': {}
                    }
            except Exception as e:
                logger.warning(f"Firestore indisponible _load_orders: {e}")
        try:
            if os.path.exists(self.orders_file):
                with open(self.orders_file, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
            else:
                file_data = None

            # 🔀 Fusion Firestore + fichier local (import historique)
            if file_data:
                file_orders = file_data.get('orders', []) if isinstance(file_data, dict) else file_data.get('orders', []) if isinstance(file_data, dict) else []
                fs_order_ids = {o['id'] for o in self.orders_data.get('orders', [])}
                new_imports = [o for o in file_orders if o.get('id') not in fs_order_ids]
                if new_imports:
                    print(f"♻️ IMPORT HISTORIQUE: Ajout de {len(new_imports)} commandes depuis le fichier local vers Firestore")
                    self.orders_data['orders'].extend(new_imports)
                    # Push en batch
                    batch = self._fs.batch()
                    col = self._fs.collection('orders')
                    for o in new_imports:
                        batch.set(col.document(o['id']), o)
                    batch.commit()
                    # Mettre à jour les données locales pour cohérence
                    merged_data = {
                        'orders': self.orders_data['orders'],
                        'last_updated': datetime.now().isoformat(),
                        'next_order_number': file_data.get('next_order_number', 1),
                        'restaurant_counters': file_data.get('restaurant_counters', {})
                    }
                    self._save_orders(merged_data)

                return {
                    'orders': self.orders_data['orders'],
                    'last_updated': datetime.now().isoformat(),
                    'next_order_number': file_data.get('next_order_number', 1),
                    'restaurant_counters': file_data.get('restaurant_counters', {})
                }
            else:
                # Créer la structure par défaut
                default_data = {
                    'orders': [],
                    'last_updated': datetime.now().isoformat(),
                    'next_order_number': 1,
                    'restaurant_counters': {}  # Compteurs par restaurant
                }
                self._save_orders(default_data)
                return default_data
        except Exception as e:
            logger.error(f"Erreur chargement commandes: {e}")
            return {
                'orders': [],
                'last_updated': datetime.now().isoformat(),
                'next_order_number': 1,
                'restaurant_counters': {}
            }
    
    def _save_orders(self, data: Dict[str, Any] = None):
        """Sauvegarder les commandes (fichier + Firestore si dispo)"""
        try:
            if data is None:
                data = self.orders_data
            
            os.makedirs(os.path.dirname(self.orders_file), exist_ok=True)
            
            with open(self.orders_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            # Firestore bulk upload (simple) – on écrase tout pour simplifier
            if getattr(self, '_fs_enabled', False):
                batch = self._fs.batch()
                col = self._fs.collection('orders')
                for o in data.get('orders', []):
                    batch.set(col.document(o['id']), o)
                batch.commit()
                
        except Exception as e:
            logger.error(f"Erreur sauvegarde commandes: {e}")
    
    def get_all_orders(self, page: int = 1, per_page: int = 20, 
                       supplier: str = '', status: str = '', restaurant_suppliers: List[str] = None) -> Dict[str, Any]:
        """Récupérer toutes les commandes avec filtres INCLUANT RESTAURANT"""
        try:
            orders = self.orders_data.get('orders', [])
            
            # NOUVEAU FILTRE: Par fournisseurs du restaurant
            if restaurant_suppliers:
                orders = [o for o in orders if o.get('supplier', '') in restaurant_suppliers]
            
            # Filtrage par fournisseur spécifique
            if supplier:
                orders = [o for o in orders if o.get('supplier', '').upper() == supplier.upper()]
            
            # Filtrage par statut
            if status:
                orders = [o for o in orders if o.get('status') == status]
            
            # Trier par date de création décroissante
            orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # Pagination
            total = len(orders)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            
            paginated_orders = orders[start_idx:end_idx]
            
            return {
                'items': paginated_orders,
                'total': total,
                'page': page,
                'pages': (total + per_page - 1) // per_page,
                'restaurant_filter': restaurant_suppliers
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération commandes: {e}")
            return {
                'items': [],
                'total': 0,
                'page': 1,
                'pages': 0,
                'restaurant_filter': restaurant_suppliers
            }
    
    def get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Récupérer une commande par son ID"""
        try:
            orders = self.orders_data.get('orders', [])
            for order in orders:
                if order.get('id') == order_id:
                    return order
            return None
        except Exception as e:
            logger.error(f"Erreur récupération commande {order_id}: {e}")
            return None
    
    def create_order(self, order_data: Dict[str, Any]) -> Optional[str]:
        """Créer une nouvelle commande"""
        try:
            # Générer un ID unique
            order_id = str(uuid.uuid4())
            
            # Récupérer l'ID du restaurant (depuis le contexte utilisateur ou les données)
            restaurant_id = order_data.get('restaurant_id', 'default')
            
            # CORRECTION: Générer le numéro de commande au format CMD-XXXX-XXXX plus cohérent
            global_number = self.orders_data.get('next_order_number', 1)
            
            # Initialiser les compteurs par restaurant si nécessaire
            if 'restaurant_counters' not in self.orders_data:
                self.orders_data['restaurant_counters'] = {}
            
            if restaurant_id not in self.orders_data['restaurant_counters']:
                self.orders_data['restaurant_counters'][restaurant_id] = 1
            restaurant_number = self.orders_data['restaurant_counters'][restaurant_id]
            
            # NOUVEAU FORMAT: CMD-GGGG-RRRR (global-restaurant) - TOUJOURS 4 chiffres
            order_number = f"CMD-{global_number:04d}-{restaurant_number:04d}"
            
            # Calculer le total
            total_amount = sum(
                item.get('quantity', 0) * item.get('unit_price', 0) 
                for item in order_data.get('items', [])
            )
            
            # Créer la commande
            new_order = {
                'id': order_id,
                'order_number': order_number,
                'supplier': order_data.get('supplier', ''),
                'supplier_email': order_data.get('supplier_email', ''),
                'status': 'draft',
                'items': order_data.get('items', []),
                'total_amount': round(total_amount, 2),
                'notes': order_data.get('notes', ''),
                'delivery_date': order_data.get('delivery_date', ''),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'restaurant_id': restaurant_id,
                'restaurant_name': order_data.get('restaurant_name', ''),
                'restaurant_address': order_data.get('restaurant_address', ''),  # NOUVEAU CHAMP
                'status_history': [{
                    'status': 'draft',
                    'timestamp': datetime.now().isoformat(),
                    'comment': 'Commande créée'
                }]
            }
            
            # Ajouter la commande
            self.orders_data['orders'].append(new_order)
            
            # Incrémenter les compteurs
            self.orders_data['next_order_number'] += 1
            self.orders_data['restaurant_counters'][restaurant_id] += 1
            self.orders_data['last_updated'] = datetime.now().isoformat()
            
            self._save_orders()
            
            # Firestore save
            if getattr(self, '_fs_enabled', False):
                try:
                    self._fs.collection('orders').document(order_id).set(new_order)
                except Exception as e:
                    logger.warning(f"Firestore create_order KO: {e}")
            
            logger.info(f"✅ Commande créée: {order_number} (ID: {order_id})")
            
            return order_id
            
        except Exception as e:
            logger.error(f"Erreur création commande: {e}")
            return None
    
    def update_order(self, order_id: str, order_data: Dict[str, Any]) -> bool:
        """Mettre à jour une commande"""
        try:
            orders = self.orders_data.get('orders', [])
            
            for i, order in enumerate(orders):
                if order.get('id') == order_id:
                    # Recalculer le total si les items ont changé
                    if 'items' in order_data:
                        total_amount = sum(
                            item.get('quantity', 0) * item.get('unit_price', 0) 
                            for item in order_data['items']
                        )
                        order_data['total_amount'] = round(total_amount, 2)
                    
                    # Mettre à jour les champs
                    order.update(order_data)
                    order['updated_at'] = datetime.now().isoformat()
                    
                    self.orders_data['orders'][i] = order
                    self.orders_data['last_updated'] = datetime.now().isoformat()
                    
                    self._save_orders()
                    
                    # Firestore update
                    if getattr(self, '_fs_enabled', False):
                        try:
                            self._fs.collection('orders').document(order_id).update(order)
                        except Exception as e:
                            logger.warning(f"Firestore update_order KO: {e}")
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur mise à jour commande {order_id}: {e}")
            return False
    
    def update_order_status(self, order_id: str, new_status: str, comment: str = '') -> bool:
        """Mettre à jour le statut d'une commande"""
        try:
            if new_status not in self.ORDER_STATUSES:
                return False
            
            orders = self.orders_data.get('orders', [])
            
            for i, order in enumerate(orders):
                if order.get('id') == order_id:
                    old_status = order.get('status', 'draft')
                    
                    # Mettre à jour le statut
                    order['status'] = new_status
                    order['updated_at'] = datetime.now().isoformat()
                    
                    # Ajouter à l'historique
                    if 'status_history' not in order:
                        order['status_history'] = []
                    
                    order['status_history'].append({
                        'status': new_status,
                        'timestamp': datetime.now().isoformat(),
                        'comment': comment or f'Passage de "{self.ORDER_STATUSES[old_status]["label"]}" à "{self.ORDER_STATUSES[new_status]["label"]}"'
                    })
                    
                    self.orders_data['orders'][i] = order
                    self.orders_data['last_updated'] = datetime.now().isoformat()
                    
                    self._save_orders()
                    
                    # Envoyer un email automatiquement si le statut passe à "confirmed" 
                    if new_status == 'confirmed' and self.email_manager:
                        self._send_order_email_auto(order)
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur mise à jour statut commande {order_id}: {e}")
            return False
    
    def delete_order(self, order_id: str) -> bool:
        """Supprimer une commande"""
        try:
            orders = self.orders_data.get('orders', [])
            
            for i, order in enumerate(orders):
                if order.get('id') == order_id:
                    del self.orders_data['orders'][i]
                    self.orders_data['last_updated'] = datetime.now().isoformat()
                    
                    self._save_orders()
                    
                    # Firestore delete
                    if getattr(self, '_fs_enabled', False):
                        try:
                            self._fs.collection('orders').document(order_id).delete()
                        except Exception as e:
                            logger.warning(f"Firestore delete_order KO: {e}")
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur suppression commande {order_id}: {e}")
            return False
    
    def get_supplier_products(self, supplier_name: str) -> List[Dict[str, Any]]:
        """Récupérer les produits d'un fournisseur pour créer une commande"""
        try:
            if not os.path.exists(self.prices_file):
                return []
            
            prices_df = pd.read_csv(self.prices_file)
            supplier_products = prices_df[
                prices_df['fournisseur'].str.upper() == supplier_name.upper()
            ]
            
            products = []
            for _, row in supplier_products.iterrows():
                products.append({
                    'name': row.get('produit', ''),
                    'unit_price': float(row.get('prix_unitaire', 0)),
                    'unit': row.get('unite', 'unité'),
                    'code': row.get('code_produit', ''),
                    'supplier': row.get('fournisseur', '')
                })
            
            return products
            
        except Exception as e:
            logger.error(f"Erreur récupération produits fournisseur {supplier_name}: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Récupérer les statistiques des commandes"""
        try:
            orders = self.orders_data.get('orders', [])
            
            total_orders = len(orders)
            total_amount = sum(order.get('total_amount', 0) for order in orders)
            
            # Statistiques par statut
            status_counts = {}
            for order in orders:
                status = order.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Commandes récentes (7 derniers jours)
            recent_date = (datetime.now() - timedelta(days=7)).isoformat()
            recent_orders = [
                order for order in orders 
                if order.get('created_at', '') > recent_date
            ]
            
            # Top fournisseurs
            supplier_amounts = {}
            for order in orders:
                supplier = order.get('supplier', 'Unknown')
                amount = order.get('total_amount', 0)
                supplier_amounts[supplier] = supplier_amounts.get(supplier, 0) + amount
            
            top_suppliers = sorted(
                supplier_amounts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
            
            return {
                'total_orders': total_orders,
                'total_amount': total_amount,
                'status_counts': status_counts,
                'recent_orders_count': len(recent_orders),
                'recent_orders': recent_orders[:5],  # 5 plus récentes
                'top_suppliers': top_suppliers,
                'average_order_value': total_amount / total_orders if total_orders > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Erreur calcul statistiques commandes: {e}")
            return {
                'total_orders': 0,
                'total_amount': 0,
                'status_counts': {},
                'recent_orders_count': 0,
                'recent_orders': [],
                'top_suppliers': [],
                'average_order_value': 0
            }
    
    def get_orders_by_restaurant(self, restaurant_id: str) -> List[Dict[str, Any]]:
        """Récupérer les commandes d'un restaurant spécifique"""
        try:
            orders = self.orders_data.get('orders', [])
            restaurant_orders = [
                order for order in orders 
                if order.get('restaurant_id') == restaurant_id
            ]
            
            # Trier par date de création décroissante
            restaurant_orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return restaurant_orders
            
        except Exception as e:
            logger.error(f"Erreur récupération commandes restaurant {restaurant_id}: {e}")
            return []
    
    def get_order_statuses(self) -> Dict[str, Dict[str, str]]:
        """Récupérer la liste des statuts possibles"""
        return self.ORDER_STATUSES
    
    def _send_order_email_auto(self, order: Dict[str, Any]) -> bool:
        """Envoyer automatiquement un email de commande au fournisseur"""
        try:
            # Vérifier si l'email du fournisseur est configuré
            supplier_email = order.get('supplier_email', '').strip()
            if not supplier_email:
                logger.warning(f"Pas d'email configuré pour le fournisseur {order.get('supplier', 'Unknown')}")
                return False
            
            # Vérifier si l'EmailManager est disponible
            if not self.email_manager:
                logger.warning("EmailManager non disponible pour envoi automatique")
                return False
            
            # Récupérer les informations du restaurant
            restaurant_info = self._get_restaurant_info(order.get('restaurant_id'))
            
            # Récupérer les informations du fournisseur
            supplier_info = self._get_supplier_info(order.get('supplier'))
            
            # Préparer les données de commande pour l'email
            order_for_email = {
                'id': order.get('order_number', order.get('id')),
                'order_number': order.get('order_number', ''),
                'supplier': order.get('supplier', ''),
                'status': order.get('status', ''),
                'created_at': order.get('created_at', ''),
                'delivery_date': order.get('delivery_date', ''),
                'notes': order.get('notes', ''),
                'restaurant': restaurant_info,
                'supplier_info': supplier_info,
                'products': []
            }
            
            # Convertir les items en format produits pour l'email
            for item in order.get('items', []):
                order_for_email['products'].append({
                    'name': item.get('product_name', item.get('name', '')),
                    'quantity': item.get('quantity', 0),
                    'unit': item.get('unit', 'kg'),
                    'unit_price': item.get('unit_price', 0)
                })
            
            # Envoyer l'email
            result = self.email_manager.send_order_notification(order_for_email, supplier_email)
            
            if result['success']:
                logger.info(f"Email automatique envoyé pour commande {order.get('order_number')} à {supplier_email}")
                return True
            else:
                logger.error(f"Erreur envoi email automatique: {result.get('error', 'Erreur inconnue')}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur envoi email automatique commande: {e}")
            return False
    
    def _get_restaurant_info(self, restaurant_id: str) -> Dict[str, str]:
        """Récupérer les informations d'un restaurant"""
        try:
            if not restaurant_id:
                return {'name': 'Restaurant', 'address': 'Adresse non renseignée', 'city': 'Ville', 'country': 'France'}
            
            # Utiliser AuthManager si disponible
            if self.auth_manager:
                restaurants = self.auth_manager._load_restaurants()
                for restaurant in restaurants:
                    if restaurant.get('id') == restaurant_id:
                        return {
                            'name': restaurant.get('name', 'Restaurant'),
                            'address': restaurant.get('address', 'Adresse non renseignée'),
                            'city': restaurant.get('city', ''),
                            'country': 'France',
                            'phone': restaurant.get('phone', ''),
                            'email': restaurant.get('email', '')
                        }
            
            # Fallback vers le fichier JSON si AuthManager non disponible
            restaurants_file = 'data/restaurants.json'
            if os.path.exists(restaurants_file):
                with open(restaurants_file, 'r', encoding='utf-8') as f:
                    restaurants = json.load(f)
                    
                for restaurant in restaurants:
                    if restaurant.get('id') == restaurant_id:
                        return {
                            'name': restaurant.get('name', 'Restaurant'),
                            'address': restaurant.get('address', 'Adresse non renseignée'),
                            'city': restaurant.get('city', ''),
                            'country': 'France',
                            'phone': restaurant.get('phone', ''),
                            'email': restaurant.get('email', '')
                        }
            
            return {'name': 'Restaurant', 'address': 'Adresse non renseignée', 'city': 'Ville', 'country': 'France'}
            
        except Exception as e:
            logger.error(f"Erreur récupération info restaurant {restaurant_id}: {e}")
            return {'name': 'Restaurant', 'address': 'Adresse non renseignée', 'city': 'Ville', 'country': 'France'}
    
    def _get_supplier_info(self, supplier_name: str) -> Dict[str, str]:
        """Récupérer les informations d'un fournisseur"""
        try:
            if not supplier_name:
                return {'name': 'Fournisseur', 'address': 'Adresse non renseignée', 'city': '', 'country': 'France'}
            
            suppliers_file = 'data/suppliers.json'
            if os.path.exists(suppliers_file):
                with open(suppliers_file, 'r', encoding='utf-8') as f:
                    suppliers = json.load(f)
                    
                for supplier in suppliers:
                    if supplier.get('name', '').upper() == supplier_name.upper():
                        return {
                            'name': supplier.get('name', supplier_name),
                            'address': supplier.get('address', 'Adresse non renseignée'),
                            'city': supplier.get('city', ''),
                            'country': supplier.get('country', 'France'),
                            'phone': supplier.get('phone', ''),
                            'email': supplier.get('email', '')
                        }
            
            return {'name': supplier_name, 'address': 'Adresse non renseignée', 'city': '', 'country': 'France'}
            
        except Exception as e:
            logger.error(f"Erreur récupération info fournisseur {supplier_name}: {e}")
            return {'name': supplier_name, 'address': 'Adresse non renseignée', 'city': '', 'country': 'France'} 