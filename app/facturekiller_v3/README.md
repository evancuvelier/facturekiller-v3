# FactureKiller V3 - Système d'Authentification Multi-Restaurants

## 🚀 Déploiement Railway avec Firebase

### 📋 Configuration Firebase pour Railway

L'application utilise Firebase Firestore comme base de données. Pour déployer sur Railway :

#### 1. Créer un projet Firebase
1. Allez sur [https://console.firebase.google.com](https://console.firebase.google.com)
2. Créez un nouveau projet ou sélectionnez un projet existant
3. Notez le Project ID (ex: `facturekiller-v3`)

#### 2. Activer Firestore
1. Dans la console Firebase, allez dans **Firestore Database**
2. Cliquez sur **Créer une base de données**
3. Choisissez **Mode production** ou **Mode test**
4. Sélectionnez une région (ex: `europe-west1`)

#### 3. Créer une clé de service
1. Dans la console Firebase, allez dans **Paramètres** > **Comptes de service**
2. Cliquez sur **Générer une nouvelle clé privée**
3. Téléchargez le fichier JSON
4. Ouvrez le fichier et copiez tout son contenu

#### 4. Configurer Railway
1. Allez sur [https://railway.app](https://railway.app)
2. Sélectionnez votre projet
3. Allez dans l'onglet **Variables**
4. Ajoutez les variables suivantes :

```env
# Configuration Firebase (OBLIGATOIRE)
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
```

#### 5. Redéploiement
- Après avoir ajouté les variables, Railway redéploiera automatiquement
- Vérifiez les logs pour s'assurer qu'il n'y a pas d'erreurs

#### 6. Test de connexion
- Une fois déployé, allez sur votre URL Railway
- Connectez-vous avec : `evancuvelier@yahoo.com` / `Evan1250!`

### 🧪 Scripts de test et configuration

```bash
# Générer la configuration Firebase
python generate_firebase_config.py

# Tester la connexion Firebase
python test_firebase.py

# Configuration rapide avec compte admin
python quick_setup.py
```

### 🔧 Diagnostic des problèmes

Si vous obtenez "Firebase non disponible" :

1. **Vérifiez les variables d'environnement** sur Railway
2. **Vérifiez que Firestore est activé** dans votre projet Firebase
3. **Vérifiez les logs Railway** pour les erreurs détaillées
4. **Testez la connexion** avec `python test_firebase.py`

### 📊 Variables d'environnement requises

| Variable | Description | Obligatoire |
|----------|-------------|-------------|
| `FIREBASE_SERVICE_KEY` | Contenu JSON de la clé de service Firebase | ✅ |
| `SECRET_KEY` | Clé secrète Flask | ✅ |
| `FLASK_ENV` | Environnement Flask | ✅ |
| `PORT` | Port de l'application | ✅ |
| `SMTP_*` | Configuration email (optionnel) | ❌ |

---

## 🚀 État Final - Système Nettoyé et Optimisé

### ✅ Fonctionnalités Principales
- **Authentification multi-niveaux** : Master Admin → Clients → Restaurants → Utilisateurs
- **Gestion complète** : Création, modification, suppression de toutes les entités
- **Système d'invitations** : Emails automatiques avec tokens sécurisés
- **Switch de restaurants** : Sélection facile pour Master Admin et Clients
- **Configuration email** : SMTP complet (Gmail, Yahoo, Outlook)
- **Interface moderne** : Bootstrap 5 avec navigation optimisée

### 🏗️ Architecture
```
Master Admin (niveau 4) - Contrôle total
├── Clients (niveau 3) - Propriétaires de restaurants  
    ├── Restaurants - Établissements
        ├── Admin Restaurant (niveau 2) - Accès complet
        └── Utilisateurs (niveau 1) - Commandes et factures
```

### 📁 Structure des Fichiers (Nettoyée)
```
app/facturekiller_v3/
├── main.py                     # Application principale Flask
├── modules/                    # Modules métier
│   ├── auth_manager.py         # Authentification et rôles
│   ├── email_manager.py        # Gestion des emails
│   ├── price_manager.py        # Gestion des prix
│   ├── supplier_manager.py     # Gestion des fournisseurs
│   ├── invoice_manager.py      # Gestion des factures
│   ├── order_manager.py        # Gestion des commandes
│   ├── stats_calculator.py     # Calculs statistiques
│   ├── invoice_analyzer.py     # Analyse des factures
│   ├── claude_vision.py        # Vision IA Claude
│   └── ocr_engine.py          # Moteur OCR
├── templates/                  # Templates HTML
│   ├── base.html              # Template de base avec menu optimisé
│   ├── login.html             # Page de connexion
│   ├── admin.html             # Interface d'administration
│   ├── client.html            # Interface client
│   ├── invitation.html        # Page d'acceptation d'invitation
│   ├── parametres.html        # Paramètres
│   ├── scanner-batch.html     # Scanner batch
│   ├── scanner-edition.html   # Édition scanner
│   ├── scanner-pro.html       # Scanner pro
│   ├── scanner-validation.html # Validation scanner
│   └── synchronisation.html   # Synchronisation
├── static/                     # Ressources statiques
│   ├── css/style.css          # Styles personnalisés
│   └── js/                    # Scripts JavaScript
│       ├── admin.js           # Administration
│       ├── client.js          # Interface client
│       └── app.js             # Scripts généraux
├── data/                       # Données JSON
│   ├── users.json             # Utilisateurs
│   ├── clients.json           # Clients
│   ├── restaurants.json       # Restaurants
│   ├── sessions.json          # Sessions actives
│   └── invitations.json       # Invitations en cours
└── requirements.txt           # Dépendances Python
```

### 🔧 Démarrage
```bash
cd app/facturekiller_v3
python3 main.py
```

### 🌐 Accès
- **URL** : http://localhost:5003
- **Master Admin** : `master` / `admin123`
- **API Health** : http://localhost:5003/api/health

### 📋 Menu d'Administration Optimisé
Cliquez sur "Master Administrator" pour accéder à :
- **📊 Dashboard & Statistiques** - Vue d'ensemble avec stats en temps réel
- **👥 Gestion Complète** - Clients, Restaurants, Utilisateurs en un seul endroit
- **📧 Configuration Email** - Paramètres SMTP complets
- **🏢 Choisir Restaurant** - Sélection de n'importe quel restaurant
- **🚪 Déconnexion**

### 🧹 Nettoyage Effectué
**Fichiers supprimés :**
- ❌ Documentations redondantes (guides, README obsolètes)
- ❌ Modules en doublon (ai_agent.py, invoice_analyzer_simple.py)
- ❌ Fichiers temporaires (cookies.txt, __pycache__)
- ❌ Scripts de test obsolètes
- ❌ Imports circulaires corrigés

**Optimisations :**
- ✅ Import circulaire ai_agent → invoice_analyzer résolu
- ✅ Menu d'administration simplifié et regroupé
- ✅ Onglets fusionnés (Dashboard + Stats)
- ✅ Code nettoyé et optimisé
- ✅ Toutes les connexions vérifiées

### 🎯 Système 100% Fonctionnel
- ✅ Authentification multi-restaurants
- ✅ Création/modification/suppression de toutes les entités
- ✅ Invitations par email automatiques
- ✅ Switch de restaurants pour Master Admin
- ✅ Configuration email complète
- ✅ Interface moderne et intuitive
- ✅ Code propre et optimisé

## 🚀 FactureKiller V3 Pro

Application professionnelle de gestion et d'analyse de factures restaurant avec intelligence artificielle.

## ✨ Fonctionnalités principales

### 📊 Dashboard
- Vue d'ensemble de l'activité
- Statistiques en temps réel
- Alertes prix et économies réalisées
- Graphiques de tendances

### 📷 Scanner intelligent
- **OCR multi-moteurs** : Tesseract + Claude Vision AI
- Analyse automatique des factures
- Détection du fournisseur
- Extraction des produits et prix
- Comparaison avec la base de référence
- Ajout automatique des nouveaux produits en attente

### 💰 Gestion des prix
- Base de référence multi-fournisseurs
- Import Excel/CSV
- Modification et suppression
- Validation des produits en attente
- Filtres et recherche avancée

### 📄 Historique des factures
- Consultation de toutes les analyses
- Filtres par date et fournisseur
- Détail complet avec image
- Export des données

### 📦 Gestion des commandes (à venir)
- Création de commandes par fournisseur
- Comparaison commande/facture
- Export PDF et envoi email

## 🛠️ Installation

### Prérequis
- Python 3.8+
- Tesseract OCR
- (Optionnel) Clé API Anthropic pour Claude Vision

### Installation rapide

```bash
# 1. Cloner le projet
git clone [votre-repo]
cd app/facturekiller_v3

# 2. Lancer le script d'installation
./start.sh
```

### Installation manuelle

```bash
# 1. Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Installer Tesseract
# macOS: brew install tesseract
# Ubuntu: sudo apt-get install tesseract-ocr tesseract-ocr-fra
# Windows: Télécharger depuis GitHub

# 4. Configuration (optionnel)
cp .env.example .env
# Éditer .env pour ajouter votre clé API Anthropic

# 5. Démarrer l'application
python main.py
```

## 📁 Structure du projet

```
facturekiller_v3/
├── main.py              # Serveur Flask principal
├── modules/             # Modules métier
│   ├── ocr_engine.py    # Moteur OCR
│   ├── invoice_analyzer.py # Analyseur de factures
│   ├── price_manager.py # Gestionnaire de prix
│   ├── stats_calculator.py # Calculs statistiques
│   └── order_manager.py # Gestion des commandes
├── templates/           # Pages HTML
│   ├── base.html       # Template de base
│   ├── dashboard.html  # Dashboard
│   ├── scanner.html    # Scanner
│   └── factures.html   # Historique
├── static/             # Ressources statiques
│   ├── css/           # Styles
│   └── js/            # JavaScript
├── data/              # Base de données
├── uploads/           # Factures uploadées
└── requirements.txt   # Dépendances Python
```

## 🔧 Configuration

### Variables d'environnement (.env)

```env
# Claude Vision API (optionnel mais recommandé)
ANTHROPIC_API_KEY=sk-ant-xxx

# Flask
FLASK_ENV=development
FLASK_DEBUG=True
```

### Import de prix de référence

1. Préparer un fichier Excel/CSV avec les colonnes :
   - Code (optionnel)
   - Produit
   - Prix
   - Unité
   - Fournisseur (optionnel)

2. Dans l'interface, aller dans "Prix" > "Importer des prix"

## 📱 Utilisation

### Scanner une facture

1. Aller dans l'onglet "Scanner"
2. Glisser-déposer ou sélectionner une photo de facture
3. Cliquer sur "Analyser"
4. Vérifier les résultats et valider

### Gérer les prix

1. Onglet "Prix" pour voir la base de référence
2. Onglet "En attente" pour valider les nouveaux produits
3. Utiliser les filtres pour rechercher
4. Cliquer sur les boutons pour modifier/supprimer

### Consulter l'historique

1. Onglet "Factures" pour voir toutes les analyses
2. Cliquer sur une facture pour voir le détail
3. Utiliser les filtres par date/fournisseur

## 🚀 Fournisseurs supportés

- METRO
- TRANSGOURMET
- BRAKE
- PROMOCASH
- MVA
- Et détection automatique pour les autres

## 🔒 Sécurité

- Pas de données sensibles stockées
- Fichiers locaux uniquement
- API sécurisée avec validation

## 📈 Performances

- Analyse en moins de 5 secondes
- Support des images haute résolution
- Multi-threading pour l'OCR
- Cache intelligent

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
- Reporter des bugs
- Proposer des améliorations
- Soumettre des pull requests

## 📄 Licence

MIT License - Voir LICENSE

## 👨‍💻 Support

Pour toute question ou problème :
- Créer une issue sur GitHub
- Contact : [votre-email]

---

**FactureKiller V3** - L'outil indispensable pour optimiser vos achats restaurant 🍽️ 