// FactureKiller V3 - Module Factures (Version Minimaliste)

let currentPage = 1;
let currentFilters = {
    supplier: '',
    date_from: '',
    date_to: '',
    anomalies: ''
};

let currentInvoiceData = null;
let currentInvoiceId = null;

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    console.log('🔧 Initialisation module Factures...');
    
    if (!document.getElementById('invoicesTable')) {
        console.error('❌ Element invoicesTable non trouvé');
        return;
    }
    
    initializeEventListeners();
    loadInvoices();
    updatePageTitle();
});

function initializeEventListeners() {
    // Filtres
    const supplierFilter = document.getElementById('supplierFilter');
    if (supplierFilter) {
        supplierFilter.addEventListener('change', (e) => {
            currentFilters.supplier = e.target.value;
            currentPage = 1;
            loadInvoices();
        });
    }
    
    const dateFromFilter = document.getElementById('dateFromFilter');
    if (dateFromFilter) {
        dateFromFilter.addEventListener('change', (e) => {
            currentFilters.date_from = e.target.value;
            currentPage = 1;
            loadInvoices();
        });
    }
    
    const dateToFilter = document.getElementById('dateToFilter');
    if (dateToFilter) {
        dateToFilter.addEventListener('change', (e) => {
            currentFilters.date_to = e.target.value;
            currentPage = 1;
            loadInvoices();
        });
    }
    
    const anomaliesFilter = document.getElementById('anomaliesFilter');
    if (anomaliesFilter) {
        anomaliesFilter.addEventListener('change', (e) => {
            currentFilters.anomalies = e.target.value;
            currentPage = 1;
            loadInvoices();
        });
    }
}

