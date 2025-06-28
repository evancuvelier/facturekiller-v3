#!/usr/bin/env python3
"""
Script de démarrage production FactureKiller V3
Démarre l'application avec toutes les vérifications nécessaires
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path

def print_banner():
    """Affiche la bannière de démarrage"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║        🚀 FACTUREKILLER V3 - DÉMARRAGE PRODUCTION 🚀        ║
    ║                                                              ║
    ║   ✨ Scanner IA Claude Vision                                ║
    ║   📊 Édition simple des produits                            ║
    ║   ⚠️  Gestion automatique des anomalies                     ║
    ║   💾 Sauvegarde intelligente avec rappels                   ║
    ║   🎯 Interface optimisée et guides d'aide                   ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_dependencies():
    """Vérifie les dépendances"""
    print("🔍 Vérification des dépendances...")
    
    required_files = [
        "main.py",
        "config.py", 
        "database.py",
        "templates/scanner.html",
        "static/js/scanner-pro.js",
        "static/js/simple-edit-functions.js"
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("❌ Fichiers manquants:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    print("✅ Tous les fichiers requis sont présents")
    return True

def check_port():
    """Vérifie si le port 5003 est libre"""
    print("🔌 Vérification du port 5003...")
    
    try:
        result = subprocess.run(['lsof', '-ti:5003'], capture_output=True, text=True)
        if result.stdout.strip():
            print("⚠️  Le port 5003 est occupé. Tentative de libération...")
            subprocess.run(['kill', '-9'] + result.stdout.strip().split('\n'), 
                         capture_output=True)
            time.sleep(2)
            print("✅ Port libéré")
        else:
            print("✅ Port 5003 disponible")
        return True
    except:
        print("ℹ️  Impossible de vérifier le port (normal sur certains systèmes)")
        return True

def start_application():
    """Démarre l'application"""
    print("🚀 Démarrage de FactureKiller V3...")
    
    try:
        # Variables d'environnement
        env = os.environ.copy()
        env['FLASK_ENV'] = 'production'
        env['FLASK_DEBUG'] = '0'
        
        # Démarrage
        process = subprocess.Popen(
            [sys.executable, 'main.py'],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Attendre que l'application démarre
        print("⏳ Démarrage en cours...")
        
        startup_timeout = 10
        for i in range(startup_timeout):
            if process.poll() is not None:
                print("❌ L'application s'est arrêtée prématurément")
                return None
            
            # Lire la sortie
            try:
                line = process.stdout.readline()
                if line:
                    print(f"📱 {line.strip()}")
                    if "Serving Flask app" in line:
                        print("✅ Application démarrée avec succès !")
                        break
            except:
                pass
            
            time.sleep(1)
        
        return process
        
    except Exception as e:
        print(f"❌ Erreur lors du démarrage: {e}")
        return None

def show_startup_info():
    """Affiche les informations de démarrage"""
    info = """
    🌐 APPLICATION DÉMARRÉE AVEC SUCCÈS !
    
    📍 URLs d'accès :
       • Dashboard    : http://localhost:5003/
       • Scanner      : http://localhost:5003/scanner  
       • Commandes    : http://localhost:5003/commandes
       • Factures     : http://localhost:5003/factures
    
    👤 Connexion par défaut :
       • Utilisateur  : admin
       • Mot de passe : motdepasse123
    
    🔧 Fonctionnalités principales :
       ✨ Scanner de factures avec IA Claude Vision
       📝 Édition simple des produits (bouton "Éditer")
       ⚠️  Création automatique d'anomalies
       💾 Rappels de sauvegarde automatiques
       🆘 Guide d'aide intégré (bouton ? flottant)
    
    📋 Workflow recommandé :
       1️⃣  Scanner une facture (photo ou upload)
       2️⃣  Vérifier les résultats de l'IA  
       3️⃣  Éditer les produits si nécessaire
       4️⃣  ⚠️ SAUVEGARDER la facture (obligatoire !)
    
    🛑 Pour arrêter : Ctrl+C
    """
    print(info)

def signal_handler(signum, frame):
    """Gestionnaire de signal pour arrêt propre"""
    print("\n🛑 Arrêt de l'application en cours...")
    sys.exit(0)

def main():
    """Fonction principale"""
    print_banner()
    
    # Gestionnaire de signal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Vérifications
    if not check_dependencies():
        print("❌ Échec de la vérification des dépendances")
        sys.exit(1)
    
    if not check_port():
        print("❌ Problème de port")
        sys.exit(1)
    
    # Démarrage
    process = start_application()
    if not process:
        print("❌ Échec du démarrage")
        sys.exit(1)
    
    # Informations
    show_startup_info()
    
    # Boucle principale
    try:
        while True:
            if process.poll() is not None:
                print("❌ L'application s'est arrêtée")
                break
            
            # Lire et afficher la sortie
            try:
                line = process.stdout.readline()
                if line:
                    # Filtrer les logs trop verbeux
                    if not any(skip in line.lower() for skip in ['debug', 'info']):
                        print(f"📱 {line.strip()}")
            except:
                pass
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n🛑 Arrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
    finally:
        if process and process.poll() is None:
            print("🔄 Arrêt de l'application...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            print("✅ Application arrêtée")

if __name__ == "__main__":
    main() 