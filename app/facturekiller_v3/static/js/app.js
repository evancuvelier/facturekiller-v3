// FactureKiller V3 - JavaScript principal

// Configuration API
const API_BASE = '';

// Utilitaires
const Utils = {
    // Formater un montant en euros
    formatCurrency: (amount) => {
        if (!amount) return '0,00 €';
        return new Intl.NumberFormat('fr-FR', {
            style: 'currency',
            currency: 'EUR'
        }).format(amount);
    },

    // Formater une date
    formatDate: (dateString) => {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return new Intl.DateTimeFormat('fr-FR').format(date);
    },

    // Formater une date avec heure
    formatDateTime: (dateString) => {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return new Intl.DateTimeFormat('fr-FR', {
            dateStyle: 'short',
            timeStyle: 'short'
        }).format(date);
    },

    // Créer un badge de statut
    createStatusBadge: (status) => {
        const badges = {
            'ok': '<span class="badge bg-success">OK</span>',
            'warning': '<span class="badge bg-warning">Attention</span>',
            'error': '<span class="badge bg-danger">Erreur</span>',
            'overprice': '<span class="badge bg-danger">Surcoût</span>',
            'savings': '<span class="badge bg-success">Économie</span>',
            'new': '<span class="badge bg-info">Nouveau</span>',
            'pending': '<span class="badge bg-warning">En attente</span>',
            'validated': '<span class="badge bg-success">Validé</span>'
        };
        return badges[status] || `<span class="badge bg-secondary">${status}</span>`;
    },

    // Débounce pour les recherches
    debounce: (func, wait) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Afficher un loader
    showLoader: (elementId) => {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <div class="text-center py-5">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Chargement...</span>
                    </div>
                </div>
            `;
        }
    },

    // Créer la pagination
    createPagination: (containerId, currentPage, totalPages, onPageChange) => {
        const container = document.getElementById(containerId);
        if (!container) return;

        let html = '';
        
        // Previous
        html += `
            <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${currentPage - 1}">
                    <i class="bi bi-chevron-left"></i>
                </a>
            </li>
        `;

        // Pages
        const maxVisible = 5;
        let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
        let endPage = Math.min(totalPages, startPage + maxVisible - 1);

        if (endPage - startPage < maxVisible - 1) {
            startPage = Math.max(1, endPage - maxVisible + 1);
        }

        if (startPage > 1) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="1">1</a></li>`;
            if (startPage > 2) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            html += `
                <li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" data-page="${i}">${i}</a>
                </li>
            `;
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${totalPages}">${totalPages}</a></li>`;
        }

        // Next
        html += `
            <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${currentPage + 1}">
                    <i class="bi bi-chevron-right"></i>
                </a>
            </li>
        `;

        container.innerHTML = html;

        // Event listeners
        container.querySelectorAll('a.page-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = parseInt(e.currentTarget.dataset.page);
                if (page && page !== currentPage) {
                    onPageChange(page);
                }
            });
        });
    }
};

