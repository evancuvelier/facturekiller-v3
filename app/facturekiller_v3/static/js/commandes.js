// Gestion des Commandes FactureKiller V3 - Version Moderne

let orders = [];
let suppliers = [];
let currentSupplier = null;
let cart = [];
let currentPage = 1;
let totalPages = 1;

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    console.log('🛒 Initialisation Gestion Commandes V3...');
    
    loadOrders();
    loadSuppliers();
    setupEventListeners();
    updatePageTitle();
});

// Mettre à jour le titre de la page avec le nom du restaurant
function updatePageTitle(restaurantName = null) {
    const pageTitleElement = document.getElementById('pageTitle');
    if (pageTitleElement) {
        if (restaurantName) {
            pageTitleElement.textContent = `Commandes - ${restaurantName}`;
        } else {
            pageTitleElement.textContent = 'Commandes';
        }
    }
}

// Configuration des écouteurs d'événements
function setupEventListeners() {
    // Filtres et recherche
    document.getElementById('searchInput').addEventListener('input', debounce(applyFilters, 300));
    document.getElementById('filterSupplier').addEventListener('change', applyFilters);
    document.getElementById('filterStatus').addEventListener('change', applyFilters);
    document.getElementById('sortBy').addEventListener('change', applyFilters);
    
    // Date de livraison
    document.getElementById('orderDeliveryDate').addEventListener('change', validateDeliveryDate);
}

// Fonction de debounce pour la recherche
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

