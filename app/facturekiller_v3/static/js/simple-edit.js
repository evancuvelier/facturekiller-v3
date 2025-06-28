// === FONCTIONS POUR L'ÉDITION SIMPLE DES PRODUITS ===

function editSingleProduct(productIndex) {
    window.scanner.editSingleProduct(productIndex);
}

function checkQuantityDifference() {
    const commandee = parseFloat(document.getElementById('quantiteCommandee').value) || 0;
    const recue = parseFloat(document.getElementById('quantiteRecue').value) || 0;
    const difference = commandee - recue;
    
    const displayDiv = document.getElementById('differenceDisplay');
    const anomalySection = document.getElementById('anomalySection');
    
    if (Math.abs(difference) < 0.01) {
        // Pas de différence
        displayDiv.innerHTML = `
            <span class="text-success fw-bold">
                <i class="bi bi-check-circle me-1"></i>
                Quantités identiques
            </span>
        `;
        displayDiv.className = 'p-2 border rounded bg-light text-center border-success';
        anomalySection.style.display = 'none';
    } else {
        // Il y a une différence
        let message, color, icon;
        if (difference > 0) {
            message = `Il manque ${difference.toFixed(1)} unité(s)`;
            color = 'danger';
            icon = 'dash-circle';
        } else {
            message = `Excédent de ${Math.abs(difference).toFixed(1)} unité(s)`;
            color = 'warning';
            icon = 'plus-circle';
        }
        
        displayDiv.innerHTML = `
            <span class="text-${color} fw-bold">
                <i class="bi bi-${icon} me-1"></i>
                ${message}
            </span>
        `;
        displayDiv.className = `p-2 border rounded bg-light text-center border-${color}`;
        anomalySection.style.display = 'block';
        
        // Mettre à jour le commentaire automatiquement
        const commentArea = document.getElementById('anomalyComment');
        if (!commentArea.value || commentArea.value === 'Une différence de quantité a été détectée.') {
            commentArea.value = `Anomalie de réception: ${message.toLowerCase()}`;
        }
    }
}

function saveSingleProductEdit(productIndex) {
    const commandee = parseFloat(document.getElementById('quantiteCommandee').value) || 0;
    const recue = parseFloat(document.getElementById('quantiteRecue').value) || 0;
    const prixScanne = parseFloat(document.getElementById('prixScanne').value) || 0;
    const anomalyComment = document.getElementById('anomalyComment').value;
    
    // Mettre à jour le produit
    const product = window.scanner.analysisResult.products[productIndex];
    product.quantity_received = recue;
    product.quantity_ordered = commandee;
    
    // S'il y a une différence, créer une anomalie
    const difference = Math.abs(commandee - recue);
    if (difference >= 0.01) {
        // Initialiser le tableau des anomalies s'il n'existe pas
        if (!window.scanner.analysisResult.anomalies) {
            window.scanner.analysisResult.anomalies = [];
        }
        
        // Créer l'anomalie
        const anomaly = {
            id: Date.now(),
            product_name: product.name,
            product_index: productIndex,
            type: 'quantity_incorrect',
            severity: difference > commandee * 0.2 ? 'high' : (difference > commandee * 0.1 ? 'medium' : 'low'),
            description: anomalyComment || `Différence de quantité détectée`,
            quantity_ordered: commandee,
            quantity_received: recue,
            unit: product.unit || 'unité',
            timestamp: new Date().toISOString(),
            resolved: false
        };
        
        // Supprimer toute anomalie existante pour ce produit
        window.scanner.analysisResult.anomalies = window.scanner.analysisResult.anomalies.filter(a => a.product_index !== productIndex);
        
        // Ajouter la nouvelle anomalie
        window.scanner.analysisResult.anomalies.push(anomaly);
    } else {
        // Supprimer l'anomalie s'il n'y a plus de différence
        if (window.scanner.analysisResult.anomalies) {
            window.scanner.analysisResult.anomalies = window.scanner.analysisResult.anomalies.filter(a => a.product_index !== productIndex);
        }
    }
    
    // Marquer comme modifié par l'utilisateur
    window.scanner.analysisResult.manual_edits = true;
    window.scanner.analysisResult.has_anomalies = window.scanner.analysisResult.anomalies && window.scanner.analysisResult.anomalies.length > 0;
    
    // Fermer le modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('editSingleProductModal'));
    modal.hide();
    
    // Rafraîchir l'affichage
    window.scanner.fillProductsList(window.scanner.analysisResult);
    
    // Notification
    const anomalyText = difference >= 0.01 ? ' avec anomalie signalée' : '';
    window.scanner.showNotification(`Produit mis à jour${anomalyText}`, 'success');
} 