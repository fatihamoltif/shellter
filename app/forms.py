"""Formulaires Flask-WTF — Séance S5.

Flask-WTF fournit automatiquement la protection CSRF (jeton caché) et la validation.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length


class RegisterForm(FlaskForm):
    username = StringField(
        "Nom d'utilisateur",
        validators=[DataRequired(), Length(min=3, max=32)],
    )
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField(
        "Mot de passe",
        validators=[DataRequired(), Length(min=8, message="8 caractères minimum.")],
    )
    submit = SubmitField("Créer le compte")


class LoginForm(FlaskForm):
    username = StringField("Nom d'utilisateur", validators=[DataRequired()])
    password = PasswordField("Mot de passe", validators=[DataRequired()])
    submit = SubmitField("Se connecter")
