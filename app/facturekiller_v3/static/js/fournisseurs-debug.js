// Version debug simplifiée pour les fournisseurs

console.log('🔧 Fournisseurs Debug JS chargé');

// Variables globales
let suppliers = [];

// Fonction de notification simple
function showNotification(message, type = 'info') {
    console.log(`📢 ${type.toUpperCase()}: ${message}`);
    
    // Essayer d'utiliser la fonction globale si elle existe
    if (window.showNotification && typeof window.showNotification === 'function') {
        window.showNotification(message, type);
    } else {
        // Fallback avec alert
        alert(`${type.toUpperCase()}: ${message}`);
    }
}

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM chargé - Initialisation fournisseurs debug');
    loadSuppliers();
});

// Charger les fournisseurs
async function loadSuppliers() {
    try {
        console.log('📦 Chargement des fournisseurs...');
        
        const response = await fetch('/api/suppliers');
        const result = await response.json();
        
        if (result.success) {
            suppliers = result.data;
            console.log(`✅ ${suppliers.length} fournisseurs chargés`);
            renderSuppliers();
        } else {
            console.error('❌ Erreur API:', result.error);
            showNotification('Erreur lors du chargement des fournisseurs', 'error');
        }
    } catch (error) {
        console.error('❌ Erreur réseau:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

// Afficher les fournisseurs
function renderSuppliers() {
    const container = document.getElementById('suppliersContainer');
    
    if (!container) {
        console.error('❌ Container suppliersContainer non trouvé');
        return;
    }
    
    if (suppliers.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-building fs-1 text-muted"></i>
                <h4 class="mt-3 text-muted">Aucun fournisseur</h4>
                <p class="text-muted">Commencez par ajouter votre premier fournisseur</p>
                <button class="btn btn-primary" onclick="showAddSupplierModal()">
                    <i class="bi bi-plus-circle me-2"></i>Nouveau Fournisseur
                </button>
            </div>
        `;
        return;
    }
    
    container.innerHTML = suppliers.map(supplier => `
        <div class="card mb-3">
            <div class="card-header">
                <div class="row align-items-center">
                    <div class="col">
                        <h5 class="mb-0">
                            <i class="bi bi-building me-2 text-primary"></i>
                            ${supplier.name}
                        </h5>
                        <small class="text-muted">
                            ${supplier.products_count} produits • 
                            ${supplier.email || 'Pas d\'email'}
                            ${supplier.pending_count > 0 ? `<span class="badge bg-warning text-dark ms-2">${supplier.pending_count} en attente</span>` : ''}
                        </small>
                    </div>
                    <div class="col-auto">
                        <div class="btn-group">
                            <button class="btn btn-sm btn-outline-primary" onclick="editSupplier('${supplier.name}')">
                                <i class="bi bi-pencil"></i> Éditer
                            </button>
                            <button class="btn btn-sm btn-outline-success" onclick="showAddProductModal('${supplier.name}')">
                                <i class="bi bi-plus-circle"></i> Produit
                            </button>
                            ${supplier.pending_count > 0 ? `
                                <button class="btn btn-sm btn-outline-warning" onclick="showPendingProducts('${supplier.name}')">
                                    <i class="bi bi-clock"></i> En attente (${supplier.pending_count})
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
            <div class="card-body">
                <p><strong>Email:</strong> ${supplier.email || 'Non défini'}</p>
                <p><strong>Livraisons:</strong> ${supplier.delivery_days.join(', ') || 'Non défini'}</p>
                <p><strong>Notes:</strong> ${supplier.notes || 'Aucune note'}</p>
                
                ${supplier.products_count > 0 ? `
                    <h6 class="mt-3">Produits (${supplier.products_count})</h6>
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Produit</th>
                                    <th>Prix</th>
                                    <th>Unité</th>
                                    <th>Statut</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${supplier.products.slice(0, 5).map(product => `
                                    <tr>
                                        <td>${product.produit}</td>
                                        <td class="text-success fw-bold">${product.prix_unitaire}€</td>
                                        <td>${product.unite}</td>
                                        <td>
                                            ${product.status === 'pending' ? 
                                                '<span class="badge bg-warning text-dark">En attente</span>' : 
                                                '<span class="badge bg-success">Validé</span>'
                                            }
                                        </td>
                                    </tr>
                                `).join('')}
                                ${supplier.products_count > 5 ? `
                                    <tr>
                                        <td colspan="4" class="text-center text-muted">
                                            <small>... et ${supplier.products_count - 5} autres produits</small>
                                        </td>
                                    </tr>
                                ` : ''}
                            </tbody>
                        </table>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
    
    console.log('✅ Fournisseurs affichés');
}

// Afficher les produits en attente d'un fournisseur
function showPendingProducts(supplierName) {
    console.log('⏳ Affichage produits en attente pour:', supplierName);
    
    const supplier = suppliers.find(s => s.name === supplierName);
    if (!supplier) return;
    
    const pendingProducts = supplier.products.filter(p => p.status === 'pending');
    
    if (pendingProducts.length === 0) {
        showNotification('Aucun produit en attente pour ce fournisseur', 'info');
        return;
    }
    
    // Créer un modal pour afficher les produits en attente
    const modalHtml = `
        <div class="modal fade" id="pendingProductsModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-clock me-2"></i>Produits en attente - ${supplierName}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="table-responsive">
                            <table class="table">
                                <thead>
                                    <tr>
                                        <th>Produit</th>
                                        <th>Prix</th>
                                        <th>Unité</th>
                                        <th>Source</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${pendingProducts.map(product => `
                                        <tr>
                                            <td>${product.produit}</td>
                                            <td class="fw-bold">${product.prix_unitaire}€</td>
                                            <td>${product.unite}</td>
                                            <td><small class="text-muted">${product.source || 'Scan auto'}</small></td>
                                            <td>
                                                <div class="btn-group btn-group-sm">
                                                    <button class="btn btn-outline-success" onclick="validatePendingProduct(${product.id})">
                                                        <i class="bi bi-check"></i> Valider
                                                    </button>
                                                    <button class="btn btn-outline-danger" onclick="rejectPendingProduct(${product.id})">
                                                        <i class="bi bi-x"></i> Rejeter
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fermer</button>
                        <button type="button" class="btn btn-success" onclick="validateAllPending('${supplierName}')">
                            <i class="bi bi-check-all"></i> Tout valider
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Supprimer l'ancien modal s'il existe
    const existingModal = document.getElementById('pendingProductsModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Ajouter le nouveau modal
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Afficher le modal
    const modal = new bootstrap.Modal(document.getElementById('pendingProductsModal'));
    modal.show();
}

// Valider un produit en attente
async function validatePendingProduct(productId) {
    try {
        const response = await fetch(`/api/prices/pending/${productId}/validate`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Produit validé avec succès', 'success');
            // Recharger les fournisseurs pour mettre à jour les compteurs
            setTimeout(() => {
                loadSuppliers();
            }, 500);
        } else {
            showNotification('Erreur lors de la validation: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('❌ Erreur validation produit:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

// Rejeter un produit en attente
async function rejectPendingProduct(productId) {
    try {
        const response = await fetch(`/api/prices/pending/${productId}/reject`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Produit rejeté', 'success');
            // Recharger les fournisseurs pour mettre à jour les compteurs
            setTimeout(() => {
                loadSuppliers();
            }, 500);
        } else {
            showNotification('Erreur lors du rejet: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('❌ Erreur rejet produit:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

// Valider tous les produits en attente d'un fournisseur
async function validateAllPending(supplierName) {
    const supplier = suppliers.find(s => s.name === supplierName);
    if (!supplier) return;
    
    const pendingProducts = supplier.products.filter(p => p.status === 'pending');
    const productIds = pendingProducts.map(p => p.id);
    
    if (productIds.length === 0) return;
    
    try {
        const response = await fetch('/api/prices/pending/bulk-validate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                product_ids: productIds
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification(`${productIds.length} produits validés avec succès`, 'success');
            
            // Fermer le modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('pendingProductsModal'));
            if (modal) {
                modal.hide();
            }
            
            // Recharger les fournisseurs
            setTimeout(() => {
                loadSuppliers();
            }, 500);
        } else {
            showNotification('Erreur lors de la validation: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('❌ Erreur validation en masse:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

// Afficher le modal d'ajout de fournisseur
function showAddSupplierModal() {
    console.log('📝 Ouverture modal nouveau fournisseur');
    
    // Réinitialiser le formulaire
    const form = document.getElementById('supplierForm');
    if (form) {
        form.reset();
    }
    
    // Ouvrir le modal
    const modalElement = document.getElementById('supplierModal');
    if (modalElement) {
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
        console.log('✅ Modal fournisseur ouvert');
    } else {
        console.error('❌ Modal supplierModal non trouvé');
        showNotification('Erreur: Modal non trouvé', 'error');
    }
}

// Éditer un fournisseur
function editSupplier(supplierName) {
    console.log('✏️ Édition fournisseur:', supplierName);
    
    const supplier = suppliers.find(s => s.name === supplierName);
    if (!supplier) {
        console.error('❌ Fournisseur non trouvé:', supplierName);
        return;
    }
    
    // Remplir le formulaire
    document.getElementById('supplierName').value = supplier.name;
    document.getElementById('supplierEmail').value = supplier.email || '';
    document.getElementById('supplierNotes').value = supplier.notes || '';
    
    // Cocher les jours de livraison
    const deliveryCheckboxes = document.querySelectorAll('[id^="delivery"]');
    deliveryCheckboxes.forEach(cb => {
        cb.checked = supplier.delivery_days.includes(cb.value);
    });
    
    // Ouvrir le modal
    const modalElement = document.getElementById('supplierModal');
    if (modalElement) {
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
        console.log('✅ Modal édition ouvert');
    }
}

// Sauvegarder un fournisseur
async function saveSupplier() {
    console.log('💾 Sauvegarde fournisseur...');
    
    try {
        const formData = {
            name: document.getElementById('supplierName').value.trim(),
            email: document.getElementById('supplierEmail').value.trim(),
            notes: document.getElementById('supplierNotes').value.trim(),
            delivery_days: []
        };
        
        // Récupérer les jours de livraison cochés
        const deliveryCheckboxes = document.querySelectorAll('[id^="delivery"]:checked');
        formData.delivery_days = Array.from(deliveryCheckboxes).map(cb => cb.value);
        
        console.log('📝 Données à envoyer:', formData);
        
        if (!formData.name) {
            showNotification('Le nom du fournisseur est obligatoire', 'error');
            return;
        }
        
        const response = await fetch('/api/suppliers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        console.log('📨 Réponse API:', result);
        
        if (result.success) {
            showNotification('Fournisseur sauvegardé avec succès', 'success');
            
            // Fermer le modal
            const modalElement = document.getElementById('supplierModal');
            if (modalElement) {
                const modal = bootstrap.Modal.getInstance(modalElement);
                if (modal) {
                    modal.hide();
                }
            }
            
            // Recharger les données
            setTimeout(() => {
                loadSuppliers();
            }, 500);
            
        } else {
            showNotification('Erreur lors de la sauvegarde: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('❌ Erreur sauvegarde fournisseur:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

// Afficher le modal d'ajout de produit
function showAddProductModal(supplierName) {
    console.log('📦 Ouverture modal nouveau produit pour:', supplierName);
    
    document.getElementById('productSupplierName').value = supplierName;
    
    // Réinitialiser le formulaire
    const form = document.getElementById('productForm');
    if (form) {
        form.reset();
    }
    
    // Ouvrir le modal
    const modalElement = document.getElementById('productModal');
    if (modalElement) {
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
        console.log('✅ Modal produit ouvert');
    } else {
        console.error('❌ Modal productModal non trouvé');
        showNotification('Erreur: Modal produit non trouvé', 'error');
    }
}

// Sauvegarder un produit
async function saveProduct() {
    console.log('💾 Sauvegarde produit...');
    
    try {
        const supplierName = document.getElementById('productSupplierName').value;
        const productData = {
            name: document.getElementById('productName').value.trim(),
            unit_price: parseFloat(document.getElementById('productPrice').value),
            unit: document.getElementById('productUnit').value,
            code: document.getElementById('productCode').value.trim()
        };
        
        console.log('📝 Données produit:', productData);
        
        if (!productData.name || !productData.unit_price) {
            showNotification('Le nom et le prix du produit sont obligatoires', 'error');
            return;
        }
        
        const response = await fetch(`/api/suppliers/${encodeURIComponent(supplierName)}/products`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(productData)
        });
        
        const result = await response.json();
        console.log('📨 Réponse API produit:', result);
        
        if (result.success) {
            showNotification('Produit ajouté avec succès', 'success');
            
            // Fermer le modal
            const modalElement = document.getElementById('productModal');
            if (modalElement) {
                const modal = bootstrap.Modal.getInstance(modalElement);
                if (modal) {
                    modal.hide();
                }
            }
            
            // Recharger les données
            setTimeout(() => {
                loadSuppliers();
            }, 500);
            
        } else {
            showNotification('Erreur lors de l\'ajout: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('❌ Erreur ajout produit:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

console.log('✅ Fournisseurs Debug JS initialisé'); 