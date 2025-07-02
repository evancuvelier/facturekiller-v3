// FactureKiller V3 - Scanner Pro Mobile
// Optimisé pour mobile avec IA Vision

class ScannerPro {
    constructor() {
        console.log('🚀 FactureKiller V3 Scanner PRO - Initialisation...');
        
        // Nettoyer le localStorage au démarrage pour éviter les quotas dépassés
        this.cleanupLocalStorage();
        
        this.scanHistory = JSON.parse(localStorage.getItem('scanHistory') || '[]');
        this.analysisResult = null;
        this.currentFile = null;
        this.currentImageData = null;
        this.selectedOrderId = null;
        this.isProcessing = false;
        this.currentFacingMode = 'environment';
        this.stream = null;
        
        // 🆕 GESTION MULTI-PAGES
        this.invoicePages = []; // Stockage des pages multiples
        this.currentPageIndex = 0;
        this.isMultiPageMode = false;
        
        // 🚀 NOUVEAU: GESTION MULTI-FACTURES
        this.scannedInvoices = []; // Liste des factures scannées
        this.currentInvoiceId = null; // ID de la facture actuellement affichée
        this.isMultiInvoiceMode = false; // Mode multi-factures activé
        this.invoiceCounter = 0; // Compteur pour générer des IDs uniques
        
        // 🚀 NOUVEAU: GESTION MULTI-FACTURES
        this.scannedInvoices = []; // Liste des factures scannées
        this.currentInvoiceId = null; // ID de la facture actuellement affichée
        this.isMultiInvoiceMode = false; // Mode multi-factures activé
        this.invoiceCounter = 0; // Compteur pour générer des IDs uniques
        
        this.video = null;
        this.canvas = null;
        this.context = null;
        this.currentStream = null;
        this.isSaved = false; // Pour les rappels de sauvegarde
        this.cameras = [];
        this.currentCameraIndex = 0;
        
        // Touch gestures
        this.touchStartY = 0;
        this.touchStartX = 0;
        
        // Auto-focus
        this.focusTimeouts = new Set();
        
        this.init();
    }
    
    cleanupLocalStorage() {
        try {
            // Vérifier l'espace utilisé
            const testKey = 'test_quota';
            const testValue = 'x'.repeat(1024 * 1024); // 1MB
            
            try {
                localStorage.setItem(testKey, testValue);
                localStorage.removeItem(testKey);
            } catch (e) {
                console.warn('🧹 LocalStorage plein, nettoyage automatique...');
                
                // Supprimer l'historique existant
                localStorage.removeItem('scanHistory');
                
                // Nettoyer d'autres clés potentiellement lourdes
                const keysToClean = ['imageCache', 'analysisCache', 'oldScanData'];
                keysToClean.forEach(key => {
                    localStorage.removeItem(key);
                });
                
                console.log('✅ LocalStorage nettoyé');
            }
        } catch (error) {
            console.error('❌ Erreur nettoyage localStorage:', error);
        }
    }

    init() {
        this.setupEventListeners();
        this.checkCameraSupport();
        this.setupServiceWorker();
        this.setupTouchGestures();
        this.setupKeyboardShortcuts();
        this.handleModeChange();
        this.fixModalAccessibility();
        this.setupRestaurantChangeListener();
        
        // Définir window.scanner pour l'accès global
        window.scanner = this;
        console.log('✅ Scanner Pro initialisé et accessible globalement');
    }

