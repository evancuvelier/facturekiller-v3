// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔍 Initialisation Scanner Validation...');
    
    // Vérifier si on a un order_id dans l'URL
    const urlParams = new URLSearchParams(window.location.search);
    const orderId = urlParams.get('order_id');
    
    if (orderId) {
        console.log(`📦 Order ID détecté: ${orderId}`);
        // Passer directement à l'étape 2 avec la commande pré-sélectionnée
        preSelectOrder(orderId);
    } else {
        // Workflow normal
        showStep(1);
    }
    
    setupEventListeners();
    setupDropZone();
});

// Pré-sélectionner une commande
async function preSelectOrder(orderId) {
    try {
        console.log(`🔍 Pré-sélection commande: ${orderId}`);
        
        // Charger la commande
        const response = await fetch(`/api/orders/${orderId}`);
        const result = await response.json();
        
        if (result.success) {
            selectedOrder = result.data;
            
            // Passer à l'étape 2 directement
            showStep(2);
            
            // Afficher les infos de la commande
            document.getElementById('selectedOrderInfo').innerHTML = `
                <div class="alert alert-info">
                    <h6><i class="bi bi-info-circle me-2"></i>Commande pré-sélectionnée</h6>
                    <p class="mb-0">
                        <strong>${selectedOrder.order_number}</strong> - ${selectedOrder.supplier}<br>
                        <small class="text-muted">
                            ${selectedOrder.products?.length || 0} produits • 
                            ${formatPrice(selectedOrder.total_amount || 0)} • 
                            Livraison: ${formatDate(selectedOrder.delivery_date)}
                        </small>
                    </p>
                </div>
            `;
            
            showNotification('Commande pré-sélectionnée - Vous pouvez maintenant scanner la facture', 'info');
        } else {
            console.error('❌ Commande non trouvée:', result.error);
            showNotification('Commande non trouvée', 'error');
            showStep(1); // Retour au workflow normal
        }
    } catch (error) {
        console.error('❌ Erreur pré-sélection:', error);
        showNotification('Erreur lors de la pré-sélection', 'error');
        showStep(1); // Retour au workflow normal
    }
} 