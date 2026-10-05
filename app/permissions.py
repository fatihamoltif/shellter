"""Contrôle d'accès par rôle — séparation utilisateur / administrateur.

admin_required : réservé aux comptes dont User.is_admin est vrai. Réutilise
login_required (redirection /login si non connecté), puis renvoie 403 si
l'utilisateur connecté n'est pas administrateur.
"""
from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not getattr(current_user, "is_admin", False):
            abort(403)
        return view(*args, **kwargs)
    return wrapped
