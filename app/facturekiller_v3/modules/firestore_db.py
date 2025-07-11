"""
Wrapper minimal pour Firestore.  
Nécessite la variable d'environnement GOOGLE_APPLICATION_CREDENTIALS pointant vers le fichier service-account JSON.
Ou la variable FIREBASE_SERVICE_KEY contenant le JSON brut de la clé de service.
"""

import os
from functools import lru_cache
from typing import Optional
import json, tempfile
import logging

logger = logging.getLogger(__name__)

def is_configured() -> bool:
    """Retourne True si une clé de service est disponible (fichier ou JSON brut)."""
    has_credentials = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("FIREBASE_SERVICE_KEY"))
    logger.info(f"Firebase configuré: {has_credentials}")
    return has_credentials


@lru_cache()
def get_client():
    """Initialiser le client Firestore (lazy, singleton)."""
    logger.info("🔧 Initialisation du client Firestore...")
    
    # Cas où une clé brute est fournie mais pas encore écrite sur disque
    firebase_service_key = os.getenv("FIREBASE_SERVICE_KEY")
    if firebase_service_key and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        logger.info("📝 Écriture de la clé de service temporaire...")
        _write_temp_key(firebase_service_key)

    if not is_configured():
        logger.error("❌ Aucune configuration Firebase trouvée")
        logger.error("   Variables disponibles:")
        logger.error(f"   - GOOGLE_APPLICATION_CREDENTIALS: {'OUI' if os.getenv('GOOGLE_APPLICATION_CREDENTIALS') else 'NON'}")
        logger.error(f"   - FIREBASE_SERVICE_KEY: {'OUI' if os.getenv('FIREBASE_SERVICE_KEY') else 'NON'}")
        return None

    try:
        from google.cloud import firestore  # type: ignore
        client = firestore.Client()
        logger.info(f"🔥 Firestore initialisé – projet : {client.project}")
        return client
    except ImportError as e:
        logger.error(f"❌ Module google-cloud-firestore non installé: {e}")
        logger.error("   Installez avec: pip install google-cloud-firestore")
        return None
    except Exception as e:
        logger.error(f"❌ Erreur initialisation Firestore: {e}")
        logger.error("   Vérifiez votre clé de service Firebase")
        return None


def available() -> bool:
    """True si Firestore prêt à l'emploi."""
    client = get_client()
    is_available = client is not None
    logger.info(f"Firebase disponible: {is_available}")
    return is_available


def _write_temp_key(raw_json: str):
    """Écrit le JSON brut dans un fichier temporaire et définit GOOGLE_APPLICATION_CREDENTIALS."""
    try:
        # Valider le JSON
        json.loads(raw_json)
        
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        tmp.write(raw_json.encode())
        tmp.flush()
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = tmp.name
        logger.info(f"✅ Clé de service écrite dans: {tmp.name}")
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON de clé de service invalide: {e}")
    except Exception as e:
        logger.error(f"❌ Erreur écriture clé de service: {e}")


class FirestoreDB:
    """Classe wrapper pour Firestore avec gestion d'erreurs améliorée"""
    
    def __init__(self):
        self.db = get_client()
        if self.db:
            logger.info("✅ FirestoreDB initialisé avec succès")
        else:
            logger.error("❌ FirestoreDB: Impossible d'initialiser le client")
    
    def is_connected(self) -> bool:
        """Vérifier si la connexion Firestore est active"""
        return self.db is not None
    
    def test_connection(self) -> bool:
        """Tester la connexion Firestore"""
        try:
            if not self.db:
                return False
            
            # Test simple: lister les collections
            collections = list(self.db.collections())
            logger.info(f"✅ Test connexion Firestore réussi - {len(collections)} collections trouvées")
            return True
        except Exception as e:
            logger.error(f"❌ Test connexion Firestore échoué: {e}")
            return False 