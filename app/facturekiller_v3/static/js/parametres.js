/**
 * Gestion de la page Paramètres - Configuration Email
 */

class ParametresManager {
    constructor() {
        this.init();
    }

    init() {
        this.loadEmailConfig();
        this.loadNotifications();
        this.bindEvents();
    }

    bindEvents() {
        // Formulaire de configuration email
        document.getElementById('emailConfigForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveEmailConfig();
        });

        // Charger les notifications quand on change d'onglet
        const notifTab = document.getElementById('notifications-tab');
        if (notifTab) {
            notifTab.addEventListener('shown.bs.tab', () => {
                this.loadNotifications();
            });
        }
    }

    async loadEmailConfig() {
        try {
            const response = await fetch('/api/email/config');
            const result = await response.json();

            if (result.success) {
                const config = result.data;
                
                // Remplir le formulaire
                document.getElementById('emailEnabled').checked = config.enabled || false;
                document.getElementById('autoSend').checked = config.auto_send !== false;
                document.getElementById('senderName').value = config.sender_name || 'FactureKiller';
                document.getElementById('emailAddress').value = config.email || '';
                
                // Pour le mot de passe : si c'est "***", laisser le champ vide plutôt que d'afficher ***
                const passwordField = document.getElementById('emailPassword');
                if (config.password === '***') {
                    passwordField.placeholder = 'Mot de passe configuré (laisser vide pour garder)';
                    passwordField.value = '';
                } else {
                    passwordField.placeholder = 'Mot de passe Gmail';
                    passwordField.value = config.password || '';
                }
                
                document.getElementById('smtpServer').value = config.smtp_server || 'smtp.gmail.com';
            }
        } catch (error) {
            console.error('Erreur chargement config:', error);
            this.showToast('Erreur lors du chargement de la configuration', 'error');
        }
    }

    async saveEmailConfig() {
        try {
            const config = {
                enabled: document.getElementById('emailEnabled').checked,
                auto_send: document.getElementById('autoSend').checked,
                sender_name: document.getElementById('senderName').value || 'FactureKiller',
                email: document.getElementById('emailAddress').value,
                password: document.getElementById('emailPassword').value,
                smtp_server: document.getElementById('smtpServer').value || 'smtp.gmail.com',
                smtp_port: 587
            };

            // Validation
            if (config.enabled && !config.email) {
                this.showToast('Email requis si les notifications sont activées', 'error');
                return;
            }
            
            // Si le mot de passe est vide, on garde l'ancien (géré côté serveur)
            if (config.enabled && !config.password) {
                // Vérifier s'il y a déjà une config
                const currentConfig = await fetch('/api/email/config').then(r => r.json());
                if (!currentConfig.success || !currentConfig.data.password || currentConfig.data.password === '') {
                    this.showToast('Mot de passe requis pour la première configuration', 'error');
                    return;
                }
            }

            const response = await fetch('/api/email/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            });

            const result = await response.json();

            if (result.success) {
                this.showToast('Configuration sauvegardée avec succès', 'success');
                // NE PAS recharger automatiquement pour éviter de tout remettre à zéro
                // L'utilisateur peut recharger manuellement s'il le souhaite
            } else {
                this.showToast(result.error || 'Erreur lors de la sauvegarde', 'error');
            }
        } catch (error) {
            console.error('Erreur sauvegarde:', error);
            this.showToast('Erreur lors de la sauvegarde', 'error');
        }
    }

    async testEmailConnection() {
        const testBtn = document.querySelector('button[onclick="testEmailConnection()"]');
        const originalText = testBtn.innerHTML;
        
        try {
            testBtn.disabled = true;
            testBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Test en cours...';

            const response = await fetch('/api/email/test', {
                method: 'POST'
            });

            const result = await response.json();

            if (result.success) {
                this.showToast('✅ ' + result.message, 'success');
            } else {
                this.showToast('❌ ' + result.error, 'error');
            }
        } catch (error) {
            console.error('Erreur test connexion:', error);
            this.showToast('Erreur lors du test de connexion', 'error');
        } finally {
            testBtn.disabled = false;
            testBtn.innerHTML = originalText;
        }
    }

    async loadNotifications() {
        try {
            const container = document.getElementById('notificationsContainer');
            if (!container) return;
            
            container.innerHTML = `
                <div class="text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Chargement...</span>
                    </div>
                </div>
            `;

            const response = await fetch('/api/email/notifications?limit=50');
            const result = await response.json();

            if (result.success) {
                this.renderNotifications(result.data);
            } else {
                container.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        Erreur: ${result.error}
                    </div>
                `;
            }
        } catch (error) {
            console.error('Erreur chargement notifications:', error);
            const container = document.getElementById('notificationsContainer');
            if (container) {
                container.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        Erreur lors du chargement des notifications
                    </div>
                `;
            }
        }
    }

    renderNotifications(notifications) {
        const container = document.getElementById('notificationsContainer');
        if (!container) return;

        if (!notifications || notifications.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5 text-muted">
                    <i class="bi bi-inbox display-4 d-block mb-3"></i>
                    <p class="mb-0">Aucune notification envoyée pour le moment</p>
                </div>
            `;
            return;
        }

        // Trier par date décroissante
        notifications.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

        const html = notifications.map(notification => {
            const date = new Date(notification.timestamp);
            const dateStr = date.toLocaleDateString('fr-FR');
            const timeStr = date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
            
            const statusBadge = this.getStatusBadge(notification.status);
            const statusIcon = this.getStatusIcon(notification.status);

            return `
                <div class="card mb-3 ${notification.status === 'failed' || notification.status === 'error' ? 'border-danger' : ''}">
                    <div class="card-body">
                        <div class="row align-items-center">
                            <div class="col-md-8">
                                <div class="d-flex align-items-center mb-2">
                                    ${statusIcon}
                                    <h6 class="mb-0 me-2">Commande #${notification.order_id || 'N/A'}</h6>
                                    ${statusBadge}
                                </div>
                                <p class="text-muted mb-1">
                                    <i class="bi bi-building me-1"></i>
                                    <strong>Fournisseur:</strong> ${notification.supplier || 'Non spécifié'}
                                </p>
                                <p class="text-muted mb-0">
                                    <i class="bi bi-envelope me-1"></i>
                                    <strong>Email:</strong> ${notification.email}
                                </p>
                                ${notification.error ? `
                                    <div class="alert alert-danger mt-2 mb-0 py-1 px-2 small">
                                        <i class="bi bi-exclamation-triangle me-1"></i>
                                        ${notification.error}
                                    </div>
                                ` : ''}
                            </div>
                            <div class="col-md-4 text-md-end">
                                <small class="text-muted">
                                    <i class="bi bi-calendar me-1"></i>${dateStr}<br>
                                    <i class="bi bi-clock me-1"></i>${timeStr}
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
    }

    getStatusBadge(status) {
        const badges = {
            'sent': '<span class="badge bg-success">✅ Envoyé</span>',
            'failed': '<span class="badge bg-danger">❌ Échec</span>',
            'error': '<span class="badge bg-warning">⚠️ Erreur</span>'
        };
        return badges[status] || '<span class="badge bg-secondary">❓ Inconnu</span>';
    }

    getStatusIcon(status) {
        const icons = {
            'sent': '<i class="bi bi-check-circle-fill text-success me-2"></i>',
            'failed': '<i class="bi bi-x-circle-fill text-danger me-2"></i>',
            'error': '<i class="bi bi-exclamation-triangle-fill text-warning me-2"></i>'
        };
        return icons[status] || '<i class="bi bi-question-circle-fill text-secondary me-2"></i>';
    }

    showToast(message, type = 'info') {
        const toast = document.getElementById('notificationToast');
        const toastBody = document.getElementById('toastMessage');
        const toastHeader = toast.querySelector('.toast-header');
        
        if (!toast || !toastBody || !toastHeader) return;
        
        // Réinitialiser les classes
        toastHeader.className = 'toast-header';
        
        // Ajouter la classe selon le type
        switch (type) {
            case 'success':
                toastHeader.classList.add('bg-success', 'text-white');
                break;
            case 'error':
                toastHeader.classList.add('bg-danger', 'text-white');
                break;
            case 'warning':
                toastHeader.classList.add('bg-warning', 'text-dark');
                break;
            default:
                toastHeader.classList.add('bg-primary', 'text-white');
        }
        
        toastBody.textContent = message;
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }
}

// Fonctions globales pour les boutons
function togglePasswordVisibility() {
    const passwordInput = document.getElementById('emailPassword');
    const toggleIcon = document.getElementById('passwordToggleIcon');
    
    if (passwordInput && toggleIcon) {
        if (passwordInput.type === 'password') {
            passwordInput.type = 'text';
            toggleIcon.className = 'bi bi-eye-slash';
        } else {
            passwordInput.type = 'password';
            toggleIcon.className = 'bi bi-eye';
        }
    }
}

function testEmailConnection() {
    if (window.parametresManager) {
        window.parametresManager.testEmailConnection();
    }
}

function loadEmailConfig() {
    if (window.parametresManager) {
        window.parametresManager.loadEmailConfig();
    }
}

function loadNotifications() {
    if (window.parametresManager) {
        window.parametresManager.loadNotifications();
    }
}

// Initialiser quand le DOM est prêt
document.addEventListener('DOMContentLoaded', function() {
    window.parametresManager = new ParametresManager();
}); 