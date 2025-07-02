"""
🔄 FactureKiller V3 - Gestionnaire de Synchronisation Multi-Restaurants
Synchronisation automatique des fournisseurs et prix entre restaurants d'un même groupe
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SyncManager:
    """Gestionnaire de synchronisation entre restaurants"""
    
    def __init__(self):
        self.restaurants_file = 'data/restaurants.json'
        self.prices_file = 'data/prices.csv'
        self.suppliers_file = 'data/suppliers.json'
        
    def get_restaurants(self) -> List[Dict]:
        """Récupérer tous les restaurants"""
        if os.path.exists(self.restaurants_file):
            try:
                with open(self.restaurants_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erreur lecture restaurants: {e}")
        return []
    
    def save_restaurants(self, restaurants: List[Dict]) -> bool:
        """Sauvegarder les restaurants"""
        try:
            with open(self.restaurants_file, 'w', encoding='utf-8') as f:
                json.dump(restaurants, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Erreur sauvegarde restaurants: {e}")
            return False
    
    def get_restaurant_by_id(self, restaurant_id: str) -> Optional[Dict]:
        """Récupérer un restaurant par son ID"""
        restaurants = self.get_restaurants()
        return next((r for r in restaurants if r['id'] == restaurant_id), None)
    
    def update_sync_settings(self, restaurant_id: str, sync_settings: Dict) -> Dict[str, Any]:
        """Mettre à jour les paramètres de synchronisation d'un restaurant"""
        try:
            restaurants = self.get_restaurants()
            restaurant = next((r for r in restaurants if r['id'] == restaurant_id), None)
            
            if not restaurant:
                return {'success': False, 'error': 'Restaurant non trouvé'}
            
            # Mettre à jour les paramètres
            if 'sync_settings' not in restaurant:
                restaurant['sync_settings'] = {}
            
            restaurant['sync_settings'].update(sync_settings)
            restaurant['sync_settings']['last_updated'] = datetime.now().isoformat()
            
            # Sauvegarder
            if self.save_restaurants(restaurants):
                return {
                    'success': True,
                    'message': 'Paramètres de synchronisation mis à jour',
                    'restaurant': restaurant
                }
            else:
                return {'success': False, 'error': 'Erreur de sauvegarde'}
                
        except Exception as e:
            logger.error(f"Erreur mise à jour sync settings: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_sync_groups(self) -> Dict[str, List[Dict]]:
        """Récupérer les groupes de synchronisation"""
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
    
    def get_restaurants_in_sync_group(self, sync_group: str) -> List[Dict]:
        """Récupérer tous les restaurants d'un groupe de synchronisation"""
        restaurants = self.get_restaurants()
        return [
            r for r in restaurants 
            if r.get('sync_settings', {}).get('sync_enabled') 
            and r.get('sync_settings', {}).get('sync_group') == sync_group
        ]
    
    def sync_suppliers_to_group(self, source_restaurant_id: str, new_supplier: str) -> Dict[str, Any]:
        """Synchroniser un nouveau fournisseur vers tous les restaurants du groupe"""
        try:
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
            
            restaurants = self.get_restaurants()
            
            for restaurant in group_restaurants:
                if restaurant['id'] != source_restaurant_id:  # Ne pas se synchroniser soi-même
                    # 🚫 VÉRIFIER LA LISTE D'EXCLUSION
                    excluded_suppliers = restaurant.get('excluded_suppliers', [])
                    if new_supplier in excluded_suppliers:
                        logger.info(f"Fournisseur '{new_supplier}' exclu de la synchronisation pour {restaurant['name']}")
                        continue
                    
                    # Ajouter le fournisseur s'il n'existe pas déjà
                    if 'suppliers' not in restaurant:
                        restaurant['suppliers'] = []
                    
                    if new_supplier not in restaurant['suppliers']:
                        restaurant['suppliers'].append(new_supplier)
                        synced_count += 1
                        synced_restaurants.append(restaurant['name'])
                        
                        # Mettre à jour dans la liste principale
                        for i, r in enumerate(restaurants):
                            if r['id'] == restaurant['id']:
                                restaurants[i] = restaurant
                                break
            
            # Sauvegarder les modifications
            if synced_count > 0:
                if self.save_restaurants(restaurants):
                    return {
                        'success': True,
                        'message': f'Fournisseur {new_supplier} synchronisé vers {synced_count} restaurant(s)',
                        'synced_count': synced_count,
                        'synced_restaurants': synced_restaurants,
                        'sync_group': sync_group
                    }
                else:
                    return {'success': False, 'error': 'Erreur de sauvegarde'}
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
        """Synchroniser un nouveau prix vers tous les restaurants du groupe"""
        try:
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
            import sys
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from price_manager import PriceManager
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
        """Créer un nouveau groupe de synchronisation"""
        try:
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
                    updated_count += 1
            
            if self.save_restaurants(restaurants):
                return {
                    'success': True,
                    'message': f'Groupe de synchronisation "{group_name}" créé avec {updated_count} restaurant(s)',
                    'group_name': group_name,
                    'restaurant_count': updated_count
                }
            else:
                return {'success': False, 'error': 'Erreur de sauvegarde'}
                
        except Exception as e:
            logger.error(f"Erreur création groupe sync: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_sync_status(self, restaurant_id: str) -> Dict[str, Any]:
        """Récupérer le statut de synchronisation d'un restaurant"""
        restaurant = self.get_restaurant_by_id(restaurant_id)
        if not restaurant:
            return {'success': False, 'error': 'Restaurant non trouvé'}
        
        sync_settings = restaurant.get('sync_settings', {})
        sync_group = sync_settings.get('sync_group')
        
        result = {
            'success': True,
            'restaurant': restaurant['name'],
            'sync_enabled': sync_settings.get('sync_enabled', False),
            'sync_suppliers': sync_settings.get('sync_suppliers', False),
            'sync_prices': sync_settings.get('sync_prices', False),
            'sync_group': sync_group,
            'sync_master': sync_settings.get('sync_master', False),
            'last_sync': sync_settings.get('last_sync'),
            'group_restaurants': []
        }
        
        if sync_group:
            group_restaurants = self.get_restaurants_in_sync_group(sync_group)
            result['group_restaurants'] = [
                {
                    'id': r['id'],
                    'name': r['name'],
                    'is_master': r.get('sync_settings', {}).get('sync_master', False)
                }
                for r in group_restaurants
            ]
        
        return result
    
    def disable_sync(self, restaurant_id: str) -> Dict[str, Any]:
        """Désactiver la synchronisation pour un restaurant"""
        return self.update_sync_settings(restaurant_id, {
            'sync_enabled': False,
            'sync_suppliers': False,
            'sync_prices': False,
            'sync_group': None,
            'sync_master': False
        })
    
    def exclude_supplier_from_sync(self, restaurant_id: str, supplier_name: str) -> Dict[str, Any]:
        """Exclure un fournisseur de la synchronisation pour un restaurant spécifique"""
        try:
            restaurants = self.get_restaurants()
            restaurant = next((r for r in restaurants if r['id'] == restaurant_id), None)
            
            if not restaurant:
                return {'success': False, 'error': 'Restaurant non trouvé'}
            
            # Initialiser la liste d'exclusion si elle n'existe pas
            if 'excluded_suppliers' not in restaurant:
                restaurant['excluded_suppliers'] = []
            
            # Ajouter le fournisseur à la liste d'exclusion s'il n'y est pas déjà
            if supplier_name not in restaurant['excluded_suppliers']:
                restaurant['excluded_suppliers'].append(supplier_name)
                
                # Retirer le fournisseur de la liste des fournisseurs actifs
                if 'suppliers' in restaurant and supplier_name in restaurant['suppliers']:
                    restaurant['suppliers'].remove(supplier_name)
                
                # Mettre à jour la liste des restaurants
                for i, r in enumerate(restaurants):
                    if r['id'] == restaurant_id:
                        restaurants[i] = restaurant
                        break
                
                # Sauvegarder
                if self.save_restaurants(restaurants):
                    return {
                        'success': True,
                        'message': f"Fournisseur '{supplier_name}' exclu de la synchronisation pour {restaurant['name']}"
                    }
                else:
                    return {'success': False, 'error': 'Erreur de sauvegarde'}
            else:
                return {
                    'success': True,
                    'message': f"Fournisseur '{supplier_name}' déjà exclu pour {restaurant['name']}"
                }
                
        except Exception as e:
            logger.error(f"Erreur exclusion fournisseur: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_available_restaurants_for_sync(self, client_id: str) -> List[Dict]:
        """Récupérer les restaurants disponibles pour la synchronisation (même client)"""
        restaurants = self.get_restaurants()
        return [
            {
                'id': r['id'],
                'name': r['name'],
                'sync_enabled': r.get('sync_settings', {}).get('sync_enabled', False),
                'sync_group': r.get('sync_settings', {}).get('sync_group'),
                'suppliers_count': len(r.get('suppliers', []))
            }
            for r in restaurants 
            if r.get('client_id') == client_id and r.get('active', True)
        ] 