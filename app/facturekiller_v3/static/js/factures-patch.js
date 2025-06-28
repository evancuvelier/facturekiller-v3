// Patch pour corriger l'erreur forEach sur les anomalies
console.log('🔧 Patch factures chargé');

document.addEventListener('DOMContentLoaded', function() {
    // Override de la fonction showInvoiceModal originale
    if (typeof showInvoiceModal !== 'undefined') {
        const originalShowInvoiceModal = showInvoiceModal;
        
        window.showInvoiceModal = function(invoice) {
            console.log('📋 Affichage facture patchée:', invoice.id);
            
            try {
                const analysis = invoice.analysis || {};
                
                // Remplir les informations de base
                const detailInvoiceNumber = document.getElementById('detailInvoiceNumber');
                const detailSupplier = document.getElementById('detailSupplier');
                const detailDate = document.getElementById('detailDate');
                const detailTotal = document.getElementById('detailTotal');
                
                if (detailInvoiceNumber) detailInvoiceNumber.textContent = analysis.invoice_number || invoice.id;
                if (detailSupplier) detailSupplier.textContent = analysis.supplier || 'Inconnu';
                if (detailDate) detailDate.textContent = formatDate(analysis.date || invoice.created_at);
                if (detailTotal) detailTotal.textContent = formatPrice(analysis.total_amount || 0);
                
                // Gestion des anomalies CORRIGÉE
                const anomaliesSection = document.getElementById('anomaliesSection');
                const detailAnomalies = document.getElementById('detailAnomalies');
                
                if (invoice.has_anomalies && invoice.anomalies) {
                    console.log('🔍 Anomalies trouvées:', invoice.anomalies);
                    
                    if (anomaliesSection) anomaliesSection.style.display = 'block';
                    
                    if (detailAnomalies) {
                        let anomaliesHtml = '';
                        
                        try {
                            // Vérifier le type et la structure des anomalies
                            if (Array.isArray(invoice.anomalies)) {
                                invoice.anomalies.forEach(anomaly => {
                                    if (!anomaly) return;
                                    
                                    anomaliesHtml += `
                                        <div class="alert alert-warning mb-2">
                                            <h6 class="alert-heading">
                                                <i class="bi bi-exclamation-triangle"></i> 
                                                ${anomaly.product || anomaly.type || 'Anomalie'}
                                            </h6>
                                            <div class="mt-2">
                                                <strong>${anomaly.description || anomaly.message || 'Détails non disponibles'}</strong>
                                            </div>
                                        </div>
                                    `;
                                });
                            } else {
                                anomaliesHtml = `
                                    <div class="alert alert-warning mb-2">
                                        <h6 class="alert-heading">
                                            <i class="bi bi-exclamation-triangle"></i> Anomalie
                                        </h6>
                                        <div class="mt-2">
                                            <strong>Format d'anomalie non standard</strong>
                                        </div>
                                    </div>
                                `;
                            }
                        } catch (error) {
                            console.error('Erreur affichage anomalies:', error);
                            anomaliesHtml = `
                                <div class="alert alert-danger">
                                    <strong>Erreur d'affichage des anomalies</strong>
                                </div>
                            `;
                        }
                        
                        detailAnomalies.innerHTML = anomaliesHtml;
                    }
                } else {
                    if (anomaliesSection) anomaliesSection.style.display = 'none';
                }
                
                // Afficher les produits
                const productsTableBody = document.querySelector('#detailProductsTable tbody');
                if (productsTableBody) {
                    const products = analysis.products || [];
                    
                    if (products.length === 0) {
                        productsTableBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Aucun produit détecté</td></tr>';
                    } else {
                        productsTableBody.innerHTML = products.map(product => `
                            <tr>
                                <td><strong>${product.name || 'Produit'}</strong></td>
                                <td>${product.quantity || 1}</td>
                                <td class="fw-bold">${formatPrice(product.unit_price || 0)}</td>
                                <td class="fw-bold">${formatPrice((product.unit_price || 0) * (product.quantity || 1))}</td>
                                <td><span class="badge bg-info">Nouveau</span></td>
                            </tr>
                        `).join('');
                    }
                }
                
                // Afficher le modal avec correction
                const modalElement = document.getElementById('invoiceDetailModal');
                if (modalElement && typeof bootstrap !== 'undefined') {
                    try {
                        const modal = new bootstrap.Modal(modalElement);
                        modal.show();
                        console.log('✅ Modal affichée avec succès');
                    } catch (error) {
                        console.error('Erreur modal:', error);
                        showNotification('Erreur lors de l\'affichage', 'error');
                    }
                }
                
            } catch (error) {
                console.error('Erreur générale showInvoiceModal:', error);
                showNotification('Erreur lors de l\'affichage de la facture', 'error');
            }
        };
        
        console.log('🔧 Patch showInvoiceModal appliqué');
    }
});
