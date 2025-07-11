#!/usr/bin/env python3
"""
Gestionnaire des fournisseurs et de leurs produits
Combine les prix validés et les produits en attente
"""

import json
import csv
import os
from datetime import datetime
from typing import List, Dict, Optional
from modules.firestore_db import available as _fs_available, get_client as _fs_client

class SupplierManager:
    def __init__(self):
        """Initialiser le gestionnaire de fournisseurs (Firestore uniquement)"""
        # 🔥 FIRESTORE UNIQUEMENT - Plus de fichiers locaux
        self._fs_enabled = False
        self._fs = None
        
        # Initialiser Firestore
        try:
            from modules.firestore_db import FirestoreDB
            firestore_db = FirestoreDB()
            self._fs = firestore_db.db
            self._fs_enabled = True
            print("✅ Firestore initialisé pour SupplierManager")
        except Exception as e:
            print(f"❌ Erreur initialisation Firestore SupplierManager: {e}")
            self._fs_enabled = False
            self._fs = None
    
    def _get_deleted_suppliers(self) -> set:
        """Récupérer la liste des fournisseurs explicitement supprimés depuis Firestore"""
        deleted_suppliers = set()
        
        if not self._fs_enabled:
            return deleted_suppliers
        
        try:
            docs = self._fs.collection('deleted_suppliers').stream()
            for doc in docs:
                data = doc.to_dict()
                if data.get('name'):
                    deleted_suppliers.add(data['name'])
            print(f"📊 Firestore deleted suppliers: {len(deleted_suppliers)}")
        except Exception as e:
            print(f"❌ Erreur lecture deleted suppliers Firestore: {e}")
        
        return deleted_suppliers
    
    def _add_to_deleted_suppliers(self, supplier_name: str):
        """Ajouter un fournisseur à la liste des supprimés dans Firestore"""
        try:
            if not self._fs_enabled:
                return
            
            self._fs.collection('deleted_suppliers').add({
                'name': supplier_name,
                'deleted_at': datetime.now().isoformat()
            })
            print(f"✅ {supplier_name} ajouté aux supprimés Firestore")
        except Exception as e:
            print(f"❌ Erreur ajout deleted supplier Firestore: {e}")
    
    def _remove_from_deleted_suppliers(self, supplier_name: str):
        """Retirer un fournisseur de la liste des supprimés dans Firestore"""
        try:
            if not self._fs_enabled:
                return
            
            docs = list(self._fs.collection('deleted_suppliers').where('name', '==', supplier_name).stream())
            for doc in docs:
                doc.reference.delete()
            print(f"✅ {supplier_name} retiré des supprimés Firestore")
        except Exception as e:
            print(f"❌ Erreur retrait deleted supplier Firestore: {e}")

    def get_all_suppliers(self) -> List[Dict]:
        """Récupérer tous les fournisseurs depuis Firestore uniquement"""
        suppliers = []
        
        print(f"🔧 Firestore enabled: {getattr(self, '_fs_enabled', False)}")
        print(f"🔧 Firestore client: {getattr(self, '_fs', None)}")
        
        # 🔥 FIRESTORE UNIQUEMENT - Plus de fallback fichiers locaux
        if getattr(self, '_fs_enabled', False) and getattr(self, '_fs', None):
            try:
                docs = list(self._fs.collection('suppliers').stream())
                for doc in docs:
                    data = doc.to_dict()
                    # Ajouter les statistiques calculées depuis Firestore
                    stats = self._get_supplier_stats_firestore(data['name'])
                    data.update(stats)
                    suppliers.append(data)
                print(f"📊 Firestore: {len(suppliers)} fournisseurs récupérés")
            except Exception as e:
                print(f"❌ Firestore get_all_suppliers KO: {e}")
                # En cas d'erreur Firestore, retourner une liste vide
                return []
        else:
            print("❌ Firestore non disponible - impossible de récupérer les fournisseurs")
            return []
        
        print(f"🎯 Total: {len(suppliers)} fournisseurs retournés")
        return suppliers
    
    def _get_supplier_stats_firestore(self, supplier_name: str) -> Dict:
        """Calculer les statistiques d'un fournisseur depuis Firestore uniquement"""
        validated_products = self._get_validated_products_firestore(supplier_name)
        pending_products = self._get_pending_products_firestore(supplier_name)
        
        return {
            'products_count': len(validated_products),
            'validated_count': len(validated_products),
            'pending_count': len(pending_products),
            'products': validated_products,
            'validated_products': validated_products,
            'pending_products': pending_products,
            'total_products_count': len(validated_products) + len(pending_products),
            'last_updated': datetime.now().isoformat()
        }
    
    def _get_validated_products_firestore(self, supplier_name: str) -> List[Dict]:
        """Récupérer les produits validés d'un fournisseur depuis Firestore uniquement"""
        products = []
        if self._fs_enabled:
            try:
                docs = self._fs.collection('prices').where('fournisseur', '==', supplier_name).stream()
                for d in docs:
                    row = d.to_dict()
                    products.append({
                        'id': row.get('code') or d.id,
                        'name': row.get('produit', ''),
                        'produit': row.get('produit', ''),
                        'code': row.get('code', ''),
                        'unit_price': float(row.get('prix') or row.get('prix_unitaire', 0)),
                        'unite': row.get('unite', 'unité'),
                        'category': row.get('categorie', ''),
                        'date_added': row.get('date_maj') or row.get('date_ajout', '')
                    })
                print(f"📊 Firestore validated products for {supplier_name}: {len(products)}")
            except Exception as e:
                print(f"❌ Firestore _get_validated_products KO: {e}")
        
        return products
    
    def _get_pending_products_firestore(self, supplier_name: str) -> List[Dict]:
        """Récupérer les produits en attente d'un fournisseur depuis Firestore uniquement"""
        products = []
        if self._fs_enabled:
            try:
                docs = self._fs.collection('pending_products').where('fournisseur', '==', supplier_name).stream()
                for d in docs:
                    row = d.to_dict()
                    products.append({
                        'id': row.get('code') or d.id,
                        'name': row.get('produit', ''),
                        'produit': row.get('produit', ''),
                        'code': row.get('code', ''),
                        'unit_price': float(row.get('prix', 0)),
                        'unite': row.get('unite', 'unité'),
                        'category': row.get('categorie', ''),
                        'date_added': row.get('date_ajout', ''),
                        'status': 'pending'
                    })
                print(f"📊 Firestore pending products for {supplier_name}: {len(products)}")
            except Exception as e:
                print(f"❌ Firestore _get_pending_products KO: {e}")
        
        return products
    
    def _get_all_supplier_names_from_products(self) -> set:
        """Récupérer tous les noms de fournisseurs depuis Firestore uniquement"""
        names = set()
        
        if not self._fs_enabled:
            return names
        
        try:
            # Depuis les prix validés
            docs = self._fs.collection('prices').stream()
            for d in docs:
                row = d.to_dict()
                if row.get('fournisseur'):
                    names.add(row['fournisseur'])
            print(f"🔍 Firestore prix validés: {len(names)} fournisseurs trouvés")
        except Exception as e:
            print(f"❌ Erreur lecture prix validés Firestore: {e}")
        
        try:
            # Depuis les produits en attente
            docs = self._fs.collection('pending_products').stream()
            for d in docs:
                row = d.to_dict()
                if row.get('fournisseur'):
                    names.add(row['fournisseur'])
            print(f"🔍 Firestore produits en attente: {len(names)} fournisseurs trouvés")
        except Exception as e:
            print(f"❌ Erreur lecture produits en attente Firestore: {e}")
        
        print(f"🎯 Fournisseurs trouvés dans Firestore: {list(names)}")
        return names
    
    def _get_supplier_stats(self, supplier_name: str) -> Dict:
        """Calculer les statistiques d'un fournisseur (Firestore uniquement)"""
        return self._get_supplier_stats_firestore(supplier_name)
    
    def _get_validated_products(self, supplier_name: str) -> List[Dict]:
        """Récupérer les produits validés d'un fournisseur (Firestore uniquement)"""
        return self._get_validated_products_firestore(supplier_name)
    
    def _get_pending_products(self, supplier_name: str) -> List[Dict]:
        """Récupérer les produits en attente d'un fournisseur (Firestore uniquement)"""
        return self._get_pending_products_firestore(supplier_name)
    
    def get_supplier_products(self, supplier_name: str) -> List[Dict]:
        """Récupérer tous les produits d'un fournisseur (validés + en attente)"""
        validated = self._get_validated_products(supplier_name)
        pending = self._get_pending_products(supplier_name)
        
        # Combiner et trier par nom
        all_products = validated + pending
        all_products.sort(key=lambda x: x.get('name', '').lower())
        
        return all_products
    
    def save_supplier(self, supplier_data: Dict) -> bool:
        """Sauvegarder un fournisseur dans Firestore uniquement avec restaurant/groupe"""
        try:
            if not self._fs_enabled:
                print("❌ Firestore non disponible")
                return False
            
            supplier_name = supplier_data.get('name')
            if not supplier_name:
                print("❌ Nom de fournisseur manquant")
                return False
            
            # 🔥 AJOUTER AUTOMATIQUEMENT LE RESTAURANT/GROUPE SÉLECTIONNÉ
            # Récupérer le contexte utilisateur pour obtenir le restaurant actuel
            try:
                from modules.auth_manager import AuthManager
                auth_manager = AuthManager()
                user_context = auth_manager.get_user_context()
                current_restaurant = user_context.get('restaurant', {})
                
                if current_restaurant:
                    supplier_data['restaurant_id'] = current_restaurant.get('id', '')
                    supplier_data['restaurant_name'] = current_restaurant.get('name', '')
                    supplier_data['restaurant_group'] = current_restaurant.get('group', '')
                    print(f"🏪 Restaurant ajouté au fournisseur: {current_restaurant.get('name', '')}")
                else:
                    print("⚠️ Aucun restaurant sélectionné, fournisseur créé sans restaurant")
                    supplier_data['restaurant_id'] = ''
                    supplier_data['restaurant_name'] = ''
                    supplier_data['restaurant_group'] = ''
                    
            except Exception as e:
                print(f"⚠️ Erreur récupération contexte restaurant: {e}")
                supplier_data['restaurant_id'] = ''
                supplier_data['restaurant_name'] = ''
                supplier_data['restaurant_group'] = ''
            
            # Vérifier si le fournisseur existe déjà
            existing_docs = list(self._fs.collection('suppliers').where('name', '==', supplier_name).stream())
            
            if existing_docs:
                # Mettre à jour le fournisseur existant
                doc_ref = existing_docs[0].reference
                supplier_data['updated_at'] = datetime.now().isoformat()
                doc_ref.update(supplier_data)
                print(f"✅ Fournisseur {supplier_name} mis à jour dans Firestore")
            else:
                # Créer un nouveau fournisseur
                supplier_data['created_at'] = datetime.now().isoformat()
                supplier_data['updated_at'] = datetime.now().isoformat()
                self._fs.collection('suppliers').add(supplier_data)
                print(f"✅ Fournisseur {supplier_name} créé dans Firestore")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur sauvegarde fournisseur Firestore: {e}")
            return False
    
    def delete_supplier(self, supplier_name: str) -> bool:
        """Supprimer un fournisseur et tous ses produits de Firestore uniquement"""
        try:
            if not self._fs_enabled:
                print("❌ Firestore non disponible")
                return False
            
            # 1️⃣ Supprimer le fournisseur
            supplier_docs = list(self._fs.collection('suppliers').where('name', '==', supplier_name).stream())
            if supplier_docs:
                supplier_docs[0].reference.delete()
                print(f"✅ Fournisseur {supplier_name} supprimé de Firestore")
            
            # 2️⃣ Supprimer tous les produits validés du fournisseur
            validated_docs = list(self._fs.collection('prices').where('fournisseur', '==', supplier_name).stream())
            for doc in validated_docs:
                doc.reference.delete()
            print(f"✅ {len(validated_docs)} produits validés supprimés de Firestore")
            
            # 3️⃣ Supprimer tous les produits en attente du fournisseur
            pending_docs = list(self._fs.collection('pending_products').where('fournisseur', '==', supplier_name).stream())
            for doc in pending_docs:
                doc.reference.delete()
            print(f"✅ {len(pending_docs)} produits en attente supprimés de Firestore")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur suppression fournisseur Firestore: {e}")
            return False
    
    def add_product_to_supplier(self, supplier_name: str, product_data: Dict) -> bool:
        """Ajouter un produit à un fournisseur dans Firestore uniquement"""
        try:
            if not self._fs_enabled:
                print("❌ Firestore non disponible")
                return False
            
            # Déterminer la collection selon le statut
            collection_name = 'pending_products' if product_data.get('status') == 'pending' else 'prices'
            
            # Ajouter les métadonnées
            product_data['fournisseur'] = supplier_name
            product_data['date_ajout'] = datetime.now().isoformat()
            product_data['date_maj'] = datetime.now().isoformat()
            
            # Sauvegarder dans Firestore
            self._fs.collection(collection_name).add(product_data)
            print(f"✅ Produit ajouté à {supplier_name} dans Firestore ({collection_name})")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur ajout produit Firestore: {e}")
            return False
    
    def update_product(self, supplier_name: str, product_id: str, product_data: Dict) -> bool:
        """Mettre à jour un produit dans Firestore uniquement"""
        try:
            if not self._fs_enabled:
                print("❌ Firestore non disponible")
                return False
            
            # Chercher dans les deux collections
            for collection_name in ['prices', 'pending_products']:
                docs = list(self._fs.collection(collection_name).where('code', '==', product_id).stream())
                if docs:
                    product_data['date_maj'] = datetime.now().isoformat()
                    docs[0].reference.update(product_data)
                    print(f"✅ Produit {product_id} mis à jour dans Firestore ({collection_name})")
                    return True
            
            print(f"❌ Produit {product_id} non trouvé dans Firestore")
            return False
            
        except Exception as e:
            print(f"❌ Erreur mise à jour produit Firestore: {e}")
            return False
    
    def delete_product(self, supplier_name: str, product_id: str) -> bool:
        """Supprimer un produit de Firestore uniquement"""
        try:
            if not self._fs_enabled:
                print("❌ Firestore non disponible")
                return False
            
            # Chercher dans les deux collections
            for collection_name in ['prices', 'pending_products']:
                docs = list(self._fs.collection(collection_name).where('code', '==', product_id).stream())
                if docs:
                    docs[0].reference.delete()
                    print(f"✅ Produit {product_id} supprimé de Firestore ({collection_name})")
                    return True
            
            print(f"❌ Produit {product_id} non trouvé dans Firestore")
            return False
            
        except Exception as e:
            print(f"❌ Erreur suppression produit Firestore: {e}")
            return False 