#!/usr/bin/env python3
"""
🔧 Configuration rapide Firebase et compte admin
"""

import os
import json
from datetime import datetime

def setup_firebase_env():
    """Configurer les variables d'environnement Firebase"""
    print("🔧 CONFIGURATION FIREBASE")
    print("=" * 50)
    
    # Instructions pour l'utilisateur
    print("\n📋 Pour configurer Firebase, vous devez :")
    print("1. Aller sur https://console.firebase.google.com")
    print("2. Créer un projet ou sélectionner un projet existant")
    print("3. Aller dans Paramètres > Comptes de service")
    print("4. Cliquer sur 'Générer une nouvelle clé privée'")
    print("5. Télécharger le fichier JSON")
    print("\n💡 Vous pouvez aussi utiliser la variable d'environnement FIREBASE_SERVICE_KEY")
    
    # Vérifier si les variables sont déjà configurées
    if os.getenv('GOOGLE_APPLICATION_CREDENTIALS') or os.getenv('FIREBASE_SERVICE_KEY'):
        print("\n✅ Variables Firebase déjà configurées!")
        return True
    
    print("\n❌ Variables Firebase non configurées")
    print("   Veuillez configurer GOOGLE_APPLICATION_CREDENTIALS ou FIREBASE_SERVICE_KEY")
    return False

def create_admin_user():
    """Créer le compte admin directement"""
    print("\n👤 CRÉATION DU COMPTE ADMIN")
    print("=" * 50)
    
    try:
        from modules.firestore_db import get_client
        
        client = get_client()
        if not client:
            print("❌ Firebase non disponible")
            print("   Veuillez configurer Firebase d'abord")
            return False
        
        # Informations du compte admin
        admin_email = "evancuvelier@yahoo.com"
        admin_password = "Evan1250!"
        admin_name = "Evan Cuvelier"
        admin_username = "evancuvelier"
        
        print(f"📧 Email: {admin_email}")
        print(f"👤 Nom: {admin_name}")
        print(f"🔑 Mot de passe: {admin_password}")
        
        # Vérifier si l'utilisateur existe déjà
        docs = list(client.collection('users').where('email', '==', admin_email).stream())
        if docs:
            existing_user = docs[0].to_dict()
            print(f"⚠️ L'utilisateur {admin_email} existe déjà")
            # Mettre à jour les permissions admin
            update_data = {
                'role': 'admin',
                'active': True
            }
            client.collection('users').document(existing_user['id']).update(update_data)
            print("✅ Permissions admin mises à jour")
            return True
        
        # Créer le nouvel utilisateur admin
        user_id = f"admin_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Hash du mot de passe
        import hashlib
        import secrets
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((admin_password + salt).encode()).hexdigest()
        hashed_password = f"{salt}:{password_hash}"
        
        user_data = {
            'id': user_id,
            'username': admin_username,
            'email': admin_email,
            'name': admin_name,
            'password': hashed_password,
            'role': 'admin',
            'active': True,
            'created_at': datetime.now().isoformat(),
            'client_id': None,
            'restaurant_id': None
        }
        
        # Créer l'utilisateur
        client.collection('users').document(user_id).set(user_data)
        
        print(f"✅ Compte admin créé avec succès!")
        print(f"   ID: {user_id}")
        print(f"   Email: {admin_email}")
        print(f"   Rôle: admin")
        return True
        
    except Exception as e:
        print(f"❌ Erreur création admin: {e}")
        return False

def create_initial_data():
    """Créer les données initiales"""
    print("\n📊 CRÉATION DES DONNÉES INITIALES")
    print("=" * 50)
    
    try:
        from modules.firestore_db import get_client
        
        client = get_client()
        if not client:
            print("❌ Firebase non disponible")
            return False
        
        # Créer un restaurant par défaut
        default_restaurant = {
            'id': 'default_restaurant',
            'name': 'Restaurant Principal',
            'address': 'Adresse du restaurant',
            'phone': '',
            'email': '',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'active': True,
            'sync_settings': {
                'sync_enabled': False,
                'sync_suppliers': False,
                'sync_prices': False
            }
        }
        
        client.collection('restaurants').document('default_restaurant').set(default_restaurant)
        print("✅ Restaurant par défaut créé")
        
        # Créer la configuration email par défaut
        email_config = {
            'enabled': False,
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'email': '',
            'password': '',
            'sender_name': 'FactureKiller',
            'auto_send': True
        }
        
        client.collection('email_config').document('main').set(email_config)
        print("✅ Configuration email créée")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur création données initiales: {e}")
        return False

def test_connection():
    """Tester la connexion Firebase"""
    print("\n🧪 TEST DE CONNEXION FIREBASE")
    print("=" * 50)
    
    try:
        from modules.firestore_db import get_client, available
        
        if available():
            client = get_client()
            if client:
                print(f"✅ Connexion Firebase réussie!")
                print(f"   Projet: {client.project}")
                return True
            else:
                print("❌ Client Firebase non disponible")
                return False
        else:
            print("❌ Impossible de se connecter à Firebase")
            print("   Vérifiez vos credentials")
            return False
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return False

def main():
    """Script principal"""
    print("🚀 CONFIGURATION RAPIDE FIREBASE")
    print("=" * 60)
    
    # 1. Vérifier la configuration Firebase
    if not setup_firebase_env():
        print("\n❌ Configuration Firebase manquante")
        print("\n📋 INSTRUCTIONS:")
        print("1. Configurez les variables d'environnement Firebase")
        print("2. Relancez ce script")
        return
    
    # 2. Tester la connexion
    if not test_connection():
        print("\n❌ Test de connexion échoué")
        return
    
    # 3. Créer le compte admin
    if not create_admin_user():
        print("\n❌ Création du compte admin échouée")
        return
    
    # 4. Créer les données initiales
    if not create_initial_data():
        print("\n❌ Création des données initiales échouée")
        return
    
    print("\n" + "=" * 60)
    print("🎉 CONFIGURATION TERMINÉE AVEC SUCCÈS!")
    print("\n📋 RÉCAPITULATIF:")
    print("✅ Firebase configuré et connecté")
    print("✅ Compte admin créé: evancuvelier@yahoo.com")
    print("✅ Données initiales créées")
    print("\n🔑 CONNEXION:")
    print("   Email: evancuvelier@yahoo.com")
    print("   Mot de passe: Evan1250!")
    print("   Rôle: Admin (toutes les permissions)")
    print("\n🚀 L'application est prête à être utilisée!")

if __name__ == "__main__":
    main() 