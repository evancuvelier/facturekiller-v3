"""
Module OCR fallback pour quand Claude Vision n'est pas disponible
"""
import os
import pytesseract
from PIL import Image
from datetime import datetime
import re
from typing import Dict, Any, List

class OCRFallback:
    """Analyseur de factures basique avec OCR Tesseract"""
    
    def __init__(self):
        pass
    
    def analyze_invoice_image(self, image_path: str) -> Dict[str, Any]:
        """
        Analyser une facture avec OCR basique
        """
        try:
            if not os.path.exists(image_path):
                return {
                    'success': False,
                    'error': f'Fichier non trouvé: {image_path}'
                }
            
            # Extraire le texte avec OCR
            with Image.open(image_path) as img:
                # Convertir en RGB si nécessaire
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # OCR avec Tesseract
                text = pytesseract.image_to_string(img, lang='fra')
                
            # Analyse basique du texte
            analysis_data = self._parse_invoice_text(text)
            
            return {
                'success': True,
                'data': analysis_data,
                'raw_text': text[:500]  # Premiers 500 caractères
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur OCR: {str(e)}',
                'data': {
                    'supplier': 'Erreur OCR',
                    'products': []
                }
            }
    
    def _parse_invoice_text(self, text: str) -> Dict[str, Any]:
        """Parser basique du texte OCR"""
        
        # Détecter le fournisseur
        supplier = self._detect_supplier(text)
        
        # Extraire les informations de base
        lines = text.split('\n')
        
        # Structure de données basique
        data = {
            'supplier': supplier,
            'invoice_number': self._extract_invoice_number(text),
            'date': self._extract_date(text),
            'total_amount': self._extract_total(text),
            'products': self._extract_products_basic(lines),
            'confidence_score': 0.7,  # Score basique
            'analysis_timestamp': datetime.now().isoformat(),
            'analyzer': 'ocr-fallback'
        }
        
        return data
    
    def _detect_supplier(self, text: str) -> str:
        """Détecter le fournisseur dans le texte"""
        text_upper = text.upper()
        
        if 'METRO' in text_upper or 'MAKRO' in text_upper:
            return 'METRO'
        elif 'TRANSGOURMET' in text_upper:
            return 'TRANSGOURMET'
        elif 'BRAKE' in text_upper:
            return 'BRAKE'
        elif 'PROMOCASH' in text_upper:
            return 'PROMOCASH'
        else:
            return 'Détection automatique'
    
    def _extract_invoice_number(self, text: str) -> str:
        """Extraire le numéro de facture"""
        patterns = [
            r'N[°\s]*(\d+)',
            r'FACTURE[:\s]*(\d+)',
            r'BON[:\s]*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return 'N/A'
    
    def _extract_date(self, text: str) -> str:
        """Extraire la date"""
        patterns = [
            r'(\d{2}[/\-\.]\d{2}[/\-\.]\d{4})',
            r'(\d{4}[/\-\.]\d{2}[/\-\.]\d{2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_total(self, text: str) -> float:
        """Extraire le montant total"""
        patterns = [
            r'TOTAL[:\s]*(\d+[,\.]\d{2})',
            r'TTC[:\s]*(\d+[,\.]\d{2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '.')
                try:
                    return float(amount_str)
                except:
                    continue
        
        return 0.0
    
    def _extract_products_basic(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Extraction basique des produits"""
        products = []
        
        for line in lines:
            line = line.strip()
            if len(line) < 5:  # Ignorer les lignes trop courtes
                continue
                
            # Rechercher des patterns de prix
            price_match = re.search(r'(\d+[,\.]\d{2})', line)
            if price_match and self._looks_like_product_line(line):
                
                # Nettoyer le nom du produit
                product_name = self._clean_product_name(line)
                if product_name and len(product_name) > 3:
                    
                    price = float(price_match.group(1).replace(',', '.'))
                    
                    products.append({
                        'name': product_name,
                        'quantity': 1,
                        'unit': 'pièce',
                        'unit_price': price,
                        'total_price': price,
                        'code': ''
                    })
        
        return products[:20]  # Limiter à 20 produits
    
    def _looks_like_product_line(self, line: str) -> bool:
        """Vérifier si une ligne ressemble à un produit"""
        # Ignorer les lignes avec des mots-clés non-produits
        exclude_keywords = [
            'total', 'tva', 'ht', 'ttc', 'facture', 'client',
            'adresse', 'tel', 'fax', 'email', 'siret'
        ]
        
        line_lower = line.lower()
        return not any(keyword in line_lower for keyword in exclude_keywords)
    
    def _clean_product_name(self, line: str) -> str:
        """Nettoyer le nom du produit"""
        # Supprimer les prix et codes
        line = re.sub(r'\d+[,\.]\d{2}', '', line)  # Prix
        line = re.sub(r'^\d+\s*', '', line)  # Codes au début
        line = re.sub(r'\s+', ' ', line)  # Espaces multiples
        
        return line.strip()[:50]  # Limiter à 50 caractères 