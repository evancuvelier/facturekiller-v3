"""
🧠 FactureKiller V3 - Détecteur d'Anomalies IA
Système intelligent pour détecter les patterns d'anomalies et SUGGÉRER des mises à jour de prix
⚠️ IMPORTANT: L'IA ne modifie JAMAIS les prix directement - elle fait seulement des suggestions
100% Firestore - Plus de fichiers locaux
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

class AIAnomalyDetector:
    def __init__(self):
        self.confidence_threshold = 0.8  # Seuil de confiance pour suggestions
        self.pattern_min_occurrences = 2  # Minimum d'occurrences pour détecter un pattern
        
        # Initialiser Firestore
        try:
            from modules.firestore_db import get_client
            self._fs = get_client()
            self._fs_enabled = self._fs is not None
            if self._fs_enabled:
                print("✅ Firestore initialisé pour AIAnomalyDetector")
            else:
                print("❌ Firestore non disponible pour AIAnomalyDetector")
        except Exception as e:
            print(f"❌ Erreur initialisation Firestore AIAnomalyDetector: {e}")
            self._fs_enabled = False
            self._fs = None
    
    def _load_anomaly_history(self) -> List[Dict]:
        """Charger l'historique des anomalies détectées depuis Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return []
            
            docs = list(self._fs.collection('anomaly_history').stream())
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"⚠️ Erreur chargement historique anomalies: {e}")
            return []
    
    def _load_ai_suggestions(self) -> List[Dict]:
        """Charger les suggestions IA précédentes depuis Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return []
            
            docs = list(self._fs.collection('ai_suggestions').stream())
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"⚠️ Erreur chargement suggestions IA: {e}")
            return []
    
    def _save_anomaly_history(self, anomalies: List[Dict]):
        """Sauvegarder l'historique des anomalies dans Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return
            
            for anomaly in anomalies:
                anomaly_id = f"hist_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{anomaly.get('product_name', 'unknown')}"
                self._fs.collection('anomaly_history').document(anomaly_id).set(anomaly)
        except Exception as e:
            logger.error(f"Erreur sauvegarde historique anomalies: {e}")
    
    def _save_ai_suggestions(self, suggestions: List[Dict]):
        """Sauvegarder les suggestions IA dans Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return
            
            for suggestion in suggestions:
                suggestion_id = suggestion.get('id', f"sugg_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                self._fs.collection('ai_suggestions').document(suggestion_id).set(suggestion)
        except Exception as e:
            logger.error(f"Erreur sauvegarde suggestions IA: {e}")
    
    def analyze_batch_anomalies(self, batch_results: List[Dict]) -> Dict[str, Any]:
        """
        🎯 ANALYSE INTELLIGENTE DU BATCH
        Détecte les patterns d'anomalies récurrentes et SUGGÈRE des mises à jour de prix
        """
        analysis = {
            'total_scans': len(batch_results),
            'total_products_scanned': 0,
            'anomalies_detected': 0,
            'recurring_price_patterns': [],
            'price_update_suggestions': [],  # 🔄 Suggestions pour validation client
            'supplier_insights': {},
            'validation_required': True,  # ⚠️ Toujours nécessite validation client
            'summary': {
                'patterns_detected': 0,
                'suggestions_generated': 0,
                'high_confidence_suggestions': 0,
                'client_validation_needed': True  # 👤 Client doit toujours valider
            }
        }
        
        # Collecter toutes les anomalies du batch
        all_anomalies = []
        supplier_stats = defaultdict(lambda: {'total_products': 0, 'anomalies': 0})
        
        for scan_result in batch_results:
            scan_anomalies = self._extract_anomalies_from_scan(scan_result)
            all_anomalies.extend(scan_anomalies)
            
            # Statistiques par fournisseur
            supplier = scan_result.get('supplier', 'Inconnu')
            products_count = len(scan_result.get('products', []))
            supplier_stats[supplier]['total_products'] += products_count
            supplier_stats[supplier]['anomalies'] += len(scan_anomalies)
            
            analysis['total_products_scanned'] += products_count
        
        analysis['anomalies_detected'] = len(all_anomalies)
        
        # 🧠 DÉTECTION INTELLIGENTE DES PATTERNS
        patterns = self._detect_intelligent_patterns(all_anomalies)
        analysis['recurring_price_patterns'] = patterns
        analysis['summary']['patterns_detected'] = len(patterns)
        
        # 💡 GÉNÉRATION DES SUGGESTIONS (PAS D'APPLICATION AUTOMATIQUE)
        suggestions = self._generate_price_suggestions(patterns)
        analysis['price_update_suggestions'] = suggestions
        analysis['summary']['suggestions_generated'] = len(suggestions)
        analysis['summary']['high_confidence_suggestions'] = len([s for s in suggestions if s['confidence_score'] >= 0.8])
        
        # 📊 INSIGHTS PAR FOURNISSEUR
        analysis['supplier_insights'] = self._generate_supplier_insights(supplier_stats, patterns)
        
        # Sauvegarder les nouvelles données
        self._save_analysis_data(all_anomalies, suggestions)
        
        return analysis
    
    def _extract_anomalies_from_scan(self, scan_result: Dict) -> List[Dict]:
        """Extraire les anomalies d'un scan individuel"""
        anomalies = []
        price_comparison = scan_result.get('price_comparison', {})
        supplier = scan_result.get('supplier', 'Inconnu')
        scan_date = scan_result.get('analysis_timestamp', datetime.now().isoformat())
        
        for variation in price_comparison.get('price_variations', []):
            # Seulement les anomalies significatives (> 5% de différence)
            if abs(variation['percentage_difference']) > 5:
                anomaly = {
                    'product_name': variation['product_name'],
                    'supplier': supplier,
                    'invoice_price': variation['invoice_price'],
                    'reference_price': variation['reference_price'],
                    'price_difference': variation['price_difference'],
                    'percentage_difference': variation['percentage_difference'],
                    'status': variation['status'],
                    'scan_date': scan_date,
                    'quantity': variation.get('quantity', 1),
                    'total_impact': variation.get('total_impact', 0)
                }
                anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_intelligent_patterns(self, anomalies: List[Dict]) -> List[Dict]:
        """
        🧠 DÉTECTION INTELLIGENTE DES PATTERNS
        Identifie les produits avec des anomalies récurrentes qui pourraient indiquer un changement de prix
        """
        patterns = []
        
        # Grouper par produit + fournisseur
        product_groups = defaultdict(list)
        for anomaly in anomalies:
            key = f"{anomaly['product_name']}_{anomaly['supplier']}"
            product_groups[key].append(anomaly)
        
        # Analyser chaque groupe
        for group_key, group_anomalies in product_groups.items():
            if len(group_anomalies) >= self.pattern_min_occurrences:
                pattern = self._analyze_pattern_group(group_key, group_anomalies)
                if pattern:
                    patterns.append(pattern)
        
        return patterns
    
    def _analyze_pattern_group(self, group_key: str, anomalies: List[Dict]) -> Optional[Dict]:
        """Analyser un groupe d'anomalies pour détecter un pattern"""
        if not anomalies:
            return None
        
        # Statistiques du groupe
        prices = [a['invoice_price'] for a in anomalies]
        percentages = [a['percentage_difference'] for a in anomalies]
        
        price_mean = sum(prices) / len(prices)
        price_std = (sum((p - price_mean) ** 2 for p in prices) / len(prices)) ** 0.5
        percentage_mean = sum(percentages) / len(percentages)
        
        # Vérifier la consistance (coefficient de variation < 20%)
        if price_std / price_mean < 0.20:
            confidence = self._calculate_pattern_confidence(anomalies, price_std, price_mean)
            
            return {
                'group_key': group_key,
                'product_name': anomalies[0]['product_name'],
                'supplier': anomalies[0]['supplier'],
                'occurrences': len(anomalies),
                'consistent_new_price': round(price_mean, 2),
                'old_reference_price': anomalies[0]['reference_price'],
                'average_percentage_change': round(percentage_mean, 1),
                'price_consistency': round(1 - (price_std / price_mean), 2),
                'confidence_score': confidence,
                'total_impact': sum(a.get('total_impact', 0) for a in anomalies),
                'evidence': [
                    f"Prix facturé: {a['invoice_price']}€ le {a['scan_date'][:10]}" 
                    for a in anomalies[-3:]  # Dernières 3 occurrences
                ]
            }
        
        return None
    
    def _calculate_pattern_confidence(self, anomalies: List[Dict], price_std: float, price_mean: float) -> float:
        """Calculer la confiance d'un pattern"""
        base_confidence = 0.6
        
        # Bonus pour nombre d'occurrences
        occurrence_bonus = min(0.2, len(anomalies) * 0.1)
        
        # Bonus pour consistance des prix
        consistency_bonus = (1 - (price_std / price_mean)) * 0.2
        
        return min(1.0, base_confidence + occurrence_bonus + consistency_bonus)
    
    def _generate_price_suggestions(self, patterns: List[Dict]) -> List[Dict]:
        """
        💡 GÉNÉRER DES SUGGESTIONS DE PRIX (SANS APPLICATION AUTOMATIQUE)
        Les suggestions seront présentées au client pour validation
        """
        suggestions = []
        
        for pattern in patterns:
            if pattern['confidence_score'] >= 0.6:  # Seuil plus bas pour suggestions
                suggestion = {
                    'id': f"suggestion_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{pattern['group_key']}",
                    'type': 'price_update_suggestion',
                    'product_name': pattern['product_name'],
                    'supplier': pattern['supplier'],
                    'current_reference_price': pattern['old_reference_price'],
                    'suggested_new_price': pattern['consistent_new_price'],
                    'confidence_score': pattern['confidence_score'],
                    'evidence': {
                        'occurrences': pattern['occurrences'],
                        'percentage_change': pattern['average_percentage_change'],
                        'price_consistency': pattern['price_consistency'],
                        'total_financial_impact': pattern['total_impact'],
                        'recent_evidence': pattern['evidence']
                    },
                    'recommendation_level': self._get_recommendation_level(pattern['confidence_score']),
                    'requires_client_validation': True,  # 👤 TOUJOURS nécessite validation
                    'auto_apply': False,  # ❌ JAMAIS d'application automatique
                    'created_at': datetime.now().isoformat(),
                    'status': 'pending_validation'  # En attente de validation client
                }
                suggestions.append(suggestion)
        
        return suggestions
    
    def _get_recommendation_level(self, confidence: float) -> str:
        """Déterminer le niveau de recommandation"""
        if confidence >= 0.85:
            return "strong"  # Recommandation forte
        elif confidence >= 0.7:
            return "moderate"  # Recommandation modérée
        else:
            return "weak"  # Recommandation faible
    
    def _generate_supplier_insights(self, supplier_stats: Dict, patterns: List[Dict]) -> Dict:
        """Générer des insights par fournisseur"""
        insights = {}
        
        for supplier, stats in supplier_stats.items():
            supplier_patterns = [p for p in patterns if p['supplier'] == supplier]
            
            insights[supplier] = {
                'total_products_scanned': stats['total_products'],
                'anomalies_detected': stats['anomalies'],
                'anomaly_rate': round((stats['anomalies'] / stats['total_products']) * 100, 1) if stats['total_products'] > 0 else 0,
                'patterns_detected': len(supplier_patterns),
                'high_confidence_patterns': len([p for p in supplier_patterns if p['confidence_score'] >= 0.8]),
                'total_financial_impact': sum(p['total_impact'] for p in supplier_patterns),
                'recommendations': self._get_supplier_recommendations(supplier_patterns)
            }
        
        return insights
    
    def _get_supplier_recommendations(self, patterns: List[Dict]) -> List[str]:
        """Générer des recommandations pour un fournisseur"""
        recommendations = []
        
        if not patterns:
            return ["Aucun pattern détecté - surveillance normale"]
        
        high_confidence_count = len([p for p in patterns if p['confidence_score'] >= 0.8])
        
        if high_confidence_count >= 3:
            recommendations.append("🔴 URGENT: Nombreux patterns de prix détectés - vérification catalogue requise")
        elif high_confidence_count >= 1:
            recommendations.append("🟡 ATTENTION: Patterns de prix détectés - surveillance renforcée")
        
        total_impact = sum(p['total_impact'] for p in patterns)
        if total_impact > 1000:
            recommendations.append("💰 Impact financier élevé - priorité haute")
        
        return recommendations
    
    def _save_analysis_data(self, anomalies: List[Dict], suggestions: List[Dict]):
        """Sauvegarder les données d'analyse dans Firestore"""
        try:
            # Sauvegarder l'historique des anomalies
            self._save_anomaly_history(anomalies)
            
            # Sauvegarder les suggestions IA
            self._save_ai_suggestions(suggestions)
            
            logger.info(f"✅ Données d'analyse sauvegardées: {len(anomalies)} anomalies, {len(suggestions)} suggestions")
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde données d'analyse: {e}")
    
    def get_pending_suggestions(self) -> List[Dict]:
        """Récupérer les suggestions en attente de validation"""
        try:
            if not self._fs_enabled or not self._fs:
                return []
            
            docs = list(self._fs.collection('ai_suggestions').where('status', '==', 'pending_validation').stream())
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Erreur récupération suggestions en attente: {e}")
            return []
    
    def mark_suggestion_reviewed(self, suggestion_id: str, client_decision: str, notes: str = '') -> bool:
        """Marquer une suggestion comme examinée par le client"""
        try:
            if not self._fs_enabled or not self._fs:
                return False
            
            doc_ref = self._fs.collection('ai_suggestions').document(suggestion_id)
            doc = doc_ref.get()
            if not doc.exists:
                return False
            
            update_data = {
                'status': 'reviewed',
                'client_decision': client_decision,
                'client_notes': notes,
                'reviewed_at': datetime.now().isoformat()
            }
            
            doc_ref.update(update_data)
            return True
        except Exception as e:
            logger.error(f"Erreur mise à jour suggestion: {e}")
            return False
    
    def get_suggestions_for_validation_interface(self) -> List[Dict]:
        """Récupérer les suggestions pour l'interface de validation"""
        suggestions = self.get_pending_suggestions()
        
        # Ajouter des informations supplémentaires pour l'interface
        for suggestion in suggestions:
            suggestion['formatted_evidence'] = self._format_evidence_for_ui(suggestion.get('evidence', {}))
            suggestion['risk_level'] = self._calculate_risk_level(suggestion)
        
        return suggestions
    
    def _format_evidence_for_ui(self, evidence: Dict) -> str:
        """Formater les preuves pour l'interface utilisateur"""
        if not evidence:
            return "Aucune preuve disponible"
        
        lines = []
        if evidence.get('occurrences'):
            lines.append(f"• {evidence['occurrences']} occurrences détectées")
        if evidence.get('percentage_change'):
            lines.append(f"• Changement moyen: {evidence['percentage_change']}%")
        if evidence.get('total_financial_impact'):
            lines.append(f"• Impact financier: {evidence['total_financial_impact']}€")
        
        return "\n".join(lines)
    
    def _calculate_risk_level(self, suggestion: Dict) -> str:
        """Calculer le niveau de risque d'une suggestion"""
        confidence = suggestion.get('confidence_score', 0)
        financial_impact = suggestion.get('evidence', {}).get('total_financial_impact', 0)
        
        if confidence >= 0.9 and financial_impact > 500:
            return "high"
        elif confidence >= 0.7 or financial_impact > 200:
            return "medium"
        else:
            return "low"

# Instance globale
ai_anomaly_detector = AIAnomalyDetector() 