from flask import render_template, redirect, url_for, flash
from app.auth import bp # Le blueprint 'auth' créé par P1
from app.auth.forms import RegistrationForm
from app.models import db, User

@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Vérification de l'unicité
        existing_user = User.query.filter(
            (User.username == form.username.data) | (User.email == form.email.data)
        ).first()
        
        if existing_user:
            flash('Ce nom d\'utilisateur ou cet email est déjà pris.', 'danger')
            return redirect(url_for('auth.register'))
            
        # Création du compte en utilisant ta méthode de S4
        new_user = User(username=form.username.data, email=form.email.data)
        new_user.set_password(form.password.data)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Inscription réussie ! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('auth.login')) # La route de login sera faite par P3
        
    return render_template('auth/register.html', form=form)