    setupEventListeners() {
        // File input - Support multi-fichiers
        document.getElementById('fileInput')?.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                if (e.target.files.length === 1) {
                    // Un seul fichier - mode normal
                    this.handleFileSelect(e.target.files[0]);
                } else {
                    // Plusieurs fichiers - mode multi-pages
                    this.handleMultipleFiles(e.target.files);
                }
            }
        });

        // Mode selection
        document.querySelectorAll('input[name="scanMode"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.handleModeChange(e.target.value);
            });
        });

        // Touch gestures
        this.setupTouchGestures();
        
        // Keyboard shortcuts
        this.setupKeyboardShortcuts();
        
        // 🎯 NOUVEAU: Écouter les changements de restaurant
        this.setupRestaurantChangeListener();
    }

    setupTouchGestures() {
        let startY = 0;
        let startX = 0;

        document.addEventListener('touchstart', (e) => {
            startY = e.touches[0].clientY;
            startX = e.touches[0].clientX;
        });

        document.addEventListener('touchend', (e) => {
            const endY = e.changedTouches[0].clientY;
            const endX = e.changedTouches[0].clientX;
            const diffY = startY - endY;
            const diffX = startX - endX;

            // Swipe up to analyze
            if (diffY > 50 && Math.abs(diffX) < 100) {
                if (this.currentFile && !this.isProcessing) {
                    this.analyzeInvoice();
                }
            }

            // Swipe down to reset - SUPPRIMÉ pour éviter de perdre les scans
            // if (diffY < -50 && Math.abs(diffX) < 100) {
            //     this.resetScanner();
            // }
        });
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case 'c':
                        e.preventDefault();
                        this.startCamera();
                        break;
                    case 'u':
                        e.preventDefault();
                        document.getElementById('fileInput').click();
                        break;
                    case 'Enter':
                        e.preventDefault();
                        if (this.currentFile) this.analyzeInvoice();
                        break;
                }
            }
        });
    }

    checkCameraSupport() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            console.warn('Camera not supported');
            document.querySelector('[onclick="startCamera()"]').style.display = 'none';
        }
    }

    async setupServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                await navigator.serviceWorker.register('/sw.js');
                console.log('Service Worker registered');
            } catch (error) {
                console.log('Service Worker registration failed');
            }
        }
    }

    handleModeChange(mode) {
        if (mode === 'order') {
            this.showOrderSelection();
        }
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate(50);
        }
    }

    async showOrderSelection() {
        const modal = new bootstrap.Modal(document.getElementById('orderSelectionModal'));
        await this.loadOrdersForModal();
        modal.show();
    }

    async loadOrdersForModal() {
        try {
            // 🎯 CORRECTION: Utiliser les commandes vérifiables du restaurant avec cache-busting
            const timestamp = Date.now();
            const response = await fetch(`/api/orders/verifiable?_t=${timestamp}`, {
                credentials: 'include'
            });
            const data = await response.json();
            
            console.log('📋 Commandes vérifiables chargées:', data);
            
            const ordersList = document.getElementById('ordersList');
            ordersList.innerHTML = '';
            
            if (data.data && data.data.length > 0) {
                data.data.forEach(order => {
                    const orderItem = document.createElement('div');
                    orderItem.className = 'list-group-item list-group-item-action';
                    orderItem.innerHTML = `
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1">${order.supplier_name || order.supplier}</h6>
                            <small class="text-muted">${this.formatDate(order.delivery_date || order.date)}</small>
                        </div>
                        <p class="mb-1">CMD: ${order.order_number || order.id}</p>
                        <small class="text-muted">Statut: ${order.status} • ${order.items?.length || 0} articles</small>
                    `;
                    orderItem.addEventListener('click', () => {
                        this.selectOrder(order.id);
                        bootstrap.Modal.getInstance(document.getElementById('orderSelectionModal')).hide();
                    });
                    ordersList.appendChild(orderItem);
                });
                
                // Afficher le contexte restaurant dans le modal
                if (data.restaurant_context) {
                    const modalTitle = document.querySelector('#orderModalLabel');
                    if (modalTitle) {
                        modalTitle.innerHTML = `<i class="bi bi-cart-check me-2"></i>Commandes - ${data.restaurant_context}`;
                    }
                }
            } else {
                ordersList.innerHTML = `
                    <div class="text-center text-muted p-4">
                        <i class="bi bi-info-circle fs-4 d-block mb-2"></i>
                        Aucune commande vérifiable trouvée
                        ${data.restaurant_context ? `<br><small>Restaurant: ${data.restaurant_context}</small>` : ''}
                    </div>
                `;
            }
        } catch (error) {
            console.error('Erreur chargement commandes vérifiables:', error);
            const ordersList = document.getElementById('ordersList');
            ordersList.innerHTML = '<div class="text-center text-danger p-4"><i class="bi bi-exclamation-triangle me-2"></i>Erreur de chargement</div>';
        }
    }

    selectOrder(orderId) {
        this.selectedOrderId = orderId;
        this.showNotification('Commande sélectionnée', 'success');
    }

    async startCamera() {
        try {
            this.showProgress('Démarrage de la caméra...');
            
            const constraints = {
                video: {
                    facingMode: this.currentFacingMode,
                    width: { ideal: 1920 },
                    height: { ideal: 1080 }
                }
            };

            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            
            const video = document.getElementById('cameraVideo');
            video.srcObject = this.stream;
            
            document.getElementById('uploadZone').style.display = 'none';
            document.getElementById('cameraPreview').style.display = 'block';
            document.getElementById('cameraControls').style.display = 'block';
            
            this.hideProgress();
            
            // Auto-focus
            this.setupAutoFocus(video);
            
        } catch (error) {
            console.error('Erreur caméra:', error);
            this.showNotification('Impossible d\'accéder à la caméra', 'error');
            this.hideProgress();
        }
    }

    setupAutoFocus(video) {
        // Détection de mouvement pour auto-focus
        let lastFrame = null;
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        const detectMovement = () => {
            if (video.videoWidth > 0) {
                canvas.width = video.videoWidth / 4;
                canvas.height = video.videoHeight / 4;
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                
                const currentFrame = ctx.getImageData(0, 0, canvas.width, canvas.height);
                
                if (lastFrame) {
                    let diff = 0;
                    for (let i = 0; i < currentFrame.data.length; i += 4) {
                        diff += Math.abs(currentFrame.data[i] - lastFrame.data[i]);
                    }
                    
                    // Si mouvement détecté, vibrer légèrement
                    if (diff > 10000 && navigator.vibrate) {
                        navigator.vibrate(10);
                    }
                }
                
                lastFrame = currentFrame;
            }
            
            if (this.stream) {
                requestAnimationFrame(detectMovement);
            }
        };
        
        video.addEventListener('loadedmetadata', () => {
            detectMovement();
        });
    }

    async switchCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
        
        this.currentFacingMode = this.currentFacingMode === 'environment' ? 'user' : 'environment';
        await this.startCamera();
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate(100);
        }
    }

    async capturePhoto() {
        const video = document.getElementById('cameraVideo');
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Capture en haute résolution
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        ctx.drawImage(video, 0, 0);
        
        // Appliquer des filtres d'amélioration
        this.enhanceImage(ctx, canvas.width, canvas.height);
        
        // Convertir en blob
        canvas.toBlob((blob) => {
            const file = new File([blob], `scan_${Date.now()}.jpg`, { type: 'image/jpeg' });
            this.handleFileSelect(file);
        }, 'image/jpeg', 0.9);
        
        // Effet de flash
        this.flashEffect();
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate([100, 50, 100]);
        }
    }

    enhanceImage(ctx, width, height) {
        const imageData = ctx.getImageData(0, 0, width, height);
        const data = imageData.data;
        
        // Amélioration du contraste et de la netteté
        for (let i = 0; i < data.length; i += 4) {
            // Augmenter le contraste
            data[i] = Math.min(255, data[i] * 1.2);     // Rouge
            data[i + 1] = Math.min(255, data[i + 1] * 1.2); // Vert
            data[i + 2] = Math.min(255, data[i + 2] * 1.2); // Bleu
        }
        
        ctx.putImageData(imageData, 0, 0);
    }

    flashEffect() {
        const flash = document.createElement('div');
        flash.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: white;
            z-index: 9999;
            opacity: 0.8;
            pointer-events: none;
        `;
        document.body.appendChild(flash);
        
        setTimeout(() => {
            flash.style.opacity = '0';
            flash.style.transition = 'opacity 0.3s ease';
            setTimeout(() => document.body.removeChild(flash), 300);
        }, 100);
    }

    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        document.getElementById('cameraPreview').style.display = 'none';
        document.getElementById('cameraControls').style.display = 'none';
        document.getElementById('uploadZone').style.display = 'block';
    }

    async handleFileSelect(file) {
        // Validation
        if (!this.validateFile(file)) return;
        
        this.currentFile = file;
        
        // Compression automatique si nécessaire
        if (file.size > 2 * 1024 * 1024) { // 2MB
            this.currentFile = await this.compressImage(file);
        }
        
        // Afficher l'aperçu
        await this.showPreview(this.currentFile);
        
        // Arrêter la caméra si active
        this.stopCamera();
        
        // Afficher les boutons d'action
        document.getElementById('actionButtons').style.display = 'block';
        
        // Auto-analyse SEULEMENT si explicitement activée dans les paramètres
        // ET pas déjà en cours de traitement
        if (this.isAutoAnalyzeEnabled() && !this.isProcessing && !this.analysisResult) {
            setTimeout(() => this.analyzeInvoice(), 1000);
        }
    }

    validateFile(file) {
        const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/heic', 'image/heif', 'application/pdf'];
        
        if (!validTypes.includes(file.type) && !file.name.toLowerCase().match(/\.(jpg|jpeg|png|gif|webp|heic|heif|pdf)$/)) {
            this.showNotification('Type de fichier non supporté', 'error');
            return false;
        }
        
        if (file.size > 10 * 1024 * 1024) {
            this.showNotification('Fichier trop volumineux (max 10MB)', 'error');
            return false;
        }
        
        return true;
    }

    async compressImage(file) {
        return new Promise((resolve) => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();
            
            img.onload = () => {
                // Calculer les nouvelles dimensions
                const maxWidth = 1920;
                const maxHeight = 1080;
                let { width, height } = img;
                
                if (width > maxWidth || height > maxHeight) {
                    const ratio = Math.min(maxWidth / width, maxHeight / height);
                    width *= ratio;
                    height *= ratio;
                }
                
                canvas.width = width;
                canvas.height = height;
                ctx.drawImage(img, 0, 0, width, height);
                
                canvas.toBlob((blob) => {
                    const compressedFile = new File([blob], file.name, { type: 'image/jpeg' });
                    resolve(compressedFile);
                }, 'image/jpeg', 0.8);
            };
            
            img.src = URL.createObjectURL(file);
        });
    }

    async showPreview(file) {
        const preview = document.getElementById('imagePreview');
        const img = document.getElementById('previewImg');
        
        // Convertir en base64 pour l'historique
        const reader = new FileReader();
        reader.onload = (e) => {
            this.currentImageData = e.target.result; // Stocker pour l'historique
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
        
        // Affichage
        preview.style.display = 'block';
        document.getElementById('uploadZone').style.display = 'none';
        document.getElementById('actionButtons').style.display = 'block';
    }

    async analyzeInvoice(forceRescan = false) {
        if (!this.currentFile || this.isProcessing) return;
        
        // Empêcher le re-scan automatique si déjà analysé
        // SAUF si c'est un re-scan forcé pour correction d'incohérences
        if (this.analysisResult && !forceRescan) {
            console.log('⚠️ Analyse déjà effectuée, utilisation du cache');
            return;
        }

        if (forceRescan) {
            console.log('🔄 Re-scan forcé pour correction d\'incohérences');
            // Reset des résultats précédents
            this.analysisResult = null;
        }
        
        this.isProcessing = true;
        this.showProgress('Préparation de l\'analyse...');
        
        try {
            const formData = new FormData();
            formData.append('file', this.currentFile);
            
            // Mode de scan
            const scanMode = document.querySelector('input[name="scanMode"]:checked').value;
            formData.append('mode', scanMode);
            
            if (scanMode === 'order' && this.selectedOrderId) {
                formData.append('order_id', this.selectedOrderId);
            }
            
            // Métadonnées
            formData.append('timestamp', Date.now());
            formData.append('device_info', JSON.stringify({
                userAgent: navigator.userAgent,
                screen: { width: screen.width, height: screen.height },
                connection: navigator.connection?.effectiveType || 'unknown'
            }));
            
            // Progression simulée
            this.simulateProgress();
            
            // Appel API
            const response = await fetch('/api/invoices/analyze', {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.analysisResult = result.data;
                await this.displayResults(result.data);
                this.saveToHistory(result.data);
                
                // Notification de succès
                this.showNotification('Analyse terminée avec succès!', 'success');
                
                // Haptic feedback
                if (navigator.vibrate) {
                    navigator.vibrate([200, 100, 200]);
                }
            } else {
                throw new Error(result.error || 'Erreur lors de l\'analyse');
            }
            
        } catch (error) {
            console.error('Erreur analyse:', error);
            this.showNotification(`Erreur: ${error.message}`, 'error');
            
            // Haptic feedback d'erreur
            if (navigator.vibrate) {
                navigator.vibrate([100, 100, 100, 100, 100]);
            }
            
        } finally {
            this.isProcessing = false;
            this.hideProgress();
        }
    }

    simulateProgress() {
        const steps = [
            { percent: 20, text: 'Upload du fichier...' },
            { percent: 40, text: 'OCR en cours...' },
            { percent: 60, text: 'Analyse IA Claude Vision...' },
            { percent: 80, text: 'Comparaison des prix...' },
            { percent: 95, text: 'Finalisation...' }
        ];
        
        let currentStep = 0;
        const interval = setInterval(() => {
            if (currentStep < steps.length) {
                const step = steps[currentStep];
                this.updateProgress(step.percent, step.text);
                currentStep++;
            } else {
                clearInterval(interval);
            }
        }, 800);
    }

    async displayResults(data) {
        try {
            this.hideProgress();
            this.analysisResult = data;
            
            // 🧠 VÉRIFICATION INTELLIGENTE D'INCOHÉRENCES
            if (data.coherence_check) {
                const coherenceIssues = this.checkResultCoherence(data);
                if (coherenceIssues.needsRescan) {
                    return this.handleIncoherentResults(data, coherenceIssues);
                }
            }
            
            // Remplir les informations de facture
            this.fillInvoiceInfo(data);
            
            // Remplir la liste des produits
            await this.fillProductsList(data);
            
            // Afficher les statistiques rapides
            this.fillQuickStats(data);
            
            // Animer l'affichage des résultats
            document.getElementById('scanResults').style.display = 'block';
            document.getElementById('scanResults').scrollIntoView({ 
                behavior: 'smooth', 
                block: 'start' 
            });
            
            // Démarrer le rappel de sauvegarde après 30 secondes
            this.startSaveReminder();
            
            // Sauvegarder automatiquement dans l'historique
            this.saveToHistory(data);
            
            console.log('✅ Résultats affichés avec succès');
            
        } catch (error) {
            console.error('❌ Erreur affichage résultats:', error);
            this.showNotification('Erreur lors de l\'affichage des résultats', 'error');
        }
    }

    checkResultCoherence(data) {
        /**
         * 🧠 VÉRIFICATION INTELLIGENTE DE LA COHÉRENCE DES RÉSULTATS
         * Détecte les problèmes qui nécessitent un re-scan automatique
         */
        const issues = {
            needsRescan: false,
            criticalIssues: [],
            warnings: [],
            confidence: 1.0
        };

        // 1. Vérifier s'il y a déjà une détection d'incohérence par Claude
        if (data.requires_rescan || data.coherence_check?.needs_rescan) {
            issues.needsRescan = true;
            issues.criticalIssues.push(...(data.rescan_reason || data.coherence_check?.critical_issues || []));
        }

        // 2. Vérifier le nombre de produits (seuil minimum)
        if (data.products && data.products.length < 2) {
            issues.warnings.push(`Seulement ${data.products.length} produit(s) détecté(s) - facture peut-être incomplète`);
            issues.confidence -= 0.3;
        }

        // 3. Vérifier les calculs de totaux
        if (data.products && data.total_amount) {
            let calculatedTotal = 0;
            let priceErrors = 0;
            
            for (const product of data.products) {
                const expectedTotal = (product.quantity || 1) * (product.unit_price || 0);
                const actualTotal = product.total_price || 0;
                
                // Vérifier cohérence des calculs
                if (Math.abs(expectedTotal - actualTotal) > 0.01) {
                    priceErrors++;
                }
                
                calculatedTotal += actualTotal;
            }
            
            // Si plus de 30% des produits ont des erreurs de calcul
            if (priceErrors > data.products.length * 0.3) {
                issues.needsRescan = true;
                issues.criticalIssues.push(`${priceErrors}/${data.products.length} produits ont des calculs de prix incohérents`);
            }
            
            // Vérifier le total général
            const totalDifference = Math.abs(calculatedTotal - data.total_amount);
            if (totalDifference > 10 || (totalDifference / data.total_amount) > 0.05) {
                issues.needsRescan = true;
                issues.criticalIssues.push(`Total incohérent: calculé ${calculatedTotal.toFixed(2)}€ vs déclaré ${data.total_amount.toFixed(2)}€`);
            }
        }

        // 4. Détecter les produits avec des noms suspects
        if (data.products) {
            const suspiciousProducts = data.products.filter(p => 
                !p.name || 
                p.name.length < 3 || 
                /^[\d\s\-\.]+$/.test(p.name) ||
                p.unit_price === 0
            );
            
            if (suspiciousProducts.length > data.products.length * 0.4) {
                issues.needsRescan = true;
                issues.criticalIssues.push(`${suspiciousProducts.length} produits suspects détectés (noms vides/incorrects)`);
            }
        }

        // 5. Calculer le score de confiance final
        if (issues.criticalIssues.length > 0) {
            issues.confidence = Math.max(0.1, issues.confidence - (issues.criticalIssues.length * 0.2));
        }

        console.log('🔍 Vérification cohérence:', issues);
        return issues;
    }

    async handleIncoherentResults(data, coherenceIssues) {
        /**
         * 🔄 GESTION DES RÉSULTATS INCOHÉRENTS
         * Propose/déclenche automatiquement un re-scan
         */
        console.log('⚠️ Résultats incohérents détectés, gestion automatique...');
        
        // Afficher une notification d'incohérence
        this.showNotification('Incohérences détectées dans l\'analyse - Vérification automatique...', 'warning');
        
        // Masquer les résultats partiels
        document.getElementById('scanResults').style.display = 'none';
        
        // Afficher le modal d'incohérence avec options
        this.showCoherenceModal(data, coherenceIssues);
    }

    showCoherenceModal(data, coherenceIssues) {
        /**
         * 📋 MODAL DE GESTION DES INCOHÉRENCES
         * Permet à l'utilisateur de choisir l'action à prendre
         */
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-warning text-dark">
                        <h5 class="modal-title">
                            <i class="bi bi-exclamation-triangle me-2"></i>Incohérences Détectées
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-warning">
                            <h6><i class="bi bi-robot me-2"></i>Analyse Intelligente</h6>
                            <p class="mb-2">L'IA a détecté des incohérences qui suggèrent que l'analyse n'est pas complète ou correcte :</p>
                        </div>
                        
                        ${coherenceIssues.criticalIssues.length > 0 ? `
                            <div class="mb-3">
                                <h6 class="text-danger"><i class="bi bi-x-circle me-2"></i>Problèmes Critiques :</h6>
                                <ul class="list-unstyled">
                                    ${coherenceIssues.criticalIssues.map(issue => `
                                        <li class="text-danger mb-1">• ${issue}</li>
                                    `).join('')}
                                </ul>
                            </div>
                        ` : ''}
                        
                        ${coherenceIssues.warnings.length > 0 ? `
                            <div class="mb-3">
                                <h6 class="text-warning"><i class="bi bi-exclamation-triangle me-2"></i>Avertissements :</h6>
                                <ul class="list-unstyled">
                                    ${coherenceIssues.warnings.map(warning => `
                                        <li class="text-warning mb-1">• ${warning}</li>
                                    `).join('')}
                                </ul>
                            </div>
                        ` : ''}
                        
                        <div class="mb-3">
                            <div class="d-flex align-items-center justify-content-between mb-2">
                                <span>Niveau de confiance :</span>
                                <span class="badge ${coherenceIssues.confidence > 0.7 ? 'bg-success' : coherenceIssues.confidence > 0.4 ? 'bg-warning' : 'bg-danger'}">
                                    ${Math.round(coherenceIssues.confidence * 100)}%
                                </span>
                            </div>
                            <div class="progress">
                                <div class="progress-bar ${coherenceIssues.confidence > 0.7 ? 'bg-success' : coherenceIssues.confidence > 0.4 ? 'bg-warning' : 'bg-danger'}" 
                                     style="width: ${coherenceIssues.confidence * 100}%"></div>
                            </div>
                        </div>
                        
                        <div class="alert alert-info">
                            <h6><i class="bi bi-lightbulb me-2"></i>Recommandations :</h6>
                            <p class="mb-2">Pour améliorer la précision :</p>
                            <ul class="mb-0">
                                <li>Assurez-vous que la facture est bien éclairée et nette</li>
                                <li>Vérifiez que tous les produits sont visibles</li>
                                <li>Évitez les reflets ou les ombres sur le document</li>
                            </ul>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <div class="d-flex justify-content-between w-100">
                            <div>
                                <button type="button" class="btn btn-outline-primary" onclick="scanner.acceptPartialResults()">
                                    <i class="bi bi-check me-2"></i>Accepter malgré tout
                                </button>
                            </div>
                            <div>
                                <button type="button" class="btn btn-warning me-2" onclick="scanner.retryAutomaticScan()">
                                    <i class="bi bi-arrow-repeat me-2"></i>Re-scanner automatiquement
                                </button>
                                <button type="button" class="btn btn-primary" onclick="scanner.retakePhoto()">
                                    <i class="bi bi-camera me-2"></i>Reprendre la photo
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        // Stocker les données pour les actions
        this.partialResults = data;
        this.coherenceIssues = coherenceIssues;
        
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
    }

    async retryAutomaticScan() {
        /**
         * 🔄 RE-SCAN AUTOMATIQUE
         * Relance l'analyse avec des paramètres optimisés
         */
        console.log('🔄 Démarrage du re-scan automatique...');
        
        // Fermer le modal
        const modal = document.querySelector('.modal.show');
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            bsModal.hide();
        }
        
        this.showNotification('Re-scan automatique en cours...', 'info');
        this.showProgress('Re-scan intelligent avec paramètres optimisés...');
        
        try {
            // Relancer l'analyse avec l'image existante
            if (this.currentFile || this.currentImageData) {
                await this.analyzeInvoice(true); // true = force rescan
            } else {
                this.showNotification('Image non disponible pour le re-scan', 'error');
                this.hideProgress();
            }
        } catch (error) {
            console.error('❌ Erreur re-scan automatique:', error);
            this.showNotification('Erreur lors du re-scan automatique', 'error');
            this.hideProgress();
        }
    }

    acceptPartialResults() {
        /**
         * ✅ ACCEPTER LES RÉSULTATS PARTIELS
         * Affiche les résultats malgré les incohérences
         */
        console.log('✅ Acceptation des résultats partiels...');
        
        // Fermer le modal
        const modal = document.querySelector('.modal.show');
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            bsModal.hide();
        }
        
        // Marquer les résultats comme acceptés malgré les problèmes
        if (this.partialResults) {
            this.partialResults.accepted_with_issues = true;
            this.partialResults.coherence_override = true;
            
            // Afficher les résultats normalement
            this.displayResults(this.partialResults);
            
            this.showNotification('Résultats acceptés - Vérifiez et corrigez si nécessaire', 'warning');
        }
    }

    retakePhoto() {
        /**
         * 📸 REPRENDRE LA PHOTO
         * Remet le scanner en mode capture
         */
        console.log('📸 Reprise de photo demandée...');
        
        // Fermer le modal
        const modal = document.querySelector('.modal.show');
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            bsModal.hide();
        }
        
        // Reset complet du scanner
        this.resetScanner();
        this.showNotification('Reprenez une photo de meilleure qualité', 'info');
    }

    formatResultsHTML(data) {
        let html = '<div class="scan-results">';
        
        // Informations de base
        if (data.invoice_info) {
            html += `
                <div class="row mb-3">
                    <div class="col-6">
                        <div class="text-center">
                            <div class="h4 text-primary">${this.formatPrice(data.invoice_info.total_amount || 0)}</div>
                            <small class="text-muted">Montant total</small>
                        </div>
                    </div>
                    <div class="col-6">
                        <div class="text-center">
                            <div class="h4 text-info">${data.products ? data.products.length : 0}</div>
                            <small class="text-muted">Produits</small>
                        </div>
                    </div>
                </div>
            `;
            
            html += `
                <div class="mb-3">
                    <strong>Fournisseur:</strong> ${data.invoice_info.supplier || 'Non détecté'}<br>
                    <strong>Date:</strong> ${data.invoice_info.date || 'Non détectée'}<br>
                    <strong>Référence:</strong> ${data.invoice_info.reference || 'Non détectée'}
                </div>
            `;
        }
        
        // Liste des produits (simplifiée)
        if (data.products && data.products.length > 0) {
            html += '<div class="products-list">';
            html += '<h6 class="mb-2">🛒 Produits détectés:</h6>';
            
            data.products.slice(0, 5).forEach(product => {
                html += `
                    <div class="d-flex justify-content-between align-items-center py-1 border-bottom">
                        <span class="text-truncate" style="max-width: 200px;">${product.name || 'Produit sans nom'}</span>
                        <span class="fw-bold">${this.formatPrice(product.unit_price || 0)}</span>
                    </div>
                `;
            });
            
            if (data.products.length > 5) {
                html += `<small class="text-muted">... et ${data.products.length - 5} autres produits</small>`;
            }
            
            html += '</div>';
        }
        
        html += '</div>';
        return html;
    }

    startSaveReminder() {
        // Rappel après 10 secondes si pas encore sauvegardé
        setTimeout(() => {
            if (!this.isSaved && this.analysisResult) {
                this.showSaveReminder();
            }
        }, 10000);
        
        // Rappel plus insistant après 30 secondes
        setTimeout(() => {
            if (!this.isSaved && this.analysisResult) {
                this.showUrgentSaveReminder();
            }
        }, 30000);
    }

    showSaveReminder() {
        // Animation du bouton de sauvegarde
        const saveBtn = document.getElementById('saveBtn');
        if (saveBtn) {
            saveBtn.style.animation = 'pulse 1s infinite';
            saveBtn.style.backgroundColor = '#fd7e14';
        }
        
        // Notification discrète
        this.showNotification('💾 N\'oubliez pas de sauvegarder votre facture !', 'warning');
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate([200, 100, 200]);
        }
    }

    showUrgentSaveReminder() {
        // Modal de rappel urgent
        const reminderModal = document.createElement('div');
        reminderModal.className = 'modal fade';
        reminderModal.id = 'saveReminderModal';
        reminderModal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-warning">
                    <div class="modal-header bg-warning text-dark">
                        <h5 class="modal-title">
                            <i class="bi bi-exclamation-triangle me-2"></i>
                            Sauvegarde Recommandée
                        </h5>
                    </div>
                    <div class="modal-body">
                        <div class="text-center">
                            <i class="bi bi-save display-1 text-warning mb-3"></i>
                            <h6>Votre facture n'est pas encore sauvegardée !</h6>
                            <p class="text-muted">
                                Pour que votre facture apparaisse dans la liste des factures, 
                                vous devez la sauvegarder.
                            </p>
                        </div>
                    </div>
                    <div class="modal-footer justify-content-center">
                        <button type="button" class="btn btn-success btn-lg" onclick="saveInvoice(); bootstrap.Modal.getInstance(document.getElementById('saveReminderModal')).hide();">
                            <i class="bi bi-save me-2"></i>Sauvegarder Maintenant
                        </button>
                        <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">
                            Plus tard
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(reminderModal);
        const modal = new bootstrap.Modal(reminderModal);
        modal.show();
        
        // Nettoyer après fermeture
        reminderModal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(reminderModal);
        });
    }

    fillQuickStats(data) {
        // Vérifier et remplir seulement les éléments qui existent
        const totalProductsEl = document.getElementById('totalProducts');
        const totalAmountEl = document.getElementById('totalAmount');
        
        if (totalProductsEl) {
            totalProductsEl.textContent = data.products?.length || 0;
        }
        
        if (totalAmountEl) {
            totalAmountEl.textContent = this.formatPrice(data.total_amount || 0);
        }
        
        // Éléments optionnels qui peuvent ne pas exister
        const savingsAmountEl = document.getElementById('savingsAmount');
        const newProductsEl = document.getElementById('newProducts');
        
        if (savingsAmountEl) {
            const stats = data.price_comparison || {};
            savingsAmountEl.textContent = this.formatPrice(stats.total_savings || 0);
        }
        
        if (newProductsEl) {
            const stats = data.price_comparison || {};
            newProductsEl.textContent = stats.new_products || 0;
        }
        
        // Animation des chiffres
        this.animateNumbers();
    }

    animateNumbers() {
        const elements = document.querySelectorAll('.stat-card .fs-4');
        elements.forEach(el => {
            const finalValue = el.textContent;
            const isPrice = finalValue.includes('€');
            const numValue = parseFloat(finalValue.replace(/[€\s]/g, ''));
            
            if (!isNaN(numValue)) {
                let current = 0;
                const increment = numValue / 30;
                const timer = setInterval(() => {
                    current += increment;
                    if (current >= numValue) {
                        current = numValue;
                        clearInterval(timer);
                    }
                    el.textContent = isPrice ? this.formatPrice(current) : Math.floor(current);
                }, 50);
            }
        });
    }

    fillInvoiceInfo(data) {
        // Vérifier et remplir seulement les éléments qui existent
        const supplierNameEl = document.getElementById('supplierName');
        const invoiceNumberEl = document.getElementById('invoiceNumber');
        const invoiceDateEl = document.getElementById('invoiceDate');
        const vatAmountEl = document.getElementById('vatAmount');
        
        if (supplierNameEl) {
            supplierNameEl.textContent = data.supplier || '-';
        }
        
        if (invoiceNumberEl) {
            invoiceNumberEl.textContent = data.invoice_number || '-';
        }
        
        if (invoiceDateEl) {
            invoiceDateEl.textContent = this.formatDate(data.date) || '-';
        }
        
        if (vatAmountEl) {
            vatAmountEl.textContent = this.formatPrice(data.vat_amount || 0);
        }
    }

    async fillProductsList(data) {
        const container = document.getElementById('productsContainer');
        container.innerHTML = '';
        
        if (!data.products || data.products.length === 0) {
            container.innerHTML = '<div class="text-center text-muted p-4">Aucun produit détecté</div>';
            return;
        }

        // Créer le HTML de tous les produits
        let productsHTML = '';
        data.products.forEach((product, index) => {
            productsHTML += this.createProductElement(product, index);
        });
        
        // Injecter tout le HTML d'un coup
        container.innerHTML = productsHTML;
        
        // Animation pour chaque produit
        const productElements = container.querySelectorAll('.product-item');
        productElements.forEach((productEl, index) => {
            // Style initial pour animation
            productEl.style.opacity = '0';
            productEl.style.transform = 'translateX(-20px)';
            productEl.style.transition = 'all 0.3s ease';
            
            // Animation décalée
            setTimeout(() => {
                productEl.style.opacity = '1';
                productEl.style.transform = 'translateX(0)';
            }, index * 100);
        });
    }

    createProductElement(product, index) {
        const status = this.getProductStatus(product);
        const statusColor = this.getStatusColor(status);
        
        return `
            <div class="product-item border-start border-${statusColor} border-3 p-3 mb-2 bg-white rounded shadow-sm">
                <div class="row align-items-center">
                    <div class="col-8">
                        <div class="d-flex align-items-center mb-2">
                            <h6 class="mb-0 fw-bold text-dark">${product.name || 'Produit sans nom'}</h6>
                            <span class="badge bg-${statusColor} ms-2 small">${status}</span>
                        </div>
                        <div class="row g-2 small text-muted">
                            <div class="col-6">
                                <i class="bi bi-tag-fill me-1"></i>
                                <strong class="text-primary">${this.formatPrice(product.unit_price || 0)}</strong>
                                <span class="text-muted">/${product.unit || 'unité'}</span>
                            </div>
                            <div class="col-6">
                                <i class="bi bi-box-seam me-1"></i>
                                <strong class="text-success">${product.quantity || 1}</strong>
                                <span class="text-muted">${product.unit || 'unité'}(s)</span>
                            </div>
                        </div>
                        <div class="mt-2">
                            <span class="badge bg-light text-dark">
                                Total: <strong class="text-primary">${this.formatPrice((product.unit_price || 0) * (product.quantity || 1))}</strong>
                            </span>
                            ${product.code ? `<span class="badge bg-secondary ms-1">${product.code}</span>` : ''}
                        </div>
                    </div>
                    <div class="col-4 text-end">
                        <div class="btn-group-vertical gap-1">
                            <button class="btn btn-sm btn-outline-info" onclick="editSingleProduct(${index})" title="Éditer ce produit">
                                <i class="bi bi-pencil-square"></i> Éditer
                            </button>
                            <button class="btn btn-sm btn-outline-secondary" onclick="showProductDetails(${index})" title="Voir détails">
                                <i class="bi bi-eye"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    getProductStatus(product) {
        if (!product.reference_price) return 'Nouveau';
        
        const diff = product.unit_price - product.reference_price;
        if (Math.abs(diff) < 0.01) return 'Identique';
        if (diff < 0) return 'Moins cher';
        return 'Plus cher';
    }

    getStatusColor(status) {
        switch(status) {
            case 'Nouveau': return 'warning';
            case 'Moins cher': return 'success';
            case 'Plus cher': return 'danger';
            default: return 'secondary';
        }
    }

    showProductDetails(productIndex) {
        const product = this.analysisResult.products[productIndex];
        if (!product) return;
        
        // Modal avec détails du produit
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${product.name}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row g-3">
                            <div class="col-6">
                                <label class="form-label">Quantité</label>
                                <div class="fw-bold">${product.quantity || 1}</div>
                            </div>
                            <div class="col-6">
                                <label class="form-label">Prix unitaire</label>
                                <div class="fw-bold">${this.formatPrice(product.unit_price || 0)}</div>
                            </div>
                            ${product.reference_price ? `
                            <div class="col-6">
                                <label class="form-label">Prix de référence</label>
                                <div class="fw-bold">${this.formatPrice(product.reference_price)}</div>
                            </div>
                            <div class="col-6">
                                <label class="form-label">Différence</label>
                                <div class="fw-bold text-${this.getStatusColor(this.getProductStatus(product))}">
                                    ${this.formatPrice(product.unit_price - product.reference_price)}
                                </div>
                            </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
    }

    async saveInvoice() {
        if (!this.analysisResult) {
            this.showNotification('Aucune analyse à sauvegarder', 'error');
            return;
        }

        try {
            // Préparer les données à sauvegarder
            const saveData = {
                ...this.analysisResult,
                manual_edits: this.hasUserModifications(),
                modifications: this.getModificationTypes(),
                scanner_version: '3.0',
                scan_timestamp: new Date().toISOString(),
                device_info: {
                    userAgent: navigator.userAgent,
                    screen: { width: screen.width, height: screen.height }
                }
            };

            this.showProgress('Sauvegarde en cours...');

            const response = await fetch('/api/invoices/save-simple', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(saveData),
                credentials: 'include'
            });

            const result = await response.json();

            if (result.success) {
                this.isSaved = true;
                
                // 🎯 NOTIFICATION INTELLIGENTE POUR NOUVEAUX PRODUITS
                const newProductsInfo = this.getNewProductsInfo();
                if (newProductsInfo.hasNewProducts) {
                    this.showNewProductsNotification(newProductsInfo);
                } else {
                    this.showNotification('✅ Facture sauvegardée avec succès!', 'success');
                }
                
                // Marquer la sauvegarde comme effectuée visuellement
                this.markAsSaved();
                
                // Vibration de succès
                if (navigator.vibrate) {
                    navigator.vibrate([100, 50, 100]);
                }
                
            } else {
                throw new Error(result.error || 'Erreur lors de la sauvegarde');
            }

        } catch (error) {
            console.error('❌ Erreur sauvegarde:', error);
            this.showNotification(`Erreur: ${error.message}`, 'error');
            
            // Vibration d'erreur
            if (navigator.vibrate) {
                navigator.vibrate([200, 100, 200, 100, 200]);
            }
        } finally {
            this.hideProgress();
        }
    }

    getNewProductsInfo() {
        /**
         * 🆕 ANALYSER LES NOUVEAUX PRODUITS DÉTECTÉS
         * Retourne des infos sur les produits qui vont en attente
         */
        if (!this.analysisResult?.products) {
            return { hasNewProducts: false, count: 0, supplier: null };
        }

        // Compter les nouveaux produits (ceux sans prix de référence)
        const newProducts = this.analysisResult.products.filter(product => 
            !product.reference_price || product.is_new === true
        );

        const supplier = this.analysisResult.supplier || 
                        this.analysisResult.invoice_info?.supplier;

        return {
            hasNewProducts: newProducts.length > 0,
            count: newProducts.length,
            supplier: supplier,
            products: newProducts.slice(0, 3), // Premiers 3 pour l'affichage
            totalProducts: this.analysisResult.products.length
        };
    }

    showNewProductsNotification(newProductsInfo) {
        /**
         * 🎯 NOTIFICATION SPÉCIALE POUR NOUVEAUX PRODUITS
         * Informe l'utilisateur et propose d'aller les valider
         */
        const { count, supplier, products } = newProductsInfo;
        
        // Créer une notification riche
        const notificationModal = document.createElement('div');
        notificationModal.className = 'modal fade';
        notificationModal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-success text-white">
                        <h5 class="modal-title">
                            <i class="bi bi-check-circle me-2"></i>Facture Sauvegardée !
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-info">
                            <h6><i class="bi bi-info-circle me-2"></i>Nouveaux produits détectés</h6>
                            <p class="mb-2">
                                <strong>${count} nouveau(x) produit(s)</strong> ont été ajoutés à la liste d'attente pour 
                                <strong>${supplier}</strong> :
                            </p>
                            <ul class="mb-2">
                                ${products.map(product => `
                                    <li>${product.name} - <strong>${product.unit_price}€</strong></li>
                                `).join('')}
                                ${count > 3 ? `<li class="text-muted">... et ${count - 3} autres</li>` : ''}
                            </ul>
                            <small class="text-muted">
                                <i class="bi bi-hourglass-split me-1"></i>
                                Ces produits ne sont <strong>pas encore dans votre catalogue</strong>. 
                                Vous devez les valider pour les ajouter définitivement.
                            </small>
                        </div>
                        
                        <div class="d-grid gap-2">
                            <button class="btn btn-warning" onclick="scanner.goToFournisseurs()">
                                <i class="bi bi-eye me-2"></i>Voir les produits en attente
                            </button>
                            <button class="btn btn-outline-primary" onclick="scanner.continueScanning()">
                                <i class="bi bi-camera me-2"></i>Scanner une autre facture
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(notificationModal);
        const bsModal = new bootstrap.Modal(notificationModal);
        bsModal.show();
        
        // Auto-suppression après fermeture
        notificationModal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(notificationModal);
        });
        
        // Notification toast aussi
        this.showNotification(
            `✅ Facture sauvée ! ${count} nouveau(x) produit(s) en attente pour ${supplier}`, 
            'success'
        );
    }

    goToFournisseurs() {
        /**
         * 🔗 REDIRECTION VERS FOURNISSEURS
         * Ferme le modal et redirige vers la page fournisseurs
         */
        // Fermer le modal
        const modal = document.querySelector('.modal.show');
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            bsModal.hide();
        }
        
        // Rediriger avec un petit délai
        setTimeout(() => {
            window.location.href = '/fournisseurs';
        }, 300);
    }

    continueScanning() {
        /**
         * 🔄 CONTINUER LE SCAN
         * Ferme le modal et reset le scanner pour une nouvelle facture
         */
        // Fermer le modal
        const modal = document.querySelector('.modal.show');
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            bsModal.hide();
        }
        
        // Reset du scanner
        setTimeout(() => {
            this.resetScanner();
            this.showNotification('Prêt pour une nouvelle facture !', 'info');
        }, 300);
    }

    markAsSaved() {
        // Ajouter une indication visuelle que la facture est sauvegardée
        const saveBtn = document.getElementById('saveBtn');
        if (saveBtn) {
            saveBtn.style.backgroundColor = '#28a745';
            saveBtn.innerHTML = '<i class="bi bi-check-lg me-2"></i>Sauvegardé!';
            saveBtn.className = 'btn btn-success';
        }
    }

    hasUserModifications() {
        // Vérifier si l'utilisateur a fait des modifications
        if (this.analysisResult.anomalies && this.analysisResult.anomalies.length > 0) return true;
        if (this.analysisResult.corrected_info) return true;
        if (this.analysisResult.manual_edits) return true;
        return false;
    }
    
    getModificationTypes() {
        const types = [];
        if (this.analysisResult.anomalies && this.analysisResult.anomalies.length > 0) {
            types.push('anomalies');
        }
        if (this.analysisResult.corrected_info) {
            types.push('invoice_info');
        }
        if (this.analysisResult.manual_edits) {
            types.push('products');
        }
        return types;
    }

    editSingleProduct(productIndex) {
        const product = this.analysisResult.products[productIndex];
        if (!product) return;

        // Créer le modal d'édition simple
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'editSingleProductModal';
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-light">
                        <h5 class="modal-title">
                            <i class="bi bi-pencil-square text-primary me-2"></i>
                            Éditer : ${product.name}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row g-3">
                            <!-- Quantité commandée (scannée) -->
                            <div class="col-6">
                                <label class="form-label fw-bold">
                                    <i class="bi bi-scan text-info me-1"></i>
                                    Quantité commandée (scannée)
                                </label>
                                <div class="input-group">
                                    <input type="number" 
                                           class="form-control" 
                                           id="quantiteCommandee" 
                                           value="${product.quantity || 1}" 
                                           min="0" 
                                           step="0.1"
                                           readonly
                                           style="background-color: #f8f9fa;">
                                    <span class="input-group-text">${product.unit || 'unité'}</span>
                                </div>
                                <small class="text-muted">Cette valeur provient du scan</small>
                            </div>

                            <!-- Prix scanné -->
                            <div class="col-6">
                                <label class="form-label fw-bold">
                                    <i class="bi bi-tag text-success me-1"></i>
                                    Prix unitaire scanné
                                </label>
                                <div class="input-group">
                                    <span class="input-group-text">€</span>
                                    <input type="number" 
                                           class="form-control" 
                                           id="prixScanne" 
                                           value="${product.unit_price || 0}" 
                                           min="0" 
                                           step="0.01"
                                           readonly
                                           style="background-color: #f8f9fa;">
                                </div>
                                <small class="text-muted">Prix détecté automatiquement</small>
                            </div>

                            <!-- Quantité reçue -->
                            <div class="col-6">
                                <label class="form-label fw-bold text-warning">
                                    <i class="bi bi-box-seam text-warning me-1"></i>
                                    Quantité réellement reçue
                                </label>
                                <div class="input-group">
                                    <input type="number" 
                                           class="form-control border-warning" 
                                           id="quantiteRecue" 
                                           value="${product.quantity_received || product.quantity || 1}" 
                                           min="0" 
                                           step="0.1"
                                           onchange="checkQuantityDifference()">
                                    <span class="input-group-text">${product.unit || 'unité'}</span>
                                </div>
                                <small class="text-muted">Saisissez ce que vous avez effectivement reçu</small>
                            </div>

                            <!-- Différence (calculée automatiquement) -->
                            <div class="col-6">
                                <label class="form-label fw-bold">
                                    <i class="bi bi-calculator text-info me-1"></i>
                                    Différence
                                </label>
                                <div id="differenceDisplay" class="p-2 border rounded bg-light text-center">
                                    <span class="text-muted">Calculé automatiquement</span>
                                </div>
                            </div>

                            <!-- Zone de commentaire pour anomalie -->
                            <div class="col-12" id="anomalySection" style="display: none;">
                                <div class="alert alert-warning border-warning">
                                    <h6 class="alert-heading">
                                        <i class="bi bi-exclamation-triangle me-1"></i>
                                        Anomalie détectée
                                    </h6>
                                    <label class="form-label fw-bold">Commentaire sur l'anomalie</label>
                                    <textarea class="form-control" 
                                              id="anomalyComment" 
                                              rows="3" 
                                              placeholder="Ex: Produit manquant, carton cassé, périmé, etc.">Une différence de quantité a été détectée.</textarea>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
                        <button type="button" class="btn btn-primary" onclick="saveSingleProductEdit(${productIndex})">
                            <i class="bi bi-check-lg me-1"></i>
                            Sauvegarder
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Ajouter le modal au DOM
        document.body.appendChild(modal);
        
        // Afficher le modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();

        // Calculer la différence initiale
        setTimeout(() => {
            checkQuantityDifference();
        }, 100);

        // Nettoyer quand le modal se ferme
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
    }

    async shareResults() {
        if (!this.analysisResult) return;
        
        const shareData = {
            title: 'Analyse FactureKiller',
            text: `Facture analysée: ${this.analysisResult.products?.length || 0} produits, Total: ${this.formatPrice(this.analysisResult.total_amount || 0)}`,
            url: window.location.href
        };
        
        try {
            if (navigator.share) {
                await navigator.share(shareData);
            } else {
                // Fallback: copier dans le presse-papiers
                await navigator.clipboard.writeText(`${shareData.text}\n${shareData.url}`);
                this.showNotification('Lien copié dans le presse-papiers', 'success');
            }
        } catch (error) {
            console.error('Erreur partage:', error);
        }
    }

    resetScanner() {
        // Arrêter la caméra si active
        this.stopCamera();
        
        // Nettoyer complètement l'état
        this.currentFile = null;
        this.currentImageData = null;
        this.analysisResult = null;
        this.selectedOrderId = null;
        this.isProcessing = false;
        
        // Réinitialiser l'interface
        document.getElementById('uploadZone').style.display = 'block';
        document.getElementById('imagePreview').style.display = 'none';
        document.getElementById('actionButtons').style.display = 'none';
        document.getElementById('scanResults').style.display = 'none';
        
        // Nettoyer l'input file
        const fileInput = document.getElementById('fileInput');
        if (fileInput) {
            fileInput.value = '';
        }
        
        console.log('🔄 Scanner réinitialisé complètement');
    }

    saveToHistory(data) {
        try {
            // Récupérer l'ID du restaurant actuel depuis la session
            const currentRestaurantId = this.getCurrentRestaurantId();
            
            const historyItem = {
                id: Date.now(),
                timestamp: new Date().toISOString(),
                restaurant_id: currentRestaurantId,
                supplier: data.supplier,
                invoice_number: data.invoice_number,
                date: data.date,
                total: data.total_amount,
                products_count: data.products?.length || 0,
                savings: data.price_comparison?.total_savings || 0,
                // LIMITATION: Stocker seulement les informations essentielles des produits
                products: (data.products || []).slice(0, 10).map(p => ({
                    name: p.name,
                    unit_price: p.unit_price,
                    quantity: p.quantity
                })),
                price_comparison: {
                    total_savings: data.price_comparison?.total_savings || 0,
                    items_analyzed: data.price_comparison?.items_analyzed || 0
                },
                // LIMITATION: Ne pas stocker l'image complète, juste un flag
                has_image: !!this.currentImageData,
                invoice_id: data.invoice_id || null,
                // Stocker les anomalies si présentes (données légères)
                has_anomalies: !!(data.anomalies && data.anomalies.length > 0),
                anomalies_count: data.anomalies ? data.anomalies.length : 0
            };
            
            this.scanHistory.unshift(historyItem);
            // Limiter à 50 éléments au lieu de 100
            this.scanHistory = this.scanHistory.slice(0, 50);
            
            // Tenter de sauvegarder avec gestion d'erreur
            try {
                localStorage.setItem('scanHistory', JSON.stringify(this.scanHistory));
                this.updateHistoryBadge();
            } catch (storageError) {
                if (storageError.name === 'QuotaExceededError') {
                    console.warn('🚨 Quota localStorage dépassé, nettoyage de l\'historique...');
                    // Réduire drastiquement l'historique
                    this.scanHistory = this.scanHistory.slice(0, 20);
                    try {
                        localStorage.setItem('scanHistory', JSON.stringify(this.scanHistory));
                        this.updateHistoryBadge();
                        this.showNotification('Historique nettoyé automatiquement (quota dépassé)', 'warning');
                    } catch (secondError) {
                        console.error('❌ Impossible de sauvegarder l\'historique:', secondError);
                        // En dernier recours, vider l'historique
                        this.scanHistory = [];
                        localStorage.removeItem('scanHistory');
                        this.showNotification('Historique vidé (problème de stockage)', 'error');
                    }
                }
            }
        } catch (error) {
            console.error('❌ Erreur sauvegarde historique:', error);
        }
    }

    getCurrentRestaurantId() {
        // Récupérer l'ID du restaurant depuis la session ou les métadonnées
        try {
            const userMeta = document.querySelector('meta[name="user-restaurant"]');
            return userMeta ? userMeta.getAttribute('content') : 'default';
        } catch (error) {
            return 'default';
        }
    }

    updateHistoryBadge() {
        const historyBtn = document.querySelector('[onclick="showHistory()"]');
        if (this.scanHistory.length > 0) {
            historyBtn.innerHTML = `<i class="bi bi-clock-history"></i> <span class="badge bg-primary">${this.scanHistory.length}</span>`;
        }
    }

    showHistory() {
        const modal = new bootstrap.Modal(document.getElementById('historyModal'));
        this.loadHistoryList();
        modal.show();
    }

    loadHistoryList() {
        const historyList = document.getElementById('historyList');
        const currentRestaurantId = this.getCurrentRestaurantId();
        
        // Filtrer par restaurant
        const restaurantHistory = this.scanHistory.filter(item => 
            item.restaurant_id === currentRestaurantId || !item.restaurant_id
        );
        
        if (restaurantHistory.length === 0) {
            historyList.innerHTML = `
                <div class="text-center text-muted p-4">
                    <i class="bi bi-clock-history fs-1 mb-3"></i>
                    <h6>Aucun scan dans l'historique</h6>
                    <p>Scannez votre première facture pour commencer !</p>
                </div>
            `;
            return;
        }
        
        // Grouper par fournisseur
        const groupedHistory = this.groupHistoryBySupplier(restaurantHistory);
        
        historyList.innerHTML = `
            <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">
                        <i class="bi bi-building me-2"></i>Restaurant actuel
                    </h6>
                    <span class="badge bg-success">${restaurantHistory.length} scans</span>
                </div>
                <hr>
            </div>
            ${Object.entries(groupedHistory).map(([supplier, items]) => `
                <div class="supplier-group mb-4">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <h6 class="text-primary mb-0">
                            <i class="bi bi-shop me-2"></i>${supplier}
                        </h6>
                        <span class="badge bg-primary">${items.length} facture${items.length > 1 ? 's' : ''}</span>
                    </div>
                    ${items.map((item, globalIndex) => {
                        const realIndex = this.scanHistory.findIndex(h => h.id === item.id);
                        return `
                            <div class="card mb-2 history-item" style="cursor: pointer;" onclick="scanner.viewHistoryItem(${realIndex})">
                                <div class="card-body p-3">
                                    <div class="d-flex justify-content-between align-items-start">
                                        <div class="flex-grow-1">
                                            <div class="d-flex justify-content-between align-items-start mb-2">
                                                <h6 class="mb-1">${item.invoice_number || `Facture #${item.id.toString().slice(-6)}`}</h6>
                                                <span class="badge bg-light text-dark">${this.formatDate(item.timestamp)}</span>
                                            </div>
                                            <div class="row g-2 mb-2">
                                                <div class="col-6">
                                                    <small class="text-muted">Total:</small>
                                                    <div class="fw-bold">${this.formatPrice(item.total || 0)}</div>
                                                </div>
                                                <div class="col-6">
                                                    <small class="text-muted">Produits:</small>
                                                    <div class="fw-bold">${item.products_count} articles</div>
                                                </div>
                                            </div>
                                            ${item.savings > 0 ? `
                                                <div class="mb-2">
                                                    <span class="badge bg-success">
                                                        <i class="bi bi-piggy-bank me-1"></i>Économie: ${this.formatPrice(item.savings)}
                                                    </span>
                                                </div>
                                            ` : ''}
                                            <div class="d-flex gap-1">
                                                <span class="badge bg-primary">
                                                    <i class="bi bi-eye me-1"></i>Voir détails
                                                </span>
                                                ${item.products_count > 5 ? `
                                                    <span class="badge bg-info">
                                                        <i class="bi bi-list me-1"></i>${item.products_count} produits
                                                    </span>
                                                ` : ''}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            `).join('')}
        `;
    }

    groupHistoryBySupplier(history) {
        return history.reduce((groups, item) => {
            const supplier = item.supplier || 'Fournisseur inconnu';
            if (!groups[supplier]) {
                groups[supplier] = [];
            }
            groups[supplier].push(item);
            return groups;
        }, {});
    }

    viewHistoryItem(index) {
        const item = this.scanHistory[index];
        if (!item) return;

        // Créer et afficher le modal de détails
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-receipt me-2"></i>${item.supplier || 'Fournisseur inconnu'}
                            ${item.invoice_number ? ` - ${item.invoice_number}` : ''}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body" style="max-height: 80vh; overflow-y: auto;">
                        <!-- Informations générales -->
                        <div class="row mb-4">
                            <div class="col-md-6">
                                <div class="card border-primary">
                                    <div class="card-header bg-primary text-white">
                                        <h6 class="mb-0"><i class="bi bi-info-circle me-2"></i>Informations générales</h6>
                                    </div>
                                    <div class="card-body">
                                        <table class="table table-sm mb-0">
                                            <tr>
                                                <td class="text-muted">Fournisseur:</td>
                                                <td class="fw-bold">${item.supplier || 'Inconnu'}</td>
                                            </tr>
                                            <tr>
                                                <td class="text-muted">N° Facture:</td>
                                                <td>${item.invoice_number || 'N/A'}</td>
                                            </tr>
                                            <tr>
                                                <td class="text-muted">Date scan:</td>
                                                <td>${this.formatDate(item.timestamp)}</td>
                                            </tr>
                                            <tr>
                                                <td class="text-muted">Date facture:</td>
                                                <td>${item.date || 'N/A'}</td>
                                            </tr>
                                            <tr>
                                                <td class="text-muted">Total:</td>
                                                <td class="fw-bold text-success">${this.formatPrice(item.total || 0)}</td>
                                            </tr>
                                        </table>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="card border-success">
                                    <div class="card-header bg-success text-white">
                                        <h6 class="mb-0"><i class="bi bi-graph-up me-2"></i>Analyse des prix</h6>
                                    </div>
                                    <div class="card-body">
                                        <div class="row g-3">
                                            <div class="col-6">
                                                <div class="text-center p-2 bg-primary bg-opacity-10 rounded">
                                                    <div class="fs-5 fw-bold text-primary">${item.products_count || 0}</div>
                                                    <small class="text-muted">Produits</small>
                                                </div>
                                            </div>
                                            <div class="col-6">
                                                <div class="text-center p-2 bg-success bg-opacity-10 rounded">
                                                    <div class="fs-5 fw-bold text-success">${this.formatPrice(item.savings || 0)}</div>
                                                    <small class="text-muted">Économies</small>
                                                </div>
                                            </div>
                                            ${item.price_comparison?.new_products ? `
                                            <div class="col-6">
                                                <div class="text-center p-2 bg-warning bg-opacity-10 rounded">
                                                    <div class="fs-6 fw-bold text-warning">${item.price_comparison.new_products}</div>
                                                    <small class="text-muted">Nouveaux</small>
                                                </div>
                                            </div>
                                            ` : ''}
                                            ${item.price_comparison?.price_alerts ? `
                                            <div class="col-6">
                                                <div class="text-center p-2 bg-danger bg-opacity-10 rounded">
                                                    <div class="fs-6 fw-bold text-danger">${item.price_comparison.price_alerts}</div>
                                                    <small class="text-muted">Alertes prix</small>
                                                </div>
                                            </div>
                                            ` : ''}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Produits détaillés -->
                        <div class="card border-info mb-4">
                            <div class="card-header bg-info text-white d-flex justify-content-between align-items-center">
                                <h6 class="mb-0"><i class="bi bi-list me-2"></i>Produits scannés (${(item.products || []).length})</h6>
                                <button class="btn btn-sm btn-outline-light" onclick="scanner.toggleProductsView(this)">
                                    <i class="bi bi-arrows-expand me-1"></i>Développer
                                </button>
                            </div>
                            <div class="card-body p-0">
                                <div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
                                    <table class="table table-striped table-hover mb-0">
                                        <thead class="table-dark sticky-top">
                                            <tr>
                                                <th width="40%">Produit</th>
                                                <th width="15%">Quantité</th>
                                                <th width="15%">Prix unitaire</th>
                                                <th width="15%">Total</th>
                                                <th width="15%">Statut</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${(item.products || []).length > 0 ? 
                                                (item.products || []).map((product, idx) => `
                                                    <tr ${product.is_new ? 'class="table-warning"' : ''}>
                                                        <td>
                                                            <div class="fw-bold">${product.name || `Produit ${idx + 1}`}</div>
                                                            ${product.category ? `<small class="text-muted">${product.category}</small>` : ''}
                                                        </td>
                                                        <td>
                                                            <span class="badge bg-secondary">${product.quantity || 0} ${product.unit || ''}</span>
                                                        </td>
                                                        <td class="fw-bold">${this.formatPrice(product.unit_price || 0)}</td>
                                                        <td class="fw-bold text-success">${this.formatPrice((product.quantity || 0) * (product.unit_price || 0))}</td>
                                                        <td>
                                                            ${this.getAdvancedProductStatusBadge(product)}
                                                        </td>
                                                    </tr>
                                                `).join('') 
                                                : `
                                                    <tr>
                                                        <td colspan="5" class="text-center text-muted p-4">
                                                            <i class="bi bi-inbox fs-3 mb-2"></i>
                                                            <br>Aucun produit détaillé disponible
                                                        </td>
                                                    </tr>
                                                `
                                            }
                                        </tbody>
                                    </table>
                                </div>
                                ${(item.products || []).length > 10 ? `
                                <div class="card-footer text-center">
                                    <small class="text-muted">
                                        <i class="bi bi-arrow-down me-1"></i>
                                        Faites défiler pour voir tous les ${(item.products || []).length} produits
                                    </small>
                                </div>
                                ` : ''}
                            </div>
                        </div>

                        <!-- Image de la facture -->
                        ${item.image_data ? `
                        <div class="card border-warning">
                            <div class="card-header bg-warning text-dark">
                                <h6 class="mb-0"><i class="bi bi-image me-2"></i>Image de la facture</h6>
                            </div>
                            <div class="card-body text-center">
                                <img src="${item.image_data}" 
                                     class="img-fluid rounded shadow" 
                                     alt="Facture scannée" 
                                     style="max-height: 400px; cursor: pointer;"
                                     onclick="scanner.showFullImage('${item.image_data}')">
                                <div class="mt-2">
                                    <small class="text-muted">
                                        <i class="bi bi-zoom-in me-1"></i>Cliquez pour agrandir
                                    </small>
                                </div>
                            </div>
                        </div>
                        ` : `
                        <div class="card border-secondary">
                            <div class="card-body text-center text-muted p-4">
                                <i class="bi bi-image fs-1 mb-3"></i>
                                <h6>Image non disponible</h6>
                                <p>L'image de cette facture n'a pas été sauvegardée</p>
                            </div>
                        </div>
                        `}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            <i class="bi bi-x-circle me-2"></i>Fermer
                        </button>
                        ${item.image_data ? `
                        <button type="button" class="btn btn-primary" onclick="scanner.rescanFromHistory(${index})">
                            <i class="bi bi-arrow-repeat me-2"></i>Rescanner
                        </button>
                        ` : ''}
                        ${item.invoice_id ? `
                        <button type="button" class="btn btn-success" onclick="window.open('/factures#invoice-${item.invoice_id}', '_blank')">
                            <i class="bi bi-eye me-2"></i>Voir dans les factures
                        </button>
                        ` : ''}
                        <button type="button" class="btn btn-info" onclick="scanner.exportHistoryItem(${index})">
                            <i class="bi bi-download me-2"></i>Exporter
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
    }

    getAdvancedProductStatusBadge(product) {
        if (product.is_new) {
            return '<span class="badge bg-warning"><i class="bi bi-star me-1"></i>Nouveau</span>';
        } else if (product.price_difference && Math.abs(product.price_difference) > 0.1) {
            const diffClass = product.price_difference > 0 ? 'bg-danger' : 'bg-success';
            const icon = product.price_difference > 0 ? 'bi-arrow-up' : 'bi-arrow-down';
            return `<span class="badge ${diffClass}"><i class="bi ${icon} me-1"></i>Écart prix</span>`;
        } else if (product.unit_price && product.unit_price > 0) {
            return '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>OK</span>';
        } else {
            return '<span class="badge bg-secondary"><i class="bi bi-question-circle me-1"></i>N/A</span>';
        }
    }

    toggleProductsView(button) {
        const tableContainer = button.closest('.card').querySelector('.table-responsive');
        const icon = button.querySelector('i');
        
        if (tableContainer.style.maxHeight === '400px') {
            tableContainer.style.maxHeight = 'none';
            icon.className = 'bi bi-arrows-collapse me-1';
            button.innerHTML = '<i class="bi bi-arrows-collapse me-1"></i>Réduire';
        } else {
            tableContainer.style.maxHeight = '400px';
            icon.className = 'bi bi-arrows-expand me-1';
            button.innerHTML = '<i class="bi bi-arrows-expand me-1"></i>Développer';
        }
    }

    showFullImage(imageData) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-fullscreen">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-image me-2"></i>Facture - Vue complète
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body p-0 bg-dark d-flex align-items-center justify-content-center">
                        <img src="${imageData}" class="img-fluid" alt="Facture" style="max-height: 90vh;">
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
    }

    exportHistoryItem(index) {
        const item = this.scanHistory[index];
        if (!item) return;
        
        const exportData = {
            facture: {
                fournisseur: item.supplier,
                numero: item.invoice_number,
                date_scan: item.timestamp,
                date_facture: item.date,
                total: item.total
            },
            produits: item.products || [],
            analyse_prix: item.price_comparison || {},
            economies: item.savings
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `facture-${item.supplier || 'scan'}-${new Date(item.timestamp).toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showNotification('Facture exportée avec succès !', 'success');
    }

    showSettings() {
        // Modal des paramètres
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-gear me-2"></i>Paramètres Scanner
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="form-check form-switch mb-3">
                            <input class="form-check-input" type="checkbox" id="autoAnalyze" ${this.isAutoAnalyzeEnabled() ? 'checked' : ''}>
                            <label class="form-check-label" for="autoAnalyze">
                                Analyse automatique
                            </label>
                        </div>
                        <div class="form-check form-switch mb-3">
                            <input class="form-check-input" type="checkbox" id="hapticFeedback" ${this.isHapticEnabled() ? 'checked' : ''}>
                            <label class="form-check-label" for="hapticFeedback">
                                Vibrations
                            </label>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Qualité d'image</label>
                            <select class="form-select" id="imageQuality">
                                <option value="0.6">Économique</option>
                                <option value="0.8" selected>Standard</option>
                                <option value="0.95">Haute qualité</option>
                            </select>
                        </div>
                        <div class="d-grid gap-2">
                            <button class="btn btn-danger" onclick="scanner.clearHistory()">
                                <i class="bi bi-trash me-2"></i>Vider l'historique
                            </button>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
                        <button type="button" class="btn btn-primary" id="saveSettingsBtn">
                            <i class="bi bi-check-lg me-2"></i>Confirmer
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        // Gestion des paramètres avec confirmation
        const saveBtn = modal.querySelector('#saveSettingsBtn');
        saveBtn.addEventListener('click', () => {
            // Sauvegarder tous les paramètres
            const autoAnalyze = modal.querySelector('#autoAnalyze').checked;
            const hapticFeedback = modal.querySelector('#hapticFeedback').checked;
            const imageQuality = modal.querySelector('#imageQuality').value;
            
            localStorage.setItem('autoAnalyze', autoAnalyze);
            localStorage.setItem('hapticFeedback', hapticFeedback);
            localStorage.setItem('imageQuality', imageQuality);
            
            // Notifier l'utilisateur
            this.showNotification('Paramètres sauvegardés !', 'success');
            
            // Fermer le modal
            bsModal.hide();
        });
        
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
    }

    isAutoAnalyzeEnabled() {
        // Vérifier le paramètre d'analyse automatique
        const autoAnalysisCheckbox = document.getElementById('autoAnalysis');
        if (autoAnalysisCheckbox) {
            return autoAnalysisCheckbox.checked;
        }
        
        // Fallback sur localStorage
        const stored = localStorage.getItem('autoAnalyze');
        return stored === 'true' || stored === null; // Par défaut activé
    }

    isHapticEnabled() {
        return localStorage.getItem('hapticFeedback') !== 'false';
    }

    clearHistory() {
        this.scanHistory = [];
        localStorage.removeItem('scanHistory');
        this.updateHistoryBadge();
        this.showNotification('Historique vidé', 'success');
    }

    // Méthodes utilitaires
    showProgress(text = 'Traitement en cours...') {
        // Afficher le status de traitement fixé en bas
        const processingStatus = document.getElementById('processingStatus');
        const processingTitle = document.getElementById('processingTitle');
        const processingDetails = document.getElementById('processingDetails');
        
        if (processingStatus) {
            processingStatus.style.display = 'block';
            processingTitle.textContent = '🤖 Analyse en cours...';
            processingDetails.textContent = text;
        }
        
        // Cacher les actions du bas pendant le traitement
        const finalActions = document.querySelector('.final-actions');
        if (finalActions) {
            finalActions.style.display = 'none';
        }
    }

    hideProgress() {
        // Cacher le status de traitement
        const processingStatus = document.getElementById('processingStatus');
        if (processingStatus) {
            processingStatus.style.display = 'none';
        }
        
        // Remettre les actions du bas
        const finalActions = document.querySelector('.final-actions');
        if (finalActions) {
            finalActions.style.display = 'block';
        }
    }

    updateProgress(percent, text) {
        const processingProgress = document.getElementById('processingProgress');
        const processingDetails = document.getElementById('processingDetails');
        
        if (processingProgress) {
            processingProgress.style.width = percent + '%';
        }
        
        if (processingDetails) {
            processingDetails.textContent = text;
        }
    }

    showNotification(message, type = 'info') {
        // Créer une notification toast
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'primary'} border-0`;
        toast.setAttribute('role', 'alert');
        toast.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999;';
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi bi-${type === 'error' ? 'exclamation-triangle' : type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', () => {
            document.body.removeChild(toast);
        });
    }

    formatPrice(price) {
        return new Intl.NumberFormat('fr-FR', {
            style: 'currency',
            currency: 'EUR'
        }).format(price);
    }

    formatDate(dateString) {
        if (!dateString) return '';
        try {
            const date = new Date(dateString);
            // Vérifier si la date est valide
            if (isNaN(date.getTime())) {
                return dateString; // Retourner la chaîne originale si invalide
            }
            return new Intl.DateTimeFormat('fr-FR', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
            }).format(date);
        } catch (error) {
            console.warn('Erreur formatage date:', error);
            return dateString; // Retourner la chaîne originale en cas d'erreur
        }
    }

    async loadOrders() {
        // Méthode pour charger les commandes (compatible avec l'ancien système)
        try {
            const response = await fetch('/api/orders', {
                credentials: 'include'
            });
            const data = await response.json();
            // Traitement des commandes si nécessaire
        } catch (error) {
            console.error('Erreur chargement commandes:', error);
        }
    }

    fixModalAccessibility() {
        // Corriger les problèmes d'accessibilité des modals Bootstrap
        document.addEventListener('shown.bs.modal', (e) => {
            const modal = e.target;
            modal.removeAttribute('aria-hidden');
        });
        
        document.addEventListener('hidden.bs.modal', (e) => {
            const modal = e.target;
            modal.setAttribute('aria-hidden', 'true');
        });
    }

    rescanFromHistory(index) {
        const item = this.scanHistory[index];
        if (!item || !item.image_data) {
            this.showNotification('Image non disponible pour ce scan', 'error');
            return;
        }

        // Fermer le modal
        const modal = document.querySelector('.modal.show');
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            bsModal.hide();
        }

        // Convertir l'image base64 en file et relancer l'analyse
        this.dataURItoFile(item.image_data, 'facture-rescan.jpg')
            .then(file => {
                this.handleFileSelect(file);
                this.showNotification('Facture rechargée, vous pouvez la reanalyser', 'success');
            })
            .catch(error => {
                this.showNotification('Erreur lors du rechargement de la facture', 'error');
                console.error('Erreur rescan:', error);
            });
    }

    dataURItoFile(dataURI, fileName) {
        return new Promise((resolve, reject) => {
            try {
                const arr = dataURI.split(',');
                const mime = arr[0].match(/:(.*?);/)[1];
                const bstr = atob(arr[1]);
                let n = bstr.length;
                const u8arr = new Uint8Array(n);
                
                while (n--) {
                    u8arr[n] = bstr.charCodeAt(n);
                }
                
                const file = new File([u8arr], fileName, { type: mime });
                resolve(file);
            } catch (error) {
                reject(error);
            }
        });
    }

    setupRestaurantChangeListener() {
        // Écouter les appels de switch de restaurant
        const originalSwitchToRestaurant = window.switchToRestaurant;
        const originalSwitchRestaurant = window.switchRestaurant;
        
        // Override pour Master Admin
        if (originalSwitchToRestaurant) {
            window.switchToRestaurant = async (restaurantId) => {
                console.log('🏪 Scanner: Détection changement restaurant Master Admin');
                this.clearOrdersCache();
                this.selectedOrderId = null; // Reset commande sélectionnée
                await originalSwitchToRestaurant(restaurantId);
            };
        }
        
        // Override pour Client
        if (originalSwitchRestaurant) {
            window.switchRestaurant = async (restaurantId) => {
                console.log('🏪 Scanner: Détection changement restaurant Client');
                this.clearOrdersCache();
                this.selectedOrderId = null; // Reset commande sélectionnée
                await originalSwitchRestaurant(restaurantId);
            };
        }
        
        // Écouter les événements personnalisés (si utilisés)
        document.addEventListener('restaurantChanged', () => {
            console.log('🏪 Scanner: Restaurant changé via événement');
            this.clearOrdersCache();
            this.selectedOrderId = null;
        });
    }
    
    clearOrdersCache() {
        console.log('🧹 Scanner: Nettoyage cache commandes');
        // Forcer le rechargement des commandes au prochain appel
        this.ordersCache = null;
        this.lastOrdersLoad = null;
    }

    // === NOUVELLES FONCTIONS D'ÉDITION ===
    
    async showEditModal() {
        const modalElement = document.getElementById('editScanModal');
        if (!modalElement) {
            console.warn('Modal editScanModal not found');
            this.showNotification('Fonction d\'édition non disponible', 'warning');
            return;
        }
        
        if (typeof bootstrap === 'undefined') {
            console.error('Bootstrap not loaded');
            this.showNotification('Erreur: Bootstrap non chargé', 'error');
            return;
        }
        
        const modal = new bootstrap.Modal(modalElement);
        
        // Charger les fournisseurs existants
        await this.loadSuppliersForEdit();
        
        // Pré-remplir avec les données actuelles
        this.fillEditForm();
        
        modal.show();
    }
    
    async loadSuppliersForEdit() {
        try {
            const response = await fetch('/api/suppliers', {
                credentials: 'include'
            });
            const data = await response.json();
            
            const select = document.getElementById('editSupplier');
            select.innerHTML = '<option value="">Choisir un fournisseur...</option>';
            
            if (data.success && data.data) {
                data.data.forEach(supplier => {
                    const option = document.createElement('option');
                    option.value = supplier.name;
                    option.textContent = supplier.name;
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Erreur chargement fournisseurs:', error);
        }
    }
    
    fillEditForm() {
        if (!this.analysisResult) return;
        
        const invoiceInfo = this.analysisResult.invoice_info || {};
        
        // Pré-remplir les champs avec les données actuelles
        document.getElementById('editSupplier').value = invoiceInfo.supplier || '';
        document.getElementById('editInvoiceNumber').value = invoiceInfo.invoice_number || '';
        document.getElementById('editInvoiceDate').value = this.formatDateForInput(invoiceInfo.invoice_date);
        document.getElementById('editVatAmount').value = invoiceInfo.vat_amount || '';
        document.getElementById('editTotalAmount').value = invoiceInfo.total_amount || '';
        document.getElementById('editNote').value = '';
    }
    
    formatDateForInput(dateString) {
        if (!dateString) return '';
        try {
            const date = new Date(dateString);
            if (isNaN(date.getTime())) return '';
            return date.toISOString().split('T')[0];
        } catch (error) {
            return '';
        }
    }
    
    toggleCustomSupplier() {
        const select = document.getElementById('editSupplier');
        const customInput = document.getElementById('customSupplier');
        const button = document.querySelector('button[onclick="toggleCustomSupplier()"]');
        
        if (customInput.classList.contains('d-none')) {
            // Afficher le champ personnalisé
            customInput.classList.remove('d-none');
            select.classList.add('d-none');
            button.innerHTML = '<i class="bi bi-list"></i>';
            customInput.focus();
        } else {
            // Afficher la liste
            customInput.classList.add('d-none');
            select.classList.remove('d-none');
            button.innerHTML = '<i class="bi bi-plus"></i>';
            customInput.value = '';
        }
    }
    
    async applyScanCorrections() {
        try {
            // Récupérer les valeurs du formulaire
            const editData = this.getEditFormData();
            
            // Valider les données
            if (!editData.supplier) {
                this.showNotification('Le fournisseur est requis', 'error');
                return;
            }
            
            // Appliquer les corrections à l'analysisResult
            this.applyCorrectionsToResult(editData);
            
            // Actualiser l'affichage
            this.updateDisplayWithCorrections(editData);
            
            // Fermer le modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('editScanModal'));
            modal.hide();
            
            this.showNotification('Corrections appliquées avec succès!', 'success');
            
        } catch (error) {
            console.error('Erreur application corrections:', error);
            this.showNotification('Erreur lors de l\'application des corrections', 'error');
        }
    }
    
    getEditFormData() {
        const customSupplier = document.getElementById('customSupplier');
        const isCustomVisible = !customSupplier.classList.contains('d-none');
        
        return {
            supplier: isCustomVisible ? 
                customSupplier.value.trim() : 
                document.getElementById('editSupplier').value,
            invoice_number: document.getElementById('editInvoiceNumber').value.trim(),
            invoice_date: document.getElementById('editInvoiceDate').value,
            vat_amount: parseFloat(document.getElementById('editVatAmount').value) || 0,
            total_amount: parseFloat(document.getElementById('editTotalAmount').value) || 0,
            note: document.getElementById('editNote').value.trim()
        };
    }
    
    applyCorrectionsToResult(editData) {
        if (!this.analysisResult) return;
        
        // Mettre à jour les informations de facture
        if (!this.analysisResult.invoice_info) {
            this.analysisResult.invoice_info = {};
        }
        
        this.analysisResult.invoice_info.supplier = editData.supplier;
        this.analysisResult.invoice_info.invoice_number = editData.invoice_number;
        this.analysisResult.invoice_info.invoice_date = editData.invoice_date;
        this.analysisResult.invoice_info.vat_amount = editData.vat_amount;
        this.analysisResult.invoice_info.total_amount = editData.total_amount;
        
        // Mettre à jour le fournisseur de tous les produits
        if (this.analysisResult.products) {
            this.analysisResult.products.forEach(product => {
                product.supplier = editData.supplier;
            });
        }
        
        // Ajouter une note sur les corrections
        this.analysisResult.corrections_applied = {
            timestamp: new Date().toISOString(),
            note: editData.note,
            user_corrected: true
        };
    }
    
    updateDisplayWithCorrections(editData) {
        // Mettre à jour l'affichage des informations de facture
        document.getElementById('supplierName').textContent = editData.supplier;
        document.getElementById('invoiceNumber').textContent = editData.invoice_number || '-';
        document.getElementById('invoiceDate').textContent = this.formatDate(editData.invoice_date) || '-';
        document.getElementById('vatAmount').textContent = editData.vat_amount ? `${editData.vat_amount}€` : '-';
        
        // Mettre à jour le total si fourni
        if (editData.total_amount) {
            document.getElementById('totalAmount').textContent = `${editData.total_amount}€`;
        }
        
        // Ajouter une indication visuelle que des corrections ont été appliquées
        const invoiceCard = document.querySelector('.invoice-info .card');
        if (invoiceCard && !invoiceCard.querySelector('.correction-badge')) {
            const badge = document.createElement('div');
            badge.className = 'correction-badge position-absolute top-0 end-0 m-2';
            badge.innerHTML = '<small class="badge bg-warning text-dark"><i class="bi bi-pencil-square me-1"></i>Corrigé</small>';
            invoiceCard.style.position = 'relative';
            invoiceCard.appendChild(badge);
        }
        
        // Actualiser la liste des produits pour refléter le nouveau fournisseur
        if (this.analysisResult.products) {
            this.fillProductsList(this.analysisResult);
        }
    }

    // === NOUVELLES FONCTIONS POUR PRODUITS ET ANOMALIES ===
    
    async showEditProductsModal() {
        const modalElement = document.getElementById('editProductsModal');
        if (!modalElement) {
            console.warn('Modal editProductsModal not found');
            this.showNotification('Fonction d\'édition des produits non disponible', 'warning');
            return;
        }
        
        if (typeof bootstrap === 'undefined') {
            console.error('Bootstrap not loaded');
            this.showNotification('Erreur: Bootstrap non chargé', 'error');
            return;
        }
        
        const modal = new bootstrap.Modal(modalElement);
        
        // Remplir la liste des produits éditables
        this.fillEditableProductsList();
        
        // Remplir la liste des produits pour les anomalies
        this.fillAnomalyProductsList();
        
        // Setup des événements pour le type d'anomalie
        this.setupAnomalyTypeListener();
        
        modal.show();
    }
    
    fillEditableProductsList() {
        const container = document.getElementById('editableProductsList');
        const countElement = document.getElementById('productsCount');
        
        if (!container) {
            console.warn('Element editableProductsList not found');
            return;
        }
        
        if (!this.analysisResult || !this.analysisResult.products) {
            container.innerHTML = '<div class="text-muted text-center p-3">Aucun produit détecté</div>';
            if (countElement) {
                countElement.textContent = '0 produits';
            }
            return;
        }
        
        const products = this.analysisResult.products;
        if (countElement) {
            countElement.textContent = `${products.length} produits`;
        }
        
        container.innerHTML = '';
        
        products.forEach((product, index) => {
            const productCard = document.createElement('div');
            productCard.className = 'card mb-2';
            productCard.innerHTML = `
                <div class="card-body p-3">
                    <div class="row g-2">
                        <div class="col-12">
                            <label class="form-label fw-bold small">Nom du produit</label>
                            <input type="text" class="form-control form-control-sm" value="${product.name || ''}" 
                                   onchange="updateProductField(${index}, 'name', this.value)">
                        </div>
                        <div class="col-6">
                            <label class="form-label fw-bold small">Prix unitaire (€)</label>
                            <input type="number" step="0.01" class="form-control form-control-sm" value="${product.unit_price || 0}" 
                                   onchange="updateProductField(${index}, 'unit_price', parseFloat(this.value))">
                        </div>
                        <div class="col-6">
                            <label class="form-label fw-bold small">Quantité</label>
                            <input type="number" step="0.01" class="form-control form-control-sm" value="${product.quantity || 1}" 
                                   onchange="updateProductField(${index}, 'quantity', parseFloat(this.value))">
                        </div>
                        <div class="col-6">
                            <label class="form-label fw-bold small">Unité</label>
                            <select class="form-select form-select-sm" onchange="updateProductField(${index}, 'unit', this.value)">
                                <option value="pièce" ${product.unit === 'pièce' ? 'selected' : ''}>pièce</option>
                                <option value="kg" ${product.unit === 'kg' ? 'selected' : ''}>kg</option>
                                <option value="litre" ${product.unit === 'litre' ? 'selected' : ''}>litre</option>
                                <option value="boîte" ${product.unit === 'boîte' ? 'selected' : ''}>boîte</option>
                                <option value="carton" ${product.unit === 'carton' ? 'selected' : ''}>carton</option>
                                <option value="sac" ${product.unit === 'sac' ? 'selected' : ''}>sac</option>
                            </select>
                        </div>
                        <div class="col-6">
                            <label class="form-label fw-bold small">Code produit</label>
                            <input type="text" class="form-control form-control-sm" value="${product.code || ''}" 
                                   onchange="updateProductField(${index}, 'code', this.value)">
                        </div>
                    </div>
                    <div class="mt-2 text-end">
                        <small class="text-muted">Total: ${this.formatPrice((product.unit_price || 0) * (product.quantity || 1))}</small>
                    </div>
                </div>
            `;
            container.appendChild(productCard);
        });
    }
    
    updateProductField(productIndex, field, value) {
        if (!this.analysisResult || !this.analysisResult.products[productIndex]) return;
        
        this.analysisResult.products[productIndex][field] = value;
        
        // Recalculer les totaux si nécessaire
        if (field === 'unit_price' || field === 'quantity') {
            this.updateProductTotal(productIndex);
        }
        
        console.log(`Produit ${productIndex} mis à jour:`, field, '=', value);
    }
    
    updateProductTotal(productIndex) {
        const product = this.analysisResult.products[productIndex];
        const total = (product.unit_price || 0) * (product.quantity || 1);
        
        // Mettre à jour l'affichage du total dans la carte
        const cards = document.querySelectorAll('#editableProductsList .card');
        if (cards[productIndex]) {
            const totalElement = cards[productIndex].querySelector('.text-muted');
            if (totalElement) {
                totalElement.textContent = `Total: ${this.formatPrice(total)}`;
            }
        }
    }
    
    fillAnomalyProductsList() {
        const select = document.getElementById('affectedProduct');
        select.innerHTML = '<option value="">Sélectionner un produit...</option>';
        
        if (!this.analysisResult || !this.analysisResult.products) return;
        
        this.analysisResult.products.forEach((product, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.textContent = `${product.name || 'Produit ' + (index + 1)} (Qté: ${product.quantity || 1} ${product.unit || 'pièce'} - ${this.formatPrice(product.unit_price || 0)})`;
            select.appendChild(option);
        });
        
        // NOUVEAU: Écouter les changements de sélection pour pré-remplir la quantité
        select.addEventListener('change', (e) => {
            const productIndex = parseInt(e.target.value);
            if (!isNaN(productIndex) && this.analysisResult.products[productIndex]) {
                const selectedProduct = this.analysisResult.products[productIndex];
                
                // Pré-remplir automatiquement la quantité commandée
                const orderedQuantityInput = document.getElementById('orderedQuantity');
                if (orderedQuantityInput) {
                    orderedQuantityInput.value = selectedProduct.quantity || 1;
                }
                
                // Mettre le focus sur le champ "Quantité reçue"
                const receivedQuantityInput = document.getElementById('receivedQuantity');
                if (receivedQuantityInput) {
                    receivedQuantityInput.focus();
                    receivedQuantityInput.placeholder = `Entrez la quantité reçue (commandé: ${selectedProduct.quantity || 1})`;
                    
                    // Écouter les changements pour calculer l'écart
                    receivedQuantityInput.addEventListener('input', () => {
                        this.calculateQuantityDifference();
                    });
                }
                
                console.log(`🎯 Produit sélectionné: ${selectedProduct.name}, Qté commandée: ${selectedProduct.quantity || 1}`);
            }
        });
    }
    
    calculateQuantityDifference() {
        const orderedQuantity = parseInt(document.getElementById('orderedQuantity').value) || 0;
        const receivedQuantity = parseInt(document.getElementById('receivedQuantity').value) || 0;
        const differenceDiv = document.getElementById('quantityDifference');
        const differenceText = document.getElementById('differenceText');
        
        if (orderedQuantity > 0 && receivedQuantity >= 0) {
            const difference = orderedQuantity - receivedQuantity;
            
            if (difference !== 0) {
                differenceDiv.style.display = 'block';
                
                if (difference > 0) {
                    // Manquant
                    differenceText.innerHTML = `
                        <i class="bi bi-exclamation-triangle text-warning me-1"></i>
                        <strong>Il manque ${difference} ${difference > 1 ? 'unités' : 'unité'}</strong>
                        (Commandé: ${orderedQuantity}, Reçu: ${receivedQuantity})
                    `;
                    differenceDiv.className = 'col-12';
                    differenceDiv.querySelector('.alert').className = 'alert alert-warning mb-0';
                } else {
                    // Surplus
                    differenceText.innerHTML = `
                        <i class="bi bi-plus-circle text-info me-1"></i>
                        <strong>Surplus de ${Math.abs(difference)} ${Math.abs(difference) > 1 ? 'unités' : 'unité'}</strong>
                        (Commandé: ${orderedQuantity}, Reçu: ${receivedQuantity})
                    `;
                    differenceDiv.className = 'col-12';
                    differenceDiv.querySelector('.alert').className = 'alert alert-info mb-0';
                }
            } else {
                // Quantités identiques
                differenceDiv.style.display = 'none';
            }
        } else {
            differenceDiv.style.display = 'none';
        }
    }
    
    setupAnomalyTypeListener() {
        const typeSelect = document.getElementById('anomalyType');
        const quantityCard = document.getElementById('quantityAnomalyCard');
        
        typeSelect.addEventListener('change', (e) => {
            if (e.target.value === 'quantity') {
                quantityCard.style.display = 'block';
            } else {
                quantityCard.style.display = 'none';
            }
        });
    }
    
    addAnomaly() {
        const type = document.getElementById('anomalyType').value;
        let description = document.getElementById('anomalyDescription').value.trim();
        const severity = document.querySelector('input[name="severity"]:checked')?.value || 'medium';
        
        if (!type) {
            this.showNotification('Veuillez sélectionner un type d\'anomalie', 'error');
            return;
        }
        
        // Construire l'objet anomalie
        const anomaly = {
            id: Date.now(),
            type: type,
            description: description,
            severity: severity,
            timestamp: new Date().toISOString(),
            reporter: 'scanner_user'
        };
        
        // Ajouter des détails spécifiques pour les anomalies de quantité
        if (type === 'quantity') {
            const ordered = parseInt(document.getElementById('orderedQuantity').value);
            const received = parseInt(document.getElementById('receivedQuantity').value);
            const productIndex = parseInt(document.getElementById('affectedProduct').value);
            
            if (isNaN(ordered) || isNaN(received) || isNaN(productIndex)) {
                this.showNotification('Veuillez remplir tous les champs de quantité', 'error');
                return;
            }
            
            const product = this.analysisResult.products[productIndex];
            const difference = ordered - received;
            
            // Générer automatiquement une description si elle est vide
            if (!description) {
                if (difference > 0) {
                    description = `Quantité manquante pour ${product.name}: commandé ${ordered}, reçu seulement ${received}. Il manque ${difference} ${product.unit || 'unité'}${difference > 1 ? 's' : ''}.`;
                } else if (difference < 0) {
                    description = `Surplus pour ${product.name}: commandé ${ordered}, reçu ${received}. Surplus de ${Math.abs(difference)} ${product.unit || 'unité'}${Math.abs(difference) > 1 ? 's' : ''}.`;
                } else {
                    description = `Anomalie signalée pour ${product.name} (quantités identiques: ${ordered}).`;
                }
                
                // Mettre à jour le champ de description
                document.getElementById('anomalyDescription').value = description;
                anomaly.description = description;
            }
            
            anomaly.quantity_details = {
                ordered: ordered,
                received: received,
                difference: difference,
                product_name: product.name,
                product_index: productIndex,
                unit: product.unit || 'unité'
            };
        }
        
        // Vérifier qu'il y a une description (auto-générée ou manuelle)
        if (!anomaly.description) {
            this.showNotification('Veuillez ajouter une description de l\'anomalie', 'error');
            return;
        }
        
        // Ajouter l'anomalie à l'analysisResult
        if (!this.analysisResult.anomalies) {
            this.analysisResult.anomalies = [];
        }
        this.analysisResult.anomalies.push(anomaly);
        
        // Afficher l'anomalie dans la liste
        this.displayAnomaly(anomaly);
        
        // Réinitialiser le formulaire
        this.resetAnomalyForm();
        
        // Fermer le modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('addAnomalyModal'));
        if (modal) {
            modal.hide();
        }
        
        this.showNotification('Anomalie ajoutée avec succès', 'success');
    }
    
    displayAnomaly(anomaly) {
        const container = document.getElementById('anomaliesContainer');
        const listContainer = document.getElementById('currentAnomaliesList');
        
        // Afficher la section si première anomalie
        if (this.analysisResult.anomalies.length === 1) {
            listContainer.style.display = 'block';
        }
        
        const anomalyElement = document.createElement('div');
        anomalyElement.className = 'card mb-2';
        anomalyElement.innerHTML = `
            <div class="card-body p-3">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-1">
                            <span class="badge bg-${this.getAnomalySeverityColor(anomaly.severity)} me-2">
                                ${this.getAnomalyTypeLabel(anomaly.type)}
                            </span>
                            ${anomaly.severity === 'high' ? '<i class="bi bi-exclamation-octagon text-danger"></i>' : ''}
                        </h6>
                        <p class="mb-1 small">${anomaly.description}</p>
                        ${anomaly.quantity_details ? `
                            <small class="text-muted">
                                Produit: ${anomaly.quantity_details.product_name}<br>
                                Commandé: ${anomaly.quantity_details.ordered} | Reçu: ${anomaly.quantity_details.received}
                                <span class="text-danger">(Manque: ${anomaly.quantity_details.difference})</span>
                            </small>
                        ` : ''}
                    </div>
                    <button class="btn btn-sm btn-outline-danger" onclick="removeAnomaly(${anomaly.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        `;
        
        container.appendChild(anomalyElement);
    }
    
    getAnomalySeverityColor(severity) {
        switch (severity) {
            case 'low': return 'success';
            case 'medium': return 'warning';
            case 'high': return 'danger';
            default: return 'secondary';
        }
    }
    
    getAnomalyTypeLabel(type) {
        const labels = {
            'quantity': 'Quantité',
            'missing': 'Manquant',
            'damaged': 'Endommagé',
            'expired': 'Périmé',
            'wrong_product': 'Mauvais produit',
            'other': 'Autre'
        };
        return labels[type] || type;
    }
    
    removeAnomaly(anomalyId) {
        if (!this.analysisResult.anomalies) return;
        
        // Supprimer de l'array
        this.analysisResult.anomalies = this.analysisResult.anomalies.filter(a => a.id !== anomalyId);
        
        // Recharger l'affichage
        this.refreshAnomaliesList();
        
        this.showNotification('Anomalie supprimée', 'info');
    }
    
    refreshAnomaliesList() {
        const container = document.getElementById('anomaliesContainer');
        const listContainer = document.getElementById('currentAnomaliesList');
        
        container.innerHTML = '';
        
        if (!this.analysisResult.anomalies || this.analysisResult.anomalies.length === 0) {
            listContainer.style.display = 'none';
            return;
        }
        
        this.analysisResult.anomalies.forEach(anomaly => {
            this.displayAnomaly(anomaly);
        });
    }
    
    resetAnomalyForm() {
        document.getElementById('anomalyType').value = '';
        document.getElementById('anomalyDescription').value = '';
        document.getElementById('orderedQuantity').value = '';
        document.getElementById('receivedQuantity').value = '';
        document.getElementById('affectedProduct').value = '';
        document.getElementById('quantityAnomalyCard').style.display = 'none';
        
        // Reset severity to medium
        document.getElementById('severityMedium').checked = true;
    }
    
    applyProductsAndAnomalies() {
        try {
            // Les modifications sont déjà appliquées en temps réel
            // Il suffit de fermer le modal et actualiser l'affichage
            
            // Recalculer les totaux généraux
            this.recalculateTotals();
            
            // Actualiser l'affichage principal des produits
            this.fillProductsList(this.analysisResult);
            
            // Fermer le modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('editProductsModal'));
            modal.hide();
            
            // Afficher un résumé des modifications
            const message = this.getModificationsSummary();
            this.showNotification(message, 'success');
            
        } catch (error) {
            console.error('Erreur application modifications:', error);
            this.showNotification('Erreur lors de l\'application des modifications', 'error');
        }
    }
    
    recalculateTotals() {
        if (!this.analysisResult || !this.analysisResult.products) return;
        
        let total = 0;
        this.analysisResult.products.forEach(product => {
            total += (product.unit_price || 0) * (product.quantity || 1);
        });
        
        // Mettre à jour l'affichage du total
        document.getElementById('totalAmount').textContent = this.formatPrice(total);
        
        // Mettre à jour dans invoice_info si existe
        if (this.analysisResult.invoice_info) {
            this.analysisResult.invoice_info.total_amount = total;
        }
    }
    
    getModificationsSummary() {
        let message = 'Modifications appliquées !';
        
        if (this.analysisResult.anomalies && this.analysisResult.anomalies.length > 0) {
            message += ` ${this.analysisResult.anomalies.length} anomalie(s) signalée(s).`;
        }
        
        return message;
    }

    setupAnomalyModal() {
        // Configurer le listener pour le type d'anomalie
        this.setupAnomalyTypeListener();
        
        // Remplir la liste des produits pour les anomalies
        this.fillAnomalyProductsList();
    }

    // ===== NOUVELLES FONCTIONS MULTI-PAGES =====
    
    async handleMultipleFiles(files) {
        console.log(`📄 ${files.length} fichiers sélectionnés pour facture multi-pages`);
        
        // Réinitialiser les pages
        this.invoicePages = [];
        this.isMultiPageMode = true;
        
        // Traiter chaque fichier
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            if (this.validateFile(file)) {
                try {
                    const compressedFile = await this.compressImage(file);
                    const imageData = await this.fileToDataURL(compressedFile);
                    
                    this.invoicePages.push({
                        id: Date.now() + i,
                        file: compressedFile,
                        imageData: imageData,
                        name: file.name,
                        pageNumber: i + 1
                    });
                } catch (error) {
                    console.error(`Erreur traitement page ${i + 1}:`, error);
                    this.showNotification(`Erreur page ${i + 1}: ${file.name}`, 'error');
                }
            }
        }
        
        if (this.invoicePages.length > 0) {
            this.showPagesContainer();
            this.renderPagesList();
            this.updatePageCounter();
        }
    }
    
    fileToDataURL(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = e => resolve(e.target.result);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }
    
    showPagesContainer() {
        // Masquer les autres sections
        document.getElementById('uploadZone').style.display = 'none';
        document.getElementById('imagePreview').style.display = 'none';
        document.getElementById('actionButtons').style.display = 'none';
        
        // Afficher le conteneur des pages
        document.getElementById('pagesContainer').style.display = 'block';
    }
    
    renderPagesList() {
        const pagesList = document.getElementById('pagesList');
        pagesList.innerHTML = '';
        
        this.invoicePages.forEach((page, index) => {
            const pageElement = document.createElement('div');
            pageElement.className = 'page-item';
            pageElement.innerHTML = `
                <div class="row align-items-center">
                    <div class="col-3">
                        <img src="${page.imageData}" class="page-thumbnail" alt="Page ${page.pageNumber}">
                    </div>
                    <div class="col-6">
                        <h6 class="mb-1">Page ${page.pageNumber}</h6>
                        <small class="text-muted">${page.name}</small>
                    </div>
                    <div class="col-3 page-actions">
                        <button class="btn btn-outline-danger btn-sm me-1" onclick="removePage(${page.id})" title="Supprimer">
                            <i class="bi bi-trash"></i>
                        </button>
                        <button class="btn btn-outline-primary btn-sm" onclick="previewPage(${page.id})" title="Agrandir">
                            <i class="bi bi-eye"></i>
                        </button>
                    </div>
                </div>
            `;
            pagesList.appendChild(pageElement);
        });
    }
    
    updatePageCounter() {
        const counter = document.getElementById('pageCounter');
        const analyzeBtn = document.getElementById('analyzeMultiBtn');
        
        counter.textContent = `${this.invoicePages.length} page(s)`;
        
        // Activer/désactiver le bouton d'analyse
        if (this.invoicePages.length > 0) {
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = `
                <i class="bi bi-robot me-1"></i>
                <small>Analyser (${this.invoicePages.length})</small>
            `;
        } else {
            analyzeBtn.disabled = true;
            analyzeBtn.innerHTML = `
                <i class="bi bi-robot me-1"></i>
                <small>Analyser</small>
            `;
        }
    }
    
    removePage(pageId) {
        this.invoicePages = this.invoicePages.filter(page => page.id !== pageId);
        
        if (this.invoicePages.length === 0) {
            this.resetToUploadMode();
        } else {
            // Renuméroter les pages
            this.invoicePages.forEach((page, index) => {
                page.pageNumber = index + 1;
            });
            this.renderPagesList();
            this.updatePageCounter();
        }
        
        this.showNotification('Page supprimée', 'info');
    }
    
    previewPage(pageId) {
        const page = this.invoicePages.find(p => p.id === pageId);
        if (page) {
            this.showFullImage(page.imageData);
        }
    }
    
    addMorePages() {
        // Réutiliser l'input file
        document.getElementById('fileInput').click();
    }
    
    clearAllPages() {
        this.invoicePages = [];
        this.resetToUploadMode();
        this.showNotification('Toutes les pages supprimées', 'info');
    }
    
    resetToUploadMode() {
        this.isMultiPageMode = false;
        
        // Afficher la zone d'upload
        document.getElementById('uploadZone').style.display = 'block';
        
        // Masquer le conteneur des pages
        document.getElementById('pagesContainer').style.display = 'none';
        document.getElementById('imagePreview').style.display = 'none';
        document.getElementById('actionButtons').style.display = 'none';
    }
    
    async analyzeMultiplePages() {
        if (this.invoicePages.length === 0) {
            this.showNotification('Aucune page à analyser', 'warning');
            return;
        }
        
        try {
            this.isProcessing = true;
            this.showProgress(`Analyse de ${this.invoicePages.length} pages...`);
            
            // Préparer les données pour l'API
            const formData = new FormData();
            
            // Ajouter toutes les pages
            this.invoicePages.forEach((page, index) => {
                formData.append(`pages`, page.file);
            });
            
            // Ajouter le mode de scan
            const scanMode = document.querySelector('input[name="scanMode"]:checked')?.value || 'quick';
            formData.append('mode', scanMode);
            formData.append('multipage', 'true');
            
            if (scanMode === 'order' && this.selectedOrderId) {
                formData.append('order_id', this.selectedOrderId);
            }
            
            // Envoyer à l'API
            const response = await fetch('/api/invoices/analyze', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                // Ajouter info multi-pages au résultat
                result.data.isMultiPage = true;
                result.data.totalPages = this.invoicePages.length;
                
                await this.displayResults(result.data);
                this.showNotification(`Facture ${this.invoicePages.length} pages analysée !`, 'success');
            } else {
                throw new Error(result.error || 'Erreur inconnue');
            }
            
        } catch (error) {
            console.error('Erreur analyse multi-pages:', error);
            this.showNotification('Erreur lors de l\'analyse: ' + error.message, 'error');
        } finally {
            this.isProcessing = false;
            this.hideProgress();
        }
    }
}

// Nouvelles fonctions globales pour multi-pages
function addMorePages() {
    window.scanner.addMorePages();
}

function clearAllPages() {
    window.scanner.clearAllPages();
}

function analyzeMultiplePages() {
    window.scanner.analyzeMultiplePages();
}

function removePage(pageId) {
    window.scanner.removePage(pageId);
}

function previewPage(pageId) {
    window.scanner.previewPage(pageId);
}

// Fonctions globales pour compatibilité
function startCamera() {
    window.scanner.startCamera();
}

function switchCamera() {
    window.scanner.switchCamera();
}

function capturePhoto() {
    window.scanner.capturePhoto();
}

function stopCamera() {
    window.scanner.stopCamera();
}

function analyzeInvoice() {
    window.scanner.analyzeInvoice();
}

function saveInvoice() {
    window.scanner.saveInvoice();
}

function shareResults() {
    window.scanner.shareResults();
}

function resetScanner() {
    window.scanner.resetScanner();
}

function showHistory() {
    window.scanner.showHistory();
}

function showSettings() {
    window.scanner.showSettings();
}

function toggleProductsView() {
    const container = document.getElementById('productsContainer');
    const icon = document.getElementById('expandIcon');
    
    if (container.style.maxHeight === 'none') {
        container.style.maxHeight = '300px';
        icon.className = 'bi bi-arrows-expand';
    } else {
        container.style.maxHeight = 'none';
        icon.className = 'bi bi-arrows-collapse';
    }
}

// === NOUVELLES FONCTIONS GLOBALES D'ÉDITION ===

function showEditModal() {
    window.scanner.showEditModal();
}

function toggleCustomSupplier() {
    window.scanner.toggleCustomSupplier();
}

function applyScanCorrections() {
    window.scanner.applyScanCorrections();
}

// === NOUVELLES FONCTIONS GLOBALES POUR PRODUITS ET ANOMALIES ===

function showEditProductsModal() {
    window.scanner.showEditProductsModal();
}

function updateProductField(productIndex, field, value) {
    window.scanner.updateProductField(productIndex, field, value);
}

function addAnomaly() {
    window.scanner.addAnomaly();
}

function removeAnomaly(anomalyId) {
    window.scanner.removeAnomaly(anomalyId);
}

function applyProductsAndAnomalies() {
    window.scanner.applyProductsAndAnomalies();
}

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    window.scanner = new ScannerPro();
});

