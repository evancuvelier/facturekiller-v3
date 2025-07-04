// FactureKiller V3 - Module Scanner

let currentFile = null;
let analysisResult = null;

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    initializeScanner();
    loadOrders();
    
    // Vérifier si on vient d'une commande à vérifier
    checkVerifyOrderMode();
});

function initializeScanner() {
    // Zone de drop
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    
    // Drag & Drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });
    
    // Input file
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });
    
    // Mode de scan
    document.querySelectorAll('input[name="scanMode"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            if (e.target.value === 'order') {
                // Rediriger vers la page de validation spécialisée
                window.location.href = '/scanner-validation';
                return;
            }
            
            const orderSelection = document.getElementById('orderSelection');
            if (e.target.value === 'commande') {
                orderSelection?.classList.remove('d-none');
            } else {
                orderSelection?.classList.add('d-none');
            }
        });
    });
    
    // Bouton analyser
    document.getElementById('analyzeBtn')?.addEventListener('click', analyzeInvoice);
    
    // Bouton sauvegarder
    document.getElementById('saveInvoiceBtn')?.addEventListener('click', saveInvoice);
}

// Charger les commandes
async function loadOrders() {
    try {
        const data = await API.get('/api/orders');
        const select = document.getElementById('orderSelect');
        
        if (data.data && data.data.length > 0) {
            // Filtrer les commandes qui peuvent être vérifiées
            const today = new Date();
            const todayStr = today.toISOString().split('T')[0];
            
            // Calculer la date d'il y a 7 jours pour inclure les livraisons récentes
            const oneWeekAgo = new Date(today);
            oneWeekAgo.setDate(today.getDate() - 7);
            const oneWeekAgoStr = oneWeekAgo.toISOString().split('T')[0];
            
            const verifiableOrders = data.data.filter(order => {
                // Inclure les commandes confirmées avec livraison aujourd'hui ou dans les 7 derniers jours
                const deliveryDate = order.delivery_date;
                const isConfirmed = order.status === 'confirmed';
                const isDeliveredRecently = ['delivered', 'delivered_with_issues', 'invoiced'].includes(order.status);
                
                if (!deliveryDate) return false;
                
                // Vérifier si la livraison est aujourd'hui ou dans les 7 derniers jours
                const isRecentDelivery = deliveryDate >= oneWeekAgoStr && deliveryDate <= todayStr;
                
                return (isConfirmed || isDeliveredRecently) && isRecentDelivery;
            });
            
            if (verifiableOrders.length === 0) {
                const option = document.createElement('option');
                option.value = '';
                option.textContent = 'Aucune commande à vérifier aujourd\'hui';
                option.disabled = true;
                select.appendChild(option);
                return;
            }
            
            // Trier par date de livraison (plus récent en premier)
            verifiableOrders.sort((a, b) => new Date(b.delivery_date) - new Date(a.delivery_date));
            
            verifiableOrders.forEach(order => {
                const option = document.createElement('option');
                option.value = order.id;
                
                // Déterminer le statut d'affichage
                const deliveryDate = new Date(order.delivery_date);
                const isToday = deliveryDate.toISOString().split('T')[0] === todayStr;
                const dayLabel = isToday ? '🚚 AUJOURD\'HUI' : `📅 ${formatDate(order.delivery_date)}`;
                
                // Statut de la commande
                const statusLabels = {
                    'confirmed': '✅ Confirmée',
                    'delivered': '📦 Livrée',
                    'delivered_with_issues': '⚠️ Livrée avec problèmes',
                    'invoiced': '🧾 Facturée'
                };
                const statusLabel = statusLabels[order.status] || order.status;
                
                option.textContent = `${order.order_number} - ${order.supplier} (${dayLabel}) - ${statusLabel}`;
                select.appendChild(option);
            });
            
            console.log(`✅ ${verifiableOrders.length} commandes à vérifier chargées`);
        } else {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'Aucune commande disponible';
            option.disabled = true;
            select.appendChild(option);
        }
    } catch (error) {
        console.error('Erreur chargement commandes:', error);
        const select = document.getElementById('orderSelect');
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'Erreur de chargement';
        option.disabled = true;
        select.appendChild(option);
    }
}

