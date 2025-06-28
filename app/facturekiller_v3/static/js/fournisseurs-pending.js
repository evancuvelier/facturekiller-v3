// Gestion des produits en attente - Extension fournisseurs.js
// FactureKiller V3

// ===== FONCTIONS POUR GÉRER LES PRODUITS EN ATTENTE =====

// Valider un produit en attente
async function validatePendingProduct(supplierName, pendingId) {
    try {
        const response = await fetch(`/api/suppliers/${encodeURIComponent(supplierName)}/pending-products/${pendingId}/validate`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification(result.message, 'success');
            // Recharger les données
            loadSuppliers();
        } else {
            showNotification('Erreur lors de la validation: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('❌ Erreur validation produit en attente:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

// Rejeter un produit en attente
async function rejectPendingProduct(supplierName, pendingId) {
    if (!confirm('Êtes-vous sûr de vouloir rejeter ce produit ?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/prices/pending/${pendingId}/reject`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Produit rejeté', 'success');
            // Recharger les données
            loadSuppliers();
        } else {
            showNotification('Erreur lors du rejet: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('❌ Erreur rejet produit en attente:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

// Éditer un produit en attente
async function editPendingProduct(supplierName, pendingId) {
    try {
        // Récupérer les détails du produit
        const supplier = suppliers.find(s => s.name === supplierName);
        const product = supplier.pending_products.find(p => p.id === pendingId);
        
        if (!product) {
            showNotification('Produit non trouvé', 'error');
            return;
        }
        
        // Remplir le modal de produit avec les données existantes
        currentEditingSupplier = supplier;
        document.getElementById('productModalTitle').innerHTML = 
            '<i class="bi bi-clock-history me-2"></i>Modifier Produit en Attente';
        
        document.getElementById('productId').value = pendingId;
        document.getElementById('productSupplier').value = supplierName;
        document.getElementById('productName').value = product.produit;
        document.getElementById('productCode').value = product.code || '';
        document.getElementById('productPrice').value = product.prix;
        document.getElementById('productUnit').value = product.unite;
        document.getElementById('productCategory').value = product.categorie || 'Non classé';
        document.getElementById('productNotes').value = `Produit en attente détecté par scanner le ${formatDate(product.date_ajout)}`;
        
        // Modifier le texte du bouton
        document.getElementById('saveProductText').textContent = 'Valider et Ajouter';
        
        const modal = new bootstrap.Modal(document.getElementById('productModal'));
        modal.show();
        
    } catch (error) {
        console.error('❌ Erreur édition produit en attente:', error);
        showNotification('Erreur lors de l\'édition', 'error');
    }
}

// Fonction pour formater les dates
function formatDate(dateString) {
    if (!dateString) return '-';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (error) {
        return dateString;
    }
}

// Charger les produits en attente pour un fournisseur
async function loadSupplierPendingProducts(supplierName) {
    try {
        const response = await fetch(`/api/suppliers/${encodeURIComponent(supplierName)}/pending-products`);
        const result = await response.json();
        
        if (result.success) {
            return result.data;
        } else {
            console.warn(`⚠️ Erreur récupération produits en attente pour ${supplierName}:`, result.error);
            return [];
        }
    } catch (error) {
        console.warn(`⚠️ Erreur réseau produits en attente pour ${supplierName}:`, error);
        return [];
    }
}

// Valider tous les produits en attente d'un fournisseur
async function validateAllPendingProducts(supplierName) {
    const supplier = suppliers.find(s => s.name === supplierName);
    if (!supplier || !supplier.pending_products || supplier.pending_products.length === 0) {
        showNotification('Aucun produit en attente pour ce fournisseur', 'info');
        return;
    }
    
    if (!confirm(`Valider tous les ${supplier.pending_products.length} produits en attente pour ${supplierName} ?`)) {
        return;
    }
    
    try {
        let validated = 0;
        let errors = 0;
        
        for (const product of supplier.pending_products) {
            try {
                const response = await fetch(`/api/suppliers/${encodeURIComponent(supplierName)}/pending-products/${product.id}/validate`, {
                    method: 'POST'
                });
                
                const result = await response.json();
                if (result.success) {
                    validated++;
                } else {
                    errors++;
                }
            } catch (error) {
                errors++;
            }
        }
        
        if (validated > 0) {
            showNotification(`✅ ${validated} produits validés${errors > 0 ? `, ${errors} erreurs` : ''}`, 'success');
            loadSuppliers(); // Recharger les données
        } else {
            showNotification('Aucun produit n\'a pu être validé', 'error');
        }
        
    } catch (error) {
        console.error('❌ Erreur validation en masse:', error);
        showNotification('Erreur lors de la validation en masse', 'error');
    }
}

console.log('📋 Module produits en attente chargé'); 