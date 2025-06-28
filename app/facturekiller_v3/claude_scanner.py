from modules.claude_vision import ClaudeVision
from modules.ocr_fallback import OCRFallback

class ClaudeScanner:
    def __init__(self, price_manager):
        self.price_manager = price_manager
        self.claude_vision = ClaudeVision()
        self.ocr_fallback = OCRFallback()
    
    def scan_facture(self, filepath):
        """Scanner une facture avec fallback OCR"""
        try:
            # Tentative d'analyse avec Claude Vision
            result = self.claude_vision.analyze_invoice_image(filepath)
            
            if result.get('success', False):
                return result
            
            # Si Claude Vision échoue, utiliser OCR fallback
            print("🔄 Claude Vision indisponible, utilisation de l'OCR fallback...")
            fallback_result = self.ocr_fallback.analyze_invoice_image(filepath)
            
            if fallback_result.get('success', False):
                fallback_result['message'] = 'Analysé avec OCR fallback (Claude Vision indisponible)'
                return fallback_result
            
            # Si tout échoue, retour structure minimale
            return {
                'success': True,
                'message': 'Analyse manuelle requise - Scanner automatique indisponible',
                'data': {
                    'supplier': 'Analyse manuelle requise',
                    'invoice_number': 'N/A',
                    'date': None,
                    'total_amount': 0.0,
                    'products': [],
                    'analysis_method': 'manual-required'
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur lors du scan: {str(e)}',
                'data': {
                    'supplier': 'Erreur',
                    'products': []
                }
            }
    
    def scan_facture_multipage(self, page_paths):
        """Scanner une facture multi-pages"""
        if not page_paths:
            return self.scan_facture(None)
        
        # Pour l'instant, scanner seulement la première page
        return self.scan_facture(page_paths[0])
    
    def get_pending_orders_for_supplier(self, supplier):
        return []  # À implémenter si nécessaire