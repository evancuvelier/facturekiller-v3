// Dashboard FactureKiller V3

let spendingChart = null;
let supplierChart = null;

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 Initialisation Dashboard FactureKiller...');
    loadDashboardStats();
    
    // Recharger toutes les 5 minutes
    setInterval(loadDashboardStats, 5 * 60 * 1000);
});

// Charger les statistiques du dashboard
async function loadDashboardStats() {
    try {
        console.log('📊 Chargement statistiques dashboard...');
        
        const response = await fetch('/api/stats/dashboard');
        const result = await response.json();
        
        if (result.success) {
            updateDashboardUI(result.data);
        } else {
            console.error('❌ Erreur données dashboard:', result.error);
            showErrorState();
        }
    } catch (error) {
        console.error('❌ Erreur chargement dashboard:', error);
        showErrorState();
    }
}

// Mettre à jour l'interface utilisateur
function updateDashboardUI(stats) {
    console.log('🔄 Mise à jour interface dashboard:', stats);
    
    // Cartes de statistiques
    updateStatsCards(stats);
    
    // Graphiques
    updateSpendingChart(stats.spending_chart_data);
    updateSupplierChart(stats.supplier_chart_data);
    
    // Listes d'activité
    updateAlertsList(stats.recent_alerts);
    updateActivityList(stats.recent_activity);
}

// Mettre à jour les cartes de statistiques
function updateStatsCards(stats) {
    // Factures ce mois
    const invoicesCount = document.getElementById('invoicesCount');
    const invoicesGrowth = document.getElementById('invoicesGrowth');
    
    if (invoicesCount) {
        invoicesCount.textContent = stats.invoices_count || 0;
    }
    
    if (invoicesGrowth) {
        const growth = stats.invoices_growth || 0;
        invoicesGrowth.textContent = growth;
        
        // Couleur selon la croissance
        const parentElement = invoicesGrowth.closest('.text-success, .text-danger, .text-muted');
        if (parentElement) {
            parentElement.className = growth > 0 ? 'text-success' : growth < 0 ? 'text-danger' : 'text-muted';
        }
    }
    
    // Économies réalisées
    const savingsAmount = document.getElementById('savingsAmount');
    const comparedProducts = document.getElementById('comparedProducts');
    
    if (savingsAmount) {
        const savings = stats.savings_amount || 0;
        savingsAmount.textContent = `${savings.toFixed(2)}€`;
    }
    
    if (comparedProducts) {
        comparedProducts.textContent = stats.compared_products || 0;
    }
    
    // Alertes prix
    const alertsCount = document.getElementById('alertsCount');
    const criticalAlerts = document.getElementById('criticalAlerts');
    
    if (alertsCount) {
        alertsCount.textContent = stats.alerts_count || 0;
    }
    
    if (criticalAlerts) {
        criticalAlerts.textContent = stats.critical_alerts || 0;
    }
    
    // Produits en attente
    const pendingCount = document.getElementById('pendingCount');
    
    if (pendingCount) {
        pendingCount.textContent = stats.pending_count || 0;
    }
}

// Mettre à jour le graphique des dépenses
function updateSpendingChart(chartData) {
    const canvas = document.getElementById('spendingChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Détruire le graphique existant
    if (spendingChart) {
        spendingChart.destroy();
    }
    
    spendingChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.labels || [],
            datasets: [{
                label: 'Dépenses (€)',
                data: chartData.data || [],
                borderColor: '#0d6efd',
                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#0d6efd',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: '#0d6efd',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            return `Dépenses: ${context.parsed.y.toFixed(2)}€`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#6c757d'
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    },
                    ticks: {
                        color: '#6c757d',
                        callback: function(value) {
                            return value.toFixed(0) + '€';
                        }
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

// Mettre à jour le graphique des fournisseurs
function updateSupplierChart(chartData) {
    const canvas = document.getElementById('supplierChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Détruire le graphique existant
    if (supplierChart) {
        supplierChart.destroy();
    }
    
    // Couleurs pour le graphique en secteurs
    const colors = [
        '#0d6efd', '#28a745', '#ffc107', '#dc3545', '#6f42c1',
        '#fd7e14', '#20c997', '#e83e8c', '#6c757d', '#17a2b8'
    ];
    
    supplierChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: chartData.labels || [],
            datasets: [{
                data: chartData.data || [],
                backgroundColor: colors.slice(0, chartData.labels?.length || 0),
                borderColor: '#ffffff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        usePointStyle: true,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: '#0d6efd',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${context.label}: ${context.parsed.toFixed(2)}€ (${percentage}%)`;
                        }
                    }
                }
            },
            cutout: '60%'
        }
    });
}

