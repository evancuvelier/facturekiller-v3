console.log('🔧 CORRECTIONS SCANNER EN COURS...');

// Fix du modal historique
function fixHistoire() {
    window.showHistory = function() {
        if (!window.scanner) return;
        
        let modal = document.getElementById('historyModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.id = 'historyModal';
            modal.innerHTML = `
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">📚 Historique</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div id="historyContent"><div id="historyList"></div></div>
                        </div>
                    </div>
                </div>`;
            document.body.appendChild(modal);
        }
        
        const bsModal = new bootstrap.Modal(modal);
        window.scanner.loadHistoryList();
        bsModal.show();
    };
}

// Fix des paramètres 
function fixParametres() {
    window.showSettings = function() {
        if (!window.scanner) return;
        
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">⚙️ Paramètres</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="form-check form-switch mb-3">
                            <input class="form-check-input" type="checkbox" id="autoAnalyze" ${window.scanner.isAutoAnalyzeEnabled() ? 'checked' : ''}>
                            <label class="form-check-label" for="autoAnalyze">Analyse automatique</label>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
                        <button type="button" class="btn btn-primary" onclick="sauvegarderParametres(this)">Confirmer</button>
                    </div>
                </div>
            </div>`;
        
        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        window.sauvegarderParametres = function(btn) {
            const autoAnalyze = modal.querySelector('#autoAnalyze').checked;
            localStorage.setItem('autoAnalyze', String(autoAnalyze));
            window.scanner.showNotification('✅ Sauvegardé !', 'success');
            bootstrap.Modal.getInstance(modal).hide();
            setTimeout(() => document.body.removeChild(modal), 500);
        };
    };
}

// Fix affichage résultats
function fixAffichage() {
    if (window.scanner && window.scanner.displayResults) {
        const old = window.scanner.displayResults;
        window.scanner.displayResults = async function(data) {
            console.log('🔧 FIX displayResults');
            
            this.hideProgress();
            this.analysisResult = data;
            
            // Éviter re-scan
            if (data.coherence_check && !this.hasRetried && !data.accepted_with_issues) {
                const issues = this.checkResultCoherence(data);
                if (issues.needsRescan) {
                    return this.handleIncoherentResults(data, issues);
                }
            }
            
            this.fillInvoiceInfo(data);
            await this.fillProductsList(data);
            this.fillQuickStats(data);
            
            // FORCER affichage
            const upload = document.getElementById('uploadZone');
            const preview = document.getElementById('imagePreview');
            const actions = document.getElementById('actionButtons');
            let results = document.getElementById('analysisResults');
            
            if (upload) upload.style.display = 'none';
            if (preview) preview.style.display = 'none';
            if (actions) actions.style.display = 'none';
            
            if (!results) {
                this.createResultsContainer();
                results = document.getElementById('analysisResults');
            }
            
            if (results) {
                results.style.display = 'block';
                results.scrollIntoView();
                console.log('✅ FIX: Résultats affichés');
            }
            
            this.startSaveReminder();
            this.saveToHistory(data);
        };
    }
}

// Appliquer
setTimeout(() => {
    fixHistoire();
    fixParametres(); 
    fixAffichage();
    console.log('✅ FIXES APPLIQUÉS !');
}, 1000); 