// Gérer la sélection de fichier
function handleFileSelect(file) {
    // Vérifier le type
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/heic', 'image/heif', 'application/pdf'];
    
    if (!validTypes.includes(file.type) && !file.name.toLowerCase().match(/\.(jpg|jpeg|png|gif|webp|heic|heif|pdf)$/)) {
        showNotification('Type de fichier non supporté', 'error');
        return;
    }
    
    // Vérifier la taille (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
        showNotification('Fichier trop volumineux (max 10MB)', 'error');
        return;
    }
    
    currentFile = file;
    
    // Afficher l'aperçu
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('previewImg').src = e.target.result;
        document.getElementById('imagePreview').classList.remove('d-none');
        document.getElementById('dropZone').style.display = 'none';
    };
    reader.readAsDataURL(file);
}

// Analyser la facture
async function analyzeInvoice() {
    if (!currentFile) {
        showNotification('Aucun fichier sélectionné', 'error');
        return;
    }
    
    // Préparer les données
    const formData = new FormData();
    formData.append('file', currentFile);
    
    // Mode de scan
    const scanMode = document.querySelector('input[name="scanMode"]:checked').value;
    formData.append('mode', scanMode);
    
    if (scanMode === 'commande') {
        const orderId = document.getElementById('orderSelect').value;
        if (orderId) {
            formData.append('order_id', orderId);
        }
    }
    
    // Afficher la progression
    showProgress(true);
    updateProgress(10, 'Envoi du fichier...');
    
    try {
        // Simuler les étapes de progression
        setTimeout(() => updateProgress(30, 'OCR en cours...'), 500);
        setTimeout(() => updateProgress(60, 'Analyse avec Claude Vision...'), 2000);
        setTimeout(() => updateProgress(80, 'Comparaison des prix...'), 4000);
        
        // Appel API
        const response = await API.post('/api/invoices/analyze', formData, true);
        
        updateProgress(100, 'Analyse terminée !');
        
        if (response.success) {
            analysisResult = response.data;
            displayResults(response.data);
            
            // Afficher le modal des produits en attente si nécessaire
            if (response.data.price_comparison?.new_products > 0) {
                showPendingProductsModal(response.data);
            }
        } else {
            throw new Error(response.error || 'Erreur lors de l\'analyse');
        }
        
    } catch (error) {
        showNotification(`Erreur: ${error.message}`, 'error');
        resetScanner();
    } finally {
        setTimeout(() => showProgress(false), 1000);
    }
}

// Afficher/masquer la progression
function showProgress(show) {
    const progressSection = document.getElementById('progressSection');
    const analyzeBtn = document.getElementById('analyzeBtn');
    
    if (show) {
        progressSection.classList.remove('d-none');
        analyzeBtn.disabled = true;
    } else {
        progressSection.classList.add('d-none');
        analyzeBtn.disabled = false;
    }
}

// Mettre à jour la progression
function updateProgress(percent, text) {
    const progressBar = document.querySelector('.progress-bar');
    const progressText = document.getElementById('progressText');
    
    progressBar.style.width = `${percent}%`;
    progressBar.setAttribute('aria-valuenow', percent);
    progressText.textContent = text;
}

