"""
Module Claude Vision pour l'analyse intelligente des factures
Utilise Claude 3 Opus pour analyser les images de factures
"""

import os
import base64
import json
import re
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import anthropic
from PIL import Image

# Support HEIF/HEIC avec gestion d'erreur
try:
    import pillow_heif
    # Enregistrer le support HEIF
    pillow_heif.register_heif_opener()
    HEIF_SUPPORT = True
    print("✅ Support HEIF/HEIC activé")
except ImportError as e:
    HEIF_SUPPORT = False
    print(f"⚠️ Support HEIF/HEIC non disponible: {e}")

logger = logging.getLogger(__name__)

class ClaudeVision:
    """Analyseur de factures avec Claude Vision"""
    
    def __init__(self):
        try:
            # Debug: vérifier les variables d'environnement
            print("🔍 Debug: Vérification des variables d'environnement...")
            api_key = os.getenv('ANTHROPIC_API_KEY')
            print(f"🔍 API Key trouvée: {api_key is not None}")
            if api_key:
                print(f"🔍 API Key commence par: {api_key[:10]}...")
            else:
                print("❌ ANTHROPIC_API_KEY est None ou vide")
                # Essayer d'autres noms possibles
                alt_key = os.getenv('ANTHROPIC_KEY')
                print(f"🔍 ANTHROPIC_KEY alternative: {alt_key is not None}")
            
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY non trouvée dans les variables d'environnement")
            
            print("🔄 Création du client Anthropic...")
            self.client = anthropic.Anthropic(
                api_key=api_key
            )
            self.model = "claude-3-5-sonnet-20241022"  # Modèle plus puissant pour une meilleure lecture d'image
            
            print(f"✅ Claude Vision initialisé avec succès")
            
            # Prompts spécialisés par fournisseur
            self.supplier_prompts = {
                'METRO': """Tu es un expert en analyse de factures METRO/MAKRO. 
Analyse cette facture et extrait UNIQUEMENT les produits alimentaires réels (viandes, poissons, légumes, épicerie).

RÈGLES STRICTES METRO:
- IGNORE les codes techniques (2524179, 2525073, etc.)
- IGNORE les mentions "ENTRECOTES250/280", "BAVETTES 220/240" 
- GARDE SEULEMENT le nom du produit alimentaire principal
- Exemple: "2524179 BAVETTES 220/240 GR X 5 BUREAU" → "Bavettes de bœuf"
- Exemple: "2525073 HACHE F. BOUCHERE ROND" → "Haché de bœuf"
- IGNORE les lignes de TVA, totaux, codes client
- Prix en euros avec virgule décimale

STRUCTURE JSON OBLIGATOIRE - RESPECTE EXACTEMENT CE FORMAT:
{
  "supplier": "METRO",
  "invoice_number": "numéro de bon",
  "date": "YYYY-MM-DD", 
  "total_amount": 123.45,
  "products": [
    {
      "name": "Bavettes de bœuf",
      "quantity": 5,
      "unit": "pièce",
      "unit_price": 36.87,
      "total_price": 184.36
    }
  ]
}

IMPORTANT: Réponds UNIQUEMENT avec ce JSON exact, rien d'autre.""",

                'MVA': """Tu es un expert en analyse de factures MVA - ULTRA-PRÉCIS.

RÈGLES SPÉCIALES MVA (qui fonctionnent parfaitement):
- Lis CHAQUE ligne de produit alimentaire
- MVA a un format très clair: Nom | Quantité | Prix
- Extrait TOUS les produits, sans exception
- Les quantités sont souvent en kg, pièces, litres
- Ignore seulement: TVA, totaux, en-têtes

MÉTHODOLOGIE MVA:
1. Scan ligne par ligne depuis le haut
2. Identifie tous les produits alimentaires 
3. Extrais quantités exactes et prix
4. Vérifie de n'avoir rien oublié

STRUCTURE JSON MVA:
{
  "supplier": "MVA",
  "invoice_number": "numéro facture MVA",
  "date": "YYYY-MM-DD",
  "total_amount": 123.45,
  "products": [
    {
      "name": "nom produit MVA",
      "quantity": 1.5,
      "unit": "kg",
      "unit_price": 12.50,
      "total_price": 18.75
    }
  ]
}

IMPORTANT: Sois aussi précis que d'habitude avec MVA - TOUS les produits !""",

                'TRANSGOURMET': """Tu es un expert en analyse de factures TRANSGOURMET.
Analyse cette facture et extrait UNIQUEMENT les produits alimentaires réels.

RÈGLES STRICTES TRANSGOURMET:
- IGNORE les codes produits numériques
- GARDE le nom alimentaire principal
- IGNORE les mentions techniques de conditionnement
- Focus sur: viandes, poissons, légumes, épicerie, produits laitiers

STRUCTURE JSON OBLIGATOIRE - RESPECTE EXACTEMENT CE FORMAT:
{
  "supplier": "TRANSGOURMET",
  "invoice_number": "numero facture",
  "date": "YYYY-MM-DD",
  "total_amount": 156.78,
  "products": [
    {
      "name": "nom du produit",
      "quantity": 2,
      "unit": "kg",
      "unit_price": 12.50,
      "total_price": 25.00
    }
  ]
}

IMPORTANT: Réponds UNIQUEMENT avec ce JSON exact, rien d'autre.""",

                'GENERIC': """Tu es un expert en analyse de factures alimentaires ULTRA-MÉTICULEUX.

⚠️ MISSION CRITIQUE: TROUVER ABSOLUMENT TOUTES LES LIGNES DE PRODUITS

MÉTHODOLOGIE STRICTE - OBLIGATOIRE:
1. COMMENCE PAR LE HAUT de la facture
2. LIS CHAQUE LIGNE une par une, de haut en bas
3. IDENTIFIE chaque produit alimentaire, même le plus petit
4. DESCENDS ligne par ligne jusqu'en bas - N'OUBLIE RIEN
5. VÉRIFIE 3 FOIS que tu as tout lu

RÈGLES ULTRA-STRICTES:
✓ Lis TOUTES les lignes - même en bas de page
✓ Trouve TOUS les produits alimentaires 
✓ Extrais TOUTES les quantités exactes
✓ Relève TOUS les prix (unitaires + totaux)
✓ Double-contrôle: si tu vois 15 lignes produits, je dois avoir 15 produits dans le JSON

FORMATS À CHERCHER (exemples):
"Filet de bœuf 2.5kg 45.80€"
"Tomates cerises 1kg 6.50€"
"Saumon fumé 500g 12.90€"
"Pain complet 3 pièces 4.20€"
"Lait bio 2L 3.80€"
"Pommes golden 2kg 5.60€"

STRUCTURE JSON - TOUS LES PRODUITS TROUVÉS:
{
  "supplier": "nom exact visible sur la facture",
  "invoice_number": "numéro exact de la facture",
  "date": "YYYY-MM-DD",
  "total_amount": 123.45,
  "products": [
    {
      "name": "nom exact du produit",
      "quantity": 2.5,
      "unit": "kg",
      "unit_price": 18.32,
      "total_price": 45.80
    }
  ]
}

⚠️ CONTRÔLE QUALITÉ FINAL:
- Compte le nombre de lignes produits sur l'image
- Vérifie que ton JSON a le même nombre de produits
- Si il y a 10 produits visibles, il DOIT y avoir 10 entrées dans le JSON

IMPORTANT: Réponds UNIQUEMENT avec le JSON complet contenant TOUS les produits."""
            }
        
        except Exception as e:
            print(f"❌ ERREUR DÉTAILLÉE initialisation Claude Vision: {type(e).__name__}: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            self.client = None
            self.model = None
    
    def analyze_invoice_image(self, image_path: str) -> Dict[str, Any]:
        """
        Analyser une image de facture avec Claude Vision
        """
        try:
            # Test de connexion d'abord
            if not self.test_api_connection():
                return {
                    'success': False,
                    'error': 'Impossible de se connecter à l\'API Anthropic'
                }
            
            # Vérifier que le fichier existe
            if not os.path.exists(image_path):
                return {
                    'success': False,
                    'error': f'Fichier non trouvé: {image_path}'
                }
            
            # Convertir l'image en base64
            image_base64 = self._image_to_base64(image_path)
            if not image_base64:
                return {
                    'success': False,
                    'error': 'Impossible de lire l\'image'
                }
            
            # Détecter le fournisseur d'abord avec un prompt simple
            supplier = self._detect_supplier_from_image(image_base64)
            logger.info(f"🏪 Fournisseur détecté: {supplier}")
            
            # Choisir le prompt approprié
            system_prompt = self.supplier_prompts.get(supplier, self.supplier_prompts['GENERIC'])
            
            # Préparer le message pour Claude
            message = {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": f"""ATTENTION: Tu dois analyser EXACTEMENT ce qui est écrit sur cette image de facture.

INSTRUCTIONS STRICTES:
1. LIS VRAIMENT le texte visible sur l'image - ne devine pas, n'invente pas
2. IDENTIFIE le vrai nom du fournisseur écrit en haut de la facture
3. EXTRAIT seulement les produits alimentaires RÉELLEMENT listés avec leurs prix
4. Si tu ne vois pas clairement quelque chose, mets "N/A" plutôt que d'inventer

Analyse cette facture {supplier} et extrait UNIQUEMENT les informations VISIBLES sur l'image.

RÉPONDS UNIQUEMENT avec le JSON dans le format exact demandé."""
                    }
                ]
            }
            
            # Appel à Claude Vision
            logger.info(f"🤖 Analyse {supplier} avec Claude Vision...")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=system_prompt,
                messages=[message]
            )
            
            # Extraire le texte de la réponse
            response_text = response.content[0].text.strip()
            logger.info(f"📝 Réponse Claude BRUTE (premiers 500 chars): {response_text[:500]}")
            logger.info(f"📝 Réponse Claude COMPLÈTE: {response_text}")
            
            # Parser le JSON
            try:
                # Nettoyer la réponse
                original_text = response_text
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                
                logger.info(f"🧹 Texte nettoyé: {response_text}")
                
                analysis_data = json.loads(response_text.strip())
                logger.info(f"✅ JSON parsé avec succès: {analysis_data}")
                
                # Valider et enrichir les données
                analysis_data = self._validate_and_enrich_data(analysis_data)
                logger.info(f"🔍 Données enrichies: {analysis_data}")
                
                return {
                    'success': True,
                    'data': analysis_data,
                    'raw_response': original_text
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Erreur parsing JSON: {e}")
                logger.error(f"📄 Texte qui a causé l'erreur: '{response_text}'")
                return {
                    'success': False,
                    'error': f'Réponse JSON invalide: {str(e)}',
                    'raw_response': original_text
                }
                
        except Exception as e:
            logger.error(f"Erreur Claude Vision: {e}")
            return {
                'success': False,
                'error': f'Erreur lors de l\'analyse: {str(e)}'
            }
    
    def _image_to_base64(self, image_path: str) -> Optional[str]:
        """Convertir une image en base64"""
        try:
            logger.info(f"🔄 Conversion image: {image_path}")
            
            # Vérifier l'existence du fichier
            if not os.path.exists(image_path):
                logger.error(f"❌ Fichier introuvable: {image_path}")
                return None
            
            # Obtenir l'extension du fichier
            file_ext = os.path.splitext(image_path)[1].lower()
            logger.info(f"📄 Extension détectée: {file_ext}")
            
            # Pour les fichiers HEIC/HEIF, utiliser une approche spéciale
            if file_ext in ['.heic', '.heif']:
                logger.info("🔄 Traitement spécial pour fichier HEIC/HEIF")
                return self._convert_heic_to_base64(image_path)
            
            # Pour les autres formats, utiliser PIL standard
            logger.info("🔄 Ouverture de l'image avec PIL...")
            with Image.open(image_path) as img:
                logger.info(f"📊 Image ouverte: {img.size}, mode: {img.mode}")
                
                # Convertir en RGB si nécessaire
                if img.mode != 'RGB':
                    logger.info(f"🔄 Conversion {img.mode} -> RGB")
                    img = img.convert('RGB')
                
                # Redimensionner si trop grande (max 2048px pour meilleure qualité)
                max_size = 2048
                if max(img.size) > max_size:
                    logger.info(f"🔄 Redimensionnement de {img.size} vers max {max_size}px")
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Créer un nom de fichier temporaire unique
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    temp_path = temp_file.name
                
                logger.info(f"💾 Sauvegarde temporaire: {temp_path}")
                # Sauvegarder en JPEG avec qualité maximale
                img.save(temp_path, 'JPEG', quality=95, optimize=True)
                
                # Lire et encoder en base64
                logger.info("🔢 Encodage en base64...")
                with open(temp_path, 'rb') as f:
                    image_data = f.read()
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                
                # Supprimer le fichier temporaire
                try:
                    os.remove(temp_path)
                    logger.info("🗑️ Fichier temporaire supprimé")
                except:
                    pass  # Pas grave si on ne peut pas supprimer
                
                logger.info(f"✅ Conversion réussie: {len(base64_data)} caractères")
                return base64_data
                
        except Exception as e:
            logger.error(f"❌ Erreur conversion image: {e}")
            import traceback
            logger.error(f"📍 Traceback: {traceback.format_exc()}")
            return None
    
    def _convert_heic_to_base64(self, image_path: str) -> Optional[str]:
        """Convertir un fichier HEIC/HEIF en base64 avec méthode alternative"""
        try:
            logger.info("🔄 Conversion HEIC avec pillow_heif...")
            
            # Méthode 1: Utiliser pillow_heif directement
            try:
                import pillow_heif
                
                # Lire le fichier HEIF
                heif_file = pillow_heif.read_heif(image_path)
                
                # Convertir en image PIL
                img = Image.frombytes(
                    heif_file.mode,
                    heif_file.size,
                    heif_file.data,
                    "raw",
                    heif_file.mode,
                    heif_file.stride
                )
                
                logger.info(f"📊 Image HEIC convertie: {img.size}, mode: {img.mode}")
                
                # Convertir en RGB si nécessaire
                if img.mode != 'RGB':
                    logger.info(f"🔄 Conversion {img.mode} -> RGB")
                    img = img.convert('RGB')
                
                # Redimensionner si trop grande
                max_size = 1600
                if max(img.size) > max_size:
                    logger.info(f"🔄 Redimensionnement de {img.size} vers max {max_size}px")
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Sauvegarder en JPEG temporaire
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    temp_path = temp_file.name
                
                logger.info(f"💾 Sauvegarde HEIC->JPEG: {temp_path}")
                img.save(temp_path, 'JPEG', quality=85, optimize=True)
                
                # Encoder en base64
                with open(temp_path, 'rb') as f:
                    image_data = f.read()
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                
                # Supprimer le fichier temporaire
                try:
                    os.remove(temp_path)
                    logger.info("🗑️ Fichier temporaire HEIC supprimé")
                except:
                    pass
                
                logger.info(f"✅ Conversion HEIC réussie: {len(base64_data)} caractères")
                return base64_data
                
            except Exception as e:
                logger.error(f"❌ Erreur méthode pillow_heif directe: {e}")
                
                # Méthode 2: Fallback avec PIL après enregistrement du plugin
                try:
                    import pillow_heif
                    pillow_heif.register_heif_opener()
                    
                    # Forcer le rechargement du plugin
                    from PIL import ImageFile
                    ImageFile.LOAD_TRUNCATED_IMAGES = True
                    
                    with Image.open(image_path) as img:
                        logger.info(f"📊 Image HEIC ouverte (fallback): {img.size}, mode: {img.mode}")
                        
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        max_size = 1600
                        if max(img.size) > max_size:
                            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                        
                        import tempfile
                        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                            temp_path = temp_file.name
                        
                        img.save(temp_path, 'JPEG', quality=85, optimize=True)
                        
                        with open(temp_path, 'rb') as f:
                            image_data = f.read()
                            base64_data = base64.b64encode(image_data).decode('utf-8')
                        
                        try:
                            os.remove(temp_path)
                        except:
                            pass
                        
                        logger.info(f"✅ Conversion HEIC réussie (fallback): {len(base64_data)} caractères")
                        return base64_data
                        
                except Exception as e2:
                    logger.error(f"❌ Erreur méthode fallback: {e2}")
                    
                    # Méthode 3: Conversion brute avec lecture directe des bytes
                    try:
                        logger.info("🔄 Tentative méthode 3: conversion brute...")
                        import pillow_heif
                        
                        # Ouvrir le fichier HEIF avec paramètres relaxés
                        heif_file = pillow_heif.open_heif(image_path, convert_hdr_to_8bit=True)
                        
                        # Obtenir la première image (principal)
                        if hasattr(heif_file, 'primary'):
                            primary_image = heif_file.primary
                        else:
                            primary_image = heif_file[0] if len(heif_file) > 0 else heif_file
                        
                        # Convertir en PIL Image avec numpy si nécessaire
                        import numpy as np
                        
                        # Obtenir les données brutes
                        if hasattr(primary_image, 'to_bytes'):
                            raw_data = primary_image.to_bytes()
                            width, height = primary_image.size
                            mode = primary_image.mode or 'RGB'
                        else:
                            # Fallback
                            raw_data = primary_image.data
                            width, height = primary_image.size
                            mode = primary_image.mode or 'RGB'
                        
                        # Créer l'image PIL
                        img = Image.frombytes(mode, (width, height), raw_data)
                        
                        logger.info(f"📊 Image HEIC convertie (méthode 3): {img.size}, mode: {img.mode}")
                        
                        # Convertir en RGB
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        # Redimensionner
                        max_size = 1600
                        if max(img.size) > max_size:
                            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                        
                        # Sauvegarder et encoder
                        import tempfile
                        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                            temp_path = temp_file.name
                        
                        img.save(temp_path, 'JPEG', quality=85, optimize=True)
                        
                        with open(temp_path, 'rb') as f:
                            image_data = f.read()
                            base64_data = base64.b64encode(image_data).decode('utf-8')
                        
                        try:
                            os.remove(temp_path)
                        except:
                            pass
                        
                        logger.info(f"✅ Conversion HEIC réussie (méthode 3): {len(base64_data)} caractères")
                        return base64_data
                        
                    except Exception as e3:
                        logger.error(f"❌ Erreur méthode 3: {e3}")
                        return None
                    
        except Exception as e:
            logger.error(f"❌ Erreur critique conversion HEIC: {e}")
            return None
    
    def _validate_and_enrich_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Valider et enrichir les données extraites"""
        # Valeurs par défaut
        validated_data = {
            'supplier': data.get('supplier', 'Inconnu'),
            'invoice_number': data.get('invoice_number'),
            'date': data.get('date'),
            'total_amount': data.get('total_amount', 0),
            'subtotal': data.get('subtotal', 0),
            'tax_amount': data.get('tax_amount', 0),
            'products': data.get('products', []),
            'confidence_score': data.get('confidence_score', 0.9),
            'analysis_timestamp': datetime.now().isoformat(),
            'analyzer': 'claude-vision'
        }
        
        # Nettoyer et valider les produits
        validated_products = []
        for product in validated_data['products']:
            if isinstance(product, dict) and product.get('name'):
                # Nettoyer le nom du produit
                clean_name = self._clean_product_name(product.get('name', ''))
                
                # Ignorer si le nom nettoyé est trop court ou invalide
                if len(clean_name) < 3 or self._is_invalid_product(clean_name):
                    continue
                
                validated_product = {
                    'name': clean_name,
                    'quantity': float(product.get('quantity', 1)),
                    'unit': product.get('unit', 'pièce'),
                    'unit_price': float(product.get('unit_price', 0)),
                    'total_price': float(product.get('total_price', 0)),
                    'code': product.get('code', '')
                }
                validated_products.append(validated_product)
        
        validated_data['products'] = validated_products
        
        # Calculer les totaux si manquants
        if not validated_data['subtotal'] and validated_products:
            validated_data['subtotal'] = sum(p['total_price'] for p in validated_products)
        
        if not validated_data['tax_amount'] and validated_data['total_amount'] and validated_data['subtotal']:
            validated_data['tax_amount'] = validated_data['total_amount'] - validated_data['subtotal']
        
        return validated_data
    
    def _clean_product_name(self, name: str) -> str:
        """Nettoyer le nom d'un produit"""
        import re
        
        # Supprimer les codes numériques au début
        name = re.sub(r'^\d+\s*', '', name)
        
        # Supprimer les mentions techniques communes
        technical_terms = [
            r'\d+/\d+', r'GR\s*X\s*\d+', r'BUREAU', r'SLOVAQUIE', r'ALLEMAGNE', 
            r'FRANCE', r'ROND', r'CARRE', r'BOUCHERE', r'SOUS\s*VIDE',
            r'FRAIS', r'SURGELE', r'KG', r'G\b', r'PCS?', r'PIECES?'
        ]
        
        for term in technical_terms:
            name = re.sub(term, '', name, flags=re.IGNORECASE)
        
        # Nettoyer les espaces multiples
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Capitaliser proprement
        return name.title()
    
    def _is_invalid_product(self, name: str) -> bool:
        """Vérifier si un nom de produit est invalide"""
        invalid_terms = [
            'tva', 'total', 'montant', 'ht', 'ttc', 'frais', 'livraison',
            'client', 'bureau', 'code', 'ref', 'numero', 'date', 'signature',
            'conditions', 'paiement', 'facture', 'bon', 'commande'
        ]
        
        name_lower = name.lower()
        
        # Vérifier les termes invalides
        for term in invalid_terms:
            if term in name_lower:
                return True
        
        # Vérifier si c'est juste des chiffres/codes
        if re.match(r'^[\d\s\-\.]+$', name):
            return True
        
        # Vérifier si c'est trop court
        if len(name.strip()) < 3:
            return True
        
        return False
    
    def _detect_supplier_from_image(self, image_base64: str) -> str:
        """Détecter le fournisseur depuis l'image"""
        try:
            # Prompt générique pour détecter n'importe quel fournisseur
            detection_message = {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": """Regarde attentivement cette facture et identifie le nom du fournisseur/entreprise.

Réponds UNIQUEMENT avec le nom exact du fournisseur tel qu'il apparaît sur la facture (par exemple: METRO, SYSCO, TRANSGOURMET, BRAKE, etc.).

Si tu ne vois pas clairement le nom, réponds "GENERIC"."""
                    }
                ]
            }
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=20,
                messages=[detection_message]
            )
            
            supplier = response.content[0].text.strip().upper()
            logger.info(f"🏪 Fournisseur brut détecté: {supplier}")
            
            # Normaliser les réponses
            if 'METRO' in supplier or 'MAKRO' in supplier:
                return 'METRO'
            elif 'TRANSGOURMET' in supplier:
                return 'TRANSGOURMET'
            elif 'BRAKE' in supplier:
                return 'BRAKE'
            elif 'PROMOCASH' in supplier:
                return 'PROMOCASH'
            elif 'SYSCO' in supplier:
                return 'SYSCO'
            elif 'MVA' in supplier:
                return 'MVA'
            else:
                return 'GENERIC'
                
        except Exception as e:
            logger.warning(f"Erreur détection fournisseur: {e}")
            return 'GENERIC'
    
    def test_api_connection(self) -> bool:
        """Tester la connexion à l'API Claude"""
        try:
            # Test simple avec un message texte
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Modèle moins cher pour le test
                max_tokens=10,
                messages=[{
                    "role": "user",
                    "content": "Bonjour"
                }]
            )
            return True
        except Exception as e:
            logger.error(f"Erreur test API Claude: {e}")
            return False 