#!/usr/bin/env python3
"""
🧪 Test de connexion Firebase pour Railway
Ce script teste la connexion Firebase et diagnostique les problèmes
"""

import os
import json
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_environment():
    """Vérifier les variables d'environnement"""
    print("🔍 VÉRIFICATION DE L'ENVIRONNEMENT")
    print("=" * 50)
    
    # Variables Firebase
    firebase_vars = {
        "FIREBASE_SERVICE_KEY": os.getenv("FIREBASE_SERVICE_KEY"),
        "GOOGLE_APPLICATION_CREDENTIALS": os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
    }
    
    # Variables Flask
    flask_vars = {
        "SECRET_KEY": os.getenv("SECRET_KEY"),
        "FLASK_ENV": os.getenv("FLASK_ENV"),
        "PORT": os.getenv("PORT"),
    }
    
    print("\n📋 Variables Firebase:")
    for key, value in firebase_vars.items():
        if value:
            if key == "FIREBASE_SERVICE_KEY":
                # Afficher seulement les premiers caractères pour la sécurité
                preview = value[:50] + "..." if len(value) > 50 else value
                print(f"   ✅ {key}: {preview}")
            else:
                print(f"   ✅ {key}: {value}")
        else:
            print(f"   ❌ {key}: NON CONFIGURÉ")
    
    print("\n📋 Variables Flask:")
    for key, value in flask_vars.items():
        if value:
            print(f"   ✅ {key}: {value}")
        else:
            print(f"   ❌ {key}: NON CONFIGURÉ")
    
    # Vérifier si au moins une méthode Firebase est configurée
    has_firebase_config = bool(firebase_vars["FIREBASE_SERVICE_KEY"] or firebase_vars["GOOGLE_APPLICATION_CREDENTIALS"])
    
    if has_firebase_config:
        print("\n✅ Configuration Firebase détectée")
    else:
        print("\n❌ Aucune configuration Firebase trouvée")
        print("   Ajoutez FIREBASE_SERVICE_KEY sur Railway")
    
    return has_firebase_config

def test_firebase_connection():
    """Tester la connexion Firebase"""
    print("\n🧪 TEST DE CONNEXION FIREBASE")
    print("=" * 50)
    
    try:
        from modules.firestore_db import get_client, available
        
        if not available():
            print("❌ Firebase non disponible")
            print("   Vérifiez votre configuration")
            return False
        
        client = get_client()
        if not client:
            print("❌ Impossible d'initialiser le client Firebase")
            return False
        
        # Test de connexion
        try:
            # Lister les collections pour tester la connexion
            collections = list(client.collections())
            print(f"✅ Connexion Firebase réussie!")
            print(f"   Projet: {client.project}")
            print(f"   Collections trouvées: {len(collections)}")
            
            # Afficher les collections
            if collections:
                print("   Collections:")
                for collection in collections[:5]:  # Limiter à 5
                    print(f"     - {collection.id}")
                if len(collections) > 5:
                    print(f"     ... et {len(collections) - 5} autres")
            else:
                print("   Aucune collection trouvée (normal pour un nouveau projet)")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test de connexion: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Module google-cloud-firestore non installé: {e}")
        print("   Installez avec: pip install google-cloud-firestore")
        return False
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False

def create_test_data():
    """Créer des données de test"""
    print("\n📊 CRÉATION DE DONNÉES DE TEST")
    print("=" * 50)
    
    try:
        from modules.firestore_db import get_client
        
        client = get_client()
        if not client:
            print("❌ Client Firebase non disponible")
            return False
        
        # Créer un document de test
        test_data = {
            "test": True,
            "timestamp": datetime.now().isoformat(),
            "message": "Test de connexion Firebase"
        }
        
        # Écrire dans une collection de test
        doc_ref = client.collection('test_connection').document('railway_test')
        doc_ref.set(test_data)
        
        print("✅ Données de test créées avec succès")
        print("   Collection: test_connection")
        print("   Document: railway_test")
        
        # Vérifier la lecture
        doc = doc_ref.get()
        if doc.exists:
            print("✅ Lecture des données de test réussie")
            return True
        else:
            print("❌ Impossible de lire les données de test")
            return False
            
    except Exception as e:
        print(f"❌ Erreur création données de test: {e}")
        return False

def cleanup_test_data():
    """Nettoyer les données de test"""
    print("\n🧹 NETTOYAGE DES DONNÉES DE TEST")
    print("=" * 50)
    
    try:
        from modules.firestore_db import get_client
        
        client = get_client()
        if not client:
            print("❌ Client Firebase non disponible")
            return False
        
        # Supprimer le document de test
        doc_ref = client.collection('test_connection').document('railway_test')
        doc_ref.delete()
        
        print("✅ Données de test supprimées")
        return True
        
    except Exception as e:
        print(f"❌ Erreur nettoyage: {e}")
        return False

def main():
    """Script principal"""
    print("🧪 TEST DE CONNEXION FIREBASE POUR RAILWAY")
    print("=" * 60)
    
    # 1. Vérifier l'environnement
    has_config = check_environment()
    
    if not has_config:
        print("\n❌ Configuration Firebase manquante")
        print("\n📋 INSTRUCTIONS:")
        print("1. Allez sur Railway > Variables")
        print("2. Ajoutez FIREBASE_SERVICE_KEY avec votre clé de service JSON")
        print("3. Redéployez l'application")
        print("4. Relancez ce test")
        return
    
    # 2. Tester la connexion
    connection_ok = test_firebase_connection()
    
    if not connection_ok:
        print("\n❌ Test de connexion échoué")
        print("\n🔧 DIAGNOSTIC:")
        print("1. Vérifiez que votre clé de service est valide")
        print("2. Vérifiez que Firestore est activé dans votre projet Firebase")
        print("3. Vérifiez les logs Railway pour plus de détails")
        return
    
    # 3. Créer des données de test
    test_ok = create_test_data()
    
    if test_ok:
        # 4. Nettoyer les données de test
        cleanup_test_data()
        
        print("\n" + "=" * 60)
        print("🎉 TOUS LES TESTS RÉUSSIS!")
        print("\n✅ Firebase est correctement configuré")
        print("✅ La connexion fonctionne")
        print("✅ Les opérations de lecture/écriture fonctionnent")
        print("\n🚀 Votre application est prête!")
    else:
        print("\n❌ Test d'écriture échoué")
        print("   Vérifiez les permissions de votre clé de service")

if __name__ == "__main__":
    main() 