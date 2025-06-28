// Vérification Manuelle FactureKiller V3

let currentOrder = null;
let verificationData = [];
let originalProducts = [];

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔍 Initialisation Vérification Manuelle...');
    
    // Récupérer l'ID de commande depuis l'URL
    const urlParams = new URLSearchParams(window.location.search);
    const orderId = urlParams.get('order_id');
    
    if (!orderId) {
        showError('Aucune commande spécifiée');
        return;
    }
    
    loadOrder(orderId);
    setupEventListeners();
});

// Configuration des écouteurs d'événements
function setupEventListeners() {
    // Checkbox de confirmation
    const confirmCheckbox = document.getElementById('confirmCheckbox');
    if (confirmCheckbox) {
        confirmCheckbox.addEventListener('change', function() {
            document.getElementById('finalizeBtn').disabled = !this.checked;
        });
    }
}

// Charger la commande
async function loadOrder(orderId) {
    try {
        console.log(`📦 Chargement commande: ${orderId}`);
        
        const response = await fetch(`/api/orders/${orderId}`);
        const result = await response.json();
        
        if (result.success) {
            currentOrder = result.data;
            originalProducts = [...(currentOrder.products || [])];
            initializeVerificationData();
            displayOrder();
            hideLoading();
        } else {
            showError(result.error || 'Commande non trouvée');
        }
    } catch (error) {
        console.error('❌ Erreur chargement commande:', error);
        showError('Erreur de connexion');
    }
}

// Initialiser les données de vérification
function initializeVerificationData() {
    verificationData = originalProducts.map((product, index) => ({
        index: index,
        original: { ...product },
        received: {
            quantity: product.quantity,
            unit_price: product.unit_price,
            total_price: product.quantity * product.unit_price
        },
        status: 'pending',
        notes: ''
    }));
}

// Afficher la commande
function displayOrder() {
    // Informations générales
    document.getElementById('orderNumber').textContent = currentOrder.order_number || 'N/A';
    document.getElementById('orderStatus').textContent = getStatusLabel(currentOrder.status);
    document.getElementById('orderInfo').textContent = 
        `${currentOrder.supplier} • ${formatDate(currentOrder.created_at)} • ${currentOrder.products?.length || 0} produits`;
    document.getElementById('orderTotal').textContent = formatPrice(currentOrder.total_amount || 0);
    
    // Tableau de vérification
    renderVerificationTable();
    updateSummary();
}

// Afficher le tableau de vérification
function renderVerificationTable() {
    const tbody = document.getElementById('verificationTableBody');
    
    tbody.innerHTML = verificationData.map((item, index) => {
        const product = item.original;
        const received = item.received;
        const orderedTotal = product.quantity * product.unit_price;
        const difference = received.total_price - orderedTotal;
        
        return `
            <tr data-index="${index}" class="${getRowClass(item.status)}">
                <td>
                    <div class="fw-bold">${product.name}</div>
                    <small class="text-muted">${product.unit || 'unité'}</small>
                </td>
                <td class="text-center">
                    <span class="badge bg-light text-dark">${product.quantity}</span>
                </td>
                <td class="text-center">
                    <input type="number" class="form-control form-control-sm text-center" 
                           value="${received.quantity}" min="0" step="0.1"
                           onchange="updateReceivedQuantity(${index}, this.value)">
                </td>
                <td class="text-center">
                    <span class="text-muted">${formatPrice(product.unit_price)}</span>
                </td>
                <td class="text-center">
                    <input type="number" class="form-control form-control-sm text-center" 
                           value="${received.unit_price}" min="0" step="0.01"
                           onchange="updateReceivedPrice(${index}, this.value)">
                </td>
                <td class="text-center">
                    <span class="fw-bold" id="totalReceived_${index}">${formatPrice(received.total_price)}</span>
                </td>
                <td class="text-center">
                    <span class="${difference >= 0 ? 'text-danger' : 'text-success'}" id="difference_${index}">
                        ${difference >= 0 ? '+' : ''}${formatPrice(difference)}
                    </span>
                </td>
                <td class="text-center">
                    <span class="badge ${getStatusBadgeClass(item.status)}" id="status_${index}">
                        ${getStatusLabel(item.status)}
                    </span>
                </td>
            </tr>
        `;
    }).join('');
}

