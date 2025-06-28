#!/usr/bin/env python3
"""
Générateur de PDF pour les bons de commande FactureKiller V3
Utilise une approche simple avec des bibliothèques Python natives
"""

import os
import tempfile
from datetime import datetime
from typing import Dict, List
import json

class PDFGenerator:
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
    
    def generate_order_pdf(self, order_data: Dict) -> str:
        """
        Génère un PDF du bon de commande et retourne le chemin du fichier
        Pour l'instant, génère un fichier HTML stylisé qui peut être converti en PDF
        """
        try:
            # Créer le contenu HTML du bon de commande
            html_content = self._generate_order_html(order_data)
            
            # Sauvegarder dans un fichier temporaire
            order_number = order_data.get('order_number', 'commande')
            filename = f"bon_commande_{order_number}.html"
            file_path = os.path.join(self.temp_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return file_path
            
        except Exception as e:
            print(f"❌ Erreur génération PDF: {e}")
            return None
    
    def _generate_order_html(self, order_data: Dict) -> str:
        """Génère le HTML du bon de commande avec style print-friendly"""
        order_number = order_data.get('order_number', 'N/A')
        restaurant_name = order_data.get('restaurant_name', 'Restaurant')
        restaurant_address = order_data.get('restaurant_address', 'Adresse non renseignée')
        supplier_name = order_data.get('supplier', 'Fournisseur')
        created_date = datetime.now().strftime('%d/%m/%Y à %H:%M')
        delivery_date = order_data.get('delivery_date', 'Non définie')
        
        # Générer le tableau des produits
        products_rows = ""
        total_amount = 0
        
        for item in order_data.get('items', []):
            product_name = item.get('product_name', 'Produit')
            product_code = item.get('product_code', '')
            quantity = item.get('quantity', 0)
            unit_price = item.get('unit_price', 0)
            total_price = quantity * unit_price
            total_amount += total_price
            
            products_rows += f"""
                <tr>
                    <td>{product_name}</td>
                    <td>{product_code}</td>
                    <td>{quantity}</td>
                    <td>{unit_price:.2f}€</td>
                    <td><strong>{total_price:.2f}€</strong></td>
                </tr>
            """
        
        # Template HTML complet
        html_content = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bon de Commande {order_number}</title>
    <style>
        @media print {{
            body {{ margin: 0; }}
            .no-print {{ display: none; }}
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            color: #333;
            line-height: 1.4;
        }}
        
        .header {{
            text-align: center;
            border-bottom: 3px solid #2c5aa0;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        
        .logo {{
            font-size: 28px;
            font-weight: bold;
            color: #2c5aa0;
            margin-bottom: 5px;
        }}
        
        .logo-subtitle {{
            color: #666;
            font-size: 14px;
        }}
        
        .order-info {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 30px;
            gap: 30px;
        }}
        
        .info-section {{
            flex: 1;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #2c5aa0;
        }}
        
        .info-section h3 {{
            margin-top: 0;
            color: #2c5aa0;
            font-size: 16px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 8px;
        }}
        
        .info-section p {{
            margin: 8px 0;
        }}
        
        .info-section strong {{
            color: #333;
        }}
        
        .products-section {{
            margin-top: 30px;
        }}
        
        .products-section h3 {{
            color: #2c5aa0;
            border-bottom: 2px solid #2c5aa0;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        
        .products-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .products-table th {{
            background: #2c5aa0;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        
        .products-table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #eee;
        }}
        
        .products-table tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        
        .products-table tr:hover {{
            background: #e3f2fd;
        }}
        
        .total-section {{
            text-align: right;
            margin-top: 20px;
            padding: 15px;
            background: #f0f8ff;
            border-radius: 8px;
            border: 2px solid #2c5aa0;
        }}
        
        .total-amount {{
            font-size: 20px;
            font-weight: bold;
            color: #2c5aa0;
        }}
        
        .footer {{
            margin-top: 40px;
            text-align: center;
            font-size: 12px;
            color: #666;
            border-top: 1px solid #ddd;
            padding-top: 20px;
        }}
        
        .order-number {{
            font-size: 24px;
            font-weight: bold;
            color: #2c5aa0;
            text-align: center;
            margin: 20px 0;
            padding: 15px;
            background: #f0f8ff;
            border-radius: 8px;
            border: 2px solid #2c5aa0;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🧾 FactureKiller</div>
        <div class="logo-subtitle">Système de Gestion des Commandes</div>
    </div>
    
    <div class="order-number">
        BON DE COMMANDE {order_number}
    </div>
    
    <div class="order-info">
        <div class="info-section">
            <h3>📍 Adresse de Livraison</h3>
            <p><strong>{restaurant_name}</strong></p>
            <p>{restaurant_address}</p>
        </div>
        
        <div class="info-section">
            <h3>📋 Informations Commande</h3>
            <p><strong>Fournisseur:</strong> {supplier_name}</p>
            <p><strong>Date commande:</strong> {created_date}</p>
            <p><strong>Livraison prévue:</strong> {delivery_date}</p>
        </div>
    </div>
    
    <div class="products-section">
        <h3>📦 Détail des Produits Commandés</h3>
        <table class="products-table">
            <thead>
                <tr>
                    <th>Produit</th>
                    <th>Code</th>
                    <th>Quantité</th>
                    <th>Prix Unitaire</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
                {products_rows}
            </tbody>
        </table>
        
        <div class="total-section">
            <div class="total-amount">
                TOTAL COMMANDE: {total_amount:.2f}€
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p>Document généré automatiquement par FactureKiller V3</p>
        <p>Pour toute question, veuillez contacter {restaurant_name}</p>
    </div>
</body>
</html>
        """
        
        return html_content
    
    def cleanup_temp_file(self, file_path: str):
        """Nettoyer le fichier temporaire après utilisation"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🧹 Fichier temporaire supprimé: {file_path}")
        except Exception as e:
            print(f"⚠️ Erreur suppression fichier temporaire: {e}") 