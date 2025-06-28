"""
Module de calcul des statistiques
Analyse des données pour le tableau de bord
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta
import pandas as pd
import logging
import json
import os

logger = logging.getLogger(__name__)

class StatsCalculator:
    """Calculateur de statistiques pour le tableau de bord"""
    
    def __init__(self):
        self.data_dir = 'data'
    
    def calculate_stats(self, prices: List[Dict], invoices: List[Dict]) -> Dict[str, Any]:
        """
        Calculer toutes les statistiques pour le tableau de bord
        
        Args:
            prices: Liste des prix de référence
            invoices: Liste des factures analysées
            
        Returns:
            Dict avec toutes les statistiques
        """
        try:
            # Convertir en DataFrames pour faciliter les calculs
            prices_df = pd.DataFrame(prices) if prices else pd.DataFrame()
            invoices_df = pd.DataFrame(invoices) if invoices else pd.DataFrame()
            
            stats = {
                'overview': self._calculate_overview(prices_df, invoices_df),
                'savings': self._calculate_savings(invoices_df),
                'suppliers': self._calculate_supplier_stats(prices_df, invoices_df),
                'categories': self._calculate_category_stats(prices_df),
                'trends': self._calculate_trends(invoices_df),
                'alerts': self._generate_alerts(prices_df, invoices_df),
                'last_update': datetime.now().isoformat()
            }
            
            # Ajouter des stats simples pour l'interface
            stats['total_invoices'] = len(invoices)
            stats['total_amount'] = sum(
                inv.get('analysis', {}).get('total_amount', 0) or 0 
                for inv in invoices 
                if isinstance(inv.get('analysis'), dict)
            )
            stats['total_savings'] = stats['savings']['net_savings']
            stats['unique_suppliers'] = len(stats['suppliers'])
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur calcul statistiques: {e}")
            return self._get_empty_stats()
    
    def _calculate_overview(self, prices_df: pd.DataFrame, invoices_df: pd.DataFrame) -> Dict:
        """Calculer les statistiques générales"""
        overview = {
            'total_reference_prices': len(prices_df),
            'active_reference_prices': len(prices_df[prices_df.get('actif', True) == True]) if 'actif' in prices_df.columns else len(prices_df),
            'total_invoices_analyzed': len(invoices_df),
            'total_products_analyzed': 0,
            'average_confidence_score': 0.0
        }
        
        # Compter les produits analysés
        if not invoices_df.empty and 'analysis' in invoices_df.columns:
            for _, invoice in invoices_df.iterrows():
                if isinstance(invoice['analysis'], dict):
                    products = invoice['analysis'].get('products', [])
                    overview['total_products_analyzed'] += len(products)
                    
                    # Score de confiance moyen
                    confidence = invoice['analysis'].get('confidence_score', 0)
                    overview['average_confidence_score'] += confidence
            
            if len(invoices_df) > 0:
                overview['average_confidence_score'] /= len(invoices_df)
        
        # Statistiques temporelles
        if not invoices_df.empty and 'created_at' in invoices_df.columns:
            invoices_df['created_at'] = pd.to_datetime(invoices_df['created_at'])
            overview['invoices_this_month'] = len(
                invoices_df[invoices_df['created_at'] >= datetime.now().replace(day=1)]
            )
            overview['invoices_last_7_days'] = len(
                invoices_df[invoices_df['created_at'] >= datetime.now() - timedelta(days=7)]
            )
        else:
            overview['invoices_this_month'] = 0
            overview['invoices_last_7_days'] = 0
        
        return overview
    
    def _calculate_savings(self, invoices_df: pd.DataFrame) -> Dict:
        """Calculer les économies potentielles"""
        savings = {
            'total_savings': 0.0,
            'total_overpayment': 0.0,
            'net_savings': 0.0,
            'savings_by_month': {},
            'top_savings_products': []
        }
        
        if invoices_df.empty:
            return savings
        
        # Parcourir les factures pour calculer les économies
        all_comparisons = []
        
        for _, invoice in invoices_df.iterrows():
            if not isinstance(invoice.get('analysis'), dict):
                continue
                
            comparison = invoice['analysis'].get('price_comparison', {})
            if comparison:
                savings['total_savings'] += comparison.get('total_savings', 0)
                savings['total_overpayment'] += comparison.get('total_overpayment', 0)
                
                # Collecter les détails pour le top des produits
                for detail in comparison.get('details', []):
                    all_comparisons.append(detail)
                
                # Économies par mois
                if 'created_at' in invoice:
                    month_key = pd.to_datetime(invoice['created_at']).strftime('%Y-%m')
                    if month_key not in savings['savings_by_month']:
                        savings['savings_by_month'][month_key] = {
                            'savings': 0,
                            'overpayment': 0
                        }
                    savings['savings_by_month'][month_key]['savings'] += comparison.get('total_savings', 0)
                    savings['savings_by_month'][month_key]['overpayment'] += comparison.get('total_overpayment', 0)
        
        # Économies nettes
        savings['net_savings'] = savings['total_savings'] - savings['total_overpayment']
        
        # Top 10 des produits avec le plus d'économies
        if all_comparisons:
            comparisons_df = pd.DataFrame(all_comparisons)
            top_products = comparisons_df.nlargest(10, 'difference').to_dict('records')
            savings['top_savings_products'] = top_products
        
        return savings
    
    def _calculate_supplier_stats(self, prices_df: pd.DataFrame, invoices_df: pd.DataFrame) -> Dict:
        """Calculer les statistiques par fournisseur"""
        supplier_stats = {}
        
        # Statistiques des prix de référence par fournisseur
        if not prices_df.empty and 'fournisseur' in prices_df.columns:
            for supplier in prices_df['fournisseur'].unique():
                supplier_prices = prices_df[prices_df['fournisseur'] == supplier]
                supplier_stats[supplier] = {
                    'total_products': len(supplier_prices),
                    'average_price': supplier_prices['prix'].mean() if 'prix' in supplier_prices.columns else 0,
                    'invoices_count': 0,
                    'total_amount': 0
                }
        
        # Ajouter les statistiques des factures
        if not invoices_df.empty:
            for _, invoice in invoices_df.iterrows():
                if isinstance(invoice.get('analysis'), dict):
                    supplier = invoice['analysis'].get('supplier', 'UNKNOWN')
                    if supplier not in supplier_stats:
                        supplier_stats[supplier] = {
                            'total_products': 0,
                            'average_price': 0,
                            'invoices_count': 0,
                            'total_amount': 0
                        }
                    
                    supplier_stats[supplier]['invoices_count'] += 1
                    amount = invoice['analysis'].get('total_amount')
                    if amount is not None:
                        supplier_stats[supplier]['total_amount'] += amount
        
        return supplier_stats
    
    def _calculate_category_stats(self, prices_df: pd.DataFrame) -> Dict:
        """Calculer les statistiques par catégorie"""
        category_stats = {}
        
        if prices_df.empty or 'categorie' not in prices_df.columns:
            return {
                'Autres': {
                    'product_count': len(prices_df),
                    'average_price': prices_df['prix'].mean() if not prices_df.empty and 'prix' in prices_df.columns else 0
                }
            }
        
        # Grouper par catégorie
        for category in prices_df['categorie'].fillna('Autres').unique():
            category_prices = prices_df[prices_df['categorie'].fillna('Autres') == category]
            category_stats[category] = {
                'product_count': len(category_prices),
                'average_price': category_prices['prix'].mean() if 'prix' in category_prices.columns else 0,
                'price_range': {
                    'min': category_prices['prix'].min() if 'prix' in category_prices.columns else 0,
                    'max': category_prices['prix'].max() if 'prix' in category_prices.columns else 0
                }
            }
        
        return category_stats
    
    def _calculate_trends(self, invoices_df: pd.DataFrame) -> Dict:
        """Calculer les tendances temporelles"""
        trends = {
            'invoices_by_day': {},
            'amount_by_day': {},
            'confidence_by_day': {}
        }
        
        if invoices_df.empty or 'created_at' not in invoices_df.columns:
            return trends
        
        # Convertir les dates
        invoices_df['created_at'] = pd.to_datetime(invoices_df['created_at'])
        
        # Derniers 30 jours
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_invoices = invoices_df[invoices_df['created_at'] >= thirty_days_ago]
        
        # Grouper par jour
        for _, invoice in recent_invoices.iterrows():
            day_key = invoice['created_at'].strftime('%Y-%m-%d')
            
            # Nombre de factures
            if day_key not in trends['invoices_by_day']:
                trends['invoices_by_day'][day_key] = 0
            trends['invoices_by_day'][day_key] += 1
            
            # Montant total
            if isinstance(invoice.get('analysis'), dict):
                amount = invoice['analysis'].get('total_amount')
                if amount is not None:
                    if day_key not in trends['amount_by_day']:
                        trends['amount_by_day'][day_key] = 0
                    trends['amount_by_day'][day_key] += amount
                
                # Score de confiance moyen
                confidence = invoice['analysis'].get('confidence_score', 0)
                if day_key not in trends['confidence_by_day']:
                    trends['confidence_by_day'][day_key] = []
                trends['confidence_by_day'][day_key].append(confidence)
        
        # Calculer les moyennes de confiance
        for day, scores in trends['confidence_by_day'].items():
            trends['confidence_by_day'][day] = sum(scores) / len(scores) if scores else 0
        
        return trends
    
    def _generate_alerts(self, prices_df: pd.DataFrame, invoices_df: pd.DataFrame) -> List[Dict]:
        """Générer des alertes et recommandations"""
        alerts = []
        
        # Alerte si peu de prix de référence
        if len(prices_df) < 50:
            alerts.append({
                'type': 'warning',
                'title': 'Base de prix limitée',
                'message': f'Seulement {len(prices_df)} prix de référence. Importez plus de données pour de meilleures comparaisons.',
                'priority': 'medium'
            })
        
        # Alerte si beaucoup de factures avec faible confiance
        if not invoices_df.empty:
            low_confidence_count = 0
            for _, invoice in invoices_df.iterrows():
                if isinstance(invoice.get('analysis'), dict):
                    if invoice['analysis'].get('confidence_score', 0) < 0.5:
                        low_confidence_count += 1
            
            if low_confidence_count > len(invoices_df) * 0.3:
                alerts.append({
                    'type': 'warning',
                    'title': 'Qualité d\'analyse faible',
                    'message': f'{low_confidence_count} factures avec un score de confiance faible. Vérifiez la qualité des images.',
                    'priority': 'high'
                })
        
        # Alerte sur les économies potentielles
        recent_overpayment = 0
        if not invoices_df.empty and 'created_at' in invoices_df.columns:
            week_ago = datetime.now() - timedelta(days=7)
            recent_invoices = invoices_df[pd.to_datetime(invoices_df['created_at']) >= week_ago]
            
            for _, invoice in recent_invoices.iterrows():
                if isinstance(invoice.get('analysis'), dict):
                    comparison = invoice['analysis'].get('price_comparison', {})
                    recent_overpayment += comparison.get('total_overpayment', 0)
        
        if recent_overpayment > 100:
            alerts.append({
                'type': 'info',
                'title': 'Économies potentielles détectées',
                'message': f'{recent_overpayment:.2f}€ de surpaiement détecté cette semaine. Négociez avec vos fournisseurs!',
                'priority': 'high'
            })
        
        # Alerte sur les prix obsolètes
        if not prices_df.empty and 'date_maj' in prices_df.columns:
            prices_df['date_maj'] = pd.to_datetime(prices_df['date_maj'])
            old_prices = prices_df[prices_df['date_maj'] < datetime.now() - timedelta(days=90)]
            
            if len(old_prices) > len(prices_df) * 0.2:
                alerts.append({
                    'type': 'warning',
                    'title': 'Prix obsolètes',
                    'message': f'{len(old_prices)} prix n\'ont pas été mis à jour depuis plus de 3 mois.',
                    'priority': 'low'
                })
        
        return alerts
    
    def _get_empty_stats(self) -> Dict:
        """Retourner des statistiques vides en cas d'erreur"""
        return {
            'overview': {
                'total_reference_prices': 0,
                'active_reference_prices': 0,
                'total_invoices_analyzed': 0,
                'total_products_analyzed': 0,
                'average_confidence_score': 0.0,
                'invoices_this_month': 0,
                'invoices_last_7_days': 0
            },
            'savings': {
                'total_savings': 0.0,
                'total_overpayment': 0.0,
                'net_savings': 0.0,
                'savings_by_month': {},
                'top_savings_products': []
            },
            'suppliers': {},
            'categories': {},
            'trends': {
                'invoices_by_day': {},
                'amount_by_day': {},
                'confidence_by_day': {}
            },
            'alerts': [],
            'last_update': datetime.now().isoformat(),
            'total_invoices': 0,
            'total_amount': 0,
            'total_savings': 0,
            'unique_suppliers': 0
        }

    def calculate_dashboard_stats(self, prices: List[Dict], invoices: List[Dict], pending_products: List[Dict]) -> Dict[str, Any]:
        """Calculer toutes les statistiques pour le dashboard"""
        try:
            stats = {
                'invoices_count': len(invoices),
                'invoices_growth': 0,
                'savings_amount': 0,
                'compared_products': 0,
                'alerts_count': 0,
                'critical_alerts': 0,
                'pending_count': len(pending_products),
                'recent_alerts': [],
                'recent_activity': [],
                'spending_chart_data': self._get_spending_chart_data(invoices),
                'supplier_chart_data': self._get_supplier_chart_data(invoices)
            }
            
            # Calculer les économies et alertes à partir des factures
            if invoices:
                savings_data = self._calculate_savings_and_alerts(invoices)
                stats.update(savings_data)
            
            # Calculer la croissance des factures
            stats['invoices_growth'] = self._calculate_invoices_growth(invoices)
            
            # Récupérer les alertes récentes
            stats['recent_alerts'] = self._get_recent_alerts(invoices)
            
            # Récupérer l'activité récente
            stats['recent_activity'] = self._get_recent_activity(invoices, pending_products)
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur calcul statistiques dashboard: {e}")
            return self._get_default_stats()
    
    def _calculate_savings_and_alerts(self, invoices: List[Dict]) -> Dict[str, Any]:
        """Calculer les économies et alertes à partir des factures"""
        total_savings = 0
        total_overpayment = 0
        compared_products = 0
        alerts_count = 0
        critical_alerts = 0
        
        for invoice in invoices:
            # Vérifier les différents formats de données
            analysis = invoice.get('analysis', {})
            price_comparison = analysis.get('price_comparison', {})
            
            if price_comparison:
                # Nouveau format avec price_comparison
                total_savings += price_comparison.get('total_savings', 0)
                total_overpayment += price_comparison.get('total_overpayment', 0)
                compared_products += price_comparison.get('compared_count', 0)
                
                # Compter les alertes (prix plus élevés)
                higher_prices = price_comparison.get('higher_prices', 0)
                alerts_count += higher_prices
                
                # Alertes critiques (différence > 20%)
                for product in price_comparison.get('comparison_details', []):
                    if product.get('status') == 'higher':
                        price_diff_percent = abs(product.get('price_difference_percent', 0))
                        if price_diff_percent > 20:
                            critical_alerts += 1
            
            # Format alternatif dans products
            products = analysis.get('products', [])
            for product in products:
                if 'price_comparison' in product:
                    compared_products += 1
                    status = product['price_comparison'].get('status')
                    if status == 'cheaper':
                        savings = product['price_comparison'].get('savings', 0)
                        total_savings += savings
                    elif status == 'expensive':
                        overpay = product['price_comparison'].get('overpayment', 0)
                        total_overpayment += overpay
                        alerts_count += 1
                        
                        # Alerte critique si différence > 20%
                        diff_percent = product['price_comparison'].get('difference_percent', 0)
                        if abs(diff_percent) > 20:
                            critical_alerts += 1
        
        return {
            'savings_amount': round(total_savings, 2),
            'overpayment_amount': round(total_overpayment, 2),
            'compared_products': compared_products,
            'alerts_count': alerts_count,
            'critical_alerts': critical_alerts
        }
    
    def _calculate_invoices_growth(self, invoices: List[Dict]) -> float:
        """Calculer la croissance du nombre de factures vs mois dernier"""
        try:
            now = datetime.now()
            current_month = now.replace(day=1)
            last_month = (current_month - timedelta(days=1)).replace(day=1)
            
            current_month_count = 0
            last_month_count = 0
            
            for invoice in invoices:
                date_str = invoice.get('date') or invoice.get('analysis', {}).get('date')
                if date_str:
                    try:
                        invoice_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        if invoice_date >= current_month:
                            current_month_count += 1
                        elif invoice_date >= last_month and invoice_date < current_month:
                            last_month_count += 1
                    except:
                        continue
            
            if last_month_count == 0:
                return 100 if current_month_count > 0 else 0
            
            growth = ((current_month_count - last_month_count) / last_month_count) * 100
            return round(growth, 1)
            
        except Exception as e:
            logger.error(f"Erreur calcul croissance: {e}")
            return 0
    
    def _get_spending_chart_data(self, invoices: List[Dict]) -> Dict[str, Any]:
        """Données pour le graphique d'évolution des dépenses"""
        try:
            # Données des 6 derniers mois
            spending_by_month = {}
            now = datetime.now()
            
            for i in range(6):
                month_date = now - timedelta(days=30*i)
                month_key = month_date.strftime('%Y-%m')
                month_label = month_date.strftime('%b %Y')
                spending_by_month[month_key] = {'label': month_label, 'amount': 0}
            
            for invoice in invoices:
                total = invoice.get('total') or invoice.get('analysis', {}).get('total', 0)
                date_str = invoice.get('date') or invoice.get('analysis', {}).get('date')
                
                if date_str and total:
                    try:
                        # Nettoyer le montant total
                        if isinstance(total, str):
                            total = float(total.replace('€', '').replace(',', '.').strip())
                        
                        invoice_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        month_key = invoice_date.strftime('%Y-%m')
                        
                        if month_key in spending_by_month:
                            spending_by_month[month_key]['amount'] += total
                    except:
                        continue
            
            # Convertir en format Chart.js
            sorted_months = sorted(spending_by_month.keys(), reverse=True)[:6]
            sorted_months.reverse()  # Ordre chronologique
            
            return {
                'labels': [spending_by_month[month]['label'] for month in sorted_months],
                'data': [round(spending_by_month[month]['amount'], 2) for month in sorted_months]
            }
            
        except Exception as e:
            logger.error(f"Erreur données graphique dépenses: {e}")
            return {'labels': [], 'data': []}
    
    def _get_supplier_chart_data(self, invoices: List[Dict]) -> Dict[str, Any]:
        """Données pour le graphique répartition par fournisseur"""
        try:
            supplier_totals = {}
            
            for invoice in invoices:
                supplier = invoice.get('supplier') or invoice.get('analysis', {}).get('supplier', 'Inconnu')
                total = invoice.get('total') or invoice.get('analysis', {}).get('total', 0)
                
                if total:
                    try:
                        # Nettoyer le montant total
                        if isinstance(total, str):
                            total = float(total.replace('€', '').replace(',', '.').strip())
                        
                        if supplier not in supplier_totals:
                            supplier_totals[supplier] = 0
                        supplier_totals[supplier] += total
                    except:
                        continue
            
            # Trier par montant décroissant et prendre les 5 premiers
            sorted_suppliers = sorted(supplier_totals.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return {
                'labels': [supplier for supplier, _ in sorted_suppliers],
                'data': [round(total, 2) for _, total in sorted_suppliers]
            }
            
        except Exception as e:
            logger.error(f"Erreur données graphique fournisseurs: {e}")
            return {'labels': [], 'data': []}
    
    def _get_recent_alerts(self, invoices: List[Dict]) -> List[Dict]:
        """Récupérer les alertes récentes"""
        alerts = []
        
        try:
            # Trier les factures par date décroissante
            sorted_invoices = sorted(invoices, 
                key=lambda x: x.get('date') or x.get('analysis', {}).get('date', ''), 
                reverse=True)
            
            for invoice in sorted_invoices[:10]:  # 10 dernières factures
                analysis = invoice.get('analysis', {})
                price_comparison = analysis.get('price_comparison', {})
                
                # Vérifier s'il y a des alertes
                if price_comparison.get('higher_prices', 0) > 0:
                    alerts.append({
                        'id': invoice.get('id', ''),
                        'supplier': analysis.get('supplier', 'Inconnu'),
                        'date': analysis.get('date', ''),
                        'alert_count': price_comparison.get('higher_prices', 0),
                        'overpayment': price_comparison.get('total_overpayment', 0)
                    })
                
                if len(alerts) >= 5:  # Limiter à 5 alertes
                    break
            
        except Exception as e:
            logger.error(f"Erreur récupération alertes: {e}")
        
        return alerts
    
    def _get_recent_activity(self, invoices: List[Dict], pending_products: List[Dict]) -> List[Dict]:
        """Récupérer l'activité récente"""
        activity = []
        
        try:
            # Activité des factures récentes
            sorted_invoices = sorted(invoices, 
                key=lambda x: x.get('date') or x.get('analysis', {}).get('date', ''), 
                reverse=True)
            
            for invoice in sorted_invoices[:3]:
                analysis = invoice.get('analysis', {})
                activity.append({
                    'type': 'invoice',
                    'title': f"Facture {analysis.get('supplier', 'Inconnu')}",
                    'description': f"Montant: {analysis.get('total', 0)}€",
                    'date': analysis.get('date', ''),
                    'icon': 'file-text'
                })
            
            # Activité des produits en attente récents
            sorted_pending = sorted(pending_products, 
                key=lambda x: x.get('date_ajout', ''), 
                reverse=True)
            
            for product in sorted_pending[:2]:
                activity.append({
                    'type': 'pending',
                    'title': f"Nouveau produit détecté",
                    'description': f"{product.get('produit', 'Produit')} - {product.get('fournisseur', 'Inconnu')}",
                    'date': product.get('date_ajout', ''),
                    'icon': 'clock-history'
                })
            
            # Trier par date
            activity.sort(key=lambda x: x.get('date', ''), reverse=True)
            
        except Exception as e:
            logger.error(f"Erreur récupération activité: {e}")
        
        return activity[:5]  # Limiter à 5 éléments
    
    def _get_default_stats(self) -> Dict[str, Any]:
        """Statistiques par défaut en cas d'erreur"""
        return {
            'invoices_count': 0,
            'invoices_growth': 0,
            'savings_amount': 0,
            'overpayment_amount': 0,
            'compared_products': 0,
            'alerts_count': 0,
            'critical_alerts': 0,
            'pending_count': 0,
            'recent_alerts': [],
            'recent_activity': [],
            'spending_chart_data': {'labels': [], 'data': []},
            'supplier_chart_data': {'labels': [], 'data': []}
        } 