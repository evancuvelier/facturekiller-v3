/**
 * Gestion des anomalies - Interface complète
 */

let anomaliesData = [];
let currentAnomalieId = null;

// Statuts avec icônes et couleurs
const STATUT_CONFIG = {
    'detectee': { icon: '🔍', class: 'warning', label: 'Détectée' },
    'mail_envoye': { icon: '📧', class: 'info', label: 'Mail Envoyé' },
    'avoir_accepte': { icon: '✅', class: 'success', label: 'Avoir Accepté' },
    'avoir_refuse': { icon: '❌', class: 'danger', label: 'Avoir Refusé' },
    'resolu': { icon: '✔️', class: 'secondary', label: 'Résolu' }
};

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Initialisation Anomalies Manager');
    loadAnomalies();
    loadStats();
});

// Charger les anomalies
async function loadAnomalies() {
    try {
        showLoading();
        
        const statut = document.getElementById('filterStatut').value;
        const fournisseur = document.getElementById('filterFournisseur').value;
        
        let url = '/api/anomalies';
        const params = new URLSearchParams();
        if (statut) params.append('statut', statut);
        if (fournisseur) params.append('fournisseur', fournisseur);
        
        if (params.toString()) {
            url += '?' + params.toString();
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            anomaliesData = data.anomalies;
            displayAnomalies(anomaliesData);
            updateStats(data.stats);
            loadFournisseurFilter();
        } else {
            showError('Erreur lors du chargement des anomalies: ' + data.error);
        }
        
    } catch (error) {
        console.error('Erreur:', error);
        showError('Erreur de connexion');
    } finally {
        hideLoading();
    }
}

// Afficher les anomalies
function displayAnomalies(anomalies) {
    const tbody = document.getElementById('anomaliesTableBody');
    const noAnomalies = document.getElementById('noAnomalies');
    
    if (!anomalies || anomalies.length === 0) {
        tbody.innerHTML = '';
        noAnomalies.style.display = 'block';
        return;
    }
    
    noAnomalies.style.display = 'none';
    
    tbody.innerHTML = anomalies.map(anomalie => {
        const statutConfig = STATUT_CONFIG[anomalie.statut] || STATUT_CONFIG['detectee'];
        const ecartClass = anomalie.ecart_euros > 0 ? 'text-danger' : 'text-success';
        
        return `
            <tr>
                <td>
                    <code class="small">${anomalie.id}</code>
                </td>
                <td>
                    <strong>${anomalie.produit_nom}</strong>
                </td>
                <td>
                    <span class="badge bg-secondary">${anomalie.fournisseur}</span>
                </td>
                <td>
                    <span class="badge bg-info">${anomalie.restaurant}</span>
                </td>
                <td>
                    <strong class="text-primary">${anomalie.prix_facture}€</strong>
                </td>
                <td>
                    <span class="text-muted">${anomalie.prix_catalogue}€</span>
                </td>
                <td>
                    <span class="${ecartClass}">
                        <strong>${anomalie.ecart_euros > 0 ? '+' : ''}${anomalie.ecart_euros}€</strong>
                        <br>
                        <small>(${anomalie.ecart_pourcent > 0 ? '+' : ''}${anomalie.ecart_pourcent}%)</small>
                    </span>
                </td>
                <td>
                    <span class="badge bg-${statutConfig.class}">
                        ${statutConfig.icon} ${statutConfig.label}
                    </span>
                </td>
                <td>
                    <small class="text-muted">
                        ${formatDate(anomalie.date_detection)}
                    </small>
                </td>
                <td>
                    ${generateActionButtons(anomalie)}
                </td>
            </tr>
        `;
    }).join('');
}

// Générer les boutons d'action selon le statut
function generateActionButtons(anomalie) {
    const buttons = [];
    
    // Bouton détails (toujours visible)
    buttons.push(`
        <button class="btn btn-sm btn-outline-primary me-1" 
                onclick="showAnomalieDetails('${anomalie.id}')" 
                title="Voir détails">
            <i class="fas fa-eye"></i>
        </button>
    `);
    
    // Actions selon le statut
    switch (anomalie.statut) {
        case 'detectee':
            buttons.push(`
                <button class="btn btn-sm btn-warning" 
                        onclick="sendMailToSupplier('${anomalie.id}')" 
                        title="Signaler au fournisseur">
                    <i class="fas fa-envelope me-1"></i>Signaler
                </button>
            `);
            break;
            
        case 'mail_envoye':
            buttons.push(`
                <button class="btn btn-sm btn-success me-1" 
                        onclick="markAvoirAccepted('${anomalie.id}')" 
                        title="Avoir accepté">
                    <i class="fas fa-check me-1"></i>Accepté
                </button>
                <button class="btn btn-sm btn-danger" 
                        onclick="markAvoirRefused('${anomalie.id}')" 
                        title="Avoir refusé">
                    <i class="fas fa-times me-1"></i>Refusé
                </button>
            `);
            break;
            
        case 'avoir_accepte':
            buttons.push(`
                <span class="badge bg-success">
                    <i class="fas fa-check-circle me-1"></i>Résolu
                </span>
            `);
            break;
            
        case 'avoir_refuse':
            buttons.push(`
                <span class="badge bg-danger">
                    <i class="fas fa-times-circle me-1"></i>Refusé
                </span>
            `);
            break;
    }
    
    return buttons.join(' ');
}

