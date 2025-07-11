// FactureKiller V3 - Module Prix Simplifié

let currentPage = 1;
let currentFilters = {
    search: '',
    supplier: '',
    category: ''
};

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    console.log('🔧 Initialisation module Prix simplifié...');
    
    // Vérifier que les éléments existent
    if (!document.getElementById('pricesTable')) {
        console.error('❌ Element pricesTable non trouvé');
        return;
    }
    
    // Attendre un peu avant de charger pour laisser le temps aux autres scripts
    setTimeout(() => {
        loadSuppliers(); // Charger les fournisseurs d'abord
        initializeEventListeners();
        loadPrices();
        loadPendingProducts();
        updatePriceStatistics();
    }, 500);
    
    // Fonction debug globale pour tester le rechargement
    window.debugReloadPrices = () => {
        console.log('🔧 DEBUG: Rechargement forcé des prix...');
        loadPrices();
    };
});

// Charger les prix
async function loadPrices() {
    try {
        window.showGlobalProgress('Chargement des prix...');
        console.log('📊 Chargement des prix...');
        
        // Construire les paramètres avec les filtres
        const params = new URLSearchParams({
            page: currentPage,
            per_page: 50
        });
        
        if (currentFilters.search) {
            params.append('search', currentFilters.search);
        }
        if (currentFilters.supplier) {
            params.append('supplier', currentFilters.supplier);
        }
        if (currentFilters.category) {
            params.append('category', currentFilters.category);
        }
        
        // Ajouter un cache-buster pour forcer le rechargement
        params.append('t', Date.now());
        
        const response = await fetch(`/api/prices?${params.toString()}`, {
            cache: 'no-cache',
            headers: {
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        });
        const data = await response.json();
        console.log('📊 Données reçues:', data);
        
        if (data && data.success) {
            displayPrices(data.data || []);
        } else {
            displayPrices([]);
        }
        window.hideGlobalProgress();
    } catch (error) {
        window.hideGlobalProgress();
        displayPrices([]);
    }
}

// Afficher les prix
function displayPrices(prices) {
    const tbody = document.querySelector('#pricesTable tbody');
    if (!tbody) {
        console.error('❌ Table tbody non trouvé');
        return;
    }
    
        if (!prices || prices.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center py-4 text-muted">
                    <i class="bi bi-inbox fs-1"></i>
                    <p class="mt-2">Aucun prix trouvé</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = prices.map(price => `
        <tr data-price-id="${price.id}">
            <td>
                <input type="checkbox" class="form-check-input price-checkbox" 
                       value="${price.id}" onchange="updateSelection()">
            </td>
            <td><code>${price.code || '-'}</code></td>
            <td>${price.produit || 'Produit'}</td>
            <td><span class="badge bg-secondary">${price.fournisseur || 'N/A'}</span></td>
            <td class="fw-bold">${formatPrice(price.prix || 0)}</td>
            <td>${price.unite || 'pièce'}</td>
            <td>${price.categorie || '-'}</td>
            <td>${formatDate(price.date_maj)}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="editPrice(${price.id})" title="Modifier ce produit">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deletePrice(${price.id})" 
                            title="Supprimer ce produit">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// Charger les produits en attente
async function loadPendingProducts() {
    try {
        console.log('⏳ Chargement produits en attente...');
        
        const response = await fetch('/api/prices/pending');
        const data = await response.json();
        console.log('⏳ Produits en attente:', data);
        
        if (data && data.success) {
            displayPendingProducts(data.data || []);
            
            const pendingCount = document.getElementById('pendingCount');
            if (pendingCount) {
                pendingCount.textContent = data.count || 0;
            }
        } else {
            displayPendingProducts([]);
        }
    } catch (error) {
        console.error('❌ Erreur chargement produits en attente:', error);
        displayPendingProducts([]);
    }
}

// Afficher les produits en attente
function displayPendingProducts(products) {
    const tbody = document.querySelector('#pendingTable tbody');
    if (!tbody) {
        console.error('❌ Table pending tbody non trouvé');
        return;
    }
    
    if (!products || products.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4 text-muted">
                    <i class="bi bi-check-circle fs-1"></i>
                    <p class="mt-2">Aucun produit en attente</p>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = products.map(product => `
        <tr data-product-id="${product.id}">
            <td><code>${product.code || '-'}</code></td>
            <td class="editable-name">${product.produit || 'Produit'}</td>
            <td><span class="badge bg-secondary">${product.fournisseur || 'N/A'}</span></td>
            <td class="editable-price fw-bold text-primary">${formatPrice(product.prix || 0)}</td>
            <td class="editable-unit">${product.unite || 'pièce'}</td>
            <td><small>${formatDateTime(product.date_ajout)}</small></td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-warning" onclick="editPendingProduct('${product.id}')" 
                            title="Modifier ce produit">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-success" onclick="validatePending('${product.id}')" 
                            title="Valider et ajouter aux prix de référence">
                        <i class="bi bi-check-lg"></i>
                    </button>
                    <button class="btn btn-danger" onclick="rejectPending('${product.id}')"
                            title="Rejeter ce produit">
                        <i class="bi bi-x-lg"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// Fonctions utilitaires simplifiées
function formatPrice(price) {
    if (!price && price !== 0) return '0,00 €';
    
    const numPrice = parseFloat(price);
    if (isNaN(numPrice)) return '0,00 €';
    
    return numPrice.toFixed(2).replace('.', ',') + ' €';
}

function formatDate(dateString) {
    if (!dateString) return '-';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('fr-FR');
    } catch (e) {
        return '-';
    }
}

function formatDateTime(dateString) {
    if (!dateString) return '-';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('fr-FR') + ' ' + date.toLocaleTimeString('fr-FR');
    } catch (e) {
        return '-';
    }
}

// Éditer un prix existant
async function editPrice(priceId) {
    try {
        const row = document.querySelector(`tr[data-price-id="${priceId}"]`);
        if (!row) return;
        
        const cells = row.querySelectorAll('td');
        
        // Remplir le modal avec les données actuelles
        document.getElementById('editPriceId').value = priceId;
        document.getElementById('editProductName').value = cells[1].textContent;
        
        // Extraire le prix (version simplifiée)
        const priceText = cells[3].textContent.replace(/[€\s]/g, '').replace(',', '.');
        document.getElementById('editPrice').value = parseFloat(priceText) || 0;
        document.getElementById('editUnit').value = cells[4].textContent;
        
        const modal = new bootstrap.Modal(document.getElementById('editPriceModal'));
        modal.show();
    } catch (error) {
        console.error('❌ Erreur édition prix:', error);
        showNotification('Erreur lors de l\'édition', 'error');
    }
}

// Mettre à jour un prix existant
async function updatePrice() {
    try {
        const priceId = document.getElementById('editPriceId').value;
        const productName = document.getElementById('editProductName').value.trim();
        const price = parseFloat(document.getElementById('editPrice').value);
        const unit = document.getElementById('editUnit').value;
        
        console.log('🔄 Mise à jour prix:', { priceId, productName, price, unit });
        
        if (!productName || price <= 0) {
            showNotification('Nom et prix requis (prix > 0)', 'warning');
            return;
        }
        
        const requestData = {
            produit: productName,
            prix: price,
            unite: unit
        };
        
        console.log('📤 Envoi requête PUT:', requestData);
        
        const response = await fetch(`/api/prices/${priceId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        
        const data = await response.json();
        console.log('📥 Réponse serveur:', data);
        
        if (data && data.success) {
            showNotification('Prix mis à jour avec succès', 'success');
            
            // Fermer le modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('editPriceModal'));
            if (modal) {
                modal.hide();
            }
            
            console.log('🔄 Rechargement des données...');
            
            // Recharger les données avec un délai pour être sûr
            setTimeout(() => {
                loadPrices();
                updatePriceStatistics();
            }, 100);
            
        } else {
            showNotification(data.message || 'Erreur lors de la mise à jour', 'error');
        }
        
    } catch (error) {
        console.error('❌ Erreur mise à jour prix:', error);
        showNotification('Erreur lors de la mise à jour', 'error');
    }
}

// Valider un produit en attente
async function validatePending(pendingId) {
    try {
        const response = await fetch(`/api/prices/pending/${pendingId}/validate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        
        const data = await response.json();
        
        if (data && data.success) {
            showNotification('Produit validé et ajouté aux prix de référence', 'success');
            loadPendingProducts();
            loadPrices();
            updatePriceStatistics();
        } else {
            showNotification('Erreur lors de la validation', 'error');
        }
    } catch (error) {
        console.error('❌ Erreur validation:', error);
        showNotification('Erreur lors de la validation', 'error');
    }
}

// Rejeter un produit en attente
async function rejectPending(pendingId) {
    if (!confirm('Êtes-vous sûr de vouloir rejeter ce produit ?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/prices/pending/${pendingId}/reject`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data && data.success) {
            showNotification('Produit rejeté', 'info');
            loadPendingProducts();
        } else {
            showNotification('Erreur lors du rejet', 'error');
        }
    } catch (error) {
        console.error('❌ Erreur rejet:', error);
        showNotification('Erreur lors du rejet', 'error');
    }
}

// Éditer un produit en attente (simplifié)
async function editPendingProduct(pendingId) {
    try {
        const row = document.querySelector(`tr[data-product-id="${pendingId}"]`);
        if (!row) return;
        
        const nameCell = row.querySelector('.editable-name');
        const priceCell = row.querySelector('.editable-price');
        const unitCell = row.querySelector('.editable-unit');
        const actionCell = row.querySelector('td:last-child');
        
        // Récupérer les valeurs actuelles (version simplifiée)
        const currentName = nameCell.textContent.trim();
        const currentPrice = priceCell.textContent.replace(/[€\s]/g, '').replace(',', '.');
        const currentUnit = unitCell.textContent.trim();
        
        // Remplacer par des inputs
        nameCell.innerHTML = `<input type="text" class="form-control form-control-sm" value="${currentName}" id="edit-name-${pendingId}">`;
        priceCell.innerHTML = `<input type="number" class="form-control form-control-sm" value="${parseFloat(currentPrice) || 0}" step="0.01" id="edit-price-${pendingId}">`;
        unitCell.innerHTML = `
            <select class="form-select form-select-sm" id="edit-unit-${pendingId}">
                <option value="pièce" ${currentUnit === 'pièce' ? 'selected' : ''}>pièce</option>
                <option value="kg" ${currentUnit === 'kg' ? 'selected' : ''}>kg</option>
                <option value="litre" ${currentUnit === 'litre' ? 'selected' : ''}>litre</option>
                <option value="unité" ${currentUnit === 'unité' ? 'selected' : ''}>unité</option>
            </select>
        `;
        
        // Modifier les boutons
        actionCell.innerHTML = `
            <div class="btn-group btn-group-sm">
                <button class="btn btn-success" onclick="savePendingEdit('${pendingId}')" title="Sauvegarder">
                    <i class="bi bi-check"></i>
                </button>
                <button class="btn btn-secondary" onclick="cancelPendingEdit('${pendingId}')" title="Annuler">
                    <i class="bi bi-x"></i>
                </button>
            </div>
        `;
        
    } catch (error) {
        console.error('❌ Erreur lors de l\'édition:', error);
        showNotification('Erreur lors de l\'édition', 'error');
    }
}

// Sauvegarder l'édition d'un produit en attente
async function savePendingEdit(pendingId) {
    try {
        const nameInput = document.getElementById(`edit-name-${pendingId}`);
        const priceInput = document.getElementById(`edit-price-${pendingId}`);
        const unitInput = document.getElementById(`edit-unit-${pendingId}`);
        
        if (!nameInput || !priceInput || !unitInput) {
            console.error('❌ Inputs non trouvés');
            return;
        }
        
        const name = nameInput.value.trim();
        const price = parseFloat(priceInput.value);
        const unit = unitInput.value;
        
        if (!name || price <= 0) {
            showNotification('Nom et prix requis (prix > 0)', 'warning');
            return;
        }
        
        const response = await fetch(`/api/prices/pending/${pendingId}/update`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                produit: name,
                prix: price,
                unite: unit
            })
        });
        
        const data = await response.json();
        
        if (data && data.success) {
            showNotification('Produit mis à jour avec succès', 'success');
            loadPendingProducts();
        } else {
            showNotification('Erreur lors de la mise à jour', 'error');
        }
        
    } catch (error) {
        console.error('❌ Erreur sauvegarde:', error);
        showNotification('Erreur lors de la sauvegarde', 'error');
    }
}