// Mettre à jour la quantité reçue
function updateReceivedQuantity(index, value) {
    const quantity = parseFloat(value) || 0;
    verificationData[index].received.quantity = quantity;
    verificationData[index].received.total_price = quantity * verificationData[index].received.unit_price;
    
    updateRowDisplay(index);
    updateSummary();
}

// Mettre à jour le prix unitaire reçu
function updateReceivedPrice(index, value) {
    const price = parseFloat(value) || 0;
    verificationData[index].received.unit_price = price;
    verificationData[index].received.total_price = verificationData[index].received.quantity * price;
    
    updateRowDisplay(index);
    updateSummary();
}

// Mettre à jour l'affichage d'une ligne
function updateRowDisplay(index) {
    const item = verificationData[index];
    const received = item.received;
    const original = item.original;
    const orderedTotal = original.quantity * original.unit_price;
    const difference = received.total_price - orderedTotal;
    
    // Mettre à jour le total reçu
    document.getElementById(`totalReceived_${index}`).textContent = formatPrice(received.total_price);
    
    // Mettre à jour la différence
    const diffElement = document.getElementById(`difference_${index}`);
    diffElement.textContent = `${difference >= 0 ? '+' : ''}${formatPrice(difference)}`;
    diffElement.className = difference >= 0 ? 'text-danger' : 'text-success';
    
    // Mettre à jour le statut
    const hasQuantityDiff = received.quantity !== original.quantity;
    const hasPriceDiff = Math.abs(received.unit_price - original.unit_price) > 0.01;
    
    let status = 'verified';
    if (hasQuantityDiff && hasPriceDiff) {
        status = 'quantity_price_diff';
    } else if (hasQuantityDiff) {
        status = 'quantity_diff';
    } else if (hasPriceDiff) {
        status = 'price_diff';
    }
    
    item.status = status;
    
    const statusElement = document.getElementById(`status_${index}`);
    statusElement.textContent = getStatusLabel(status);
    statusElement.className = `badge ${getStatusBadgeClass(status)}`;
    
    // Mettre à jour la classe de la ligne
    const row = document.querySelector(`tr[data-index="${index}"]`);
    row.className = getRowClass(status);
}

// Mettre à jour le résumé
function updateSummary() {
    let totalSavings = 0;
    let totalOvercharge = 0;
    
    verificationData.forEach(item => {
        const orderedTotal = item.original.quantity * item.original.unit_price;
        const difference = item.received.total_price - orderedTotal;
        
        if (difference < 0) {
            totalSavings += Math.abs(difference);
        } else if (difference > 0) {
            totalOvercharge += difference;
        }
    });
    
    const netDifference = totalOvercharge - totalSavings;
    
    document.getElementById('totalSavings').textContent = formatPrice(totalSavings);
    document.getElementById('totalOvercharge').textContent = formatPrice(totalOvercharge);
    
    const netElement = document.getElementById('netDifference');
    netElement.textContent = formatPrice(Math.abs(netDifference));
    netElement.className = netDifference >= 0 ? 'h4 text-danger' : 'h4 text-success';
}

// Réinitialiser tous les produits aux valeurs commandées
function resetAllToOrdered() {
    if (confirm('Êtes-vous sûr de vouloir réinitialiser tous les produits aux valeurs commandées ?')) {
        initializeVerificationData();
        renderVerificationTable();
        updateSummary();
        showNotification('Tous les produits ont été réinitialisés', 'info');
    }
}