// Envoyer mail au fournisseur
async function sendMailToSupplier(anomalieId) {
    if (!confirm('Envoyer un signalement au fournisseur pour cette anomalie ?')) {
        return;
    }
    
    try {
        showLoading();
        
        const response = await fetch(`/api/anomalies/${anomalieId}/send-mail`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess('Mail marqué comme envoyé au fournisseur !');
            
            // Afficher le contenu de l'email
            document.getElementById('emailContent').textContent = data.email_content;
            new bootstrap.Modal(document.getElementById('emailModal')).show();
            
            // Recharger les données
            loadAnomalies();
        } else {
            showError('Erreur: ' + data.error);
        }
        
    } catch (error) {
        console.error('Erreur:', error);
        showError('Erreur de connexion');
    } finally {
        hideLoading();
    }
}

// Marquer avoir accepté
async function markAvoirAccepted(anomalieId) {
    const commentaire = prompt('Commentaire (optionnel) :');
    
    try {
        showLoading();
        
        const response = await fetch(`/api/anomalies/${anomalieId}/avoir-accepte`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                commentaire: commentaire
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess('Avoir marqué comme accepté !');
            loadAnomalies();
        } else {
            showError('Erreur: ' + data.error);
        }
        
    } catch (error) {
        console.error('Erreur:', error);
        showError('Erreur de connexion');
    } finally {
        hideLoading();
    }
}

// Marquer avoir refusé
async function markAvoirRefused(anomalieId) {
    const commentaire = prompt('Raison du refus (optionnel) :');
    
    try {
        showLoading();
        
        const response = await fetch(`/api/anomalies/${anomalieId}/avoir-refuse`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                commentaire: commentaire
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess('Avoir marqué comme refusé !');
            loadAnomalies();
        } else {
            showError('Erreur: ' + data.error);
        }
        
    } catch (error) {
        console.error('Erreur:', error);
        showError('Erreur de connexion');
    } finally {
        hideLoading();
    }
}

