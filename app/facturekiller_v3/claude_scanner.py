from modules.claude_vision import ClaudeVision

class ClaudeScanner:
    def __init__(self, price_manager):
        self.price_manager = price_manager
        self.claude_vision = None
        
        try:
            print("🔄 Initialisation de Claude Vision...")
            self.claude_vision = ClaudeVision()
            
            # Vérifier que l'initialisation a réussi
            if hasattr(self.claude_vision, 'client') and self.claude_vision.client is not None:
                print("✅ Claude Vision initialisé avec succès")
            else:
                print("❌ Claude Vision mal initialisé")
                self.claude_vision = None
                
        except ImportError as e:
            print(f"❌ Erreur import Claude Vision: {e}")
            self.claude_vision = None
        except Exception as e:
            print(f"❌ Erreur générale initialisation Claude Vision: {e}")
            self.claude_vision = None
    
    def scan_facture(self, filepath):
        """Scanner une facture avec Claude Vision"""
        if self.claude_vision is None:
            return {
                'success': False,
                'error': 'Claude Vision non disponible - vérifiez la clé API ANTHROPIC_API_KEY',
                'data': {
                    'supplier': 'Configuration requise',
                    'invoice_number': 'N/A',
                    'date': None,
                    'total_amount': 0.0,
                    'products': [],
                    'analysis_method': 'error-no-claude'
                }
            }
        
        try:
            print(f"🔍 Analyse de la facture: {filepath}")
            result = self.claude_vision.analyze_invoice_image(filepath)
            return result
        except Exception as e:
            print(f"❌ Erreur scan facture: {e}")
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