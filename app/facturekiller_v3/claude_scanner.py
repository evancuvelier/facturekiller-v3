from modules.claude_vision import ClaudeVision

class ClaudeScanner:
    def __init__(self, price_manager):
        self.price_manager = price_manager
        try:
            self.claude_vision = ClaudeVision()
        except Exception as e:
            print(f"⚠️ Erreur initialisation Claude Vision: {e}")
            self.claude_vision = None
    
    def scan_facture(self, filepath):
        """Scanner une facture avec Claude Vision"""
        if self.claude_vision is None:
            return {
                'success': False,
                'error': 'Claude Vision non initialisé',
                'data': {
                    'supplier': 'Erreur init',
                    'products': []
                }
            }
        
        try:
            result = self.claude_vision.analyze_invoice_image(filepath)
            return result
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur Claude Scanner: {str(e)}',
                'data': {
                    'supplier': 'Erreur scan',
                    'products': []
                }
            }
    
    def scan_facture_multipage(self, page_paths):
        if not page_paths:
            return self.scan_facture(None)
        return self.scan_facture(page_paths[0])
    
    def get_pending_orders_for_supplier(self, supplier):
        return []