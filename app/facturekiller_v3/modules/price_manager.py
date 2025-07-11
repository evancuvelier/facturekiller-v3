"""
Module de gestion des prix de référence
Import depuis Excel/CSV et comparaison avec les factures
"""

import pandas as pd
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)

# === Firestore ===
try:
    from modules.firestore_db import available as _fs_available, get_client as _fs_client
except Exception:
    # Import léger pour éviter ImportError si Firestore non configuré
    def _fs_available():
        return False
    def _fs_client():
        return None

class PriceManager:
    """Gestionnaire des prix de référence (Firestore uniquement)"""
    
    def __init__(self):
        """Initialiser le gestionnaire de prix (Firestore uniquement)"""
        # 🔥 FIRESTORE UNIQUEMENT - Plus de fichiers locaux
        self._fs_enabled = False
        self._fs = None
        
        # Initialiser Firestore
        try:
            from modules.firestore_db import FirestoreDB
            firestore_db = FirestoreDB()
            self._fs = firestore_db.db
            self._fs_enabled = True
            print("✅ Firestore initialisé pour PriceManager")
        except Exception as e:
            print(f"❌ Erreur initialisation Firestore PriceManager: {e}")
            self._fs_enabled = False
            self._fs = None
    
    def is_connected(self) -> bool:
        """Vérifier si Firestore est accessible"""
        return self._fs_enabled and self._fs is not None
    
    def get_all_prices(self, page: int = 1, per_page: int = 50, 
                      search: str = '', supplier: str = '', restaurant_name: str = None) -> Dict[str, Any]:
        """Récupérer tous les prix de référence depuis Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return {
                    'items': [],
                    'total': 0,
                    'page': page,
                    'pages': 1,
                    'per_page': per_page,
                    'error': 'Firestore non disponible'
                }
            
            # Construire la requête Firestore
            query = self._fs.collection('prices')
            
            # Appliquer les filtres
            if supplier:
                query = query.where('fournisseur', '==', supplier)
            
            if restaurant_name:
                # Filtrer par restaurant OU prix généraux
                # Note: Firestore ne supporte pas les requêtes OR complexes
                # On va filtrer côté application
                pass
            
            # Récupérer tous les documents
            docs = list(query.stream())
            
            # Convertir en liste de dictionnaires
            items = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                items.append(data)
            
            # Appliquer les filtres côté application
            if restaurant_name:
                items = [item for item in items if 
                        item.get('restaurant') == restaurant_name or 
                        item.get('restaurant') == 'Général' or 
                        not item.get('restaurant')]
            
            if search:
                search_lower = search.lower()
                items = [item for item in items if 
                        search_lower in item.get('produit', '').lower() or 
                        search_lower in item.get('code', '').lower()]
            
            # Calculer la pagination
            total = len(items)
            
            # Si per_page est très grand, retourner tous les résultats
            if per_page > 9999:
                return {
                    'items': items,
                    'total': total,
                    'page': 1,
                    'pages': 1,
                    'per_page': total
                }
            
            total_pages = max(1, (total + per_page - 1) // per_page)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            
            # Extraire la page
            page_items = items[start_idx:end_idx]
            
            return {
                'items': page_items,
                'total': total,
                'page': page,
                'pages': total_pages,
                'per_page': per_page,
                'restaurant_filter': restaurant_name
            }
            
        except Exception as e:
            print(f"❌ Erreur get_all_prices Firestore: {e}")
            return {
                'items': [],
                'total': 0,
                'page': page,
                'pages': 1,
                'per_page': per_page,
                'error': str(e)
            }
    
    def import_from_file(self, file_path: str) -> Dict[str, Any]:
        """Importer des prix depuis un fichier Excel ou CSV vers Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return {
                    'total_rows': 0,
                    'new_products': 0,
                    'updated_products': 0,
                    'errors': ['Firestore non disponible']
                }
            
            # Déterminer le type de fichier
            if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                df = pd.read_excel(file_path)
            elif file_path.endswith('.csv'):
                # Essayer différents encodages
                for encoding in ['utf-8', 'latin-1', 'iso-8859-1']:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding)
                        break
                    except:
                        continue
            else:
                raise ValueError("Format de fichier non supporté")
            
            # Mapper les colonnes
            column_mapping = self._detect_column_mapping(df.columns.tolist())
            df = df.rename(columns=column_mapping)
            
            # Valider les colonnes requises
            required_columns = ['produit', 'prix']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Colonnes manquantes: {missing_columns}")
            
            # Nettoyer et formater les données
            df = self._clean_import_data(df)
            
            # Statistiques avant import
            stats = {
                'total_rows': len(df),
                'new_products': 0,
                'updated_products': 0,
                'errors': []
            }
            
            # Traiter chaque ligne
            for _, row in df.iterrows():
                try:
                    self._import_price_row_firestore(row, stats)
                except Exception as e:
                    stats['errors'].append(f"Ligne {row.name}: {str(e)}")
            
            stats['imported'] = stats['new_products'] + stats['updated_products']
            return stats
            
        except Exception as e:
            print(f"❌ Erreur import fichier Firestore: {e}")
            return {
                'total_rows': 0,
                'new_products': 0,
                'updated_products': 0,
                'errors': [str(e)]
            }
    
    def _detect_column_mapping(self, columns: List[str]) -> Dict[str, str]:
        """Détecter automatiquement le mapping des colonnes"""
        mapping = {}
        
        # Patterns de détection
        patterns = {
            'code': ['code', 'ref', 'reference', 'sku', 'article'],
            'produit': ['produit', 'product', 'libelle', 'designation', 'nom', 'article'],
            'fournisseur': ['fournisseur', 'supplier', 'vendeur', 'four'],
            'prix': ['prix', 'price', 'tarif', 'cout', 'pu', 'prix_unitaire'],
            'unite': ['unite', 'unit', 'uom', 'conditionnement'],
            'categorie': ['categorie', 'category', 'famille', 'rayon']
        }
        
        for col in columns:
            col_lower = col.lower().strip()
            for target, keywords in patterns.items():
                if any(keyword in col_lower for keyword in keywords):
                    mapping[col] = target
                    break
        
        return mapping
    
    def _clean_import_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Nettoyer les données d'import pour Firestore"""
        try:
            # Supprimer les lignes vides
            df = df.dropna(subset=['produit'])
            
            # Nettoyer les noms de produits
            df['produit'] = df['produit'].astype(str).str.strip()
            
            # Convertir les prix en float
            df['prix'] = pd.to_numeric(df['prix'], errors='coerce').fillna(0)
            
            # Nettoyer les fournisseurs
            df['fournisseur'] = df['fournisseur'].astype(str).str.strip().fillna('UNKNOWN')
            
            # Nettoyer les unités
            df['unite'] = df['unite'].astype(str).str.strip().fillna('unité')
            
            # Nettoyer les catégories
            df['categorie'] = df['categorie'].astype(str).str.strip().fillna('Non classé')
            
            return df
            
        except Exception as e:
            print(f"❌ Erreur nettoyage données: {e}")
            return df
    
    def _generate_product_code_firestore(self, product_name: str, supplier: str) -> str:
        """Générer un code produit automatique pour Firestore"""
        try:
            # Nettoyer le nom du produit
            clean_name = ''.join(c for c in product_name.upper() if c.isalnum())[:8]
            # Nettoyer le fournisseur
            clean_supplier = ''.join(c for c in supplier.upper() if c.isalnum())[:4]
            # Ajouter timestamp
            timestamp = datetime.now().strftime('%m%d')
            
            return f"{clean_name}_{clean_supplier}_{timestamp}"
        except:
            return f"AUTO_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def _import_price_row_firestore(self, row: pd.Series, stats: Dict):
        """Importer une ligne de prix dans Firestore"""
        try:
            # Préparer les données
            price_data = {
                'code': row.get('code', ''),
                'produit': str(row.get('produit', '')).strip(),
                'fournisseur': row.get('fournisseur', 'UNKNOWN'),
                'prix': float(row.get('prix', 0)),
                'prix_unitaire': float(row.get('prix', 0)),
                'unite': row.get('unite', 'unité'),
                'categorie': row.get('categorie', 'Non classé'),
                'restaurant': row.get('restaurant', 'Général'),
                'date_maj': datetime.now().isoformat(),
                'actif': True
            }
            
            # Générer un code si manquant
            if not price_data['code']:
                price_data['code'] = self._generate_product_code_firestore(price_data['produit'], price_data['fournisseur'])
            
            # Vérifier si le produit existe déjà
            existing_docs = list(self._fs.collection('prices').where('produit', '==', price_data['produit']).where('fournisseur', '==', price_data['fournisseur']).stream())
            
            if existing_docs:
                # Mettre à jour le produit existant
                existing_docs[0].reference.update(price_data)
                stats['updated_products'] += 1
            else:
                # Ajouter nouveau produit
                self._fs.collection('prices').add(price_data)
                stats['new_products'] += 1
                
        except Exception as e:
            raise Exception(f"Erreur import ligne: {e}")
    
    def _save_prices(self):
        """Méthode obsolète - Firestore uniquement"""
        print("⚠️ _save_prices obsolète - Firestore uniquement")
        pass
    
    def compare_prices(self, products: List[Dict], restaurant_name: str = None) -> Dict[str, Any]:
        """Comparer les prix des produits avec les prix de référence dans Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return {
                    'total_products': len(products),
                    'matched_products': 0,
                    'unmatched_products': len(products),
                    'price_differences': [],
                    'missing_products': products
                }
            
            results = {
                'total_products': len(products),
                'matched_products': 0,
                'unmatched_products': 0,
                'price_differences': [],
                'missing_products': []
            }
            
            for product in products:
                product_name = product.get('produit', product.get('name', ''))
                supplier = product.get('fournisseur', product.get('supplier', ''))
                invoice_price = float(product.get('prix', product.get('price', 0)))
                
                # Chercher le prix de référence
                ref_price = self.find_product_price(product_name, supplier, restaurant_name)
                
                if ref_price:
                    ref_price_value = float(ref_price.get('prix', ref_price.get('prix_unitaire', 0)))
                    price_diff = invoice_price - ref_price_value
                    price_diff_percent = (price_diff / ref_price_value * 100) if ref_price_value > 0 else 0
                    
                    results['matched_products'] += 1
                    results['price_differences'].append({
                        'product': product_name,
                        'supplier': supplier,
                        'invoice_price': invoice_price,
                        'reference_price': ref_price_value,
                        'difference': price_diff,
                        'difference_percent': price_diff_percent,
                        'status': 'match'
                    })
                else:
                    results['unmatched_products'] += 1
                    results['missing_products'].append({
                        'product': product_name,
                        'supplier': supplier,
                        'invoice_price': invoice_price,
                        'status': 'missing'
                    })
            
            return results
            
        except Exception as e:
            print(f"❌ Erreur compare_prices Firestore: {e}")
            return {
                'total_products': len(products),
                'matched_products': 0,
                'unmatched_products': len(products),
                'price_differences': [],
                'missing_products': products,
                'error': str(e)
            }
    
    def add_pending_product_OLD(self, code: str, name: str, price: float, 
                           unit: str = 'unité', supplier: str = 'UNKNOWN', 
                           category: str = 'Non classé') -> int:
        """Méthode obsolète - utiliser add_pending_product avec dict"""
        print("⚠️ add_pending_product_OLD obsolète - utiliser add_pending_product")
        return 0
    
    def get_pending_products(self) -> List[Dict]:
        """Récupérer tous les produits en attente depuis Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return []
            
            docs = list(self._fs.collection('pending_products').stream())
            products = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                products.append(data)
            
            print(f"📊 Firestore pending products: {len(products)}")
            return products
            
        except Exception as e:
            print(f"❌ Erreur get_pending_products Firestore: {e}")
            return []
    
    def validate_pending_product(self, pending_id: int) -> bool:
        """Valider un produit en attente (le déplacer vers les prix validés)"""
        try:
            if not self._fs_enabled:
                return False
            
            # Récupérer le produit en attente
            pending_docs = list(self._fs.collection('pending_products').where('id', '==', pending_id).stream())
            if not pending_docs:
                print(f"❌ Produit en attente {pending_id} non trouvé")
                return False
            
            pending_doc = pending_docs[0]
            pending_data = pending_doc.to_dict()
            
            # Préparer les données pour les prix validés
            validated_data = {
                'code': pending_data.get('code', ''),
                'produit': pending_data.get('produit', ''),
                'fournisseur': pending_data.get('fournisseur', ''),
                'prix': pending_data.get('prix', 0),
                'prix_unitaire': pending_data.get('prix', 0),
                'unite': pending_data.get('unite', 'unité'),
                'categorie': pending_data.get('categorie', 'Non classé'),
                'date_maj': datetime.now().isoformat(),
                'actif': True,
                'restaurant': pending_data.get('restaurant', 'Général')
            }
            
            # Ajouter aux prix validés
            self._fs.collection('prices').add(validated_data)
            
            # Supprimer des produits en attente
            pending_doc.reference.delete()
            
            print(f"✅ Produit {pending_id} validé et déplacé vers les prix")
            return True
            
        except Exception as e:
            print(f"❌ Erreur validation produit Firestore: {e}")
            return False
    
    def reject_pending_product(self, pending_id: int) -> bool:
        """Rejeter un produit en attente (le supprimer)"""
        try:
            if not self._fs_enabled:
                return False
            
            # Récupérer le produit en attente
            pending_docs = list(self._fs.collection('pending_products').where('id', '==', pending_id).stream())
            if not pending_docs:
                print(f"❌ Produit en attente {pending_id} non trouvé")
                return False
            
            # Supprimer le produit
            pending_docs[0].reference.delete()
            
            print(f"✅ Produit {pending_id} rejeté et supprimé")
            return True
            
        except Exception as e:
            print(f"❌ Erreur rejet produit Firestore: {e}")
            return False
    
    def update_pending_product(self, pending_id: int, updates: Dict) -> bool:
        """Mettre à jour un produit en attente"""
        try:
            if not self._fs_enabled:
                return False
            
            # Récupérer le produit en attente
            pending_docs = list(self._fs.collection('pending_products').where('id', '==', pending_id).stream())
            if not pending_docs:
                print(f"❌ Produit en attente {pending_id} non trouvé")
                return False
            
            # Mettre à jour le produit
            updates['date_maj'] = datetime.now().isoformat()
            pending_docs[0].reference.update(updates)
            
            print(f"✅ Produit {pending_id} mis à jour")
            return True
            
        except Exception as e:
            print(f"❌ Erreur mise à jour produit Firestore: {e}")
            return False
    
    def add_pending_product(self, product_data: Dict) -> bool:
        """Ajouter un produit en attente dans Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return False
            
            # Générer un ID unique
            product_data['id'] = int(datetime.now().timestamp() * 1000)
            product_data['date_ajout'] = datetime.now().isoformat()
            product_data['status'] = 'pending'
            
            # Ajouter à Firestore
            self._fs.collection('pending_products').add(product_data)
            
            print(f"✅ Produit en attente ajouté: {product_data.get('produit', '')}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur ajout produit en attente Firestore: {e}")
            return False
    
    def _generate_pending_code(self, name: str, supplier: str) -> str:
        """Générer un code pour un produit en attente"""
        # Prendre les 3 premières lettres du nom et fournisseur
        name_part = ''.join(c for c in name[:3] if c.isalnum()).upper()
        supplier_part = ''.join(c for c in supplier[:3] if c.isalnum()).upper()
        
        # Ajouter timestamp
        timestamp = datetime.now().strftime('%m%d')
        
        return f"P{supplier_part}{name_part}{timestamp}"

    # ===== NOUVELLE MÉTHODE ANTI-DOUBLON =====
    def _product_exists(self, name: str, supplier: str, restaurant: str = 'Général') -> bool:
        """Vérifier si un produit existe déjà dans la base confirmée (nom + fournisseur + restaurant)"""
        try:
            if not self._fs_enabled:
                return False
            query = self._fs.collection('prices').where('produit', '==', name).where('fournisseur', '==', supplier).where('restaurant', '==', restaurant)
            docs = list(query.stream())
            return bool(docs)
        except Exception:
            return False
    
    def add_confirmed_product_directly(self, product_data: Dict) -> bool:
        """
        ⚠️ FONCTION DÉSACTIVÉE - Utiliser add_pending_product à la place
        Cette fonction créait des produits validés automatiquement, ce qui causait des problèmes
        """
        print(f"⚠️ ADD_CONFIRMED: Fonction désactivée - utiliser add_pending_product")
        return False

    def add_price(self, price_data: Dict) -> bool:
        """Ajouter un prix validé dans Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return False
            
            # Ajouter les métadonnées
            price_data['date_maj'] = datetime.now().isoformat()
            price_data['actif'] = True
            
            # Ajouter à Firestore
            self._fs.collection('prices').add(price_data)
            
            print(f"✅ Prix ajouté: {price_data.get('produit', '')}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur ajout prix Firestore: {e}")
            return False
    
    def update_price(self, code: str, updates: Dict) -> bool:
        """Mettre à jour un prix dans Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return False
            
            # Chercher le prix par code
            docs = list(self._fs.collection('prices').where('code', '==', code).stream())
            if not docs:
                print(f"❌ Prix avec code {code} non trouvé")
                return False
            
            # Mettre à jour
            updates['date_maj'] = datetime.now().isoformat()
            docs[0].reference.update(updates)
            
            print(f"✅ Prix {code} mis à jour")
            return True
            
        except Exception as e:
            print(f"❌ Erreur mise à jour prix Firestore: {e}")
            return False
    
    def update_price_by_id(self, price_id: int, updates: Dict) -> bool:
        """Mettre à jour un prix par ID dans Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return False
            
            # Chercher le prix par ID
            docs = list(self._fs.collection('prices').where('id', '==', price_id).stream())
            if not docs:
                print(f"❌ Prix avec ID {price_id} non trouvé")
                return False
            
            # Mettre à jour
            updates['date_maj'] = datetime.now().isoformat()
            docs[0].reference.update(updates)
            
            print(f"✅ Prix {price_id} mis à jour")
            return True
            
        except Exception as e:
            print(f"❌ Erreur mise à jour prix Firestore: {e}")
            return False
    
    def delete_price(self, code: str) -> bool:
        """Supprimer un prix par code dans Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return False
            
            # Chercher le prix par code
            docs = list(self._fs.collection('prices').where('code', '==', code).stream())
            if not docs:
                print(f"❌ Prix avec code {code} non trouvé")
                return False
            
            # Supprimer
            docs[0].reference.delete()
            
            print(f"✅ Prix {code} supprimé")
            return True
            
        except Exception as e:
            print(f"❌ Erreur suppression prix Firestore: {e}")
            return False
    
    def delete_price_by_id(self, price_id: int) -> bool:
        """Supprimer un prix par ID dans Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return False
            
            # Chercher le prix par ID
            docs = list(self._fs.collection('prices').where('id', '==', price_id).stream())
            if not docs:
                print(f"❌ Prix avec ID {price_id} non trouvé")
                return False
            
            # Supprimer
            docs[0].reference.delete()
            
            print(f"✅ Prix {price_id} supprimé")
            return True
            
        except Exception as e:
            print(f"❌ Erreur suppression prix Firestore: {e}")
            return False
    
    def delete_price_cascade(self, price_id: int) -> Dict[str, Any]:
        """Supprimer un prix et tous ses produits associés dans Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return {
                    'success': False,
                    'error': 'Firestore non disponible',
                    'deleted_price': False,
                    'deleted_products': 0
                }
            
            # Chercher le prix par ID
            docs = list(self._fs.collection('prices').where('id', '==', price_id).stream())
            if not docs:
                return {
                    'success': False,
                    'error': f'Prix avec ID {price_id} non trouvé',
                    'deleted_price': False,
                    'deleted_products': 0
                }
            
            price_doc = docs[0]
            price_data = price_doc.to_dict()
            
            # Supprimer le prix
            price_doc.reference.delete()
            
            # Supprimer les produits en attente associés
            pending_docs = list(self._fs.collection('pending_products').where('produit', '==', price_data.get('produit', '')).stream())
            for doc in pending_docs:
                doc.reference.delete()
            
            result = {
                'success': True,
                'deleted_price': True,
                'deleted_products': len(pending_docs),
                'price_id': price_id
            }
            
            print(f"✅ Prix {price_id} et {len(pending_docs)} produits associés supprimés")
            return result
            
        except Exception as e:
            print(f"❌ Erreur suppression prix cascade Firestore: {e}")
            return {
                'success': False,
                'error': str(e),
                'deleted_price': False,
                'deleted_products': 0
            }
    
    def get_suppliers(self) -> List[str]:
        """Récupérer la liste des fournisseurs depuis Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return []
            
            # Récupérer tous les prix
            docs = list(self._fs.collection('prices').stream())
            suppliers = set()
            
            for doc in docs:
                data = doc.to_dict()
                if data.get('fournisseur'):
                    suppliers.add(data['fournisseur'])
            
            suppliers_list = list(suppliers)
            suppliers_list.sort()
            
            print(f"📊 Firestore suppliers: {len(suppliers_list)}")
            return suppliers_list
            
        except Exception as e:
            print(f"❌ Erreur get_suppliers Firestore: {e}")
            return []
    
    def get_prices_by_suppliers(self, supplier_names: List[str]) -> List[Dict[str, Any]]:
        """Récupérer les prix par fournisseurs depuis Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return []
            
            all_prices = []
            
            for supplier in supplier_names:
                docs = list(self._fs.collection('prices').where('fournisseur', '==', supplier).stream())
                for doc in docs:
                    data = doc.to_dict()
                    data['id'] = doc.id
                    all_prices.append(data)
            
            print(f"📊 Firestore prices by suppliers: {len(all_prices)}")
            return all_prices
            
        except Exception as e:
            print(f"❌ Erreur get_prices_by_suppliers Firestore: {e}")
            return []
    
    def find_product_price(self, product_name: str, supplier: str = '', restaurant: str = 'Général') -> Optional[Dict]:
        """Trouver un prix de produit dans Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return None
            
            # Construire la requête
            query = self._fs.collection('prices').where('produit', '==', product_name)
            
            if supplier:
                query = query.where('fournisseur', '==', supplier)
            
            docs = list(query.stream())
            
            if not docs:
                return None
            
            # Si plusieurs résultats, filtrer par restaurant
            if len(docs) > 1 and restaurant:
                filtered_docs = []
                for doc in docs:
                    data = doc.to_dict()
                    if data.get('restaurant') == restaurant or data.get('restaurant') == 'Général':
                        filtered_docs.append(doc)
                docs = filtered_docs
            
            if docs:
                data = docs[0].to_dict()
                data['id'] = docs[0].id
                return data
            
            return None
            
        except Exception as e:
            print(f"❌ Erreur find_product_price Firestore: {e}")
            return None 