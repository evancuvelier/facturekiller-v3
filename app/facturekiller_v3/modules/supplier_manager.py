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
        self.suppliers_file = 'data/suppliers.json'
        self.prices_file = 'data/prices.csv'
        self.pending_file = 'data/pending_products.csv'
        self.deleted_suppliers_file = 'data/deleted_suppliers.json'  # Nouveau fichier pour les supprimés
        
        # Firestore
        self._fs_enabled = _fs_available()
        self._fs = _fs_client() if self._fs_enabled else None
        
        # Créer les fichiers s'ils n'existent pas
        self._ensure_files_exist()
    
    def _ensure_files_exist(self):
        """Créer les fichiers de base s'ils n'existent pas"""
        if not os.path.exists(self.suppliers_file):
            with open(self.suppliers_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        
        # Nouveau fichier pour les fournisseurs supprimés
        if not os.path.exists(self.deleted_suppliers_file):
            with open(self.deleted_suppliers_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        
        # Vérifier et corriger le format du fichier prices.csv
        if not os.path.exists(self.prices_file):
            with open(self.prices_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'code', 'produit', 'fournisseur', 'prix_unitaire', 'unite', 'categorie', 'date_ajout'])
        else:
            # Vérifier l'en-tête existant
            with open(self.prices_file, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                expected_header = 'id,code,produit,fournisseur,prix_unitaire,unite,categorie,date_ajout'
                if first_line != expected_header:
                    print(f"⚠️ Format de prices.csv incorrect. Attendu: {expected_header}")
                    print(f"   Trouvé: {first_line}")
                    # Sauvegarder et recréer avec le bon format
                    self._fix_prices_file_format()
        
        if not os.path.exists(self.pending_file):
            with open(self.pending_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'code', 'produit', 'fournisseur', 'prix', 'unite', 'categorie', 'date_ajout', 'source'])
    
    def _get_deleted_suppliers(self) -> set:
        """Récupérer la liste des fournisseurs explicitement supprimés"""
        try:
            with open(self.deleted_suppliers_file, 'r', encoding='utf-8') as f:
                deleted_list = json.load(f)
                return set(deleted_list)
        except:
            return set()
    
    def _add_to_deleted_suppliers(self, supplier_name: str):
        """Ajouter un fournisseur à la liste des supprimés"""
        try:
            deleted_suppliers = list(self._get_deleted_suppliers())
            if supplier_name not in deleted_suppliers:
                deleted_suppliers.append(supplier_name)
                with open(self.deleted_suppliers_file, 'w', encoding='utf-8') as f:
                    json.dump(deleted_suppliers, f, ensure_ascii=False, indent=2)
                print(f"📝 Fournisseur '{supplier_name}' ajouté à la liste des supprimés")
        except Exception as e:
            print(f"Erreur ajout à la liste des supprimés: {e}")

    def _remove_from_deleted_suppliers(self, supplier_name: str):
        """Retirer un fournisseur de la liste des supprimés"""
        try:
            deleted = list(self._get_deleted_suppliers())
            if supplier_name in deleted:
                deleted.remove(supplier_name)
                with open(self.deleted_suppliers_file, 'w', encoding='utf-8') as f:
                    json.dump(deleted, f, ensure_ascii=False, indent=2)
                print(f"♻️ Fournisseur '{supplier_name}' retiré de la liste des supprimés")
        except Exception as e:
            print(f"Erreur suppression de la liste deleted_suppliers: {e}")

    def get_all_suppliers(self) -> List[Dict]:
        """Récupérer tous les fournisseurs avec leurs statistiques"""
        # 1️⃣ Firestore d'abord
        if getattr(self, '_fs_enabled', False):
            try:
                docs = list(self._fs.collection('suppliers').stream())
                suppliers_fs = []
                for doc in docs:
                    data = doc.to_dict()
                    stats = self._get_supplier_stats(data['name'])
                    data.update(stats)
                    suppliers_fs.append(data)

                # Même si la collection est vide on renvoie la liste (pour ne pas tomber sur le legacy)
                return suppliers_fs
            except Exception as e:
                print(f"Firestore get_all_suppliers KO: {e}")

        try:
            # Charger les fournisseurs de base
            with open(self.suppliers_file, 'r', encoding='utf-8') as f:
                suppliers = json.load(f)
            
            # Ajouter les statistiques de produits
            for supplier in suppliers:
                supplier_stats = self._get_supplier_stats(supplier['name'])
                supplier.update(supplier_stats)
            
            # Récupérer les fournisseurs supprimés pour les exclure
            deleted_suppliers = self._get_deleted_suppliers()
            
            # Ajouter les fournisseurs qui ont des produits mais pas de fiche
            # SAUF ceux qui ont été explicitement supprimés
            all_supplier_names = self._get_all_supplier_names_from_products()
            existing_names = {s['name'] for s in suppliers}
            
            for name in all_supplier_names:
                if name not in existing_names and name not in deleted_suppliers:
                    supplier_stats = self._get_supplier_stats(name)
                    suppliers.append({
                        'name': name,
                        'email': '',
                        'delivery_days': [],
                        'notes': 'Fournisseur créé automatiquement',
                        'created_at': datetime.now().isoformat(),
                        **supplier_stats
                    })
            
            # Sauvegarder la liste des fournisseurs
            with open(self.suppliers_file, 'w', encoding='utf-8') as f:
                json.dump(suppliers, f, ensure_ascii=False, indent=2)

            return suppliers
            
        except Exception as e:
            print(f"Erreur lors du chargement des fournisseurs: {e}")
            return []
    
    def _get_all_supplier_names_from_products(self) -> set:
        """Récupérer tous les noms de fournisseurs depuis les produits"""
        names = set()
        
        # Depuis les prix validés
        try:
            with open(self.prices_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('fournisseur'):
                        names.add(row['fournisseur'])
        except:
            pass
        
        # Depuis les produits en attente
        try:
            with open(self.pending_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('fournisseur'):
                        names.add(row['fournisseur'])
        except:
            pass
        
        return names
    
    def _get_supplier_stats(self, supplier_name: str) -> Dict:
        """Calculer les statistiques d'un fournisseur"""
        validated_products = self._get_validated_products(supplier_name)
        pending_products = self._get_pending_products(supplier_name)
        
        # ✅ CORRECTION : Séparer clairement validés et pending
        return {
            'products_count': len(validated_products),  # ← SEULEMENT les validés dans le compte
            'validated_count': len(validated_products),
            'pending_count': len(pending_products),
            'products': validated_products,  # ← SEULEMENT les produits validés
            'validated_products': validated_products,  # ← Ajout explicite
            'pending_products': pending_products,  # ← Ajout explicite  
            'total_products_count': len(validated_products) + len(pending_products),  # ← Total si besoin
            'last_updated': datetime.now().isoformat()
        }
    
    def _get_validated_products(self, supplier_name: str) -> List[Dict]:
        """Récupérer les produits validés d'un fournisseur"""
        products = []
        # 1️⃣ Priorité Firestore si disponible
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
            except Exception as e:
                print(f"Firestore _get_validated_products KO: {e}")

        # 2️⃣ Compléter avec le fichier local (pour backup / historique)
        try:
            if os.path.exists(self.prices_file):
                with open(self.prices_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('fournisseur') == supplier_name:
                            products.append({
                                'id': row.get('id', ''),
                                'name': row.get('produit', ''),
                                'produit': row.get('produit', ''),
                                'code': row.get('code', ''),
                                'unit_price': float(row.get('prix_unitaire') or row.get('prix') or 0),
                                'unite': row.get('unite', 'unité'),
                                'category': row.get('categorie', ''),
                                'date_added': row.get('date_ajout', '')
                            })
        except Exception as e:
            print(f"CSV _get_validated_products KO: {e}")
        
        return products
    
    def _get_pending_products(self, supplier_name: str) -> List[Dict]:
        """Récupérer les produits en attente d'un fournisseur"""
        products = []
        try:
            with open(self.pending_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('fournisseur') == supplier_name:
                        products.append({
                            'id': row.get('id', ''),
                            'name': row.get('produit', ''),
                            'produit': row.get('produit', ''),  # Pour compatibilité
                            'code': row.get('code', ''),
                            'unit_price': float(row.get('prix', 0)),
                            'prix_unitaire': float(row.get('prix', 0)),  # Pour compatibilité
                            'unit': row.get('unite', ''),
                            'unite': row.get('unite', ''),  # Pour compatibilité
                            'category': row.get('categorie', ''),
                            'status': 'pending',
                            'date_added': row.get('date_ajout', ''),
                            'source': row.get('source', '')
                        })
        except Exception as e:
            print(f"Erreur lecture produits en attente: {e}")
        
        return products
    
    def get_supplier_products(self, supplier_name: str) -> List[Dict]:
        """Récupérer tous les produits d'un fournisseur (validés + en attente)"""
        validated = self._get_validated_products(supplier_name)
        pending = self._get_pending_products(supplier_name)
        
        # Combiner et trier par nom
        all_products = validated + pending
        all_products.sort(key=lambda x: x.get('name', '').lower())
        
        return all_products
    
    def save_supplier(self, supplier_data: Dict) -> bool:
        """Sauvegarder ou mettre à jour un fournisseur"""
        try:
            suppliers = []
            
            # Charger les fournisseurs existants
            if os.path.exists(self.suppliers_file):
                with open(self.suppliers_file, 'r', encoding='utf-8') as f:
                    suppliers = json.load(f)
            
            # Chercher si le fournisseur existe déjà
            supplier_name = supplier_data.get('name', '')
            existing_index = -1
            for i, supplier in enumerate(suppliers):
                if supplier.get('name') == supplier_name:
                    existing_index = i
                    break
            
            # Préparer les données du fournisseur
            supplier_record = {
                'name': supplier_name,
                'email': supplier_data.get('email', ''),
                'delivery_days': supplier_data.get('delivery_days', []),
                'notes': supplier_data.get('notes', ''),
                'updated_at': datetime.now().isoformat()
            }
            
            if existing_index >= 0:
                # Mettre à jour
                supplier_record['created_at'] = suppliers[existing_index].get('created_at', datetime.now().isoformat())
                suppliers[existing_index] = supplier_record
            else:
                # Ajouter nouveau
                supplier_record['created_at'] = datetime.now().isoformat()
                suppliers.append(supplier_record)
            
            # Sauvegarder la liste
            with open(self.suppliers_file, 'w', encoding='utf-8') as f:
                json.dump(suppliers, f, ensure_ascii=False, indent=2)

            # ➕ Autoriser la recréation : retirer de deleted_suppliers.json si présent
            self._remove_from_deleted_suppliers(supplier_name)

            # Firestore save / update
            if getattr(self, '_fs_enabled', False):
                try:
                    self._fs.collection('suppliers').document(supplier_name).set(supplier_record)
                except Exception as e:
                    print(f"Firestore save_supplier KO: {e}")
            
            return True
            
        except Exception as e:
            print(f"Erreur sauvegarde fournisseur: {e}")
            return False
    
    def delete_supplier(self, supplier_name: str) -> bool:
        """Supprimer un fournisseur ET tous ses produits"""
        try:
            # 1. Ajouter à la liste des fournisseurs supprimés AVANT de supprimer
            self._add_to_deleted_suppliers(supplier_name)
            
            # 2. Supprimer la fiche fournisseur
            suppliers = []
            if os.path.exists(self.suppliers_file):
                with open(self.suppliers_file, 'r', encoding='utf-8') as f:
                    suppliers = json.load(f)
            
            # Filtrer pour supprimer le fournisseur
            suppliers = [s for s in suppliers if s.get('name') != supplier_name]
            
            # Sauvegarder la liste des fournisseurs
            with open(self.suppliers_file, 'w', encoding='utf-8') as f:
                json.dump(suppliers, f, ensure_ascii=False, indent=2)
            
            # 3. Supprimer les produits validés du fournisseur
            self._remove_supplier_from_prices(supplier_name)
            
            # 4. Supprimer les produits en attente du fournisseur
            self._remove_supplier_from_pending(supplier_name)
            
            # 5. Supprimer le document Firestore
            if getattr(self, '_fs_enabled', False):
                try:
                    self._fs.collection('suppliers').document(supplier_name).delete()
                except Exception as e:
                    print(f"Firestore delete_supplier KO: {e}")

            print(f"✅ Fournisseur '{supplier_name}' et tous ses produits supprimés")
            return True
            
        except Exception as e:
            print(f"Erreur suppression fournisseur: {e}")
            return False
    
    def _remove_supplier_from_prices(self, supplier_name: str):
        """Supprimer tous les produits d'un fournisseur du fichier prices.csv"""
        try:
            if not os.path.exists(self.prices_file):
                return
            
            # Lire tous les prix
            rows_to_keep = []
            with open(self.prices_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                for row in reader:
                    if row.get('fournisseur') != supplier_name:
                        rows_to_keep.append(row)
            
            # Réécrire le fichier sans les produits du fournisseur
            with open(self.prices_file, 'w', newline='', encoding='utf-8') as f:
                if fieldnames:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows_to_keep)
            
            print(f"🗑️ Produits validés de '{supplier_name}' supprimés")
            
        except Exception as e:
            print(f"Erreur suppression produits validés: {e}")
    
    def _remove_supplier_from_pending(self, supplier_name: str):
        """Supprimer tous les produits en attente d'un fournisseur"""
        try:
            if not os.path.exists(self.pending_file):
                return
            
            # Lire tous les produits en attente
            rows_to_keep = []
            with open(self.pending_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                for row in reader:
                    if row.get('fournisseur') != supplier_name:
                        rows_to_keep.append(row)
            
            # Réécrire le fichier sans les produits du fournisseur
            with open(self.pending_file, 'w', newline='', encoding='utf-8') as f:
                if fieldnames:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows_to_keep)
            
            print(f"🗑️ Produits en attente de '{supplier_name}' supprimés")
            
        except Exception as e:
            print(f"Erreur suppression produits en attente: {e}")
    
    def add_product_to_supplier(self, supplier_name: str, product_data: Dict) -> bool:
        """Ajouter un produit directement dans les prix validés (sans doublons)"""
        try:
            # 1️⃣ Vérifier l'existence d'un produit identique (nom + fournisseur)
            existing_id = None
            product_name = product_data.get('name', '').strip().lower()

            # Chercher d'abord dans les produits validés
            if os.path.exists(self.prices_file):
                with open(self.prices_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('fournisseur') == supplier_name and row.get('produit', '').strip().lower() == product_name:
                            existing_id = row.get('id')
                            break

            # Chercher ensuite dans les produits en attente
            if not existing_id and os.path.exists(self.pending_file):
                with open(self.pending_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('fournisseur') == supplier_name and row.get('produit', '').strip().lower() == product_name:
                            existing_id = row.get('id')
                            break

            # S'il existe déjà, on fait simplement une mise à jour
            if existing_id:
                print(f"ℹ️ Produit déjà existant (id={existing_id}) pour {supplier_name} – mise à jour au lieu de doublon")
                return self.update_product(supplier_name, existing_id, product_data)

            # Générer un ID unique
            product_id = datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]  # Inclure millisecondes
            
            # Préparer les données
            row_data = [
                product_id,
                product_data.get('code', ''),
                product_data.get('name', ''),
                supplier_name,
                product_data.get('unit_price', 0),
                product_data.get('unit', 'unité'),
                product_data.get('category', 'Non classé'),
                datetime.now().isoformat()
            ]
            
            # Ajouter au fichier CSV
            with open(self.prices_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row_data)
            
            print(f"✅ Produit '{product_data.get('name')}' ajouté au fournisseur '{supplier_name}'")
            return True
            
        except Exception as e:
            print(f"Erreur ajout produit: {e}")
            return False
    
    def update_product(self, supplier_name: str, product_id: str, product_data: Dict) -> bool:
        """Mettre à jour un produit existant"""
        try:
            # Chercher d'abord dans les prix validés
            if self._update_product_in_prices(product_id, product_data):
                print(f"✅ Produit validé '{product_id}' mis à jour")
                return True
            
            # Si pas trouvé, chercher dans les produits en attente
            if self._update_product_in_pending(product_id, product_data):
                print(f"✅ Produit en attente '{product_id}' mis à jour")
                return True
            
            print(f"❌ Produit '{product_id}' non trouvé")
            return False
            
        except Exception as e:
            print(f"Erreur mise à jour produit: {e}")
            return False
    
    def delete_product(self, supplier_name: str, product_id: str) -> bool:
        """Supprimer un produit existant"""
        try:
            # Chercher d'abord dans les prix validés
            if self._delete_product_from_prices(product_id):
                print(f"✅ Produit validé '{product_id}' supprimé")
                return True
            
            # Si pas trouvé, chercher dans les produits en attente
            if self._delete_product_from_pending(product_id):
                print(f"✅ Produit en attente '{product_id}' supprimé")
                return True
            
            print(f"❌ Produit '{product_id}' non trouvé")
            return False
            
        except Exception as e:
            print(f"Erreur suppression produit: {e}")
            return False
    
    def _update_product_in_prices(self, product_id: str, product_data: Dict) -> bool:
        """Mettre à jour un produit dans prices.csv"""
        try:
            if not os.path.exists(self.prices_file):
                return False
            
            rows = []
            updated = False
            
            with open(self.prices_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                
                for row in reader:
                    if row.get('id') == product_id:
                        # Mettre à jour la ligne
                        row['produit'] = product_data.get('name', row['produit'])
                        row['code'] = product_data.get('code', row['code'])
                        row['prix_unitaire'] = product_data.get('unit_price', row['prix_unitaire'])
                        row['unite'] = product_data.get('unit', row['unite'])
                        row['categorie'] = product_data.get('category', row['categorie'])
                        updated = True
                    
                    rows.append(row)
            
            if updated:
                # Réécrire le fichier
                with open(self.prices_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
            
            return updated
            
        except Exception as e:
            print(f"Erreur mise à jour produit validé: {e}")
            return False
    
    def _update_product_in_pending(self, product_id: str, product_data: Dict) -> bool:
        """Mettre à jour un produit dans pending_products.csv"""
        try:
            if not os.path.exists(self.pending_file):
                return False
            
            rows = []
            updated = False
            
            with open(self.pending_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                
                for row in reader:
                    if row.get('id') == product_id:
                        # Mettre à jour la ligne
                        row['produit'] = product_data.get('name', row['produit'])
                        row['code'] = product_data.get('code', row['code'])
                        row['prix'] = product_data.get('unit_price', row['prix'])
                        row['unite'] = product_data.get('unit', row['unite'])
                        row['categorie'] = product_data.get('category', row['categorie'])
                        updated = True
                    
                    rows.append(row)
            
            if updated:
                # Réécrire le fichier
                with open(self.pending_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
            
            return updated
            
        except Exception as e:
            print(f"Erreur mise à jour produit en attente: {e}")
            return False
    
    def _delete_product_from_prices(self, product_id: str) -> bool:
        """Supprimer un produit de prices.csv"""
        try:
            if not os.path.exists(self.prices_file):
                return False
            
            rows = []
            deleted = False
            
            with open(self.prices_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                
                for row in reader:
                    if row.get('id') == product_id:
                        deleted = True
                        continue  # Ne pas ajouter cette ligne
                    
                    rows.append(row)
            
            if deleted:
                # Réécrire le fichier
                with open(self.prices_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
            
            return deleted
            
        except Exception as e:
            print(f"Erreur suppression produit validé: {e}")
            return False
    
    def _delete_product_from_pending(self, product_id: str) -> bool:
        """Supprimer un produit de pending_products.csv"""
        try:
            if not os.path.exists(self.pending_file):
                return False
            
            rows = []
            deleted = False
            
            with open(self.pending_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                
                for row in reader:
                    if row.get('id') == product_id:
                        deleted = True
                        continue  # Ne pas ajouter cette ligne
                    
                    rows.append(row)
            
            if deleted:
                # Réécrire le fichier
                with open(self.pending_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
            
            return deleted
            
        except Exception as e:
            print(f"Erreur suppression produit en attente: {e}")
            return False
    
    def _fix_prices_file_format(self):
        """Corriger le format du fichier prices.csv"""
        try:
            import shutil
            
            # Sauvegarder l'ancien fichier
            backup_file = self.prices_file + '.backup'
            shutil.copy2(self.prices_file, backup_file)
            print(f"📁 Sauvegarde créée: {backup_file}")
            
            # Lire les données existantes
            existing_data = []
            with open(self.prices_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Mapper les anciennes colonnes vers les nouvelles
                    new_row = {
                        'id': row.get('code', ''),  # Utiliser le code comme ID temporaire
                        'code': row.get('code_produit', row.get('code', '')),
                        'produit': row.get('produit', ''),
                        'fournisseur': row.get('fournisseur', ''),
                        'prix_unitaire': row.get('prix_unitaire', row.get('prix', '0')),
                        'unite': row.get('unite', ''),
                        'categorie': row.get('categorie', 'Non classé'),
                        'date_ajout': row.get('date_ajout', row.get('date_maj', datetime.now().isoformat()))
                    }
                    existing_data.append(new_row)
            
            # Recréer le fichier avec le bon format
            with open(self.prices_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['id', 'code', 'produit', 'fournisseur', 'prix_unitaire', 'unite', 'categorie', 'date_ajout']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(existing_data)
            
            print(f"✅ Fichier prices.csv corrigé avec {len(existing_data)} produits")
            
        except Exception as e:
            print(f"❌ Erreur correction format: {e}") 