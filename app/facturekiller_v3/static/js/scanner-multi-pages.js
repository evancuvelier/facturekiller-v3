/**
 * 🎯 SYSTÈME QUEUE MULTI-FACTURES - Intégré au Scanner Existant
 * Ce script étend le scanner existant avec les fonctionnalités de queue
 */

// Variables globales pour la queue
window.invoiceQueue = [];
window.currentInvoiceId = null;
let nextInvoiceId = 1;

// Statuts possibles des factures
const INVOICE_STATUS = {
    PENDING: 'pending',      // En attente
    PROCESSING: 'processing', // En cours de traitement
    COMPLETED: 'completed',   // Terminé
    ERROR: 'error'           // Erreur
};

/**
 * 🔧 FONCTIONS DE GESTION DE LA QUEUE
 */

// Ajouter la facture courante à la queue
function addToQueue() {
    console.log('📥 Ajout à la file d\'attente...');
    
    // Vérifier qu'il y a des pages
    if (!window.scanner || !window.scanner.currentPages || window.scanner.currentPages.length === 0) {
        showToast('❌ Aucune page à ajouter', 'warning');
        return;
    }
    
    // Générer un ID unique pour cette facture
    const invoiceId = `INV-${String(nextInvoiceId).padStart(3, '0')}`;
    nextInvoiceId++;
    
    // Créer l'objet facture
    const invoice = {
        id: invoiceId,
        name: `Facture ${invoiceId}`,
        pages: [...window.scanner.currentPages], // Copie des pages
        status: INVOICE_STATUS.PENDING,
        createdAt: new Date(),
        result: null,
        error: null
    };
    
    // Ajouter à la queue
    window.invoiceQueue.push(invoice);
    
    // Mettre à jour l'interface
    updateQueueDisplay();
    updateQueueButtons();
    
    // Réinitialiser le scanner pour une nouvelle facture
    resetScanner();
    
    showToast(`✅ ${invoice.name} ajoutée à la file`, 'success');
    console.log(`📋 Facture ${invoiceId} ajoutée:`, invoice);
}

