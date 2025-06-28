#!/usr/bin/env python3
"""
Gestionnaire d'anomalies - Workflow complet avec fournisseurs
"""

import pandas as pd
import os
from datetime import datetime
import json

class AnomalyManager:
    def __init__(self):
        self.anomalies_file = 'data/anomalies.csv'
        self.ensure_files_exist()
    
    def ensure_files_exist(self):
        """Créer les fichiers s'ils n'existent pas"""
        if not os.path.exists('data'):
            os.makedirs('data')
        
        if not os.path.exists(self.anomalies_file):
            df = pd.DataFrame(columns=[
                'id', 'facture_id', 'produit_nom', 'fournisseur', 'restaurant',
                'type_anomalie', 'prix_facture', 'prix_catalogue', 'ecart_euros', 'ecart_pourcent',
                'statut', 'date_detection', 'date_mail_envoye', 'date_reponse', 
                'reponse_fournisseur', 'commentaire', 'utilisateur'
            ])
            df.to_csv(self.anomalies_file, index=False)
    
    def detect_price_anomalies(self, facture_products, seuil_pourcent=10, seuil_euros=2):
        """
        Détecter les anomalies de prix automatiquement
        """
        from modules.price_manager import PriceManager
        
        anomalies = []
        price_manager = PriceManager()
        
        for product in facture_products:
            # Rechercher le prix catalogue
            catalogue_price = price_manager.find_product_price(
                product['name'], 
                product.get('supplier', ''),
                product.get('restaurant', 'Général')
            )
            
            if catalogue_price:
                prix_facture = float(product.get('unit_price', 0))
                prix_catalogue = float(catalogue_price.get('prix_unitaire', 0))
                
                # Calculer l'écart
                if prix_catalogue > 0:
                    ecart_euros = prix_facture - prix_catalogue
                    ecart_pourcent = (ecart_euros / prix_catalogue) * 100
                    
                    # Détecter anomalie
                    if abs(ecart_pourcent) >= seuil_pourcent or abs(ecart_euros) >= seuil_euros:
                        anomalie = {
                            'produit_nom': product['name'],
                            'fournisseur': product.get('supplier', ''),
                            'restaurant': product.get('restaurant', 'Général'),
                            'type_anomalie': 'prix_different',
                            'prix_facture': prix_facture,
                            'prix_catalogue': prix_catalogue,
                            'ecart_euros': round(ecart_euros, 2),
                            'ecart_pourcent': round(ecart_pourcent, 1),
                            'statut': 'detectee',
                            'date_detection': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        anomalies.append(anomalie)
        
        return anomalies
    
    def save_anomaly(self, anomalie_data, facture_id=None):
        """Sauvegarder une nouvelle anomalie"""
        df = pd.read_csv(self.anomalies_file)
        
        # Générer un ID unique
        anomalie_id = f"ANOM_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(df)+1}"
        
        anomalie_data['id'] = anomalie_id
        anomalie_data['facture_id'] = facture_id
        
        # Ajouter à la DataFrame
        new_row = pd.DataFrame([anomalie_data])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(self.anomalies_file, index=False)
        
        return anomalie_id
    
    def get_anomalies(self, statut=None, fournisseur=None):
        """Récupérer les anomalies avec filtres"""
        if not os.path.exists(self.anomalies_file):
            return []
        
        df = pd.read_csv(self.anomalies_file)
        
        if statut:
            df = df[df['statut'] == statut]
        
        if fournisseur:
            df = df[df['fournisseur'] == fournisseur]
        
        return df.to_dict('records')
    
    def update_anomaly_status(self, anomalie_id, nouveau_statut, commentaire=None, reponse_fournisseur=None):
        """Mettre à jour le statut d'une anomalie"""
        df = pd.read_csv(self.anomalies_file)
        
        mask = df['id'] == anomalie_id
        if not mask.any():
            return False
        
        # Mettre à jour le statut
        df.loc[mask, 'statut'] = nouveau_statut
        
        # Dates spécifiques selon le statut
        if nouveau_statut == 'mail_envoye':
            df.loc[mask, 'date_mail_envoye'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        elif nouveau_statut in ['avoir_accepte', 'avoir_refuse', 'resolu']:
            df.loc[mask, 'date_reponse'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Commentaires et réponses
        if commentaire:
            df.loc[mask, 'commentaire'] = commentaire
        
        if reponse_fournisseur:
            df.loc[mask, 'reponse_fournisseur'] = reponse_fournisseur
        
        df.to_csv(self.anomalies_file, index=False)
        return True
    
    def send_mail_to_supplier(self, anomalie_id):
        """Marquer comme mail envoyé au fournisseur"""
        return self.update_anomaly_status(
            anomalie_id, 
            'mail_envoye',
            commentaire=f"Mail automatique envoyé le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
        )
    
    def mark_avoir_accepted(self, anomalie_id, commentaire=None):
        """Marquer un avoir comme accepté"""
        return self.update_anomaly_status(
            anomalie_id,
            'avoir_accepte',
            commentaire=commentaire or "Avoir accepté par le fournisseur"
        )
    
    def mark_avoir_refused(self, anomalie_id, commentaire=None):
        """Marquer un avoir comme refusé"""
        return self.update_anomaly_status(
            anomalie_id,
            'avoir_refuse', 
            commentaire=commentaire or "Avoir refusé par le fournisseur"
        )
    
    def get_anomaly_stats(self):
        """Statistiques des anomalies"""
        if not os.path.exists(self.anomalies_file):
            return {}
        
        df = pd.read_csv(self.anomalies_file)
        
        stats = {
            'total': len(df),
            'detectees': len(df[df['statut'] == 'detectee']),
            'mail_envoyes': len(df[df['statut'] == 'mail_envoye']),
            'avoir_acceptes': len(df[df['statut'] == 'avoir_accepte']),
            'avoir_refuses': len(df[df['statut'] == 'avoir_refuse']),
            'resolues': len(df[df['statut'] == 'resolu']),
            'montant_total_ecarts': df['ecart_euros'].sum() if not df.empty else 0
        }
        
        return stats
    
    def get_anomaly_by_id(self, anomalie_id):
        """Récupérer une anomalie spécifique"""
        df = pd.read_csv(self.anomalies_file)
        mask = df['id'] == anomalie_id
        
        if not mask.any():
            return None
        
        return df[mask].iloc[0].to_dict()
    
    def generate_supplier_email_content(self, anomalie_id):
        """Générer le contenu d'email pour le fournisseur"""
        anomalie = self.get_anomaly_by_id(anomalie_id)
        
        if not anomalie:
            return None
        
        email_content = f"""
Objet: Anomalie de prix détectée - {anomalie['produit_nom']}

Bonjour,

Nous avons détecté une anomalie de prix sur la facture concernant :

• Produit : {anomalie['produit_nom']}
• Fournisseur : {anomalie['fournisseur']}
• Restaurant : {anomalie['restaurant']}

Détails de l'anomalie :
• Prix facturé : {anomalie['prix_facture']}€
• Prix catalogue : {anomalie['prix_catalogue']}€
• Écart : {anomalie['ecart_euros']}€ ({anomalie['ecart_pourcent']}%)

Date de détection : {anomalie['date_detection']}

Merci de nous confirmer :
1. S'il s'agit d'une erreur de facturation → Avoir à établir
2. S'il s'agit d'une mise à jour de prix → Nouveau catalogue à transmettre

Cordialement,
L'équipe FactureKiller
        """
        
        return email_content.strip()

# Instance globale
anomaly_manager = AnomalyManager() 