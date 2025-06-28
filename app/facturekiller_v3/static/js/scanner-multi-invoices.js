/**
 * Scanner Multi-Factures - Système Hybride
 * Permet de gérer plusieurs factures avec plusieurs pages chacune
 */

// Variables globales
let currentInvoice = {
    id: null,
    name: '',
    pages: [],
    status: 'editing'
};

let invoicesQueue = [];
let invoiceCounter = 1;
let pageCounter = 1;

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Scanner Multi-Factures initialisé');
    updateCurrentInvoiceTitle();
    
    // Event listeners
    document.getElementById('fileInput').addEventListener('change', handleFileSelect);
});

// === GESTION FACTURE COURANTE ===

function updateCurrentInvoiceTitle() {
    const title = currentInvoice.name || `Facture ${invoiceCounter.toString().padStart(3, '0')}`;
    document.getElementById('currentInvoiceTitle').textContent = title;
    document.getElementById('currentPageCount').textContent = `${currentInvoice.pages.length} page(s)`;
    
    // Activer/désactiver les boutons
    const hasPages = currentInvoice.pages.length > 0;
    document.getElementById('analyzeCurrentBtn').disabled = !hasPages;
    document.getElementById('addToQueueBtn').disabled = !hasPages;
    
    // Afficher/masquer la section pages
    const pagesSection = document.getElementById('currentPages');
    if (hasPages) {
        pagesSection.style.display = 'block';
        displayCurrentPages();
    } else {
        pagesSection.style.display = 'none';
    }
}

function handleFileSelect(event) {
    const files = Array.from(event.target.files);
    
    files.forEach(file => {
        if (file.type.startsWith('image/') || file.type === 'application/pdf') {
            addPageToCurrentInvoice(file);
        }
    });
    
    // Reset input
    event.target.value = '';
}

function addPageToCurrentInvoice(file) {
    const pageId = `page_${Date.now()}_${pageCounter++}`;
    const pageData = {
        id: pageId,
        file: file,
        name: file.name,
        size: file.size,
        type: file.type,
        preview: null
    };
    
    // Générer preview
    if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = function(e) {
            pageData.preview = e.target.result;
            updateCurrentInvoiceDisplay();
        };
        reader.readAsDataURL(file);
    }
    
    currentInvoice.pages.push(pageData);
    updateCurrentInvoiceTitle();
    
    console.log(`📄 Page ajoutée: ${file.name} (${(file.size/1024/1024).toFixed(2)}MB)`);
}

