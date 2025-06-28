// ===== DASHBOARD CLIENT =====

let clientData = {
    restaurants: [],
    allUsers: []
};

let currentRestaurantId = null;

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    loadClientData();
});

// ===== CHARGEMENT DES DONNÉES =====

async function loadClientData() {
    try {
        await loadRestaurants();
        updateStatistics();
    } catch (error) {
        console.error('Erreur chargement données client:', error);
        showNotification('Erreur de chargement des données', 'error');
    }
}

async function loadRestaurants() {
    try {
        const response = await fetch('/api/client/restaurants');
        const result = await response.json();
        
        if (result.success) {
            clientData.restaurants = result.restaurants;
            displayRestaurants();
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        console.error('Erreur chargement restaurants:', error);
        document.getElementById('restaurantsList').innerHTML = 
            '<div class="alert alert-danger">Erreur de chargement des restaurants</div>';
    }
}

async function loadRestaurantUsers(restaurantId) {
    try {
        const response = await fetch(`/api/client/restaurant/${restaurantId}/users`);
        const result = await response.json();
        
        if (result.success) {
            return result.users;
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        console.error('Erreur chargement utilisateurs restaurant:', error);
        return [];
    }
}

// ===== AFFICHAGE DES DONNÉES =====

function displayRestaurants() {
    const container = document.getElementById('restaurantsList');
    
    if (clientData.restaurants.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-building display-4 text-muted"></i>
                <h5 class="text-muted mt-3">Aucun restaurant</h5>
                <p class="text-muted">Vos restaurants seront créés par l'administrateur</p>
            </div>
        `;
        return;
    }
    
    let html = '<div class="row">';
    
    clientData.restaurants.forEach(restaurant => {
        html += `
            <div class="col-md-6 col-lg-4 mb-4">
                <div class="card h-100 shadow-sm">
                    <div class="card-header bg-light">
                        <h6 class="mb-0">
                            <i class="bi bi-building me-2 text-info"></i>
                            ${restaurant.name}
                        </h6>
                    </div>
                    <div class="card-body">
                        <p class="text-muted small mb-2">
                            <i class="bi bi-geo-alt me-1"></i>
                            ${restaurant.address}
                        </p>
                        
                        ${restaurant.phone ? `
                            <p class="text-muted small mb-2">
                                <i class="bi bi-telephone me-1"></i>
                                ${restaurant.phone}
                            </p>
                        ` : ''}
                        
                        ${restaurant.email ? `
                            <p class="text-muted small mb-2">
                                <i class="bi bi-envelope me-1"></i>
                                ${restaurant.email}
                            </p>
                        ` : ''}
                        
                        <div class="mt-3">
                            <small class="text-muted">
                                <i class="bi bi-calendar me-1"></i>
                                Créé le ${formatDate(restaurant.created_at)}
                            </small>
                        </div>
                    </div>
                    <div class="card-footer bg-light">
                        <div class="d-grid">
                            <button class="btn btn-info btn-sm" onclick="manageRestaurantUsers('${restaurant.id}', '${restaurant.name}')">
                                <i class="bi bi-people me-1"></i>
                                Gérer les utilisateurs
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function displayRestaurantUsers(users) {
    const container = document.getElementById('usersList');
    
    if (users.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="bi bi-people display-4 text-muted"></i>
                <p class="text-muted mt-2">Aucun utilisateur dans ce restaurant</p>
                <small class="text-muted">Cliquez sur "Ajouter un utilisateur" pour commencer</small>
            </div>
        `;
        return;
    }
    
    let html = '<div class="table-responsive">';
    html += '<table class="table table-hover">';
    html += '<thead><tr><th>Utilisateur</th><th>Rôle</th><th>Email</th><th>Status</th><th>Actions</th></tr></thead>';
    html += '<tbody>';
    
    users.forEach(user => {
        const roleNames = {
            'admin': 'Admin Restaurant',
            'user': 'Utilisateur'
        };
        
        const roleBadges = {
            'admin': 'bg-success',
            'user': 'bg-secondary'
        };
        
        const roleIcons = {
            'admin': 'bi-shield-check',
            'user': 'bi-person'
        };
        
        html += `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <i class="bi ${roleIcons[user.role]} me-2 text-muted"></i>
                        <div>
                            <strong>${user.name}</strong>
                            <br><small class="text-muted">@${user.username}</small>
                        </div>
                    </div>
                </td>
                <td>
                    <span class="badge ${roleBadges[user.role]}">
                        ${roleNames[user.role]}
                    </span>
                </td>
                <td>
                    <a href="mailto:${user.email}">${user.email}</a>
                </td>
                <td>
                    <span class="badge ${user.active ? 'bg-success' : 'bg-danger'}">
                        ${user.active ? 'Actif' : 'Inactif'}
                    </span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="editUser('${user.id}')" disabled>
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-outline-danger" onclick="deleteUser('${user.id}')" disabled>
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                    <small class="text-muted d-block">Bientôt disponible</small>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// ===== GESTION DES UTILISATEURS =====

async function manageRestaurantUsers(restaurantId, restaurantName) {
    currentRestaurantId = restaurantId;
    
    // Mettre à jour le titre du modal
    document.getElementById('modalRestaurantName').textContent = restaurantName;
    
    // Charger les utilisateurs
    const users = await loadRestaurantUsers(restaurantId);
    displayRestaurantUsers(users);
    
    // Afficher le modal
    const modal = new bootstrap.Modal(document.getElementById('manageUsersModal'));
    modal.show();
}

function showAddUserForm() {
    document.getElementById('addUserForm').style.display = 'block';
    document.getElementById('createUserForm').reset();
}

function hideAddUserForm() {
    document.getElementById('addUserForm').style.display = 'none';
    document.getElementById('createUserForm').reset();
}

// Gestion du formulaire de création d'utilisateur
document.getElementById('createUserForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    if (!currentRestaurantId) {
        showNotification('Erreur: Restaurant non sélectionné', 'error');
        return;
    }
    
    try {
        const formData = {
            name: document.getElementById('newUserName').value,
            username: document.getElementById('newUserUsername').value,
            email: document.getElementById('newUserEmail').value,
            password: document.getElementById('newUserPassword').value,
            role: document.getElementById('newUserRole').value
        };
        
        const response = await fetch(`/api/client/restaurant/${currentRestaurantId}/users`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Utilisateur créé avec succès', 'success');
            hideAddUserForm();
            
            // Recharger la liste des utilisateurs
            const users = await loadRestaurantUsers(currentRestaurantId);
            displayRestaurantUsers(users);
            
            // Mettre à jour les statistiques
            loadClientData();
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        console.error('Erreur création utilisateur:', error);
        showNotification('Erreur lors de la création de l\'utilisateur: ' + error.message, 'error');
    }
});

// ===== STATISTIQUES =====

async function updateStatistics() {
    try {
        // Compter les restaurants
        const totalRestaurants = clientData.restaurants.length;
        document.getElementById('totalRestaurants').textContent = totalRestaurants;
        
        // Charger tous les utilisateurs pour les statistiques
        let allUsers = [];
        for (const restaurant of clientData.restaurants) {
            const users = await loadRestaurantUsers(restaurant.id);
            allUsers = allUsers.concat(users);
        }
        
        clientData.allUsers = allUsers;
        
        // Compter les utilisateurs par rôle
        const totalUsers = allUsers.length;
        const totalAdmins = allUsers.filter(u => u.role === 'admin').length;
        const totalRegularUsers = allUsers.filter(u => u.role === 'user').length;
        
        document.getElementById('totalUsers').textContent = totalUsers;
        document.getElementById('totalAdmins').textContent = totalAdmins;
        document.getElementById('totalRegularUsers').textContent = totalRegularUsers;
        
    } catch (error) {
        console.error('Erreur calcul statistiques:', error);
    }
}

// ===== FONCTIONS UTILITAIRES =====

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// ===== FONCTIONS PLACEHOLDER =====

function editUser(userId) {
    showNotification('Fonction d\'édition en cours de développement', 'warning');
}

function deleteUser(userId) {
    showNotification('Fonction de suppression en cours de développement', 'warning');
}