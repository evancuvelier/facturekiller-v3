// === FONCTIONS POUR L'ÉDITION SIMPLE DES PRODUITS ===

function editSingleProduct(productIndex) {
    window.scanner.editSingleProduct(productIndex);
}

function checkQuantityDifference() {
    const commandee = parseFloat(document.getElementById("quantiteCommandee").value) || 0;
    const recue = parseFloat(document.getElementById("quantiteRecue").value) || 0;
    const difference = commandee - recue;
    
    const displayDiv = document.getElementById("differenceDisplay");
    const anomalySection = document.getElementById("anomalySection");
    
    if (Math.abs(difference) < 0.01) {
        displayDiv.innerHTML = `<span class="text-success fw-bold"><i class="bi bi-check-circle me-1"></i>Quantités identiques</span>`;
        displayDiv.className = "p-2 border rounded bg-light text-center border-success";
        anomalySection.style.display = "none";
    } else {
        let message, color, icon;
        if (difference > 0) {
            message = `Il manque ${difference.toFixed(1)} unité(s)`;
            color = "danger";
            icon = "dash-circle";
        } else {
            message = `Excédent de ${Math.abs(difference).toFixed(1)} unité(s)`;
            color = "warning";
            icon = "plus-circle";
        }
        
        displayDiv.innerHTML = `<span class="text-${color} fw-bold"><i class="bi bi-${icon} me-1"></i>${message}</span>`;
        displayDiv.className = `p-2 border rounded bg-light text-center border-${color}`;
        anomalySection.style.display = "block";
        
        const commentArea = document.getElementById("anomalyComment");
        if (!commentArea.value || commentArea.value === "Une différence de quantité a été détectée.") {
            commentArea.value = `Anomalie de réception: ${message.toLowerCase()}`;
        }
    }
}

function saveSingleProductEdit(productIndex) {
    const commandee = parseFloat(document.getElementById("quantiteCommandee").value) || 0;
    const recue = parseFloat(document.getElementById("quantiteRecue").value) || 0;
    const anomalyComment = document.getElementById("anomalyComment").value;
    
    const product = window.scanner.analysisResult.products[productIndex];
    product.quantity_received = recue;
    product.quantity_ordered = commandee;
    
    const difference = Math.abs(commandee - recue);
    if (difference >= 0.01) {
        if (!window.scanner.analysisResult.anomalies) {
            window.scanner.analysisResult.anomalies = [];
        }
        
        const anomaly = {
            id: Date.now(),
            product_name: product.name,
            product_index: productIndex,
            type: "quantity_incorrect",
            severity: difference > commandee * 0.2 ? "high" : (difference > commandee * 0.1 ? "medium" : "low"),
            description: anomalyComment || `Différence de quantité détectée`,
            quantity_ordered: commandee,
            quantity_received: recue,
            unit: product.unit || "unité",
            timestamp: new Date().toISOString(),
            resolved: false
        };
        
        window.scanner.analysisResult.anomalies = window.scanner.analysisResult.anomalies.filter(a => a.product_index !== productIndex);
        window.scanner.analysisResult.anomalies.push(anomaly);
    } else {
        if (window.scanner.analysisResult.anomalies) {
            window.scanner.analysisResult.anomalies = window.scanner.analysisResult.anomalies.filter(a => a.product_index !== productIndex);
        }
    }
    
    window.scanner.analysisResult.manual_edits = true;
    window.scanner.analysisResult.has_anomalies = window.scanner.analysisResult.anomalies && window.scanner.analysisResult.anomalies.length > 0;
    
    const modal = bootstrap.Modal.getInstance(document.getElementById("editSingleProductModal"));
    modal.hide();
    
    window.scanner.fillProductsList(window.scanner.analysisResult);
    
    const anomalyText = difference >= 0.01 ? " avec anomalie signalée" : "";
    window.scanner.showNotification(`Produit mis à jour${anomalyText}`, "success");
}
