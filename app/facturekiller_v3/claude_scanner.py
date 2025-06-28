from modules.claude_vision import ClaudeVision

class ClaudeScanner:
    def __init__(self, price_manager):
        self.price_manager = price_manager
        self.claude_vision = ClaudeVision()
    
    def scan_facture(self, filepath):
        return self.claude_vision.analyze_invoice(filepath)
    
    def scan_facture_multipage(self, page_paths):
        return self.claude_vision.analyze_multi_page(page_paths)
    
    def get_pending_orders_for_supplier(self, supplier):
        return []  # À implémenter si nécessaire