// Traiter une facture spécifique de la queue
async function processInvoiceFromQueue(invoiceId) {
    console.log(`🚀 Traitement de la facture ${invoiceId}`);
    
    const invoice = window.invoiceQueue.find(inv => inv.id === invoiceId);
    if (!invoice) {
        console.error('Facture non trouvée:', invoiceId);
        return;
    }
    
    // Mettre à jour le statut
    invoice.status = INVOICE_STATUS.PROCESSING;
    updateQueueDisplay();
    
    // Afficher l'overlay de traitement
    showProcessingOverlay(`Analyse de ${invoice.name}...`);
    
    try {
        // Préparer les données pour l'analyse
        const formData = new FormData();
        
        // Ajouter chaque page
        invoice.pages.forEach((pageData, index) => {
            // Convertir base64 en blob
            const blob = base64ToBlob(pageData.data, pageData.type);
            formData.append('pages', blob, `page_${index + 1}.${pageData.type.split('/')[1]}`);
        });
        
        // Indiquer que c'est un mode multi-pages
        formData.append('multipage', 'true');
        
        // Envoyer pour analyse
        const response = await fetch('/api/invoices/analyze', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Erreur HTTP: ${response.status}`);
        }
        
        const result = await response.json();
        
        // Sauvegarder le résultat
        invoice.result = result;
        invoice.status = INVOICE_STATUS.COMPLETED;
        
        hideProcessingOverlay();
        updateQueueDisplay();
        
        showToast(`✅ ${invoice.name} analysée avec succès`, 'success');
        console.log(`✅ Facture ${invoiceId} traitée:`, result);
        
    } catch (error) {
        console.error(`❌ Erreur lors du traitement de ${invoiceId}:`, error);
        
        invoice.error = error.message;
        invoice.status = INVOICE_STATUS.ERROR;
        
        hideProcessingOverlay();
        updateQueueDisplay();
        
        showToast(`❌ Erreur: ${invoice.name}`, 'error');
    }
}

// Traiter toutes les factures en attente
async function processAllInvoices() {
    console.log('🚀 Traitement de toutes les factures...');
    
    const pendingInvoices = window.invoiceQueue.filter(inv => inv.status === INVOICE_STATUS.PENDING);
    
    if (pendingInvoices.length === 0) {
        showToast('ℹ️ Aucune facture en attente', 'info');
        return;
    }
    
    // Traiter les factures une par une
    for (let i = 0; i < pendingInvoices.length; i++) {
        const invoice = pendingInvoices[i];
        updateProcessingOverlay(`Traitement ${i + 1}/${pendingInvoices.length}: ${invoice.name}`);
        await processInvoiceFromQueue(invoice.id);
        
        // Petite pause entre les traitements
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    hideProcessingOverlay();
    showToast(`✅ ${pendingInvoices.length} facture(s) traitée(s)`, 'success');
}

// Voir les résultats d'une facture
function viewInvoiceResults(invoiceId) {
    console.log(`👁️ Affichage des résultats de ${invoiceId}`);
    
    const invoice = window.invoiceQueue.find(inv => inv.id === invoiceId);
    if (!invoice || !invoice.result) {
        showToast('❌ Aucun résultat disponible', 'warning');
        return;
    }
    
    // Afficher les résultats dans l'interface principale
    if (window.scanner && window.scanner.displayAnalysisResults) {
        window.scanner.analysisResult = invoice.result;
        window.scanner.displayAnalysisResults(invoice.result);
        
        // Masquer la queue et afficher les résultats
        hideQueueSection();
        document.getElementById('analysisResults').style.display = 'block';
    }
}

// Réessayer une facture en erreur
function retryInvoice(invoiceId) {
    console.log(`🔄 Nouvelle tentative pour ${invoiceId}`);
    
    const invoice = window.invoiceQueue.find(inv => inv.id === invoiceId);
    if (!invoice) return;
    
    // Remettre en attente
    invoice.status = INVOICE_STATUS.PENDING;
    invoice.error = null;
    
    updateQueueDisplay();
    
    showToast(`🔄 ${invoice.name} remise en file`, 'info');
}

// Supprimer une facture de la queue
function removeFromQueue(invoiceId) {
    console.log(`🗑️ Suppression de ${invoiceId}`);
    
    const index = window.invoiceQueue.findIndex(inv => inv.id === invoiceId);
    if (index === -1) return;
    
    const invoice = window.invoiceQueue[index];
    window.invoiceQueue.splice(index, 1);
    
    updateQueueDisplay();
    updateQueueButtons();
    
    showToast(`🗑️ ${invoice.name} supprimée`, 'info');
}

// Vider toute la queue
function clearQueue() {
    if (window.invoiceQueue.length === 0) {
        showToast('ℹ️ La file est déjà vide', 'info');
        return;
    }
    
    if (confirm(`Êtes-vous sûr de vouloir supprimer ${window.invoiceQueue.length} facture(s) ?`)) {
        window.invoiceQueue = [];
        updateQueueDisplay();
        updateQueueButtons();
        hideQueueSection();
        
        showToast('🧹 File d\'attente vidée', 'info');
    }
}

// Commencer une nouvelle facture
function newInvoice() {
    console.log('📸 Nouvelle facture');
    
    hideQueueSection();
    resetScanner();
    
    showToast('📸 Prêt pour une nouvelle facture', 'info');
}

/**
 * 🎨 FONCTIONS D'INTERFACE
 */

// Mettre à jour l'affichage de la queue
function updateQueueDisplay() {
    const queueList = document.getElementById('queueList');
    const queueCount = document.getElementById('queueCount');
    const floatingQueueCount = document.getElementById('floatingQueueCount');
    const emptyMessage = document.getElementById('emptyQueueMessage');
    
    if (!queueList) return;
    
    // Mettre à jour les compteurs
    const count = window.invoiceQueue.length;
    if (queueCount) queueCount.textContent = count;
    if (floatingQueueCount) floatingQueueCount.textContent = count;
    
    // Afficher/masquer le message vide
    if (emptyMessage) {
        emptyMessage.style.display = count === 0 ? 'block' : 'none';
    }
    
    // Afficher/masquer le bouton flottant
    const floatingBtn = document.getElementById('floatingQueueBtn');
    if (floatingBtn) {
        floatingBtn.style.display = count > 0 ? 'block' : 'none';
    }
    
    // Générer le HTML de la liste
    queueList.innerHTML = window.invoiceQueue.map(invoice => createInvoiceQueueHTML(invoice)).join('');
}

// Créer le HTML pour une facture en queue
function createInvoiceQueueHTML(invoice) {
    const statusConfig = getStatusConfig(invoice.status);
    const timeAgo = getTimeAgo(invoice.createdAt);
    
    return `
        <div class="queue-item border rounded p-3 mb-2 ${statusConfig.class}" data-invoice-id="${invoice.id}">
            <div class="d-flex align-items-center justify-content-between">
                <div class="flex-grow-1">
                    <div class="d-flex align-items-center mb-1">
                        <strong class="me-2">${invoice.name}</strong>
                        <span class="badge ${statusConfig.badgeClass}">${statusConfig.icon} ${statusConfig.text}</span>
                    </div>
                    <div class="d-flex align-items-center text-muted small">
                        <i class="bi bi-images me-1"></i>
                        ${invoice.pages.length} page(s)
                        <span class="mx-2">•</span>
                        <i class="bi bi-clock me-1"></i>
                        ${timeAgo}
                    </div>
                    ${invoice.error ? `
                        <div class="text-danger small mt-1">
                            <i class="bi bi-exclamation-triangle me-1"></i>
                            ${invoice.error}
                        </div>
                    ` : ''}
                </div>
                <div class="queue-actions">
                    ${createInvoiceActionsHTML(invoice)}
                </div>
            </div>
        </div>
    `;
}

// Créer les boutons d'action pour une facture
function createInvoiceActionsHTML(invoice) {
    switch (invoice.status) {
        case INVOICE_STATUS.PENDING:
            return `
                <button class="btn btn-sm btn-warning me-1" onclick="processInvoiceFromQueue('${invoice.id}')" title="Analyser">
                    <i class="bi bi-play-circle"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="removeFromQueue('${invoice.id}')" title="Supprimer">
                    <i class="bi bi-trash"></i>
                </button>
            `;
            
        case INVOICE_STATUS.PROCESSING:
            return `
                <div class="spinner-border spinner-border-sm text-warning" role="status">
                    <span class="visually-hidden">Traitement...</span>
                </div>
            `;
            
        case INVOICE_STATUS.COMPLETED:
            return `
                <button class="btn btn-sm btn-success me-1" onclick="viewInvoiceResults('${invoice.id}')" title="Voir résultats">
                    <i class="bi bi-eye"></i>
                </button>
                <button class="btn btn-sm btn-outline-secondary" onclick="removeFromQueue('${invoice.id}')" title="Supprimer">
                    <i class="bi bi-trash"></i>
                </button>
            `;
            
        case INVOICE_STATUS.ERROR:
            return `
                <button class="btn btn-sm btn-warning me-1" onclick="retryInvoice('${invoice.id}')" title="Réessayer">
                    <i class="bi bi-arrow-repeat"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="removeFromQueue('${invoice.id}')" title="Supprimer">
                    <i class="bi bi-trash"></i>
                </button>
            `;
            
        default:
            return '';
    }
}

// Configuration des statuts
function getStatusConfig(status) {
    switch (status) {
        case INVOICE_STATUS.PENDING:
            return {
                icon: '⏳',
                text: 'En attente',
                class: 'border-warning',
                badgeClass: 'bg-warning'
            };
        case INVOICE_STATUS.PROCESSING:
            return {
                icon: '🔄',
                text: 'Traitement',
                class: 'border-info',
                badgeClass: 'bg-info'
            };
        case INVOICE_STATUS.COMPLETED:
            return {
                icon: '✅',
                text: 'Terminé',
                class: 'border-success',
                badgeClass: 'bg-success'
            };
        case INVOICE_STATUS.ERROR:
            return {
                icon: '❌',
                text: 'Erreur',
                class: 'border-danger',
                badgeClass: 'bg-danger'
            };
        default:
            return {
                icon: '❓',
                text: 'Inconnu',
                class: 'border-secondary',
                badgeClass: 'bg-secondary'
            };
    }
}

// Mettre à jour les boutons selon l'état de la queue
function updateQueueButtons() {
    const addToQueueBtn = document.getElementById('addToQueueBtn');
    const analyzeMultiBtn = document.getElementById('analyzeMultiBtn');
    const processAllBtn = document.getElementById('processAllBtn');
    
    // Bouton "En File" activé si il y a des pages
    if (addToQueueBtn) {
        const hasPages = window.scanner && window.scanner.currentPages && window.scanner.currentPages.length > 0;
        addToQueueBtn.disabled = !hasPages;
    }
    
    // Bouton "Analyser" activé si il y a des pages
    if (analyzeMultiBtn) {
        const hasPages = window.scanner && window.scanner.currentPages && window.scanner.currentPages.length > 0;
        analyzeMultiBtn.disabled = !hasPages;
    }
    
    // Bouton "Traiter Tout" activé si il y a des factures en attente
    if (processAllBtn) {
        const hasPending = window.invoiceQueue.some(inv => inv.status === INVOICE_STATUS.PENDING);
        processAllBtn.disabled = !hasPending;
    }
}

// Afficher/masquer la section queue
function toggleQueueSection() {
    const queueSection = document.getElementById('invoiceQueueSection');
    const mainScanner = document.querySelector('.scanner-container');
    const analysisResults = document.getElementById('analysisResults');
    
    if (!queueSection) return;
    
    const isVisible = queueSection.style.display !== 'none';
    
    if (isVisible) {
        hideQueueSection();
    } else {
        showQueueSection();
    }
}

function showQueueSection() {
    const queueSection = document.getElementById('invoiceQueueSection');
    const mainScanner = document.querySelector('.scanner-container');
    const analysisResults = document.getElementById('analysisResults');
    
    if (queueSection) queueSection.style.display = 'block';
    if (mainScanner) mainScanner.style.display = 'none';
    if (analysisResults) analysisResults.style.display = 'none';
    
    updateQueueDisplay();
}

function hideQueueSection() {
    const queueSection = document.getElementById('invoiceQueueSection');
    const mainScanner = document.querySelector('.scanner-container');
    
    if (queueSection) queueSection.style.display = 'none';
    if (mainScanner) mainScanner.style.display = 'block';
}

// Afficher l'overlay de traitement
function showProcessingOverlay(message) {
    const overlay = document.getElementById('processingOverlay');
    const title = document.getElementById('processingTitle');
    const status = document.getElementById('processingStatus');
    
    if (overlay) overlay.style.display = 'flex';
    if (title) title.textContent = '🤖 Analyse en cours...';
    if (status) status.textContent = message;
    
    // Animation de la barre de progression
    animateProgressBar();
}

function updateProcessingOverlay(message) {
    const status = document.getElementById('processingStatus');
    if (status) status.textContent = message;
}

function hideProcessingOverlay() {
    const overlay = document.getElementById('processingOverlay');
    if (overlay) overlay.style.display = 'none';
}

// Animation de la barre de progression
function animateProgressBar() {
    const progressBar = document.getElementById('processingProgress');
    if (!progressBar) return;
    
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 20;
        if (progress > 90) progress = 90; // Ne jamais atteindre 100% automatiquement
        
        progressBar.style.width = `${progress}%`;
        
        if (progress >= 90) {
            clearInterval(interval);
        }
    }, 500);
}

/**
 * 🛠️ FONCTIONS UTILITAIRES
 */

// Convertir base64 en blob
function base64ToBlob(base64Data, contentType) {
    const byteCharacters = atob(base64Data.split(',')[1]);
    const byteNumbers = new Array(byteCharacters.length);
    
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: contentType });
}

// Calculer le temps écoulé
function getTimeAgo(date) {
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);
    
    if (diffInSeconds < 60) return 'À l\'instant';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}min`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h`;
    return `${Math.floor(diffInSeconds / 86400)}j`;
}

// Afficher un toast
function showToast(message, type = 'info') {
    // Utiliser la fonction toast existante si disponible
    if (window.scanner && window.scanner.showToast) {
        window.scanner.showToast(message, type);
        return;
    }
    
    // Sinon, simple console.log
    const emoji = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️'
    };
    
    console.log(`${emoji[type] || 'ℹ️'} ${message}`);
}

/**
 * 🔄 EXTENSION DU SCANNER EXISTANT
 */

// Observer les changements de pages pour mettre à jour les boutons
function observePageChanges() {
    if (!window.scanner) return;
    
    // Observer les changements dans currentPages
    const originalUpdatePagesDisplay = window.scanner.updatePagesDisplay;
    if (originalUpdatePagesDisplay) {
        window.scanner.updatePagesDisplay = function() {
            originalUpdatePagesDisplay.call(this);
            updateQueueButtons();
        };
    }
    
    // Observer l'ajout de pages
    const originalAddPage = window.scanner.addPage;
    if (originalAddPage) {
        window.scanner.addPage = function(pageData) {
            originalAddPage.call(this, pageData);
            updateQueueButtons();
        };
    }
    
    // Observer la suppression de pages
    const originalRemovePage = window.scanner.removePage;
    if (originalRemovePage) {
        window.scanner.removePage = function(index) {
            originalRemovePage.call(this, index);
            updateQueueButtons();
        };
    }
}

/**
 * 🚀 INITIALISATION
 */

// Initialiser le système multi-factures quand le DOM est prêt
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 Initialisation du système Multi-Factures...');
    
    // Attendre que le scanner soit chargé
    const checkScanner = setInterval(() => {
        if (window.scanner) {
            clearInterval(checkScanner);
            
            // Étendre le scanner existant
            observePageChanges();
            updateQueueButtons();
            
            console.log('✅ Système Multi-Factures initialisé et intégré');
        }
    }, 100);
    
    // Mettre à jour les boutons périodiquement
    setInterval(updateQueueButtons, 1000);
});

console.log('📋 Module Queue Multi-Factures chargé'); 