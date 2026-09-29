from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length

class RegistrationForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email(message="Email invalide")])
    password = PasswordField('Mot de passe', validators=[
        DataRequired(), 
        Length(min=8, message="Le mot de passe doit contenir au moins 8 caractères.")
    ])
    submit = SubmitField('S\'inscrire')