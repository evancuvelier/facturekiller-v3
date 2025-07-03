// Gestion des produits en attente - Extension fournisseurs.js
// FactureKiller V3

// ===== FONCTIONS POUR GÉRER LES PRODUITS EN ATTENTE =====

// Valider un produit en attente
async function validatePendingProduct(supplierName, pendingId) {
    try {
        console.log(`🔄 Validation produit ${pendingId} pour ${supplierName}`);
        
        const response = await fetch(`/api/suppliers/${encodeURIComponent(supplierName)}/pending-products/${pendingId}/validate`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification(result.message, 'success');
            
            // 🔄 NOTIFICATION DE SYNCHRONISATION si applicable
            if (result.sync_result && result.sync_result.success && result.sync_count > 0) {
                const syncRestaurants = result.sync_result.synced_restaurants || [];
                const restaurantNames = syncRestaurants.join(', ');
                
                setTimeout(() => {
                    showNotification(
                        `🔄 Prix synchronisé automatiquement vers ${result.sync_count} restaurant(s) couplé(s): ${restaurantNames}`,
                        'info',
                        5000
                    );
                }, 1000);
                
                console.log(`🔄 SYNC: Produit synchronisé vers: ${restaurantNames}`);
            }
            
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
    
    if (!confirm(`Valider tous les ${supplier.pending_products.length} produits en attente pour ${supplierName} ?\n\n⚠️ Cette action synchronisera automatiquement les prix vers les restaurants couplés.`)) {
        return;
    }
    
    try {
        let validated = 0;
        let errors = 0;
        let totalSyncCount = 0;
        let syncedRestaurants = new Set();
        
        console.log(`🔄 Validation en masse de ${supplier.pending_products.length} produits pour ${supplierName}`);
        
        for (const product of supplier.pending_products) {
            try {
                console.log(`🔄 Validation: ${product.produit} (ID: ${product.id})`);
                
                const response = await fetch(`/api/suppliers/${encodeURIComponent(supplierName)}/pending-products/${product.id}/validate`, {
                    method: 'POST'
                });
                
                const result = await response.json();
                if (result.success) {
                    validated++;
                    
                    // Compter les synchronisations
                    if (result.sync_result && result.sync_result.success && result.sync_count > 0) {
                        totalSyncCount += result.sync_count;
                        const restaurants = result.sync_result.synced_restaurants || [];
                        restaurants.forEach(r => syncedRestaurants.add(r));
                    }
                } else {
                    errors++;
                    console.error(`❌ Erreur validation ${product.produit}:`, result.error);
                }
            } catch (error) {
                errors++;
                console.error(`❌ Erreur réseau ${product.produit}:`, error);
            }
        }
        
        if (validated > 0) {
            showNotification(`✅ ${validated} produits validés${errors > 0 ? `, ${errors} erreurs` : ''}`, 'success');
            
            // 🔄 NOTIFICATION DE SYNCHRONISATION EN MASSE
            if (totalSyncCount > 0 && syncedRestaurants.size > 0) {
                const restaurantNames = Array.from(syncedRestaurants).join(', ');
                setTimeout(() => {
                    showNotification(
                        `🔄 ${validated} prix synchronisés automatiquement vers ${syncedRestaurants.size} restaurant(s) couplé(s): ${restaurantNames}`,
                        'info',
                        6000
                    );
                }, 1500);
                
                console.log(`🔄 SYNC MASSE: ${validated} produits synchronisés vers: ${restaurantNames}`);
            }
            
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