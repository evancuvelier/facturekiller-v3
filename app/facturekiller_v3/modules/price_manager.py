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
    """Gestionnaire des prix de référence"""
    
    def __init__(self):
        self.prices_db = self._load_prices()
        # Firestore
        self._fs_enabled = _fs_available()
        self._fs = _fs_client() if self._fs_enabled else None
        
    def _load_prices(self) -> pd.DataFrame:
        """Charger les prix depuis le fichier de données"""
        prices_file = 'data/prices.csv'
        
        if os.path.exists(prices_file):
            try:
                return pd.read_csv(prices_file, encoding='utf-8')
            except Exception as e:
                logger.error(f"Erreur chargement prix: {e}")
        
        # Créer un DataFrame vide avec les colonnes nécessaires
        return pd.DataFrame(columns=[
            'code', 'produit', 'fournisseur', 'prix', 'unite', 
            'categorie', 'date_maj', 'actif'
        ])
    
    def is_connected(self) -> bool:
        """Vérifier si la base de données est accessible"""
        return True  # Pour l'instant, toujours vrai avec fichiers locaux
    
    def get_all_prices(self, page: int = 1, per_page: int = 50, 
                      search: str = '', supplier: str = '', restaurant_name: str = None) -> Dict[str, Any]:
        """Récupérer tous les prix de référence avec pagination et filtres INCLUANT RESTAURANT"""
        # Si per_page est très grand, retourner tous les résultats
        if per_page > 9999:
            # Mode "tous les résultats"
            items = self.prices_db.to_dict('records')
            for i, item in enumerate(items):
                item['id'] = i + 1
            return {
                'items': items,
                'total': len(items),
                'page': 1,
                'pages': 1,
                'per_page': len(items)
            }
        
        # Appliquer les filtres
        filtered_df = self.prices_db.copy()
        
        # NOUVEAU FILTRE: Par restaurant
        if restaurant_name:
            # Ajouter une colonne restaurant si elle n'existe pas
            if 'restaurant' not in filtered_df.columns:
                filtered_df['restaurant'] = 'Général'  # Valeur par défaut
            
            # Filtrer par restaurant OU prix généraux
            mask = (
                (filtered_df['restaurant'] == restaurant_name) |
                (filtered_df['restaurant'] == 'Général') |
                (filtered_df['restaurant'].isna())
            )
            filtered_df = filtered_df[mask]
        
        # Filtre par recherche
        if search:
            mask = (
                filtered_df['produit'].str.contains(search, case=False, na=False) |
                filtered_df['code'].str.contains(search, case=False, na=False)
            )
            filtered_df = filtered_df[mask]
        
        # Filtre par fournisseur
        if supplier:
            filtered_df = filtered_df[filtered_df['fournisseur'] == supplier]
        
        # Calculer la pagination
        total = len(filtered_df)
        total_pages = max(1, (total + per_page - 1) // per_page)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        # Extraire la page
        page_df = filtered_df.iloc[start_idx:end_idx]
        
        # Ajouter des IDs aux enregistrements
        items = page_df.to_dict('records')
        for i, item in enumerate(items):
            item['id'] = start_idx + i + 1
            # Remplacer NaN par None pour éviter les erreurs JSON
            for key, value in item.items():
                if pd.isna(value):
                    item[key] = None
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'pages': total_pages,
            'per_page': per_page,
            'restaurant_filter': restaurant_name
        }
    
    def import_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Importer des prix depuis un fichier Excel ou CSV
        
        Returns:
            Dict avec statistiques d'import
        """
        try:
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
            column_mapping = self._detect_column_mapping(df.columns)
            df = df.rename(columns=column_mapping)
            
            # Valider les colonnes requises
            required_columns = ['produit', 'prix']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Colonnes manquantes: {missing_columns}")
            
            # Nettoyer et formater les données
            df = self._clean_import_data(df)
            
            # Générer les codes produits si manquants
            if 'code' not in df.columns:
                df['code'] = df.apply(lambda row: self._generate_product_code(row), axis=1)
            
            # Ajouter les métadonnées
            df['date_maj'] = datetime.now().strftime('%Y-%m-%d')
            df['actif'] = True
            
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
                    self._import_price_row(row, stats)
                except Exception as e:
                    stats['errors'].append(f"Ligne {row.name}: {str(e)}")
            
            # Sauvegarder
            self._save_prices()
            
            stats['imported'] = stats['new_products'] + stats['updated_products']
            return stats
            
        except Exception as e:
            logger.error(f"Erreur import fichier: {e}")
            raise
    
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
        """Nettoyer et formater les données importées"""
        # Nettoyer les prix
        if 'prix' in df.columns:
            df['prix'] = pd.to_numeric(
                df['prix'].astype(str).str.replace(',', '.').str.replace('€', '').str.strip(),
                errors='coerce'
            )
            df = df[df['prix'] > 0]  # Filtrer les prix invalides
        
        # Nettoyer les noms de produits
        if 'produit' in df.columns:
            df['produit'] = df['produit'].str.strip().str.title()
        
        # Fournisseur par défaut
        if 'fournisseur' not in df.columns:
            df['fournisseur'] = 'IMPORT'
        else:
            df['fournisseur'] = df['fournisseur'].str.upper()
        
        # Unité par défaut
        if 'unite' not in df.columns:
            df['unite'] = 'pièce'
        else:
            df['unite'] = df['unite'].str.lower()
        
        return df
    
    def _generate_product_code(self, row: pd.Series) -> str:
        """Générer un code produit unique"""
        # Prendre les 3 premières lettres du produit et du fournisseur
        prod_part = ''.join(c for c in row.get('produit', '')[:3] if c.isalnum()).upper()
        four_part = ''.join(c for c in row.get('fournisseur', '')[:3] if c.isalnum()).upper()
        
        # Ajouter un numéro séquentiel
        base_code = f"{four_part}{prod_part}"
        counter = 1
        code = f"{base_code}{counter:03d}"
        
        while code in self.prices_db['code'].values:
            counter += 1
            code = f"{base_code}{counter:03d}"
        
        return code
    
    def _import_price_row(self, row: pd.Series, stats: Dict):
        """Importer une ligne de prix"""
        # Vérifier si le produit existe déjà
        existing_mask = (
            (self.prices_db['produit'] == row['produit']) &
            (self.prices_db['fournisseur'] == row.get('fournisseur', 'IMPORT'))
        )
        
        if existing_mask.any():
            # Mise à jour
            idx = self.prices_db[existing_mask].index[0]
            self.prices_db.loc[idx] = row
            stats['updated_products'] += 1
        else:
            # Nouveau produit
            self.prices_db = pd.concat([self.prices_db, pd.DataFrame([row])], ignore_index=True)
            stats['new_products'] += 1
    
    def _save_prices(self):
        """Sauvegarder les prix dans le fichier"""
        os.makedirs('data', exist_ok=True)
        self.prices_db.to_csv('data/prices.csv', index=False, encoding='utf-8')
    
    def compare_prices(self, products: List[Dict], restaurant_name: str = None) -> Dict[str, Any]:
        """
        Comparer les prix des produits scannés avec la base de données existante
        Ajoute automatiquement les nouveaux produits en attente
        """
        print(f"🔍 COMPARE_PRICES: Démarrage pour {len(products)} produits")
        print(f"🏪 COMPARE_PRICES: Restaurant: {restaurant_name}")
        
        if not products:
            return {
                'total_savings': 0.0,
                'items_analyzed': 0,
                'new_products': 0,
                'products_details': [],
                'products_with_price_differences': []
            }

        comparison = {
            'total_savings': 0.0,
            'items_analyzed': len(products),
            'new_products': 0,
            'products_details': [],
            'products_with_price_differences': []
        }

        # Charger les prix existants
        prices_data = self.get_all_prices(per_page=99999, restaurant_name=restaurant_name)
        existing_prices = prices_data.get('items', [])
        
        print(f"📋 COMPARE_PRICES: Prix existants chargés: {len(existing_prices)}")

        for i, product in enumerate(products):
            try:
                # Nettoyer le nom du produit
                product_name = str(product.get('name', '')).strip()
                if not product_name:
                    print(f"⚠️ COMPARE_PRICES: Produit {i} sans nom, ignoré")
                    continue

                # Prix facturé
                unit_price = float(product.get('unit_price', 0))
                if unit_price <= 0:
                    print(f"⚠️ COMPARE_PRICES: Produit {i} '{product_name}' sans prix valide, ignoré")
                    continue

                # Obtenir le fournisseur depuis le produit ou utiliser 'SCAN'
                supplier = product.get('supplier', 'SCAN')
                
                print(f"🔍 COMPARE_PRICES: Produit {i+1}/{len(products)}: '{product_name}' - {supplier} - {unit_price}€")

                # Générer un code produit
                product_code = self._generate_product_code(product_name, supplier)

                # Chercher un prix existant pour ce produit et fournisseur
                name_clean = product_name.lower().strip()
                
                matching_price = None
                for existing in existing_prices:
                    existing_name = str(existing.get('produit', '')).lower().strip()
                    existing_supplier = str(existing.get('fournisseur', '')).upper()
                    current_supplier = supplier.upper()
                    
                    if existing_name == name_clean and existing_supplier == current_supplier:
                        matching_price = existing
                        print(f"✅ COMPARE_PRICES: Prix existant trouvé pour '{product_name}' ({supplier})")
                        break

                if matching_price:
                    # PRODUIT EXISTANT
                    reference_price = float(matching_price.get('prix', 0))
                    savings = reference_price - unit_price

                    comparison['total_savings'] += savings
                    if abs(savings) > 0.01:
                        comparison['products_with_price_differences'].append({
                            'product_name': product_name,
                            'savings': savings,
                            'unit_price_invoice': unit_price,
                            'unit_price_reference': reference_price
                        })
                    comparison['products_details'].append({
                        'product_name': product_name,
                        'product_code': product_code,
                        'unit_price_invoice': unit_price,
                        'unit_price_reference': reference_price,
                        'savings': savings,
                        'status': 'existing',
                        'message': f'Économie: {savings:.2f}€' if savings > 0 else f'Surcoût: {abs(savings):.2f}€',
                        'restaurant': restaurant_name or 'Général'
                    })
                else:
                    # NOUVEAU PRODUIT : Ajouter en attente (prix unitaire uniquement)
                    print(f"🆕 COMPARE_PRICES: NOUVEAU PRODUIT détecté: '{product_name}' ({supplier}) - {unit_price}€")
                    comparison['new_products'] += 1
                    
                    # Ajouter à la base avec statut "en attente" - PRIX UNITAIRE SEULEMENT
                    pending_data = {
                        'code': product_code or '',
                        'produit': product_name,
                        'prix': unit_price,  # Prix unitaire uniquement
                        'unite': product.get('unit', 'unité'),
                        'fournisseur': supplier,
                        'categorie': product.get('category', 'Non classé')
                    }
                    
                    # Ajouter le restaurant si spécifié
                    if restaurant_name:
                        pending_data['restaurant'] = restaurant_name
                        print(f"🏪 COMPARE_PRICES: Restaurant ajouté au produit en attente: {restaurant_name}")
                    else:
                        print(f"⚠️ COMPARE_PRICES: Aucun restaurant spécifié, utilisera 'Général'")
                    
                    print(f"💾 COMPARE_PRICES: Tentative d'ajout en attente: {pending_data}")
                    success = self.add_pending_product(pending_data)
                    print(f"📝 COMPARE_PRICES: Résultat ajout en attente: {'✅ Succès' if success else '❌ Échec'}")
                    
                    comparison['products_details'].append({
                        'product_name': product_name,
                        'product_code': product_code,
                        'unit_price_invoice': unit_price,
                        'unit_price_reference': None,
                        'status': 'new',
                        'message': f'Nouveau produit à {unit_price:.2f}€/unité - En attente de validation',
                        'restaurant': restaurant_name or 'Général'
                    })

            except Exception as e:
                print(f"❌ COMPARE_PRICES: Erreur traitement produit {i}: {e}")
                continue

        print(f"🏁 COMPARE_PRICES: Terminé - {comparison['new_products']} nouveaux produits ajoutés en attente")
        return comparison
    
    def add_pending_product_OLD(self, code: str, name: str, price: float, 
                           unit: str = 'unité', supplier: str = 'UNKNOWN', 
                           category: str = 'Non classé') -> int:
        """[DEPRECATED] Ajouter un produit en attente de validation - Utiliser add_pending_product avec dict"""
        # Appeler la nouvelle méthode
        product_data = {
            'code': code,
            'produit': name,
            'prix': price,
            'unite': unit,
            'fournisseur': supplier,
            'categorie': category
        }
        success = self.add_pending_product(product_data)
        return 1 if success else -1
    
    def get_pending_products(self) -> List[Dict]:
        """Récupérer tous les produits en attente de validation"""
        pending_file = 'data/pending_products.csv'
        if os.path.exists(pending_file):
            pending_df = pd.read_csv(pending_file)
            items = pending_df.to_dict('records')
            # Remplacer NaN par None pour éviter les erreurs JSON
            for item in items:
                for key, value in item.items():
                    if pd.isna(value):
                        item[key] = None
            return items
        return []
    
    def validate_pending_product(self, pending_id: int) -> bool:
        """Valider un produit en attente et l'ajouter aux prix de référence"""
        try:
            pending_file = 'data/pending_products.csv'
            prices_file = 'data/prices.csv'
            
            if not os.path.exists(pending_file):
                return False
            
            pending_df = pd.read_csv(pending_file)
            
            # Récupérer le produit en attente
            pending_product = pending_df[pending_df['id'] == pending_id]
            if pending_product.empty:
                return False
            
            # Préparer les données pour prices.csv avec la bonne structure
            pending_data = pending_product.iloc[0].to_dict()
            
            # Charger prices.csv existant
            if os.path.exists(prices_file):
                prices_df = pd.read_csv(prices_file)
                # Ajouter colonne restaurant si manquante
                if 'restaurant' not in prices_df.columns:
                    prices_df['restaurant'] = 'Général'
                    
                # 🚨 VÉRIFICATION DOUBLONS AVANT VALIDATION
                name_clean = pending_data.get('produit', '').strip().lower()
                supplier_clean = pending_data.get('fournisseur', '').upper()
                restaurant_check = pending_data.get('restaurant', 'Général')
                
                existing_validated = prices_df[
                    (prices_df['produit'].str.strip().str.lower() == name_clean) & 
                    (prices_df['fournisseur'].str.upper() == supplier_clean) &
                    (prices_df['restaurant'] == restaurant_check)
                ]
                
                if not existing_validated.empty:
                    print(f"⚠️ VALIDATE_PENDING: DOUBLON DÉTECTÉ! Produit '{pending_data.get('produit')}' déjà validé pour {supplier_clean} - Restaurant: {restaurant_check}")
                    # Supprimer de pending quand même car c'est un doublon
                    pending_df = pending_df[pending_df['id'] != pending_id]
                    pending_df.to_csv(pending_file, index=False)
                    return True  # Retourner true car "techniquement" validé (déjà existe)
                
                # Générer un nouvel ID
                if not prices_df.empty and 'id' in prices_df.columns:
                    numeric_ids = pd.to_numeric(prices_df['id'], errors='coerce')
                    max_id = numeric_ids.max()
                    new_id = int(max_id + 1) if pd.notna(max_id) else 1
                else:
                    new_id = 1
            else:
                # Créer nouveau fichier avec en-têtes - STRUCTURE COHÉRENTE
                prices_df = pd.DataFrame(columns=[
                    'id', 'code', 'produit', 'fournisseur', 'prix', 'unite', 
                    'categorie', 'restaurant', 'date_ajout', 'actif', 'source'
                ])
                new_id = 1
            
            # Mapper les colonnes de pending vers prices - CORRECTION STRUCTURE
            product_data = {
                'id': new_id,
                'code': pending_data.get('code', ''),
                'produit': pending_data.get('produit', ''),
                'fournisseur': pending_data.get('fournisseur', ''),
                'prix': float(pending_data.get('prix', 0)),  # ✅ CORRECTION: Garder 'prix' pour cohérence
                'unite': pending_data.get('unite', 'pièce'),
                'categorie': pending_data.get('categorie', 'Non classé'),
                'restaurant': pending_data.get('restaurant', 'Général'),  # Ajout restaurant
                'date_ajout': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'actif': True,
                'source': 'validated_pending'
            }
            
            # Ajouter aux prix de référence
            prices_df = pd.concat([prices_df, pd.DataFrame([product_data])], ignore_index=True)
            prices_df.to_csv(prices_file, index=False)
            
            # Recharger self.prices_db pour synchroniser
            self.prices_db = self._load_prices()
            
            # Supprimer de la liste d'attente
            pending_df = pending_df[pending_df['id'] != pending_id]
            pending_df.to_csv(pending_file, index=False)
            
            print(f"✅ Produit '{product_data['produit']}' validé et ajouté aux prix de référence (ID: {new_id})")
            
            # 🔥 Firestore push si activé
            if self._fs_enabled:
                try:
                    doc_id = product_data.get('code') or str(product_data['id'])
                    self._fs.collection('prices').document(doc_id).set(product_data)
                except Exception as e:
                    logger.warning(f"Firestore prices push KO: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur validation produit: {e}")
            return False
    
    def reject_pending_product(self, pending_id: int) -> bool:
        """Rejeter un produit en attente"""
        try:
            pending_file = 'data/pending_products.csv'
            if not os.path.exists(pending_file):
                return False
            
            pending_df = pd.read_csv(pending_file)
            initial_len = len(pending_df)
            
            # Supprimer le produit
            pending_df = pending_df[pending_df['id'] != pending_id]
            
            if len(pending_df) < initial_len:
                pending_df.to_csv(pending_file, index=False)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur rejet produit: {e}")
            return False
    
    def update_pending_product(self, pending_id: int, updates: Dict) -> bool:
        """Mettre à jour un produit en attente (prix, nom, etc.)"""
        try:
            pending_file = 'data/pending_products.csv'
            if not os.path.exists(pending_file):
                return False
            
            pending_df = pd.read_csv(pending_file)
            
            # Vérifier que le produit existe
            if pending_id not in pending_df['id'].values:
                return False
            
            # Appliquer les modifications
            idx = pending_df[pending_df['id'] == pending_id].index[0]
            
            # Mettre à jour uniquement les champs fournis
            updateable_fields = ['produit', 'prix', 'unite', 'code', 'fournisseur', 'categorie']
            for field in updateable_fields:
                if field in updates:
                    pending_df.loc[idx, field] = updates[field]
            
            # Mettre à jour la date de modification
            pending_df.loc[idx, 'date_ajout'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Sauvegarder
            pending_df.to_csv(pending_file, index=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur mise à jour produit en attente: {e}")
            return False
    
    def add_pending_product(self, product_data: Dict) -> bool:
        """Ajouter un produit en attente depuis un dict (pour scanner batch)"""
        try:
            print(f"💾 ADD_PENDING: Démarrage ajout produit en attente")
            print(f"💾 ADD_PENDING: Données reçues: {product_data}")
            
            code = product_data.get('code', '')
            name = product_data.get('produit', product_data.get('name', ''))
            price = float(product_data.get('prix', product_data.get('price', 0)))
            unit = product_data.get('unite', product_data.get('unit', 'pièce'))
            supplier = product_data.get('fournisseur', product_data.get('supplier', 'SCANNER'))
            restaurant = product_data.get('restaurant', 'Général')  # Nouveau champ restaurant
            
            print(f"💾 ADD_PENDING: Valeurs extraites - nom:'{name}', prix:{price}, fournisseur:'{supplier}', restaurant:'{restaurant}'")
            
            if not name or price <= 0:
                print(f"❌ ADD_PENDING: Validation échouée - nom vide ou prix invalide")
                return False
            
            # Charger les produits en attente
            pending_file = 'data/pending_products.csv'
            if os.path.exists(pending_file):
                pending_df = pd.read_csv(pending_file)
            else:
                pending_df = pd.DataFrame(columns=[
                    'id', 'code', 'produit', 'fournisseur', 'prix', 'unite', 
                    'categorie', 'date_ajout', 'source', 'restaurant'  # Ajout colonne restaurant
                ])
            
            # Ajouter la colonne restaurant si elle n'existe pas
            if 'restaurant' not in pending_df.columns:
                pending_df['restaurant'] = 'Général'
            
            # Générer un code si manquant
            if not code:
                code = self._generate_pending_code(name, supplier)
            
            # 🔍 VÉRIFICATION STRICTE DES DOUBLONS (nom similaire + fournisseur + restaurant)
            if not pending_df.empty:
                # Nettoyer les noms pour comparaison (enlever espaces, casse)
                pending_df['produit_clean'] = pending_df['produit'].str.strip().str.lower()
                name_clean = name.strip().lower()
                
                existing = pending_df[
                    (pending_df['produit_clean'] == name_clean) & 
                    (pending_df['fournisseur'].str.upper() == supplier.upper()) &
                    (pending_df['restaurant'] == restaurant)
                ]
                
                if not existing.empty:
                    print(f"⚠️ Produit '{name}' ({supplier}) déjà en attente pour {restaurant} - mise à jour du prix")
                    # Mettre à jour le prix existant au lieu d'ajouter un doublon
                    idx = existing.index[0]
                    pending_df.loc[idx, 'prix'] = price
                    pending_df.loc[idx, 'date_ajout'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Supprimer la colonne temporaire et sauvegarder
                    pending_df = pending_df.drop('produit_clean', axis=1)
                    pending_df.to_csv(pending_file, index=False)
                    return True
                
                # Supprimer la colonne temporaire
                pending_df = pending_df.drop('produit_clean', axis=1)
            
            # 🔍 VÉRIFIER AUSSI S'IL EXISTE DÉJÀ DANS LES PRIX VALIDÉS
            prices_file = 'data/prices.csv'
            if os.path.exists(prices_file):
                prices_df = pd.read_csv(prices_file)
                if not prices_df.empty:
                    # Ajouter colonne restaurant si manquante
                    if 'restaurant' not in prices_df.columns:
                        prices_df['restaurant'] = 'Général'
                    
                    # 🚨 VÉRIFICATION STRICTE - nom + fournisseur + restaurant
                    name_clean = name.strip().lower()
                    existing_in_prices = prices_df[
                        (prices_df['produit'].str.strip().str.lower() == name_clean) & 
                        (prices_df['fournisseur'].str.upper() == supplier.upper()) &
                        (prices_df['restaurant'] == restaurant)
                    ]
                    
                    if not existing_in_prices.empty:
                        print(f"ℹ️ DOUBLON DÉTECTÉ: Produit '{name}' ({supplier}) déjà validé pour restaurant {restaurant} - ignoré")
                        return True  # Ne pas ajouter car déjà validé
            
            # Ajouter nouveau produit en attente
            new_id = int(pending_df['id'].max()) + 1 if not pending_df.empty and 'id' in pending_df.columns else 1
            new_product = {
                'id': new_id,
                'code': code,
                'produit': name,
                'fournisseur': supplier,
                'prix': price,
                'unite': unit,
                'categorie': product_data.get('categorie', 'Auto'),
                'date_ajout': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': product_data.get('source', 'scanner_auto'),
                'restaurant': restaurant  # Ajouter le restaurant
            }
            
            pending_df = pd.concat([pending_df, pd.DataFrame([new_product])], ignore_index=True)
            
            # Sauvegarder
            print(f"💾 ADD_PENDING: Sauvegarde en cours dans {pending_file}")
            os.makedirs('data', exist_ok=True)
            pending_df.to_csv(pending_file, index=False)
            
            print(f"✅ ADD_PENDING: Nouveau produit en attente sauvegardé: '{name}' ({supplier}) - {price}€ - Restaurant: {restaurant}")
            print(f"✅ ADD_PENDING: ID assigné: {new_id}")
            
            # 🔥 Firestore push si activé
            if self._fs_enabled:
                try:
                    doc_id = new_product.get('code') or str(int(datetime.now().timestamp()))
                    self._fs.collection('prices').document(doc_id).set(new_product)
                except Exception as e:
                    logger.warning(f"Firestore prices push KO: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ ADD_PENDING: Erreur lors de l'ajout: {e}")
            logger.error(f"Erreur ajout produit en attente (dict): {e}")
            return False
    
    def _generate_pending_code(self, name: str, supplier: str) -> str:
        """Générer un code pour un produit en attente"""
        # Prendre les 3 premières lettres du nom et fournisseur
        name_part = ''.join(c for c in name[:3] if c.isalnum()).upper()
        supplier_part = ''.join(c for c in supplier[:3] if c.isalnum()).upper()
        
        # Ajouter timestamp
        timestamp = datetime.now().strftime('%m%d')
        
        return f"P{supplier_part}{name_part}{timestamp}"
    
    def add_confirmed_product_directly(self, product_data: Dict) -> bool:
        """
        Ajouter un produit directement dans les prix confirmés (pour création manuelle)
        SANS passer par les produits en attente
        """
        try:
            print(f"💾 ADD_CONFIRMED: Ajout direct produit confirmé")
            print(f"💾 ADD_CONFIRMED: Données reçues: {product_data}")
            
            # Valider les données
            name = product_data.get('produit', product_data.get('name', '')).strip()
            price = float(product_data.get('prix', product_data.get('unit_price', 0)))
            supplier = product_data.get('fournisseur', product_data.get('supplier', 'MANUEL'))
            restaurant = product_data.get('restaurant', 'Général')
            
            if not name or price <= 0 or not supplier:
                print(f"❌ ADD_CONFIRMED: Validation échouée - données manquantes")
                return False
            
            # 🚨 VÉRIFICATION STRICTE DOUBLONS - nom + fournisseur + restaurant
            prices_file = 'data/prices.csv'
            if os.path.exists(prices_file):
                existing_df = pd.read_csv(prices_file)
                if not existing_df.empty:
                    # Ajouter colonne restaurant si manquante pour compatibilité
                    if 'restaurant' not in existing_df.columns:
                        existing_df['restaurant'] = 'Général'
                    
                    # Vérifier doublons STRICT (nom + fournisseur + restaurant)
                    name_clean = name.strip().lower()
                    existing = existing_df[
                        (existing_df['produit'].str.strip().str.lower() == name_clean) & 
                        (existing_df['fournisseur'].str.upper() == supplier.upper()) &
                        (existing_df['restaurant'] == restaurant)
                    ]
                    if not existing.empty:
                        print(f"⚠️ ADD_CONFIRMED: DOUBLON DÉTECTÉ! Produit '{name}' déjà confirmé pour {supplier} - Restaurant: {restaurant}")
                        return False
            
            # Préparer les données pour prices.csv avec la structure correcte
            new_price = {
                'code': product_data.get('code', ''),
                'produit': name,
                'fournisseur': supplier,
                'prix': price,  # Note: dans prices.csv c'est 'prix' mais parfois lu comme 'prix_unitaire'
                'unite': product_data.get('unite', product_data.get('unit', 'unité')),
                'categorie': product_data.get('categorie', product_data.get('category', 'Manuel')),
                'restaurant': restaurant,
                'date_maj': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'actif': True,
                'source': 'manual_direct'
            }
            
            # Générer un code si manquant
            if not new_price['code']:
                new_price['code'] = self._generate_product_code(name, supplier)
            
            # Charger ou créer le fichier prices.csv
            if os.path.exists(prices_file):
                prices_df = pd.read_csv(prices_file)
                # Générer un nouvel ID
                if not prices_df.empty and 'id' in prices_df.columns:
                    numeric_ids = pd.to_numeric(prices_df['id'], errors='coerce')
                    max_id = numeric_ids.max()
                    new_id = int(max_id + 1) if pd.notna(max_id) else 1
                else:
                    new_id = 1
            else:
                # Créer nouveau fichier
                prices_df = pd.DataFrame(columns=[
                    'id', 'code', 'produit', 'fournisseur', 'prix', 'unite', 
                    'categorie', 'restaurant', 'date_maj', 'actif', 'source'
                ])
                new_id = 1
            
            new_price['id'] = new_id
            
            # Ajouter le nouveau produit
            new_row = pd.DataFrame([new_price])
            prices_df = pd.concat([prices_df, new_row], ignore_index=True)
            
            # Sauvegarder
            os.makedirs('data', exist_ok=True)
            prices_df.to_csv(prices_file, index=False)
            
            # 🔄 SYNCHRONISATION CRITIQUE: Recharger IMMÉDIATEMENT les données en mémoire
            self.prices_db = self._load_prices()
            
            # 🚨 VÉRIFICATION FINALE: S'assurer que le produit est bien ajouté
            final_check = self.prices_db[
                (self.prices_db['produit'].str.strip().str.lower() == name.strip().lower()) & 
                (self.prices_db['fournisseur'].str.upper() == supplier.upper())
            ]
            if final_check.empty:
                print(f"❌ ADD_CONFIRMED: ERREUR CRITIQUE - Produit non trouvé après sauvegarde!")
                return False
            
            print(f"✅ ADD_CONFIRMED: Produit '{name}' ajouté directement en confirmé (ID: {new_id}) - Vérification finale OK")
            
            # 🔥 Firestore push si activé
            if self._fs_enabled:
                try:
                    doc_id = new_price.get('code') or str(new_price['id'])
                    self._fs.collection('prices').document(doc_id).set(new_price)
                except Exception as e:
                    logger.warning(f"Firestore prices push KO: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ ADD_CONFIRMED: Erreur lors de l'ajout: {e}")
            logger.error(f"Erreur ajout produit confirmé direct: {e}")
            return False

    def add_price(self, price_data: Dict) -> bool:
        """
        Ajouter un nouveau prix de référence
        AVEC SYNCHRONISATION AUTOMATIQUE si activée
        """
        try:
            # Valider les données
            required_fields = ['produit', 'prix']
            for field in required_fields:
                if field not in price_data or not price_data[field]:
                    logger.error(f"Champ requis manquant: {field}")
                    return False
            
            # Préparer les données
            new_price = {
                'code': price_data.get('code', ''),
                'produit': str(price_data['produit']).strip(),
                'fournisseur': price_data.get('fournisseur', 'UNKNOWN'),
                'prix': float(price_data['prix']),
                'unite': price_data.get('unite', 'unité'),
                'categorie': price_data.get('categorie', 'Non classé'),
                'restaurant': price_data.get('restaurant', 'Général'),
                'date_maj': datetime.now().strftime('%Y-%m-%d'),
                'actif': True
            }
            
            # Générer un code si manquant
            if not new_price['code']:
                temp_series = pd.Series(new_price)
                new_price['code'] = self._generate_product_code(temp_series)
            
            # Ajouter à la base de données
            new_row = pd.DataFrame([new_price])
            self.prices_db = pd.concat([self.prices_db, new_row], ignore_index=True)
            
            # Sauvegarder
            self._save_prices()
            
            # 🔄 SYNCHRONISATION AUTOMATIQUE
            restaurant_name = price_data.get('restaurant')
            if restaurant_name and restaurant_name != 'Général':
                try:
                    from sync_manager import SyncManager
                    sync_manager = SyncManager()
                    
                    # Synchroniser vers les autres restaurants du groupe
                    sync_result = sync_manager.sync_prices_to_group(restaurant_name, price_data)
                    if sync_result.get('synced_count', 0) > 0:
                        logger.info(f"Prix synchronisé vers {sync_result['synced_count']} restaurant(s)")
                except Exception as sync_error:
                    logger.warning(f"Erreur synchronisation prix: {sync_error}")
                    # Ne pas faire échouer l'ajout si la sync échoue
            
            # 🔥 Firestore push si activé
            if self._fs_enabled:
                try:
                    doc_id = new_price.get('code') or str(int(datetime.now().timestamp()))
                    self._fs.collection('prices').document(doc_id).set(new_price)
                except Exception as e:
                    logger.warning(f"Firestore prices push KO: {e}")
            
            logger.info(f"Prix ajouté: {new_price['produit']} - {new_price['prix']}€")
            return True
            
        except Exception as e:
            logger.error(f"Erreur ajout prix: {e}")
            return False
    
    def _generate_product_code(self, product_name: str, supplier: str) -> str:
        """Générer un code produit automatique"""
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
    
    def update_price(self, code: str, updates: Dict) -> bool:
        """Mettre à jour un prix existant"""
        try:
            if code not in self.prices_db['code'].values:
                raise ValueError(f"Code produit non trouvé: {code}")
            
            # Appliquer les mises à jour
            idx = self.prices_db[self.prices_db['code'] == code].index[0]
            for key, value in updates.items():
                if key in self.prices_db.columns:
                    self.prices_db.loc[idx, key] = value
            
            # Mettre à jour la date
            self.prices_db.loc[idx, 'date_maj'] = datetime.now().strftime('%Y-%m-%d')
            
            # Sauvegarder
            self._save_prices()
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur mise à jour prix: {e}")
            return False
    
    def update_price_by_id(self, price_id: int, updates: Dict) -> bool:
        """Mettre à jour un prix existant par ID"""
        try:
            # Convertir l'ID en index (ID commence à 1, index à 0)
            idx = price_id - 1
            
            if idx < 0 or idx >= len(self.prices_db):
                raise ValueError(f"ID produit non trouvé: {price_id}")
            
            # Appliquer les mises à jour
            for key, value in updates.items():
                # Mapper les clés du frontend vers les colonnes de la DB
                if key == 'produit' and 'produit' in self.prices_db.columns:
                    self.prices_db.loc[idx, 'produit'] = value
                elif key == 'prix' and 'prix' in self.prices_db.columns:
                    self.prices_db.loc[idx, 'prix'] = float(value)
                elif key == 'unite' and 'unite' in self.prices_db.columns:
                    self.prices_db.loc[idx, 'unite'] = value
                elif key in self.prices_db.columns:
                    self.prices_db.loc[idx, key] = value
            
            # Mettre à jour la date
            self.prices_db.loc[idx, 'date_maj'] = datetime.now().strftime('%Y-%m-%d')
            
            # Sauvegarder
            self._save_prices()
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur mise à jour prix par ID: {e}")
            return False
    
    def delete_price(self, code: str) -> bool:
        """Supprimer un prix (désactivation) par code"""
        try:
            if code not in self.prices_db['code'].values:
                raise ValueError(f"Code produit non trouvé: {code}")
            
            # Désactiver au lieu de supprimer
            idx = self.prices_db[self.prices_db['code'] == code].index[0]
            self.prices_db.loc[idx, 'actif'] = False
            self.prices_db.loc[idx, 'date_maj'] = datetime.now().strftime('%Y-%m-%d')
            
            # Sauvegarder
            self._save_prices()
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur suppression prix: {e}")
            return False
    
    def delete_price_by_id(self, price_id: int) -> bool:
        """Supprimer un prix (désactivation) par ID"""
        try:
            # Convertir l'ID en index (ID commence à 1, index à 0)
            idx = price_id - 1
            
            if idx < 0 or idx >= len(self.prices_db):
                raise ValueError(f"ID produit non trouvé: {price_id}")
            
            # Désactiver au lieu de supprimer
            self.prices_db.loc[idx, 'actif'] = False
            self.prices_db.loc[idx, 'date_maj'] = datetime.now().strftime('%Y-%m-%d')
            
            # Sauvegarder
            self._save_prices()
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur suppression prix par ID: {e}")
            return False
    
    def delete_price_cascade(self, price_id: int) -> Dict[str, Any]:
        """Supprimer complètement un produit et toutes ses références (factures, prix en attente)"""
        try:
            # Récupérer le produit à supprimer
            if price_id >= len(self.prices_db):
                return {'success': False, 'error': 'Produit non trouvé'}
            
            product_row = self.prices_db.iloc[price_id]
            product_name = product_row['produit']
            product_code = product_row.get('code', '')
            
            # Statistiques de suppression
            stats = {
                'product_name': product_name,
                'deleted_pending': 0,
                'deleted_invoices': 0,
                'deleted_references': 0
            }
            
            # 1. Supprimer de la base de prix de référence
            self.prices_db = self.prices_db.drop(self.prices_db.index[price_id]).reset_index(drop=True)
            self._save_prices()
            stats['deleted_references'] = 1
            
            # 2. Supprimer des produits en attente (même nom ou code)
            pending_file = 'data/pending_products.csv'
            if os.path.exists(pending_file):
                pending_df = pd.read_csv(pending_file)
                initial_pending_count = len(pending_df)
                
                # Supprimer par nom ou code
                pending_df = pending_df[
                    ~((pending_df['produit'].str.lower() == product_name.lower()) |
                      (pending_df.get('code', '') == product_code))
                ]
                
                stats['deleted_pending'] = initial_pending_count - len(pending_df)
                pending_df.to_csv(pending_file, index=False)
            
            # 3. Supprimer des factures contenant ce produit
            invoices_file = 'data/invoices.json'
            if os.path.exists(invoices_file):
                try:
                    with open(invoices_file, 'r', encoding='utf-8') as f:
                        invoices_data = json.load(f)
                    
                    if isinstance(invoices_data, dict) and 'invoices' in invoices_data:
                        invoices = invoices_data['invoices']
                        initial_invoice_count = len(invoices)
                        
                        # Filtrer les factures qui contiennent ce produit
                        filtered_invoices = []
                        for invoice in invoices:
                            products = invoice.get('products', [])
                            analysis_products = invoice.get('analysis', {}).get('products', [])
                            
                            # Vérifier si le produit est dans cette facture
                            has_product = False
                            
                            for product in products + analysis_products:
                                if (product.get('name', '').lower() == product_name.lower() or
                                    product.get('produit', '').lower() == product_name.lower() or
                                    product.get('code', '') == product_code):
                                    has_product = True
                                    break
                            
                            if not has_product:
                                filtered_invoices.append(invoice)
                        
                        stats['deleted_invoices'] = initial_invoice_count - len(filtered_invoices)
                        
                        # Sauvegarder les factures filtrées
                        invoices_data['invoices'] = filtered_invoices
                        invoices_data['last_updated'] = datetime.now().isoformat()
                        
                        with open(invoices_file, 'w', encoding='utf-8') as f:
                            json.dump(invoices_data, f, ensure_ascii=False, indent=2)
                            
                except Exception as e:
                    logger.error(f"Erreur suppression factures: {e}")
            
            return {
                'success': True,
                'stats': stats,
                'message': f"Produit '{product_name}' supprimé avec toutes ses références"
            }
            
        except Exception as e:
            logger.error(f"Erreur suppression cascade: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_suppliers(self) -> List[str]:
        """Récupérer la liste des fournisseurs disponibles"""
        try:
            # Fournisseurs des prix de référence
            ref_suppliers = set()
            if not self.prices_db.empty and 'fournisseur' in self.prices_db.columns:
                ref_suppliers = set(self.prices_db['fournisseur'].dropna().unique())
            
            # Fournisseurs des produits en attente
            pending_suppliers = set()
            pending_file = 'data/pending_products.csv'
            if os.path.exists(pending_file):
                pending_df = pd.read_csv(pending_file)
                if not pending_df.empty and 'fournisseur' in pending_df.columns:
                    pending_suppliers = set(pending_df['fournisseur'].dropna().unique())
            
            # Combiner et trier
            all_suppliers = sorted(list(ref_suppliers.union(pending_suppliers)))
            
            # Filtrer les valeurs vides
            all_suppliers = [s for s in all_suppliers if s and str(s).strip()]
            
            # 🔥 NOUVEAU: Exclure les fournisseurs supprimés
            try:
                from modules.supplier_manager import SupplierManager
                supplier_manager = SupplierManager()
                deleted_suppliers = supplier_manager._get_deleted_suppliers()
                
                # Filtrer les fournisseurs supprimés
                all_suppliers = [s for s in all_suppliers if s not in deleted_suppliers]
                
                logger.info(f"Fournisseurs filtrés: {len(deleted_suppliers)} supprimés exclus")
            except Exception as e:
                logger.warning(f"Impossible de filtrer les fournisseurs supprimés: {e}")
            
            return all_suppliers
            
        except Exception as e:
            logger.error(f"Erreur récupération fournisseurs: {e}")
            return []
    
    def get_prices_by_suppliers(self, supplier_names: List[str]) -> List[Dict[str, Any]]:
        """Récupérer les prix pour une liste de fournisseurs spécifiques"""
        try:
            if not supplier_names:
                return []
            
            # Filtrer les prix par fournisseurs
            filtered_df = self.prices_db[
                self.prices_db['fournisseur'].isin(supplier_names)
            ]
            
            # Convertir en dictionnaire
            prices = filtered_df.to_dict('records')
            
            # Nettoyer les valeurs NaN
            for price in prices:
                for key, value in price.items():
                    if pd.isna(value):
                        price[key] = None
            
            return prices
            
        except Exception as e:
            logger.error(f"Erreur récupération prix par fournisseurs: {e}")
            return []
    
    def find_product_price(self, product_name: str, supplier: str = '', restaurant: str = 'Général') -> Optional[Dict]:
        """
        Rechercher le prix d'un produit dans le catalogue
        
        Args:
            product_name: Nom du produit à rechercher
            supplier: Fournisseur (optionnel)
            restaurant: Restaurant (défaut: Général)
            
        Returns:
            Dict avec les infos du produit ou None si non trouvé
        """
        try:
            # Charger les prix validés
            prices_file = 'data/prices.csv'
            if not os.path.exists(prices_file):
                return None
            
            df = pd.read_csv(prices_file)
            
            if df.empty:
                return None
            
            # Standardiser les noms pour la recherche
            product_name_clean = product_name.strip().lower()
            
            # Recherche exacte d'abord
            mask = df['produit'].str.lower() == product_name_clean
            
            # Filtre fournisseur si spécifié
            if supplier:
                mask = mask & (df['fournisseur'] == supplier)
            
            # Filtre restaurant si colonne existe
            if 'restaurant' in df.columns:
                mask = mask & (
                    (df['restaurant'] == restaurant) |
                    (df['restaurant'] == 'Général') |
                    (df['restaurant'].isna())
                )
            
            matches = df[mask]
            
            if not matches.empty:
                # Prendre le premier match
                match = matches.iloc[0]
                return {
                    'code': match.get('code', ''),
                    'produit': match.get('produit', ''),
                    'prix_unitaire': float(match.get('prix', 0)),
                    'fournisseur': match.get('fournisseur', ''),
                    'restaurant': match.get('restaurant', 'Général'),
                    'unite': match.get('unite', 'unité'),
                    'categorie': match.get('categorie', '')
                }
            
            # Si pas de match exact, essayer une recherche partielle
            mask_partial = df['produit'].str.lower().str.contains(product_name_clean, na=False)
            
            # Filtre fournisseur si spécifié
            if supplier:
                mask_partial = mask_partial & (df['fournisseur'] == supplier)
            
            # Filtre restaurant si colonne existe
            if 'restaurant' in df.columns:
                mask_partial = mask_partial & (
                    (df['restaurant'] == restaurant) |
                    (df['restaurant'] == 'Général') |
                    (df['restaurant'].isna())
                )
            
            partial_matches = df[mask_partial]
            
            if not partial_matches.empty:
                # Prendre le premier match partiel
                match = partial_matches.iloc[0]
                return {
                    'code': match.get('code', ''),
                    'produit': match.get('produit', ''),
                    'prix_unitaire': float(match.get('prix', 0)),
                    'fournisseur': match.get('fournisseur', ''),
                    'restaurant': match.get('restaurant', 'Général'),
                    'unite': match.get('unite', 'unité'),
                    'categorie': match.get('categorie', '')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur recherche produit {product_name}: {e}")
            return None 