// Annuler l'édition
function cancelPendingEdit(pendingId) {
    console.log('❌ Annulation édition pour:', pendingId);
    loadPendingProducts();
}

// Mettre à jour les statistiques
async function updatePriceStatistics() {
    try {
        const allPricesResponse = await fetch('/api/prices?per_page=99999');
        const pendingResponse = await fetch('/api/prices/pending');
        
        const allPricesData = await allPricesResponse.json();
        const pendingData = await pendingResponse.json();
        
        if (allPricesData && allPricesData.data) {
            const prices = allPricesData.data || [];
            
            // Total produits
            const totalElement = document.getElementById('totalProductsCount');
            if (totalElement) {
                totalElement.textContent = prices.length;
            }
            
            // Compter les fournisseurs uniques
            const suppliers = [...new Set(prices.map(p => p.fournisseur).filter(f => f))];
            const suppliersElement = document.getElementById('suppliersCount');
            if (suppliersElement) {
                suppliersElement.textContent = suppliers.length;
            }
        }
        
        // Produits en attente
        if (pendingData && pendingData.data) {
            const pendingCount = pendingData.count || 0;
            const pendingElement = document.getElementById('pendingStatsCount');
            if (pendingElement) {
                pendingElement.textContent = pendingCount;
            }
        }
    } catch (error) {
        console.error('❌ Erreur chargement statistiques:', error);
    }
}

