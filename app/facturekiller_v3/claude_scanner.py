from modules.claude_vision import ClaudeVision

class ClaudeScanner:
    def __init__(self, price_manager):
        self.price_manager = price_manager
        self.claude_vision = ClaudeVision()
    
    def scan_facture(self, filepath):
        """Scanner une facture - version temporaire sans Claude Vision"""
        try:
            # Tentative d'analyse avec Claude Vision
            result = self.claude_vision.analyze_invoice_image(filepath)
            
            if not result.get('success', False):
                # Fallback vers une structure de données de base
                return {
                    'success': True,
                    'message': 'Analyse manuelle requise - Claude Vision non disponible',
                    'data': {
                        'supplier': 'Analyse manuelle requise',
                        'invoice_number': 'N/A',
                        'date': None,
                        'total_amount': 0.0,
                        'products': [],
                        'analysis_method': 'fallback-manual'
                    }
                }
            
            return result
            
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