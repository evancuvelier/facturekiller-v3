/**
 * 🔧 CORRECTIONS URGENTES POUR SCANNER
 * Fixes pour: Historique, Réglages, Affichage Résultats
 */

console.log('🔧 Chargement des corrections scanner...');

// Fix 1: Historique - Modal manquant
function fixHistoryModal() {
    const originalShowHistory = window.showHistory;
    window.showHistory = function() {
        if (!window.scanner) return;
        
        // Créer le modal s'il n'existe pas
        let modal = document.getElementById('historyModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.id = 'historyModal';
            modal.innerHTML = `
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="bi bi-clock-history me-2"></i>📚 Historique des Scans
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div id="historyContent">
                                <div id="historyList"></div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        const bsModal = new bootstrap.Modal(modal);
        window.scanner.loadHistoryList();
        bsModal.show();
    };
}

// Fix 2: Réglages - Sauvegarde forcée
function fixSettingsModal() {
    const originalShowSettings = window.showSettings;
    window.showSettings = function() {
        if (!window.scanner) return;
        
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-gear me-2"></i>Paramètres Scanner
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="form-check form-switch mb-3">
                            <input class="form-check-input" type="checkbox" id="autoAnalyze" ${window.scanner.isAutoAnalyzeEnabled() ? 'checked' : ''}>
                            <label class="form-check-label" for="autoAnalyze">
                                <strong>Analyse automatique</strong><br>
                                <small class="text-muted">Analyser directement après sélection</small>
                            </label>
                        </div>
                        <div class="form-check form-switch mb-3">
                            <input class="form-check-input" type="checkbox" id="hapticFeedback" ${window.scanner.isHapticEnabled() ? 'checked' : ''}>
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
        
        // FORCER la sauvegarde
        modal.querySelector('#saveSettingsBtn').addEventListener('click', () => {
            const autoAnalyze = modal.querySelector('#autoAnalyze').checked;
            const hapticFeedback = modal.querySelector('#hapticFeedback').checked;
            const imageQuality = modal.querySelector('#imageQuality').value;
            
            // SAUVEGARDER FORCÉ
            localStorage.setItem('autoAnalyze', String(autoAnalyze));
            localStorage.setItem('hapticFeedback', String(hapticFeedback));
            localStorage.setItem('imageQuality', imageQuality);
            
            console.log('🔧 Paramètres forcés:', { autoAnalyze, hapticFeedback, imageQuality });
            
            window.scanner.showNotification('✅ Paramètres sauvegardés !', 'success');
            bsModal.hide();
        });
        
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
    };
}

// Fix 3: Affichage résultats - Forcer l'affichage
function fixDisplayResults() {
    if (!window.scanner) return;
    
    const originalDisplayResults = window.scanner.displayResults;
    window.scanner.displayResults = async function(data) {
        console.log('🔧 FIX displayResults:', data);
        
        try {
            this.hideProgress();
            this.analysisResult = data;
            
            // Éviter les re-scans infinis
            if (data.coherence_check && !this.hasRetried && !data.accepted_with_issues) {
                const coherenceIssues = this.checkResultCoherence(data);
                if (coherenceIssues.needsRescan) {
                    return this.handleIncoherentResults(data, coherenceIssues);
                }
            }
            
            // Remplir les données
            this.fillInvoiceInfo(data);
            await this.fillProductsList(data);
            this.fillQuickStats(data);
            
            // FORCER l'affichage
            const uploadZone = document.getElementById('uploadZone');
            const imagePreview = document.getElementById('imagePreview');
            const actionButtons = document.getElementById('actionButtons');
            let resultsElement = document.getElementById('analysisResults');
            
            // Masquer upload/preview
            if (uploadZone) uploadZone.style.display = 'none';
            if (imagePreview) imagePreview.style.display = 'none';
            if (actionButtons) actionButtons.style.display = 'none';
            
            // Créer résultats si nécessaire
            if (!resultsElement) {
                this.createResultsContainer();
                resultsElement = document.getElementById('analysisResults');
            }
            
            // AFFICHER FORCÉ
            if (resultsElement) {
                resultsElement.style.display = 'block';
                resultsElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                console.log('✅ FIX: Résultats affichés !');
            }
            
            this.startSaveReminder();
            this.saveToHistory(data);
            
        } catch (error) {
            console.error('❌ FIX displayResults error:', error);
            this.showNotification('Erreur affichage: ' + error.message, 'error');
        }
    };
}

// Appliquer les corrections
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        if (window.scanner) {
            fixHistoryModal();
            fixSettingsModal();
            fixDisplayResults();
            console.log('✅ Toutes les corrections appliquées !');
        }
    }, 1000);
});

console.log('🔧 Scanner-fixes chargé !'); 