// Fonction de notification simple
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Charger la liste des fournisseurs
async function loadSuppliers() {
    try {
        console.log('📋 Chargement des fournisseurs...');
        
        const response = await fetch('/api/prices/suppliers');
        const data = await response.json();
        
        if (data && data.success) {
            updateSuppliersFilter(data.data || []);
        } else {
            console.error('❌ Erreur chargement fournisseurs:', data);
        }
    } catch (error) {
        console.error('❌ Erreur chargement fournisseurs:', error);
    }
}

// Mettre à jour le filtre des fournisseurs
function updateSuppliersFilter(suppliers) {
    const supplierFilter = document.getElementById('supplierFilter');
    if (!supplierFilter) return;
    
    // Sauvegarder la valeur actuelle
    const currentValue = supplierFilter.value;
    
    // Vider le select et ajouter l'option par défaut
    supplierFilter.innerHTML = '<option value="">Tous les fournisseurs</option>';
    
    // Ajouter chaque fournisseur
    suppliers.forEach(supplier => {
        const option = document.createElement('option');
        option.value = supplier;
        option.textContent = supplier;
        if (supplier === currentValue) {
            option.selected = true;
        }
        supplierFilter.appendChild(option);
    });
    
    console.log(`📋 ${suppliers.length} fournisseurs chargés:`, suppliers);
}

