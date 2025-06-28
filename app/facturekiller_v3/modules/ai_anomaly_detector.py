"""
🧠 FactureKiller V3 - Détecteur d'Anomalies IA
Système intelligent pour détecter les patterns d'anomalies et SUGGÉRER des mises à jour de prix
⚠️ IMPORTANT: L'IA ne modifie JAMAIS les prix directement - elle fait seulement des suggestions
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import os
from collections import defaultdict, Counter

class AIAnomalyDetector:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.anomaly_history_file = os.path.join(data_dir, "anomaly_history.json")
        self.ai_suggestions_file = os.path.join(data_dir, "ai_suggestions.json")
        self.confidence_threshold = 0.8  # Seuil de confiance pour suggestions
        self.pattern_min_occurrences = 2  # Minimum d'occurrences pour détecter un pattern
        
        # Charger l'historique des anomalies
        self.anomaly_history = self._load_anomaly_history()
        self.ai_suggestions = self._load_ai_suggestions()
    
    def _load_anomaly_history(self) -> List[Dict]:
        """Charger l'historique des anomalies détectées"""
        try:
            if os.path.exists(self.anomaly_history_file):
                with open(self.anomaly_history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"⚠️ Erreur chargement historique anomalies: {e}")
            return []
    
    def _load_ai_suggestions(self) -> List[Dict]:
        """Charger les suggestions IA précédentes"""
        try:
            if os.path.exists(self.ai_suggestions_file):
                with open(self.ai_suggestions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"⚠️ Erreur chargement suggestions IA: {e}")
            return []
    
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
                'anomaly_rate': round(stats['anomalies'] / max(stats['total_products'], 1) * 100, 1),
                'price_patterns_detected': len(supplier_patterns),
                'suggestions_count': len(supplier_patterns),
                'requires_review': len(supplier_patterns) > 0,
                'recommended_actions': self._get_supplier_recommendations(supplier_patterns)
            }
        
        return insights
    
    def _get_supplier_recommendations(self, patterns: List[Dict]) -> List[str]:
        """Obtenir les recommandations pour un fournisseur"""
        recommendations = []
        
        strong_suggestions = len([p for p in patterns if p['confidence_score'] >= 0.85])
        moderate_suggestions = len([p for p in patterns if 0.7 <= p['confidence_score'] < 0.85])
        
        if strong_suggestions > 0:
            recommendations.append(f"💪 {strong_suggestions} suggestions fortes à réviser")
        
        if moderate_suggestions > 0:
            recommendations.append(f"👀 {moderate_suggestions} suggestions modérées à examiner")
        
        if not recommendations:
            recommendations.append("✅ Aucune suggestion - prix stables")
        
        return recommendations
    
    def _save_analysis_data(self, anomalies: List[Dict], suggestions: List[Dict]):
        """Sauvegarder les données d'analyse"""
        try:
            # Ajouter les nouvelles anomalies à l'historique
            self.anomaly_history.extend(anomalies)
            
            # Limiter l'historique aux 1000 dernières anomalies
            if len(self.anomaly_history) > 1000:
                self.anomaly_history = self.anomaly_history[-1000:]
            
            # Ajouter les nouvelles suggestions
            self.ai_suggestions.extend(suggestions)
            
            # Sauvegarder
            with open(self.anomaly_history_file, 'w', encoding='utf-8') as f:
                json.dump(self.anomaly_history, f, indent=2, ensure_ascii=False)
            
            with open(self.ai_suggestions_file, 'w', encoding='utf-8') as f:
                json.dump(self.ai_suggestions, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"⚠️ Erreur sauvegarde données IA: {e}")
    
    def get_pending_suggestions(self) -> List[Dict]:
        """Obtenir les suggestions en attente de validation client"""
        return [s for s in self.ai_suggestions if s.get('status') == 'pending_validation']
    
    def mark_suggestion_reviewed(self, suggestion_id: str, client_decision: str, notes: str = '') -> bool:
        """
        Marquer une suggestion comme révisée par le client
        client_decision: 'accepted', 'rejected', 'modified'
        """
        for suggestion in self.ai_suggestions:
            if suggestion['id'] == suggestion_id:
                suggestion['status'] = f'client_{client_decision}'
                suggestion['reviewed_at'] = datetime.now().isoformat()
                suggestion['client_notes'] = notes
                self._save_analysis_data([], [])
                return True
        return False
    
    def get_suggestions_for_validation_interface(self) -> List[Dict]:
        """
        Obtenir les suggestions formatées pour l'interface de validation client
        """
        pending_suggestions = self.get_pending_suggestions()
        
        formatted_suggestions = []
        for suggestion in pending_suggestions:
            formatted = {
                'id': suggestion['id'],
                'product_name': suggestion['product_name'],
                'supplier': suggestion['supplier'],
                'current_price': suggestion['current_reference_price'],
                'suggested_price': suggestion['suggested_new_price'],
                'price_change': suggestion['suggested_new_price'] - suggestion['current_reference_price'],
                'percentage_change': suggestion['evidence']['percentage_change'],
                'confidence': round(suggestion['confidence_score'] * 100),
                'recommendation_level': suggestion['recommendation_level'],
                'evidence_count': suggestion['evidence']['occurrences'],
                'financial_impact': suggestion['evidence']['total_financial_impact'],
                'can_accept': True,  # Client peut accepter
                'can_reject': True,  # Client peut rejeter
                'can_modify': True   # Client peut modifier le prix suggéré
            }
            formatted_suggestions.append(formatted)
        
        return formatted_suggestions 