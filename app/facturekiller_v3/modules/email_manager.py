#!/usr/bin/env python3
"""
Gestionnaire d'emails pour FactureKiller V3
Envoi de notifications aux fournisseurs lors des commandes
"""

import smtplib
import ssl
import json
import os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Optional
import logging
from pathlib import Path
import secrets

# Import du générateur PDF
try:
    from .pdf_generator import PDFGenerator
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("⚠️ PDFGenerator non disponible, utilisation de l'email HTML simple")

logger = logging.getLogger(__name__)

class EmailManager:
    def __init__(self):
        # Initialiser Firestore
        try:
            from modules.firestore_db import get_client
            self._fs = get_client()
            self._fs_enabled = self._fs is not None
            if self._fs_enabled:
                print("✅ Firestore initialisé pour EmailManager")
            else:
                print("❌ Firestore non disponible pour EmailManager")
        except Exception as e:
            print(f"❌ Erreur initialisation Firestore EmailManager: {e}")
            self._fs_enabled = False
            self._fs = None
        
        # Charger la configuration depuis Firestore
        self.config = self._load_config()
        
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_username)
        self.from_name = os.getenv('FROM_NAME', 'FactureKiller V3')
    
    def _load_config(self) -> Dict:
        """Charger la configuration email depuis Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return {"enabled": False}
            
            doc = self._fs.collection('email_config').document('main').get()
            if doc.exists:
                return doc.to_dict()
            else:
                # Créer la configuration par défaut
                default_config = {
                    "enabled": False,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "email": "",
                    "password": "",
                    "sender_name": "FactureKiller",
                    "auto_send": True
                }
                self._fs.collection('email_config').document('main').set(default_config)
                return default_config
        except Exception as e:
            logger.error(f"Erreur chargement config email: {e}")
            return {"enabled": False}
    
    def save_config(self, config: Dict) -> bool:
        """Sauvegarder la configuration email dans Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return False
            
            # Si le mot de passe est masqué (contient uniquement des *), garder l'ancien
            password = config.get('password', '')
            if not password or password.strip() == '' or all(c == '*' for c in password.strip()):
                # Charger l'ancienne config et garder l'ancien mot de passe
                old_config = self._load_config()
                if old_config.get('password'):
                    config['password'] = old_config['password']
                    print(f"💾 Mot de passe préservé (masqué détecté: '{password}')")
            
            self._fs.collection('email_config').document('main').set(config)
            self.config = config
            return True
        except Exception as e:
            logger.error(f"Erreur sauvegarde config email: {e}")
            return False
    
    def test_connection(self) -> Dict[str, any]:
        """Tester la connexion SMTP avec la configuration actuelle"""
        if not self.config.get('enabled', False):
            return {'success': False, 'error': 'Service email désactivé'}
        
        try:
            context = ssl.create_default_context()
            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            server.starttls(context=context)
            server.login(self.config['email'], self.config['password'])
            server.quit()
            return {'success': True, 'message': 'Connexion SMTP réussie'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def test_connection_with_params(self, email: str, password: str, smtp_server: str = 'smtp.gmail.com', smtp_port: int = 587) -> Dict[str, any]:
        """Tester la connexion SMTP avec des paramètres temporaires"""
        try:
            context = ssl.create_default_context()
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls(context=context)
            server.login(email, password)
            server.quit()
            return {'success': True, 'message': 'Connexion SMTP réussie'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send_order_notification(self, order_data: Dict, supplier_email: str) -> Dict[str, any]:
        """Envoyer une notification de commande à un fournisseur avec PDF en pièce jointe"""
        try:
            # Nouveau format d'objet : "Nouvelle commande (nom du restaurant) - numero de commande"
            restaurant_name = order_data.get('restaurant_name', 'Restaurant')
            order_number = order_data.get('order_number', order_data.get('id', 'N/A'))
            subject = f"Nouvelle commande ({restaurant_name}) - {order_number}"
            
            # Générer l'email simple (sans le bon de commande intégré)
            html_content = self._generate_simple_order_email_html(order_data)
            
            # Générer le PDF du bon de commande si possible
            pdf_path = None
            if PDF_AVAILABLE:
                try:
                    pdf_generator = PDFGenerator()
                    pdf_path = pdf_generator.generate_order_pdf(order_data)
                    print(f"📄 PDF généré: {pdf_path}")
                except Exception as e:
                    print(f"⚠️ Erreur génération PDF: {e}")
            
            # Envoyer l'email avec ou sans pièce jointe
            if pdf_path:
                result = self._send_email_with_attachment(supplier_email, subject, html_content, pdf_path, f"bon_commande_{order_number}.html")
            else:
                # Fallback vers l'ancien format avec bon de commande intégré
                html_content = self._generate_order_email_html(order_data)
                result = self._send_email_generic(supplier_email, subject, html_content)
            
            # Nettoyer le fichier temporaire
            if pdf_path and PDF_AVAILABLE:
                try:
                    pdf_generator.cleanup_temp_file(pdf_path)
                except:
                    pass
            
            # Enregistrer la notification
            self._log_notification(order_data, supplier_email, 'order', 
                                 'sent' if result['success'] else 'failed', 
                                 result.get('error'))
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur envoi notification: {e}")
            return {'success': False, 'error': str(e)}
    
    def _send_email_generic(self, to_email: str, subject: str, html_content: str) -> Dict[str, any]:
        """Envoyer un email avec gestion de la simulation"""
        try:
            # Si pas de configuration SMTP ou service désactivé, simuler l'envoi
            if not self.config.get('enabled', False) or not self.config.get('email') or not self.config.get('password'):
                print(f"📧 EMAIL SIMULÉ vers {to_email}")
                print(f"📌 Sujet: {subject}")
                print(f"🔗 Contenu HTML généré avec succès")
                return {
                    'success': True,
                    'message': 'Email simulé (configuration SMTP manquante)',
                    'simulated': True
                }
            
            # Créer le message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.config.get('sender_name', 'FactureKiller V3')} <{self.config['email']}>"
            msg['To'] = to_email
            
            # Ajouter le contenu HTML
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Envoyer via SMTP
            context = ssl.create_default_context()
            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            server.starttls(context=context)
            server.login(self.config['email'], self.config['password'])
            server.sendmail(self.config['email'], to_email, msg.as_string())
            server.quit()
            
            return {
                'success': True,
                'message': 'Email envoyé avec succès'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur envoi email: {str(e)}'
            }
    
    def _generate_order_email_html(self, order_data: Dict) -> str:
        """Générer le contenu HTML de l'email de commande au nouveau format demandé"""
        # Récupérer les informations importantes
        order_number = order_data.get('order_number', order_data.get('id', 'N/A'))
        restaurant_name = order_data.get('restaurant_name', 'Restaurant')
        restaurant_address = order_data.get('restaurant_address', 'Adresse du restaurant non renseignée')
        
        # Générer le tableau des produits en pièce jointe
        products_html = ""
        total_amount = 0
        
        for product in order_data.get('items', []):  # Changé de 'products' à 'items'
            quantity = product.get('quantity', 0)
            unit_price = product.get('unit_price', 0)
            line_total = quantity * unit_price
            total_amount += line_total
            
            products_html += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: left;">{product.get('product_name', 'Produit')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: center;">{product.get('unit', 'unité')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">{unit_price:.2f}€</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: center;">{quantity}</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right; font-weight: bold;">{line_total:.2f}€</td>
            </tr>
            """
        
        # Logo FactureKiller en SVG
        logo_svg = """
        <svg width="200" height="60" viewBox="0 0 200 60" xmlns="http://www.w3.org/2000/svg">
            <rect width="200" height="60" fill="#2c3e50" rx="8"/>
            <text x="100" y="25" font-family="Arial, sans-serif" font-size="16" font-weight="bold" fill="#e74c3c" text-anchor="middle">FACTURE</text>
            <text x="100" y="45" font-family="Arial, sans-serif" font-size="16" font-weight="bold" fill="#3498db" text-anchor="middle">KILLER</text>
            <circle cx="20" cy="30" r="8" fill="#e74c3c"/>
            <circle cx="180" cy="30" r="8" fill="#3498db"/>
        </svg>
        """
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Nouvelle commande {order_number}</title>
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 700px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .logo {{ text-align: center; margin-bottom: 30px; }}
                .greeting {{ font-size: 16px; margin: 20px 0; line-height: 1.6; }}
                .order-info {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #3498db; }}
                .address {{ background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107; }}
                .attachment {{ background: #e8f5e8; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745; }}
                .products-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                .products-table th {{ background: #34495e; color: white; padding: 10px; text-align: left; font-size: 14px; }}
                .products-table td {{ padding: 8px; border-bottom: 1px solid #ddd; font-size: 14px; }}
                .total-row {{ background: #ecf0f1; font-weight: bold; }}
                .footer {{ margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px; text-align: center; color: #6c757d; }}
                .highlight {{ color: #2c3e50; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- Logo FactureKiller -->
                <div class="logo">
                    {logo_svg}
                </div>
                
                <!-- Message principal -->
                <div class="greeting">
                    <p>Bonjour,</p>
                    <p>Vous trouverez en pièce jointe le bon de commande <span class="highlight">{order_number}</span>.</p>
                </div>
                
                <!-- Adresse de livraison -->
                <div class="address">
                    <h3 style="margin: 0 0 10px 0; color: #856404;">📍 Adresse de livraison :</h3>
                    <p style="margin: 5px 0; font-weight: bold;">{restaurant_name}</p>
                    <p style="margin: 5px 0;">{restaurant_address}</p>
                </div>
                
                <!-- Bon de commande en pièce jointe -->
                <div class="attachment">
                    <h3 style="margin: 0 0 15px 0; color: #155724;">📋 Bon de commande {order_number}</h3>
                    
                    <div class="order-info">
                        <p><strong>Numéro de commande :</strong> {order_number}</p>
                        <p><strong>Restaurant :</strong> {restaurant_name}</p>
                        <p><strong>Date de commande :</strong> {datetime.now().strftime('%d/%m/%Y')}</p>
                        <p><strong>Date de livraison souhaitée :</strong> {order_data.get('delivery_date', datetime.now().strftime('%d/%m/%Y'))}</p>
                    </div>
                    
                    <!-- Détail des produits -->
                    <table class="products-table">
                        <thead>
                            <tr>
                                <th>Article</th>
                                <th style="text-align: center;">Conditionnement</th>
                                <th style="text-align: right;">Prix H.T</th>
                                <th style="text-align: center;">Quantité</th>
                                <th style="text-align: right;">Total H.T</th>
                            </tr>
                        </thead>
                        <tbody>
                            {products_html}
                        </tbody>
                        <tfoot>
                            <tr class="total-row">
                                <td colspan="4" style="text-align: right; padding: 12px;"><strong>Total H.T</strong></td>
                                <td style="text-align: right; padding: 12px;"><strong>{total_amount:.2f}€</strong></td>
                            </tr>
                        </tfoot>
                    </table>
                    
                    {f'<div style="margin: 15px 0; padding: 12px; background: #fff3cd; border-radius: 5px;"><strong>📝 Notes :</strong><br>{order_data.get("notes", "")}</div>' if order_data.get("notes") else ""}
                </div>
                
                <!-- Pied de page -->
                <div class="footer">
                    <p style="margin: 0;">
                        <strong>Email généré automatiquement par FactureKiller</strong><br>
                        Merci de confirmer la réception de cette commande
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    def _log_notification(self, order_data: Dict, email: str, notification_type: str, status: str, error: str = None):
        """Enregistrer une notification dans l'historique Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return
            
            notification = {
                'timestamp': datetime.now().isoformat(),
                'order_id': order_data.get('id', ''),
                'supplier': order_data.get('supplier', ''),
                'email': email,
                'type': notification_type,
                'status': status,
                'error': error or ''
            }
            
            # Sauvegarder dans Firestore
            notification_id = f"notif_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self._fs.collection('email_notifications').document(notification_id).set(notification)
                
        except Exception as e:
            logger.error(f"Erreur log notification: {e}")
    
    def get_notifications_history(self, limit: int = 50) -> List[Dict]:
        """Récupérer l'historique des notifications depuis Firestore"""
        try:
            if not self._fs_enabled or not self._fs:
                return []
            
            docs = list(self._fs.collection('email_notifications').order_by('timestamp', direction='desc').limit(limit).stream())
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Erreur récupération historique: {e}")
            return []
    
    def get_config(self) -> Dict:
        """Récupérer la configuration actuelle (sans le mot de passe)"""
        config = self.config.copy()
        if 'password' in config:
            config['password'] = '***' if config['password'] else ''
        return config
    
    def get_config_raw(self) -> Dict:
        """Récupérer la configuration complète (avec le mot de passe)"""
        return self.config.copy()
    
    def is_enabled(self) -> bool:
        """Vérifier si le service email est activé"""
        return (self.config.get('enabled', False) and 
                bool(self.config.get('email')) and 
                bool(self.config.get('password')))
    
    def _load_invitations(self):
        """Charger les invitations depuis le fichier"""
        try:
            if self.invitations_file.exists():
                with open(self.invitations_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Erreur chargement invitations: {e}")
            return []
    
    def _save_invitations(self, invitations):
        """Sauvegarder les invitations dans le fichier"""
        try:
            with open(self.invitations_file, 'w', encoding='utf-8') as f:
                json.dump(invitations, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur sauvegarde invitations: {e}")
    
    def create_invitation(self, client_id, client_name, client_email, invited_by):
        """Créer une invitation pour un client"""
        try:
            invitations = self._load_invitations()
            
            # Vérifier si une invitation existe déjà
            existing = next((inv for inv in invitations if inv['client_id'] == client_id and inv['status'] == 'pending'), None)
            if existing:
                return {
                    'success': False,
                    'error': 'Une invitation est déjà en attente pour ce client'
                }
            
            # Générer un token unique
            token = secrets.token_urlsafe(32)
            
            # Créer l'invitation
            invitation = {
                'id': len(invitations) + 1,
                'client_id': client_id,
                'client_name': client_name,
                'client_email': client_email,
                'token': token,
                'invited_by': invited_by,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=7)).isoformat(),
                'status': 'pending'  # pending, accepted, expired
            }
            
            invitations.append(invitation)
            self._save_invitations(invitations)
            
            return {
                'success': True,
                'invitation': invitation,
                'token': token
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur création invitation: {str(e)}'
            }
    
    def send_client_invitation(self, client_name, client_email, token, base_url='http://localhost:5003'):
        """Envoyer l'email d'invitation à un client"""
        try:
            # URL d'invitation
            invitation_url = f"{base_url}/invitation/{token}"
            
            # Contenu de l'email
            subject = f"🎉 Invitation à rejoindre FactureKiller V3 - {client_name}"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: white; padding: 30px; border: 1px solid #ddd; }}
                    .footer {{ background: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; }}
                    .btn {{ display: inline-block; background: #28a745; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                    .btn:hover {{ background: #218838; }}
                    .info-box {{ background: #e3f2fd; padding: 15px; border-left: 4px solid #2196f3; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🍽️ FactureKiller V3</h1>
                        <p>Système de gestion multi-restaurants</p>
                    </div>
                    
                    <div class="content">
                        <h2>Bonjour {client_name} ! 👋</h2>
                        
                        <p>Vous avez été invité(e) à rejoindre <strong>FactureKiller V3</strong>, notre plateforme de gestion multi-restaurants.</p>
                        
                        <div class="info-box">
                            <h3>🔑 Vos privilèges en tant que Client :</h3>
                            <ul>
                                <li>✅ Gérer vos restaurants</li>
                                <li>✅ Ajouter des utilisateurs (Admin/User) à vos restaurants</li>
                                <li>✅ Voir les statistiques de tous vos établissements</li>
                                <li>✅ Contrôler les permissions d'accès</li>
                            </ul>
                        </div>
                        
                        <p><strong>Pour créer votre compte, cliquez sur le bouton ci-dessous :</strong></p>
                        
                        <p style="text-align: center; margin: 30px 0;">
                            <a href="{invitation_url}" class="btn">🚀 Créer mon compte</a>
                        </p>
                        
                        <p><small>Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :<br>
                        <a href="{invitation_url}">{invitation_url}</a></small></p>
                        
                        <div class="info-box">
                            <p><strong>⏰ Cette invitation expire dans 7 jours.</strong></p>
                            <p>Si vous avez des questions, contactez votre administrateur.</p>
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p>© 2024 FactureKiller V3 - Système de gestion multi-restaurants</p>
                        <p><small>Cet email a été envoyé automatiquement, merci de ne pas répondre.</small></p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Envoyer l'email
            return self._send_email_generic(client_email, subject, html_content)
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur envoi invitation: {str(e)}'
            }
    
    def get_invitation_by_token(self, token):
        """Récupérer une invitation par son token"""
        try:
            invitations = self._load_invitations()
            invitation = next((inv for inv in invitations if inv['token'] == token), None)
            
            if not invitation:
                return {
                    'success': False,
                    'error': 'Invitation introuvable'
                }
            
            # Vérifier si l'invitation a expiré
            expires_at = datetime.fromisoformat(invitation['expires_at'])
            if datetime.now() > expires_at:
                invitation['status'] = 'expired'
                self._save_invitations(invitations)
                return {
                    'success': False,
                    'error': 'Invitation expirée'
                }
            
            return {
                'success': True,
                'invitation': invitation
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur récupération invitation: {str(e)}'
            }
    
    def accept_invitation(self, token):
        """Marquer une invitation comme acceptée"""
        try:
            invitations = self._load_invitations()
            invitation = next((inv for inv in invitations if inv['token'] == token), None)
            
            if invitation:
                invitation['status'] = 'accepted'
                invitation['accepted_at'] = datetime.now().isoformat()
                self._save_invitations(invitations)
                return True
            
            return False
            
        except Exception as e:
            print(f"Erreur acceptation invitation: {e}")
            return False
    
    def send_anomaly_notification(self, invoice_id: str, order_id: str, supplier: str, 
                                 anomalies: List[Dict], total_anomalies: int,
                                 recipient_email: str = None, custom_message: str = '') -> Dict[str, any]:
        """Envoyer une notification d'anomalie détectée"""
        try:
            # Email par défaut (configuré dans les paramètres)
            if not recipient_email:
                recipient_email = self.config.get('anomaly_notification_email', self.config.get('email', ''))
            
            if not recipient_email:
                return {'success': False, 'error': 'Aucun email de destination configuré pour les anomalies'}
            
            subject = f"🚨 ANOMALIE DÉTECTÉE - Facture {invoice_id} - {supplier}"
            html_content = self._generate_anomaly_email_html(
                invoice_id, order_id, supplier, anomalies, total_anomalies, custom_message
            )
            
            # Envoyer l'email
            result = self._send_email_generic(recipient_email, subject, html_content)
            
            # Enregistrer la notification
            self._log_notification(
                {'id': invoice_id, 'supplier': supplier, 'order_id': order_id}, 
                recipient_email, 'anomaly', 
                'sent' if result['success'] else 'failed', 
                result.get('error')
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur envoi notification anomalie: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_anomaly_email_html(self, invoice_id: str, order_id: str, supplier: str, 
                                   anomalies: List[Dict], total_anomalies: int, custom_message: str = '') -> str:
        """Générer le contenu HTML de l'email d'anomalie"""
        
        # Générer la liste des anomalies
        anomalies_html = ""
        critical_count = 0
        warning_count = 0
        
        for anomaly in anomalies:
            severity_icon = "🔴" if anomaly.get('severity') == 'critical' else "🟡"
            severity_class = "critical" if anomaly.get('severity') == 'critical' else "warning"
            
            if anomaly.get('severity') == 'critical':
                critical_count += 1
            else:
                warning_count += 1
            
            anomalies_html += f"""
            <tr class="{severity_class}">
                <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: center;">{severity_icon}</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{anomaly.get('type', 'Inconnu').title()}</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{anomaly.get('message', 'Aucun détail')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: center;">{anomaly.get('severity', 'unknown').title()}</td>
            </tr>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #dc3545, #c82333); color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }}
                .content {{ padding: 30px; }}
                .alert {{ background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .info-box {{ background-color: #e9ecef; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .anomaly-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .anomaly-table th {{ background-color: #6c757d; color: white; padding: 12px; text-align: left; }}
                .anomaly-table td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
                .critical {{ background-color: #f8d7da; }}
                .warning {{ background-color: #fff3cd; }}
                .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .stat-box {{ text-align: center; padding: 15px; background-color: #f8f9fa; border-radius: 5px; }}
                .footer {{ background-color: #6c757d; color: white; padding: 15px; text-align: center; border-radius: 0 0 8px 8px; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 ANOMALIE DÉTECTÉE</h1>
                    <p>Une ou plusieurs anomalies ont été détectées lors de la vérification d'une livraison</p>
                </div>
                
                <div class="content">
                    <div class="alert">
                        <strong>⚠️ Action requise :</strong> Des différences ont été constatées entre la commande et la livraison reçue.
                    </div>
                    
                    <div class="info-box">
                        <h3>📋 Informations de la facture</h3>
                        <p><strong>ID Facture :</strong> {invoice_id}</p>
                        <p><strong>ID Commande :</strong> {order_id}</p>
                        <p><strong>Fournisseur :</strong> {supplier}</p>
                        <p><strong>Date de détection :</strong> {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
                    </div>
                    
                    <div class="stats">
                        <div class="stat-box">
                            <h4>🔴 Critiques</h4>
                            <p style="font-size: 24px; margin: 0; color: #dc3545;">{critical_count}</p>
                        </div>
                        <div class="stat-box">
                            <h4>🟡 Avertissements</h4>
                            <p style="font-size: 24px; margin: 0; color: #ffc107;">{warning_count}</p>
                        </div>
                        <div class="stat-box">
                            <h4>📊 Total</h4>
                            <p style="font-size: 24px; margin: 0; color: #6c757d;">{len(anomalies)}</p>
                        </div>
                    </div>
                    
                    <h3>📝 Détail des anomalies</h3>
                    <table class="anomaly-table">
                        <thead>
                            <tr>
                                <th style="width: 60px;">Niveau</th>
                                <th style="width: 120px;">Type</th>
                                <th>Description</th>
                                <th style="width: 100px;">Sévérité</th>
                            </tr>
                        </thead>
                        <tbody>
                            {anomalies_html}
                        </tbody>
                    </table>
                    
                    {f'<div class="info-box"><h4>💬 Message personnalisé</h4><p>{custom_message}</p></div>' if custom_message else ''}
                    
                    <div style="margin-top: 30px; padding: 20px; background-color: #e3f2fd; border-radius: 5px;">
                        <h4>🔧 Actions recommandées :</h4>
                        <ul>
                            <li>Vérifier la facture dans FactureKiller V3</li>
                            <li>Contacter le fournisseur si nécessaire</li>
                            <li>Marquer l'anomalie comme résolue après traitement</li>
                        </ul>
                        <p><a href="http://localhost:5003/factures" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🔗 Accéder aux factures</a></p>
                    </div>
                </div>
                
                <div class="footer">
                    <p>FactureKiller V3 - Système de gestion automatisé des factures</p>
                    <p>Email généré automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _send_email_with_attachment(self, to_email: str, subject: str, html_content: str, attachment_path: str, attachment_name: str) -> Dict[str, any]:
        """Envoyer un email avec pièce jointe"""
        try:
            # Si pas de configuration SMTP ou service désactivé, simuler l'envoi
            if not self.config.get('enabled', False) or not self.config.get('email') or not self.config.get('password'):
                print(f"📧 EMAIL SIMULÉ vers {to_email}")
                print(f"📌 Sujet: {subject}")
                print(f"📎 Pièce jointe: {attachment_name}")
                print(f"🔗 Contenu HTML généré avec succès")
                return {
                    'success': True,
                    'message': 'Email avec pièce jointe simulé (configuration SMTP manquante)',
                    'simulated': True
                }
            
            # Créer le message
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = f"{self.config.get('sender_name', 'FactureKiller V3')} <{self.config['email']}>"
            msg['To'] = to_email
            
            # Ajouter le contenu HTML
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Ajouter la pièce jointe
            if os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {attachment_name}'
                )
                msg.attach(part)
            
            # Envoyer via SMTP
            context = ssl.create_default_context()
            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            server.starttls(context=context)
            server.login(self.config['email'], self.config['password'])
            server.sendmail(self.config['email'], to_email, msg.as_string())
            server.quit()
            
            return {
                'success': True,
                'message': 'Email avec pièce jointe envoyé avec succès'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur envoi email avec pièce jointe: {str(e)}'
            }

    def _generate_simple_order_email_html(self, order_data: Dict) -> str:
        """Générer un email simple avec juste le message et l'adresse de livraison (bon de commande en pièce jointe)"""
        # Récupérer les informations importantes
        order_number = order_data.get('order_number', order_data.get('id', 'N/A'))
        restaurant_name = order_data.get('restaurant_name', 'Restaurant')
        restaurant_address = order_data.get('restaurant_address', 'Adresse du restaurant non renseignée')
        
        # Logo FactureKiller en SVG
        logo_svg = """
        <svg width="200" height="60" viewBox="0 0 200 60" xmlns="http://www.w3.org/2000/svg">
            <rect width="200" height="60" fill="#2c3e50" rx="8"/>
            <text x="100" y="25" font-family="Arial, sans-serif" font-size="16" font-weight="bold" fill="#e74c3c" text-anchor="middle">FACTURE</text>
            <text x="100" y="45" font-family="Arial, sans-serif" font-size="16" font-weight="bold" fill="#3498db" text-anchor="middle">KILLER</text>
            <circle cx="20" cy="30" r="8" fill="#e74c3c"/>
            <circle cx="180" cy="30" r="8" fill="#3498db"/>
        </svg>
        """
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Nouvelle commande {order_number}</title>
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .logo {{ text-align: center; margin-bottom: 30px; }}
                .greeting {{ font-size: 16px; margin: 20px 0; line-height: 1.6; }}
                .address {{ background: #fff3cd; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107; }}
                .attachment-info {{ background: #d1ecf1; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #17a2b8; }}
                .footer {{ margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px; text-align: center; color: #6c757d; }}
                .highlight {{ color: #2c3e50; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- Logo FactureKiller -->
                <div class="logo">
                    {logo_svg}
                </div>
                
                <!-- Message principal -->
                <div class="greeting">
                    <p>Bonjour,</p>
                    <p>Vous trouverez en pièce jointe le bon de commande <span class="highlight">{order_number}</span>.</p>
                </div>
                
                <!-- Adresse de livraison -->
                <div class="address">
                    <h3 style="margin: 0 0 10px 0; color: #856404;">📍 Adresse de livraison :</h3>
                    <p style="margin: 5px 0; font-weight: bold;">{restaurant_name}</p>
                    <p style="margin: 5px 0;">{restaurant_address}</p>
                </div>
                
                <!-- Information pièce jointe -->
                <div class="attachment-info">
                    <h3 style="margin: 0 0 10px 0; color: #0c5460;">📎 Pièce jointe :</h3>
                    <p style="margin: 5px 0;">Le détail complet de la commande se trouve dans le fichier joint à cet email.</p>
                    <p style="margin: 5px 0; font-size: 14px; color: #6c757d;">Nom du fichier : <strong>bon_commande_{order_number}.html</strong></p>
                </div>
                
                <!-- Footer -->
                <div class="footer">
                    <p><strong>FactureKiller V3</strong> - Système de gestion des commandes</p>
                    <p>Cet email a été généré automatiquement. Pour toute question, contactez {restaurant_name}.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html 

    def send_credit_note(self, invoice_data: Dict, credit_items: List[Dict], supplier_email: str = '') -> Dict[str, any]:
        """Envoyer une demande d'avoir au fournisseur sur les écarts détectés"""
        try:
            if not credit_items:
                return {'success': False, 'error': 'Aucun écart à signaler'}

            # Si pas d'email fourni, tenter de récupérer depuis supplier manager
            if not supplier_email:
                try:
                    from modules.supplier_manager import SupplierManager
                    supplier_manager = SupplierManager()
                    supplier = supplier_manager.get_supplier_by_name(invoice_data.get('supplier', ''))
                    supplier_email = supplier.get('email', '') if supplier else ''
                except Exception:
                    supplier_email = ''

            if not supplier_email:
                return {'success': False, 'error': 'Email fournisseur manquant'}

            invoice_code = invoice_data.get('invoice_code', invoice_data.get('id', 'N/A'))
            subject = f"Demande d'avoir – Facture {invoice_code}"

            # Générer tableau HTML des écarts
            rows = ''
            total_credit = 0
            for item in credit_items:
                rows += f"<tr><td>{item.get('product')}</td><td>{item.get('issue')}</td><td style='text-align:right;'>{item.get('amount',0):.2f}€</td></tr>"
                total_credit += item.get('amount', 0)

            html_content = f"""
            <h3>Bonjour,</h3>
            <p>Suite à la livraison de la facture <strong>{invoice_code}</strong>, nous avons constaté les écarts suivants :</p>
            <table style='border-collapse:collapse;width:100%;'>
                <thead><tr><th style='text-align:left;border-bottom:1px solid #ccc;'>Produit</th><th style='text-align:left;border-bottom:1px solid #ccc;'>Écart</th><th style='text-align:right;border-bottom:1px solid #ccc;'>Montant avoir</th></tr></thead>
                <tbody>{rows}</tbody>
                <tfoot><tr><td colspan='2' style='text-align:right;font-weight:bold;'>Total</td><td style='text-align:right;font-weight:bold;'>{total_credit:.2f}€</td></tr></tfoot>
            </table>
            <p>Merci de bien vouloir émettre un avoir correspondant.</p>
            <p>Cordialement,<br>FactureKiller</p>
            """

            return self._send_email_generic(supplier_email, subject, html_content)

        except Exception as e:
            logger.error(f"Erreur envoi demande d'avoir: {e}")
            return {'success': False, 'error': str(e)} 