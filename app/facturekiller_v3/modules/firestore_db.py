"""
Wrapper minimal pour Firestore.  
Nécessite la variable d'environnement GOOGLE_APPLICATION_CREDENTIALS pointant vers le fichier service-account JSON.
"""

import os
from functools import lru_cache
from typing import Optional
import json, tempfile


def is_configured() -> bool:
    """Retourne True si une clé de service est disponible (fichier ou JSON brut)."""
    return bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("FIREBASE_SERVICE_KEY"))


@lru_cache()
def get_client():
    """Initialiser le client Firestore (lazy, singleton)."""
    # Cas où une clé brute est fournie mais pas encore écrite sur disque
    if os.getenv("FIREBASE_SERVICE_KEY") and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        _write_temp_key(os.getenv("FIREBASE_SERVICE_KEY"))

    if not is_configured():
        return None

    try:
        from google.cloud import firestore  # type: ignore
        client = firestore.Client()
        print(f"🔥 Firestore initialisé – projet : {client.project}")
        return client
    except Exception:
        return None


def available() -> bool:
    """True si Firestore prêt à l'emploi."""
    return get_client() is not None


def _write_temp_key(raw_json: str):
    """Écrit le JSON brut dans un fichier temporaire et définit GOOGLE_APPLICATION_CREDENTIALS."""
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        tmp.write(raw_json.encode())
        tmp.flush()
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = tmp.name
    except Exception:
        pass 