#!/usr/bin/env python3
"""
🔧 Générateur de configuration Firebase pour Railway
Ce script aide à configurer Firebase pour le déploiement Railway
"""

import json
import os
from datetime import datetime

def generate_railway_config():
    """Générer la configuration Railway pour Firebase"""
    print("🚀 GÉNÉRATEUR DE CONFIGURATION RAILWAY")
    print("=" * 60)
    
    print("\n📋 INSTRUCTIONS POUR CONFIGURER FIREBASE SUR RAILWAY:")
    print("=" * 60)
    
    print("\n1️⃣ CRÉER UN PROJET FIREBASE:")
    print("   - Allez sur https://console.firebase.google.com")
    print("   - Créez un nouveau projet ou sélectionnez un projet existant")
    print("   - Notez le Project ID (ex: facturekiller-v3)")
    
    print("\n2️⃣ ACTIVER FIRESTORE:")
    print("   - Dans la console Firebase, allez dans 'Firestore Database'")
    print("   - Cliquez sur 'Créer une base de données'")
    print("   - Choisissez 'Mode production' ou 'Mode test'")
    print("   - Sélectionnez une région (ex: europe-west1)")
    
    print("\n3️⃣ CRÉER UNE CLÉ DE SERVICE:")
    print("   - Dans la console Firebase, allez dans 'Paramètres' > 'Comptes de service'")
    print("   - Cliquez sur 'Générer une nouvelle clé privée'")
    print("   - Téléchargez le fichier JSON")
    print("   - Ouvrez le fichier et copiez tout son contenu")
    
    print("\n4️⃣ CONFIGURER RAILWAY:")
    print("   - Allez sur https://railway.app")
    print("   - Sélectionnez votre projet")
    print("   - Allez dans l'onglet 'Variables'")
    print("   - Ajoutez les variables suivantes:")
    
    print("\n📝 VARIABLES À AJOUTER SUR RAILWAY:")
    print("=" * 40)
    
    variables = {
        "FIREBASE_SERVICE_KEY": "COLLEZ_ICI_LE_CONTENU_JSON_DE_VOTRE_CLE_DE_SERVICE",
        "SECRET_KEY": "facturekiller-v3-secret-key-2025-production",
        "FLASK_ENV": "production",
        "PORT": "8000"
    }
    
    for key, value in variables.items():
        print(f"   {key} = {value}")
    
    print("\n5️⃣ REDÉPLOIEMENT:")
    print("   - Après avoir ajouté les variables, Railway redéploiera automatiquement")
    print("   - Vérifiez les logs pour s'assurer qu'il n'y a pas d'erreurs")
    
    print("\n6️⃣ TEST DE CONNEXION:")
    print("   - Une fois déployé, allez sur votre URL Railway")
    print("   - Connectez-vous avec: evancuvelier@yahoo.com / Evan1250!")
    
    print("\n" + "=" * 60)
    print("🎯 RÉSUMÉ DES ÉTAPES:")
    print("1. Créer projet Firebase")
    print("2. Activer Firestore")
    print("3. Télécharger clé de service")
    print("4. Ajouter FIREBASE_SERVICE_KEY sur Railway")
    print("5. Redéployer")
    print("6. Tester la connexion")
    
    return variables

def create_env_example():
    """Créer un fichier .env.example avec les variables nécessaires"""
    env_content = """# Configuration Firebase pour Railway
# Copiez le contenu JSON de votre clé de service Firebase ici
FIREBASE_SERVICE_KEY={"type":"service_account","project_id":"votre-projet-id",...}

# Configuration Flask
SECRET_KEY=facturekiller-v3-secret-key-2025-production
FLASK_ENV=production
PORT=8000

# Configuration SMTP (optionnel)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=votre-email@gmail.com
SMTP_PASSWORD=votre-mot-de-passe-app
FROM_EMAIL=votre-email@gmail.com
FROM_NAME=FactureKiller
"""
    
    with open('.env.example', 'w') as f:
        f.write(env_content)
    
    print("\n✅ Fichier .env.example créé avec les variables nécessaires")

def main():
    """Script principal"""
    print("🔧 GÉNÉRATEUR DE CONFIGURATION RAILWAY")
    print("=" * 60)
    
    # Générer la configuration
    variables = generate_railway_config()
    
    # Créer le fichier .env.example
    create_env_example()
    
    print("\n✅ Configuration générée avec succès!")
    print("\n📋 PROCHAINES ÉTAPES:")
    print("1. Suivez les instructions ci-dessus")
    print("2. Ajoutez FIREBASE_SERVICE_KEY sur Railway")
    print("3. Redéployez l'application")
    print("4. Testez la connexion")

if __name__ == "__main__":
    main() 