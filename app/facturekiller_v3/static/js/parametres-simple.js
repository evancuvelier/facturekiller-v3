// Version ultra-simple pour test
console.log('✅ Script parametres-simple.js chargé !');

// Test immédiat
alert('🔧 Script JavaScript chargé !');

// Attendre que le DOM soit prêt
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ DOM prêt !');
    alert('🔧 DOM prêt, initialisation...');
    
    // Test de chargement de config
    fetch('/api/email/config')
        .then(response => response.json())
        .then(result => {
            console.log('Config reçue:', result);
            alert('✅ Configuration reçue : ' + JSON.stringify(result.data));
            
            // Remplir quelques champs
            const emailField = document.getElementById('emailAddress');
            if (emailField && result.success) {
                emailField.value = result.data.email || '';
                alert('✅ Email rempli : ' + result.data.email);
            }
        })
        .catch(error => {
            console.error('Erreur:', error);
            alert('❌ Erreur chargement config : ' + error.message);
        });
    
    // Test de sauvegarde simple
    const form = document.getElementById('emailConfigForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            alert('🔧 Formulaire soumis ! Test de sauvegarde...');
            
            const testConfig = {
                enabled: true,
                email: 'test@example.com',
                password: 'test123',
                sender_name: 'Test',
                smtp_server: 'smtp.gmail.com',
                smtp_port: 587,
                auto_send: true
            };
            
            fetch('/api/email/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(testConfig)
            })
            .then(response => response.json())
            .then(result => {
                alert('✅ Sauvegarde : ' + (result.success ? 'SUCCÈS' : 'ÉCHEC - ' + result.error));
            })
            .catch(error => {
                alert('❌ Erreur sauvegarde : ' + error.message);
            });
        });
        
        alert('✅ Événement de formulaire configuré !');
    } else {
        alert('❌ Formulaire non trouvé !');
    }
});

// Fonction de test simple
function testEmailConnectionSimple() {
    alert('🔧 Test de connexion...');
    
    fetch('/api/email/test', { method: 'POST' })
        .then(response => response.json())
        .then(result => {
            alert(result.success ? '✅ ' + result.message : '❌ ' + result.error);
        })
        .catch(error => {
            alert('❌ Erreur test : ' + error.message);
        });
}

// Remplacer la fonction globale
window.testEmailConnection = testEmailConnectionSimple;

console.log('✅ Script parametres-simple.js initialisé !'); 