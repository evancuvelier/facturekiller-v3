/**
 * Version DEBUG de parametres.js pour diagnostiquer les problèmes
 */

console.log('🔧 Script parametres-debug.js chargé');

// Test de base
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 DOM prêt, initialisation...');
    
    // Test 1: Vérifier que les éléments existent
    const elements = {
        emailEnabled: document.getElementById('emailEnabled'),
        autoSend: document.getElementById('autoSend'), 
        senderName: document.getElementById('senderName'),
        emailAddress: document.getElementById('emailAddress'),
        emailPassword: document.getElementById('emailPassword'),
        smtpServer: document.getElementById('smtpServer'),
        form: document.getElementById('emailConfigForm')
    };
    
    console.log('🔧 Éléments trouvés:', elements);
    
    // Test 2: Charger la configuration
    console.log('🔧 Test chargement configuration...');
    fetch('/api/email/config')
        .then(response => response.json())
        .then(result => {
            console.log('🔧 Configuration reçue:', result);
            
            if (result.success) {
                const config = result.data;
                
                // Remplir le formulaire
                if (elements.emailEnabled) elements.emailEnabled.checked = config.enabled || false;
                if (elements.autoSend) elements.autoSend.checked = config.auto_send !== false;
                if (elements.senderName) elements.senderName.value = config.sender_name || 'FactureKiller';
                if (elements.emailAddress) elements.emailAddress.value = config.email || '';
                if (elements.emailPassword) {
                    if (config.password === '***') {
                        elements.emailPassword.placeholder = 'Mot de passe configuré (laisser vide pour garder)';
                        elements.emailPassword.value = '';
                    } else {
                        elements.emailPassword.value = config.password || '';
                    }
                }
                if (elements.smtpServer) elements.smtpServer.value = config.smtp_server || 'smtp.gmail.com';
                
                console.log('✅ Formulaire rempli avec succès');
            }
        })
        .catch(error => {
            console.error('❌ Erreur chargement config:', error);
        });
    
    // Test 3: Événement de sauvegarde
    if (elements.form) {
        elements.form.addEventListener('submit', function(e) {
            e.preventDefault();
            console.log('🔧 Tentative de sauvegarde...');
            
            const config = {
                enabled: elements.emailEnabled ? elements.emailEnabled.checked : false,
                auto_send: elements.autoSend ? elements.autoSend.checked : true,
                sender_name: elements.senderName ? elements.senderName.value : 'FactureKiller',
                email: elements.emailAddress ? elements.emailAddress.value : '',
                password: elements.emailPassword ? elements.emailPassword.value : '',
                smtp_server: elements.smtpServer ? elements.smtpServer.value : 'smtp.gmail.com',
                smtp_port: 587
            };
            
            console.log('🔧 Configuration à sauvegarder:', config);
            
            fetch('/api/email/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            })
            .then(response => response.json())
            .then(result => {
                console.log('🔧 Résultat sauvegarde:', result);
                
                if (result.success) {
                    alert('✅ Configuration sauvegardée avec succès !');
                } else {
                    alert('❌ Erreur: ' + (result.error || 'Erreur inconnue'));
                }
            })
            .catch(error => {
                console.error('❌ Erreur sauvegarde:', error);
                alert('❌ Erreur de connexion: ' + error.message);
            });
        });
        
        console.log('✅ Événement de sauvegarde configuré');
    } else {
        console.error('❌ Formulaire non trouvé !');
    }
});

// Test 4: Fonction de test de connexion
function testEmailConnectionDebug() {
    console.log('🔧 Test de connexion email...');
    
    fetch('/api/email/test', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(result => {
        console.log('🔧 Résultat test connexion:', result);
        
        if (result.success) {
            alert('✅ ' + result.message);
        } else {
            alert('❌ ' + result.error);
        }
    })
    .catch(error => {
        console.error('❌ Erreur test connexion:', error);
        alert('❌ Erreur: ' + error.message);
    });
}

// Remplacer les fonctions globales
window.testEmailConnection = testEmailConnectionDebug;

console.log('🔧 Script parametres-debug.js initialisé'); 