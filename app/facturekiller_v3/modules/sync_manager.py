"""
🔄 FactureKiller V3 - Gestionnaire de Synchronisation Multi-Restaurants
Synchronisation automatique des fournisseurs et prix entre restaurants d'un même groupe
100% Firestore - Plus de fichiers locaux
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SyncManager:
    """Gestionnaire de synchronisation entre restaurants"""
    
    def __init__(self):
        # Initialiser Firestore
        try:
            from modules.firestore_db import get_client
            self._fs = get_client()
            self._fs_enabled = self._fs is not None
            if self._fs_enabled:
                print("✅ Firestore initialisé pour SyncManager")
            else:
                print("❌ Firestore non disponible pour SyncManager")
        except Exception as e:
            print(f"❌ Erreur initialisation Firestore SyncManager: {e}")
            self._fs_enabled = False
            self._fs = None
    
    def get_restaurants(self) -> List[Dict]:
        """Récupérer tous les restaurants depuis Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return []
            
            docs = list(self._fs.collection('restaurants').stream())
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Erreur lecture restaurants: {e}")
            return []
    
    def save_restaurants(self, restaurants: List[Dict]) -> bool:
        """Sauvegarder les restaurants dans Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return False
            
            # Supprimer tous les restaurants existants
            docs = list(self._fs.collection('restaurants').stream())
            for doc in docs:
                doc.reference.delete()
            
            # Ajouter les nouveaux restaurants
            for restaurant in restaurants:
                restaurant_id = restaurant.get('id', f"rest_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                self._fs.collection('restaurants').document(restaurant_id).set(restaurant)
            
            return True
        except Exception as e:
            logger.error(f"Erreur sauvegarde restaurants: {e}")
            return False
    
    def get_restaurant_by_id(self, restaurant_id: str) -> Optional[Dict]:
        """Récupérer un restaurant par son ID depuis Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return None
            
            doc = self._fs.collection('restaurants').document(restaurant_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Erreur récupération restaurant: {e}")
            return None
    
    def update_sync_settings(self, restaurant_id: str, sync_settings: Dict) -> Dict[str, Any]:
        """Mettre à jour les paramètres de synchronisation d'un restaurant dans Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return {'success': False, 'error': 'Firestore non disponible'}
            
            doc_ref = self._fs.collection('restaurants').document(restaurant_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return {'success': False, 'error': 'Restaurant non trouvé'}
            
            restaurant = doc.to_dict()
            
            # Mettre à jour les paramètres
            if 'sync_settings' not in restaurant:
                restaurant['sync_settings'] = {}
            
            restaurant['sync_settings'].update(sync_settings)
            restaurant['sync_settings']['last_updated'] = datetime.now().isoformat()
            
            # Sauvegarder dans Firestore
            doc_ref.set(restaurant)
            
            return {
                'success': True,
                'message': 'Paramètres de synchronisation mis à jour',
                'restaurant': restaurant
            }
                
        except Exception as e:
            logger.error(f"Erreur mise à jour sync settings: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_sync_groups(self) -> Dict[str, List[Dict]]:
        """Récupérer les groupes de synchronisation depuis Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return {}
            
            restaurants = self.get_restaurants()
            sync_groups = {}
            
            for restaurant in restaurants:
                sync_settings = restaurant.get('sync_settings', {})
                if sync_settings.get('sync_enabled') and sync_settings.get('sync_group'):
                    group_name = sync_settings['sync_group']
                    if group_name not in sync_groups:
                        sync_groups[group_name] = []
                    sync_groups[group_name].append(restaurant)
            
            return sync_groups
        except Exception as e:
            logger.error(f"Erreur récupération groupes sync: {e}")
            return {}
    
    def get_restaurants_in_sync_group(self, sync_group: str) -> List[Dict]:
        """Récupérer tous les restaurants d'un groupe de synchronisation depuis Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return []
            
            restaurants = self.get_restaurants()
            return [
                r for r in restaurants 
                if r.get('sync_settings', {}).get('sync_enabled') 
                and r.get('sync_settings', {}).get('sync_group') == sync_group
            ]
        except Exception as e:
            logger.error(f"Erreur récupération restaurants groupe: {e}")
            return []
    
    def sync_suppliers_to_group(self, source_restaurant_id: str, new_supplier: str) -> Dict[str, Any]:
        """Synchroniser un nouveau fournisseur vers tous les restaurants du groupe via Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return {'success': False, 'error': 'Firestore non disponible'}
            
            source_restaurant = self.get_restaurant_by_id(source_restaurant_id)
            if not source_restaurant:
                return {'success': False, 'error': 'Restaurant source non trouvé'}
            
            sync_settings = source_restaurant.get('sync_settings', {})
            if not sync_settings.get('sync_enabled') or not sync_settings.get('sync_suppliers'):
                return {'success': True, 'message': 'Synchronisation fournisseurs désactivée', 'synced_count': 0}
            
            sync_group = sync_settings.get('sync_group')
            if not sync_group:
                return {'success': True, 'message': 'Aucun groupe de synchronisation', 'synced_count': 0}
            
            # Récupérer tous les restaurants du groupe
            group_restaurants = self.get_restaurants_in_sync_group(sync_group)
            synced_count = 0
            synced_restaurants = []
            
            for restaurant in group_restaurants:
                if restaurant['id'] != source_restaurant_id:  # Ne pas se synchroniser soi-même
                    # Ajouter le fournisseur s'il n'existe pas déjà
                    if 'suppliers' not in restaurant:
                        restaurant['suppliers'] = []
                    
                    if new_supplier not in restaurant['suppliers']:
                        restaurant['suppliers'].append(new_supplier)
                        synced_count += 1
                        synced_restaurants.append(restaurant['name'])
                        
                        # Mettre à jour dans Firestore
                        self._fs.collection('restaurants').document(restaurant['id']).set(restaurant)
            
            if synced_count > 0:
                return {
                    'success': True,
                    'message': f'Fournisseur {new_supplier} synchronisé vers {synced_count} restaurant(s)',
                    'synced_count': synced_count,
                    'synced_restaurants': synced_restaurants,
                    'sync_group': sync_group
                }
            else:
                return {
                    'success': True,
                    'message': 'Fournisseur déjà présent dans tous les restaurants du groupe',
                    'synced_count': 0
                }
                
        except Exception as e:
            logger.error(f"Erreur synchronisation fournisseurs: {e}")
            return {'success': False, 'error': str(e)}
    
    def sync_prices_to_group(self, source_restaurant_name: str, product_data: Dict) -> Dict[str, Any]:
        """Synchroniser un nouveau prix vers tous les restaurants du groupe via Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return {'success': False, 'error': 'Firestore non disponible'}
            
            # Trouver le restaurant source par nom
            restaurants = self.get_restaurants()
            source_restaurant = next((r for r in restaurants if r['name'] == source_restaurant_name), None)
            
            if not source_restaurant:
                return {'success': False, 'error': 'Restaurant source non trouvé'}
            
            sync_settings = source_restaurant.get('sync_settings', {})
            if not sync_settings.get('sync_enabled') or not sync_settings.get('sync_prices'):
                return {'success': True, 'message': 'Synchronisation prix désactivée', 'synced_count': 0}
            
            sync_group = sync_settings.get('sync_group')
            if not sync_group:
                return {'success': True, 'message': 'Aucun groupe de synchronisation', 'synced_count': 0}
            
            # Récupérer tous les restaurants du groupe
            group_restaurants = self.get_restaurants_in_sync_group(sync_group)
            synced_count = 0
            synced_restaurants = []
            
            # Importer le PriceManager pour ajouter les prix
            from modules.price_manager import PriceManager
            price_manager = PriceManager()
            
            for restaurant in group_restaurants:
                if restaurant['name'] != source_restaurant_name:  # Ne pas se synchroniser soi-même
                    # Créer une copie du produit avec le restaurant cible
                    sync_product_data = product_data.copy()
                    sync_product_data['restaurant'] = restaurant['name']
                    
                    # Ajouter le prix pour ce restaurant
                    if price_manager.add_price(sync_product_data):
                        synced_count += 1
                        synced_restaurants.append(restaurant['name'])
            
            if synced_count > 0:
                return {
                    'success': True,
                    'message': f'Prix synchronisé vers {synced_count} restaurant(s)',
                    'synced_count': synced_count,
                    'synced_restaurants': synced_restaurants,
                    'sync_group': sync_group
                }
            else:
                return {
                    'success': True,
                    'message': 'Aucune synchronisation nécessaire',
                    'synced_count': 0
                }
                
        except Exception as e:
            logger.error(f"Erreur synchronisation prix: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_sync_group(self, group_name: str, restaurant_ids: List[str], master_restaurant_id: str) -> Dict[str, Any]:
        """Créer un nouveau groupe de synchronisation dans Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return {'success': False, 'error': 'Firestore non disponible'}
            
            restaurants = self.get_restaurants()
            updated_count = 0
            
            for restaurant_id in restaurant_ids:
                restaurant = next((r for r in restaurants if r['id'] == restaurant_id), None)
                if restaurant:
                    if 'sync_settings' not in restaurant:
                        restaurant['sync_settings'] = {}
                    
                    restaurant['sync_settings'].update({
                        'sync_enabled': True,
                        'sync_suppliers': True,
                        'sync_prices': True,
                        'sync_group': group_name,
                        'sync_master': restaurant_id == master_restaurant_id,
                        'last_sync': datetime.now().isoformat()
                    })
                    
                    # Mettre à jour dans Firestore
                    self._fs.collection('restaurants').document(restaurant_id).set(restaurant)
                    updated_count += 1
            
            if updated_count > 0:
                return {
                    'success': True,
                    'message': f'Groupe de synchronisation "{group_name}" créé avec {updated_count} restaurant(s)',
                    'group_name': group_name,
                    'restaurant_count': updated_count
                }
            else:
                return {'success': False, 'error': 'Aucun restaurant mis à jour'}
                
        except Exception as e:
            logger.error(f"Erreur création groupe sync: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_sync_status(self, restaurant_id: str) -> Dict[str, Any]:
        """Récupérer le statut de synchronisation d'un restaurant depuis Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return {'enabled': False, 'error': 'Firestore non disponible'}
            
            restaurant = self.get_restaurant_by_id(restaurant_id)
            if not restaurant:
                return {'enabled': False, 'error': 'Restaurant non trouvé'}
            
            sync_settings = restaurant.get('sync_settings', {})
            
            return {
                'enabled': sync_settings.get('sync_enabled', False),
                'sync_suppliers': sync_settings.get('sync_suppliers', False),
                'sync_prices': sync_settings.get('sync_prices', False),
                'sync_group': sync_settings.get('sync_group', ''),
                'is_master': sync_settings.get('sync_master', False),
                'last_sync': sync_settings.get('last_sync', ''),
                'last_updated': sync_settings.get('last_updated', '')
            }
        except Exception as e:
            logger.error(f"Erreur récupération statut sync: {e}")
            return {'enabled': False, 'error': str(e)}
    
    def disable_sync(self, restaurant_id: str) -> Dict[str, Any]:
        """Désactiver la synchronisation pour un restaurant dans Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return {'success': False, 'error': 'Firestore non disponible'}
            
            doc_ref = self._fs.collection('restaurants').document(restaurant_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return {'success': False, 'error': 'Restaurant non trouvé'}
            
            restaurant = doc.to_dict()
            if 'sync_settings' not in restaurant:
                restaurant['sync_settings'] = {}
            
            restaurant['sync_settings']['sync_enabled'] = False
            restaurant['sync_settings']['last_updated'] = datetime.now().isoformat()
            
            doc_ref.set(restaurant)
            
            return {'success': True, 'message': 'Synchronisation désactivée'}
        except Exception as e:
            logger.error(f"Erreur désactivation sync: {e}")
            return {'success': False, 'error': str(e)}
    
    def sync_supplier_removal_to_group(self, source_restaurant_id: str, removed_supplier: str) -> Dict[str, Any]:
        """Synchroniser la suppression d'un fournisseur vers tous les restaurants du groupe via Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return {'success': False, 'error': 'Firestore non disponible'}
            
            source_restaurant = self.get_restaurant_by_id(source_restaurant_id)
            if not source_restaurant:
                return {'success': False, 'error': 'Restaurant source non trouvé'}
            
            sync_settings = source_restaurant.get('sync_settings', {})
            if not sync_settings.get('sync_enabled') or not sync_settings.get('sync_suppliers'):
                return {'success': True, 'message': 'Synchronisation fournisseurs désactivée', 'synced_count': 0}
            
            sync_group = sync_settings.get('sync_group')
            if not sync_group:
                return {'success': True, 'message': 'Aucun groupe de synchronisation', 'synced_count': 0}
            
            # Récupérer tous les restaurants du groupe
            group_restaurants = self.get_restaurants_in_sync_group(sync_group)
            synced_count = 0
            synced_restaurants = []
            
            for restaurant in group_restaurants:
                if restaurant['id'] != source_restaurant_id:  # Ne pas se synchroniser soi-même
                    # Retirer le fournisseur s'il existe
                    if 'suppliers' in restaurant and removed_supplier in restaurant['suppliers']:
                        restaurant['suppliers'].remove(removed_supplier)
                        synced_count += 1
                        synced_restaurants.append(restaurant['name'])
                        
                        # Mettre à jour dans Firestore
                        self._fs.collection('restaurants').document(restaurant['id']).set(restaurant)
            
            if synced_count > 0:
                return {
                    'success': True,
                    'message': f'Fournisseur {removed_supplier} retiré de {synced_count} restaurant(s)',
                    'synced_count': synced_count,
                    'synced_restaurants': synced_restaurants,
                    'sync_group': sync_group
                }
            else:
                return {
                    'success': True,
                    'message': 'Fournisseur non présent dans les autres restaurants du groupe',
                    'synced_count': 0
                }
                
        except Exception as e:
            logger.error(f"Erreur synchronisation suppression fournisseur: {e}")
            return {'success': False, 'error': str(e)}
    
    def sync_full_suppliers_list_to_group(self, source_restaurant_id: str) -> Dict[str, Any]:
        """Synchroniser la liste complète des fournisseurs vers tous les restaurants du groupe via Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return {'success': False, 'error': 'Firestore non disponible'}
            
            source_restaurant = self.get_restaurant_by_id(source_restaurant_id)
            if not source_restaurant:
                return {'success': False, 'error': 'Restaurant source non trouvé'}
            
            sync_settings = source_restaurant.get('sync_settings', {})
            if not sync_settings.get('sync_enabled') or not sync_settings.get('sync_suppliers'):
                return {'success': True, 'message': 'Synchronisation fournisseurs désactivée', 'synced_count': 0}
            
            sync_group = sync_settings.get('sync_group')
            if not sync_group:
                return {'success': True, 'message': 'Aucun groupe de synchronisation', 'synced_count': 0}
            
            # Récupérer tous les restaurants du groupe
            group_restaurants = self.get_restaurants_in_sync_group(sync_group)
            synced_count = 0
            synced_restaurants = []
            
            source_suppliers = source_restaurant.get('suppliers', [])
            
            for restaurant in group_restaurants:
                if restaurant['id'] != source_restaurant_id:  # Ne pas se synchroniser soi-même
                    # Remplacer complètement la liste des fournisseurs
                    restaurant['suppliers'] = source_suppliers.copy()
                    synced_count += 1
                    synced_restaurants.append(restaurant['name'])
                    
                    # Mettre à jour dans Firestore
                    self._fs.collection('restaurants').document(restaurant['id']).set(restaurant)
            
            if synced_count > 0:
                return {
                    'success': True,
                    'message': f'Liste complète des fournisseurs synchronisée vers {synced_count} restaurant(s)',
                    'synced_count': synced_count,
                    'synced_restaurants': synced_restaurants,
                    'sync_group': sync_group,
                    'suppliers_count': len(source_suppliers)
                }
            else:
                return {
                    'success': True,
                    'message': 'Aucune synchronisation nécessaire',
                    'synced_count': 0
                }
                
        except Exception as e:
            logger.error(f"Erreur synchronisation liste complète fournisseurs: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_available_restaurants_for_sync(self, client_id: str) -> List[Dict]:
        """Récupérer les restaurants disponibles pour la synchronisation depuis Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return []
            
            restaurants = self.get_restaurants()
            return [
                {
                    'id': r['id'],
                    'name': r['name'],
                    'sync_enabled': r.get('sync_settings', {}).get('sync_enabled', False),
                    'sync_group': r.get('sync_settings', {}).get('sync_group', ''),
                    'is_master': r.get('sync_settings', {}).get('sync_master', False)
                }
                for r in restaurants
            ]
        except Exception as e:
            logger.error(f"Erreur récupération restaurants disponibles: {e}")
            return []

# Instance globale
sync_manager = SyncManager() 