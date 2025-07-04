"""
Wrapper minimal pour Firestore.  
Nécessite la variable d'environnement GOOGLE_APPLICATION_CREDENTIALS pointant vers le fichier service-account JSON.
"""

import os
from functools import lru_cache
from typing import Optional
import json, tempfile


def is_configured() -> bool:
    """Retourne True si la clé de service est disponible."""
    return bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))


@lru_cache()
def get_client():
    """Initialiser le client Firestore (lazy, singleton)."""
    if not is_configured():
        return None

    # Autoriser un secret JSON brut dans la variable FIREBASE_SERVICE_KEY
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and os.getenv("FIREBASE_SERVICE_KEY"):
        _write_temp_key(os.getenv("FIREBASE_SERVICE_KEY"))

    try:
        from google.cloud import firestore  # type: ignore
        return firestore.Client()
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