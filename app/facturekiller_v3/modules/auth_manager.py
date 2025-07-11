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
        """Initialiser le gestionnaire d'authentification (Firestore uniquement)"""
        # 🔥 FIRESTORE UNIQUEMENT - Plus de fichiers locaux
        self._fs_enabled = False
        self._fs = None
        
        # Initialiser Firestore
        try:
            from modules.firestore_db import FirestoreDB
            firestore_db = FirestoreDB()
            self._fs = firestore_db.db
            self._fs_enabled = True
            print("✅ Firestore initialisé pour AuthManager")
            
            # Créer le master admin par défaut
            self._create_master_admin()
        except Exception as e:
            print(f"❌ Erreur initialisation Firestore AuthManager: {e}")
            self._fs_enabled = False
            self._fs = None
    
    def _create_master_admin(self):
        """Crée le master admin par défaut dans Firestore s'il n'existe pas"""
        try:
            if not self._fs_enabled:
                return
            
            # Vérifier si le master admin existe déjà
            docs = list(self._fs.collection('users').where('role', '==', 'master_admin').stream())
            
            if not docs:
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
                
                self._fs.collection('users').document('master_001').set(master_admin)
                print("🔐 Master admin créé dans Firestore - Username: master, Password: admin123")
            else:
                print("🔐 Master admin existe déjà dans Firestore")
                
        except Exception as e:
            print(f"❌ Erreur création master admin Firestore: {e}")
    
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
    
    def login(self, username, password):
        """Connexion utilisateur depuis Firestore uniquement"""
        try:
            if not self._fs_enabled:
                return {'success': False, 'error': 'Firestore non disponible'}
            
            # Chercher l'utilisateur par username ou email
            docs = list(self._fs.collection('users').where('username', '==', username).stream())
            if not docs:
                docs = list(self._fs.collection('users').where('email', '==', username).stream())
            
            if docs:
                user = docs[0].to_dict()
                if user.get('active', True) and self._verify_password(password, user['password']):
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
            
        except Exception as e:
            print(f"❌ Erreur login Firestore: {e}")
            return {'success': False, 'error': 'Erreur de connexion'}
    
    def logout(self):
        """Déconnexion"""
        session.clear()
        return {'success': True, 'message': 'Déconnecté avec succès'}
    
    def get_current_user(self):
        """Récupère l'utilisateur actuel depuis Firestore uniquement"""
        try:
            if 'user_id' not in session or not self._fs_enabled:
                return None
            
            doc = self._fs.collection('users').document(session['user_id']).get()
            if doc.exists:
                user = doc.to_dict()
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'name': user['name'],
                    'role': user['role'],
                    'client_id': user.get('client_id'),
                    'restaurant_id': user.get('restaurant_id')
                }
            return None
            
        except Exception as e:
            print(f"❌ Erreur get_current_user Firestore: {e}")
            return None
    
    def create_client(self, name, email, contact_name, phone=None):
        """Créer un nouveau client"""
        try:
            # 🔥 FIRESTORE UNIQUEMENT - Plus de fichiers locaux
            if not self._fs_enabled:
                return {'success': False, 'error': 'Firestore non disponible'}
            
            # Vérifier si l'email existe déjà
            docs = list(self._fs.collection('clients').where('email', '==', email).stream())
            if docs:
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
            self._fs.collection('clients').document(client_id).set(new_client)
            
            return {
                'success': True,
                'client': new_client
            }
            
        except Exception as e:
            print(f"❌ Erreur création client Firestore: {e}")
            return {
                'success': False,
                'error': f'Erreur création client: {str(e)}'
            }
    
    def create_restaurant(self, client_id, name, address, phone=None, email=None):
        """Créer un nouveau restaurant"""
        try:
            # 🔥 FIRESTORE UNIQUEMENT - Plus de fichiers locaux
            if not self._fs_enabled:
                return {'success': False, 'error': 'Firestore non disponible'}
            
            # Vérifier que le client existe
            client_doc = self._fs.collection('clients').document(client_id).get()
            if not client_doc.exists:
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
            self._fs.collection('restaurants').document(restaurant_id).set(new_restaurant)
            
            return {
                'success': True,
                'restaurant': new_restaurant
            }
            
        except Exception as e:
            print(f"❌ Erreur création restaurant Firestore: {e}")
            return {
                'success': False,
                'error': f'Erreur création restaurant: {str(e)}'
            }
    
    def create_user(self, username, email, password, name, role, client_id=None, restaurant_id=None):
        """Créer un nouvel utilisateur"""
        try:
            # 🔥 FIRESTORE UNIQUEMENT - Plus de fichiers locaux
            if not self._fs_enabled:
                return {'success': False, 'error': 'Firestore non disponible'}
            
            # Vérifier si le username ou email existe déjà
            docs = list(self._fs.collection('users').where('username', '==', username).stream())
            if docs:
                return {
                    'success': False,
                    'error': 'Ce nom d\'utilisateur existe déjà'
                }
            
            docs = list(self._fs.collection('users').where('email', '==', email).stream())
            if docs:
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
                restaurant_doc = self._fs.collection('restaurants').document(restaurant_id).get()
                if not restaurant_doc.exists:
                    return {
                        'success': False,
                        'error': 'Restaurant introuvable'
                    }
                
                # Pour admin/user, le client_id doit correspondre au propriétaire du restaurant
                client_id = restaurant_doc.to_dict()['client_id']
            
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
            self._fs.collection('users').document(user_id).set(new_user)
            
            return {
                'success': True,
                'user': new_user
            }
            
        except Exception as e:
            print(f"❌ Erreur création utilisateur Firestore: {e}")
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
            client_doc = self._fs.collection('clients').document(current_user['client_id']).get()
            if client_doc.exists:
                context['client'] = client_doc.to_dict()
                
                # Charger tous les restaurants du client
                if context['client']:
                    restaurants_docs = list(self._fs.collection('restaurants').where('client_id', '==', current_user['client_id']).stream())
                    context['restaurants'] = [r.to_dict() for r in restaurants_docs]
        
        # Charger le restaurant spécifique
        restaurant_id = None
        
        # Pour les Master Admin, vérifier d'abord selected_restaurant_id puis la session
        if current_user.get('role') == 'master_admin':
            # Recharger l'utilisateur pour avoir les données les plus récentes
            user_doc = self._fs.collection('users').document(current_user['id']).get()
            user_data = user_doc.to_dict()
            
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
            restaurant_doc = self._fs.collection('restaurants').document(restaurant_id).get()
            if restaurant_doc.exists:
                context['restaurant'] = restaurant_doc.to_dict()
        
        return context
    
    def update_client(self, client_id, name=None, email=None, contact_name=None, phone=None):
        """Modifier un client existant"""
        try:
            # 🔥 FIRESTORE UNIQUEMENT - Plus de fichiers locaux
            if not self._fs_enabled:
                return {'success': False, 'error': 'Firestore non disponible'}
            
            client_doc = self._fs.collection('clients').document(client_id).get()
            
            if not client_doc.exists:
                return {
                    'success': False,
                    'error': 'Client introuvable'
                }
            
            # Vérifier si l'email est déjà utilisé par un autre client
            if email and email != client_doc.to_dict().get('email'):
                docs = list(self._fs.collection('clients').where('email', '==', email).stream())
                if docs:
                    return {
                        'success': False,
                        'error': 'Un client avec cet email existe déjà'
                    }
            
            # Mettre à jour les champs
            update_data = {}
            if name is not None:
                update_data['name'] = name
            if email is not None:
                update_data['email'] = email
            if contact_name is not None:
                update_data['contact_name'] = contact_name
            if phone is not None:
                update_data['phone'] = phone
            
            update_data['updated_at'] = datetime.now().isoformat()
            
            # Sauvegarder
            self._fs.collection('clients').document(client_id).update(update_data)
            
            return {
                'success': True,
                'client': client_doc.to_dict()
            }
            
        except Exception as e:
            print(f"❌ Erreur modification client Firestore: {e}")
            return {
                'success': False,
                'error': f'Erreur modification client: {str(e)}'
            }
    
    def delete_client(self, client_id):
        """Supprimer un client et tous ses restaurants/utilisateurs"""
        try:
            # 🔥 FIRESTORE UNIQUEMENT - Plus de fichiers locaux
            if not self._fs_enabled:
                return {'success': False, 'error': 'Firestore non disponible'}
            
            client_doc = self._fs.collection('clients').document(client_id).get()
            if not client_doc.exists:
                return {
                    'success': False,
                    'error': 'Client introuvable'
                }
            
            # Supprimer tous les restaurants du client
            restaurants_to_delete = [r['id'] for r in self._fs.collection('restaurants').where('client_id', '==', client_id).stream()]
            self._fs.collection('restaurants').where('client_id', '==', client_id).delete()
            
            # Supprimer tous les utilisateurs liés au client ou à ses restaurants
            users_to_delete = 0
            for user_doc in self._fs.collection('users').where('client_id', '==', client_id).stream():
                user_data = user_doc.to_dict()
                if user_data.get('restaurant_id') in restaurants_to_delete:
                    self._fs.collection('users').document(user_data['id']).delete()
                    users_to_delete += 1
            
            # Supprimer le client
            self._fs.collection('clients').document(client_id).delete()
            
            return {
                'success': True,
                'message': f'Client {client_doc.to_dict()["name"]} supprimé avec {users_to_delete} utilisateurs'
            }
            
        except Exception as e:
            print(f"❌ Erreur suppression client Firestore: {e}")
            return {
                'success': False,
                'error': f'Erreur suppression client: {str(e)}'
            }
    
    def update_restaurant(self, restaurant_id, name=None, address=None, phone=None, email=None):
        """Modifier un restaurant existant"""
        try:
            # 🔥 FIRESTORE UNIQUEMENT - Plus de fichiers locaux
            if not self._fs_enabled:
                return {'success': False, 'error': 'Firestore non disponible'}
            
            restaurant_doc = self._fs.collection('restaurants').document(restaurant_id).get()
            
            if not restaurant_doc.exists:
                return {
                    'success': False,
                    'error': 'Restaurant introuvable'
                }
            
            # Mettre à jour les champs
            update_data = {}
            if name is not None:
                update_data['name'] = name
            if address is not None:
                update_data['address'] = address
            if phone is not None:
                update_data['phone'] = phone
            if email is not None:
                update_data['email'] = email
            
            update_data['updated_at'] = datetime.now().isoformat()
            
            # Sauvegarder
            self._fs.collection('restaurants').document(restaurant_id).update(update_data)
            
            return {
                'success': True,
                'restaurant': restaurant_doc.to_dict()
            }
            
        except Exception as e:
            print(f"❌ Erreur modification restaurant Firestore: {e}")
            return {
                'success': False,
                'error': f'Erreur modification restaurant: {str(e)}'
            }
    
    def delete_restaurant(self, restaurant_id):
        """Supprimer un restaurant et tous ses utilisateurs"""
        try:
            # 🔥 FIRESTORE UNIQUEMENT - Plus de fichiers locaux
            if not self._fs_enabled:
                return {'success': False, 'error': 'Firestore non disponible'}
            
            restaurant_doc = self._fs.collection('restaurants').document(restaurant_id).get()
            if not restaurant_doc.exists:
                return {
                    'success': False,
                    'error': 'Restaurant introuvable'
                }
            
            # Supprimer tous les utilisateurs du restaurant
            users_to_delete = 0
            for user_doc in self._fs.collection('users').where('restaurant_id', '==', restaurant_id).stream():
                user_doc.reference.delete()
                users_to_delete += 1
            
            # Supprimer le restaurant
            self._fs.collection('restaurants').document(restaurant_id).delete()
            
            return {
                'success': True,
                'message': f'Restaurant {restaurant_doc.to_dict()["name"]} supprimé avec {users_to_delete} utilisateurs'
            }
            
        except Exception as e:
            print(f"❌ Erreur suppression restaurant Firestore: {e}")
            return {
                'success': False,
                'error': f'Erreur suppression restaurant: {str(e)}'
            }
    
    def update_user(self, user_id, name=None, email=None, username=None, role=None, client_id=None, restaurant_id=None, active=None):
        """Modifier un utilisateur existant"""
        try:
            # 🔥 FIRESTORE UNIQUEMENT - Plus de fichiers locaux
            if not self._fs_enabled:
                return {'success': False, 'error': 'Firestore non disponible'}
            
            user_doc = self._fs.collection('users').document(user_id).get()
            
            if not user_doc.exists:
                return {
                    'success': False,
                    'error': 'Utilisateur introuvable'
                }
            
            # Vérifier l'unicité du username et email
            if username and username != user_doc.to_dict().get('username'):
                docs = list(self._fs.collection('users').where('username', '==', username).stream())
                if docs:
                    return {
                        'success': False,
                        'error': 'Ce nom d\'utilisateur existe déjà'
                    }
            
            if email and email != user_doc.to_dict().get('email'):
                docs = list(self._fs.collection('users').where('email', '==', email).stream())
                if docs:
                    return {
                        'success': False,
                        'error': 'Un utilisateur avec cet email existe déjà'
                    }
            
            # Vérifier les contraintes selon le rôle
            if role and role != user_doc.to_dict().get('role'):
                if role in ['admin', 'user'] and not restaurant_id:
                    return {
                        'success': False,
                        'error': 'Un restaurant doit être assigné pour ce rôle'
                    }
            
            # Mettre à jour les champs
            update_data = {}
            if name is not None:
                update_data['name'] = name
            if email is not None:
                update_data['email'] = email
            if username is not None:
                update_data['username'] = username
            if role is not None:
                update_data['role'] = role
            if client_id is not None:
                update_data['client_id'] = client_id
            if restaurant_id is not None:
                update_data['restaurant_id'] = restaurant_id
            if active is not None:
                update_data['active'] = active
            
            update_data['updated_at'] = datetime.now().isoformat()
            
            # Sauvegarder
            self._fs.collection('users').document(user_id).update(update_data)
            
            return {
                'success': True,
                'user': user_doc.to_dict()
            }
            
        except Exception as e:
            print(f"❌ Erreur modification utilisateur Firestore: {e}")
            return {
                'success': False,
                'error': f'Erreur modification utilisateur: {str(e)}'
            }
    
    def delete_user(self, user_id):
        """Supprimer un utilisateur"""
        try:
            # 🔥 FIRESTORE UNIQUEMENT - Plus de fichiers locaux
            if not self._fs_enabled:
                return {'success': False, 'error': 'Firestore non disponible'}
            
            user_doc = self._fs.collection('users').document(user_id).get()
            
            if not user_doc.exists:
                return {
                    'success': False,
                    'error': 'Utilisateur introuvable'
                }
            
            # Empêcher la suppression du master admin
            if user_doc.to_dict().get('role') == 'master_admin':
                return {
                    'success': False,
                    'error': 'Impossible de supprimer le Master Admin'
                }
            
            # Supprimer l'utilisateur
            self._fs.collection('users').document(user_id).delete()
            
            return {
                'success': True,
                'message': f'Utilisateur {user_doc.to_dict()["name"]} supprimé'
            }
            
        except Exception as e:
            print(f"❌ Erreur suppression utilisateur Firestore: {e}")
            return {
                'success': False,
                'error': f'Erreur suppression utilisateur: {str(e)}'
            }
    
    def get_client_restaurants(self, client_id):
        """Récupérer tous les restaurants d'un client"""
        try:
            # 🔥 FIRESTORE UNIQUEMENT - Plus de fichiers locaux
            if not self._fs_enabled:
                return {'success': False, 'error': 'Firestore non disponible'}
            
            restaurants_docs = list(self._fs.collection('restaurants').where('client_id', '==', client_id).stream())
            client_restaurants = [r.to_dict() for r in restaurants_docs]
            
            return {
                'success': True,
                'restaurants': client_restaurants
            }
            
        except Exception as e:
            print(f"❌ Erreur récupération restaurants Firestore: {e}")
            return {
                'success': False,
                'error': f'Erreur récupération restaurants: {str(e)}'
            }
    
    def get_restaurant_users(self, restaurant_id):
        """Récupérer tous les utilisateurs d'un restaurant"""
        try:
            # 🔥 FIRESTORE UNIQUEMENT - Plus de fichiers locaux
            if not self._fs_enabled:
                return {'success': False, 'error': 'Firestore non disponible'}
            
            users_docs = list(self._fs.collection('users').where('restaurant_id', '==', restaurant_id).stream())
            restaurant_users = [u.to_dict() for u in users_docs]
            
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
            print(f"❌ Erreur récupération utilisateurs Firestore: {e}")
            return {
                'success': False,
                'error': f'Erreur récupération utilisateurs: {str(e)}'
            }
    
    def create_user_for_client(self, client_id, username, email, password, name, role, restaurant_id):
        """Créer un utilisateur pour un client spécifique (utilisé par les clients)"""
        try:
            # 🔥 FIRESTORE UNIQUEMENT - Plus de fichiers locaux
            if not self._fs_enabled:
                return {'success': False, 'error': 'Firestore non disponible'}
            
            # Vérifier que le client existe
            client_doc = self._fs.collection('clients').document(client_id).get()
            if not client_doc.exists:
                return {
                    'success': False,
                    'error': 'Client introuvable'
                }
            
            # Vérifier que le restaurant appartient au client
            restaurant_doc = self._fs.collection('restaurants').document(restaurant_id).get()
            if not restaurant_doc.exists or restaurant_doc.to_dict()['client_id'] != client_id:
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
            print(f"❌ Erreur création utilisateur pour client Firestore: {e}")
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