// Service Worker pour cache offline
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => console.log('SW registered'))
            .catch(error => console.log('SW registration failed'));
    });
} 

// 🚀 NOUVELLES FONCTIONS POUR MULTI-FACTURES
// ========================================

// Fonction pour sauvegarder et continuer
function saveAndContinue() {
    if (window.scanner.analysisResult) {
        // Ajouter la facture à la liste des scannées
        window.scanner.addToScannedList();
        
        // Sauvegarder automatiquement
        window.scanner.saveInvoice(true); // true = mode silencieux
        
        // Préparer pour la suivante
        window.scanner.prepareNextScan();
    }
}

// Fonction pour ajouter une nouvelle facture à scanner
function addNewInvoice() {
    window.scanner.resetScanner();
    window.scanner.hideScannedList();
}

// Fonction pour voir toutes les factures
function viewAllInvoices() {
    window.location.href = '/factures';
}

// Fonction pour voir une facture spécifique
function viewScannedInvoice(invoiceId) {
    window.scanner.showScannedInvoice(invoiceId);
}

// Nouvelles méthodes dans la classe ScannerPro
ScannerPro.prototype.addToScannedList = function() {
    if (!this.analysisResult) return;
    
    // Générer un ID unique pour cette facture
    this.invoiceCounter++;
    const invoiceId = `SCAN-${Date.now()}-${this.invoiceCounter}`;
    
    // Créer l'objet facture
    const scannedInvoice = {
        id: invoiceId,
        supplier: this.analysisResult.supplier || 'Inconnu',
        invoiceNumber: this.analysisResult.invoice_number || '',
        total: this.analysisResult.total_amount || 0,
        date: this.analysisResult.date || new Date().toLocaleDateString(),
        products: this.analysisResult.products || [],
        analysisData: { ...this.analysisResult },
        status: 'processing', // processing, completed, error
        progress: 0,
        scannedAt: new Date().toISOString(),
        saved: false
    };
    
    // Ajouter à la liste
    this.scannedInvoices.push(scannedInvoice);
    this.currentInvoiceId = invoiceId;
    this.isMultiInvoiceMode = true;
    
    // Mettre à jour l'affichage
    this.updateScannedInvoicesList();
    this.showScannedList();
    
    // Simuler la progression de sauvegarde
    this.simulateSaveProgress(invoiceId);
};

