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
import pillow_heif

# Enregistrer le support HEIF
pillow_heif.register_heif_opener()

logger = logging.getLogger(__name__)

class ClaudeVision:
    """Analyseur de factures avec Claude Vision"""
    
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.getenv('ANTHROPIC_API_KEY')
        )
        self.model = "claude-3-opus-20240229"  # Claude 3 Opus avec vision
        
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

STRUCTURE JSON ATTENDUE:
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

Réponds UNIQUEMENT avec le JSON, pas d'autre texte.""",

            'TRANSGOURMET': """Tu es un expert en analyse de factures TRANSGOURMET.
Analyse cette facture et extrait UNIQUEMENT les produits alimentaires réels.

RÈGLES STRICTES TRANSGOURMET:
- IGNORE les codes produits numériques
- GARDE le nom alimentaire principal
- IGNORE les mentions techniques de conditionnement
- Focus sur: viandes, poissons, légumes, épicerie, produits laitiers

Réponds UNIQUEMENT avec le JSON de structure identique.""",

            'GENERIC': """Tu es un expert en analyse de factures alimentaires.
Analyse cette facture et extrait UNIQUEMENT les produits alimentaires réels.

RÈGLES STRICTES:
- IGNORE tous les codes techniques, références, numéros
- GARDE SEULEMENT les noms de produits alimentaires
- Simplifie les noms (ex: "FILET DE BOEUF 1KG SOUS VIDE" → "Filet de bœuf")
- IGNORE: TVA, totaux, frais, codes client, mentions techniques

Réponds UNIQUEMENT avec le JSON."""
        }
    
    def analyze_invoice_image(self, image_path: str) -> Dict[str, Any]:
        """
        Analyser une image de facture avec Claude Vision
        """
        try:
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
                        "text": f"Analyse cette facture {supplier} et extrait les produits alimentaires selon les règles spécifiques."
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
            logger.info(f"📝 Réponse Claude: {response_text[:200]}...")
            
            # Parser le JSON
            try:
                # Nettoyer la réponse
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                
                analysis_data = json.loads(response_text.strip())
                
                # Valider et enrichir les données
                analysis_data = self._validate_and_enrich_data(analysis_data)
                
                return {
                    'success': True,
                    'data': analysis_data,
                    'raw_response': response_text
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Erreur parsing JSON: {e}")
                return {
                    'success': False,
                    'error': f'Réponse JSON invalide: {str(e)}',
                    'raw_response': response_text
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
            # Ouvrir l'image avec PIL (support HEIC)
            with Image.open(image_path) as img:
                # Convertir en RGB si nécessaire
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Redimensionner si trop grande (max 1600px)
                max_size = 1600
                if max(img.size) > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Sauvegarder temporairement en JPEG
                temp_path = image_path + "_temp.jpg"
                img.save(temp_path, 'JPEG', quality=85)
                
                # Lire et encoder en base64
                with open(temp_path, 'rb') as f:
                    image_data = f.read()
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                
                # Supprimer le fichier temporaire
                os.remove(temp_path)
                
                return base64_data
                
        except Exception as e:
            logger.error(f"Erreur conversion image: {e}")
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
            # Prompt simple pour détecter le fournisseur
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
                        "text": "Quel est le fournisseur de cette facture ? Réponds par un seul mot: METRO, TRANSGOURMET, BRAKE, PROMOCASH, MAKRO ou AUTRE"
                    }
                ]
            }
            
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",  # Modèle plus rapide pour la détection
                max_tokens=10,
                messages=[detection_message]
            )
            
            supplier = response.content[0].text.strip().upper()
            
            # Normaliser les réponses
            if 'METRO' in supplier or 'MAKRO' in supplier:
                return 'METRO'
            elif 'TRANSGOURMET' in supplier:
                return 'TRANSGOURMET'
            elif 'BRAKE' in supplier:
                return 'BRAKE'
            elif 'PROMOCASH' in supplier:
                return 'PROMOCASH'
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
                model="claude-3-haiku-20240307",  # Modèle moins cher pour le test
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