// Initialiser les listeners des filtres
function initializeEventListeners() {
    // Filtre par fournisseur
    const supplierFilter = document.getElementById('supplierFilter');
    if (supplierFilter) {
        supplierFilter.addEventListener('change', () => {
            currentFilters.supplier = supplierFilter.value;
            currentPage = 1;
            loadPrices();
        });
    }
    
    // Filtre par recherche
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(() => {
            currentFilters.search = searchInput.value;
            currentPage = 1;
            loadPrices();
        }, 300));
    }
    
    // Filtre par catégorie
    const categoryFilter = document.getElementById('categoryFilter');
    if (categoryFilter) {
        categoryFilter.addEventListener('change', () => {
            currentFilters.category = categoryFilter.value;
            currentPage = 1;
            loadPrices();
        });
    }
    
    // Sélection multiple
    const selectAllPrices = document.getElementById('selectAllPrices');
    if (selectAllPrices) {
        selectAllPrices.addEventListener('change', toggleSelectAll);
    }
}

// Fonction debounce pour éviter trop de requêtes
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Supprimer un prix de référence
async function deletePrice(priceId) {
    try {
        // Récupérer le nom du produit pour l'affichage
        const row = event.target.closest('tr');
        const productName = row.cells[1].textContent;
        
        // Demander confirmation avec option cascade
        const result = await showDeleteConfirmation(productName);
        
        if (!result.confirmed) {
            return;
        }
        
        const cascade = result.cascade;
        const url = `/api/prices/${priceId}${cascade ? '?cascade=true' : ''}`;
        
        const response = await fetch(url, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data && data.success) {
            if (cascade && data.stats) {
                const stats = data.stats;
                let message = `Produit "${stats.product_name}" supprimé avec succès!\n\n`;
                message += `📊 Éléments supprimés:\n`;
                message += `• Prix de référence: ${stats.deleted_references}\n`;
                message += `• Produits en attente: ${stats.deleted_pending}\n`;
                message += `• Factures contenant ce produit: ${stats.deleted_invoices}`;
                
                showNotification(message.replace(/\n/g, '<br>'), 'success');
            } else {
                showNotification(data.message || 'Produit supprimé avec succès', 'success');
            }
            
            // Recharger les données
            loadPrices();
            loadPendingProducts();
            updatePriceStatistics();
            
            // Recharger les fournisseurs si suppression cascade
            if (cascade) {
                loadSuppliers();
            }
        } else {
            showNotification(data.error || 'Erreur lors de la suppression', 'error');
        }
    } catch (error) {
        console.error('❌ Erreur suppression prix:', error);
        showNotification('Erreur lors de la suppression', 'error');
    }
}