function displayCurrentPages() {
    const container = document.getElementById('currentPagesList');
    
    if (currentInvoice.pages.length === 0) {
        container.innerHTML = '<p class="text-muted text-center">Aucune page ajoutée</p>';
        return;
    }
    
    container.innerHTML = currentInvoice.pages.map((page, index) => `
        <div class="page-item d-flex align-items-center" data-page-id="${page.id}">
            <div class="page-preview me-3">
                ${page.preview ? 
                    `<img src="${page.preview}" class="page-thumbnail" alt="Page ${index + 1}">` :
                    `<div class="page-thumbnail d-flex align-items-center justify-content-center bg-light">
                        <i class="fas fa-file-pdf text-secondary"></i>
                    </div>`
                }
            </div>
            <div class="page-info flex-grow-1">
                <h6 class="mb-1">Page ${index + 1}</h6>
                <p class="mb-0 text-muted small">
                    ${page.name} • ${(page.size/1024/1024).toFixed(2)}MB
                </p>
            </div>
            <div class="page-actions">
                <button class="btn btn-outline-danger btn-sm" onclick="removePageFromCurrent('${page.id}')">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

function removePageFromCurrent(pageId) {
    currentInvoice.pages = currentInvoice.pages.filter(page => page.id !== pageId);
    updateCurrentInvoiceTitle();
    console.log(`🗑️ Page supprimée: ${pageId}`);
}

function addMorePages() {
    document.getElementById('fileInput').click();
}

function clearCurrentInvoice() {
    if (currentInvoice.pages.length > 0) {
        if (!confirm('Supprimer toutes les pages de cette facture ?')) {
            return;
        }
    }
    
    currentInvoice = {
        id: null,
        name: '',
        pages: [],
        status: 'editing'
    };
    
    updateCurrentInvoiceTitle();
    console.log('🗑️ Facture courante vidée');
}

// === GESTION FILE D'ATTENTE ===

function addToQueue() {
    if (currentInvoice.pages.length === 0) {
        alert('Ajoutez au moins une page à cette facture');
        return;
    }
    
    // Créer l'ID de la facture
    const invoiceId = `FACT_${Date.now()}_${invoiceCounter.toString().padStart(3, '0')}`;
    
    // Ajouter à la queue
    const queueInvoice = {
        id: invoiceId,
        name: currentInvoice.name || `Facture ${invoiceCounter.toString().padStart(3, '0')}`,
        pages: [...currentInvoice.pages],
        status: 'waiting',
        dateAdded: new Date(),
        progress: 0,
        result: null
    };
    
    invoicesQueue.push(queueInvoice);
    invoiceCounter++;
    
    // Réinitialiser la facture courante
    clearCurrentInvoice();
    
    // Mettre à jour l'affichage
    updateQueueDisplay();
    
    console.log(`📋 Facture ajoutée à la file: ${queueInvoice.name}`);
    showSuccess(`Facture "${queueInvoice.name}" ajoutée à la file d'attente`);
}

function updateQueueDisplay() {
    const queueContainer = document.getElementById('invoicesQueue');
    const queueList = document.getElementById('invoiceList');
    const queueCount = document.getElementById('queueCount');
    
    queueCount.textContent = invoicesQueue.length;
    
    if (invoicesQueue.length === 0) {
        queueContainer.style.display = 'none';
        return;
    }
    
    queueContainer.style.display = 'block';
    
    queueList.innerHTML = invoicesQueue.map(invoice => `
        <div class="invoice-item ${invoice.status}" data-invoice-id="${invoice.id}">
            <div class="row align-items-center">
                <div class="col-md-2">
                    <div class="d-flex">
                        ${invoice.pages.slice(0, 3).map(page => 
                            page.preview ? 
                            `<img src="${page.preview}" class="page-thumbnail" alt="Page">` :
                            `<div class="page-thumbnail d-flex align-items-center justify-content-center bg-light">
                                <i class="fas fa-file-pdf text-secondary"></i>
                            </div>`
                        ).join('')}
                        ${invoice.pages.length > 3 ? 
                            `<div class="page-thumbnail d-flex align-items-center justify-content-center bg-light">
                                <small>+${invoice.pages.length - 3}</small>
                            </div>` : ''
                        }
                    </div>
                </div>
                <div class="col-md-4">
                    <h6 class="mb-1">${invoice.name}</h6>
                    <p class="mb-0 text-muted small">
                        ${invoice.pages.length} page(s) • ${formatDate(invoice.dateAdded)}
                    </p>
                </div>
                <div class="col-md-3">
                    <span class="invoice-status status-${invoice.status}">
                        ${getStatusLabel(invoice.status)}
                    </span>
                    ${invoice.status === 'processing' ? 
                        `<div class="progress mt-2" style="height: 4px;">
                            <div class="progress-bar bg-warning progress-bar-animated" 
                                 style="width: ${invoice.progress}%"></div>
                        </div>` : ''
                    }
                </div>
                <div class="col-md-3 text-end">
                    ${generateInvoiceActions(invoice)}
                </div>
            </div>
        </div>
    `).join('');
}

function generateInvoiceActions(invoice) {
    switch (invoice.status) {
        case 'waiting':
            return `
                <button class="btn btn-warning btn-sm me-1" onclick="processInvoice('${invoice.id}')">
                    <i class="fas fa-play me-1"></i>Traiter
                </button>
                <button class="btn btn-outline-secondary btn-sm" onclick="removeFromQueue('${invoice.id}')">
                    <i class="fas fa-trash"></i>
                </button>
            `;
        case 'processing':
            return `
                <button class="btn btn-secondary btn-sm" disabled>
                    <i class="fas fa-spinner fa-spin me-1"></i>Traitement...
                </button>
            `;
        case 'completed':
            return `
                <button class="btn btn-success btn-sm me-1" onclick="viewInvoiceResults('${invoice.id}')">
                    <i class="fas fa-eye me-1"></i>Voir
                </button>
                <button class="btn btn-primary btn-sm" onclick="saveInvoice('${invoice.id}')">
                    <i class="fas fa-save me-1"></i>Enregistrer
                </button>
            `;
        case 'error':
            return `
                <button class="btn btn-outline-warning btn-sm me-1" onclick="retryInvoice('${invoice.id}')">
                    <i class="fas fa-redo me-1"></i>Réessayer
                </button>
                <button class="btn btn-outline-secondary btn-sm" onclick="removeFromQueue('${invoice.id}')">
                    <i class="fas fa-trash"></i>
                </button>
            `;
        default:
            return '';
    }
}

function getStatusLabel(status) {
    const labels = {
        'waiting': '⏳ En attente',
        'processing': '🔄 Traitement...',
        'completed': '✅ Terminé',
        'error': '❌ Erreur'
    };
    return labels[status] || status;
}

// === TRAITEMENT DES FACTURES ===

async function startCurrentInvoiceAnalysis() {
    if (currentInvoice.pages.length === 0) {
        alert('Aucune page à analyser');
        return;
    }
    
    // Créer un ID temporaire pour la facture courante
    const invoiceId = `TEMP_${Date.now()}`;
    currentInvoice.id = invoiceId;
    currentInvoice.status = 'processing';
    
    try {
        showLoading('Analyse en cours...');
        
        const result = await processInvoicePages(currentInvoice.pages);
        
        if (result.success) {
            currentInvoice.result = result;
            currentInvoice.status = 'completed';
            
            hideLoading();
            showInvoiceResults(result);
        } else {
            throw new Error(result.error || 'Erreur lors de l\'analyse');
        }
        
    } catch (error) {
        console.error('Erreur analyse facture courante:', error);
        currentInvoice.status = 'error';
        hideLoading();
        showError('Erreur lors de l\'analyse: ' + error.message);
    }
}

async function processInvoice(invoiceId) {
    const invoice = invoicesQueue.find(inv => inv.id === invoiceId);
    if (!invoice) return;
    
    invoice.status = 'processing';
    invoice.progress = 0;
    updateQueueDisplay();
    
    try {
        // Simulation du progrès
        const progressInterval = setInterval(() => {
            if (invoice.progress < 90) {
                invoice.progress += Math.random() * 20;
                updateQueueDisplay();
            }
        }, 500);
        
        const result = await processInvoicePages(invoice.pages);
        clearInterval(progressInterval);
        
        if (result.success) {
            invoice.status = 'completed';
            invoice.progress = 100;
            invoice.result = result;
            showSuccess(`Facture "${invoice.name}" analysée avec succès !`);
        } else {
            throw new Error(result.error || 'Erreur lors de l\'analyse');
        }
        
    } catch (error) {
        console.error('Erreur traitement facture:', error);
        invoice.status = 'error';
        invoice.progress = 0;
        showError(`Erreur lors du traitement de "${invoice.name}": ${error.message}`);
    }
    
    updateQueueDisplay();
}

async function processAllInQueue() {
    const waitingInvoices = invoicesQueue.filter(inv => inv.status === 'waiting');
    
    if (waitingInvoices.length === 0) {
        alert('Aucune facture en attente');
        return;
    }
    
    if (!confirm(`Traiter ${waitingInvoices.length} facture(s) en attente ?`)) {
        return;
    }
    
    // Traiter toutes les factures en parallèle (ou séquentiellement selon votre préférence)
    for (const invoice of waitingInvoices) {
        processInvoice(invoice.id);
        // Petit délai pour éviter de surcharger l'API
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
}

async function processInvoicePages(pages) {
    // Préparer les fichiers pour l'API
    const formData = new FormData();
    
    pages.forEach((page, index) => {
        formData.append('pages', page.file);
    });
    
    // Envoyer à l'API
    const response = await fetch('/api/process-multi-page-invoice', {
        method: 'POST',
        body: formData
    });
    
    return await response.json();
}

// === AFFICHAGE DES RÉSULTATS ===

function showInvoiceResults(result) {
    const container = document.getElementById('resultsContainer');
    const content = document.getElementById('resultsContent');
    
    content.innerHTML = generateResultsHTML(result);
    container.style.display = 'block';
    
    // Scroll vers les résultats
    container.scrollIntoView({ behavior: 'smooth' });
}

function viewInvoiceResults(invoiceId) {
    const invoice = invoicesQueue.find(inv => inv.id === invoiceId);
    if (!invoice || !invoice.result) return;
    
    // Afficher dans une modal
    const modalContent = document.getElementById('invoiceDetailsContent');
    modalContent.innerHTML = generateResultsHTML(invoice.result);
    
    new bootstrap.Modal(document.getElementById('invoiceDetailsModal')).show();
}

function generateResultsHTML(result) {
    return `
        <div class="row">
            <div class="col-md-6">
                <h6><i class="fas fa-info-circle me-2"></i>Informations Facture</h6>
                <ul class="list-unstyled">
                    <li><strong>Fournisseur:</strong> ${result.supplier || 'Non détecté'}</li>
                    <li><strong>Date:</strong> ${result.date || 'Non détectée'}</li>
                    <li><strong>Numéro:</strong> ${result.invoice_number || 'Non détecté'}</li>
                    <li><strong>Total:</strong> ${result.total || 'Non détecté'}</li>
                </ul>
            </div>
            <div class="col-md-6">
                <h6><i class="fas fa-chart-bar me-2"></i>Statistiques</h6>
                <ul class="list-unstyled">
                    <li><strong>Produits détectés:</strong> ${result.products?.length || 0}</li>
                    <li><strong>Pages analysées:</strong> ${result.pages_count || 1}</li>
                    <li><strong>Confiance IA:</strong> ${result.confidence || 'N/A'}%</li>
                </ul>
            </div>
        </div>
        
        ${result.products && result.products.length > 0 ? `
            <h6 class="mt-4"><i class="fas fa-box me-2"></i>Produits Détectés</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Produit</th>
                            <th>Quantité</th>
                            <th>Prix Unitaire</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${result.products.map(product => `
                            <tr>
                                <td>${product.name}</td>
                                <td>${product.quantity}</td>
                                <td>${product.unit_price}€</td>
                                <td>${product.total_price}€</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        ` : ''}
    `;
}

// === ACTIONS UTILITAIRES ===

function removeFromQueue(invoiceId) {
    if (!confirm('Supprimer cette facture de la file ?')) return;
    
    invoicesQueue = invoicesQueue.filter(inv => inv.id !== invoiceId);
    updateQueueDisplay();
    console.log(`🗑️ Facture supprimée de la file: ${invoiceId}`);
}

function retryInvoice(invoiceId) {
    const invoice = invoicesQueue.find(inv => inv.id === invoiceId);
    if (!invoice) return;
    
    invoice.status = 'waiting';
    invoice.progress = 0;
    invoice.result = null;
    updateQueueDisplay();
    
    console.log(`🔄 Facture remise en attente: ${invoice.name}`);
}

function clearQueue() {
    if (invoicesQueue.length === 0) return;
    
    if (!confirm('Vider toute la file d\'attente ?')) return;
    
    invoicesQueue = [];
    updateQueueDisplay();
    console.log('🗑️ File d\'attente vidée');
}

function clearAllInvoices() {
    if (!confirm('Supprimer la facture courante ET vider la file d\'attente ?')) return;
    
    clearCurrentInvoice();
    clearQueue();
    
    // Masquer les résultats
    document.getElementById('resultsContainer').style.display = 'none';
}

async function saveInvoice(invoiceId) {
    const invoice = invoicesQueue.find(inv => inv.id === invoiceId);
    if (!invoice || !invoice.result) return;
    
    try {
        showLoading('Enregistrement...');
        
        const response = await fetch('/api/save-invoice', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                invoice_id: invoiceId,
                result: invoice.result
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess('Facture enregistrée avec succès !');
            removeFromQueue(invoiceId);
        } else {
            throw new Error(data.error || 'Erreur lors de l\'enregistrement');
        }
        
    } catch (error) {
        console.error('Erreur sauvegarde:', error);
        showError('Erreur lors de l\'enregistrement: ' + error.message);
    } finally {
        hideLoading();
    }
}

function saveInvoiceFromModal() {
    // Récupérer l'ID de la facture depuis la modal (à implémenter selon vos besoins)
    console.log('Sauvegarde depuis modal');
}

// === CAMERA ===

function openCamera() {
    new bootstrap.Modal(document.getElementById('cameraModal')).show();
    startCameraStream();
}

async function startCameraStream() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                facingMode: 'environment',
                width: { ideal: 1920 },
                height: { ideal: 1080 }
            } 
        });
        
        document.getElementById('cameraVideo').srcObject = stream;
    } catch (error) {
        console.error('Erreur caméra:', error);
        alert('Impossible d\'accéder à la caméra');
    }
}

function capturePhoto() {
    const video = document.getElementById('cameraVideo');
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0);
    
    canvas.toBlob(blob => {
        const file = new File([blob], `photo_${Date.now()}.jpg`, { type: 'image/jpeg' });
        addPageToCurrentInvoice(file);
        
        // Fermer la modal
        bootstrap.Modal.getInstance(document.getElementById('cameraModal')).hide();
        
        // Arrêter le stream
        const stream = video.srcObject;
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
    }, 'image/jpeg', 0.8);
}

// === UTILITAIRES ===

function formatDate(date) {
    return new Intl.DateTimeFormat('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

function showLoading(message = 'Chargement...') {
    // Implémenter selon votre système de loading
    console.log('Loading:', message);
}

function hideLoading() {
    // Implémenter selon votre système de loading
    console.log('Loading hidden');
}

function showSuccess(message) {
    // Implémenter selon votre système de notifications
    console.log('Success:', message);
    alert('✅ ' + message);
}

function showError(message) {
    // Implémenter selon votre système de notifications
    console.error('Error:', message);
    alert('❌ ' + message);
} 