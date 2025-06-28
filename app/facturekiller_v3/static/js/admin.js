// ===== VARIABLES GLOBALES =====
let adminData = {
    clients: [],
    restaurants: [],
    users: []
};

// ===== INITIALISATION =====

function isAdminPage() {
    return window.location.pathname.includes('/admin');
}

document.addEventListener('DOMContentLoaded', function() {
    if (isAdminPage()) {
        console.log('🔧 Initialisation page admin');
        loadAllData();
        loadConfig();
    }
});

// ===== CHARGEMENT DES DONNÉES =====

async function loadAllData() {
    try {
        await Promise.all([
            loadClients(),
            loadRestaurants(),
            loadUsers()
        ]);
        
        updateQuickStats();
        updateClientSelects();
        updateRestaurantSelects();
        
        console.log('✅ Données admin chargées');
    } catch (error) {
        console.error('Erreur chargement données admin:', error);
    }
}

async function loadClients() {
    try {
        const response = await fetch('/api/admin/clients', {
            credentials: 'include'
        });
        const data = await response.json();
        
        if (data.success) {
            adminData.clients = data.data;
            displayClients();
        }
    } catch (error) {
        console.error('Erreur chargement clients:', error);
    }
}

async function loadRestaurants() {
    try {
        const response = await fetch('/api/admin/restaurants', {
            credentials: 'include'
        });
        const data = await response.json();
        
        if (data.success) {
            adminData.restaurants = data.data;
            displayRestaurants();
        }
    } catch (error) {
        console.error('Erreur chargement restaurants:', error);
    }
}

async function loadUsers() {
    try {
        const response = await fetch('/api/admin/users', {
            credentials: 'include'
        });
        const data = await response.json();
        
        if (data.success) {
            adminData.users = data.data;
            displayUsers();
        }
    } catch (error) {
        console.error('Erreur chargement utilisateurs:', error);
    }
}

// ===== AFFICHAGE DES DONNÉES =====