// API Helper
const API = {
    // Requête GET
    get: async (endpoint, params = {}) => {
        try {
            const url = new URL(`${API_BASE}${endpoint}`, window.location.origin);
            Object.keys(params).forEach(key => {
                if (params[key] !== undefined && params[key] !== '') {
                    url.searchParams.append(key, params[key]);
                }
            });

            const response = await fetch(url);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Erreur serveur');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            showNotification(error.message, 'error');
            throw error;
        }
    },

    // Requête POST
    post: async (endpoint, body, isFormData = false) => {
        try {
            const options = {
                method: 'POST',
                headers: {}
            };

            if (isFormData) {
                options.body = body;
            } else {
                options.headers['Content-Type'] = 'application/json';
                options.body = JSON.stringify(body);
            }

            const response = await fetch(`${API_BASE}${endpoint}`, options);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Erreur serveur');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            showNotification(error.message, 'error');
            throw error;
        }
    },

    // Requête PUT
    put: async (endpoint, body) => {
        try {
            const response = await fetch(`${API_BASE}${endpoint}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(body)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Erreur serveur');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            showNotification(error.message, 'error');
            throw error;
        }
    },

    // Requête DELETE
    delete: async (endpoint) => {
        try {
            const response = await fetch(`${API_BASE}${endpoint}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Erreur serveur');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            showNotification(error.message, 'error');
            throw error;
        }
    }
};

// Export pour utilisation dans d'autres modules
window.Utils = Utils;
window.API = API;

// Fonction de notification globale
function showNotification(message, type = 'info') {
    // Créer la notification
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-supprimer après 5 secondes
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Export global
window.showNotification = showNotification;

// ===== APPLICATION PRINCIPALE =====

// Variables globales
// currentUser, loadUserInfo, logout sont déclarés dans base.html
let appConfig = {
    apiBaseUrl: '/api',
    uploadMaxSize: 10 * 1024 * 1024, // 10MB
    supportedFormats: ['image/jpeg', 'image/png', 'image/webp', 'application/pdf']
};

// ===== INITIALISATION =====

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

async function initializeApp() {
    try {
        // Vérifier la santé de l'API
        await checkApiHealth();
        
        // Les informations utilisateur sont chargées par base.html
        
        // Initialiser les composants
        initializeComponents();
        
        console.log('✅ Application app.js initialisée avec succès');
    } catch (error) {
        console.error('❌ Erreur initialisation application:', error);
        showNotification('Erreur d\'initialisation de l\'application', 'error');
    }
}

// ===== GESTION UTILISATEUR =====
// Les fonctions loadUserInfo et updateUserInterface sont dans base.html

function updateContextInfo() {
    const contextInfo = document.getElementById('userContextInfo');
    if (!contextInfo) return;
    
    let contextHtml = '';
    
    if (currentUser && currentUser.client) {
        contextHtml += `
            <li class="dropdown-item-text">
                <small class="text-muted">Client:</small><br>
                <strong>${currentUser.client.name}</strong>
            </li>
        `;
    }
    
    if (currentUser && currentUser.restaurant) {
        contextHtml += `
            <li class="dropdown-item-text">
                <small class="text-muted">Restaurant:</small><br>
                <strong>${currentUser.restaurant.name}</strong>
            </li>
        `;
    }
    
    if (currentUser && currentUser.restaurants && currentUser.restaurants.length > 1) {
        contextHtml += `
            <li class="dropdown-item-text">
                <small class="text-muted">${currentUser.restaurants.length} restaurants gérés</small>
            </li>
        `;
    }
    
    contextInfo.innerHTML = contextHtml;
}

function hasUserPermission(requiredRole) {
    if (!currentUser || !currentUser.user) return false;
    
    const roleHierarchy = {
        'master_admin': 4,
        'client': 3,
        'admin': 2,
        'user': 1
    };
    
    const userLevel = roleHierarchy[currentUser.user.role] || 0;
    const requiredLevel = roleHierarchy[requiredRole] || 0;
    
    return userLevel >= requiredLevel;
}

// ===== GESTION API =====

async function checkApiHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        
        if (!data.services?.ocr) {
            showNotification('⚠️ Service OCR non disponible', 'warning');
        }
        
        return data;
    } catch (error) {
        showNotification('❌ Erreur de connexion au serveur', 'error');
        throw error;
    }
}

async function apiRequest(endpoint, options = {}) {
    try {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };
        
        const response = await fetch(`${appConfig.apiBaseUrl}${endpoint}`, defaultOptions);
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || `Erreur HTTP ${response.status}`);
        }
        
        return result;
    } catch (error) {
        console.error(`Erreur API ${endpoint}:`, error);
        throw error;
    }
}

// ===== GESTION FICHIERS =====

function validateFile(file) {
    // Vérifier le type
    if (!appConfig.supportedFormats.includes(file.type)) {
        throw new Error('Format de fichier non supporté');
    }
    
    // Vérifier la taille
    if (file.size > appConfig.uploadMaxSize) {
        throw new Error('Fichier trop volumineux (max 10MB)');
    }
    
    return true;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// ===== UTILITAIRES =====

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('fr-FR', {
        style: 'currency',
        currency: 'EUR'
    }).format(amount);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

// ===== COMPOSANTS =====

function initializeComponents() {
    // Initialiser les tooltips Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialiser les popovers Bootstrap
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Initialiser les formulaires avec validation
    initializeFormValidation();
}

function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
}

// ===== DÉCONNEXION =====
// La fonction logout est définie dans base.html

// ===== EXPORTS GLOBAUX =====

// currentUser, loadUserInfo, logout sont déjà exportés par base.html
window.updateContextInfo = updateContextInfo;
window.hasUserPermission = hasUserPermission;
window.apiRequest = apiRequest;
window.validateFile = validateFile;
window.formatFileSize = formatFileSize;
window.formatDate = formatDate;
window.formatCurrency = formatCurrency;
window.debounce = debounce;
window.throttle = throttle; 