// Charger les factures (version simplifiée)
async function loadInvoices() {
    try {
        console.log('📄 Chargement des factures...');
        
        const tableBody = document.querySelector('#invoicesTable tbody');
        if (tableBody) {
            showLoader();
        }
        
        const params = {
            page: currentPage,
            per_page: 20,
            supplier: currentFilters.supplier,
            date_from: currentFilters.date_from,
            date_to: currentFilters.date_to,
            anomalies: currentFilters.anomalies
        };
        
        const url = new URL('/api/invoices', window.location.origin);
        Object.keys(params).forEach(key => {
            if (params[key]) url.searchParams.append(key, params[key]);
        });
        
        const response = await fetch(url);
        const data = await response.json();
        console.log('📄 Données factures reçues:', data);
        
        if (data && data.success) {
            // Affichage contexte restaurant simplifié
            displaySimpleRestaurantContext(data.restaurant_context, data.restaurant_id);
            
            // Mettre à jour le titre avec le nom du restaurant
            if (data.restaurant_context) {
                updatePageTitle(data.restaurant_context);
            }
            
            displayInvoices(data.data || []);
            
            // Pagination
            const paginationContainer = document.getElementById('invoicesPagination');
            if (paginationContainer) {
                if (data.pages > 1) {
                    createSimplePagination(paginationContainer, data.page, data.pages);
                } else {
                    paginationContainer.innerHTML = '';
                }
            }
            
            // Compteur simple
            const invoicesCount = document.getElementById('invoicesCount');
            if (invoicesCount) {
                invoicesCount.textContent = data.total || 0;
            }
            
        } else {
            console.error('❌ Erreur données factures:', data);
            
            if (data.error && data.error.includes('restaurant')) {
                // Afficher l'erreur de restaurant dans le tableau
                const tbody = document.querySelector('#invoicesTable tbody');
                if (tbody) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="6" class="text-center py-5">
                                <div class="alert alert-warning">
                                    <i class="bi bi-exclamation-triangle me-2"></i>
                                    ${data.error}
                                </div>
                            </td>
                        </tr>
                    `;
                }
            } else {
                displayInvoices([]);
            }
        }
    } catch (error) {
        console.error('❌ Erreur chargement factures:', error);
        displayInvoices([]);
    }
}

// Afficher les factures
function displayInvoices(invoices) {
    const tbody = document.querySelector('#invoicesTable tbody');
    if (!tbody) {
        console.error('❌ Table factures tbody non trouvé');
        return;
    }
    
    if (!invoices || invoices.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-4 text-muted">
                    <i class="bi bi-inbox fs-1"></i>
                    <p class="mt-2">Aucune facture trouvée</p>
                    <small>Scannez votre première facture pour commencer</small>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = invoices.map(invoice => {
        const analysis = invoice.analysis || {};
        
        // 🎯 AFFICHAGE DU CODE FCT-XXXX-XXXX
        const invoiceCode = invoice.invoice_code || `FCT-${invoice.id}`;
        
        // 🎯 DATE DE SCAN (pas date facture)
        const scanDate = invoice.scan_date || invoice.created_at;
        
        // 🎯 GESTION DES ANOMALIES COMPLÈTE
        let anomaliesBadge = '<span class="badge bg-success"><i class="bi bi-check-circle"></i> Aucune</span>';
        let statusBadge = '<span class="badge bg-success">✅ Validée</span>';
        
        if (invoice.has_anomalies && invoice.anomalies_count > 0) {
            const count = invoice.anomalies_count || invoice.anomalies?.length || 0;
            const severity = invoice.priority === 'high' ? 'danger' : 'warning';
            
            anomaliesBadge = `<span class="badge bg-${severity}"><i class="bi bi-exclamation-triangle"></i> ${count}</span>`;
            statusBadge = `<span class="badge bg-${severity}">⚠️ ${invoice.anomaly_status === 'pending' ? 'En attente' : 'À traiter'}</span>`;
        }
        
        // 🎯 WORKFLOW STATUS
        let workflowBadge = statusBadge;
        if (invoice.workflow_status === 'validated') {
            workflowBadge = '<span class="badge bg-success">✅ Validée</span>';
        } else if (invoice.validation_required) {
            workflowBadge = '<span class="badge bg-warning">⏳ Validation requise</span>';
        }
        
        return `
            <tr ${invoice.has_anomalies ? 'class="table-warning"' : ''} onclick="viewInvoice('${invoice.id}')" style="cursor: pointer;">
                <td>
                    <strong class="text-primary">${invoiceCode}</strong>
                    ${invoice.is_multipage ? '<span class="badge bg-info ms-1">Multi-pages</span>' : ''}
                </td>
                <td>
                    <small class="text-muted">${formatDate(scanDate)}</small><br>
                    <small class="text-muted">${formatTime(scanDate)}</small>
                </td>
                <td><span class="badge bg-secondary">${analysis.supplier || analysis.fournisseur || 'Inconnu'}</span></td>
                <td><code>${analysis.invoice_number || analysis.numero_facture || invoice.id}</code></td>
                <td class="fw-bold">${formatPrice(analysis.total_amount || analysis.montant_total || 0)}</td>
                <td>${anomaliesBadge}</td>
                <td>${workflowBadge}</td>
                <td onclick="event.stopPropagation();">
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="viewInvoice('${invoice.id}')" 
                                title="Voir le détail">
                            <i class="bi bi-eye"></i>
                        </button>
                        ${invoice.has_anomalies ? 
                            `<button class="btn btn-outline-warning" onclick="viewAnomalies('${invoice.id}')" 
                                     title="Gérer les anomalies">
                                <i class="bi bi-exclamation-triangle"></i>
                            </button>` : ''}
                        <button class="btn btn-outline-secondary" onclick="downloadInvoice('${invoice.id}')"
                                title="Télécharger">
                            <i class="bi bi-download"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// 🎯 NOUVELLE FONCTION POUR FORMATER L'HEURE
function formatTime(dateString) {
    if (!dateString) return '';
    try {
        const date = new Date(dateString);
        return date.toLocaleTimeString('fr-FR', { 
            hour: '2-digit', 
            minute: '2-digit'
        });
    } catch {
        return '';
    }
}

// 🎯 NOUVELLE FONCTION POUR GÉRER LES ANOMALIES
async function viewAnomalies(invoiceId) {
    console.log(`🚨 Gestion des anomalies pour facture ${invoiceId}`);
    
    try {
        // Rediriger vers la page d'anomalies avec filtre sur cette facture
        window.location.href = `/anomalies?invoice=${invoiceId}`;
    } catch (error) {
        console.error('❌ Erreur ouverture anomalies:', error);
        showNotification('Erreur lors de l\'ouverture des anomalies', 'error');
    }
}

// Afficher le loader
function showLoader() {
    const tbody = document.querySelector('#invoicesTable tbody');
    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-5">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Chargement...</span>
                    </div>
                </td>
            </tr>
        `;
    }
}

// Fonctions utilitaires
function formatPrice(price) {
    if (!price && price !== 0) return '0,00 €';
    return new Intl.NumberFormat('fr-FR', {
        style: 'currency',
        currency: 'EUR'
    }).format(price);
}

function formatDate(dateString) {
    if (!dateString) return '-';
    try {
        const date = new Date(dateString);
        return new Intl.DateTimeFormat('fr-FR').format(date);
    } catch (e) {
        return '-';
    }
}

// Créer une pagination simple
function createSimplePagination(container, currentPageNum, totalPages) {
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    let paginationHtml = '<nav aria-label="Navigation des factures"><ul class="pagination justify-content-center">';
    
    // Bouton précédent
    paginationHtml += `<li class="page-item ${currentPageNum === 1 ? 'disabled' : ''}">
        <a class="page-link" href="#" onclick="goToPage(${currentPageNum - 1}); return false;">Précédent</a>
    </li>`;
    
    // Pages
    for (let i = 1; i <= totalPages; i++) {
        if (i === currentPageNum) {
            paginationHtml += `<li class="page-item active">
                <span class="page-link">${i}</span>
            </li>`;
        } else {
            paginationHtml += `<li class="page-item">
                <a class="page-link" href="#" onclick="goToPage(${i}); return false;">${i}</a>
            </li>`;
        }
    }
    
    // Bouton suivant
    paginationHtml += `<li class="page-item ${currentPageNum === totalPages ? 'disabled' : ''}">
        <a class="page-link" href="#" onclick="goToPage(${currentPageNum + 1}); return false;">Suivant</a>
    </li>`;
    
    paginationHtml += '</ul></nav>';
    
    container.innerHTML = paginationHtml;
}

// Aller à une page spécifique
function goToPage(page) {
    currentPage = page;
    loadInvoices();
}

// Voir le détail d'une facture
async function viewInvoice(invoiceId) {
    try {
        console.log('👁️ Affichage facture:', invoiceId);
        
        const response = await fetch(`/api/invoices/${invoiceId}`);
        const data = await response.json();
        
        if (data && data.success) {
            showInvoiceModal(data.data);
        } else {
            showNotification('Facture non trouvée', 'error');
        }
    } catch (error) {
        console.error('❌ Erreur affichage facture:', error);
        showNotification('Erreur lors de l\'affichage', 'error');
    }
}

// Afficher la modal de détail
function showInvoiceModal(invoice) {
    const analysis = invoice.analysis || {};
    const priceAnalysis = analysis.price_analysis || {};
    
    // Remplir les informations générales avec les bons IDs
    const detailInvoiceNumber = document.getElementById('detailInvoiceNumber');
    const detailSupplier = document.getElementById('detailSupplier');
    const detailDate = document.getElementById('detailDate');
    const detailTotal = document.getElementById('detailTotal');
    
    if (detailInvoiceNumber) detailInvoiceNumber.textContent = analysis.invoice_number || analysis.numero_facture || invoice.id;
    if (detailSupplier) detailSupplier.textContent = analysis.supplier || analysis.fournisseur || 'Inconnu';
    if (detailDate) detailDate.textContent = formatDate(analysis.date || invoice.created_at);
    if (detailTotal) detailTotal.textContent = formatPrice(analysis.total_amount || analysis.montant_total || 0);
    
    // Afficher la méthode de vérification
    const verificationInfo = document.getElementById('detailVerificationMethod');
    if (verificationInfo) {
        const verificationMethod = analysis.verification_method || 'scan';
        const verificationBadge = getVerificationBadge(verificationMethod);
        const verificationDate = analysis.verified_at || analysis.created_at || invoice.created_at;
        
        verificationInfo.innerHTML = `
            <div class="d-flex align-items-center">
                ${verificationBadge}
                <small class="text-muted ms-2">
                    ${formatDate(verificationDate)}
                    ${analysis.verified_by ? ` par ${analysis.verified_by}` : ''}
                </small>
            </div>
            ${analysis.verification_notes ? `<small class="text-muted mt-1">${analysis.verification_notes}</small>` : ''}
        `;
    }
    
    // 🚨 AFFICHER LES ANOMALIES
    const anomaliesSection = document.getElementById('anomaliesSection');
    const detailAnomalies = document.getElementById('detailAnomalies');
    
    if (invoice.has_anomalies && invoice.anomalies && Array.isArray(invoice.anomalies) && invoice.anomalies.length > 0) {
        // Afficher la section anomalies
        if (anomaliesSection) anomaliesSection.style.display = 'block';
        
        if (detailAnomalies) {
            let anomaliesHtml = '';
            
            invoice.anomalies.forEach(anomaly => {
                // Vérifier que l'anomalie a bien la structure attendue
                if (!anomaly || !Array.isArray(anomaly.anomalies)) {
                    console.warn('Structure d\'anomalie invalide:', anomaly);
                    return;
                }
                anomaliesHtml += `
                    <div class="alert alert-warning mb-2">
                        <h6 class="alert-heading">
                            <i class="bi bi-exclamation-triangle"></i> 
                            Produit: ${anomaly.product}
                        </h6>
                        <div class="row">
                `;
                
                anomaly.anomalies.forEach(item => {
                    const severityClass = item.severity === 'critical' ? 'danger' : 'warning';
                    const severityIcon = item.severity === 'critical' ? 'exclamation-circle-fill' : 'exclamation-triangle-fill';
                    
                    anomaliesHtml += `
                        <div class="col-md-6 mb-2">
                            <div class="d-flex align-items-center">
                                <span class="badge bg-${severityClass} me-2">
                                    <i class="bi bi-${severityIcon}"></i>
                                    ${item.severity === 'critical' ? 'Critique' : 'Avertissement'}
                                </span>
                                <small class="text-muted">${item.type}</small>
                            </div>
                            <div class="mt-1">
                                <strong>${item.message}</strong>
                            </div>
                            ${item.expected !== undefined && item.received !== undefined ? `
                                <div class="mt-1">
                                    <small class="text-muted">
                                        Attendu: <span class="fw-bold">${item.type === 'price' ? formatPrice(item.expected) : item.expected}</span> | 
                                        Reçu: <span class="fw-bold">${item.type === 'price' ? formatPrice(item.received) : item.received}</span>
                                    </small>
                                </div>
                            ` : ''}
                        </div>
                    `;
                });
                
                anomaliesHtml += `
                        </div>
                    </div>
                `;
            });
            
            // Ajouter les actions de résolution
            anomaliesHtml += `
                <div class="d-flex gap-2 mt-3">
                    ${invoice.anomaly_status !== 'resolved' ? `
                        <button class="btn btn-success btn-sm" onclick="resolveAnomaly('${invoice.id}')">
                            <i class="bi bi-check-circle"></i> Marquer comme résolue
                        </button>
                        <button class="btn btn-warning btn-sm" onclick="sendAnomalyNotification('${invoice.id}')">
                            <i class="bi bi-envelope"></i> Envoyer notification
                        </button>
                    ` : `
                        <span class="badge bg-success">
                            <i class="bi bi-check-circle"></i> Anomalie résolue
                        </span>
                    `}
                </div>
            `;
            
            detailAnomalies.innerHTML = anomaliesHtml;
        }
    } else {
        // Masquer la section anomalies
        if (anomaliesSection) anomaliesSection.style.display = 'none';
    }
    
    // Afficher l'analyse des prix AMÉLIORÉE
    const priceAnalysisContainer = document.getElementById('detailPriceAnalysis');
    if (priceAnalysisContainer) {
        displayPriceAnalysis(priceAnalysisContainer, analysis);
    }
    
    // Afficher les produits dans le tableau avec écarts
    const productsTableBody = document.querySelector('#detailProductsTable tbody');
    const products = analysis.products || [];
    const priceComparison = analysis.price_comparison || {};
    
    if (productsTableBody) {
        if (products.length === 0) {
            productsTableBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Aucun produit détecté</td></tr>';
        } else {
            productsTableBody.innerHTML = products.map((product, index) => {
                // Chercher les données de comparaison pour ce produit
                const comparison = findProductComparison(product, priceComparison);
                
                return `
                    <tr>
                        <td>
                            <strong>${product.name || product.produit || 'Produit'}</strong>
                            ${product.unit ? `<br><small class="text-muted">Unité: ${product.unit}</small>` : ''}
                        </td>
                        <td>${product.quantity || 1}</td>
                        <td>
                            <div class="d-flex align-items-center">
                                <span class="fw-bold">${formatPrice(product.unit_price || 0)}</span>
                                ${comparison ? renderPriceComparison(comparison) : ''}
                            </div>
                        </td>
                        <td class="fw-bold">${formatPrice(product.total_price || (product.quantity * product.unit_price) || 0)}</td>
                        <td>${renderProductStatus(product, comparison)}</td>
                    </tr>
                `;
            }).join('');
        }
    }
    
    // Afficher la modal
    const modalElement = document.getElementById('invoiceDetailModal');
    if (!modalElement) {
        console.error('Modal invoiceDetailModal not found');
        showNotification('Erreur: Modal non trouvé', 'error');
        return;
    }
    
    if (typeof bootstrap === 'undefined') {
        console.error('Bootstrap not loaded');
        showNotification('Erreur: Bootstrap non chargé', 'error');
        return;
    }
    
    try {
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    } catch (error) {
        console.error('Erreur création modal:', error);
        showNotification('Erreur lors de l\'affichage', 'error');
    }
}

// Nouvelle fonction pour obtenir le badge de méthode de vérification
function getVerificationBadge(method) {
    switch (method) {
        case 'manual':
            return '<span class="badge bg-warning"><i class="bi bi-list-check me-1"></i>Vérifié manuellement</span>';
        case 'scan':
            return '<span class="badge bg-primary"><i class="bi bi-camera me-1"></i>Vérifié par scan</span>';
        default:
            return '<span class="badge bg-secondary"><i class="bi bi-question me-1"></i>Méthode inconnue</span>';
    }
}

// Nouvelle fonction pour afficher l'analyse des prix détaillée
function displayPriceAnalysis(container, analysis) {
    const priceAnalysis = analysis.price_analysis || {};
    const priceComparison = analysis.price_comparison || {};
    
    let html = '<div class="row text-center mb-3">';
    
    // Statistiques générales
    html += `
        <div class="col-3">
            <div class="text-primary fw-bold fs-5">${priceAnalysis.total_products || 0}</div>
            <small>Total produits</small>
        </div>
        <div class="col-3">
            <div class="text-success fw-bold fs-5">${priceAnalysis.matched_products || 0}</div>
            <small>Connus</small>
        </div>
        <div class="col-3">
            <div class="text-info fw-bold fs-5">${priceAnalysis.new_products || 0}</div>
            <small>Nouveaux</small>
        </div>
        <div class="col-3">
            <div class="text-warning fw-bold fs-5">${(priceAnalysis.price_variations || []).length}</div>
            <small>Écarts prix</small>
        </div>
    `;
    html += '</div>';
    
    // Détails des écarts de prix si disponibles
    if (priceAnalysis.price_variations && priceAnalysis.price_variations.length > 0) {
        html += '<div class="mt-3"><h6><i class="bi bi-exclamation-triangle text-warning"></i> Écarts de prix détectés</h6>';
        html += '<div class="table-responsive"><table class="table table-sm">';
        html += '<thead><tr><th>Produit</th><th>Prix Facture</th><th>Prix Référence</th><th>Écart</th><th>%</th></tr></thead><tbody>';
        
        priceAnalysis.price_variations.forEach(variation => {
            const percentDiff = variation.percentage_difference || 0;
            const priceDiff = variation.price_difference || 0;
            const diffClass = priceDiff > 0 ? 'text-danger' : 'text-success';
            
            html += `
                <tr>
                    <td>${variation.product_name || 'Produit'}</td>
                    <td class="fw-bold">${formatPrice(variation.invoice_price || 0)}</td>
                    <td>${formatPrice(variation.reference_price || 0)}</td>
                    <td class="${diffClass} fw-bold">${priceDiff > 0 ? '+' : ''}${formatPrice(priceDiff)}</td>
                    <td class="${diffClass} fw-bold">${percentDiff > 0 ? '+' : ''}${percentDiff.toFixed(1)}%</td>
                </tr>
            `;
        });
        
        html += '</tbody></table></div></div>';
    }
    
    // Résumé financier des écarts
    const totalOverpayment = (priceAnalysis.price_variations || [])
        .filter(v => (v.price_difference || 0) > 0)
        .reduce((sum, v) => sum + (v.price_difference * v.quantity || 0), 0);
        
    const totalSavings = Math.abs((priceAnalysis.price_variations || [])
        .filter(v => (v.price_difference || 0) < 0)
        .reduce((sum, v) => sum + (v.price_difference * v.quantity || 0), 0));
    
    if (totalOverpayment > 0 || totalSavings > 0) {
        html += '<div class="mt-3 p-3 bg-light rounded">';
        html += '<div class="row text-center">';
        if (totalSavings > 0) {
            html += `<div class="col-6"><div class="text-success fw-bold">${formatPrice(totalSavings)}</div><small>Économies réalisées</small></div>`;
        }
        if (totalOverpayment > 0) {
            html += `<div class="col-6"><div class="text-danger fw-bold">${formatPrice(totalOverpayment)}</div><small>Surpaiement détecté</small></div>`;
        }
        html += '</div></div>';
    }
    
    container.innerHTML = html;
}

// Trouver les données de comparaison pour un produit
function findProductComparison(product, priceComparison) {
    if (!priceComparison.price_variations) return null;
    
    return priceComparison.price_variations.find(variation => 
        variation.product_name === product.name || 
        variation.product_name.toLowerCase().includes(product.name.toLowerCase()) ||
        product.name.toLowerCase().includes(variation.product_name.toLowerCase())
    );
}

// Rendu de la comparaison de prix
function renderPriceComparison(comparison) {
    if (!comparison) return '';
    
    const priceDiff = comparison.price_difference || 0;
    if (Math.abs(priceDiff) < 0.01) return '';
    
    const diffClass = priceDiff > 0 ? 'text-danger' : 'text-success';
    const icon = priceDiff > 0 ? 'arrow-up' : 'arrow-down';
    
    return `
        <div class="ms-2">
            <small class="${diffClass}">
                <i class="bi bi-${icon}"></i>
                ${priceDiff > 0 ? '+' : ''}${formatPrice(priceDiff)}
            </small>
        </div>
    `;
}

// Rendu du statut du produit
function renderProductStatus(product, comparison) {
    if (!comparison) {
        return '<span class="badge bg-info">Nouveau</span>';
    }
    
    const priceDiff = comparison.price_difference || 0;
    const percentDiff = Math.abs(comparison.percentage_difference || 0);
    
    if (Math.abs(priceDiff) < 0.01) {
        return '<span class="badge bg-success">Prix identique</span>';
    } else if (priceDiff > 0) {
        if (percentDiff > 20) {
            return '<span class="badge bg-danger">Très cher</span>';
        } else if (percentDiff > 10) {
            return '<span class="badge bg-warning">Plus cher</span>';
        } else {
            return '<span class="badge bg-warning text-dark">Légère hausse</span>';
        }
    } else {
        if (percentDiff > 20) {
            return '<span class="badge bg-success">Très avantageux</span>';
        } else if (percentDiff > 10) {
            return '<span class="badge bg-success">Moins cher</span>';
        } else {
            return '<span class="badge bg-success text-dark">Légère baisse</span>';
        }
    }
}

// Télécharger une facture
function downloadInvoice(invoiceId) {
    // TODO: Implémenter le téléchargement
    showNotification('Fonctionnalité à implémenter', 'info');
}

// Réinitialiser les filtres
function resetFilters() {
    const supplierFilter = document.getElementById('supplierFilter');
    const dateFromFilter = document.getElementById('dateFromFilter');
    const dateToFilter = document.getElementById('dateToFilter');
    
    if (supplierFilter) supplierFilter.value = '';
    if (dateFromFilter) dateFromFilter.value = '';
    if (dateToFilter) dateToFilter.value = '';
    
    currentFilters = {
        supplier: '',
        date_from: '',
        date_to: '',
        anomalies: ''
    };
    
    currentPage = 1;
    loadInvoices();
}

// Appliquer les filtres
function applyFilters() {
    const supplierFilter = document.getElementById('supplierFilter');
    const dateFromFilter = document.getElementById('dateFromFilter');
    const dateToFilter = document.getElementById('dateToFilter');
    
    currentFilters = {
        supplier: supplierFilter ? supplierFilter.value : '',
        date_from: dateFromFilter ? dateFromFilter.value : '',
        date_to: dateToFilter ? dateToFilter.value : '',
        anomalies: ''
    };
    
    currentPage = 1;
    loadInvoices();
}

// 🚨 FONCTIONS GESTION ANOMALIES

async function resolveAnomaly(invoiceId) {
    const notes = prompt('Notes de résolution (optionnel):');
    if (notes === null) return; // Annulé
    
    try {
        const response = await fetch(`/api/anomalies/resolve/${invoiceId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                notes: notes,
                resolved_by: 'user'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            Utils.showNotification('Anomalie marquée comme résolue', 'success');
            loadInvoices(); // Recharger la liste
        } else {
            Utils.showNotification(result.error || 'Erreur lors de la résolution', 'error');
        }
    } catch (error) {
        console.error('Erreur résolution anomalie:', error);
        Utils.showNotification('Erreur lors de la résolution', 'error');
    }
}

async function sendAnomalyNotification(invoiceId) {
    const email = prompt('Email de destination (laisser vide pour utiliser l\'email par défaut):');
    if (email === null) return; // Annulé
    
    const message = prompt('Message personnalisé (optionnel):');
    if (message === null) return; // Annulé
    
    try {
        const response = await fetch(`/api/anomalies/send-notification/${invoiceId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: email,
                message: message
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            Utils.showNotification('Notification d\'anomalie envoyée', 'success');
        } else {
            Utils.showNotification(result.error || 'Erreur lors de l\'envoi', 'error');
        }
    } catch (error) {
        console.error('Erreur envoi notification:', error);
        Utils.showNotification('Erreur lors de l\'envoi', 'error');
    }
}

// Charger les statistiques d'anomalies pour le dashboard
async function loadAnomaliesStats() {
    try {
        const response = await fetch('/api/anomalies/stats');
        const data = await response.json();
        
        if (data.success) {
            updateAnomaliesStatsDisplay(data.data);
        }
    } catch (error) {
        console.error('Erreur chargement stats anomalies:', error);
    }
}

function updateAnomaliesStatsDisplay(stats) {
    // Mettre à jour les éléments du dashboard si ils existent
    const anomaliesRate = document.getElementById('anomaliesRate');
    if (anomaliesRate) {
        anomaliesRate.textContent = `${stats.anomaly_rate}%`;
    }
    
    const criticalAnomalies = document.getElementById('criticalAnomalies');
    if (criticalAnomalies) {
        criticalAnomalies.textContent = stats.critical_anomalies;
    }
    
    const invoicesWithAnomalies = document.getElementById('invoicesWithAnomalies');
    if (invoicesWithAnomalies) {
        invoicesWithAnomalies.textContent = stats.invoices_with_anomalies;
    }
}

// 🏢 AFFICHER LE CONTEXTE RESTAURANT SIMPLIFIÉ
function displaySimpleRestaurantContext(restaurantName, restaurantId) {
    let contextContainer = document.getElementById('restaurantContext');
    
    if (!contextContainer) {
        const mainContent = document.querySelector('.container-fluid');
        if (mainContent) {
            contextContainer = document.createElement('div');
            contextContainer.id = 'restaurantContext';
            contextContainer.className = 'alert alert-info d-flex align-items-center mb-3';
            mainContent.insertBefore(contextContainer, mainContent.firstChild);
        }
    }
    
    if (contextContainer) {
        if (restaurantName) {
            contextContainer.innerHTML = `
                <div class="me-3">
                    <i class="bi bi-building text-primary fs-5"></i>
                </div>
                <div class="flex-grow-1">
                    <strong>${restaurantName}</strong>
                    <small class="text-muted ms-2">• Factures filtrées par restaurant</small>
                </div>
            `;
            contextContainer.className = 'alert alert-info d-flex align-items-center mb-3';
        } else {
            contextContainer.innerHTML = `
                <div class="me-3">
                    <i class="bi bi-exclamation-triangle text-warning fs-5"></i>
                </div>
                <div class="flex-grow-1">
                    <strong>Aucun restaurant sélectionné</strong>
                    <small class="text-muted ms-2">• Toutes les factures</small>
                </div>
            `;
            contextContainer.className = 'alert alert-warning d-flex align-items-center mb-3';
        }
    }
    
    console.log('🏢 Restaurant:', restaurantName, '(ID:', restaurantId, ')');
}

// Masquer le conteneur de stats s'il existe
function hideStatsContainer() {
    const statsContainer = document.getElementById('restaurantStats');
    if (statsContainer) {
        statsContainer.style.display = 'none';
    }
}

// 🔧 FONCTIONS DE DEBUG
function toggleRestaurantDetails() {
    // Afficher/masquer les détails du restaurant
    const contextContainer = document.getElementById('restaurantContext');
    if (!contextContainer) return;
    
    const detailsContainer = document.getElementById('restaurantDetails');
    
    if (!detailsContainer) {
        // Créer le conteneur de détails
        const details = document.createElement('div');
        details.id = 'restaurantDetails';
        details.className = 'mt-3 p-3 bg-light rounded';
        details.innerHTML = `
            <h6><i class="bi bi-info-circle"></i> Informations de filtrage</h6>
            <div id="debugInfo"></div>
        `;
        contextContainer.appendChild(details);
    }
    
    detailsContainer.style.display = detailsContainer.style.display === 'none' ? 'block' : 'none';
}

function updatePageTitle(restaurantName = null) {
    const title = document.querySelector('h1') || document.querySelector('.page-title') || document.querySelector('.breadcrumb-item.active');
    if (title) {
        const baseTitle = "Factures";
        if (restaurantName) {
            title.textContent = `${baseTitle} - ${restaurantName}`;
        } else {
            title.textContent = baseTitle;
        }
    }
}

// 🔧 FONCTION DE CORRECTION TEMPORAIRE
async function fixInvoicesRestaurant() {
    try {
        console.log('🔧 Correction des factures...');
        
        const response = await fetch('/api/debug/fix-invoices-restaurant', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        console.log('🔧 Résultat correction:', result);
        
        if (result.success) {
            alert(`✅ ${result.fixed_count} facture(s) corrigée(s) pour ${result.restaurant}`);
            // Recharger les factures
            loadInvoices();
        } else {
            alert(`❌ Erreur: ${result.error}`);
        }
        
    } catch (error) {
        console.error('❌ Erreur correction factures:', error);
        alert('❌ Erreur lors de la correction');
    }
}

// Ajouter le bouton de correction temporaire
document.addEventListener('DOMContentLoaded', () => {
    // Attendre que le DOM soit chargé
    setTimeout(() => {
        const container = document.querySelector('.row .col-12') || document.querySelector('.container-fluid');
        if (container) {
            const fixButton = document.createElement('button');
            fixButton.className = 'btn btn-warning btn-sm mb-3';
            fixButton.innerHTML = '<i class="bi bi-tools"></i> Corriger Factures Restaurant';
            fixButton.onclick = fixInvoicesRestaurant;
            
            // Insérer le bouton au début
            container.insertBefore(fixButton, container.firstChild);
        }
    }, 1000);
});

// Fonction de notification
function showNotification(message, type = 'info') {
    // Créer l'élément de notification
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="bi bi-${type === 'error' ? 'exclamation-triangle' : 'check-circle'} me-2"></i>
            <span>${message}</span>
        </div>
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Ajouter l'élément à la page
    const notificationContainer = document.getElementById('notificationContainer');
    if (notificationContainer) {
        notificationContainer.appendChild(notification);
    } else {
        console.error('Notification container not found');
    }
    
    // Supprimer l'élément après 3 secondes
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// 🔧 FONCTION DE CORRECTION TEMPORAIRE
async function fixInvoicesRestaurant() {
    try {
        console.log('🔧 Correction des factures...');
        
        const response = await fetch('/api/debug/fix-invoices-restaurant', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        console.log('🔧 Résultat correction:', result);
        
        if (result.success) {
            alert(`✅ ${result.fixed_count} facture(s) corrigée(s) pour ${result.restaurant}`);
            // Recharger les factures
            loadInvoices();
        } else {
            alert(`❌ Erreur: ${result.error}`);
        }
        
    } catch (error) {
        console.error('❌ Erreur correction factures:', error);
        alert('❌ Erreur lors de la correction');
    }
}

// Ajouter le bouton de correction temporaire
document.addEventListener('DOMContentLoaded', () => {
    // Attendre que le DOM soit chargé
    setTimeout(() => {
        const container = document.querySelector('.row .col-12') || document.querySelector('.container-fluid');
        if (container) {
            const fixButton = document.createElement('button');
            fixButton.className = 'btn btn-warning btn-sm mb-3';
            fixButton.innerHTML = '<i class="bi bi-tools"></i> Corriger Factures Restaurant';
            fixButton.onclick = fixInvoicesRestaurant;
            
            // Insérer le bouton au début
            container.insertBefore(fixButton, container.firstChild);
        }
    }, 1000);
});