// Mettre à jour la liste des alertes
function updateAlertsList(alerts) {
    const alertsList = document.getElementById('alertsList');
    if (!alertsList) return;
    
    if (!alerts || alerts.length === 0) {
        alertsList.innerHTML = `
            <div class="text-center text-muted py-3">
                <i class="bi bi-check-circle-fill fs-2 text-success"></i>
                <p class="mt-2 mb-0">Aucune alerte récente</p>
                <small>Tous vos prix sont optimaux !</small>
            </div>
        `;
        return;
    }
    
    alertsList.innerHTML = alerts.map(alert => `
        <div class="list-group-item border-0 px-0">
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1">
                    <h6 class="mb-1 text-danger">
                        <i class="bi bi-exclamation-triangle-fill me-2"></i>
                        ${alert.supplier}
                    </h6>
                    <p class="mb-1 small text-muted">
                        ${alert.alert_count} produit(s) plus cher(s) que la référence
                    </p>
                    <small class="text-danger">
                        Surcoût: +${alert.overpayment?.toFixed(2) || 0}€
                    </small>
                </div>
                <small class="text-muted">
                    ${formatDate(alert.date)}
                </small>
            </div>
        </div>
    `).join('');
}

// Mettre à jour la liste d'activité
function updateActivityList(activities) {
    const activityList = document.getElementById('activityList');
    if (!activityList) return;
    
    if (!activities || activities.length === 0) {
        activityList.innerHTML = `
            <div class="text-center text-muted py-3">
                <i class="bi bi-clock-history fs-2"></i>
                <p class="mt-2 mb-0">Aucune activité récente</p>
            </div>
        `;
        return;
    }
    
    activityList.innerHTML = activities.map(activity => {
        const iconClass = activity.icon === 'file-text' ? 'bi-file-text-fill text-primary' : 'bi-clock-history text-warning';
        
        return `
            <div class="list-group-item border-0 px-0">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="d-flex align-items-center mb-1">
                            <i class="bi ${iconClass} me-2"></i>
                            <h6 class="mb-0">${activity.title}</h6>
                        </div>
                        <p class="mb-0 small text-muted">
                            ${activity.description}
                        </p>
                    </div>
                    <small class="text-muted">
                        ${formatDate(activity.date)}
                    </small>
                </div>
            </div>
        `;
    }).join('');
}

// Afficher l'état d'erreur
function showErrorState() {
    // Mettre des valeurs par défaut
    const elements = [
        'invoicesCount', 'savingsAmount', 'alertsCount', 'pendingCount'
    ];
    
    elements.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = '-';
        }
    });
    
    // Messages d'erreur dans les listes
    const alertsList = document.getElementById('alertsList');
    const activityList = document.getElementById('activityList');
    
    const errorMessage = `
        <div class="text-center text-danger py-3">
            <i class="bi bi-exclamation-triangle fs-2"></i>
            <p class="mt-2 mb-0">Erreur de chargement</p>
            <small>Impossible de récupérer les données</small>
        </div>
    `;
    
    if (alertsList) alertsList.innerHTML = errorMessage;
    if (activityList) activityList.innerHTML = errorMessage;
}

// Formater une date
function formatDate(dateString) {
    if (!dateString) return '-';
    
    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays === 1) {
            return 'Aujourd\'hui';
        } else if (diffDays === 2) {
            return 'Hier';
        } else if (diffDays <= 7) {
            return `Il y a ${diffDays - 1} jours`;
        } else {
            return date.toLocaleDateString('fr-FR', {
                day: 'numeric',
                month: 'short'
            });
        }
    } catch (e) {
        return '-';
    }
}

// Recharger manuellement
window.reloadDashboard = function() {
    loadDashboardStats();
}; 
}; 