// Charger toutes les commandes
async function loadOrders(page = 1) {
    try {
        console.log(`📦 Chargement des commandes (page ${page})...`);
        
        const response = await fetch(`/api/restaurant/orders`);
        const result = await response.json();
        
        if (result.success) {
            let allOrders = result.data || [];
            
            // Appliquer les filtres côté client
            const supplier = document.getElementById('supplierFilter')?.value || '';
            const status = document.getElementById('statusFilter')?.value || '';
            const searchTerm = document.getElementById('searchInput')?.value.toLowerCase() || '';
            
            if (supplier) {
                allOrders = allOrders.filter(order => order.supplier === supplier);
            }
            
            if (status) {
                allOrders = allOrders.filter(order => order.status === status);
            }
            
            if (searchTerm) {
                allOrders = allOrders.filter(order => 
                    order.order_number?.toLowerCase().includes(searchTerm) ||
                    order.supplier?.toLowerCase().includes(searchTerm) ||
                    order.notes?.toLowerCase().includes(searchTerm)
                );
            }
            
            // 🎯 TRI PAR PRIORITÉ INTELLIGENTE
            const sortBy = document.getElementById('sortBy')?.value || 'priority';
            
            if (sortBy === 'priority') {
                // Tri par priorité (par défaut)
                allOrders.sort((a, b) => {
                    const priorityA = getOrderPriority(a);
                    const priorityB = getOrderPriority(b);
                    
                    // Si même priorité, trier par date de livraison puis par date de création
                    if (priorityA === priorityB) {
                        // Comparer les dates de livraison
                        const deliveryA = new Date(a.delivery_date || '9999-12-31');
                        const deliveryB = new Date(b.delivery_date || '9999-12-31');
                        
                        if (deliveryA.getTime() === deliveryB.getTime()) {
                            // Si même date de livraison, trier par date de création (plus récent en premier)
                            return new Date(b.created_at) - new Date(a.created_at);
                        }
                        
                        return deliveryA - deliveryB;
                    }
                    
                    // Tri par priorité (priorité 1 en premier)
                    return priorityA - priorityB;
                });
            } else {
                // Autres tris classiques
                switch (sortBy) {
                    case 'date_desc':
                        allOrders.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
                        break;
                    case 'date_asc':
                        allOrders.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
                        break;
                    case 'amount_desc':
                        allOrders.sort((a, b) => (b.total_amount || 0) - (a.total_amount || 0));
                        break;
                    case 'amount_asc':
                        allOrders.sort((a, b) => (a.total_amount || 0) - (b.total_amount || 0));
                        break;
                    case 'supplier':
                        allOrders.sort((a, b) => (a.supplier || '').localeCompare(b.supplier || ''));
                        break;
                }
            }
            
            // Pagination côté client
            const perPage = 10;
            totalPages = Math.ceil(allOrders.length / perPage);
            const startIndex = (page - 1) * perPage;
            const endIndex = startIndex + perPage;
            orders = allOrders.slice(startIndex, endIndex);
            currentPage = page;
            
            updateStats();
            renderOrders();
            updatePagination();
            
            // Mettre à jour le titre avec le nom du restaurant
            if (result.restaurant) {
                updatePageTitle(result.restaurant);
            }
            
            console.log(`✅ ${orders.length}/${allOrders.length} commandes affichées pour le restaurant ${result.restaurant}`);
        } else {
            console.error('❌ Erreur chargement commandes:', result.error);
            showNotification('Erreur lors du chargement des commandes: ' + result.error, 'error');
            
            // Si aucun restaurant sélectionné - afficher dans le tableau
            if (result.requires_restaurant) {
                const tableBody = document.querySelector('#ordersTable tbody');
                if (tableBody) {
                    tableBody.innerHTML = `
                        <tr>
                            <td colspan="7" class="text-center py-5">
                                <div class="alert alert-warning">
                                    <i class="bi bi-exclamation-triangle me-2"></i>
                                    ${result.error}
                                </div>
                            </td>
                        </tr>
                    `;
                }
            }
        }
    } catch (error) {
        console.error('❌ Erreur réseau:', error);
        showNotification('Erreur de connexion', 'error');
        
        // Affichage d'erreur dans le tableau
        const tableBody = document.querySelector('#ordersTable tbody');
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-5">
                        <div class="alert alert-warning">
                            <i class="bi bi-exclamation-triangle me-2"></i>
                            Impossible de charger les commandes. Vérifiez votre connexion.
                        </div>
                    </td>
                </tr>
            `;
        }
    }
}

// 🎯 FONCTION DE PRIORITÉ DES COMMANDES
function getOrderPriority(order) {
    const today = new Date();
    today.setHours(0, 0, 0, 0); // Début de journée
    
    const deliveryDate = order.delivery_date ? new Date(order.delivery_date) : null;
    if (deliveryDate) {
        deliveryDate.setHours(0, 0, 0, 0);
    }
    
    // 🔥 PRIORITÉ 1: Commandes "confirmées" - Action requise
    if (order.status === 'confirmed') {
        return 1;
    }
    
    // 📅 PRIORITÉ 2: Commandes avec date de livraison = aujourd'hui
    if (deliveryDate && deliveryDate.getTime() === today.getTime()) {
        return 2;
    }
    
    // ⏰ PRIORITÉ 3: Commandes avec date de livraison passée encore en statut "livraison"
    if (deliveryDate && deliveryDate < today && 
        (order.status === 'shipped' || order.status === 'in_delivery')) {
        return 3;
    }
    
    // 📋 PRIORITÉ 4: Autres commandes
    return 4;
}

// Charger les fournisseurs
async function loadSuppliers() {
    try {
        const response = await fetch('/api/restaurant/suppliers');
        const result = await response.json();
        
        if (result.success) {
            suppliers = result.data.map(supplier => ({
                name: supplier.name,
                email: supplier.email,
                validated_products: supplier.validated_count || 0
            }));
            updateSupplierSelects();
            console.log(`✅ ${suppliers.length} fournisseurs chargés`);
        } else {
            console.error('❌ Erreur chargement fournisseurs:', result.error);
        }
    } catch (error) {
        console.error('❌ Erreur chargement fournisseurs:', error);
    }
}

// Mettre à jour les selects de fournisseurs
function updateSupplierSelects() {
    const selects = ['orderSupplier', 'supplierFilter'];
    
    selects.forEach(selectId => {
        const select = document.getElementById(selectId);
        if (!select) return;
        
        // Garder l'option par défaut
        const defaultOption = select.querySelector('option[value=""]');
        select.innerHTML = '';
        if (defaultOption) {
            select.appendChild(defaultOption);
        }
        
        // Ajouter les fournisseurs
        suppliers.forEach(supplier => {
            const option = document.createElement('option');
            option.value = supplier.name;
            option.textContent = `${supplier.name} (${supplier.validated_products || 0} produits)`;
            select.appendChild(option);
        });
    });
}

// Mettre à jour les statistiques (si les éléments existent)
async function updateStats() {
    // Vérifier si les éléments de stats existent (pour compatibilité)
    const statsElements = [
        'totalOrders', 'totalAmount', 'pendingOrders', 
        'monthOrders', 'monthAmount', 'avgOrderAmount'
    ];
    
    const hasStatsElements = statsElements.some(id => document.getElementById(id) !== null);
    
    if (!hasStatsElements) {
        console.log('ℹ️ Éléments de statistiques non présents (design minimaliste)');
        return;
    }
    
    try {
        const response = await fetch('/api/orders/stats');
        const result = await response.json();
        
        if (result.success) {
            const stats = result.data;
            
            // Utiliser des vérifications sécurisées pour chaque élément
            const totalOrdersEl = document.getElementById('totalOrders');
            if (totalOrdersEl) totalOrdersEl.textContent = stats.total_orders || 0;
            
            const totalAmountEl = document.getElementById('totalAmount');
            if (totalAmountEl) totalAmountEl.textContent = (stats.total_amount || 0).toFixed(2);
            
            const pendingOrdersEl = document.getElementById('pendingOrders');
            if (pendingOrdersEl) pendingOrdersEl.textContent = stats.pending_orders || 0;
            
            const monthOrdersEl = document.getElementById('monthOrders');
            if (monthOrdersEl) monthOrdersEl.textContent = stats.month_orders || 0;
            
            const monthAmountEl = document.getElementById('monthAmount');
            if (monthAmountEl) monthAmountEl.textContent = (stats.month_amount || 0).toFixed(2);
            
            const avgOrderAmountEl = document.getElementById('avgOrderAmount');
            if (avgOrderAmountEl) avgOrderAmountEl.textContent = (stats.avg_order_amount || 0).toFixed(2) + '€';
        }
    } catch (error) {
        console.error('❌ Erreur stats commandes:', error);
        // Valeurs par défaut avec vérifications sécurisées
        const totalOrdersEl = document.getElementById('totalOrders');
        if (totalOrdersEl) totalOrdersEl.textContent = '0';
        
        const totalAmountEl = document.getElementById('totalAmount');
        if (totalAmountEl) totalAmountEl.textContent = '0.00';
        
        const pendingOrdersEl = document.getElementById('pendingOrders');
        if (pendingOrdersEl) pendingOrdersEl.textContent = '0';
        
        const monthOrdersEl = document.getElementById('monthOrders');
        if (monthOrdersEl) monthOrdersEl.textContent = '0';
        
        const monthAmountEl = document.getElementById('monthAmount');
        if (monthAmountEl) monthAmountEl.textContent = '0.00';
        
        const avgOrderAmountEl = document.getElementById('avgOrderAmount');
        if (avgOrderAmountEl) avgOrderAmountEl.textContent = '0.00€';
    }
}

// Appliquer les filtres
function applyFilters() {
    loadOrders(1);
}

// Réinitialiser les filtres
function resetFilters() {
    console.log('🔄 Réinitialisation des filtres...');
    
    // Reset des selects
    document.getElementById('searchInput').value = '';
    document.getElementById('supplierFilter').value = '';
    document.getElementById('statusFilter').value = '';
    document.getElementById('sortBy').value = 'priority';
    
    // Recharger les commandes
    loadOrders(1);
}

// Afficher les commandes
function renderOrders() {
    const tableBody = document.querySelector('#ordersTable tbody');
    const ordersCount = document.getElementById('ordersCount');
    
    if (!tableBody) {
        console.error('❌ Élément ordersTable tbody non trouvé');
        return;
    }
    
    // Mettre à jour le compteur
    if (ordersCount) {
        ordersCount.textContent = orders.length;
    }
    
    if (orders.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-5">
                    <i class="bi bi-cart-x fs-1 text-muted"></i>
                    <h4 class="mt-3 text-muted">Aucune commande trouvée</h4>
                    <p class="text-muted">Commencez par créer votre première commande</p>
                    <button class="btn btn-primary btn-lg" onclick="showNewOrderModal()">
                        <i class="bi bi-plus-circle me-2"></i>Nouvelle Commande
                    </button>
                </td>
            </tr>
        `;
        return;
    }
    
    // Générer les lignes du tableau
    const rows = orders.map(order => {
        const statusInfo = getStatusInfo(order.status);
        const createdDate = new Date(order.created_at).toLocaleDateString('fr-FR');
        const deliveryDate = order.delivery_date ? new Date(order.delivery_date).toLocaleDateString('fr-FR') : 'Non définie';
        
        // 🎯 CALCUL DE LA PRIORITÉ POUR LE TABLEAU
        const priority = getOrderPriority(order);
        let rowClass = '';
        let priorityBadge = '';
        
        switch (priority) {
            case 1: // 🔥 PRIORITÉ 1: Commandes confirmées
                rowClass = 'table-danger';
                priorityBadge = '<span class="badge bg-danger me-1"><i class="bi bi-exclamation-triangle-fill"></i> ACTION</span>';
                break;
            case 2: // 📅 PRIORITÉ 2: Livraison aujourd'hui
                rowClass = 'table-warning';
                priorityBadge = '<span class="badge bg-warning me-1"><i class="bi bi-truck"></i> AUJOURD\'HUI</span>';
                break;
            case 3: // ⏰ PRIORITÉ 3: Retard de livraison
                rowClass = 'table-warning';
                priorityBadge = '<span class="badge bg-secondary me-1"><i class="bi bi-clock-history"></i> RETARD</span>';
                break;
            default: // 📋 PRIORITÉ 4: Normal
                rowClass = '';
                priorityBadge = '';
                break;
        }
        
        return `
            <tr class="order-row ${rowClass}" onclick="showOrderDetails('${order.id}')" style="cursor: pointer;">
                <td>
                    ${priorityBadge}
                    <strong>${order.order_number}</strong>
                </td>
                <td>
                    <i class="bi bi-building me-2"></i>${order.supplier}
                </td>
                <td>
                    <i class="bi bi-calendar me-2"></i>${createdDate}
                </td>
                <td>
                    <i class="bi bi-truck me-2"></i>${deliveryDate}
                </td>
                <td>
                    <strong class="text-success">${order.total_amount?.toFixed(2) || '0.00'}€</strong>
                </td>
                <td>
                    <span class="badge bg-${statusInfo.color}">
                        <i class="bi bi-${statusInfo.icon} me-1"></i>${statusInfo.label}
                    </span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-primary" onclick="event.stopPropagation(); showOrderDetails('${order.id}')" title="Détails">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button class="btn btn-outline-warning" onclick="event.stopPropagation(); showStatusModal('${order.id}')" title="Changer statut">
                            <i class="bi bi-arrow-repeat"></i>
                        </button>
                        <button class="btn btn-outline-danger" onclick="event.stopPropagation(); deleteOrder('${order.id}', '${order.order_number}')" title="Supprimer">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
    
    tableBody.innerHTML = rows;
}

// Afficher une carte de commande
function renderOrderCard(order) {
    const statusInfo = getStatusInfo(order.status);
    const createdDate = new Date(order.created_at).toLocaleDateString('fr-FR');
    const deliveryDate = order.delivery_date ? 
        new Date(order.delivery_date).toLocaleDateString('fr-FR') : 'Non définie';
    
    // 🎯 CALCUL DE LA PRIORITÉ ET INDICATEURS VISUELS
    const priority = getOrderPriority(order);
    const today = new Date().toDateString();
    const orderDeliveryDate = order.delivery_date ? new Date(order.delivery_date).toDateString() : null;
    const isDeliveryToday = orderDeliveryDate === today;
    const canBeVerified = isDeliveryToday && (order.status === 'sent' || order.status === 'confirmed' || order.status === 'shipped');
    
    // Indicateurs de priorité
    let priorityBadge = '';
    let cardBorder = '';
    let cardBg = '';
    
    switch (priority) {
        case 1: // 🔥 PRIORITÉ 1: Commandes confirmées
            priorityBadge = '<span class="badge bg-danger fs-6 me-2 text-white"><i class="bi bi-exclamation-triangle-fill me-1"></i>ACTION REQUISE</span>';
            cardBorder = 'border-danger border-3';
            cardBg = 'bg-danger bg-opacity-5';
            break;
        case 2: // 📅 PRIORITÉ 2: Livraison aujourd'hui
            priorityBadge = '<span class="badge bg-warning fs-6 me-2"><i class="bi bi-truck me-1"></i>LIVRAISON AUJOURD\'HUI</span>';
            cardBorder = 'border-warning border-2';
            cardBg = 'bg-warning bg-opacity-10';
            break;
        case 3: // ⏰ PRIORITÉ 3: Retard de livraison
            priorityBadge = '<span class="badge bg-warning fs-6 me-2"><i class="bi bi-clock-history me-1"></i>RETARD LIVRAISON</span>';
            cardBorder = 'border-warning border-2';
            break;
        default: // 📋 PRIORITÉ 4: Normal
            cardBorder = '';
            break;
    }
    
    return `
        <div class="card mb-3 shadow-sm ${cardBorder}">
            <div class="card-header ${cardBg}">
                <div class="row align-items-center">
                    <div class="col">
                        ${priorityBadge}
                        <h5 class="mb-0 ${priority === 1 ? 'fw-bold' : ''}">
                            <i class="bi bi-receipt me-2 text-primary"></i>
                            ${order.order_number}
                            <span class="badge bg-${statusInfo.color} ms-2">
                                <i class="bi bi-${statusInfo.icon} me-1"></i>
                                ${statusInfo.label}
                            </span>
                            ${order.status === 'pending' ? '<span class="badge bg-danger ms-2"><i class="bi bi-envelope-x me-1"></i>Email non envoyé</span>' : ''}
                        </h5>
                        <small class="text-muted">
                            <i class="bi bi-building me-1"></i>${order.supplier} • 
                            <i class="bi bi-calendar me-1"></i>Créée le ${createdDate}
                            ${order.status === 'pending' ? '<br><span class="text-warning"><i class="bi bi-exclamation-triangle me-1"></i>Utilisez le bouton Email pour envoyer la commande</span>' : ''}
                        </small>
                    </div>
                    <div class="col-auto">
                        <div class="btn-group">
                            <button class="btn btn-sm btn-outline-primary" onclick="showOrderDetails('${order.id}')">
                                <i class="bi bi-eye"></i> Voir
                            </button>
                            <button class="btn btn-sm btn-outline-success" onclick="sendOrderEmail('${order.id}', '${order.supplier}')" title="Envoyer par email au fournisseur">
                                <i class="bi bi-envelope"></i> Email
                            </button>
                            <button class="btn btn-sm btn-outline-warning" onclick="showStatusModal('${order.id}')">
                                <i class="bi bi-arrow-repeat"></i> Statut
                            </button>
                            ${order.status === 'sent' ? `
                                <button class="btn btn-sm btn-outline-danger" onclick="deleteOrder('${order.id}', '${order.order_number}')" title="Supprimer cette commande envoyée">
                                    <i class="bi bi-trash"></i> Supprimer
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-3">
                        <small class="text-muted">Montant total</small>
                        <div class="h5 text-success">${(order.total_amount || 0).toFixed(2)}€</div>
                    </div>
                    <div class="col-md-3">
                        <small class="text-muted">Articles</small>
                        <div class="h6">${order.items_count || 0} produit(s)</div>
                    </div>
                    <div class="col-md-3">
                        <small class="text-muted">Livraison prévue</small>
                        <div class="h6 ${isDeliveryToday ? 'text-warning fw-bold' : ''}">${deliveryDate}</div>
                    </div>
                    <div class="col-md-3">
                        <small class="text-muted">Dernière MAJ</small>
                        <div class="h6">${formatRelativeTime(order.updated_at || order.created_at)}</div>
                    </div>
                </div>
                ${order.notes ? `<div class="mt-2"><small class="text-muted"><i class="bi bi-sticky me-1"></i>${order.notes}</small></div>` : ''}
                
                ${getDeliveryVerificationButtons(order)}
            </div>
        </div>
    `;
}

// Informations de statut
function getStatusInfo(status) {
    const statusMap = {
        'draft': { label: 'Brouillon', color: 'secondary', icon: 'pencil' },
        'pending': { label: 'En attente', color: 'warning', icon: 'clock' },
        'sent': { label: 'Envoyée', color: 'info', icon: 'send' },
        'confirmed': { label: 'Confirmée', color: 'primary', icon: 'check-circle' },
        'preparing': { label: 'En préparation', color: 'info', icon: 'gear' },
        'shipped': { label: 'Expédiée', color: 'primary', icon: 'truck' },
        'delivered': { label: 'Livrée ✓', color: 'success', icon: 'check-all' },
        'delivered_with_issues': { label: 'Livrée avec différences', color: 'warning', icon: 'exclamation-triangle' },
        'invoiced': { label: 'Facturée', color: 'success', icon: 'receipt' },
        'paid': { label: 'Payée', color: 'success', icon: 'credit-card' },
        'cancelled': { label: 'Annulée', color: 'danger', icon: 'x-circle' }
    };
    
    return statusMap[status] || { label: status, color: 'secondary', icon: 'question' };
}

// Mettre à jour la pagination
function updatePagination() {
    const container = document.getElementById('ordersPagination');
    
    if (!container) {
        console.error('❌ Élément ordersPagination non trouvé');
        return;
    }
    
    if (totalPages <= 1) {
        container.classList.add('d-none');
        return;
    }
    
    container.classList.remove('d-none');
    
    let paginationHtml = '<nav aria-label="Navigation des commandes"><ul class="pagination justify-content-center">';
    
    // Bouton précédent
    paginationHtml += `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
        <a class="page-link" href="#" onclick="loadOrders(${currentPage - 1}); return false;">Précédent</a>
    </li>`;
    
    // Pages
    for (let i = 1; i <= totalPages; i++) {
        if (i === currentPage) {
            paginationHtml += `<li class="page-item active">
                <span class="page-link">${i}</span>
            </li>`;
        } else {
            paginationHtml += `<li class="page-item">
                <a class="page-link" href="#" onclick="loadOrders(${i}); return false;">${i}</a>
            </li>`;
        }
    }
    
    // Bouton suivant
    paginationHtml += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
        <a class="page-link" href="#" onclick="loadOrders(${currentPage + 1}); return false;">Suivant</a>
    </li>`;
    
    paginationHtml += '</ul></nav>';
    
    container.innerHTML = paginationHtml;
}

// === NOUVELLE COMMANDE ===

// Afficher le modal de nouvelle commande
function showNewOrderModal() {
    console.log('🛒 Ouverture modal nouvelle commande');
    
    // Reset du formulaire
    resetOrderForm();
    
    // Afficher le modal
    const modal = new bootstrap.Modal(document.getElementById('newOrderModal'));
    modal.show();
}

// Reset du formulaire de commande
function resetOrderForm() {
    document.getElementById('orderSupplier').value = '';
    document.getElementById('orderDeliveryDate').value = '';
    document.getElementById('orderNotes').value = '';
    
    // Reset des conteneurs
    document.getElementById('supplierInfo').classList.add('d-none');
    document.getElementById('cartContainer').classList.add('d-none');
    
    // Reset des données
    currentSupplier = null;
    cart = [];
    
    // Reset de l'affichage
    document.getElementById('supplierProductsContainer').innerHTML = `
        <div class="text-center text-muted py-5">
            <i class="bi bi-arrow-up fs-1 text-muted"></i>
            <h5 class="mt-3 text-muted">Sélectionnez un fournisseur</h5>
            <p class="text-muted">pour voir ses produits disponibles</p>
        </div>
    `;
    
    document.getElementById('deliveryInfo').innerHTML = `
        <small class="text-muted">💡 Sélectionnez d'abord un fournisseur pour voir ses jours de livraison</small>
    `;
    
    updateCartDisplay();
    updateSaveButton();
}

// Charger les produits du fournisseur
async function loadSupplierProducts() {
    const supplierName = document.getElementById('orderSupplier').value;
    
    if (!supplierName) {
        resetOrderForm();
        return;
    }
    
    try {
        console.log(`📦 Chargement produits fournisseur: ${supplierName}`);
        
        const response = await fetch(`/api/suppliers/${encodeURIComponent(supplierName)}/products`);
        const result = await response.json();
        
        if (result.success) {
            currentSupplier = suppliers.find(s => s.name === supplierName);
            const products = result.data;
            
            // Afficher les infos fournisseur
            displaySupplierInfo(currentSupplier, products.length);
            
            // Afficher les jours de livraison
            displayDeliveryInfo(currentSupplier);
            
            // Afficher les produits
            displaySupplierProducts(products);
            
            console.log(`✅ ${products.length} produits chargés`);
        } else {
            console.error('❌ Erreur chargement produits:', result.error);
            showNotification('Erreur lors du chargement des produits', 'error');
        }
    } catch (error) {
        console.error('❌ Erreur réseau:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

// Afficher les informations du fournisseur
function displaySupplierInfo(supplier, productCount) {
    const infoContainer = document.getElementById('supplierInfo');
    const nameElement = document.getElementById('supplierInfoName');
    const detailsElement = document.getElementById('supplierInfoDetails');
    
    nameElement.textContent = supplier.name;
    detailsElement.innerHTML = `
        <i class="bi bi-box-seam me-1"></i>${productCount} produits disponibles
        ${supplier.email ? `<br><i class="bi bi-envelope me-1"></i>${supplier.email}` : ''}
        ${supplier.notes ? `<br><i class="bi bi-sticky me-1"></i>${supplier.notes}` : ''}
    `;
    
    infoContainer.classList.remove('d-none');
}

// Afficher les informations de livraison
function displayDeliveryInfo(supplier) {
    const deliveryInfo = document.getElementById('deliveryInfo');
    
    if (supplier.delivery_days && supplier.delivery_days.length > 0) {
        const days = supplier.delivery_days.map(day => {
            const dayNames = {
                'monday': 'Lundi', 'tuesday': 'Mardi', 'wednesday': 'Mercredi',
                'thursday': 'Jeudi', 'friday': 'Vendredi', 'saturday': 'Samedi', 'sunday': 'Dimanche'
            };
            return dayNames[day] || day;
        });
        
        deliveryInfo.innerHTML = `
            <div class="alert alert-success alert-sm">
                <i class="bi bi-truck me-2"></i>
                <strong>Jours de livraison:</strong> ${days.join(', ')}
            </div>
            <small class="text-muted">💡 Choisissez une date correspondant à un jour de livraison</small>
        `;
    } else {
        deliveryInfo.innerHTML = `
            <div class="alert alert-info alert-sm">
                <i class="bi bi-info-circle me-2"></i>
                Aucun jour de livraison spécifié pour ce fournisseur
            </div>
        `;
    }
}

// Afficher les produits du fournisseur
function displaySupplierProducts(products) {
    const container = document.getElementById('supplierProductsContainer');
    
    if (products.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="bi bi-box fs-1"></i>
                <h5 class="mt-3">Aucun produit disponible</h5>
                <p>Ce fournisseur n'a pas encore de produits validés</p>
            </div>
        `;
        return;
    }
    
    // Initialiser le panier avec tous les produits à quantité 0
    initializeCartWithAllProducts(products);
    
    // Masquer l'affichage des produits individuels car tout est maintenant dans le panier
    container.innerHTML = `
        <div class="text-center text-success py-4">
            <i class="bi bi-check-circle fs-1"></i>
            <h5 class="mt-3">Produits chargés avec succès</h5>
            <p>Tous les produits sont maintenant disponibles dans le panier ci-dessous</p>
            <small class="text-muted">Ajustez les quantités avec les boutons +/-</small>
        </div>
    `;
}

// Initialiser le panier avec tous les produits à quantité 0
function initializeCartWithAllProducts(products) {
    cart = []; // Vider le panier actuel
    
    // Ajouter tous les produits avec quantité 0
    products.forEach(product => {
        cart.push({
            id: product.id,
            name: product.name,
            code: product.code,
            unit_price: parseFloat(product.unit_price),
            unit: product.unit,
            category: product.category || 'Autres',
            quantity: 0
        });
    });
    
    // Trier par catégorie puis par nom
    cart.sort((a, b) => {
        if (a.category !== b.category) {
            return a.category.localeCompare(b.category);
        }
        return a.name.localeCompare(b.name);
    });
    
    updateCartDisplay();
    updateSaveButton();
}

// Mettre à jour l'affichage du panier
function updateCartDisplay() {
    const cartContainer = document.getElementById('cartContainer');
    const cartItems = document.getElementById('cartItems');
    const cartItemCount = document.getElementById('cartItemCount');
    const orderTotal = document.getElementById('orderTotal');
    const totalItems = document.getElementById('totalItems');
    const footerTotal = document.getElementById('footerTotal');
    
    if (cart.length === 0) {
        cartContainer.classList.add('d-none');
        return;
    }
    
    cartContainer.classList.remove('d-none');
    
    // Grouper par catégorie
    const categories = {};
    cart.forEach((item, index) => {
        const category = item.category || 'Autres';
        if (!categories[category]) {
            categories[category] = [];
        }
        categories[category].push({...item, originalIndex: index});
    });
    
    // Afficher les articles par catégorie
    let html = '';
    Object.keys(categories).sort().forEach(category => {
        const categoryItems = categories[category];
        const hasItemsWithQuantity = categoryItems.some(item => item.quantity > 0);
        
        html += `
            <tr class="table-secondary">
                <td colspan="5">
                    <strong><i class="bi bi-tag me-2"></i>${category}</strong>
                    <span class="badge bg-primary ms-2">${categoryItems.length} produits</span>
                    ${hasItemsWithQuantity ? '<span class="badge bg-success ms-1">Sélectionnés</span>' : ''}
                </td>
            </tr>
        `;
        
        categoryItems.forEach(item => {
            const isSelected = item.quantity > 0;
            const rowClass = isSelected ? 'table-light' : '';
            
            html += `
                <tr class="${rowClass}">
                    <td>
                        <strong class="${isSelected ? 'text-success' : ''}">${item.name}</strong>
                        ${item.code ? `<br><small class="text-muted">Code: ${item.code}</small>` : ''}
                        ${isSelected ? '<i class="bi bi-check-circle text-success ms-2"></i>' : ''}
                    </td>
                    <td>
                        <span class="text-success">${item.unit_price.toFixed(2)}€</span>
                        ${item.unit ? `<small class="text-muted">/${item.unit}</small>` : ''}
                    </td>
                    <td>
                        <div class="input-group input-group-sm" style="width: 130px;">
                            <button class="btn btn-outline-secondary" onclick="updateQuantity(${item.originalIndex}, -1)">
                                <i class="bi bi-dash"></i>
                            </button>
                            <input type="number" class="form-control text-center ${isSelected ? 'border-success' : ''}" 
                                   value="${item.quantity}" min="0" onchange="setQuantity(${item.originalIndex}, this.value)">
                            <button class="btn btn-outline-secondary" onclick="updateQuantity(${item.originalIndex}, 1)">
                                <i class="bi bi-plus"></i>
                            </button>
                        </div>
                    </td>
                    <td>
                        <strong class="${isSelected ? 'text-success' : 'text-muted'}">${(item.unit_price * item.quantity).toFixed(2)}€</strong>
                    </td>
                    <td>
                        ${isSelected ? `
                            <button class="btn btn-sm btn-outline-warning" onclick="setQuantity(${item.originalIndex}, 0)" title="Remettre à zéro">
                                <i class="bi bi-arrow-counterclockwise"></i>
                            </button>
                        ` : `
                            <span class="text-muted">-</span>
                        `}
                    </td>
                </tr>
            `;
        });
    });
    
    cartItems.innerHTML = html;
    
    // Calculer le total
    const total = cart.reduce((sum, item) => sum + (item.unit_price * item.quantity), 0);
    const itemCount = cart.reduce((sum, item) => sum + item.quantity, 0);
    const selectedProducts = cart.filter(item => item.quantity > 0).length;
    
    cartItemCount.textContent = selectedProducts;
    orderTotal.textContent = total.toFixed(2) + '€';
    totalItems.textContent = itemCount;
    footerTotal.textContent = total.toFixed(2) + '€';
}

// Mettre à jour la quantité d'un produit
function updateQuantity(index, delta) {
    cart[index].quantity = Math.max(0, cart[index].quantity + delta);
    updateCartDisplay();
    updateSaveButton();
}

// Définir la quantité d'un produit
function setQuantity(index, value) {
    const quantity = parseInt(value) || 0;
    cart[index].quantity = Math.max(0, quantity);
    updateCartDisplay();
    updateSaveButton();
}

// Vider le panier (remettre toutes les quantités à 0)
function clearCart() {
    if (cart.length === 0) return;
    
    if (confirm('Êtes-vous sûr de vouloir remettre toutes les quantités à zéro ?')) {
        cart.forEach(item => item.quantity = 0);
        updateCartDisplay();
        updateSaveButton();
        
        showNotification('Toutes les quantités remises à zéro', 'info');
    }
}

// Valider la date de livraison
function validateDeliveryDate() {
    const dateInput = document.getElementById('orderDeliveryDate');
    const selectedDate = new Date(dateInput.value);
    
    if (!currentSupplier || !currentSupplier.delivery_days || currentSupplier.delivery_days.length === 0) {
        return; // Pas de restriction
    }
    
    const dayNames = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
    const selectedDay = dayNames[selectedDate.getDay()];
    
    if (!currentSupplier.delivery_days.includes(selectedDay)) {
        const deliveryInfo = document.getElementById('deliveryInfo');
        deliveryInfo.innerHTML = `
            <div class="alert alert-warning alert-sm">
                <i class="bi bi-exclamation-triangle me-2"></i>
                <strong>Attention:</strong> Cette date ne correspond pas aux jours de livraison du fournisseur
            </div>
        `;
    } else {
        displayDeliveryInfo(currentSupplier);
    }
}

// Mettre à jour le bouton de sauvegarde
function updateSaveButton() {
    const saveBtn = document.getElementById('saveOrderBtn');
    const hasSupplier = document.getElementById('orderSupplier').value;
    const hasProducts = cart.some(item => item.quantity > 0);
    
    saveBtn.disabled = !hasSupplier || !hasProducts;
}

// Sauvegarder la commande
async function saveOrder() {
    const supplierName = document.getElementById('orderSupplier').value;
    const deliveryDate = document.getElementById('orderDeliveryDate').value;
    const notes = document.getElementById('orderNotes').value;
    
    // Filtrer les produits avec quantité > 0
    const selectedItems = cart.filter(item => item.quantity > 0);
    
    if (!supplierName || selectedItems.length === 0) {
        showNotification('Veuillez sélectionner un fournisseur et ajouter des produits', 'error');
        return;
    }
    
    const orderData = {
        supplier: supplierName,
        delivery_date: deliveryDate || null,
        notes: notes,
        items: selectedItems.map(item => ({
            product_id: item.id,
            product_name: item.name,
            unit_price: item.unit_price,
            quantity: item.quantity,
            total: item.unit_price * item.quantity
        })),
        total_amount: selectedItems.reduce((sum, item) => sum + (item.unit_price * item.quantity), 0)
    };
    
    try {
        console.log('💾 Sauvegarde commande:', orderData);
        
        const response = await fetch('/api/orders', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(orderData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Commande créée avec succès', 'success');
            
            // Fermer le modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('newOrderModal'));
            modal.hide();
            
            // Recharger les commandes
            loadOrders();
            
            console.log('✅ Commande sauvegardée:', result.data);
            
            // Envoi automatique de l'email au fournisseur (seulement si les données sont disponibles)
            if (result.data && result.data.id && result.data.order_number) {
                const orderId = result.data.id;
                const orderNumber = result.data.order_number;
                
                showNotification('📧 Envoi de l\'email au fournisseur...', 'info');
                
                // Attendre un peu pour que l'interface se mette à jour
                setTimeout(async () => {
                    try {
                        await sendOrderEmailSilent(orderId, supplierName, orderNumber);
                    } catch (emailError) {
                        console.error('❌ Erreur envoi email automatique:', emailError);
                        showNotification(`⚠️ Commande ${orderNumber} créée mais email non envoyé - Utilisez le bouton Email pour renvoyer`, 'warning');
                    }
                }, 1000);
            } else {
                console.warn('⚠️ Données de commande incomplètes, email non envoyé automatiquement');
                showNotification('⚠️ Commande créée mais email non envoyé automatiquement - Utilisez le bouton Email', 'warning');
            }
        } else {
            console.error('❌ Erreur sauvegarde:', result.error);
            showNotification('Erreur lors de la création de la commande: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('❌ Erreur réseau:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

// === GESTION DES COMMANDES EXISTANTES ===

// Afficher les détails d'une commande
async function showOrderDetails(orderId) {
    try {
        const response = await fetch(`/api/orders/${orderId}`);
        const result = await response.json();
        
        if (result.success) {
            const order = result.data;
            
            // Remplir le modal
            document.getElementById('orderDetailsTitle').innerHTML = `
                <i class="bi bi-file-text me-2"></i>Commande ${order.order_number}
            `;
            
            document.getElementById('orderDetailsContent').innerHTML = renderOrderDetails(order);
            
            // Afficher le modal avec gestion d'accessibilité
            const modalElement = document.getElementById('orderDetailsModal');
            const modal = new bootstrap.Modal(modalElement);
            
            // Corriger les problèmes d'accessibilité
            modalElement.addEventListener('shown.bs.modal', function () {
                modalElement.removeAttribute('aria-hidden');
            });
            
            modalElement.addEventListener('hidden.bs.modal', function () {
                modalElement.setAttribute('aria-hidden', 'true');
            });
            
            modal.show();
        }
    } catch (error) {
        console.error('❌ Erreur détails commande:', error);
        showNotification('Erreur lors du chargement des détails', 'error');
    }
}

// Afficher le modal de changement de statut
function showStatusModal(orderId) {
    document.getElementById('statusOrderId').value = orderId;
    
    const modalElement = document.getElementById('statusModal');
    const modal = new bootstrap.Modal(modalElement);
    
    // Corriger les problèmes d'accessibilité
    modalElement.addEventListener('shown.bs.modal', function () {
        modalElement.removeAttribute('aria-hidden');
    });
    
    modalElement.addEventListener('hidden.bs.modal', function () {
        modalElement.setAttribute('aria-hidden', 'true');
    });
    
    modal.show();
}

// Mettre à jour le statut d'une commande
async function updateOrderStatus() {
    const orderId = document.getElementById('statusOrderId').value;
    const newStatus = document.getElementById('newStatus').value;
    const comment = document.getElementById('statusComment').value;
    
    try {
        const response = await fetch(`/api/orders/${orderId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                status: newStatus,
                comment: comment
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Statut mis à jour avec succès', 'success');
            
            // Fermer le modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('statusModal'));
            modal.hide();
            
            // Recharger les commandes
            loadOrders();
        } else {
            showNotification('Erreur lors de la mise à jour du statut', 'error');
        }
    } catch (error) {
        console.error('❌ Erreur mise à jour statut:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

// Afficher les détails d'une commande
function renderOrderDetails(order) {
    const statusInfo = getStatusInfo(order.status);
    const createdDate = new Date(order.created_at).toLocaleDateString('fr-FR');
    const deliveryDate = order.delivery_date ? 
        new Date(order.delivery_date).toLocaleDateString('fr-FR') : 'Non définie';
    
    return `
        <div class="row g-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0"><i class="bi bi-info-circle me-2"></i>Informations générales</h6>
                    </div>
                    <div class="card-body">
                        <dl class="row">
                            <dt class="col-sm-4">N° Commande:</dt>
                            <dd class="col-sm-8">${order.order_number}</dd>
                            
                            <dt class="col-sm-4">Fournisseur:</dt>
                            <dd class="col-sm-8">${order.supplier}</dd>
                            
                            <dt class="col-sm-4">Statut:</dt>
                            <dd class="col-sm-8">
                                <span class="badge bg-${statusInfo.color}">
                                    <i class="bi bi-${statusInfo.icon} me-1"></i>
                                    ${statusInfo.label}
                                </span>
                            </dd>
                            
                            <dt class="col-sm-4">Créée le:</dt>
                            <dd class="col-sm-8">${createdDate}</dd>
                            
                            <dt class="col-sm-4">Livraison:</dt>
                            <dd class="col-sm-8">${deliveryDate}</dd>
                            
                            <dt class="col-sm-4">Montant total:</dt>
                            <dd class="col-sm-8"><strong class="text-success">${(order.total_amount || 0).toFixed(2)}€</strong></dd>
                        </dl>
                        
                        ${order.notes ? `
                            <div class="mt-3">
                                <strong>Notes:</strong>
                                <p class="text-muted mt-1">${order.notes}</p>
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
            
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0"><i class="bi bi-box-seam me-2"></i>Produits commandés</h6>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Produit</th>
                                        <th>P.U.</th>
                                        <th>Qté</th>
                                        <th>Total</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${(order.items || []).map(item => `
                                        <tr>
                                            <td>
                                                <strong>${item.product_name}</strong>
                                                ${item.product_code ? `<br><small class="text-muted">${item.product_code}</small>` : ''}
                                            </td>
                                            <td>${(item.unit_price || 0).toFixed(2)}€</td>
                                            <td>${item.quantity || 0}</td>
                                            <td><strong>${(item.total || 0).toFixed(2)}€</strong></td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            
            ${getDeliveryVerificationButtons(order)}
        </div>
    `;
}

// === UTILITAIRES ===

// Formater le temps relatif
function formatRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);
    
    if (diffInSeconds < 60) return 'À l\'instant';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}min`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h`;
    if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 86400)}j`;
    
    return date.toLocaleDateString('fr-FR');
}

// Supprimer une commande
async function deleteOrder(orderId, orderNumber) {
    if (!confirm(`⚠️ Êtes-vous sûr de vouloir supprimer la commande ${orderNumber} ?\n\nCette action est irréversible.`)) {
        return;
    }
    
    try {
        console.log(`🗑️ Suppression commande: ${orderNumber} (${orderId})`);
        
        const response = await fetch(`/api/orders/${orderId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification(`Commande ${orderNumber} supprimée avec succès`, 'success');
            
            // Recharger la liste des commandes
            await loadOrders(currentPage);
            
            // Mettre à jour les statistiques
            await updateStats();
            
            console.log(`✅ Commande ${orderNumber} supprimée`);
        } else {
            showNotification(result.error || 'Erreur lors de la suppression', 'error');
            console.error('❌ Erreur suppression:', result.error);
        }
    } catch (error) {
        console.error('❌ Erreur réseau suppression:', error);
        showNotification('Erreur de connexion lors de la suppression', 'error');
    }
}

// Afficher une notification
function showNotification(message, type = 'info') {
    // Créer ou réutiliser le conteneur de notifications
    let container = document.getElementById('notificationContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notificationContainer';
        container.className = 'position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    
    // Créer la notification
    const notification = document.createElement('div');
    const alertClass = type === 'error' ? 'alert-danger' : 
                      type === 'success' ? 'alert-success' : 
                      type === 'warning' ? 'alert-warning' : 'alert-info';
    
    notification.className = `alert ${alertClass} alert-dismissible fade show`;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.appendChild(notification);
    
    // Auto-supprimer après 5 secondes
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// === NOUVELLES FONCTIONS DE VÉRIFICATION ===

// Vérifier une commande manuellement
function verifyOrderManually(orderId) {
    console.log(`🔍 Vérification manuelle commande: ${orderId}`);
    
    // Rediriger vers la page de vérification manuelle
    window.location.href = `/verification-manuelle?order_id=${orderId}`;
}

// Vérifier une commande en scannant la facture
function verifyOrderByScanning(orderId) {
    console.log(`📷 Vérification par scan commande: ${orderId}`);
    
    // Rediriger vers le scanner avec l'ID de commande
    window.location.href = `/scanner-validation?order_id=${orderId}`;
}

// Fonction pour envoyer un email manuel à un fournisseur
async function sendOrderEmail(orderId, supplierName) {
    // Déclarer originalText au début pour qu'elle soit accessible partout
    let originalText = '';
    
    try {
        // Debug: afficher les informations de recherche
        console.log('🔍 Recherche fournisseur:', supplierName);
        console.log('📋 Fournisseurs disponibles:', suppliers.map(s => ({name: s.name, email: s.email})));
        
        // Récupérer l'email du fournisseur
        const supplier = suppliers.find(s => s.name === supplierName);
        console.log('🎯 Fournisseur trouvé:', supplier);
        
        if (!supplier || !supplier.email) {
            const errorMsg = !supplier ? 
                `❌ Fournisseur '${supplierName}' non trouvé dans la liste` : 
                `❌ Email non configuré pour le fournisseur '${supplierName}'`;
            console.error(errorMsg);
            showNotification(errorMsg, 'error');
            return;
        }

        const confirmMessage = `Envoyer un email de commande à ${supplierName} (${supplier.email}) ?`;
        if (!confirm(confirmMessage)) {
            return;
        }

        // Afficher un indicateur de chargement
        const button = document.querySelector(`button[onclick="sendOrderEmail('${orderId}', '${supplierName}')"]`);
        originalText = button ? button.innerHTML : '';  // Assigner la valeur ici
        if (button) {
            button.disabled = true;
            button.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Envoi...';
        }

        const response = await fetch('/api/email/send-order', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                order_id: orderId,
                supplier_email: supplier.email
            })
        });

        const result = await response.json();

        if (result.success) {
            showNotification(`✅ Email envoyé avec succès à ${supplierName}`, 'success');
            
            // Passer la commande en "confirmée" après envoi réussi
            try {
                const statusResponse = await fetch(`/api/orders/${orderId}/status`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        status: 'confirmed',
                        notes: `Email envoyé automatiquement à ${supplierName} (${supplier.email})`
                    })
                });
                
                const statusResult = await statusResponse.json();
                if (statusResult.success) {
                    console.log('✅ Statut mis à jour vers "confirmée"');
                    // Recharger les commandes pour afficher le nouveau statut
                    loadOrders();
                } else {
                    console.error('❌ Erreur mise à jour statut:', statusResult.error);
                }
            } catch (statusError) {
                console.error('❌ Erreur mise à jour statut:', statusError);
            }
        } else {
            showNotification(`❌ Erreur envoi email: ${result.error}`, 'error');
        }

    } catch (error) {
        console.error('Erreur envoi email:', error);
        showNotification('❌ Erreur lors de l\'envoi de l\'email', 'error');
    } finally {
        // Restaurer le bouton
        const button = document.querySelector(`button[onclick="sendOrderEmail('${orderId}', '${supplierName}')"]`);
        if (button && originalText) {
            button.disabled = false;
            button.innerHTML = originalText;
        }
    }
}

// Fonction pour vérifier si c'est le jour de livraison
function isDeliveryDay(deliveryDate) {
    if (!deliveryDate) return false;
    
    const today = new Date().toISOString().split('T')[0];
    const delivery = new Date(deliveryDate).toISOString().split('T')[0];
    
    return today === delivery;
}

// Fonction pour afficher les boutons de vérification de livraison
function getDeliveryVerificationButtons(order) {
    // VERSION FORCÉE - Afficher les boutons pour toutes les commandes confirmées
    if (order.status !== 'confirmed') {
        return '';
    }
    
    const isActualDeliveryDay = isDeliveryDay(order.delivery_date);
    const statusText = isActualDeliveryDay ? 'Jour de livraison' : 'Vérification disponible';
    const debugText = isActualDeliveryDay ? '' : ' (Version forcée pour test)';
    
    return `
        <div class="delivery-verification-card mt-3">
            <div class="card border-warning bg-warning bg-opacity-10">
                <div class="card-body">
                    <h6 class="card-title text-warning">
                        <i class="bi bi-truck"></i> ${statusText} - ${order.order_number}${debugText}
                    </h6>
                    <p class="card-text mb-3">
                        <small class="text-muted">
                            La commande peut être vérifiée avec la facture de livraison.
                        </small>
                    </p>
                    <div class="btn-group w-100" role="group">
                        <button class="btn btn-warning" onclick="startManualVerification('${order.id}')">
                            <i class="bi bi-check-circle"></i> Vérifier manuellement
                        </button>
                        <button class="btn btn-outline-warning" onclick="startScanVerification('${order.id}')">
                            <i class="bi bi-camera"></i> Scanner la facture
                        </button>
                    </div>
                    <div class="mt-2">
                        <a href="/scanner-validation?order_id=${order.id}" class="btn btn-sm btn-outline-primary w-100">
                            <i class="bi bi-arrow-right-circle"></i> Aller à la page de vérification
                        </a>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Fonction pour démarrer la vérification manuelle
async function startManualVerification(orderId) {
    try {
        // Récupérer les détails de la commande
        const order = orders.find(o => o.id === orderId);
        if (!order) {
            showNotification('❌ Commande non trouvée', 'error');
            return;
        }
        
        // Afficher le modal de vérification manuelle
        showManualVerificationModal(order);
        
    } catch (error) {
        console.error('Erreur vérification manuelle:', error);
        showNotification('❌ Erreur lors de la vérification manuelle', 'error');
    }
}

// Fonction pour démarrer la vérification par scan
async function startScanVerification(orderId) {
    try {
        // Récupérer les détails de la commande
        const order = orders.find(o => o.id === orderId);
        if (!order) {
            showNotification('❌ Commande non trouvée', 'error');
            return;
        }
        
        // Afficher le modal de scan de facture
        showScanVerificationModal(order);
        
    } catch (error) {
        console.error('Erreur vérification scan:', error);
        showNotification('❌ Erreur lors de la vérification par scan', 'error');
    }
}

// Fonction pour afficher le modal de vérification manuelle
function showManualVerificationModal(order) {
    const modalHtml = `
        <div class="modal fade" id="manualVerificationModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header bg-warning bg-opacity-25">
                        <h5 class="modal-title">
                            <i class="bi bi-pencil-check me-2"></i>Vérification manuelle - ${order.order_number}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-info">
                            <i class="bi bi-info-circle me-2"></i>
                            Vérifiez manuellement les quantités et prix reçus par rapport à la commande
                        </div>
                        
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>Produit</th>
                                        <th>Commandé</th>
                                        <th>Prix commandé</th>
                                        <th>Quantité reçue</th>
                                        <th>Prix facturé</th>
                                        <th>Statut</th>
                                    </tr>
                                </thead>
                                <tbody id="manualVerificationItems">
                                    ${order.items.map((item, index) => `
                                        <tr>
                                            <td class="fw-bold">${item.product_name || item.name}</td>
                                            <td>${item.quantity} ${item.unit}</td>
                                            <td>${(item.unit_price || 0).toFixed(2)}€</td>
                                            <td>
                                                <input type="number" class="form-control form-control-sm" 
                                                       id="received_qty_${index}" 
                                                       value="${item.quantity}" 
                                                       step="0.01" min="0">
                                            </td>
                                            <td>
                                                <input type="number" class="form-control form-control-sm" 
                                                       id="received_price_${index}" 
                                                       value="${(item.unit_price || 0).toFixed(2)}" 
                                                       step="0.01" min="0">
                                            </td>
                                            <td>
                                                <span id="status_${index}" class="badge bg-secondary">En attente</span>
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                        
                        <div class="mt-3">
                            <h6>Résumé de vérification :</h6>
                            <div id="verificationSummary" class="alert alert-light">
                                <div class="row">
                                    <div class="col-md-6">
                                        <strong>Total commandé :</strong> ${(order.total_amount || 0).toFixed(2)}€
                                    </div>
                                    <div class="col-md-6">
                                        <strong>Total facturé :</strong> <span id="totalReceived">0.00€</span>
                                    </div>
                                </div>
                                <div class="mt-2">
                                    <strong>Différence :</strong> <span id="totalDifference" class="text-muted">0.00€</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="mt-3">
                            <label for="verificationNotes" class="form-label">Notes de vérification :</label>
                            <textarea class="form-control" id="verificationNotes" rows="3" 
                                      placeholder="Ajoutez des notes sur les différences observées..."></textarea>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
                        <button type="button" class="btn btn-success" onclick="saveManualVerification('${order.id}')">
                            <i class="bi bi-check-circle me-2"></i>Valider la vérification
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Ajouter le nouveau modal
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Afficher le modal avec gestion d'accessibilité
    const modalElement = document.getElementById('manualVerificationModal');
    const modal = new bootstrap.Modal(modalElement);
    
    // Corriger les problèmes d'accessibilité
    modalElement.addEventListener('shown.bs.modal', function () {
        // Supprimer aria-hidden quand la modale est affichée
        modalElement.removeAttribute('aria-hidden');
    });
    
    modalElement.addEventListener('hidden.bs.modal', function () {
        // Remettre aria-hidden quand la modale est fermée
        modalElement.setAttribute('aria-hidden', 'true');
        // Nettoyer la modale du DOM
        modalElement.remove();
    });
    
    modal.show();
    
    // Ajouter les event listeners pour le calcul automatique
    order.items.forEach((item, index) => {
        const qtyInput = document.getElementById(`received_qty_${index}`);
        const priceInput = document.getElementById(`received_price_${index}`);
        
        [qtyInput, priceInput].forEach(input => {
            input.addEventListener('input', () => updateManualVerificationSummary(order));
        });
    });
    
    // Calculer le résumé initial
    updateManualVerificationSummary(order);
}

// Fonction pour mettre à jour le résumé de vérification manuelle
function updateManualVerificationSummary(order) {
    let totalReceived = 0;
    
    order.items.forEach((item, index) => {
        const receivedQty = parseFloat(document.getElementById(`received_qty_${index}`).value) || 0;
        const receivedPrice = parseFloat(document.getElementById(`received_price_${index}`).value) || 0;
        const statusElement = document.getElementById(`status_${index}`);
        
        const orderedQty = item.quantity || 0;
        const orderedPrice = item.unit_price || 0;
        
        // Calculer le total pour cet item
        const itemTotal = receivedQty * receivedPrice;
        totalReceived += itemTotal;
        
        // Déterminer le statut
        let status = 'Conforme';
        let statusClass = 'bg-success';
        
        if (receivedQty !== orderedQty || receivedPrice !== orderedPrice) {
            status = 'Différence';
            statusClass = 'bg-warning';
        }
        
        if (receivedQty === 0) {
            status = 'Non livré';
            statusClass = 'bg-danger';
        }
        
        statusElement.textContent = status;
        statusElement.className = `badge ${statusClass}`;
    });
    
    // Mettre à jour le résumé
    const totalOrderedElement = document.getElementById('totalReceived');
    const totalDifferenceElement = document.getElementById('totalDifference');
    
    if (totalOrderedElement) {
        totalOrderedElement.textContent = totalReceived.toFixed(2) + '€';
    }
    
    if (totalDifferenceElement) {
        const difference = totalReceived - (order.total_amount || 0);
        totalDifferenceElement.textContent = difference.toFixed(2) + '€';
        
        if (difference > 0) {
            totalDifferenceElement.className = 'text-danger';
        } else if (difference < 0) {
            totalDifferenceElement.className = 'text-success';
        } else {
            totalDifferenceElement.className = 'text-muted';
        }
    }
}

// Fonction pour sauvegarder la vérification manuelle
async function saveManualVerification(orderId) {
    try {
        const order = orders.find(o => o.id === orderId);
        if (!order) {
            showNotification('❌ Commande non trouvée', 'error');
            return;
        }
        
        // Collecter les données de vérification pour la création de facture
        const verificationData = [];
        let hasDiscrepancies = false;
        
        order.items.forEach((item, index) => {
            const receivedQty = parseFloat(document.getElementById(`received_qty_${index}`).value) || 0;
            const receivedPrice = parseFloat(document.getElementById(`received_price_${index}`).value) || 0;
            
            const itemVerification = {
                original: {
                    name: item.product_name || item.name,
                    quantity: item.quantity || 0,
                    unit_price: item.unit_price || 0,
                    unit: item.unit || 'unité'
                },
                received: {
                    quantity: receivedQty,
                    unit_price: receivedPrice,
                    total_price: receivedQty * receivedPrice
                }
            };
            
            // Détecter les différences
            if (receivedQty !== (item.quantity || 0) || Math.abs(receivedPrice - (item.unit_price || 0)) > 0.01) {
                hasDiscrepancies = true;
            }
            
            verificationData.push(itemVerification);
        });
        
        // Préparer les données pour l'API validate-manual qui crée automatiquement une facture
        const requestData = {
            order_id: orderId,
            verification_data: verificationData,
            notes: document.getElementById('verificationNotes').value,
            verified_at: new Date().toISOString(),
            verified_by: 'user'
        };
        
        // Utiliser l'endpoint validate-manual qui crée automatiquement une facture
        const response = await fetch('/api/orders/validate-manual', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Fermer le modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('manualVerificationModal'));
            modal.hide();
            
            // Afficher un message de succès avec mention de la facture créée
            const statusMessage = hasDiscrepancies ? 'avec différences détectées' : 'conforme';
            showNotification(`✅ Vérification terminée ${statusMessage}. Facture créée automatiquement!`, 'success');
            
            // Recharger les commandes pour voir le nouveau statut
            await loadOrders();
            
        } else {
            showNotification('❌ Erreur lors de la validation: ' + result.error, 'error');
        }
        
    } catch (error) {
        console.error('Erreur validation manuelle:', error);
        showNotification('❌ Erreur lors de la validation de la commande', 'error');
    }
}

// Fonction pour afficher le modal de scan de facture
function showScanVerificationModal(order) {
    const modalHtml = `
        <div class="modal fade" id="scanVerificationModal" tabindex="-1">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header bg-primary bg-opacity-25">
                        <h5 class="modal-title">
                            <i class="bi bi-camera me-2"></i>Scanner la facture - ${order.order_number}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-info">
                            <i class="bi bi-info-circle me-2"></i>
                            Scannez ou uploadez la facture de livraison pour vérification automatique
                        </div>
                        
                        <div class="row">
                            <div class="col-md-6">
                                <h6>📋 Commande originale :</h6>
                                <div class="table-responsive">
                                    <table class="table table-sm">
                                        <thead>
                                            <tr>
                                                <th>Produit</th>
                                                <th>Qté</th>
                                                <th>Prix</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${order.items.map(item => `
                                                <tr>
                                                    <td>${item.product_name || item.name}</td>
                                                    <td>${item.quantity} ${item.unit}</td>
                                                    <td>${(item.unit_price || 0).toFixed(2)}€</td>
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
                                </div>
                                <div class="alert alert-light">
                                    <strong>Total commandé :</strong> ${(order.total_amount || 0).toFixed(2)}€
                                </div>
                            </div>
                            
                            <div class="col-md-6">
                                <h6>📷 Scanner la facture :</h6>
                                <div class="border rounded p-3 text-center" style="min-height: 200px;">
                                    <input type="file" id="invoiceFile" accept="image/*,.pdf" class="d-none">
                                    <button type="button" class="btn btn-primary btn-lg" onclick="document.getElementById('invoiceFile').click()">
                                        <i class="bi bi-cloud-upload me-2"></i>Choisir un fichier
                                    </button>
                                    <p class="text-muted mt-2">Formats acceptés: JPG, PNG, PDF</p>
                                    
                                    <div id="scanProgress" class="d-none mt-3">
                                        <div class="spinner-border text-primary" role="status">
                                            <span class="visually-hidden">Analyse en cours...</span>
                                        </div>
                                        <p class="mt-2">Analyse de la facture en cours...</p>
                                    </div>
                                    
                                    <div id="scanResults" class="d-none mt-3">
                                        <!-- Les résultats du scan apparaîtront ici -->
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div id="comparisonResults" class="d-none mt-4">
                            <h6>📊 Résultats de la comparaison :</h6>
                            <div id="comparisonTable">
                                <!-- Le tableau de comparaison apparaîtra ici -->
                            </div>
                        </div>
                        
                        <div class="mt-3">
                            <label for="scanVerificationNotes" class="form-label">Notes de vérification :</label>
                            <textarea class="form-control" id="scanVerificationNotes" rows="3" 
                                      placeholder="Notes automatiques du scan ou commentaires supplémentaires..."></textarea>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
                        <button type="button" class="btn btn-success d-none" id="validateScanBtn" onclick="saveScanVerification('${order.id}')">
                            <i class="bi bi-check-circle me-2"></i>Valider la vérification
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Supprimer le modal existant s'il y en a un
    const existingModal = document.getElementById('scanVerificationModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Ajouter le nouveau modal
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Afficher le modal avec gestion d'accessibilité
    const modalElement = document.getElementById('scanVerificationModal');
    const modal = new bootstrap.Modal(modalElement);
    
    // Corriger les problèmes d'accessibilité
    modalElement.addEventListener('shown.bs.modal', function () {
        modalElement.removeAttribute('aria-hidden');
    });
    
    modalElement.addEventListener('hidden.bs.modal', function () {
        modalElement.setAttribute('aria-hidden', 'true');
        // Nettoyer la modale du DOM
        modalElement.remove();
    });
    
    modal.show();
    
    // Ajouter l'event listener pour le fichier
    document.getElementById('invoiceFile').addEventListener('change', (event) => {
        handleInvoiceFileUpload(event, order);
    });
}

// Fonction pour gérer l'upload et l'analyse de la facture
async function handleInvoiceFileUpload(event, order) {
    const file = event.target.files[0];
    if (!file) return;
    
    try {
        // Afficher le progress
        document.getElementById('scanProgress').classList.remove('d-none');
        document.getElementById('scanResults').classList.add('d-none');
        document.getElementById('comparisonResults').classList.add('d-none');
        
        // Créer FormData pour l'upload
        const formData = new FormData();
        formData.append('invoice', file);
        formData.append('order_id', order.id);
        
        // Envoyer au serveur pour analyse
        const response = await fetch('/api/orders/scan-verification', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        // Masquer le progress
        document.getElementById('scanProgress').classList.add('d-none');
        
        if (result.success) {
            // Afficher les résultats du scan
            displayScanResults(result.scan_data, order);
            
            // Afficher la comparaison
            displayComparisonResults(result.comparison, order);
            
            // Activer le bouton de validation
            document.getElementById('validateScanBtn').classList.remove('d-none');
            
            // Ajouter les notes automatiques
            document.getElementById('scanVerificationNotes').value = result.notes || '';
            
        } else {
            showNotification('❌ Erreur lors de l\'analyse: ' + result.error, 'error');
        }
        
    } catch (error) {
        console.error('Erreur upload facture:', error);
        document.getElementById('scanProgress').classList.add('d-none');
        showNotification('❌ Erreur lors de l\'upload de la facture', 'error');
    }
}

// Fonction pour afficher les résultats du scan
function displayScanResults(scanData, order) {
    const resultsDiv = document.getElementById('scanResults');
    
    const html = `
        <div class="alert alert-success">
            <i class="bi bi-check-circle me-2"></i>Facture analysée avec succès !
        </div>
        <div class="table-responsive">
            <table class="table table-sm">
                <thead>
                    <tr>
                        <th>Produit détecté</th>
                        <th>Quantité</th>
                        <th>Prix</th>
                    </tr>
                </thead>
                <tbody>
                    ${scanData.items.map(item => `
                        <tr>
                            <td>${item.name}</td>
                            <td>${item.quantity} ${item.unit || ''}</td>
                            <td>${(item.price || 0).toFixed(2)}€</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
        <div class="alert alert-light">
            <strong>Total facturé détecté :</strong> ${(scanData.total || 0).toFixed(2)}€
        </div>
    `;
    
    resultsDiv.innerHTML = html;
    resultsDiv.classList.remove('d-none');
}

// Fonction pour afficher les résultats de comparaison
function displayComparisonResults(comparison, order) {
    const comparisonDiv = document.getElementById('comparisonResults');
    const tableDiv = document.getElementById('comparisonTable');
    
    const html = `
        <div class="table-responsive">
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>Produit</th>
                        <th>Commandé</th>
                        <th>Facturé</th>
                        <th>Différence Qté</th>
                        <th>Différence Prix</th>
                        <th>Statut</th>
                    </tr>
                </thead>
                <tbody>
                    ${comparison.items.map(item => `
                        <tr class="${item.status === 'match' ? 'table-success' : item.status === 'difference' ? 'table-warning' : 'table-danger'}">
                            <td class="fw-bold">${item.product_name}</td>
                            <td>${item.ordered_quantity} ${item.ordered_unit || ''} - ${(item.ordered_price || 0).toFixed(2)}€</td>
                            <td>${item.received_quantity || 0} ${item.received_unit || ''} - ${(item.received_price || 0).toFixed(2)}€</td>
                            <td>${((item.received_quantity || 0) - (item.ordered_quantity || 0)).toFixed(2)}</td>
                            <td>${((item.received_price || 0) - (item.ordered_price || 0)).toFixed(2)}€</td>
                            <td>
                                <span class="badge ${item.status === 'match' ? 'bg-success' : item.status === 'difference' ? 'bg-warning' : 'bg-danger'}">
                                    ${item.status === 'match' ? 'Conforme' : item.status === 'difference' ? 'Différence' : 'Non trouvé'}
                                </span>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
        
        <div class="row mt-3">
            <div class="col-md-4">
                <div class="alert alert-info">
                    <strong>Total commandé :</strong><br>
                    ${(comparison.total_ordered || 0).toFixed(2)}€
                </div>
            </div>
            <div class="col-md-4">
                <div class="alert alert-primary">
                    <strong>Total facturé :</strong><br>
                    ${(comparison.total_received || 0).toFixed(2)}€
                </div>
            </div>
            <div class="col-md-4">
                <div class="alert ${comparison.total_difference >= 0 ? 'alert-danger' : 'alert-success'}">
                    <strong>Différence :</strong><br>
                    ${(comparison.total_difference || 0).toFixed(2)}€
                </div>
            </div>
        </div>
        
        <div class="alert ${comparison.has_discrepancies ? 'alert-warning' : 'alert-success'}">
            <i class="bi bi-${comparison.has_discrepancies ? 'exclamation-triangle' : 'check-circle'} me-2"></i>
            ${comparison.has_discrepancies ? 'Des différences ont été détectées dans la livraison' : 'La livraison correspond parfaitement à la commande'}
        </div>
    `;
    
    tableDiv.innerHTML = html;
    comparisonDiv.classList.remove('d-none');
}

// Fonction pour sauvegarder la vérification par scan
async function saveScanVerification(orderId) {
    try {
        // Les données de vérification sont déjà stockées côté serveur lors du scan
        // On doit juste confirmer la validation
        
        const notes = document.getElementById('scanVerificationNotes').value;
        
        const response = await fetch('/api/orders/confirm-scan-verification', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                order_id: orderId,
                notes: notes
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Fermer le modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('scanVerificationModal'));
            modal.hide();
            
            // Mettre à jour le statut de la commande
            const newStatus = result.has_discrepancies ? 'delivered_with_issues' : 'delivered';
            await updateOrderStatus(orderId, newStatus, 'Vérification par scan effectuée');
            
            showNotification('✅ Vérification par scan sauvegardée avec succès', 'success');
            
            // Recharger les commandes
            await loadOrders();
            
        } else {
            showNotification('❌ Erreur lors de la confirmation: ' + result.error, 'error');
        }
        
    } catch (error) {
        console.error('Erreur confirmation scan:', error);
        showNotification('❌ Erreur lors de la confirmation de la vérification', 'error');
    }
}

// Fonction pour envoyer un email silencieusement (sans interface utilisateur)
async function sendOrderEmailSilent(orderId, supplierName, orderNumber) {
    try {
        console.log('📧 Envoi automatique email pour commande:', orderNumber);
        
        // Récupérer l'email du fournisseur
        const supplier = suppliers.find(s => s.name === supplierName);
        
        if (!supplier || !supplier.email) {
            const errorMsg = !supplier ? 
                `Fournisseur '${supplierName}' non trouvé` : 
                `Email non configuré pour ${supplierName}`;
            console.error('❌', errorMsg);
            throw new Error(errorMsg);
        }

        const response = await fetch('/api/email/send-order', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                order_id: orderId,
                supplier_email: supplier.email
            })
        });

        const result = await response.json();

        if (result.success) {
            console.log('✅ Email automatique envoyé à', supplierName);
            showNotification(`✅ Email envoyé à ${supplierName} - Commande ${orderNumber} confirmée`, 'success');
            
            // Passer la commande en "confirmée" après envoi réussi
            try {
                const statusResponse = await fetch(`/api/orders/${orderId}/status`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        status: 'confirmed',
                        notes: `Email envoyé automatiquement à ${supplierName} (${supplier.email})`
                    })
                });
                
                const statusResult = await statusResponse.json();
                if (statusResult.success) {
                    console.log('✅ Statut mis à jour vers "confirmée"');
                    // Recharger les commandes pour afficher le nouveau statut
                    loadOrders();
                }
            } catch (statusError) {
                console.error('❌ Erreur mise à jour statut:', statusError);
            }
        } else {
            console.error('❌ Erreur envoi email automatique:', result.error);
            throw new Error(result.error);
        }

    } catch (error) {
        console.error('❌ Erreur envoi email automatique:', error);
        throw error;
    }
}

// === GESTION DES MODALES ET ACCESSIBILITÉ ===

/**
 * Fonction utilitaire pour gérer l'accessibilité des modales Bootstrap
 * Corrige le problème aria-hidden avec les éléments focusables
 */
function showModalWithAccessibility(modalId, isDynamic = false) {
    const modalElement = document.getElementById(modalId);
    if (!modalElement) {
        console.error(`Modal ${modalId} non trouvée`);
        return null;
    }
    
    const modal = new bootstrap.Modal(modalElement);
    
    // Gérer les événements d'accessibilité
    const handleShown = function() {
        // Supprimer aria-hidden quand la modale est affichée
        modalElement.removeAttribute('aria-hidden');
    };
    
    const handleHidden = function() {
        // Remettre aria-hidden quand la modale est fermée
        modalElement.setAttribute('aria-hidden', 'true');
        
        // Nettoyer les event listeners
        modalElement.removeEventListener('shown.bs.modal', handleShown);
        modalElement.removeEventListener('hidden.bs.modal', handleHidden);
        
        // Supprimer la modale du DOM si elle est dynamique
        if (isDynamic) {
            modalElement.remove();
        }
    };
    
    // Ajouter les event listeners
    modalElement.addEventListener('shown.bs.modal', handleShown);
    modalElement.addEventListener('hidden.bs.modal', handleHidden);
    
    return modal;
}

// === CORRECTION D'ACCESSIBILITÉ POUR LES MODALES ===

/**
 * Corrige automatiquement les problèmes d'aria-hidden sur les modales Bootstrap
 * Cette fonction est appelée à chaque fois qu'une modale est affichée
 */
function fixModalAccessibility() {
    // Observer les changements sur les modales
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                const modal = mutation.target;
                if (modal.classList.contains('modal') && modal.style.display === 'block') {
                    // La modale est affichée, supprimer aria-hidden
                    modal.removeAttribute('aria-hidden');
                }
            }
        });
    });
    
    // Observer toutes les modales existantes et futures
    document.querySelectorAll('.modal').forEach(modal => {
        observer.observe(modal, {
            attributes: true,
            attributeFilter: ['style', 'aria-hidden']
        });
    });
    
    // Observer les nouvelles modales ajoutées au DOM
    const bodyObserver = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === 1 && node.classList && node.classList.contains('modal')) {
                    observer.observe(node, {
                        attributes: true,
                        attributeFilter: ['style', 'aria-hidden']
                    });
                }
            });
        });
    });
    
    bodyObserver.observe(document.body, { childList: true, subtree: true });
}

// Démarrer la correction d'accessibilité dès que le DOM est prêt
document.addEventListener('DOMContentLoaded', fixModalAccessibility);

// === VARIABLES GLOBALES ===

console.log('✅ Commandes V3 initialisé'); 