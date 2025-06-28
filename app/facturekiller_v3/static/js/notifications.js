// FactureKiller V3 - Système de notifications

// Fonction de notification globale
function showNotification(message, type = 'info', duration = 5000) {
    const toast = document.getElementById('notificationToast');
    if (!toast) return;
    
    const toastBody = toast.querySelector('.toast-body');
    const toastIcon = toast.querySelector('.toast-header i');
    const toastTitle = toast.querySelector('.toast-header strong');
    
    if (!toastBody || !toastIcon || !toastTitle) return;
    
    toastBody.textContent = message;
    
    // Configuration selon le type
    const configs = {
        success: {
            icon: 'bi-check-circle-fill text-success',
            title: 'Succès'
        },
        error: {
            icon: 'bi-x-circle-fill text-danger',
            title: 'Erreur'
        },
        warning: {
            icon: 'bi-exclamation-triangle-fill text-warning',
            title: 'Attention'
        },
        info: {
            icon: 'bi-info-circle-fill text-primary',
            title: 'Information'
        }
    };
    
    const config = configs[type] || configs.info;
    
    // Mettre à jour l'icône et le titre
    toastIcon.className = `bi ${config.icon} me-2`;
    toastTitle.textContent = config.title;
    
    // Afficher le toast
    const bsToast = new bootstrap.Toast(toast, {
        delay: duration
    });
    bsToast.show();
}

// Fonction pour afficher une notification de confirmation
function showConfirmNotification(message, onConfirm, onCancel = null) {
    const result = confirm(message);
    if (result && onConfirm) {
        onConfirm();
    } else if (!result && onCancel) {
        onCancel();
    }
    return result;
}

// Fonction pour afficher une notification de chargement
function showLoadingNotification(message = 'Chargement en cours...') {
    showNotification(message, 'info', 10000);
}

// Fonction pour masquer toutes les notifications
function hideAllNotifications() {
    const toasts = document.querySelectorAll('.toast');
    toasts.forEach(toast => {
        const bsToast = bootstrap.Toast.getInstance(toast);
        if (bsToast) {
            bsToast.hide();
        }
    });
}

// Export pour utilisation globale
window.showNotification = showNotification;
window.showConfirmNotification = showConfirmNotification;
window.showLoadingNotification = showLoadingNotification;
window.hideAllNotifications = hideAllNotifications; 