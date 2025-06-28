"""
Module OCR unifié pour l'extraction de texte
Supporte uniquement Tesseract pour l'OCR de base
Claude Vision gère l'analyse intelligente
"""

import os
import re
from typing import Dict, List, Any, Optional
import pytesseract
from PIL import Image
import cv2
import numpy as np
import logging
from pathlib import Path

# Support des formats iPhone
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_SUPPORT = True
except ImportError:
    HEIF_SUPPORT = False

logger = logging.getLogger(__name__)

class OCREngine:
    """Moteur OCR unifié utilisant Tesseract"""
    
    def __init__(self):
        self.tesseract_available = self._check_tesseract()
        
    def _check_tesseract(self) -> bool:
        """Vérifier si Tesseract est installé"""
        try:
            pytesseract.get_tesseract_version()
            return True
        except:
            logger.warning("⚠️ Tesseract non installé")
            return False
    
    def is_available(self) -> bool:
        """Vérifier si au moins un moteur OCR est disponible"""
        return self.tesseract_available
    
    def extract_text(self, image_path: str) -> Dict[str, Any]:
        """Extraire le texte d'une image"""
        if not self.is_available():
            return {
                'success': False,
                'error': 'Aucun moteur OCR disponible'
            }
        
        try:
            # Prétraiter l'image
            processed_image = self._preprocess_image(image_path)
            
            # OCR avec Tesseract
            text = pytesseract.image_to_string(
                processed_image,
                lang='fra+eng',
                config='--psm 6'
            )
            
            return {
                'success': True,
                'text': text,
                'confidence': 0.8,  # Confiance par défaut pour Tesseract
                'engine': 'tesseract',
                'structured_data': {}
            }
            
        except Exception as e:
            logger.error(f"Erreur OCR: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _preprocess_image(self, image_path: str) -> np.ndarray:
        """Prétraiter l'image pour améliorer l'OCR"""
        # Charger l'image
        if image_path.lower().endswith(('.heic', '.heif')):
            pil_image = Image.open(image_path)
            image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        else:
            image = cv2.imread(image_path)
        
        # Convertir en niveaux de gris
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Améliorer le contraste
        enhanced = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
        
        # Débruitage
        denoised = cv2.fastNlMeansDenoising(enhanced)
        
        # Binarisation adaptative
        binary = cv2.adaptiveThreshold(
            denoised, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        
        return binary
    
    def get_config(self) -> Dict[str, Any]:
        """Obtenir la configuration actuelle"""
        return {
            'engines_available': {
                'tesseract': self.tesseract_available
            },
            'current_config': {
                'primary_engine': 'tesseract' if self.tesseract_available else None
            }
        }
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """Mettre à jour la configuration"""
        # Configuration simple pour Tesseract uniquement
        pass 