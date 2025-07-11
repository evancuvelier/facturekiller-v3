#!/usr/bin/env python3
"""
🔧 Configuration Firebase et création du compte admin
"""

import os
import json
from datetime import datetime
import getpass

def setup_firebase_credentials():
    """Configurer les credentials Firebase"""
    print("🔧 CONFIGURATION FIREBASE")
    print("=" * 50)
    
    # Demander les informations Firebase
    print("\n📋 Veuillez fournir vos informations Firebase :")
    
    # Option 1: Fichier de clé de service
    print("\n1️⃣ Option 1: Fichier de clé de service JSON")
    service_key_path = input("   Chemin vers le fichier service-account.json (ou laissez vide): ").strip()
    
    if service_key_path and os.path.exists(service_key_path):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = service_key_path
        print(f"✅ Fichier de clé configuré: {service_key_path}")
        return True
    
    # Option 2: JSON brut
    print("\n2️⃣ Option 2: JSON brut de la clé de service")
    print("   Collez le contenu JSON de votre clé de service Firebase :")
    print("   (Appuyez sur Ctrl+D quand vous avez fini)")
    
    try:
        lines = []
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass
    
    if lines:
        service_key_json = '\n'.join(lines)
        try:
            # Valider le JSON
            json.loads(service_key_json)
            os.environ['FIREBASE_SERVICE_KEY'] = service_key_json
            print("✅ JSON de clé configuré")
            return True
        except json.JSONDecodeError:
            print("❌ JSON invalide")
            return False
    
    print("❌ Aucune configuration Firebase fournie")
    return False

def test_firebase_connection():
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

def create_admin_user():
    """Créer le compte admin"""
    print("\n👤 CRÉATION DU COMPTE ADMIN")
    print("=" * 50)
    
    try:
        from modules.firestore_db import get_client
        from modules.auth_manager import AuthManager
        
        client = get_client()
        if not client:
            print("❌ Firebase non disponible")
            return False
        
        # Créer l'AuthManager
        auth_manager = AuthManager()
        
        # Informations du compte admin
        admin_email = "evancuvelier@yahoo.com"
        admin_password = "Evan1250!"
        admin_name = "Evan Cuvelier"
        
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
        user_data = {
            'id': user_id,
            'username': admin_email.split('@')[0],
            'email': admin_email,
            'name': admin_name,
            'password': auth_manager._hash_password(admin_password),
            'role': 'admin',
            'active': True,
            'created_at': datetime.now().isoformat(),
            'client_id': None,
            'restaurant_id': None
        }
        
        # Créer l'utilisateur
        client.collection('users').document(user_id).set(user_data)
        
        if user_id:
            print(f"✅ Compte admin créé avec succès!")
            print(f"   ID: {user_id}")
            print(f"   Email: {admin_email}")
            print(f"   Rôle: admin")
            return True
        else:
            print("❌ Erreur lors de la création du compte admin")
            return False
            
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

def main():
    """Script principal"""
    print("🚀 CONFIGURATION COMPLÈTE FIREBASE")
    print("=" * 60)
    
    # 1. Configurer Firebase
    if not setup_firebase_credentials():
        print("\n❌ Configuration Firebase échouée")
        return
    
    # 2. Tester la connexion
    if not test_firebase_connection():
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