// Sauvegarder le brouillon
async function saveDraft() {
    try {
        const draftData = {
            order_id: currentOrder.id,
            verification_data: verificationData,
            notes: document.getElementById('verificationNotes').value,
            status: 'draft',
            saved_at: new Date().toISOString()
        };
        
        // Sauvegarder localement pour l'instant
        localStorage.setItem(`verification_draft_${currentOrder.id}`, JSON.stringify(draftData));
        
        showNotification('Brouillon sauvegardé', 'success');
    } catch (error) {
        console.error('❌ Erreur sauvegarde brouillon:', error);
        showNotification('Erreur lors de la sauvegarde', 'error');
    }
}

// Refuser la livraison
function rejectDelivery() {
    if (confirm('Êtes-vous sûr de vouloir refuser cette livraison ?')) {
        // TODO: Implémenter la logique de refus
        showNotification('Fonctionnalité à implémenter', 'warning');
    }
}

// Valider la livraison
function validateDelivery() {
    // Préparer le résumé pour la modal
    const summary = [];
    let hasChanges = false;
    
    verificationData.forEach(item => {
        const orderedTotal = item.original.quantity * item.original.unit_price;
        const difference = item.received.total_price - orderedTotal;
        
        if (Math.abs(difference) > 0.01) {
            hasChanges = true;
            summary.push(`<li>${item.original.name}: ${difference >= 0 ? '+' : ''}${formatPrice(difference)}</li>`);
        }
    });
    
    if (!hasChanges) {
        summary.push('<li class="text-success">Aucun écart détecté - Livraison conforme</li>');
    }
    
    document.getElementById('confirmationSummary').innerHTML = summary.join('');
    
    // Afficher la modal
    const modal = new bootstrap.Modal(document.getElementById('confirmationModal'));
    modal.show();
}

// Finaliser la validation
async function finalizeValidation() {
    try {
        const validationData = {
            order_id: currentOrder.id,
            verification_method: 'manual',
            verification_data: verificationData,
            notes: document.getElementById('verificationNotes').value,
            verified_at: new Date().toISOString(),
            verified_by: 'user' // TODO: Ajouter l'utilisateur connecté
        };
        
        // Envoyer la validation
        const response = await fetch('/api/orders/validate-manual', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(validationData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Livraison validée avec succès', 'success');
            
            // Rediriger vers les commandes après 2 secondes
            setTimeout(() => {
                window.location.href = '/commandes';
            }, 2000);
        } else {
            showNotification(result.error || 'Erreur lors de la validation', 'error');
        }
    } catch (error) {
        console.error('❌ Erreur validation:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

// Fonctions utilitaires
function getStatusLabel(status) {
    const statusMap = {
        'pending': 'En attente',
        'verified': 'Vérifié',
        'quantity_diff': 'Écart quantité',
        'price_diff': 'Écart prix',
        'quantity_price_diff': 'Écarts multiples',
        'sent': 'Envoyée',
        'delivered': 'Livrée'
    };
    return statusMap[status] || status;
}

function getStatusBadgeClass(status) {
    const classMap = {
        'pending': 'bg-warning',
        'verified': 'bg-success',
        'quantity_diff': 'bg-info',
        'price_diff': 'bg-warning',
        'quantity_price_diff': 'bg-danger'
    };
    return classMap[status] || 'bg-secondary';
}

function getRowClass(status) {
    const classMap = {
        'pending': '',
        'verified': 'table-success',
        'quantity_diff': 'table-info',
        'price_diff': 'table-warning',
        'quantity_price_diff': 'table-danger'
    };
    return classMap[status] || '';
}

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

function hideLoading() {
    document.getElementById('loadingContainer').classList.add('d-none');
    document.getElementById('verificationContainer').classList.remove('d-none');
}

function showError(message) {
    document.getElementById('loadingContainer').classList.add('d-none');
    document.getElementById('errorContainer').classList.remove('d-none');
    document.getElementById('errorMessage').textContent = message;
}

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

console.log('✅ Vérification Manuelle initialisée'); 