ScannerPro.prototype.simulateSaveProgress = function(invoiceId) {
    const invoice = this.scannedInvoices.find(inv => inv.id === invoiceId);
    if (!invoice) return;
    
    let progress = 0;
    invoice.status = 'processing';
    
    const progressInterval = setInterval(() => {
        progress += Math.random() * 20 + 5; // Progression aléatoire
        
        if (progress >= 100) {
            progress = 100;
            invoice.status = 'completed';
            invoice.progress = 100;
            clearInterval(progressInterval);
            
            // Notification de fin
            this.showNotification(`✅ Facture ${invoice.supplier} sauvegardée !`, 'success');
        } else {
            invoice.progress = progress;
        }
        
        this.updateScannedInvoicesList();
    }, 500);
};

ScannerPro.prototype.updateScannedInvoicesList = function() {
    const container = document.getElementById('scannedInvoicesContainer');
    const countBadge = document.getElementById('scannedCount');
    const viewAllBtn = document.getElementById('viewAllBtn');
    
    if (!container) return;
    
    // Mettre à jour le compteur
    if (countBadge) {
        countBadge.textContent = this.scannedInvoices.length;
    }
    
    // Afficher le bouton "Voir Toutes" s'il y a des factures
    if (viewAllBtn) {
        viewAllBtn.style.display = this.scannedInvoices.length > 0 ? 'inline-block' : 'none';
    }
    
    // Générer le HTML de la liste
    container.innerHTML = this.scannedInvoices.map(invoice => {
        const statusClass = invoice.status;
        const statusText = {
            'processing': '⏳ En cours...',
            'completed': '✅ Terminée',
            'error': '❌ Erreur'
        }[invoice.status] || 'En attente';
        
        const progressBarClass = invoice.status === 'processing' ? 'processing' : '';
        
        return `
            <div class="invoice-item ${statusClass}" onclick="viewScannedInvoice('${invoice.id}')">
                <div class="row align-items-center">
                    <div class="col-3">
                        <div class="text-center">
                            <div class="fw-bold text-primary">${invoice.supplier}</div>
                            <small class="text-muted">#${invoice.invoiceNumber}</small>
                        </div>
                    </div>
                    <div class="col-6">
                        <div class="fw-bold">${this.formatPrice(invoice.total)}</div>
                        <small class="text-muted">${invoice.date}</small>
                        
                        <!-- Barre de progression -->
                        <div class="invoice-progress ${progressBarClass}">
                            <div class="progress-bar" style="width: ${invoice.progress}%"></div>
                        </div>
                    </div>
                    <div class="col-3 text-end">
                        <span class="invoice-status ${statusClass}">${statusText}</span>
                        <br>
                        <small class="text-muted">${invoice.products?.length || 0} produits</small>
                    </div>
                </div>
            </div>
        `;
    }).join('');
};

