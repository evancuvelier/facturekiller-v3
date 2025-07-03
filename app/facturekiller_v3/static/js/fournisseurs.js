// Gestion des Fournisseurs FactureKiller V3

let suppliers = [];
let filteredSuppliers = [];
let currentEditingSupplier = null;

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    console.log('🏢 Initialisation Gestion Fournisseurs...');
    
    loadSuppliers();
    setupEventListeners();
});

// Configuration des écouteurs d'événements
function setupEventListeners() {
    // Recherche en temps réel
    document.getElementById('searchInput').addEventListener('input', applyFilters);
    
    // Filtres
    document.getElementById('filterStatus').addEventListener('change', applyFilters);
    document.getElementById('sortBy').addEventListener('change', applyFilters);
}

// Charger les fournisseurs du restaurant
async function loadSuppliers() {
    try {
        console.log('🔄 Chargement des fournisseurs...');
        
        // Utiliser l'API filtrée par restaurant
        const response = await fetch('/api/restaurant/suppliers');
        const result = await response.json();
        
        if (result.success) {
            suppliers = result.data;
            
            // Pour chaque fournisseur, récupérer les produits en attente
            for (let supplier of suppliers) {
                try {
                    const pendingResponse = await fetch(`/api/suppliers/${encodeURIComponent(supplier.name)}/pending-products`);
                    const pendingResult = await pendingResponse.json();
                    
                    if (pendingResult.success) {
                        supplier.pending_products = pendingResult.data;
                        console.log(`📋 ${supplier.name}: ${pendingResult.count} produits en attente`);
                    } else {
                        supplier.pending_products = [];
                    }
                } catch (error) {
                    console.warn(`⚠️ Erreur récupération produits en attente pour ${supplier.name}:`, error);
                    supplier.pending_products = [];
                }
            }
            
            filteredSuppliers = [...suppliers];
            
            renderSuppliers();
            
            console.log(`✅ ${suppliers.length} fournisseurs chargés pour ${result.restaurant}`);
            
            // 🔔 NOTIFICATION SI NOUVEAUX PRODUITS EN ATTENTE
            const totalPendingProducts = suppliers.reduce((total, supplier) => 
                total + (supplier.pending_products?.length || 0), 0
            );
            
            if (totalPendingProducts > 0) {
                showPendingProductsAlert(totalPendingProducts);
            }
            
            // Afficher le restaurant actuel dans le titre
            const titleElement = document.querySelector('h1.h2');
            if (titleElement && result.restaurant) {
                titleElement.innerHTML = `
                    <i class="bi bi-building"></i> Fournisseurs - ${result.restaurant}
                    ${totalPendingProducts > 0 ? `<span class="badge bg-warning ms-2">${totalPendingProducts} en attente</span>` : ''}
                `;
            }
            
            // Afficher un message informatif
            const container = document.getElementById('suppliersContainer');
            if (suppliers.length === 0) {
                container.innerHTML = `
                    <div class="text-center py-5">
                        <i class="bi bi-building fs-1 text-muted"></i>
                        <h4 class="mt-3 text-muted">Aucun fournisseur pour ${result.restaurant}</h4>
                        <p class="text-muted">Ce restaurant n'a pas encore de fournisseurs associés</p>
                        <p class="text-muted">Demandez à votre administrateur d'ajouter des fournisseurs à ce restaurant</p>
                        <div class="mt-4">
                            <small class="text-muted">
                                <i class="bi bi-info-circle me-1"></i>
                                Les fournisseurs sont gérés dans l'interface d'administration
                            </small>
                        </div>
                    </div>
                `;
            }
        } else {
            console.error('❌ Erreur chargement fournisseurs:', result.error);
            
            if (result.requires_restaurant) {
                // Aucun restaurant sélectionné
                const container = document.getElementById('suppliersContainer');
                container.innerHTML = `
                    <div class="text-center py-5">
                        <i class="bi bi-exclamation-triangle fs-1 text-warning"></i>
                        <h4 class="mt-3 text-warning">Restaurant requis</h4>
                        <p class="text-muted">Veuillez sélectionner un restaurant pour voir ses fournisseurs</p>
                        <p class="text-muted">Utilisez le sélecteur de restaurant en haut à droite</p>
                    </div>
                `;
                return;
            }
            
            showNotification('Erreur lors du chargement des fournisseurs', 'error');
        }
    } catch (error) {
        console.error('❌ Erreur réseau:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

// Appliquer les filtres et le tri
function applyFilters() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const statusFilter = document.getElementById('filterStatus').value;
    const sortBy = document.getElementById('sortBy').value;
    
    // Filtrage
    filteredSuppliers = suppliers.filter(supplier => {
        // Recherche textuelle
        const matchesSearch = !searchTerm || 
            supplier.name.toLowerCase().includes(searchTerm) ||
            supplier.email.toLowerCase().includes(searchTerm);
        
        // Filtre par statut
        let matchesStatus = true;
        if (statusFilter === 'complete') {
            matchesStatus = supplier.email && supplier.delivery_days.length > 0;
        } else if (statusFilter === 'incomplete') {
            matchesStatus = !supplier.email || supplier.delivery_days.length === 0;
        } else if (statusFilter === 'no-email') {
            matchesStatus = !supplier.email;
        }
        
        return matchesSearch && matchesStatus;
    });
    
    // Tri
    filteredSuppliers.sort((a, b) => {
        switch (sortBy) {
            case 'products':
                return b.products_count - a.products_count;
            case 'updated':
                return new Date(b.updated_at || 0) - new Date(a.updated_at || 0);
            default: // name
                return a.name.localeCompare(b.name);
        }
    });
    
    renderSuppliers();
}

// Afficher les fournisseurs
function renderSuppliers() {
    const container = document.getElementById('suppliersContainer');
    
    if (filteredSuppliers.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-building fs-1 text-muted"></i>
                <h4 class="mt-3 text-muted">Aucun fournisseur trouvé</h4>
                <p class="text-muted">Commencez par ajouter votre premier fournisseur</p>
                <button class="btn btn-primary" onclick="showAddSupplierModal()">
                    <i class="bi bi-plus-circle me-2"></i>Nouveau Fournisseur
                </button>
            </div>
        `;
        return;
    }
    
    container.innerHTML = filteredSuppliers.map(supplier => `
        <div class="card mb-3">
            <div class="card-header">
                <div class="row align-items-center">
                    <div class="col">
                        <h5 class="mb-0">
                            <i class="bi bi-building me-2 text-primary"></i>
                            ${supplier.name}
                            ${supplier.is_auto_created ? '<span class="badge bg-warning ms-2">Auto-créé</span>' : ''}
                        </h5>
                    </div>
                    <div class="col-auto">
                        <div class="btn-group">
                            <button class="btn btn-sm btn-outline-primary" onclick="editSupplier('${supplier.name}')">
                                <i class="bi bi-pencil"></i> Éditer
                            </button>
                            <button class="btn btn-sm btn-outline-success" onclick="showAddProductModal('${supplier.name}')">
                                <i class="bi bi-plus-circle"></i> Produit
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteSupplier('${supplier.name}')">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            <div class="card-body">
                <div class="row g-3 mb-3">
                    <div class="col-md-4">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-envelope me-2 text-info"></i>
                            <span class="text-muted">Email:</span>
                            <span class="ms-2">${supplier.email || '<em>Non renseigné</em>'}</span>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-calendar-week me-2 text-success"></i>
                            <span class="text-muted">Livraisons:</span>
                            <span class="ms-2">${supplier.delivery_days.length ? supplier.delivery_days.join(', ') : '<em>Non défini</em>'}</span>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-box-seam me-2 text-warning"></i>
                            <span class="text-muted">Produits:</span>
                            <span class="ms-2 fw-bold">${supplier.products_count}</span>
                        </div>
                    </div>
                </div>
                
                ${supplier.notes ? `
                    <div class="mb-3">
                        <small class="text-muted">
                            <i class="bi bi-sticky me-1"></i>
                            ${supplier.notes}
                        </small>
                    </div>
                ` : ''}
                
                <!-- Liste des produits -->
                <div class="products-section">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <h6 class="mb-0">
                            <i class="bi bi-box-seam me-1"></i>
                            Catalogue produits (${supplier.products_count})
                        </h6>
                        <button class="btn btn-sm btn-outline-secondary" onclick="toggleProducts('${supplier.name}')">
                            <i class="bi bi-chevron-down" id="toggle-${supplier.name.replace(/\s+/g, '-')}"></i>
                        </button>
                    </div>
                    <div class="collapse" id="products-${supplier.name.replace(/\s+/g, '-')}">
                        ${renderSupplierProducts(supplier)}
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

// Afficher les produits d'un fournisseur
function renderSupplierProducts(supplier) {
    if (supplier.products_count === 0 && (!supplier.pending_products || supplier.pending_products.length === 0)) {
        return `
            <div class="text-center py-3 text-muted">
                <i class="bi bi-box fs-4"></i>
                <p class="mt-2 mb-0">Aucun produit dans le catalogue</p>
                <button class="btn btn-sm btn-primary mt-2" onclick="showAddProductModal('${supplier.name}')">
                    <i class="bi bi-plus-circle me-1"></i>Ajouter le premier produit
                </button>
            </div>
        `;
    }
    
    let html = '';
    
    // Section des produits en attente (si il y en a)
    if (supplier.pending_products && supplier.pending_products.length > 0) {
        html += `
            <div class="card border-warning mb-3">
                <div class="card-header bg-warning bg-opacity-10">
                    <div class="d-flex justify-content-between align-items-center">
                        <h6 class="mb-0 text-warning">
                            <i class="bi bi-clock-history me-2"></i>
                            ⏳ Produits en attente de validation (${supplier.pending_products.length})
                        </h6>
                        <div>
                            <button class="btn btn-sm btn-warning" onclick="validateAllPendingProducts('${supplier.name}')" title="Valider tous les produits en attente">
                                <i class="bi bi-check-all me-1"></i>Tout valider
                            </button>
                        </div>
                    </div>
                    <div class="alert alert-warning alert-sm mt-2 mb-0" style="font-size: 0.85em;">
                        <i class="bi bi-info-circle me-1"></i>
                        <strong>Attention :</strong> Ces produits ont été détectés par le scanner mais ne sont <strong>PAS encore dans votre catalogue</strong>. 
                        Vous devez les valider manuellement pour les ajouter définitivement.
                    </div>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Produit</th>
                                    <th>Prix unitaire</th>
                                    <th>Unité</th>
                                    <th>Date scan</th>
                                    <th>Statut</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${supplier.pending_products.map(product => `
                                    <tr class="table-warning bg-opacity-25">
                                        <td>
                                            <div>
                                                <strong>${product.produit}</strong>
                                                <br><small class="text-muted">Source: ${product.source || 'scanner'}</small>
                                                ${product.code ? `<br><code class="text-primary small">${product.code}</code>` : ''}
                                            </div>
                                        </td>
                                        <td class="fw-bold text-warning">${product.prix}€</td>
                                        <td>${product.unite}</td>
                                        <td><small class="text-muted">${formatDate(product.date_ajout)}</small></td>
                                        <td>
                                            <span class="badge bg-warning text-dark">
                                                <i class="bi bi-hourglass-split me-1"></i>EN ATTENTE
                                            </span>
                                        </td>
                                        <td>
                                            <div class="btn-group btn-group-sm">
                                                <button class="btn btn-outline-success btn-sm" 
                                                        onclick="validatePendingProduct('${supplier.name}', ${product.id})"
                                                        title="✅ Valider et ajouter au catalogue">
                                                    <i class="bi bi-check"></i>
                                                </button>
                                                <button class="btn btn-outline-primary btn-sm" 
                                                        onclick="editPendingProduct('${supplier.name}', ${product.id})"
                                                        title="✏️ Modifier avant validation">
                                                    <i class="bi bi-pencil"></i>
                                                </button>
                                                <button class="btn btn-outline-danger btn-sm" 
                                                        onclick="rejectPendingProduct('${supplier.name}', ${product.id})"
                                                        title="❌ Rejeter">
                                                    <i class="bi bi-trash"></i>
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Section des produits validés
    if (supplier.products_count > 0) {
        html += `
            <div class="card border-success">
                <div class="card-header bg-success bg-opacity-10">
                    <h6 class="mb-0 text-success">
                        <i class="bi bi-check-circle me-2"></i>
                        ✅ Catalogue officiel (${supplier.products_count} produits)
                    </h6>
                    <div class="alert alert-success alert-sm mt-2 mb-0" style="font-size: 0.85em;">
                        <i class="bi bi-check-circle me-1"></i>
                        Ces produits sont <strong>validés et actifs</strong> dans votre catalogue. Ils sont utilisés pour les comparaisons de prix.
                    </div>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Produit</th>
                                    <th>Prix unitaire</th>
                                    <th>Unité</th>
                                    <th>Code</th>
                                    <th>Statut</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${supplier.products.map((product, index) => `
                                    <tr class="table-success bg-opacity-10">
                                        <td>
                                            <strong>${product.produit}</strong>
                                            ${product.categorie ? `<br><small class="text-muted">${product.categorie}</small>` : ''}
                                        </td>
                                        <td class="fw-bold text-success">${product.prix_unitaire}€</td>
                                        <td>${product.unite}</td>
                                        <td><small class="text-muted">${product.code_produit || '-'}</small></td>
                                        <td>
                                            <span class="badge bg-success">
                                                <i class="bi bi-check-circle me-1"></i>VALIDÉ
                                            </span>
                                        </td>
                                        <td>
                                            <div class="btn-group btn-group-sm">
                                                <button class="btn btn-outline-primary btn-sm" onclick="editProduct('${supplier.name}', ${index})">
                                                    <i class="bi bi-pencil"></i>
                                                </button>
                                                <button class="btn btn-outline-danger btn-sm" onclick="deleteProduct('${supplier.name}', ${index})">
                                                    <i class="bi bi-trash"></i>
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }
    
    return html;
}

// Basculer l'affichage des produits
function toggleProducts(supplierName) {
    const cleanName = supplierName.replace(/\s+/g, '-');
    const productsDiv = document.getElementById(`products-${cleanName}`);
    const toggleIcon = document.getElementById(`toggle-${cleanName}`);
    
    if (productsDiv.classList.contains('show')) {
        productsDiv.classList.remove('show');
        toggleIcon.className = 'bi bi-chevron-down';
    } else {
        productsDiv.classList.add('show');
        toggleIcon.className = 'bi bi-chevron-up';
    }
}

// Afficher le modal d'ajout de fournisseur
function showAddSupplierModal() {
    currentEditingSupplier = null;
    
    document.getElementById('supplierModalTitle').innerHTML = 
        '<i class="bi bi-building me-2"></i>Nouveau Fournisseur';
    
    // Reset du formulaire
    document.getElementById('supplierForm').reset();
    document.getElementById('supplierId').value = '';
    
    // Décocher toutes les cases de livraison
    const deliveryCheckboxes = document.querySelectorAll('[id^="delivery"]');
    deliveryCheckboxes.forEach(cb => cb.checked = false);
    
    const modal = new bootstrap.Modal(document.getElementById('supplierModal'));
    modal.show();
}

// Éditer un fournisseur
function editSupplier(supplierName) {
    const supplier = suppliers.find(s => s.name === supplierName);
    if (!supplier) return;
    
    currentEditingSupplier = supplier;
    
    document.getElementById('supplierModalTitle').innerHTML = 
        '<i class="bi bi-building me-2"></i>Éditer Fournisseur';
    
    // Remplir le formulaire
    document.getElementById('supplierId').value = supplier.name;
    document.getElementById('supplierName').value = supplier.name;
    document.getElementById('supplierEmail').value = supplier.email || '';
    document.getElementById('supplierNotes').value = supplier.notes || '';
    
    // Cocher les jours de livraison
    const deliveryCheckboxes = document.querySelectorAll('[id^="delivery"]');
    deliveryCheckboxes.forEach(cb => {
        cb.checked = supplier.delivery_days.includes(cb.value);
    });
    
    const modal = new bootstrap.Modal(document.getElementById('supplierModal'));
    modal.show();
}

// Sauvegarder un fournisseur
async function saveSupplier() {
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
        
        if (!formData.name) {
            showNotification('Le nom du fournisseur est obligatoire', 'error');
            return;
        }
        
        // Utiliser l'API spécifique au restaurant pour créer un nouveau fournisseur
        const apiUrl = currentEditingSupplier ? '/api/suppliers' : '/api/restaurant/suppliers/create';
        
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            let message = currentEditingSupplier ? 'Fournisseur mis à jour' : 'Fournisseur créé avec succès';
            
            if (!currentEditingSupplier && result.restaurant) {
                message += ` et associé au restaurant ${result.restaurant}`;
            }
            
            showNotification(message, 'success');
            
            // Fermer le modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('supplierModal'));
            modal.hide();
            
            // Recharger les données
            loadSuppliers();
        } else {
            if (result.requires_restaurant) {
                showNotification('Veuillez sélectionner un restaurant pour créer un fournisseur', 'error');
            } else {
                showNotification('Erreur lors de la sauvegarde: ' + result.error, 'error');
            }
        }
    } catch (error) {
        console.error('❌ Erreur sauvegarde fournisseur:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

// Supprimer un fournisseur
function deleteSupplier(supplierName) {
    const supplier = suppliers.find(s => s.name === supplierName);
    if (!supplier) return;
    
    if (confirm(`Êtes-vous sûr de vouloir supprimer le fournisseur "${supplierName}" ?\n\nCela supprimera également tous ses produits (${supplier.products_count} produits).`)) {
        performDeleteSupplier(supplierName);
    }
}

// Effectuer la suppression
async function performDeleteSupplier(supplierName) {
    try {
        const response = await fetch(`/api/suppliers/${encodeURIComponent(supplierName)}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification(`Fournisseur "${supplierName}" supprimé avec succès`, 'success');
            loadSuppliers();
        } else {
            showNotification('Erreur lors de la suppression: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('❌ Erreur suppression fournisseur:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

// Afficher le modal d'ajout de produit
function showAddProductModal(supplierName) {
    document.getElementById('productSupplier').value = supplierName;
    document.getElementById('productForm').reset();
    document.getElementById('productSupplier').value = supplierName; // Remettre après reset
    
    const modal = new bootstrap.Modal(document.getElementById('productModal'));
    modal.show();
}

// Sauvegarder un produit
async function saveProduct() {
    try {
        const supplierName = document.getElementById('productSupplier').value;
        const productData = {
            name: document.getElementById('productName').value.trim(),
            unit_price: parseFloat(document.getElementById('productPrice').value),
            unit: document.getElementById('productUnit').value,
            code: document.getElementById('productCode').value.trim(),
            category: document.getElementById('productCategory').value,
            notes: document.getElementById('productNotes').value.trim()
        };
        
        if (!productData.name || !productData.unit_price) {
            showNotification('Le nom et le prix du produit sont obligatoires', 'error');
            return;
        }
        
        // IMPORTANT: Utiliser l'API restaurant pour associer le produit au restaurant actuel
        const response = await fetch(`/api/restaurant/suppliers/${encodeURIComponent(supplierName)}/products`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(productData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            let message = 'Produit ajouté avec succès';
            if (result.restaurant) {
                message += ` pour le restaurant ${result.restaurant}`;
            }
            showNotification(message, 'success');
            
            // Fermer le modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('productModal'));
            modal.hide();
            
            // Recharger les données
            loadSuppliers();
        } else {
            if (result.requires_restaurant) {
                showNotification('Veuillez sélectionner un restaurant pour ajouter un produit', 'error');
            } else {
                showNotification('Erreur lors de l\'ajout: ' + result.error, 'error');
            }
        }
    } catch (error) {
        console.error('❌ Erreur ajout produit:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

// Éditer un produit (modal d'édition locale)
function editProduct(supplierName, productIndex) {
    const supplier = suppliers.find(s => s.name === supplierName);
    if (!supplier || !supplier.products[productIndex]) return;
    
    const product = supplier.products[productIndex];
    
    // Pré-remplir le modal avec les données du produit pour édition
    document.getElementById('productSupplier').value = supplierName;
    document.getElementById('productName').value = product.produit || '';
    document.getElementById('productPrice').value = product.prix_unitaire || '';
    document.getElementById('productUnit').value = product.unite || 'unité';
    document.getElementById('productCode').value = product.code || '';
    document.getElementById('productCategory').value = product.categorie || '';
    document.getElementById('productNotes').value = product.notes || '';
    
    // Afficher le modal d'édition
    const modal = new bootstrap.Modal(document.getElementById('productModal'));
    modal.show();
}

// Supprimer un produit
function deleteProduct(supplierName, productIndex) {
    const supplier = suppliers.find(s => s.name === supplierName);
    if (!supplier || !supplier.products[productIndex]) return;
    
    const product = supplier.products[productIndex];
    
    if (confirm(`Supprimer le produit "${product.produit}" ?`)) {
        // Utiliser l'API des prix pour supprimer
        // TODO: Implémenter la suppression de produit individuel
        showNotification('Fonctionnalité en cours de développement', 'warning');
    }
}

// Fonction de notification
function showNotification(message, type = 'info') {
    const alertClass = {
        'success': 'alert-success',
        'error': 'alert-danger', 
        'warning': 'alert-warning',
        'info': 'alert-info'
    }[type] || 'alert-info';
    
    const notification = document.createElement('div');
    notification.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

// ===== NOUVELLES FONCTIONS POUR GÉRER LES PRODUITS EN ATTENTE =====

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
    if (!dateString) return '';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    } catch (error) {
        return dateString;
    }
}

function showPendingProductsAlert(count) {
    /**
     * 🔔 ALERTE POUR PRODUITS EN ATTENTE
     * Affiche une notification discrète mais visible
     */
    const existingAlert = document.getElementById('pendingProductsAlert');
    if (existingAlert) {
        existingAlert.remove();
    }
    
    const alert = document.createElement('div');
    alert.id = 'pendingProductsAlert';
    alert.className = 'alert alert-warning alert-dismissible fade show';
    alert.style.position = 'sticky';
    alert.style.top = '10px';
    alert.style.zIndex = '1050';
    alert.innerHTML = `
        <div class="d-flex align-items-center">
            <div class="flex-grow-1">
                <h6 class="alert-heading mb-1">
                    <i class="bi bi-hourglass-split me-2"></i>Nouveaux produits détectés !
                </h6>
                <p class="mb-0">
                    <strong>${count} produit(s)</strong> en attente de validation. 
                    Ces produits ont été détectés lors de scans mais ne sont pas encore dans vos catalogues.
                </p>
            </div>
            <div class="ms-3">
                <button class="btn btn-warning btn-sm" onclick="scrollToPendingProducts()">
                    <i class="bi bi-eye me-1"></i>Voir
                </button>
            </div>
        </div>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insérer en haut de la page
    const container = document.querySelector('.container-fluid');
    container.insertBefore(alert, container.firstChild);
}

function scrollToPendingProducts() {
    /**
     * 📍 SCROLL VERS LES PRODUITS EN ATTENTE
     * Trouve et affiche la première section de produits en attente
     */
    const pendingCard = document.querySelector('.card.border-warning');
    if (pendingCard) {
        // Développer la section produits si elle est fermée
        const parentCard = pendingCard.closest('.card');
        const productSection = parentCard.querySelector('.collapse');
        if (productSection && !productSection.classList.contains('show')) {
            productSection.classList.add('show');
            // Mettre à jour l'icône
            const toggleIcon = parentCard.querySelector('[id^="toggle-"]');
            if (toggleIcon) {
                toggleIcon.className = 'bi bi-chevron-up';
            }
        }
        
        // Scroll vers la carte
        pendingCard.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center' 
        });
        
        // Animation de surbrillance
        pendingCard.style.animation = 'pulse 1s ease-in-out 3';
    } else {
        showNotification('Aucun produit en attente visible actuellement', 'info');
    }
}

// 🔄 FONCTION DE RECHARGEMENT FORCÉ
async function forceRefreshSuppliers() {
    /**
     * Force le rechargement complet des données fournisseurs
     * Utile après un scan ou des modifications
     */
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.innerHTML = '<i class="bi bi-arrow-repeat spinner-border spinner-border-sm me-2"></i>Actualisation...';
    }
    
    try {
        await loadSuppliers();
        showNotification('Données actualisées !', 'success');
    } catch (error) {
        showNotification('Erreur lors de l\'actualisation', 'error');
    } finally {
        if (refreshBtn) {
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = '<i class="bi bi-arrow-repeat me-2"></i>Actualiser';
        }
    }
}

// 🎧 ÉCOUTER LES ÉVÉNEMENTS DE SCAN TERMINÉ
window.addEventListener('invoiceScanCompleted', function(event) {
    /**
     * Réagir aux scans de factures terminés depuis d'autres pages
     * Recharge automatiquement les fournisseurs si de nouveaux produits ont été détectés
     */
    console.log('🔔 Scan de facture terminé détecté, rechargement des fournisseurs...');
    
    if (event.detail?.newProductsCount > 0) {
        showNotification(
            `🆕 ${event.detail.newProductsCount} nouveaux produits détectés ! Actualisation en cours...`, 
            'info'
        );
        
        // Recharger après un court délai
        setTimeout(() => {
            forceRefreshSuppliers();
        }, 1000);
    }
});

// 🔧 FONCTION DE TEST POUR DEBUG RAPIDE
window.debugAddTestPending = async function() {
    try {
        console.log('🔧 DEBUG: Test ajout produit en attente...');
        
        const response = await fetch('/api/debug/add-test-pending', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification(`✅ Produit test ajouté avec succès !`, 'success');
            console.log('🔧 DEBUG: Succès:', result);
            
            // Recharger les fournisseurs
            setTimeout(() => {
                loadSuppliers();
            }, 1000);
        } else {
            showNotification(`❌ Échec ajout produit test: ${result.error}`, 'error');
            console.error('🔧 DEBUG: Échec:', result);
        }
    } catch (error) {
        console.error('🔧 DEBUG: Erreur:', error);
        showNotification('❌ Erreur lors du test', 'error');
    }
};

window.debugCheckWorkflow = async function() {
    try {
        console.log('🔧 DEBUG: Vérification workflow...');
        
        const response = await fetch('/api/debug/check-pending-workflow');
        const result = await response.json();
        
        console.log('🔧 DEBUG: Workflow Status:', result);
        
        if (result.success) {
            const message = `
📊 WORKFLOW STATUS:
• Restaurant: ${result.current_restaurant}
• Produits en attente système: ${result.total_pending_system}
• Produits en attente restaurant: ${result.total_pending_restaurant}
• Fournisseurs avec produits: ${Object.keys(result.suppliers_with_pending).join(', ')}
            `;
            
            showNotification(message, 'info', 8000);
        }
    } catch (error) {
        console.error('🔧 DEBUG: Erreur vérification:', error);
    }
};

// 🔧 DEBUG: Forcer le rechargement avec produits en attente
async function debugForceRefreshWithPending() {
    console.log('🔧 DEBUG: Forçage rechargement avec produits en attente...');
    
    try {
        const response = await fetch('/api/suppliers');
        const data = await response.json();
        
        if (data.success) {
            console.log('📊 Fournisseurs chargés:', data.data.length);
            
            // Vérifier les produits en attente
            let totalPending = 0;
            data.data.forEach(supplier => {
                const pendingCount = supplier.pending_products ? supplier.pending_products.length : 0;
                if (pendingCount > 0) {
                    console.log(`✅ ${supplier.name}: ${pendingCount} produits en attente`);
                    totalPending += pendingCount;
                }
            });
            
            console.log(`📈 Total produits en attente: ${totalPending}`);
            
            // Forcer le rechargement de l'interface
            suppliers = data.data;
            filteredSuppliers = data.data;
            renderSuppliers();
            
            // Afficher notification
            showNotification(`Rechargement forcé: ${totalPending} produits en attente trouvés`, 'success');
            
        } else {
            console.error('❌ Erreur API:', data.error);
        }
    } catch (error) {
        console.error('❌ Erreur rechargement:', error);
    }
} 