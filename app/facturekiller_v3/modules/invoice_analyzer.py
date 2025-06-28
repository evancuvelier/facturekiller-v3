"""
Module d'analyse intelligente des factures
Extraction des données structurées et détection des fournisseurs
"""

import re
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
# from modules.ai_agent import IntelligentAIAgent  # Removed to fix circular import

logger = logging.getLogger(__name__)

class InvoiceAnalyzer:
    """Analyseur intelligent de factures avec templates par fournisseur"""
    
    def __init__(self):
        self.supplier_templates = self._load_supplier_templates()
        self.invoices_db = []  # Base de données en mémoire (à remplacer par une vraie DB)
        # self.ai_agent = IntelligentAIAgent()  # Removed to fix circular import
        
    def _load_supplier_templates(self) -> Dict[str, Dict]:
        """Charger les templates de fournisseurs"""
        templates_path = 'config/supplier_templates.json'
        if os.path.exists(templates_path):
            with open(templates_path, 'r') as f:
                return json.load(f)
        
        # Templates par défaut
        return {
            'METRO': {
                'patterns': {
                    'name': [r'METRO', r'Metro Cash'],
                    'invoice_number': [r'Facture\s*[Nn]°?\s*([A-Z0-9\-]+)', r'N°\s*([A-Z0-9\-]+)'],
                    'date': [r'(\d{2}[/\-]\d{2}[/\-]\d{4})', r'Date:\s*(\d{2}[/\-]\d{2}[/\-]\d{4})'],
                    'total': [r'TOTAL\s*TTC\s*([0-9]+[,\.]\d{2})', r'Total\s*:\s*([0-9]+[,\.]\d{2})'],
                    'products': [r'([A-Za-z][A-Za-z\s]+)\s+(\d+)\s*([A-Za-z]+)\s+([0-9]+[,\.]\d{2})']
                },
                'confidence_boost': 0.1
            },
            'TRANSGOURMET': {
                'patterns': {
                    'name': [r'TRANSGOURMET', r'Transgourmet'],
                    'invoice_number': [r'Facture\s*:\s*([0-9]+)', r'N°\s*facture\s*:\s*([0-9]+)'],
                    'date': [r'Date\s*:\s*(\d{2}[/\-]\d{2}[/\-]\d{4})'],
                    'total': [r'Montant\s*TTC\s*:\s*([0-9]+[,\.]\d{2})'],
                    'products': [r'(.+?)\s+(\d+[,\.]\d{3})\s*([A-Z]+)\s+([0-9]+[,\.]\d{2})']
                },
                'confidence_boost': 0.1
            },
            'GENERIC': {
                'patterns': {
                    'name': [],
                    'invoice_number': [r'[FfNn]°?\s*(?:facture|invoice)?\s*:?\s*([A-Z0-9\-]+)'],
                    'date': [r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})'],
                    'total': [r'(?:TOTAL|Total|Montant)\s*(?:TTC)?\s*:?\s*([0-9]+[,\.]\d{2})'],
                    'products': [r'([A-Za-z][A-Za-z\s]+)\s+([0-9]+[,\.]\d{2})']
                },
                'confidence_boost': 0.0
            }
        }
    
    def get_supported_suppliers(self) -> List[str]:
        """Obtenir la liste des fournisseurs supportés"""
        return [s for s in self.supplier_templates.keys() if s != 'GENERIC']
    
    def analyze(self, text: str, structured_data: Optional[Dict] = None, ocr_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Analyser une facture et extraire les informations structurées
        
        Args:
            text: Texte extrait par OCR
            structured_data: Données structurées optionnelles de l'OCR
            ocr_data: Données OCR complètes 
            
        Returns:
            Dict avec toutes les informations extraites
        """
        if not text and not ocr_data:
            return {
                'success': False,
                'error': 'Aucun texte à analyser',
                'data': {}
            }
        
        # Analyse classique
        # Détecter le fournisseur
        supplier = self._detect_supplier(text)
        template = self.supplier_templates.get(supplier, self.supplier_templates['GENERIC'])
        
        # Extraire les informations
        extracted_data = {
            'supplier': supplier,
            'invoice_number': self._extract_invoice_number(text, template),
            'date': self._extract_date(text, template),
            'total_amount': self._extract_total(text, template),
            'products': self._extract_products(text, template),
            'raw_text': text[:500],  # Garder un aperçu du texte brut
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        # Calculer le score de confiance
        confidence = self._calculate_confidence(extracted_data)
        if supplier != 'GENERIC':
            confidence += template['confidence_boost']
        
        extracted_data['confidence_score'] = min(confidence, 1.0)
        
        # Améliorer avec les données structurées si disponibles
        if structured_data:
            extracted_data = self._enhance_with_structured_data(extracted_data, structured_data)
        
        return {
            'success': True,
            'data': extracted_data
        }
    
    def _analyze_simple(self, text: str) -> Dict[str, Any]:
        """Analyse simple d'une facture"""
        # Détecter le fournisseur
        supplier = self._detect_supplier(text)
        template = self.supplier_templates.get(supplier, self.supplier_templates['GENERIC'])
        
        # Extraire les informations
        extracted_data = {
            'supplier': supplier,
            'invoice_number': self._extract_invoice_number(text, template),
            'date': self._extract_date(text, template),
            'total_amount': self._extract_total(text, template),
            'products': self._extract_products(text, template),
            'raw_text': text[:500],
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        # Calculer le score de confiance
        confidence = self._calculate_confidence(extracted_data)
        if supplier != 'GENERIC':
            confidence += template['confidence_boost']
        
        extracted_data['confidence_score'] = min(confidence, 1.0)
        
        return {
            'success': True,
            'data': extracted_data
        }
    
    def _detect_supplier(self, text: str) -> str:
        """Détecter le fournisseur dans le texte"""
        text_upper = text.upper()
        
        for supplier, template in self.supplier_templates.items():
            if supplier == 'GENERIC':
                continue
                
            for pattern in template['patterns']['name']:
                if re.search(pattern, text, re.IGNORECASE):
                    logger.info(f"Fournisseur détecté: {supplier}")
                    return supplier
        
        # Recherche additionnelle par mots-clés
        supplier_keywords = {
            'METRO': ['metro', 'cash & carry'],
            'TRANSGOURMET': ['transgourmet', 'tg ', 'trans gourmet'],
            'BRAKE': ['brake', 'brake france'],
            'PROMOCASH': ['promocash', 'promo cash'],
            'MAKRO': ['makro']
        }
        
        for supplier, keywords in supplier_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_upper.lower():
                    logger.info(f"Fournisseur détecté par mot-clé: {supplier}")
                    return supplier
        
        logger.info("Aucun fournisseur spécifique détecté")
        return 'GENERIC'
    
    def _extract_invoice_number(self, text: str, template: Dict) -> Optional[str]:
        """Extraire le numéro de facture"""
        for pattern in template['patterns']['invoice_number']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_date(self, text: str, template: Dict) -> Optional[str]:
        """Extraire la date de la facture"""
        for pattern in template['patterns']['date']:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                # Normaliser le format de date
                try:
                    # Essayer différents formats
                    for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y']:
                        try:
                            date_obj = datetime.strptime(date_str, fmt)
                            return date_obj.strftime('%Y-%m-%d')
                        except:
                            continue
                except:
                    pass
                return date_str
        return None
    
    def _extract_total(self, text: str, template: Dict) -> Optional[float]:
        """Extraire le montant total"""
        amounts = []
        
        # Chercher d'abord les patterns spécifiques
        for pattern in template['patterns']['total']:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                try:
                    # Gérer le format européen (1.234,56) et US (1,234.56)
                    amount_str = match
                    
                    # Si le format est européen (virgule pour décimales)
                    if ',' in amount_str and '.' in amount_str:
                        # Format européen: 1.234,56
                        amount_str = amount_str.replace('.', '').replace(',', '.')
                    elif ',' in amount_str and amount_str.count(',') == 1:
                        # Virgule unique = décimale
                        amount_str = amount_str.replace(',', '.')
                    
                    amount = float(amount_str)
                    if amount > 0:
                        amounts.append(amount)
                except:
                    pass
        
        # Recherche additionnelle pour les gros montants en fin de document
        # Pattern pour capturer des montants comme 2.402,04
        big_amounts_pattern = r'([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2})\s*(?:€|EUR|Euros?)?'
        big_matches = re.findall(big_amounts_pattern, text)
        
        for match in big_matches:
            try:
                amount_str = match.replace('.', '').replace(',', '.')
                amount = float(amount_str)
                if amount > 100:  # Probablement un total si > 100€
                    amounts.append(amount)
            except:
                pass
        
        # Retourner le montant le plus élevé (probablement le total TTC)
        if amounts:
            # Privilégier les montants > 1000 qui sont souvent les totaux
            big_amounts = [a for a in amounts if a > 1000]
            return max(big_amounts) if big_amounts else max(amounts)
        
        return None
    
    def _extract_products(self, text: str, template: Dict) -> List[Dict]:
        """Extraire la liste des produits"""
        products = []
        seen_products = set()
        
        # Pour METRO, chercher spécifiquement les lignes de produits
        if 'METRO' in template.get('patterns', {}).get('name', []):
            # Pattern pour les lignes METRO: Code | Description | QTÉ | PU | Total
            metro_pattern = r'([A-Z0-9.]+)\s+(.+?)\s+(\d+[,.]?\d*)\s+(\d+[,.]?\d*)\s+(\d+[,.]?\d*)'
            lines = text.split('\n')
            
            for line in lines:
                # Ignorer les lignes de TVA et totaux
                if any(skip in line.upper() for skip in ['TVA', 'TOTAL', 'TAXES', 'MONTANT', 'HT', 'TTC']):
                    continue
                    
                match = re.search(metro_pattern, line)
                if match:
                    try:
                        code = match.group(1)
                        desc = match.group(2).strip()
                        qty = float(match.group(3).replace(',', '.'))
                        unit_price = float(match.group(4).replace(',', '.'))
                        total = float(match.group(5).replace(',', '.'))
                        
                        # Vérifier que ce sont des valeurs raisonnables
                        if total > 0 and len(desc) > 2:
                            products.append({
                                'code': code,
                                'name': desc.title(),
                                'quantity': qty,
                                'unit': 'unité',
                                'unit_price': unit_price,
                                'total_price': total
                            })
                    except:
                        pass
        
        # Patterns génériques si pas assez de produits trouvés
        if len(products) < 3:
            for pattern in template['patterns']['products']:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                
                for match in matches:
                    try:
                        if len(match) >= 2:
                            name = match[0].strip() if isinstance(match, tuple) else match
                            
                            # Nettoyer le nom
                            name = re.sub(r'\s+', ' ', name)
                            name = name.title()
                            
                            # Éviter les doublons et noms trop courts
                            if name in seen_products or len(name) < 3:
                                continue
                            
                            # Extraire le prix
                            price_str = match[-1] if isinstance(match, tuple) else '0'
                            
                            # Gérer format européen
                            if ',' in price_str:
                                price_str = price_str.replace('.', '').replace(',', '.')
                            
                            price = float(price_str)
                            
                            if price > 0:
                                # Extraire la quantité et l'unité si disponibles
                                quantity = 1
                                unit = 'pièce'
                                
                                if len(match) >= 3:
                                    try:
                                        qty_str = match[1] if isinstance(match, tuple) else '1'
                                        quantity = float(qty_str.replace(',', '.'))
                                        
                                        if len(match) >= 4:
                                            unit = match[2].lower() if isinstance(match, tuple) else 'pièce'
                                    except:
                                        pass
                                
                                products.append({
                                    'name': name,
                                    'quantity': quantity,
                                    'unit': unit,
                                    'unit_price': round(price / quantity, 2),
                                    'total_price': price
                                })
                                
                                seen_products.add(name)
                            
                    except Exception as e:
                        logger.debug(f"Erreur extraction produit: {e}")
                        continue
        
        return products[:30]  # Limiter à 30 produits max
    
    def _calculate_confidence(self, data: Dict) -> float:
        """Calculer le score de confiance de l'analyse"""
        score = 0.0
        
        # Points par élément trouvé
        if data.get('supplier') != 'GENERIC':
            score += 0.2
        if data.get('invoice_number'):
            score += 0.2
        if data.get('date'):
            score += 0.2
        if data.get('total_amount'):
            score += 0.2
        if len(data.get('products', [])) > 0:
            score += 0.2
        
        # Bonus si beaucoup de produits trouvés
        product_count = len(data.get('products', []))
        if product_count > 5:
            score += 0.1
        if product_count > 10:
            score += 0.1
        
        return min(score, 1.0)
    
    def _enhance_with_structured_data(self, data: Dict, structured_data: Dict) -> Dict:
        """Améliorer les données avec les informations structurées de l'OCR"""
        # TODO: Utiliser les données structurées pour améliorer l'extraction
        return data
    
    def save_invoice(self, analysis: Dict, file_path: str, restaurant_id: str = None, restaurant_name: str = None) -> str:
        """Sauvegarder une facture analysée avec contexte restaurant"""
        invoice_id = str(len(self.invoices_db) + 1).zfill(6)
        
        invoice_record = {
            'id': invoice_id,
            'file_path': file_path,
            'analysis': analysis['data'] if 'data' in analysis else analysis,
            'created_at': datetime.now().isoformat(),
            'restaurant_id': restaurant_id,
            'restaurant_name': restaurant_name
        }
        
        self.invoices_db.append(invoice_record)
        
        # Sauvegarder dans un fichier JSON (à remplacer par une vraie DB)
        os.makedirs('data', exist_ok=True)
        with open('data/invoices.json', 'w') as f:
            json.dump(self.invoices_db, f, indent=2, ensure_ascii=False)
        
        return invoice_id
    
    def get_all_invoices(self, page: int = 1, per_page: int = 20,
                        supplier: str = '', date_from: str = '', 
                        date_to: str = '', restaurant_suppliers: List[str] = None) -> Dict[str, Any]:
        """Récupérer toutes les factures avec pagination et filtres INCLUANT RESTAURANT"""
        # Charger depuis le fichier si nécessaire
        if not self.invoices_db and os.path.exists('data/invoices.json'):
            with open('data/invoices.json', 'r') as f:
                self.invoices_db = json.load(f)
        
        # Appliquer les filtres
        filtered_invoices = []
        
        for invoice in self.invoices_db:
            # NOUVEAU FILTRE: Par fournisseurs du restaurant
            if restaurant_suppliers:
                invoice_supplier = invoice.get('analysis', {}).get('supplier', '')
                if invoice_supplier and invoice_supplier not in restaurant_suppliers:
                    continue  # Ignorer les factures de fournisseurs non autorisés
            
            # Filtre par fournisseur
            if supplier:
                invoice_supplier = invoice.get('analysis', {}).get('supplier', '')
                if invoice_supplier != supplier:
                    continue
            
            # Filtre par date
            if date_from or date_to:
                invoice_date = invoice.get('analysis', {}).get('date', '')
                if not invoice_date:
                    invoice_date = invoice.get('created_at', '')
                
                if invoice_date:
                    try:
                        # Convertir en date pour comparaison
                        inv_date = datetime.fromisoformat(invoice_date.replace('Z', '+00:00')).date()
                        
                        if date_from:
                            from_date = datetime.fromisoformat(date_from).date()
                            if inv_date < from_date:
                                continue
                        
                        if date_to:
                            to_date = datetime.fromisoformat(date_to).date()
                            if inv_date > to_date:
                                continue
                    except:
                        continue
            
            filtered_invoices.append(invoice)
        
        # Trier par date décroissante
        filtered_invoices.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Calculer la pagination
        total = len(filtered_invoices)
        total_pages = (total + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        # Extraire la page
        page_items = filtered_invoices[start_idx:end_idx]
        
        return {
            'items': page_items,
            'total': total,
            'page': page,
            'pages': total_pages,
            'per_page': per_page,
            'restaurant_filter': restaurant_suppliers
        }
    
    def get_invoice(self, invoice_id: str) -> Optional[Dict]:
        """Récupérer une facture par son ID"""
        for invoice in self.get_all_invoices():
            if invoice['id'] == invoice_id:
                return invoice
        return None
    
    def get_invoices_by_restaurant(self, restaurant_id: str) -> List[Dict[str, Any]]:
        """Récupérer les factures d'un restaurant spécifique"""
        try:
            # Charger depuis le fichier si nécessaire
            if not self.invoices_db and os.path.exists('data/invoices.json'):
                with open('data/invoices.json', 'r') as f:
                    self.invoices_db = json.load(f)
            
            # Filtrer les factures par restaurant_id
            restaurant_invoices = [
                invoice for invoice in self.invoices_db
                if invoice.get('restaurant_id') == restaurant_id
            ]
            
            # Trier par date de création décroissante
            restaurant_invoices.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return restaurant_invoices
            
        except Exception as e:
            logger.error(f"Erreur récupération factures restaurant {restaurant_id}: {e}")
            return [] 