#!/usr/bin/env python3
"""
Gestionnaire d'anomalies - Workflow complet avec fournisseurs
100% Firestore - Plus de fichiers locaux
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class AnomalyManager:
    def __init__(self):
        # Initialiser Firestore
        try:
            from modules.firestore_db import get_client
            self._fs = get_client()
            self._fs_enabled = self._fs is not None
            if self._fs_enabled:
                print("✅ Firestore initialisé pour AnomalyManager")
            else:
                print("❌ Firestore non disponible pour AnomalyManager")
        except Exception as e:
            print(f"❌ Erreur initialisation Firestore AnomalyManager: {e}")
            self._fs_enabled = False
            self._fs = None
    
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
        """Sauvegarder une nouvelle anomalie dans Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                logger.error("Firestore non disponible pour sauvegarder l'anomalie")
                return None
            
            # Générer un ID unique
            anomalie_id = f"ANOM_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self._get_next_anomaly_number()}"
            
            anomalie_data['id'] = anomalie_id
            anomalie_data['facture_id'] = facture_id
            anomalie_data['created_at'] = datetime.now().isoformat()
            anomalie_data['updated_at'] = datetime.now().isoformat()
            
            # Sauvegarder dans Firestore
            self._fs.collection('anomalies').document(anomalie_id).set(anomalie_data)
            
            logger.info(f"Anomalie sauvegardée: {anomalie_id}")
            return anomalie_id
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde anomalie: {e}")
            return None
    
    def _get_next_anomaly_number(self):
        """Obtenir le prochain numéro d'anomalie"""
        try:
            if not self._fs_enabled or not self._fs:
                return 1
            docs = list(self._fs.collection('anomalies').stream())
            return len(docs) + 1
        except:
            return 1
    
    def get_anomalies(self, statut=None, fournisseur=None, restaurant=None):
        """Récupérer les anomalies avec filtres depuis Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return []
            
            docs = list(self._fs.collection('anomalies').stream())
            anomalies = [doc.to_dict() for doc in docs]
            
            # Appliquer les filtres
            if statut:
                anomalies = [a for a in anomalies if a.get('statut') == statut]
            
            if fournisseur:
                anomalies = [a for a in anomalies if a.get('fournisseur') == fournisseur]
            
            if restaurant:
                anomalies = [a for a in anomalies if a.get('restaurant') == restaurant]
            
            # Trier par date de création (plus récent en premier)
            anomalies.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Erreur récupération anomalies: {e}")
            return []
    
    def update_anomaly_status(self, anomalie_id, nouveau_statut, commentaire=None, reponse_fournisseur=None):
        """Mettre à jour le statut d'une anomalie dans Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                logger.error("Firestore non disponible pour mettre à jour l'anomalie")
                return False
            
            # Récupérer l'anomalie
            doc_ref = self._fs.collection('anomalies').document(anomalie_id)
            doc = doc_ref.get()
            if not doc.exists:
                logger.warning(f"Anomalie non trouvée: {anomalie_id}")
                return False
            
            # Mettre à jour le statut
            update_data = {
                'statut': nouveau_statut,
                'updated_at': datetime.now().isoformat()
            }
            
            # Dates spécifiques selon le statut
            if nouveau_statut == 'mail_envoye':
                update_data['date_mail_envoye'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            elif nouveau_statut in ['avoir_accepte', 'avoir_refuse', 'resolu']:
                update_data['date_reponse'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Commentaires et réponses
            if commentaire:
                update_data['commentaire'] = commentaire
            
            if reponse_fournisseur:
                update_data['reponse_fournisseur'] = reponse_fournisseur
            
            # Mettre à jour dans Firestore
            doc_ref.update(update_data)
            
            logger.info(f"Statut anomalie mis à jour: {anomalie_id} -> {nouveau_statut}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur mise à jour anomalie: {e}")
            return False
    
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
        """Statistiques des anomalies depuis Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return {
                    'total': 0,
                    'detectees': 0,
                    'mail_envoyes': 0,
                    'avoir_acceptes': 0,
                    'avoir_refuses': 0,
                    'resolues': 0,
                    'montant_total_ecarts': 0
                }
            
            docs = list(self._fs.collection('anomalies').stream())
            anomalies = [doc.to_dict() for doc in docs]
            
            if not anomalies:
                return {
                    'total': 0,
                    'detectees': 0,
                    'mail_envoyes': 0,
                    'avoir_acceptes': 0,
                    'avoir_refuses': 0,
                    'resolues': 0,
                    'montant_total_ecarts': 0
                }
            
            stats = {
                'total': len(anomalies),
                'detectees': len([a for a in anomalies if a.get('statut') == 'detectee']),
                'mail_envoyes': len([a for a in anomalies if a.get('statut') == 'mail_envoye']),
                'avoir_acceptes': len([a for a in anomalies if a.get('statut') == 'avoir_accepte']),
                'avoir_refuses': len([a for a in anomalies if a.get('statut') == 'avoir_refuse']),
                'resolues': len([a for a in anomalies if a.get('statut') == 'resolu']),
                'montant_total_ecarts': sum(float(a.get('ecart_euros', 0)) for a in anomalies)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur calcul stats anomalies: {e}")
            return {}
    
    def get_anomaly_by_id(self, anomalie_id):
        """Récupérer une anomalie spécifique depuis Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return None
            
            doc = self._fs.collection('anomalies').document(anomalie_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Erreur récupération anomalie: {e}")
            return None
    
    def delete_anomaly(self, anomalie_id):
        """Supprimer une anomalie de Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                logger.error("Firestore non disponible pour supprimer l'anomalie")
                return False
            
            self._fs.collection('anomalies').document(anomalie_id).delete()
            logger.info(f"Anomalie supprimée: {anomalie_id}")
            return True
        except Exception as e:
            logger.error(f"Erreur suppression anomalie: {e}")
            return False
    
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