// Afficher une confirmation de suppression avec option cascade
function showDeleteConfirmation(productName) {
    return new Promise((resolve) => {
        const modalHtml = `
            <div class="modal fade" id="deleteConfirmModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header bg-danger text-white">
                            <h5 class="modal-title">
                                <i class="bi bi-exclamation-triangle"></i> Supprimer le produit
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p><strong>Produit à supprimer :</strong> ${productName}</p>
                            
                            <div class="alert alert-warning">
                                <i class="bi bi-info-circle"></i>
                                <strong>Options de suppression :</strong>
                            </div>
                            
                            <div class="form-check">
                                <input class="form-check-input" type="radio" name="deleteOption" id="deleteSimple" value="simple" checked>
                                <label class="form-check-label" for="deleteSimple">
                                    <strong>Suppression simple</strong><br>
                                    <small class="text-muted">Désactive seulement le prix de référence</small>
                                </label>
                            </div>
                            
                            <div class="form-check mt-2">
                                <input class="form-check-input" type="radio" name="deleteOption" id="deleteCascade" value="cascade">
                                <label class="form-check-label" for="deleteCascade">
                                    <strong>Suppression complète (CASCADE)</strong><br>
                                    <small class="text-danger">⚠️ Supprime TOUT : prix de référence + produits en attente + factures contenant ce produit</small>
                                </label>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
                            <button type="button" class="btn btn-danger" id="confirmDeleteBtn">
                                <i class="bi bi-trash"></i> Supprimer
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Ajouter la modal au DOM
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
        const confirmBtn = document.getElementById('confirmDeleteBtn');
        
        // Gérer la fermeture de la modal
        let resolved = false;
        
        confirmBtn.addEventListener('click', () => {
            const cascade = document.getElementById('deleteCascade').checked;
            resolved = true;
            modal.hide();
            resolve({ confirmed: true, cascade });
        });
        
        document.getElementById('deleteConfirmModal').addEventListener('hidden.bs.modal', () => {
            if (!resolved) {
                resolve({ confirmed: false, cascade: false });
            }
            document.getElementById('deleteConfirmModal').remove();
        });
        
        modal.show();
    });
}

// Export des fonctions globales
window.editPrice = editPrice;
window.deletePrice = deletePrice;
window.validatePending = validatePending;
window.rejectPending = rejectPending;
window.editPendingProduct = editPendingProduct;
window.savePendingEdit = savePendingEdit;
window.cancelPendingEdit = cancelPendingEdit;
window.loadSuppliers = loadSuppliers;

// Fonction pour réinitialiser les filtres
function resetFilters() {
    // Réinitialiser les variables
    currentFilters = {
        search: '',
        supplier: '',
        category: ''
    };
    currentPage = 1;
    
    // Réinitialiser les éléments de l'interface
    const searchInput = document.getElementById('searchInput');
    if (searchInput) searchInput.value = '';
    
    const supplierFilter = document.getElementById('supplierFilter');
    if (supplierFilter) supplierFilter.value = '';
    
    const categoryFilter = document.getElementById('categoryFilter');
    if (categoryFilter) categoryFilter.value = '';
    
    // Recharger les données
    loadPrices();
}

// Export de la fonction reset
window.resetFilters = resetFilters;

// === FONCTIONS DE SÉLECTION MULTIPLE ===

// Mettre à jour l'état de la sélection
function updateSelection() {
    const checkboxes = document.querySelectorAll('.price-checkbox');
    const checkedBoxes = document.querySelectorAll('.price-checkbox:checked');
    const selectAll = document.getElementById('selectAllPrices');
    const bulkActions = document.getElementById('bulkActions');
    const selectedCount = document.getElementById('selectedCount');
    
    // Mettre à jour le compteur
    if (selectedCount) {
        selectedCount.textContent = checkedBoxes.length;
    }
    
    // Afficher/masquer les actions en masse
    if (bulkActions) {
        bulkActions.style.display = checkedBoxes.length > 0 ? 'block' : 'none';
    }
    
    // Mettre à jour l'état du "Tout sélectionner"
    if (selectAll) {
        if (checkedBoxes.length === 0) {
            selectAll.indeterminate = false;
            selectAll.checked = false;
        } else if (checkedBoxes.length === checkboxes.length) {
            selectAll.indeterminate = false;
            selectAll.checked = true;
        } else {
            selectAll.indeterminate = true;
        }
    }
}

// Sélectionner/désélectionner tout
function toggleSelectAll() {
    const checkboxes = document.querySelectorAll('.price-checkbox');
    const selectAll = document.getElementById('selectAllPrices');
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAll.checked;
    });
    
    updateSelection();
}

// Annuler la sélection
function clearSelection() {
    const checkboxes = document.querySelectorAll('.price-checkbox');
    const selectAll = document.getElementById('selectAllPrices');
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    
    if (selectAll) {
        selectAll.checked = false;
        selectAll.indeterminate = false;
    }
    
    updateSelection();
}

// Obtenir les IDs sélectionnés
function getSelectedPriceIds() {
    const checkedBoxes = document.querySelectorAll('.price-checkbox:checked');
    return Array.from(checkedBoxes).map(checkbox => parseInt(checkbox.value));
}

// Modifier en masse
async function bulkEditPrices() {
    const selectedIds = getSelectedPriceIds();
    
    if (selectedIds.length === 0) {
        showNotification('Aucun produit sélectionné', 'warning');
        return;
    }
    
    // Pour l'instant, on modifie le premier sélectionné
    // TODO: Créer un modal de modification en masse
    const firstId = selectedIds[0];
    editPrice(firstId);
    
    showNotification(`${selectedIds.length} produit(s) sélectionné(s). Modification du premier...`, 'info');
}

// Supprimer en masse
async function bulkDeletePrices() {
    const selectedIds = getSelectedPriceIds();
    
    if (selectedIds.length === 0) {
        showNotification('Aucun produit sélectionné', 'warning');
        return;
    }
    
    const confirmMessage = `Êtes-vous sûr de vouloir supprimer ${selectedIds.length} produit(s) ?
    
⚠️ Choisissez le type de suppression :
• SIMPLE : Désactive les produits (recommandé)
• CASCADE : Supprime tout (produits + factures + en attente)`;
    
    if (!confirm(confirmMessage)) {
        return;
    }
    
    const cascade = confirm('Suppression CASCADE (supprime tout) ?\n\nOK = CASCADE\nAnnuler = SIMPLE');
    
    let successCount = 0;
    let errorCount = 0;
    
    showNotification(`Suppression de ${selectedIds.length} produit(s) en cours...`, 'info');
    
    // Supprimer un par un
    for (const priceId of selectedIds) {
        try {
            const url = cascade ? 
                `/api/prices/${priceId}?cascade=true` : 
                `/api/prices/${priceId}`;
                
            const response = await fetch(url, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data && data.success) {
                successCount++;
            } else {
                errorCount++;
            }
        } catch (error) {
            console.error(`❌ Erreur suppression ${priceId}:`, error);
            errorCount++;
        }
    }
    
    // Résultats
    if (successCount > 0) {
        showNotification(`${successCount} produit(s) supprimé(s) avec succès`, 'success');
        clearSelection();
        loadPrices();
        loadSuppliers();
        updatePriceStatistics();
    }
    
    if (errorCount > 0) {
        showNotification(`${errorCount} erreur(s) lors de la suppression`, 'error');
    }
} 