function displayClients() {
    const container = document.getElementById('clientsList');
    if (!container) {
        console.log('🚫 Élément clientsList non trouvé, affichage ignoré');
        return;
    }
    
    if (adminData.clients.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="bi bi-person-badge display-4 text-muted"></i>
                <p class="text-muted mt-2">Aucun client créé</p>
            </div>
        `;
        return;
    }
    
    let html = '<div class="table-responsive">';
    html += '<table class="table table-hover">';
    html += '<thead><tr><th>Client</th><th>Contact</th><th>Restaurants</th><th>Status</th><th>Actions</th></tr></thead>';
    html += '<tbody>';
    
    adminData.clients.forEach(client => {
        const clientRestaurants = adminData.restaurants.filter(r => r.client_id === client.id);
        
        html += `
            <tr>
                <td>
                    <strong>${client.name}</strong>
                    <br><small class="text-muted">ID: ${client.id}</small>
                </td>
                <td>
                    <strong>${client.contact_name}</strong><br>
                    <a href="mailto:${client.email}">${client.email}</a><br>
                    ${client.phone ? `<small>${client.phone}</small>` : ''}
                </td>
                <td>
                    <span class="badge bg-info">${clientRestaurants.length} restaurant(s)</span>
                    ${clientRestaurants.map(r => `<br><small class="text-muted">${r.name}</small>`).join('')}
                </td>
                <td>
                    <span class="badge ${client.active ? 'bg-success' : 'bg-danger'}">
                        ${client.active ? 'Actif' : 'Inactif'}
                    </span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="editClient('${client.id}')">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-outline-danger" onclick="deleteClient('${client.id}')">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

function displayRestaurants() {
    const container = document.getElementById('restaurantsList');
    if (!container) {
        console.log('🚫 Élément restaurantsList non trouvé, affichage ignoré');
        return;
    }
    
    if (adminData.restaurants.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="bi bi-building display-4 text-muted"></i>
                <p class="text-muted mt-2">Aucun restaurant créé</p>
            </div>
        `;
        return;
    }
    
    let html = '<div class="table-responsive">';
    html += '<table class="table table-hover">';
    html += '<thead><tr><th>Restaurant</th><th>Client</th><th>Fournisseurs</th><th>Contact</th><th>Actions</th></tr></thead>';
    html += '<tbody>';
    
    adminData.restaurants.forEach(restaurant => {
        const client = adminData.clients.find(c => c.id === restaurant.client_id);
        const suppliers = restaurant.suppliers || [];
        
        html += `
            <tr>
                <td>
                    <strong>${restaurant.name}</strong>
                    <br><small class="text-muted">ID: ${restaurant.id}</small>
                </td>
                <td>${client ? client.name : 'Client introuvable'}</td>
                <td>
                    <div class="d-flex flex-wrap gap-1 mb-2">
                        ${suppliers.map(supplier => 
                            `<span class="badge bg-primary">${supplier}</span>`
                        ).join('')}
                        ${suppliers.length === 0 ? '<small class="text-muted">Aucun fournisseur</small>' : ''}
                    </div>
                    <button class="btn btn-sm btn-outline-primary" onclick="manageRestaurantSuppliers('${restaurant.id}')">
                        <i class="bi bi-truck me-1"></i>Gérer (${suppliers.length})
                    </button>
                </td>
                <td>
                    ${restaurant.email ? `<a href="mailto:${restaurant.email}">${restaurant.email}</a><br>` : ''}
                    ${restaurant.phone ? `<small>${restaurant.phone}</small>` : ''}
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-success" onclick="editRestaurant('${restaurant.id}')">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-outline-danger" onclick="deleteRestaurant('${restaurant.id}')">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

function displayUsers() {
    const container = document.getElementById('usersList');
    if (!container) {
        console.log('🚫 Élément usersList non trouvé, affichage ignoré');
        return;
    }
    
    if (adminData.users.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="bi bi-person-gear display-4 text-muted"></i>
                <p class="text-muted mt-2">Aucun utilisateur créé</p>
            </div>
        `;
        return;
    }
    
    let html = '<div class="table-responsive">';
    html += '<table class="table table-hover">';
    html += '<thead><tr><th>Utilisateur</th><th>Rôle</th><th>Client/Restaurant</th><th>Status</th><th>Actions</th></tr></thead>';
    html += '<tbody>';
    
    adminData.users.forEach(user => {
        const client = user.client_id ? adminData.clients.find(c => c.id === user.client_id) : null;
        const restaurant = user.restaurant_id ? adminData.restaurants.find(r => r.id === user.restaurant_id) : null;
        
        const roleNames = {
            'master_admin': 'Master Admin',
            'client': 'Client',
            'admin': 'Admin',
            'user': 'Utilisateur'
        };
        
        const roleBadges = {
            'master_admin': 'bg-warning text-dark',
            'client': 'bg-info',
            'admin': 'bg-success',
            'user': 'bg-secondary'
        };
        
        html += `
            <tr>
                <td>
                    <strong>${user.name}</strong>
                    <br><small class="text-muted">@${user.username} • ${user.email}</small>
                </td>
                <td>
                    <span class="badge ${roleBadges[user.role]}">${roleNames[user.role]}</span>
                </td>
                <td>
                    ${client ? `<strong>Client:</strong> ${client.name}<br>` : ''}
                    ${restaurant ? `<strong>Restaurant:</strong> ${restaurant.name}` : ''}
                    ${!client && !restaurant ? '<small class="text-muted">Aucune affectation</small>' : ''}
                </td>
                <td>
                    <span class="badge ${user.active ? 'bg-success' : 'bg-danger'}">
                        ${user.active ? 'Actif' : 'Inactif'}
                    </span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-warning" onclick="editUser('${user.id}')">
                            <i class="bi bi-pencil"></i>
                        </button>
                        ${user.role !== 'master_admin' ? `
                            <button class="btn btn-outline-danger" onclick="deleteUser('${user.id}')">
                                <i class="bi bi-trash"></i>
                            </button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// ===== CRÉATION D'ENTITÉS =====

function showCreateClientModal() {
    const modal = new bootstrap.Modal(document.getElementById('createClientModal'));
    document.getElementById('createClientForm').reset();
    resetClientModal();
    modal.show();
}

function showCreateRestaurantModal() {
    const modal = new bootstrap.Modal(document.getElementById('createRestaurantModal'));
    document.getElementById('createRestaurantForm').reset();
    resetRestaurantModal();
    updateClientSelects();
    modal.show();
}

function showCreateUserModal() {
    const modal = new bootstrap.Modal(document.getElementById('createUserModal'));
    document.getElementById('createUserForm').reset();
    resetUserModal();
    updateClientSelects();
    updateRestaurantSelects();
    modal.show();
}

async function createClient() {
    try {
        const formData = {
            name: document.getElementById('clientName').value,
            email: document.getElementById('clientEmail').value,
            contact_name: document.getElementById('clientContactName').value,
            phone: document.getElementById('clientPhone').value
        };
        
        const response = await fetch('/api/admin/clients', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            let message = 'Client créé avec succès';
            
            if (result.invitation_sent) {
                if (result.simulated) {
                    message += ' 📧 Invitation simulée (configuration email manquante)';
                } else {
                    message += ' 📧 Invitation envoyée par email';
                }
            } else {
                message += ' ⚠️ Erreur envoi invitation: ' + result.email_message;
            }
            
            showNotification(message, 'success');
            bootstrap.Modal.getInstance(document.getElementById('createClientModal')).hide();
            document.getElementById('createClientForm').reset();
            loadClients();
            updateQuickStats();
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        console.error('Erreur création client:', error);
        showNotification('Erreur lors de la création du client: ' + error.message, 'error');
    }
}

async function createRestaurant() {
    try {
        const formData = {
            client_id: document.getElementById('restaurantClient').value,
            name: document.getElementById('restaurantName').value,
            address: document.getElementById('restaurantAddress').value,
            phone: document.getElementById('restaurantPhone').value,
            email: document.getElementById('restaurantEmail').value
        };
        
        const response = await fetch('/api/admin/restaurants', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Restaurant créé avec succès', 'success');
            bootstrap.Modal.getInstance(document.getElementById('createRestaurantModal')).hide();
            loadRestaurants();
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        console.error('Erreur création restaurant:', error);
        showNotification('Erreur lors de la création du restaurant: ' + error.message, 'error');
    }
}

async function createUser() {
    try {
        const formData = {
            name: document.getElementById('userName').value,
            username: document.getElementById('userUsername').value,
            email: document.getElementById('userEmail').value,
            password: document.getElementById('userPassword').value,
            role: document.getElementById('userRole').value,
            client_id: document.getElementById('userClient').value || null,
            restaurant_id: document.getElementById('userRestaurant').value || null
        };
        
        const response = await fetch('/api/admin/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Utilisateur créé avec succès', 'success');
            bootstrap.Modal.getInstance(document.getElementById('createUserModal')).hide();
            loadUsers();
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        console.error('Erreur création utilisateur:', error);
        showNotification('Erreur lors de la création de l\'utilisateur: ' + error.message, 'error');
    }
}

// ===== FONCTIONS UTILITAIRES =====

function updateClientSelects() {
    const selects = ['restaurantClient', 'userClient'];
    
    selects.forEach(selectId => {
        const select = document.getElementById(selectId);
        if (select) {
            const firstOption = select.children[0];
            select.innerHTML = '';
            select.appendChild(firstOption);
            
            adminData.clients.forEach(client => {
                const option = document.createElement('option');
                option.value = client.id;
                option.textContent = client.name;
                select.appendChild(option);
            });
        }
    });
}

function updateRestaurantSelects() {
    const select = document.getElementById('userRestaurant');
    if (select) {
        const firstOption = select.children[0];
        select.innerHTML = '';
        select.appendChild(firstOption);
        
        adminData.restaurants.forEach(restaurant => {
            const client = adminData.clients.find(c => c.id === restaurant.client_id);
            const option = document.createElement('option');
            option.value = restaurant.id;
            option.textContent = `${restaurant.name} (${client ? client.name : 'Client inconnu'})`;
            select.appendChild(option);
        });
    }
}

function updateUserFormFields() {
    const role = document.getElementById('userRole').value;
    const clientField = document.getElementById('userClientField');
    const restaurantField = document.getElementById('userRestaurantField');
    
    clientField.style.display = 'none';
    restaurantField.style.display = 'none';
    
    if (role === 'client') {
        // Les clients n'ont besoin d'aucune affectation spécifique
    } else if (role === 'admin' || role === 'user') {
        clientField.style.display = 'block';
        restaurantField.style.display = 'block';
    }
}

function updateQuickStats() {
    const clientsCount = adminData.clients.length;
    const restaurantsCount = adminData.restaurants.length;
    const usersCount = adminData.users.length;
    
    const statsClients = document.getElementById('statsClients');
    const statsRestaurants = document.getElementById('statsRestaurants');
    const statsUsers = document.getElementById('statsUsers');
    
    if (statsClients) statsClients.textContent = clientsCount;
    if (statsRestaurants) statsRestaurants.textContent = restaurantsCount;
    if (statsUsers) statsUsers.textContent = usersCount;
    
    const dashboardClients = document.getElementById('dashboardClients');
    const dashboardRestaurants = document.getElementById('dashboardRestaurants');
    const dashboardUsers = document.getElementById('dashboardUsers');
    const dashboardEmails = document.getElementById('dashboardEmails');
    
    if (dashboardClients) dashboardClients.textContent = clientsCount;
    if (dashboardRestaurants) dashboardRestaurants.textContent = restaurantsCount;
    if (dashboardUsers) dashboardUsers.textContent = usersCount;
    if (dashboardEmails) dashboardEmails.textContent = '1';
}

// ===== FONCTIONS DE SUPPRESSION =====

async function deleteClient(clientId) {
    if (confirm('Êtes-vous sûr de vouloir supprimer ce client ? Cela supprimera aussi tous ses restaurants et utilisateurs.')) {
        try {
            const response = await fetch(`/api/admin/clients/${clientId}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                showNotification(result.message, 'success');
                loadClients();
                updateQuickStats();
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('Erreur suppression client:', error);
            showNotification('Erreur lors de la suppression du client: ' + error.message, 'error');
        }
    }
}

async function deleteRestaurant(restaurantId) {
    if (confirm('Êtes-vous sûr de vouloir supprimer ce restaurant ?')) {
        try {
            const response = await fetch(`/api/admin/restaurants/${restaurantId}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                showNotification(result.message, 'success');
                loadRestaurants();
                updateQuickStats();
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('Erreur suppression restaurant:', error);
            showNotification('Erreur lors de la suppression du restaurant: ' + error.message, 'error');
        }
    }
}

async function deleteUser(userId) {
    if (confirm('Êtes-vous sûr de vouloir supprimer cet utilisateur ?')) {
        try {
            const response = await fetch(`/api/admin/users/${userId}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                showNotification(result.message, 'success');
                loadUsers();
                updateQuickStats();
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('Erreur suppression utilisateur:', error);
            showNotification('Erreur lors de la suppression de l\'utilisateur: ' + error.message, 'error');
        }
    }
}

// ===== FONCTIONS D'ÉDITION =====

function editClient(clientId) {
    const client = adminData.clients.find(c => c.id === clientId);
    if (!client) {
        showNotification('Client introuvable', 'error');
        return;
    }
    
    document.getElementById('clientName').value = client.name;
    document.getElementById('clientEmail').value = client.email;
    document.getElementById('clientContactName').value = client.contact_name;
    document.getElementById('clientPhone').value = client.phone || '';
    
    const modal = document.getElementById('createClientModal');
    const title = modal.querySelector('.modal-title');
    const button = modal.querySelector('button[onclick="createClient()"]');
    
    title.innerHTML = '<i class="bi bi-pencil me-2"></i>Modifier le Client';
    button.innerHTML = '<i class="bi bi-save me-1"></i>Modifier le Client';
    button.setAttribute('onclick', `updateClient('${clientId}')`);
    
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

function editRestaurant(restaurantId) {
    const restaurant = adminData.restaurants.find(r => r.id === restaurantId);
    if (!restaurant) {
        showNotification('Restaurant introuvable', 'error');
        return;
    }
    
    document.getElementById('restaurantClient').value = restaurant.client_id;
    document.getElementById('restaurantName').value = restaurant.name;
    document.getElementById('restaurantAddress').value = restaurant.address;
    document.getElementById('restaurantPhone').value = restaurant.phone || '';
    document.getElementById('restaurantEmail').value = restaurant.email || '';
    
    const modal = document.getElementById('createRestaurantModal');
    const title = modal.querySelector('.modal-title');
    const button = modal.querySelector('button[onclick="createRestaurant()"]');
    
    title.innerHTML = '<i class="bi bi-pencil me-2"></i>Modifier le Restaurant';
    button.innerHTML = '<i class="bi bi-save me-1"></i>Modifier le Restaurant';
    button.setAttribute('onclick', `updateRestaurant('${restaurantId}')`);
    
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

function editUser(userId) {
    const user = adminData.users.find(u => u.id === userId);
    if (!user) {
        showNotification('Utilisateur introuvable', 'error');
        return;
    }
    
    document.getElementById('userName').value = user.name;
    document.getElementById('userUsername').value = user.username;
    document.getElementById('userEmail').value = user.email;
    document.getElementById('userPassword').value = '';
    document.getElementById('userRole').value = user.role;
    document.getElementById('userClient').value = user.client_id || '';
    document.getElementById('userRestaurant').value = user.restaurant_id || '';
    
    updateUserFormFields();
    
    const modal = document.getElementById('createUserModal');
    const title = modal.querySelector('.modal-title');
    const button = modal.querySelector('button[onclick="createUser()"]');
    
    title.innerHTML = '<i class="bi bi-pencil me-2"></i>Modifier l\'Utilisateur';
    button.innerHTML = '<i class="bi bi-save me-1"></i>Modifier l\'Utilisateur';
    button.setAttribute('onclick', `updateUser('${userId}')`);
    
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

// ===== FONCTIONS DE MISE À JOUR =====

async function updateClient(clientId) {
    try {
        const formData = {
            name: document.getElementById('clientName').value,
            email: document.getElementById('clientEmail').value,
            contact_name: document.getElementById('clientContactName').value,
            phone: document.getElementById('clientPhone').value
        };
        
        const response = await fetch(`/api/admin/clients/${clientId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Client modifié avec succès', 'success');
            bootstrap.Modal.getInstance(document.getElementById('createClientModal')).hide();
            loadClients();
            resetClientModal();
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        console.error('Erreur modification client:', error);
        showNotification('Erreur lors de la modification du client: ' + error.message, 'error');
    }
}

async function updateRestaurant(restaurantId) {
    try {
        const formData = {
            client_id: document.getElementById('restaurantClient').value,
            name: document.getElementById('restaurantName').value,
            address: document.getElementById('restaurantAddress').value,
            phone: document.getElementById('restaurantPhone').value,
            email: document.getElementById('restaurantEmail').value
        };
        
        const response = await fetch(`/api/admin/restaurants/${restaurantId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Restaurant modifié avec succès', 'success');
            bootstrap.Modal.getInstance(document.getElementById('createRestaurantModal')).hide();
            loadRestaurants();
            resetRestaurantModal();
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        console.error('Erreur modification restaurant:', error);
        showNotification('Erreur lors de la modification du restaurant: ' + error.message, 'error');
    }
}

async function updateUser(userId) {
    try {
        const formData = {
            name: document.getElementById('userName').value,
            username: document.getElementById('userUsername').value,
            email: document.getElementById('userEmail').value,
            role: document.getElementById('userRole').value,
            client_id: document.getElementById('userClient').value || null,
            restaurant_id: document.getElementById('userRestaurant').value || null
        };
        
        const password = document.getElementById('userPassword').value;
        if (password) {
            formData.password = password;
        }
        
        const response = await fetch(`/api/admin/users/${userId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Utilisateur modifié avec succès', 'success');
            bootstrap.Modal.getInstance(document.getElementById('createUserModal')).hide();
            loadUsers();
            resetUserModal();
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        console.error('Erreur modification utilisateur:', error);
        showNotification('Erreur lors de la modification de l\'utilisateur: ' + error.message, 'error');
    }
}

// ===== FONCTIONS DE RESET =====

function resetClientModal() {
    const modal = document.getElementById('createClientModal');
    const title = modal.querySelector('.modal-title');
    const button = modal.querySelector('button[onclick*="Client"]');
    
    title.innerHTML = '<i class="bi bi-plus-circle me-2"></i>Nouveau Client';
    button.innerHTML = '<i class="bi bi-save me-1"></i>Créer le Client';
    button.setAttribute('onclick', 'createClient()');
}

function resetRestaurantModal() {
    const modal = document.getElementById('createRestaurantModal');
    const title = modal.querySelector('.modal-title');
    const button = modal.querySelector('button[onclick*="Restaurant"]');
    
    title.innerHTML = '<i class="bi bi-plus-circle me-2"></i>Nouveau Restaurant';
    button.innerHTML = '<i class="bi bi-save me-1"></i>Créer le Restaurant';
    button.setAttribute('onclick', 'createRestaurant()');
}

function resetUserModal() {
    const modal = document.getElementById('createUserModal');
    const title = modal.querySelector('.modal-title');
    const button = modal.querySelector('button[onclick*="User"]');
    
    title.innerHTML = '<i class="bi bi-plus-circle me-2"></i>Nouvel Utilisateur';
    button.innerHTML = '<i class="bi bi-save me-1"></i>Créer l\'Utilisateur';
    button.setAttribute('onclick', 'createUser()');
}

// ===== CONFIGURATION =====

async function loadConfig() {
    try {
        await loadAdminEmailConfig();
    } catch (error) {
        console.error('Erreur chargement config:', error);
    }
}

async function loadAdminEmailConfig() {
    try {
        const response = await fetch('/api/admin/email-config', {
            credentials: 'include'
        });
        const data = await response.json();
        
        if (data.success) {
            const config = data.data;
            
            if (config.email) document.getElementById('adminEmailAddress').value = config.email;
            if (config.password && config.password !== '***') {
                document.getElementById('adminEmailPassword').value = config.password;
            }
            if (config.smtp_server) document.getElementById('adminSmtpServer').value = config.smtp_server;
            if (config.sender_name) document.getElementById('adminSenderName').value = config.sender_name;
            if (config.enabled !== undefined) document.getElementById('adminEmailEnabled').checked = config.enabled;
            if (config.auto_send !== undefined) document.getElementById('adminAutoSend').checked = config.auto_send;
            
            const statusElement = document.getElementById('adminEmailStatus');
            if (statusElement) {
                if (config.email && config.password) {
                    statusElement.innerHTML = '<h6>📊 Statut :</h6><span class="badge bg-success">Configuré</span>';
                } else {
                    statusElement.innerHTML = '<h6>📊 Statut :</h6><span class="badge bg-warning">Non configuré</span>';
                }
            }
        }
    } catch (error) {
        console.error('Erreur chargement config email admin:', error);
    }
}

async function saveAdminEmailConfig() {
    try {
        const formData = {
            email: document.getElementById('adminEmailAddress').value,
            password: document.getElementById('adminEmailPassword').value,
            smtp_server: document.getElementById('adminSmtpServer').value,
            smtp_port: getSmtpPortFromServer(document.getElementById('adminSmtpServer').value),
            sender_name: document.getElementById('adminSenderName').value,
            enabled: document.getElementById('adminEmailEnabled').checked,
            auto_send: document.getElementById('adminAutoSend').checked
        };
        
        const response = await fetch('/api/admin/email-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Configuration email sauvegardée avec succès', 'success');
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        console.error('Erreur sauvegarde config email:', error);
        showNotification('Erreur lors de la sauvegarde: ' + error.message, 'error');
    }
}

async function testAdminEmailConnection() {
    try {
        const formData = {
            email: document.getElementById('adminEmailAddress').value,
            password: document.getElementById('adminEmailPassword').value,
            smtp_server: document.getElementById('adminSmtpServer').value,
            smtp_port: getSmtpPortFromServer(document.getElementById('adminSmtpServer').value),
            sender_name: document.getElementById('adminSenderName').value
        };
        
        // Vérifier que les champs requis sont remplis
        if (!formData.email || !formData.password) {
            showNotification('Veuillez remplir l\'adresse email et le mot de passe', 'warning');
            return;
        }
        
        const response = await fetch('/api/admin/test-email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('✅ Test de connexion réussi !', 'success');
        } else {
            showNotification('❌ Échec du test: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Erreur test email:', error);
        showNotification('Erreur lors du test: ' + error.message, 'error');
    }
}

// Fonction utilitaire pour obtenir le port SMTP selon le serveur
function getSmtpPortFromServer(server) {
    switch (server) {
        case 'smtp.gmail.com':
            return 587;
        case 'smtp.mail.yahoo.com':
            return 587;
        case 'smtp.outlook.com':
            return 587;
        default:
            return 587;
    }
}

// ===== GESTION DES FOURNISSEURS DE RESTAURANT =====

async function manageRestaurantSuppliers(restaurantId) {
    try {
        const restaurant = adminData.restaurants.find(r => r.id === restaurantId);
        if (!restaurant) {
            showNotification('Restaurant introuvable', 'error');
            return;
        }
        
        const response = await fetch('/api/suppliers');
        const data = await response.json();
        
        if (!data.success) {
            showNotification('Erreur lors du chargement des fournisseurs', 'error');
            return;
        }
        
        const allSuppliers = data.data;
        const restaurantSuppliers = restaurant.suppliers || [];
        
        const modalHtml = `
            <div class="modal fade" id="manageSuppliersModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title">
                                <i class="bi bi-truck me-2"></i>Fournisseurs - ${restaurant.name}
                            </h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <h6 class="text-success">
                                        <i class="bi bi-check-circle me-1"></i>Fournisseurs Actifs (${restaurantSuppliers.length})
                                    </h6>
                                    <div id="activeSuppliers" class="border rounded p-3 mb-3" style="min-height: 200px;">
                                        ${restaurantSuppliers.map(supplier => `
                                            <div class="d-flex justify-content-between align-items-center mb-2">
                                                <span class="badge bg-success">${supplier}</span>
                                                <button class="btn btn-sm btn-outline-danger" onclick="removeSupplierFromRestaurant('${restaurantId}', '${supplier}')">
                                                    <i class="bi bi-x"></i>
                                                </button>
                                            </div>
                                        `).join('')}
                                        ${restaurantSuppliers.length === 0 ? '<p class="text-muted">Aucun fournisseur actif</p>' : ''}
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <h6 class="text-info">
                                        <i class="bi bi-plus-circle me-1"></i>Fournisseurs Disponibles
                                    </h6>
                                    <div id="availableSuppliers" class="border rounded p-3" style="min-height: 200px;">
                                        ${allSuppliers.filter(s => !restaurantSuppliers.includes(s.name)).map(supplier => `
                                            <div class="d-flex justify-content-between align-items-center mb-2">
                                                <span class="badge bg-info">${supplier.name}</span>
                                                <button class="btn btn-sm btn-outline-success" onclick="addSupplierToRestaurant('${restaurantId}', '${supplier.name}')">
                                                    <i class="bi bi-plus"></i>
                                                </button>
                                            </div>
                                        `).join('')}
                                        ${allSuppliers.filter(s => !restaurantSuppliers.includes(s.name)).length === 0 ? '<p class="text-muted">Tous les fournisseurs sont déjà ajoutés</p>' : ''}
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fermer</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        const existingModal = document.getElementById('manageSuppliersModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = new bootstrap.Modal(document.getElementById('manageSuppliersModal'));
        modal.show();
        
        document.getElementById('manageSuppliersModal').addEventListener('hidden.bs.modal', function () {
            this.remove();
        });
        
    } catch (error) {
        console.error('Erreur gestion fournisseurs restaurant:', error);
        showNotification('Erreur lors de la gestion des fournisseurs: ' + error.message, 'error');
    }
}

async function addSupplierToRestaurant(restaurantId, supplierName) {
    try {
        const response = await fetch(`/api/admin/restaurants/${restaurantId}/suppliers`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ supplier_name: supplierName })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification(`Fournisseur ${supplierName} ajouté avec succès`, 'success');
            await loadRestaurants();
            bootstrap.Modal.getInstance(document.getElementById('manageSuppliersModal')).hide();
        } else {
            showNotification('Erreur: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Erreur ajout fournisseur:', error);
        showNotification('Erreur lors de l\'ajout du fournisseur: ' + error.message, 'error');
    }
}

async function removeSupplierFromRestaurant(restaurantId, supplierName) {
    if (confirm(`Êtes-vous sûr de vouloir retirer ${supplierName} de ce restaurant ?`)) {
        try {
            const response = await fetch(`/api/admin/restaurants/${restaurantId}/suppliers`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ supplier_name: supplierName })
            });
            
            const result = await response.json();
            
            if (result.success) {
                showNotification(`Fournisseur ${supplierName} retiré avec succès`, 'success');
                await loadRestaurants();
                bootstrap.Modal.getInstance(document.getElementById('manageSuppliersModal')).hide();
            } else {
                showNotification('Erreur: ' + result.error, 'error');
            }
        } catch (error) {
            console.error('Erreur suppression fournisseur:', error);
            showNotification('Erreur lors de la suppression du fournisseur: ' + error.message, 'error');
        }
    }
}

// ===== NOTIFICATIONS =====

function showNotification(message, type = 'info') {
    const alertClass = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    }[type] || 'alert-info';
    
    const notification = document.createElement('div');
    notification.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}