ScannerPro.prototype.showScannedList = function() {
    const listContainer = document.getElementById('scannedInvoicesList');
    const analysisResults = document.getElementById('analysisResults');
    
    if (listContainer) {
        listContainer.style.display = 'block';
    }
    
    // Masquer les résultats d'analyse
    if (analysisResults) {
        analysisResults.style.display = 'none';
    }
};

ScannerPro.prototype.hideScannedList = function() {
    const listContainer = document.getElementById('scannedInvoicesList');
    
    if (listContainer) {
        listContainer.style.display = 'none';
    }
};

ScannerPro.prototype.showScannedInvoice = function(invoiceId) {
    const invoice = this.scannedInvoices.find(inv => inv.id === invoiceId);
    if (!invoice) return;
    
    // Marquer comme vue
    this.currentInvoiceId = invoiceId;
    
    // Afficher les détails de la facture
    this.analysisResult = invoice.analysisData;
    
    // Masquer la liste et afficher les résultats
    this.hideScannedList();
    this.displayResults(invoice.analysisData);
    
    // Notification
    this.showNotification(`📄 Facture ${invoice.supplier} affichée`, 'info');
};

ScannerPro.prototype.prepareNextScan = function() {
    // Réinitialiser pour le prochain scan
    this.currentFile = null;
    this.currentImageData = null;
    this.analysisResult = null;
    
    // Afficher la zone d'upload
    document.getElementById('uploadZone').style.display = 'block';
    document.getElementById('imagePreview').style.display = 'none';
    document.getElementById('actionButtons').style.display = 'none';
    
    // Réinitialiser le file input
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.value = '';
    }
    
    // Notification
    this.showNotification('📄 Prêt pour la prochaine facture !', 'info');
};

// Nouvelles fonctions globales pour multi-pages

// ... existing code ...