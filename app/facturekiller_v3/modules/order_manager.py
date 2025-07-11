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
        """Initialiser le gestionnaire de commandes (Firestore uniquement)"""
        # 🔥 FIRESTORE UNIQUEMENT - Plus de fichiers locaux
        self._fs_enabled = False
        self._fs = None
        
        # Initialiser Firestore
        try:
            from modules.firestore_db import FirestoreDB
            firestore_db = FirestoreDB()
            self._fs = firestore_db.db
            self._fs_enabled = True
            print("✅ Firestore initialisé pour OrderManager")
        except Exception as e:
            print(f"❌ Erreur initialisation Firestore OrderManager: {e}")
            self._fs_enabled = False
            self._fs = None
        
        self.email_manager = email_manager
        self.auth_manager = auth_manager
        
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
    
    def get_all_orders(self, page: int = 1, per_page: int = 20, 
                       supplier: str = '', status: str = '', restaurant_suppliers: List[str] = None) -> Dict[str, Any]:
        """Récupérer toutes les commandes depuis Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return {
                    'items': [],
                    'total': 0,
                    'page': page,
                    'pages': 0,
                    'restaurant_filter': restaurant_suppliers,
                    'error': 'Firestore non disponible'
                }
            
            # Construire la requête Firestore
            query = self._fs.collection('orders')
            
            # Appliquer les filtres
            if supplier:
                query = query.where('supplier', '==', supplier)
            
            if status:
                query = query.where('status', '==', status)
            
            # Récupérer tous les documents
            docs = list(query.stream())
            orders = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                orders.append(data)
            
            # Filtrer par fournisseurs du restaurant côté application
            if restaurant_suppliers:
                orders = [o for o in orders if o.get('supplier', '') in restaurant_suppliers]
            
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
            print(f"❌ Erreur get_all_orders Firestore: {e}")
            return {
                'items': [],
                'total': 0,
                'page': page,
                'pages': 0,
                'restaurant_filter': restaurant_suppliers,
                'error': str(e)
            }
    
    def get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Récupérer une commande par son ID depuis Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return None
            
            doc = self._fs.collection('orders').document(order_id).get()
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id
                return data
            return None
            
        except Exception as e:
            print(f"❌ Erreur get_order_by_id Firestore: {e}")
            return None
    
    def create_order(self, order_data: Dict[str, Any]) -> Optional[str]:
        """Créer une nouvelle commande dans Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return None
            
            # Générer un ID unique
            order_id = str(uuid.uuid4())
            
            # Ajouter les métadonnées
            order_data['id'] = order_id
            order_data['created_at'] = datetime.now().isoformat()
            order_data['updated_at'] = datetime.now().isoformat()
            
            # Sauvegarder dans Firestore
            self._fs.collection('orders').document(order_id).set(order_data)
            
            print(f"✅ Commande créée: {order_id}")
            return order_id
            
        except Exception as e:
            print(f"❌ Erreur create_order Firestore: {e}")
            return None
    
    def update_order(self, order_id: str, order_data: Dict[str, Any]) -> bool:
        """Mettre à jour une commande dans Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return False
            
            # Vérifier que la commande existe
            doc = self._fs.collection('orders').document(order_id).get()
            if not doc.exists:
                print(f"❌ Commande {order_id} non trouvée")
                return False
            
            # Mettre à jour les métadonnées
            order_data['updated_at'] = datetime.now().isoformat()
            
            # Mettre à jour dans Firestore
            self._fs.collection('orders').document(order_id).update(order_data)
            
            print(f"✅ Commande {order_id} mise à jour")
            return True
            
        except Exception as e:
            print(f"❌ Erreur update_order Firestore: {e}")
            return False
    
    def update_order_status(self, order_id: str, new_status: str, comment: str = '') -> bool:
        """Mettre à jour le statut d'une commande dans Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return False
            
            # Vérifier que la commande existe
            doc = self._fs.collection('orders').document(order_id).get()
            if not doc.exists:
                print(f"❌ Commande {order_id} non trouvée")
                return False
            
            order_data = doc.to_dict()
            
            # Mettre à jour le statut
            updates = {
                'status': new_status,
                'updated_at': datetime.now().isoformat()
            }
            
            # Ajouter à l'historique des statuts
            if 'status_history' not in order_data:
                order_data['status_history'] = []
            
            order_data['status_history'].append({
                'status': new_status,
                'timestamp': datetime.now().isoformat(),
                'comment': comment or f'Statut changé vers {new_status}'
            })
            
            updates['status_history'] = order_data['status_history']
            
            # Mettre à jour dans Firestore
            self._fs.collection('orders').document(order_id).update(updates)
            
            print(f"✅ Statut de la commande {order_id} mis à jour: {new_status}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur update_order_status Firestore: {e}")
            return False
    
    def delete_order(self, order_id: str) -> bool:
        """Supprimer une commande dans Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return False
            
            # Vérifier que la commande existe
            doc = self._fs.collection('orders').document(order_id).get()
            if not doc.exists:
                print(f"❌ Commande {order_id} non trouvée")
                return False
            
            # Supprimer de Firestore
            self._fs.collection('orders').document(order_id).delete()
            
            print(f"✅ Commande {order_id} supprimée")
            return True
            
        except Exception as e:
            print(f"❌ Erreur delete_order Firestore: {e}")
            return False
    
    def get_supplier_products(self, supplier_name: str) -> List[Dict[str, Any]]:
        """Récupérer les produits d'un fournisseur depuis Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return []
            
            # Récupérer les prix validés du fournisseur
            docs = list(self._fs.collection('prices').where('fournisseur', '==', supplier_name).stream())
            products = []
            
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                products.append(data)
            
            print(f"📊 Firestore supplier products for {supplier_name}: {len(products)}")
            return products
            
        except Exception as e:
            print(f"❌ Erreur get_supplier_products Firestore: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Récupérer les statistiques des commandes depuis Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return {
                    'total_orders': 0,
                    'orders_by_status': {},
                    'total_amount': 0,
                    'average_order_value': 0
                }
            
            # Récupérer toutes les commandes
            docs = list(self._fs.collection('orders').stream())
            orders = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                orders.append(data)
            
            # Calculer les statistiques
            total_orders = len(orders)
            orders_by_status = {}
            total_amount = 0
            
            for order in orders:
                status = order.get('status', 'unknown')
                orders_by_status[status] = orders_by_status.get(status, 0) + 1
                total_amount += float(order.get('total_amount', 0))
            
            average_order_value = total_amount / total_orders if total_orders > 0 else 0
            
            return {
                'total_orders': total_orders,
                'orders_by_status': orders_by_status,
                'total_amount': round(total_amount, 2),
                'average_order_value': round(average_order_value, 2)
            }
            
        except Exception as e:
            print(f"❌ Erreur get_stats Firestore: {e}")
            return {
                'total_orders': 0,
                'orders_by_status': {},
                'total_amount': 0,
                'average_order_value': 0,
                'error': str(e)
            }
    
    def get_orders_by_restaurant(self, restaurant_id: str) -> List[Dict[str, Any]]:
        """Récupérer les commandes d'un restaurant depuis Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return []
            
            docs = list(self._fs.collection('orders').where('restaurant_id', '==', restaurant_id).stream())
            orders = []
            
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                orders.append(data)
            
            print(f"📊 Firestore orders for restaurant {restaurant_id}: {len(orders)}")
            return orders
            
        except Exception as e:
            print(f"❌ Erreur get_orders_by_restaurant Firestore: {e}")
            return []
    
    def get_order_statuses(self) -> Dict[str, Dict[str, str]]:
        """Récupérer les statuts possibles des commandes"""
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