// Afficher détails d'une anomalie
async function showAnomalieDetails(anomalieId) {
    try {
        const response = await fetch(`/api/anomalies/${anomalieId}`);
        const data = await response.json();
        
        if (data.success) {
            const anomalie = data.anomalie;
            const statutConfig = STATUT_CONFIG[anomalie.statut] || STATUT_CONFIG['detectee'];
            
            document.getElementById('anomalieModalBody').innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <h6><i class="fas fa-info-circle me-2"></i>Informations Générales</h6>
                        <ul class="list-unstyled">
                            <li><strong>ID:</strong> <code>${anomalie.id}</code></li>
                            <li><strong>Produit:</strong> ${anomalie.produit_nom}</li>
                            <li><strong>Fournisseur:</strong> ${anomalie.fournisseur}</li>
                            <li><strong>Restaurant:</strong> ${anomalie.restaurant}</li>
                            <li><strong>Type:</strong> ${anomalie.type_anomalie}</li>
                        </ul>
                    </div>
                    <div class="col-md-6">
                        <h6><i class="fas fa-euro-sign me-2"></i>Détails Prix</h6>
                        <ul class="list-unstyled">
                            <li><strong>Prix Facturé:</strong> <span class="text-primary">${anomalie.prix_facture}€</span></li>
                            <li><strong>Prix Catalogue:</strong> <span class="text-muted">${anomalie.prix_catalogue}€</span></li>
                            <li><strong>Écart:</strong> <span class="${anomalie.ecart_euros > 0 ? 'text-danger' : 'text-success'}">${anomalie.ecart_euros > 0 ? '+' : ''}${anomalie.ecart_euros}€ (${anomalie.ecart_pourcent > 0 ? '+' : ''}${anomalie.ecart_pourcent}%)</span></li>
                        </ul>
                    </div>
                </div>
                
                <hr>
                
                <div class="row">
                    <div class="col-12">
                        <h6><i class="fas fa-clock me-2"></i>Historique</h6>
                        <div class="timeline">
                            <div class="timeline-item">
                                <span class="badge bg-warning">🔍</span>
                                <strong>Détectée:</strong> ${formatDate(anomalie.date_detection)}
                            </div>
                            ${anomalie.date_mail_envoye ? `
                                <div class="timeline-item">
                                    <span class="badge bg-info">📧</span>
                                    <strong>Mail envoyé:</strong> ${formatDate(anomalie.date_mail_envoye)}
                                </div>
                            ` : ''}
                            ${anomalie.date_reponse ? `
                                <div class="timeline-item">
                                    <span class="badge bg-${statutConfig.class}">${statutConfig.icon}</span>
                                    <strong>Réponse:</strong> ${formatDate(anomalie.date_reponse)}
                                </div>
                            ` : ''}
                        </div>
                        
                        ${anomalie.commentaire ? `
                            <div class="alert alert-info mt-3">
                                <strong>Commentaire:</strong> ${anomalie.commentaire}
                            </div>
                        ` : ''}
                        
                        <div class="mt-3">
                            <span class="badge bg-${statutConfig.class} fs-6">
                                ${statutConfig.icon} Statut: ${statutConfig.label}
                            </span>
                        </div>
                    </div>
                </div>
            `;
            
            new bootstrap.Modal(document.getElementById('anomalieModal')).show();
        } else {
            showError('Erreur: ' + data.error);
        }
        
    } catch (error) {
        console.error('Erreur:', error);
        showError('Erreur de connexion');
    }
}

// Charger les stats
async function loadStats() {
    try {
        const response = await fetch('/api/anomalies/stats');
        const data = await response.json();
        
        if (data.success) {
            updateStats(data.stats);
        }
        
    } catch (error) {
        console.error('Erreur chargement stats:', error);
    }
}

// Mettre à jour les stats
function updateStats(stats) {
    if (!stats) return;
    
    document.getElementById('totalAnomalies').textContent = stats.total || 0;
    document.getElementById('detecteesAnomalies').textContent = stats.detectees || 0;
    document.getElementById('mailEnvoyesAnomalies').textContent = stats.mail_envoyes || 0;
    document.getElementById('avoirAcceptesAnomalies').textContent = stats.avoir_acceptes || 0;
    document.getElementById('avoirRefusesAnomalies').textContent = stats.avoir_refuses || 0;
    document.getElementById('montantEcarts').textContent = (stats.montant_total_ecarts || 0).toFixed(2) + '€';
}

// Charger le filtre fournisseurs
function loadFournisseurFilter() {
    const select = document.getElementById('filterFournisseur');
    const fournisseurs = [...new Set(anomaliesData.map(a => a.fournisseur))].sort();
    
    // Garder l'option "Tous"
    const currentValue = select.value;
    select.innerHTML = '<option value="">Tous les fournisseurs</option>';
    
    fournisseurs.forEach(fournisseur => {
        if (fournisseur) {
            const option = document.createElement('option');
            option.value = fournisseur;
            option.textContent = fournisseur;
            select.appendChild(option);
        }
    });
    
    select.value = currentValue;
}

// Reset filters
function resetFilters() {
    document.getElementById('filterStatut').value = '';
    document.getElementById('filterFournisseur').value = '';
    loadAnomalies();
}

// Actualiser données
function refreshData() {
    loadAnomalies();
    loadStats();
}

// Utilitaires
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR') + ' ' + date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}

function showLoading() {
    // Implémenter loading si nécessaire
}

function hideLoading() {
    // Implémenter hide loading si nécessaire
}

function showSuccess(message) {
    // Vous pouvez implémenter un système de toast ici
    alert('✅ ' + message);
}

function showError(message) {
    // Vous pouvez implémenter un système de toast ici
    alert('❌ ' + message);
}

// Styles pour la timeline
const timelineStyles = `
<style>
.timeline {
    position: relative;
    padding-left: 30px;
}

.timeline-item {
    position: relative;
    padding: 8px 0;
    border-left: 2px solid #dee2e6;
    padding-left: 20px;
    margin-bottom: 10px;
}

.timeline-item:last-child {
    border-left: none;
}

.timeline-item .badge {
    position: absolute;
    left: -12px;
    top: 8px;
}

.stat-card {
    padding: 15px;
    border-radius: 10px;
    text-align: center;
    color: white;
    margin-bottom: 10px;
}

.stat-number {
    font-size: 1.5rem;
    font-weight: bold;
}

.stat-label {
    font-size: 0.8rem;
    opacity: 0.9;
}
</style>
`;

// Ajouter les styles
document.head.insertAdjacentHTML('beforeend', timelineStyles); 