// Afficher les résultats
function displayResults(data) {
    // Masquer les conseils et afficher les résultats
    document.getElementById('tipsCard').classList.add('d-none');
    document.getElementById('resultsCard').classList.remove('d-none');
    
    // Informations générales
    document.getElementById('resultSupplier').textContent = data.supplier || 'Non identifié';
    document.getElementById('resultInvoiceNumber').textContent = data.invoice_number || '-';
    document.getElementById('resultDate').textContent = Utils.formatDate(data.date);
    document.getElementById('resultTotal').textContent = Utils.formatCurrency(data.total_amount);
    
    // Comparaison des prix avec notifications spéciales
    if (data.price_comparison) {
        const comp = data.price_comparison;
        document.getElementById('comparedCount').textContent = comp.matched_products || 0;
        document.getElementById('newProductsCount').textContent = comp.new_products || 0;
        document.getElementById('savingsAmount').textContent = Utils.formatCurrency(comp.total_savings);
        document.getElementById('overpaymentAmount').textContent = Utils.formatCurrency(comp.total_overpayment);
        
        // 🎉 NOUVELLES NOTIFICATIONS POUR CRÉATION AUTOMATIQUE
        if (comp.new_products > 0) {
            // Notification pour nouveaux produits
            showNewProductsNotification(comp.new_products, data.supplier);
            
            // Vérifier si c'est un nouveau fournisseur
            checkIfNewSupplier(data.supplier);
        }
    }
    
    // Liste des produits
    const tbody = document.querySelector('#productsTable tbody');
    tbody.innerHTML = '';
    
    if (data.products && data.products.length > 0) {
        data.products.forEach((product, index) => {
            const comparison = data.price_comparison?.products_details?.[index];
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${product.name}</td>
                <td>${product.quantity} ${product.unit || ''}</td>
                <td>${Utils.formatCurrency(product.unit_price)}</td>
                <td>${comparison?.reference_price ? Utils.formatCurrency(comparison.reference_price) : '-'}</td>
                <td>${comparison ? Utils.createStatusBadge(comparison.status) : '-'}</td>
            `;
            
            // Colorer la ligne selon le statut
            if (comparison?.status === 'overprice') {
                row.classList.add('table-danger');
            } else if (comparison?.status === 'savings') {
                row.classList.add('table-success');
            } else if (comparison?.status === 'new') {
                row.classList.add('table-info');
            }
            
            tbody.appendChild(row);
        });
    } else {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Aucun produit détecté</td></tr>';
    }
}

// 🎉 NOUVELLE FONCTION : Notification pour nouveaux produits
function showNewProductsNotification(newProductsCount, supplier) {
    const notificationHtml = `
        <div class="alert alert-success alert-dismissible fade show mt-3" role="alert">
            <h6 class="alert-heading">
                <i class="bi bi-plus-circle me-2"></i>Nouveaux produits détectés !
            </h6>
            <p class="mb-2">
                <strong>${newProductsCount} nouveau${newProductsCount > 1 ? 'x' : ''} produit${newProductsCount > 1 ? 's' : ''}</strong> 
                ${newProductsCount > 1 ? 'ont été ajoutés' : 'a été ajouté'} en attente de validation pour 
                <strong>${supplier}</strong>.
            </p>
            <hr>
            <div class="d-flex justify-content-between align-items-center">
                <small class="text-muted">
                    <i class="bi bi-clock me-1"></i>Ces produits seront disponibles après validation dans la section Fournisseurs.
                </small>
                <a href="/fournisseurs" class="btn btn-sm btn-outline-success">
                    <i class="bi bi-arrow-right me-1"></i>Voir les fournisseurs
                </a>
            </div>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    // Insérer après la section des résultats
    const resultsCard = document.getElementById('resultsCard');
    resultsCard.insertAdjacentHTML('afterend', notificationHtml);
}

// 🆕 NOUVELLE FONCTION : Vérifier si c'est un nouveau fournisseur
async function checkIfNewSupplier(supplierName) {
    try {
        // Appel API pour vérifier si le fournisseur existait avant ce scan
        const response = await fetch(`/api/suppliers/check-new/${encodeURIComponent(supplierName)}`);
        
        if (response.ok) {
            const result = await response.json();
            
            if (result.is_new) {
                showNewSupplierNotification(supplierName);
            }
        }
    } catch (error) {
        console.log('Impossible de vérifier le statut du fournisseur:', error);
        // Pas grave, on continue sans notification
    }
}

// 🆕 NOUVELLE FONCTION : Notification pour nouveau fournisseur
function showNewSupplierNotification(supplierName) {
    const notificationHtml = `
        <div class="alert alert-primary alert-dismissible fade show mt-3" role="alert">
            <h6 class="alert-heading">
                <i class="bi bi-building-add me-2"></i>Nouveau fournisseur créé !
            </h6>
            <p class="mb-2">
                Le fournisseur <strong>${supplierName}</strong> a été créé automatiquement lors de ce scan.
            </p>
            <hr>
            <div class="d-flex justify-content-between align-items-center">
                <small class="text-muted">
                    <i class="bi bi-info-circle me-1"></i>Vous pouvez maintenant configurer ses informations de livraison et valider ses produits.
                </small>
                <a href="/fournisseurs" class="btn btn-sm btn-outline-primary">
                    <i class="bi bi-gear me-1"></i>Configurer le fournisseur
                </a>
            </div>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    // Insérer après la section des résultats
    const resultsCard = document.getElementById('resultsCard');
    resultsCard.insertAdjacentHTML('afterend', notificationHtml);
}

// Sauvegarder la facture
async function saveInvoice() {
    if (!analysisResult) return;
    
    try {
        // La facture est déjà sauvegardée lors de l'analyse
        showNotification('Facture enregistrée avec succès !', 'success');
        
        // Rediriger vers l'historique après 2 secondes
        setTimeout(() => {
            window.location.href = '/factures';
        }, 2000);
        
    } catch (error) {
        showNotification('Erreur lors de l\'enregistrement', 'error');
    }
}

// Afficher le modal des produits en attente
function showPendingProductsModal(data) {
    const modal = new bootstrap.Modal(document.getElementById('pendingProductsModal'));
    const listContainer = document.getElementById('pendingProductsList');
    
    // Lister les nouveaux produits
    const newProducts = data.products.filter((product, index) => {
        const comparison = data.price_comparison?.products_details?.[index];
        return comparison?.status === 'new';
    });
    
    if (newProducts.length > 0) {
        let html = '<ul class="list-group">';
        newProducts.forEach(product => {
            html += `
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${product.name}</strong>
                        <small class="text-muted d-block">${product.quantity} ${product.unit || ''}</small>
                    </div>
                    <span class="badge bg-primary rounded-pill">${Utils.formatCurrency(product.unit_price)}</span>
                </li>
            `;
        });
        html += '</ul>';
        listContainer.innerHTML = html;
        
        modal.show();
    }
}

// Réinitialiser le scanner
function resetScanner() {
    currentFile = null;
    analysisResult = null;
    
    document.getElementById('fileInput').value = '';
    document.getElementById('imagePreview').classList.add('d-none');
    document.getElementById('dropZone').style.display = '';
    document.getElementById('resultsCard').classList.add('d-none');
    document.getElementById('tipsCard').classList.remove('d-none');
    
    showProgress(false);
}

// Export global
window.resetScanner = resetScanner;

// Vérifier le mode vérification de commande
async function checkVerifyOrderMode() {
    const urlParams = new URLSearchParams(window.location.search);
    const verifyOrderId = urlParams.get('verify_order');
    
    if (verifyOrderId) {
        try {
            // Charger les infos de la commande
            const response = await fetch(`/api/orders/${verifyOrderId}`);
            const result = await response.json();
            
            if (result.success) {
                const order = result.data;
                showVerificationAlert(order);
            }
        } catch (error) {
            console.error('Erreur chargement commande:', error);
        }
    }
}

// Afficher l'alerte de vérification
function showVerificationAlert(order) {
    const alertHtml = `
        <div class="alert alert-warning alert-dismissible fade show" id="verificationAlert">
            <h6 class="alert-heading">
                <i class="bi bi-exclamation-triangle me-2"></i>Mode Vérification de Commande
            </h6>
            <p class="mb-2">
                <strong>Attention :</strong> Vous êtes en train de vérifier la commande 
                <strong>${order.order_number}</strong> de <strong>${order.supplier}</strong>
            </p>
            <hr>
            <div class="row">
                <div class="col-md-6">
                    <small class="text-muted">
                        <i class="bi bi-calendar me-1"></i>Livraison prévue : ${formatDate(order.delivery_date)}<br>
                        <i class="bi bi-box me-1"></i>Produits commandés : ${order.products?.length || 0}<br>
                        <i class="bi bi-currency-euro me-1"></i>Montant : ${formatPrice(order.total_amount || 0)}
                    </small>
                </div>
                <div class="col-md-6 text-end">
                    <button class="btn btn-sm btn-outline-primary me-2" onclick="showOrderDetails('${order.id}')">
                        <i class="bi bi-eye me-1"></i>Voir la commande
                    </button>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            </div>
        </div>
    `;
    
    // Insérer l'alerte au début du container
    const container = document.querySelector('.container-fluid');
    const firstChild = container.firstElementChild;
    const alertDiv = document.createElement('div');
    alertDiv.innerHTML = alertHtml;
    container.insertBefore(alertDiv.firstElementChild, firstChild);
}

// Afficher les détails de la commande (modal simple)
function showOrderDetails(orderId) {
    // Rediriger vers la page commandes avec focus sur cette commande
    window.open(`/commandes#order-${orderId}`, '_blank');
}

// Fonctions utilitaires
function formatDate(dateString) {
    if (!dateString) return '-';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('fr-FR');
    } catch (e) {
        return '-';
    }
}

function formatPrice(price) {
    if (!price && price !== 0) return '0,00 €';
    const numPrice = parseFloat(price);
    if (isNaN(numPrice)) return '0,00 €';
    return numPrice.toFixed(2).replace('.', ',') + ' €';
}

// Afficher l'aperçu de l'image scannée
function previewScanImage(event) {
    const input = event.target;
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('scanPreviewImg').src = e.target.result;
            document.getElementById('scanPreview').style.display = 'block';
        };
        reader.readAsDataURL(input.files[0]);
    } else {
        document.getElementById('scanPreview').style.display = 'none';
    }
} 