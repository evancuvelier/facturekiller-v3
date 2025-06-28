// 🚀 FactureKiller V3 - Scanner Batch Avancé
// Scanner multi-factures avec traitement parallèle

class BatchScanner {
    constructor() {
        this.scanQueue = [];
        this.activeScans = new Map();
        this.results = new Map();
        this.maxConcurrent = 3; // 3 scans en parallèle max
        this.factureGroups = new Map(); // Regrouper multi-pages
        this.abortControllers = new Map(); // Pour annuler les requêtes en cours
        this.isProcessing = false;
        this.editingProducts = new Set(); // Pour tracker les produits en cours d'édition
        
        this.initializeElements();
        this.setupEventListeners();
        this.setupNavigationProtection();
    }
    
    initializeElements() {
        this.dropZone = document.getElementById('batchDropZone');
        this.queueContainer = document.getElementById('scanQueue');
        this.resultsContainer = document.getElementById('scanResults');
        this.progressBar = document.getElementById('batchProgress');
        this.statsContainer = document.getElementById('batchStats');
    }
    
    setupEventListeners() {
        // Zone de drop multi-fichiers
        this.dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.dropZone.classList.add('dragover');
        });
        
        this.dropZone.addEventListener('dragleave', () => {
            this.dropZone.classList.remove('dragover');
        });
        
        this.dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.dropZone.classList.remove('dragover');
            this.handleFiles(e.dataTransfer.files);
        });
        
        // Input file multiple
        const fileInput = document.getElementById('batchFileInput');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                this.handleFiles(e.target.files);
            });
        }
    }
    
    setupNavigationProtection() {
        // Prévenir la navigation si des scans sont en cours
        window.addEventListener('beforeunload', (e) => {
            if (this.activeScans.size > 0 || this.scanQueue.length > 0) {
                const message = 'Des scans sont en cours. Si vous quittez maintenant, ils seront annulés.';
                e.preventDefault();
                e.returnValue = message;
                return message;
            }
        });
        
        // Intercepter les changements de page dans l'app
        const originalPushState = history.pushState;
        const originalReplaceState = history.replaceState;
        
        const checkActiveScans = () => {
            if (this.activeScans.size > 0) {
                if (!confirm('Des scans sont en cours. Voulez-vous vraiment changer de page ?')) {
                    return false;
                }
                // Annuler tous les scans en cours
                this.cancelAllScans();
            }
            return true;
        };
        
        history.pushState = function(...args) {
            if (checkActiveScans()) {
                originalPushState.apply(history, args);
            }
        };
        
        history.replaceState = function(...args) {
            if (checkActiveScans()) {
                originalReplaceState.apply(history, args);
            }
        };
    }
    
    cancelAllScans() {
        console.log('❌ Annulation de tous les scans en cours...');
        
        // Annuler toutes les requêtes
        this.abortControllers.forEach((controller, scanId) => {
            controller.abort();
        });
        
        // Nettoyer
        this.abortControllers.clear();
        this.activeScans.clear();
        this.scanQueue = [];
        
        // Mettre à jour l'UI
        this.updateStats();
    }
    
    handleFiles(files) {
        console.log(`📁 ${files.length} fichiers ajoutés à la queue`);
        
        for (let file of files) {
            if (this.isValidImageFile(file)) {
                const scanItem = {
                    id: this.generateId(),
                    file: file,
                    name: file.name,
                    size: file.size,
                    status: 'pending',
                    progress: 0,
                    result: null,
                    error: null,
                    group: this.detectFactureGroup(file.name)
                };
                
                this.scanQueue.push(scanItem);
                this.addToQueueUI(scanItem);
            }
        }
        
        this.updateStats();
        this.processQueue();
    }
    
    detectFactureGroup(filename) {
        // Détecter si plusieurs pages de la même facture
        // Ex: "facture_mva_001_page1.jpg", "facture_mva_001_page2.jpg"
        const match = filename.match(/(.+?)(?:_page\d+|_p\d+|\(\d+\))/i);
        return match ? match[1] : filename.replace(/\.[^/.]+$/, "");
    }
    
    isValidImageFile(file) {
        const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/heic', 'image/heif'];
        return validTypes.includes(file.type) || file.name.toLowerCase().match(/\.(jpg|jpeg|png|heic|heif)$/);
    }
    
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
    
    addToQueueUI(scanItem) {
        const queueItem = document.createElement('div');
        queueItem.className = 'scan-queue-item';
        queueItem.id = `queue-${scanItem.id}`;
        
        queueItem.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="scan-status me-3">
                    <div class="spinner-border spinner-border-sm text-primary" role="status">
                        <span class="visually-hidden">En attente...</span>
                    </div>
                </div>
                <div class="flex-grow-1">
                    <div class="fw-bold">${scanItem.name}</div>
                    <div class="text-muted small">
                        ${this.formatFileSize(scanItem.size)} • Groupe: ${scanItem.group}
                    </div>
                    <div class="progress mt-1" style="height: 4px;">
                        <div class="progress-bar" role="progressbar" style="width: 0%"></div>
                    </div>
                </div>
                <div class="scan-actions ms-3">
                    <button class="btn btn-sm btn-outline-danger" onclick="batchScanner.removeFromQueue('${scanItem.id}')">
                        <i class="bi bi-x"></i>
                    </button>
                </div>
            </div>
        `;
        
        this.queueContainer.appendChild(queueItem);
    }
    
    async processQueue() {
        while (this.scanQueue.length > 0 && this.activeScans.size < this.maxConcurrent) {
            const scanItem = this.scanQueue.shift();
            this.activeScans.set(scanItem.id, scanItem);
            
            this.updateQueueItemStatus(scanItem.id, 'processing', 0);
            this.processScanItem(scanItem);
        }
    }
    
    async processScanItem(scanItem) {
        try {
            console.log(`🤖 Début scan: ${scanItem.name}`);
            
            // Créer un AbortController pour cette requête
            const abortController = new AbortController();
            this.abortControllers.set(scanItem.id, abortController);
            
            // Préparer le FormData
            const formData = new FormData();
            formData.append('file', scanItem.file);
            formData.append('mode', 'batch');
            formData.append('group', scanItem.group);
            
            // Progress simulation
            this.updateProgress(scanItem.id, 20);
            
            // Appel API scan avec signal pour annulation
            const response = await fetch('/api/invoices/analyze', {
                method: 'POST',
                body: formData,
                signal: abortController.signal
            });
            
            this.updateProgress(scanItem.id, 70);
            
            const result = await response.json();
            
            if (result.success) {
                scanItem.result = result.data;
                scanItem.status = 'completed';
                this.updateProgress(scanItem.id, 100);
                
                console.log(`✅ Scan réussi: ${scanItem.name}`);
                
                // Sauvegarder automatiquement la facture
                await this.saveInvoiceToDatabase(scanItem);
                
                // Ajouter aux résultats
                this.addToResults(scanItem);
                
                // Traiter les nouveaux produits pour prix.js
                this.processNewProducts(scanItem.result);
                
                // Mettre à jour la liste des fournisseurs si prix.js est disponible
                if (typeof window.loadSuppliers === 'function') {
                    window.loadSuppliers();
                }
                
            } else {
                throw new Error(result.error || 'Erreur scan');
            }
            
        } catch (error) {
            // Ignorer les erreurs d'annulation
            if (error.name === 'AbortError') {
                console.log(`⏹️ Scan annulé: ${scanItem.name}`);
                scanItem.status = 'cancelled';
                this.updateQueueItemStatus(scanItem.id, 'cancelled', 0);
            } else {
                console.error(`❌ Erreur scan ${scanItem.name}:`, error);
                scanItem.status = 'error';
                scanItem.error = error.message;
                this.updateQueueItemStatus(scanItem.id, 'error', 0);
            }
        } finally {
            // Nettoyer
            this.abortControllers.delete(scanItem.id);
            this.activeScans.delete(scanItem.id);
            this.updateStats();
            this.processQueue(); // Continuer la queue
        }
    }
    
    updateProgress(scanId, progress) {
        const queueItem = document.getElementById(`queue-${scanId}`);
        if (queueItem) {
            const progressBar = queueItem.querySelector('.progress-bar');
            if (progressBar) {
                progressBar.style.width = `${progress}%`;
            }
        }
    }
    
    updateQueueItemStatus(scanId, status, progress) {
        const queueItem = document.getElementById(`queue-${scanId}`);
        if (!queueItem) return;
        
        const statusEl = queueItem.querySelector('.scan-status');
        const progressBar = queueItem.querySelector('.progress-bar');
        
        // Mettre à jour le statut visuel
        switch (status) {
            case 'processing':
                statusEl.innerHTML = '<div class="spinner-border spinner-border-sm text-primary"></div>';
                queueItem.classList.add('processing');
                break;
            case 'completed':
                statusEl.innerHTML = '<i class="bi bi-check-circle-fill text-success"></i>';
                queueItem.classList.add('completed');
                progressBar.style.width = '100%';
                progressBar.classList.add('bg-success');
                break;
            case 'error':
                statusEl.innerHTML = '<i class="bi bi-exclamation-circle-fill text-danger"></i>';
                queueItem.classList.add('error');
                progressBar.classList.add('bg-danger');
                break;
            case 'cancelled':
                statusEl.innerHTML = '<i class="bi bi-stop-circle-fill text-warning"></i>';
                queueItem.classList.add('cancelled');
                progressBar.classList.add('bg-warning');
                break;
        }
    }
    
    addToResults(scanItem) {
        const result = scanItem.result;
        
        // Créer la carte de résultat avec édition rapide
        const resultCard = document.createElement('div');
        resultCard.className = 'scan-result-card card mb-3';
        resultCard.innerHTML = `
            <div class="card-header d-flex justify-content-between align-items-center">
                <div>
                    <strong>${result.supplier || result.fournisseur || 'Fournisseur inconnu'}</strong>
                    <small class="text-muted ms-2">${scanItem.name}</small>
                    ${scanItem.invoiceId ? `<span class="badge bg-success ms-2">Sauvegardée</span>` : ''}
                </div>
                <div class="text-end">
                    <span class="badge bg-success">${this.formatPrice(result.total_amount || result.montant_total || 0)}</span>
                    <small class="text-muted d-block">${result.products?.length || 0} produits</small>
                </div>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <small class="text-muted">N° Facture:</small>
                        <div>${result.invoice_number || result.numero_facture || 'N/A'}</div>
                    </div>
                    <div class="col-md-6">
                        <small class="text-muted">Date:</small>
                        <div>${result.date || 'N/A'}</div>
                    </div>
                </div>
                
                ${this.renderEditableProductsList(result.products, scanItem.id)}
                ${this.renderPriceComparison(result.price_comparison)}
                
                <div class="mt-3">
                    <button class="btn btn-primary btn-sm" onclick="batchScanner.saveToCommande('${scanItem.id}')">
                        <i class="bi bi-cart-plus"></i> Associer à commande
                    </button>
                    <button class="btn btn-success btn-sm" onclick="batchScanner.validateAllProducts('${scanItem.id}')">
                        <i class="bi bi-check-all"></i> Valider nouveaux produits
                    </button>
                    ${scanItem.invoiceId ? `
                        <button class="btn btn-info btn-sm" onclick="batchScanner.viewInvoice('${scanItem.invoiceId}')">
                            <i class="bi bi-eye"></i> Voir facture
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
        
        this.resultsContainer.appendChild(resultCard);
        
        // Grouper si multi-pages
        this.groupMultiPageResults(scanItem);
    }
    
    renderProductsList(products) {
        if (!products || products.length === 0) {
            return '<div class="text-muted">Aucun produit détecté</div>';
        }
        
        return `
            <div class="mt-3">
                <small class="text-muted">Produits détectés (prix unitaires):</small>
                <div class="products-list">
                    ${products.slice(0, 5).map(product => `
                        <div class="d-flex justify-content-between align-items-center py-1 border-bottom">
                            <div>
                                <span class="fw-bold">${product.name}</span>
                                <br><small class="text-muted">
                                    ${product.quantity ? `Qté: ${product.quantity}` : ''}
                                    ${product.unit ? ` | ${product.unit}` : ''}
                                </small>
                            </div>
                            <div class="text-end">
                                <span class="fw-bold text-primary">${this.formatPrice(product.unit_price || 0)}</span>
                                <br><small class="text-muted">prix unitaire</small>
                            </div>
                        </div>
                    `).join('')}
                    ${products.length > 5 ? `<div class="text-muted small">... et ${products.length - 5} autres</div>` : ''}
                </div>
            </div>
        `;
    }
    
    renderPriceComparison(comparison) {
        if (!comparison) return '';
        
        const summary = comparison.summary || {};
        const newProducts = comparison.new_products || 0;
        const alerts = comparison.price_alerts || [];
        
        let html = '<div class="price-comparison mt-3 p-2 bg-light rounded">';
        html += '<h6 class="mb-2">💰 Analyse des prix unitaires</h6>';
        
        // Alertes importantes
        if (alerts.length > 0) {
            html += '<div class="mb-2">';
            alerts.forEach(alert => {
                const alertClass = alert.severity === 'high' ? 'danger' : 
                                 alert.severity === 'success' ? 'success' : 'warning';
                html += `<div class="alert alert-${alertClass} py-1 px-2 mb-1 small">${alert.message}</div>`;
            });
            html += '</div>';
        }
        
        // Résumé des comparaisons
        html += '<div class="row text-center">';
        html += `<div class="col-3">
                    <div class="text-success fw-bold">${summary.products_with_better_prices || 0}</div>
                    <small class="text-muted">Prix plus bas</small>
                 </div>`;
        html += `<div class="col-3">
                    <div class="text-danger fw-bold">${summary.products_with_higher_prices || 0}</div>
                    <small class="text-muted">Prix plus élevés</small>
                 </div>`;
        html += `<div class="col-3">
                    <div class="text-secondary fw-bold">${summary.products_with_same_prices || 0}</div>
                    <small class="text-muted">Prix identiques</small>
                 </div>`;
        html += `<div class="col-3">
                    <div class="text-info fw-bold">${newProducts}</div>
                    <small class="text-muted">Nouveaux produits</small>
                 </div>`;
        html += '</div></div>';
        
        return html;
    }
    
    processNewProducts(result) {
        if (!result.products) return;
        
        const newProducts = result.products.filter(product => 
            product.is_new || !product.reference_price
        );
        
        if (newProducts.length > 0) {
            console.log(`💾 ${newProducts.length} nouveaux produits à sauvegarder`);
            
            // Intégration avec prix.js - Ajouter aux produits en attente
            if (window.addNewProductsToPending) {
                window.addNewProductsToPending(newProducts, result.supplier);
            }
        }
    }
    
    groupMultiPageResults(scanItem) {
        const group = scanItem.group;
        
        if (!this.factureGroups.has(group)) {
            this.factureGroups.set(group, []);
        }
        
        this.factureGroups.get(group).push(scanItem);
        
        // Si plusieurs pages détectées, créer un regroupement
        const groupItems = this.factureGroups.get(group);
        if (groupItems.length > 1) {
            this.createGroupSummary(group, groupItems);
        }
    }
    
    createGroupSummary(group, items) {
        const totalAmount = items.reduce((sum, item) => 
            sum + (item.result?.total_amount || 0), 0
        );
        
        const allProducts = items.flatMap(item => item.result?.products || []);
        
        console.log(`📋 Groupe ${group}: ${items.length} pages, Total: ${totalAmount}€`);
        
        // Créer une carte de résumé de groupe
        const groupCard = document.createElement('div');
        groupCard.className = 'group-summary-card card mb-3 border-primary';
        groupCard.innerHTML = `
            <div class="card-header bg-primary text-white">
                <strong>📋 ${group}</strong> (${items.length} pages)
                <span class="float-end">${totalAmount.toFixed(2)}€</span>
            </div>
            <div class="card-body">
                <div class="text-muted">Total consolidé: ${allProducts.length} produits</div>
                <button class="btn btn-primary btn-sm mt-2" onclick="batchScanner.exportGroup('${group}')">
                    <i class="bi bi-download"></i> Exporter groupe
                </button>
            </div>
        `;
        
        this.resultsContainer.insertBefore(groupCard, this.resultsContainer.firstChild);
    }
    
    updateStats() {
        const total = this.scanQueue.length + this.activeScans.size + this.results.size;
        const completed = this.results.size;
        const active = this.activeScans.size;
        const pending = this.scanQueue.length;
        
        if (this.statsContainer) {
            this.statsContainer.innerHTML = `
                <div class="row text-center">
                    <div class="col-3">
                        <div class="fw-bold text-primary">${total}</div>
                        <small>Total</small>
                    </div>
                    <div class="col-3">
                        <div class="fw-bold text-success">${completed}</div>
                        <small>Terminés</small>
                    </div>
                    <div class="col-3">
                        <div class="fw-bold text-warning">${active}</div>
                        <small>En cours</small>
                    </div>
                    <div class="col-3">
                        <div class="fw-bold text-secondary">${pending}</div>
                        <small>En attente</small>
                    </div>
                </div>
            `;
        }
        
        // Mettre à jour la progress bar globale
        if (this.progressBar && total > 0) {
            const progress = (completed / total) * 100;
            this.progressBar.style.width = `${progress}%`;
        }
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
    
    removeFromQueue(scanId) {
        this.scanQueue = this.scanQueue.filter(item => item.id !== scanId);
        const queueItem = document.getElementById(`queue-${scanId}`);
        if (queueItem) {
            queueItem.remove();
        }
        this.updateStats();
    }
    
    clearQueue() {
        this.scanQueue = [];
        this.queueContainer.innerHTML = '';
        this.updateStats();
    }
    
    clearResults() {
        this.results.clear();
        this.resultsContainer.innerHTML = '';
        this.factureGroups.clear();
        this.updateStats();
    }

    // Nouvelle fonction pour sauvegarder la facture en base
    async saveInvoiceToDatabase(scanItem) {
        try {
            const invoiceData = {
                filename: scanItem.name,
                supplier: scanItem.result.supplier || scanItem.result.fournisseur,
                invoice_number: scanItem.result.invoice_number || scanItem.result.numero_facture,
                date: scanItem.result.date,
                total_amount: scanItem.result.total_amount || scanItem.result.montant_total,
                products: scanItem.result.products || [],
                analysis: scanItem.result,
                file_size: scanItem.size,
                scan_date: new Date().toISOString()
            };

            const response = await fetch('/api/invoices/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(invoiceData)
            });

            const result = await response.json();
            if (result.success) {
                scanItem.invoiceId = result.invoice_id;
                console.log(`💾 Facture sauvegardée: ${result.invoice_id}`);
            }
        } catch (error) {
            console.error('❌ Erreur sauvegarde facture:', error);
        }
    }

    // Nouvelle fonction pour afficher les produits éditables
    renderEditableProductsList(products, scanId) {
        if (!products || products.length === 0) {
            return '<div class="text-muted">Aucun produit détecté</div>';
        }
        
        return `
            <div class="mt-3">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <small class="text-muted">Produits détectés:</small>
                    <button class="btn btn-sm btn-outline-primary" onclick="batchScanner.toggleEditMode('${scanId}')">
                        <i class="bi bi-pencil"></i> Éditer les prix
                    </button>
                </div>
                <div class="products-list" id="products-${scanId}">
                    ${products.map((product, index) => `
                        <div class="product-item d-flex justify-content-between align-items-center py-2 border-bottom" 
                             data-product-index="${index}">
                            <div class="product-info flex-grow-1">
                                <div class="product-name">${product.name || product.produit}</div>
                                <small class="text-muted">
                                    ${product.quantity ? `Qté: ${product.quantity} | ` : ''}
                                    Prix unitaire: <strong>${this.formatPrice(product.unit_price || 0)}</strong>
                                    ${product.unit ? ` / ${product.unit}` : ''}
                                </small>
                            </div>
                            <div class="product-price">
                                <span class="price-display fw-bold">${this.formatPrice(product.total_price || product.prix_total || 0)}</span>
                                <div class="price-edit" style="display: none;">
                                    <input type="number" class="form-control form-control-sm" 
                                           value="${product.total_price || product.prix_total || 0}" 
                                           step="0.01" style="width: 80px;">
                                </div>
                            </div>
                            <div class="product-actions ms-2" style="display: none;">
                                <button class="btn btn-sm btn-success" onclick="batchScanner.saveProductEdit('${scanId}', ${index})">
                                    <i class="bi bi-check"></i>
                                </button>
                                <button class="btn btn-sm btn-secondary" onclick="batchScanner.cancelProductEdit('${scanId}', ${index})">
                                    <i class="bi bi-x"></i>
                                </button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    // Nouvelle fonction pour basculer le mode édition
    toggleEditMode(scanId) {
        const productsList = document.getElementById(`products-${scanId}`);
        const isEditing = productsList.classList.contains('editing');
        
        if (isEditing) {
            // Sortir du mode édition
            productsList.classList.remove('editing');
            productsList.querySelectorAll('.price-edit').forEach(el => el.style.display = 'none');
            productsList.querySelectorAll('.price-display').forEach(el => el.style.display = 'inline');
            productsList.querySelectorAll('.product-actions').forEach(el => el.style.display = 'none');
            
            // Changer le bouton
            const toggleBtn = productsList.parentElement.querySelector('button[onclick*="toggleEditMode"]');
            if (toggleBtn) {
                toggleBtn.innerHTML = '<i class="bi bi-pencil"></i> Éditer les prix';
                toggleBtn.className = 'btn btn-sm btn-outline-primary';
            }
        } else {
            // Entrer en mode édition
            productsList.classList.add('editing');
            productsList.querySelectorAll('.price-edit').forEach(el => el.style.display = 'inline-block');
            productsList.querySelectorAll('.price-display').forEach(el => el.style.display = 'none');
            productsList.querySelectorAll('.product-actions').forEach(el => el.style.display = 'inline-block');
            
            // Changer le bouton
            const toggleBtn = productsList.parentElement.querySelector('button[onclick*="toggleEditMode"]');
            if (toggleBtn) {
                toggleBtn.innerHTML = '<i class="bi bi-x"></i> Annuler édition';
                toggleBtn.className = 'btn btn-sm btn-outline-danger';
            }
        }
    }

    // Nouvelle fonction pour sauvegarder l'édition d'un produit
    async saveProductEdit(scanId, productIndex) {
        try {
            const productItem = document.querySelector(`#products-${scanId} .product-item[data-product-index="${productIndex}"]`);
            const priceInput = productItem.querySelector('.price-edit input');
            const newPrice = parseFloat(priceInput.value);
            
            if (isNaN(newPrice) || newPrice < 0) {
                showNotification('Prix invalide', 'warning');
                return;
            }
            
            // Mettre à jour l'affichage
            const priceDisplay = productItem.querySelector('.price-display');
            priceDisplay.textContent = this.formatPrice(newPrice);
            
            // Mettre à jour les données dans les résultats
            const scanResult = this.results.find(r => r.id === scanId);
            if (scanResult && scanResult.result.products[productIndex]) {
                scanResult.result.products[productIndex].total_price = newPrice;
                scanResult.result.products[productIndex].prix_total = newPrice;
            }
            
            showNotification('Prix mis à jour', 'success');
            
            // Sortir du mode édition pour ce produit
            this.cancelProductEdit(scanId, productIndex);
            
        } catch (error) {
            console.error('❌ Erreur sauvegarde prix:', error);
            showNotification('Erreur lors de la sauvegarde', 'error');
        }
    }

    // Nouvelle fonction pour annuler l'édition d'un produit
    cancelProductEdit(scanId, productIndex) {
        const productItem = document.querySelector(`#products-${scanId} .product-item[data-product-index="${productIndex}"]`);
        const priceEdit = productItem.querySelector('.price-edit');
        const priceDisplay = productItem.querySelector('.price-display');
        const actions = productItem.querySelector('.product-actions');
        
        priceEdit.style.display = 'none';
        priceDisplay.style.display = 'inline';
        actions.style.display = 'none';
    }

    // Nouvelle fonction pour voir une facture
    viewInvoice(invoiceId) {
        // Rediriger vers la page factures avec l'ID
        window.open(`/factures#invoice-${invoiceId}`, '_blank');
    }

    // Fonction utilitaire pour formater les prix
    formatPrice(price) {
        return new Intl.NumberFormat('fr-FR', {
            style: 'currency',
            currency: 'EUR'
        }).format(parseFloat(price) || 0);
    }
    
    // 🧠 NOUVELLES FONCTIONNALITÉS IA
    
    async analyzeBatchWithAI() {
        """
        🎯 ANALYSE IA DU BATCH COMPLET
        Détecte les patterns d'anomalies et suggère des mises à jour de prix
        """
        const completedScans = Array.from(this.results.values()).filter(item => item.status === 'completed');
        
        if (completedScans.length === 0) {
            this.showNotification('Aucun scan terminé à analyser', 'warning');
            return;
        }
        
        try {
            console.log(`🧠 Analyse IA de ${completedScans.length} factures...`);
            
            // Préparer les données pour l'IA
            const batchData = completedScans.map(scan => ({
                supplier: scan.result.supplier || scan.result.fournisseur,
                products: scan.result.products || [],
                price_comparison: scan.result.price_comparison,
                analysis_timestamp: scan.result.analysis_timestamp
            }));
            
            // Appel API d'analyse IA
            const response = await fetch('/api/ai/analyze-batch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    batch_results: batchData
                })
            });
            
            const aiAnalysis = await response.json();
            
            if (aiAnalysis.success) {
                this.displayAIAnalysis(aiAnalysis.data);
                this.handleAISuggestions(aiAnalysis.data.ai_suggestions);
            } else {
                throw new Error(aiAnalysis.error);
            }
            
        } catch (error) {
            console.error('❌ Erreur analyse IA:', error);
            this.showNotification('Erreur lors de l\'analyse IA', 'danger');
        }
    }
    
    displayAIAnalysis(analysis) {
        """Afficher les résultats de l'analyse IA"""
        const aiResultsContainer = document.getElementById('aiAnalysisResults') || this.createAIResultsContainer();
        
        const html = `
            <div class="card border-primary mb-4">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0">
                        <i class="bi bi-robot"></i> Analyse IA du Batch
                    </h5>
                </div>
                <div class="card-body">
                    <!-- Statistiques générales -->
                    <div class="row mb-4">
                        <div class="col-md-3">
                            <div class="text-center">
                                <div class="h4 text-primary">${analysis.total_scans}</div>
                                <small>Factures analysées</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="text-center">
                                <div class="h4 text-warning">${analysis.anomalies_detected}</div>
                                <small>Anomalies détectées</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="text-center">
                                <div class="h4 text-success">${analysis.recurring_price_patterns.length}</div>
                                <small>Patterns récurrents</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="text-center">
                                <div class="h4 text-info">${analysis.auto_update_candidates.length}</div>
                                <small>Mises à jour auto</small>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Insights par fournisseur -->
                    ${this.renderSupplierInsights(analysis.supplier_insights)}
                    
                    <!-- Suggestions IA -->
                    ${this.renderAISuggestions(analysis.ai_suggestions)}
                    
                    <!-- Actions recommandées -->
                    <div class="mt-4">
                        <h6>🎯 Actions recommandées</h6>
                        ${this.renderRecommendedActions(analysis)}
                    </div>
                </div>
            </div>
        `;
        
        aiResultsContainer.innerHTML = html;
    }
    
    createAIResultsContainer() {
        """Créer le conteneur pour les résultats IA"""
        const container = document.createElement('div');
        container.id = 'aiAnalysisResults';
        container.className = 'ai-analysis-container';
        
        // Insérer avant les résultats de scan
        const resultsContainer = document.getElementById('scanResults');
        resultsContainer.parentNode.insertBefore(container, resultsContainer);
        
        return container;
    }
    
    renderSupplierInsights(insights) {
        """Afficher les insights par fournisseur"""
        if (!insights || Object.keys(insights).length === 0) {
            return '<p class="text-muted">Aucun insight fournisseur disponible</p>';
        }
        
        let html = '<div class="supplier-insights mb-4">';
        html += '<h6>📊 Insights par fournisseur</h6>';
        html += '<div class="row">';
        
        for (const [supplier, data] of Object.entries(insights)) {
            const confidenceClass = data.confidence_level === 'high_confidence_changes' ? 'danger' : 
                                   data.confidence_level === 'moderate_changes' ? 'warning' : 'success';
            
            html += `
                <div class="col-md-6 mb-3">
                    <div class="card border-${confidenceClass}">
                        <div class="card-body">
                            <h6 class="card-title">${supplier}</h6>
                            <div class="small">
                                <div>Produits scannés: ${data.total_products_scanned}</div>
                                <div>Anomalies: ${data.anomalies_detected} (${data.anomaly_rate}%)</div>
                                <div>Patterns détectés: ${data.price_patterns_detected}</div>
                            </div>
                            <div class="mt-2">
                                ${data.recommended_actions.map(action => `
                                    <div class="badge bg-${confidenceClass} me-1">${action}</div>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        html += '</div></div>';
        return html;
    }
    
    renderAISuggestions(suggestions) {
        """Afficher les suggestions IA avec interface de validation client"""
        if (!suggestions || suggestions.length === 0) {
            return '<p class="text-muted">Aucune suggestion IA disponible</p>';
        }
        
        let html = '<div class="ai-suggestions mb-4">';
        html += '<h6>🤖 Suggestions IA - Validation requise</h6>';
        html += '<div class="alert alert-info small mb-3">';
        html += '<i class="bi bi-info-circle"></i> ';
        html += 'L\'IA a détecté des patterns de prix récurrents. Veuillez réviser et valider chaque suggestion.';
        html += '</div>';
        
        suggestions.forEach((suggestion, index) => {
            const recommendationClass = suggestion.recommendation_level === 'strong' ? 'success' : 
                                       suggestion.recommendation_level === 'moderate' ? 'warning' : 'secondary';
            
            html += `
                <div class="card border-${recommendationClass} mb-3" id="suggestion-${suggestion.id}">
                    <div class="card-header bg-light">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <strong>${suggestion.product_name}</strong> 
                                <span class="text-muted">chez ${suggestion.supplier}</span>
                                <span class="badge bg-${recommendationClass} ms-2">${suggestion.recommendation_level}</span>
                            </div>
                            <div class="text-end">
                                <div class="fw-bold">${suggestion.current_reference_price}€ → ${suggestion.suggested_new_price}€</div>
                                <small class="text-muted">Confiance: ${suggestion.confidence}%</small>
                            </div>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <small class="text-muted">Changement de prix:</small>
                                <div class="${suggestion.price_change > 0 ? 'text-danger' : 'text-success'}">
                                    ${suggestion.price_change > 0 ? '+' : ''}${suggestion.price_change.toFixed(2)}€ 
                                    (${suggestion.percentage_change > 0 ? '+' : ''}${suggestion.percentage_change.toFixed(1)}%)
                                </div>
                            </div>
                            <div class="col-md-6">
                                <small class="text-muted">Évidence:</small>
                                <div>${suggestion.evidence_count} occurrences détectées</div>
                            </div>
                        </div>
                        
                        <!-- Interface de validation -->
                        <div class="validation-interface">
                            <div class="row">
                                <div class="col-md-8">
                                    <div class="btn-group w-100" role="group">
                                        <input type="radio" class="btn-check" name="decision-${suggestion.id}" 
                                               id="accept-${suggestion.id}" value="accept">
                                        <label class="btn btn-outline-success" for="accept-${suggestion.id}">
                                            <i class="bi bi-check-circle"></i> Accepter ${suggestion.suggested_new_price}€
                                        </label>
                                        
                                        <input type="radio" class="btn-check" name="decision-${suggestion.id}" 
                                               id="modify-${suggestion.id}" value="modify">
                                        <label class="btn btn-outline-warning" for="modify-${suggestion.id}">
                                            <i class="bi bi-pencil"></i> Modifier
                                        </label>
                                        
                                        <input type="radio" class="btn-check" name="decision-${suggestion.id}" 
                                               id="reject-${suggestion.id}" value="reject">
                                        <label class="btn btn-outline-danger" for="reject-${suggestion.id}">
                                            <i class="bi bi-x-circle"></i> Rejeter
                                        </label>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <button class="btn btn-primary w-100" 
                                            onclick="batchScanner.validateSuggestion('${suggestion.id}')">
                                        <i class="bi bi-check2"></i> Valider
                                    </button>
                                </div>
                            </div>
                            
                            <!-- Champ prix personnalisé (masqué par défaut) -->
                            <div class="custom-price-input mt-2" id="custom-price-${suggestion.id}" style="display: none;">
                                <div class="input-group">
                                    <span class="input-group-text">€</span>
                                    <input type="number" class="form-control" step="0.01" 
                                           placeholder="Nouveau prix" id="price-input-${suggestion.id}">
                                    <span class="input-group-text">€</span>
                                </div>
                            </div>
                            
                            <!-- Champ notes -->
                            <div class="mt-2">
                                <input type="text" class="form-control form-control-sm" 
                                       placeholder="Notes (optionnel)" id="notes-${suggestion.id}">
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        // Bouton de validation en masse
        html += `
            <div class="text-center mt-3">
                <button class="btn btn-success btn-lg" onclick="batchScanner.bulkValidateSuggestions()">
                    <i class="bi bi-check-all"></i> Valider toutes les sélections
                </button>
            </div>
        `;
        
        html += '</div>';
        return html;
    }
    
    setupSuggestionListeners() {
        """Configurer les listeners pour l'interface de validation"""
        // Listener pour afficher/masquer le champ prix personnalisé
        document.addEventListener('change', (e) => {
            if (e.target.type === 'radio' && e.target.name.startsWith('decision-')) {
                const suggestionId = e.target.name.replace('decision-', '');
                const customPriceDiv = document.getElementById(`custom-price-${suggestionId}`);
                
                if (e.target.value === 'modify') {
                    customPriceDiv.style.display = 'block';
                    document.getElementById(`price-input-${suggestionId}`).focus();
                } else {
                    customPriceDiv.style.display = 'none';
                }
            }
        });
    }
    
    async validateSuggestion(suggestionId) {
        """Valider une suggestion IA individuelle"""
        try {
            // Récupérer la décision du client
            const decisionElement = document.querySelector(`input[name="decision-${suggestionId}"]:checked`);
            if (!decisionElement) {
                this.showNotification('Veuillez sélectionner une action (Accepter/Modifier/Rejeter)', 'warning');
                return;
            }
            
            const decision = decisionElement.value;
            const notes = document.getElementById(`notes-${suggestionId}`).value;
            let modifiedPrice = null;
            
            // Si modification, récupérer le nouveau prix
            if (decision === 'modify') {
                const priceInput = document.getElementById(`price-input-${suggestionId}`);
                modifiedPrice = parseFloat(priceInput.value);
                
                if (!modifiedPrice || modifiedPrice <= 0) {
                    this.showNotification('Veuillez saisir un prix valide', 'warning');
                    priceInput.focus();
                    return;
                }
            }
            
            // Appel API de validation
            const response = await fetch(`/api/ai/validate-suggestion/${suggestionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    decision: decision,
                    modified_price: modifiedPrice,
                    notes: notes
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Marquer la suggestion comme traitée
                const suggestionCard = document.getElementById(`suggestion-${suggestionId}`);
                suggestionCard.classList.add('border-success', 'bg-light');
                suggestionCard.querySelector('.validation-interface').innerHTML = `
                    <div class="alert alert-success mb-0">
                        <i class="bi bi-check-circle"></i> ${result.message}
                    </div>
                `;
                
                this.showNotification('✅ Suggestion validée avec succès', 'success');
            } else {
                throw new Error(result.error);
            }
            
        } catch (error) {
            console.error('❌ Erreur validation suggestion:', error);
            this.showNotification('Erreur lors de la validation', 'danger');
        }
    }
    
    async bulkValidateSuggestions() {
        """Valider toutes les suggestions sélectionnées en une fois"""
        try {
            // Collecter toutes les validations
            const validations = [];
            const suggestionCards = document.querySelectorAll('[id^="suggestion-"]');
            
            suggestionCards.forEach(card => {
                const suggestionId = card.id.replace('suggestion-', '');
                const decisionElement = card.querySelector(`input[name="decision-${suggestionId}"]:checked`);
                
                if (decisionElement && !card.classList.contains('bg-light')) {
                    const decision = decisionElement.value;
                    const notes = card.querySelector(`#notes-${suggestionId}`).value;
                    let modifiedPrice = null;
                    
                    if (decision === 'modify') {
                        const priceInput = card.querySelector(`#price-input-${suggestionId}`);
                        modifiedPrice = parseFloat(priceInput.value);
                        
                        if (!modifiedPrice || modifiedPrice <= 0) {
                            this.showNotification(`Prix invalide pour la suggestion ${suggestionId}`, 'warning');
                            return;
                        }
                    }
                    
                    validations.push({
                        suggestion_id: suggestionId,
                        decision: decision,
                        modified_price: modifiedPrice,
                        notes: notes
                    });
                }
            });
            
            if (validations.length === 0) {
                this.showNotification('Aucune suggestion sélectionnée', 'warning');
                return;
            }
            
            // Appel API de validation en masse
            const response = await fetch('/api/ai/bulk-validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    validations: validations
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                const data = result.data;
                this.showNotification(
                    `✅ Validation terminée: ${data.accepted} acceptées, ${data.modified} modifiées, ${data.rejected} rejetées`, 
                    'success'
                );
                
                // Marquer toutes les suggestions comme traitées
                validations.forEach(v => {
                    const suggestionCard = document.getElementById(`suggestion-${v.suggestion_id}`);
                    suggestionCard.classList.add('border-success', 'bg-light');
                    suggestionCard.querySelector('.validation-interface').innerHTML = `
                        <div class="alert alert-success mb-0">
                            <i class="bi bi-check-circle"></i> Suggestion ${v.decision === 'accept' ? 'acceptée' : 
                                                                                v.decision === 'modify' ? 'modifiée' : 'rejetée'}
                        </div>
                    `;
                });
                
                // Afficher les erreurs s'il y en a
                if (data.errors.length > 0) {
                    console.warn('Erreurs lors de la validation:', data.errors);
                }
                
            } else {
                throw new Error(result.error);
            }
            
        } catch (error) {
            console.error('❌ Erreur validation en masse:', error);
            this.showNotification('Erreur lors de la validation en masse', 'danger');
        }
    }
    
    renderRecommendedActions(analysis) {
        """Afficher les actions recommandées"""
        const autoUpdates = analysis.auto_update_candidates.length;
        const totalSuggestions = analysis.ai_suggestions.length;
        
        let html = '<div class="recommended-actions">';
        
        if (autoUpdates > 0) {
            html += `
                <button class="btn btn-success me-2" onclick="batchScanner.applyAllAutoUpdates()">
                    <i class="bi bi-robot"></i> Appliquer ${autoUpdates} mises à jour automatiques
                </button>
            `;
        }
        
        if (totalSuggestions > autoUpdates) {
            html += `
                <button class="btn btn-warning me-2" onclick="batchScanner.reviewAllSuggestions()">
                    <i class="bi bi-eye"></i> Réviser ${totalSuggestions - autoUpdates} suggestions manuelles
                </button>
            `;
        }
        
        html += `
            <button class="btn btn-info" onclick="batchScanner.exportAIReport()">
                <i class="bi bi-download"></i> Exporter rapport IA
            </button>
        `;
        
        html += '</div>';
        return html;
    }
    
    async applyAllAutoUpdates() {
        """Appliquer toutes les mises à jour automatiques"""
        try {
            const response = await fetch('/api/ai/apply-all-auto-updates', {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification(`✅ ${result.applied_count} mises à jour appliquées`, 'success');
                // Rafraîchir l'analyse
                setTimeout(() => this.analyzeBatchWithAI(), 1000);
            } else {
                throw new Error(result.error);
            }
            
        } catch (error) {
            console.error('❌ Erreur application batch:', error);
            this.showNotification('Erreur lors de l\'application des mises à jour', 'danger');
        }
    }
    
    reviewSuggestion(suggestionId) {
        """Ouvrir la modal de révision d'une suggestion"""
        // TODO: Implémenter modal de révision détaillée
        this.showNotification('Fonctionnalité de révision en cours de développement', 'info');
    }
    
    async rejectSuggestion(suggestionId) {
        """Rejeter une suggestion IA"""
        if (confirm('Êtes-vous sûr de vouloir rejeter cette suggestion ?')) {
            try {
                const response = await fetch(`/api/ai/reject-suggestion/${suggestionId}`, {
                    method: 'POST'
                });
                
                const result = await response.json();
                
                if (result.success) {
                    this.showNotification('Suggestion rejetée', 'info');
                    // Rafraîchir l'analyse
                    setTimeout(() => this.analyzeBatchWithAI(), 1000);
                }
                
            } catch (error) {
                console.error('❌ Erreur rejet suggestion:', error);
            }
        }
    }
    
    async exportAIReport() {
        """Exporter le rapport d'analyse IA"""
        try {
            const response = await fetch('/api/ai/export-report', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    batch_id: Date.now(),
                    scan_results: Array.from(this.results.values())
                })
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `rapport_ia_batch_${new Date().toISOString().split('T')[0]}.json`;
                a.click();
                window.URL.revokeObjectURL(url);
                
                this.showNotification('📄 Rapport IA exporté', 'success');
            }
            
        } catch (error) {
            console.error('❌ Erreur export rapport:', error);
            this.showNotification('Erreur lors de l\'export du rapport', 'danger');
        }
    }
    
    showNotification(message, type = 'info') {
        """Afficher une notification toast"""
        const toastContainer = document.getElementById('toastContainer') || this.createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        // Initialiser et afficher le toast
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Nettoyer après fermeture
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
    
    createToastContainer() {
        """Créer le conteneur pour les toasts"""
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
        return container;
    }
}

// Initialisation
let batchScanner;
document.addEventListener('DOMContentLoaded', () => {
    batchScanner = new BatchScanner();
    window.batchScanner = batchScanner; // Export après création
    console.log('🚀 Scanner Batch initialisé');
    
    // Vérifier si les éléments existent
    if (!document.getElementById('batchDropZone')) {
        console.error('❌ Element batchDropZone introuvable!');
    }
}); 
}); 