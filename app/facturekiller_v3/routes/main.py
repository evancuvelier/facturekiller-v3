#!/usr/bin/env python3
"""
Routes principales de l'application
"""

from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html')

@main_bp.route('/dashboard')
def dashboard():
    """Tableau de bord"""
    return render_template('dashboard.html') 