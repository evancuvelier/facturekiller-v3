import json
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import session, request, jsonify, redirect, url_for
import os
import uuid

class AuthManager:
    def __init__(self):
        self.users_file = 'data/users.json'
        self.clients_file = 'data/clients.json'
        self.restaurants_file = 'data/restaurants.json'
        self.sessions_file = 'data/sessions.json'
        
        # Créer les fichiers s'ils n'existent pas
        self._init_files()
        
        # Créer le master admin par défaut
        self._create_master_admin()
    
    def _init_files(self):
        """Initialise les fichiers de données"""
        files_data = {
            self.users_file: [],
            self.clients_file: [],
            self.restaurants_file: [],
            self.sessions_file: {}
        }
        
        for file_path, default_data in files_data.items():
            if not os.path.exists(file_path):
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, indent=2, ensure_ascii=False)
    
    def _create_master_admin(self):
        """Crée le master admin par défaut s'il n'existe pas"""
        users = self._load_users()
        
        # Vérifier si le master admin existe déjà
        master_exists = any(user.get('role') == 'master_admin' for user in users)
        
        if not master_exists:
            master_admin = {
                'id': 'master_001',
                'username': 'master',
                'email': 'admin@facturekiller.com',
                'password': self._hash_password('admin123'),
                'role': 'master_admin',
                'name': 'Master Administrator',
                'created_at': datetime.now().isoformat(),
                'active': True,
                'client_id': None,
                'restaurant_id': None
            }
            
            users.append(master_admin)
            self._save_users(users)
            print("🔐 Master admin créé - Username: master, Password: admin123")
    
    def _hash_password(self, password):
        """Hash un mot de passe avec salt"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{password_hash}"
    
    def _verify_password(self, password, hashed):
        """Vérifie un mot de passe"""
        try:
            salt, password_hash = hashed.split(':')
            return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash
        except:
            return False
    
    def _load_users(self):
        """Charge les utilisateurs"""
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def _save_users(self, users):
        """Sauvegarde les utilisateurs"""
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
    
    def _load_clients(self):
        """Charge les clients"""
        try:
            with open(self.clients_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def _save_clients(self, clients):
        """Sauvegarde les clients"""
        with open(self.clients_file, 'w', encoding='utf-8') as f:
            json.dump(clients, f, indent=2, ensure_ascii=False)
    
    def _load_restaurants(self):
        """Charge les restaurants"""
        try:
            with open(self.restaurants_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def _save_restaurants(self, restaurants):
        """Sauvegarde les restaurants"""
        with open(self.restaurants_file, 'w', encoding='utf-8') as f:
            json.dump(restaurants, f, indent=2, ensure_ascii=False)
    
    def login(self, username, password):
        """Connexion utilisateur"""
        users = self._load_users()
        
        for user in users:
            if (user['username'] == username or user['email'] == username) and user['active']:
                if self._verify_password(password, user['password']):
                    # Créer la session
                    session_token = secrets.token_urlsafe(32)
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['role'] = user['role']
                    session['client_id'] = user.get('client_id')
                    session['restaurant_id'] = user.get('restaurant_id')
                    session['token'] = session_token
                    
                    # Synchroniser le restaurant sélectionné pour les master admin
                    if user.get('role') == 'master_admin' and user.get('selected_restaurant_id'):
                        session['current_restaurant_id'] = user['selected_restaurant_id']
                        print(f"🏢 Restaurant sélectionné: {user['selected_restaurant_id']}")
                    
                    # Log de connexion
                    print(f"🔐 Connexion réussie: {user['username']} ({user['role']})")
                    
                    return {
                        'success': True,
                        'user': {
                            'id': user['id'],
                            'username': user['username'],
                            'name': user['name'],
                            'role': user['role'],
                            'client_id': user.get('client_id'),
                            'restaurant_id': user.get('restaurant_id')
                        }
                    }
        
        return {'success': False, 'error': 'Identifiants incorrects'}
    
    def logout(self):
        """Déconnexion"""
        session.clear()
        return {'success': True, 'message': 'Déconnecté avec succès'}
    
    def get_current_user(self):
        """Récupère l'utilisateur actuel"""
        if 'user_id' not in session:
            return None
        
        users = self._load_users()
        for user in users:
            if user['id'] == session['user_id']:
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'name': user['name'],
                    'role': user['role'],
                    'client_id': user.get('client_id'),
                    'restaurant_id': user.get('restaurant_id')
                }
        return None
    
    def create_client(self, name, email, contact_name, phone=None):
        """Créer un nouveau client"""
        try:
            clients = self._load_clients()
            
            # Vérifier si l'email existe déjà
            if any(c['email'] == email for c in clients):
                return {
                    'success': False,
                    'error': 'Un client avec cet email existe déjà'
                }
            
            # Générer un ID unique
            client_id = str(uuid.uuid4())
            
            # Créer le client
            new_client = {
                'id': client_id,
                'name': name,
                'email': email,
                'contact_name': contact_name,
                'phone': phone,
                'created_at': datetime.now().isoformat(),
                'active': True
            }
            
            # Ajouter et sauvegarder
            clients.append(new_client)
            self._save_clients(clients)
            
            return {
                'success': True,
                'client': new_client
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur création client: {str(e)}'
            }
    
    def create_restaurant(self, client_id, name, address, phone=None, email=None):
        """Créer un nouveau restaurant"""
        try:
            restaurants = self._load_restaurants()
            clients = self._load_clients()
            
            # Vérifier que le client existe
            if not any(c['id'] == client_id for c in clients):
                return {
                    'success': False,
                    'error': 'Client introuvable'
                }
            
            # Générer un ID unique
            restaurant_id = str(uuid.uuid4())
            
            # Créer le restaurant
            new_restaurant = {
                'id': restaurant_id,
                'client_id': client_id,
                'name': name,
                'address': address,
                'phone': phone,
                'email': email,
                'created_at': datetime.now().isoformat(),
                'active': True,
                'suppliers': []  # Liste des fournisseurs spécifiques à ce restaurant
            }
            
            # Ajouter et sauvegarder
            restaurants.append(new_restaurant)
            self._save_restaurants(restaurants)
            
            return {
                'success': True,
                'restaurant': new_restaurant
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur création restaurant: {str(e)}'
            }
    
    def create_user(self, username, email, password, name, role, client_id=None, restaurant_id=None):
        """Créer un nouvel utilisateur"""
        try:
            users = self._load_users()
            
            # Vérifier si le username ou email existe déjà
            if any(u['username'] == username for u in users):
                return {
                    'success': False,
                    'error': 'Ce nom d\'utilisateur existe déjà'
                }
            
            if any(u['email'] == email for u in users):
                return {
                    'success': False,
                    'error': 'Un utilisateur avec cet email existe déjà'
                }
            
            # Valider le rôle
            valid_roles = ['client', 'admin', 'user']
            if role not in valid_roles:
                return {
                    'success': False,
                    'error': 'Rôle invalide'
                }
            
            # Vérifier les contraintes selon le rôle
            if role in ['admin', 'user']:
                if not restaurant_id:
                    return {
                        'success': False,
                        'error': 'Un restaurant doit être assigné pour ce rôle'
                    }
                
                # Vérifier que le restaurant existe
                restaurants = self._load_restaurants()
                restaurant = next((r for r in restaurants if r['id'] == restaurant_id), None)
                if not restaurant:
                    return {
                        'success': False,
                        'error': 'Restaurant introuvable'
                    }
                
                # Pour admin/user, le client_id doit correspondre au propriétaire du restaurant
                client_id = restaurant['client_id']
            
            elif role == 'client':
                # Les clients peuvent être créés sans restaurant spécifique
                restaurant_id = None
            
            # Générer un ID unique et hasher le mot de passe
            user_id = str(uuid.uuid4())
            hashed_password = self._hash_password(password)
            
            # Créer l'utilisateur
            new_user = {
                'id': user_id,
                'username': username,
                'email': email,
                'password': hashed_password,
                'name': name,
                'role': role,
                'client_id': client_id,
                'restaurant_id': restaurant_id,
                'created_at': datetime.now().isoformat(),
                'active': True
            }
            
            # Ajouter et sauvegarder
            users.append(new_user)
            self._save_users(users)
            
            return {
                'success': True,
                'user': new_user
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur création utilisateur: {str(e)}'
            }
    
    def has_permission(self, required_role):
        """Vérifie les permissions de l'utilisateur actuel"""
        current_user = self.get_current_user()
        if not current_user:
            return False
        
        role_hierarchy = {
            'master_admin': 4,
            'client': 3,
            'admin': 2,
            'user': 1
        }
        
        user_level = role_hierarchy.get(current_user['role'], 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level
    
    def get_user_context(self):
        """Récupère le contexte complet de l'utilisateur (client, restaurant)"""
        from flask import session
        
        current_user = self.get_current_user()
        if not current_user:
            return None
        
        context = {
            'user': current_user,
            'client': None,
            'restaurant': None,
            'restaurants': []
        }
        
        # Charger le client si applicable
        if current_user.get('client_id'):
            clients = self._load_clients()
            context['client'] = next((c for c in clients if c['id'] == current_user['client_id']), None)
            
            # Charger tous les restaurants du client
            if context['client']:
                restaurants = self._load_restaurants()
                context['restaurants'] = [r for r in restaurants if r['client_id'] == current_user['client_id']]
        
        # Charger le restaurant spécifique
        restaurant_id = None
        
        # Pour les Master Admin, vérifier d'abord selected_restaurant_id puis la session
        if current_user.get('role') == 'master_admin':
            # Recharger l'utilisateur pour avoir les données les plus récentes
            users = self._load_users()
            user_data = next((u for u in users if u['id'] == current_user['id']), None)
            
            if user_data and user_data.get('selected_restaurant_id'):
                restaurant_id = user_data['selected_restaurant_id']
                # Synchroniser avec la session
                session['current_restaurant_id'] = restaurant_id
                print(f"🏢 Restaurant trouvé dans selected_restaurant_id: {restaurant_id}")
            else:
                restaurant_id = session.get('current_restaurant_id')
        else:
            # Pour les autres utilisateurs, utiliser leur restaurant_id
            restaurant_id = current_user.get('restaurant_id')
        
        # NOUVEAU: Sélection automatique du premier restaurant si aucun n'est sélectionné
        if not restaurant_id and context['restaurants']:
            # Sélectionner automatiquement le premier restaurant disponible
            restaurant_id = context['restaurants'][0]['id']
            print(f"🏢 Sélection automatique du restaurant: {context['restaurants'][0]['name']}")
            
            # Mettre à jour la session pour Master Admin
            if current_user.get('role') == 'master_admin':
                session['current_restaurant_id'] = restaurant_id
            # Pour les autres utilisateurs, on ne modifie pas leur restaurant_id permanent
        
        if restaurant_id:
            restaurants = self._load_restaurants()
            context['restaurant'] = next((r for r in restaurants if r['id'] == restaurant_id), None)
        
        return context
    
    def update_client(self, client_id, name=None, email=None, contact_name=None, phone=None):
        """Modifier un client existant"""
        try:
            clients = self._load_clients()
            client = next((c for c in clients if c['id'] == client_id), None)
            
            if not client:
                return {
                    'success': False,
                    'error': 'Client introuvable'
                }
            
            # Vérifier si l'email est déjà utilisé par un autre client
            if email and email != client.get('email'):
                if any(c['email'] == email and c['id'] != client_id for c in clients):
                    return {
                        'success': False,
                        'error': 'Un client avec cet email existe déjà'
                    }
            
            # Mettre à jour les champs
            if name is not None:
                client['name'] = name
            if email is not None:
                client['email'] = email
            if contact_name is not None:
                client['contact_name'] = contact_name
            if phone is not None:
                client['phone'] = phone
            
            client['updated_at'] = datetime.now().isoformat()
            
            # Sauvegarder
            self._save_clients(clients)
            
            return {
                'success': True,
                'client': client
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur modification client: {str(e)}'
            }
    
    def delete_client(self, client_id):
        """Supprimer un client et tous ses restaurants/utilisateurs"""
        try:
            clients = self._load_clients()
            restaurants = self._load_restaurants()
            users = self._load_users()
            
            # Vérifier que le client existe
            client = next((c for c in clients if c['id'] == client_id), None)
            if not client:
                return {
                    'success': False,
                    'error': 'Client introuvable'
                }
            
            # Supprimer tous les restaurants du client
            restaurants_to_delete = [r['id'] for r in restaurants if r['client_id'] == client_id]
            restaurants = [r for r in restaurants if r['client_id'] != client_id]
            
            # Supprimer tous les utilisateurs liés au client ou à ses restaurants
            users = [u for u in users if u.get('client_id') != client_id and u.get('restaurant_id') not in restaurants_to_delete]
            
            # Supprimer le client
            clients = [c for c in clients if c['id'] != client_id]
            
            # Sauvegarder
            self._save_clients(clients)
            self._save_restaurants(restaurants)
            self._save_users(users)
            
            return {
                'success': True,
                'message': f'Client {client["name"]} supprimé avec {len(restaurants_to_delete)} restaurants'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur suppression client: {str(e)}'
            }
    
    def update_restaurant(self, restaurant_id, name=None, address=None, phone=None, email=None):
        """Modifier un restaurant existant"""
        try:
            restaurants = self._load_restaurants()
            restaurant = next((r for r in restaurants if r['id'] == restaurant_id), None)
            
            if not restaurant:
                return {
                    'success': False,
                    'error': 'Restaurant introuvable'
                }
            
            # Mettre à jour les champs
            if name is not None:
                restaurant['name'] = name
            if address is not None:
                restaurant['address'] = address
            if phone is not None:
                restaurant['phone'] = phone
            if email is not None:
                restaurant['email'] = email
            
            restaurant['updated_at'] = datetime.now().isoformat()
            
            # Sauvegarder
            self._save_restaurants(restaurants)
            
            return {
                'success': True,
                'restaurant': restaurant
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur modification restaurant: {str(e)}'
            }
    
    def delete_restaurant(self, restaurant_id):
        """Supprimer un restaurant et tous ses utilisateurs"""
        try:
            restaurants = self._load_restaurants()
            users = self._load_users()
            
            # Vérifier que le restaurant existe
            restaurant = next((r for r in restaurants if r['id'] == restaurant_id), None)
            if not restaurant:
                return {
                    'success': False,
                    'error': 'Restaurant introuvable'
                }
            
            # Supprimer tous les utilisateurs du restaurant
            users_to_delete = len([u for u in users if u.get('restaurant_id') == restaurant_id])
            users = [u for u in users if u.get('restaurant_id') != restaurant_id]
            
            # Supprimer le restaurant
            restaurants = [r for r in restaurants if r['id'] != restaurant_id]
            
            # Sauvegarder
            self._save_restaurants(restaurants)
            self._save_users(users)
            
            return {
                'success': True,
                'message': f'Restaurant {restaurant["name"]} supprimé avec {users_to_delete} utilisateurs'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur suppression restaurant: {str(e)}'
            }
    
    def update_user(self, user_id, name=None, email=None, username=None, role=None, client_id=None, restaurant_id=None, active=None):
        """Modifier un utilisateur existant"""
        try:
            users = self._load_users()
            user = next((u for u in users if u['id'] == user_id), None)
            
            if not user:
                return {
                    'success': False,
                    'error': 'Utilisateur introuvable'
                }
            
            # Vérifier l'unicité du username et email
            if username and username != user.get('username'):
                if any(u['username'] == username and u['id'] != user_id for u in users):
                    return {
                        'success': False,
                        'error': 'Ce nom d\'utilisateur existe déjà'
                    }
            
            if email and email != user.get('email'):
                if any(u['email'] == email and u['id'] != user_id for u in users):
                    return {
                        'success': False,
                        'error': 'Un utilisateur avec cet email existe déjà'
                    }
            
            # Vérifier les contraintes selon le rôle
            if role and role != user.get('role'):
                if role in ['admin', 'user'] and not restaurant_id:
                    return {
                        'success': False,
                        'error': 'Un restaurant doit être assigné pour ce rôle'
                    }
            
            # Mettre à jour les champs
            if name is not None:
                user['name'] = name
            if email is not None:
                user['email'] = email
            if username is not None:
                user['username'] = username
            if role is not None:
                user['role'] = role
            if client_id is not None:
                user['client_id'] = client_id
            if restaurant_id is not None:
                user['restaurant_id'] = restaurant_id
            if active is not None:
                user['active'] = active
            
            user['updated_at'] = datetime.now().isoformat()
            
            # Sauvegarder
            self._save_users(users)
            
            return {
                'success': True,
                'user': user
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur modification utilisateur: {str(e)}'
            }
    
    def delete_user(self, user_id):
        """Supprimer un utilisateur"""
        try:
            users = self._load_users()
            user = next((u for u in users if u['id'] == user_id), None)
            
            if not user:
                return {
                    'success': False,
                    'error': 'Utilisateur introuvable'
                }
            
            # Empêcher la suppression du master admin
            if user.get('role') == 'master_admin':
                return {
                    'success': False,
                    'error': 'Impossible de supprimer le Master Admin'
                }
            
            # Supprimer l'utilisateur
            users = [u for u in users if u['id'] != user_id]
            
            # Sauvegarder
            self._save_users(users)
            
            return {
                'success': True,
                'message': f'Utilisateur {user["name"]} supprimé'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur suppression utilisateur: {str(e)}'
            }
    
    def get_client_restaurants(self, client_id):
        """Récupérer tous les restaurants d'un client"""
        try:
            restaurants = self._load_restaurants()
            client_restaurants = [r for r in restaurants if r['client_id'] == client_id]
            
            return {
                'success': True,
                'restaurants': client_restaurants
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur récupération restaurants: {str(e)}'
            }
    
    def get_restaurant_users(self, restaurant_id):
        """Récupérer tous les utilisateurs d'un restaurant"""
        try:
            users = self._load_users()
            restaurant_users = [u for u in users if u.get('restaurant_id') == restaurant_id]
            
            # Masquer les mots de passe
            safe_users = []
            for user in restaurant_users:
                safe_user = user.copy()
                safe_user.pop('password', None)
                safe_users.append(safe_user)
            
            return {
                'success': True,
                'users': safe_users
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur récupération utilisateurs: {str(e)}'
            }
    
    def create_user_for_client(self, client_id, username, email, password, name, role, restaurant_id):
        """Créer un utilisateur pour un client spécifique (utilisé par les clients)"""
        try:
            # Vérifier que le client existe
            clients = self._load_clients()
            client = next((c for c in clients if c['id'] == client_id), None)
            if not client:
                return {
                    'success': False,
                    'error': 'Client introuvable'
                }
            
            # Vérifier que le restaurant appartient au client
            restaurants = self._load_restaurants()
            restaurant = next((r for r in restaurants if r['id'] == restaurant_id), None)
            if not restaurant or restaurant['client_id'] != client_id:
                return {
                    'success': False,
                    'error': 'Restaurant introuvable ou n\'appartient pas à ce client'
                }
            
            # Créer l'utilisateur avec les bonnes contraintes
            return self.create_user(
                username=username,
                email=email,
                password=password,
                name=name,
                role=role,
                client_id=client_id,
                restaurant_id=restaurant_id
            )
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur création utilisateur: {str(e)}'
            }

# Décorateurs pour les permissions
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Connexion requise', 'code': 'AUTH_REQUIRED'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_manager = AuthManager()
            if not auth_manager.has_permission(required_role):
                if request.is_json:
                    return jsonify({'error': 'Permissions insuffisantes', 'code': 'INSUFFICIENT_PERMISSIONS'}), 403
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator 