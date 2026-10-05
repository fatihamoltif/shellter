from flask import render_template
from flask_login import login_required, current_user
from . import dashboard_bp

@dashboard_bp.route("/dashboard")
@login_required
def index():
    # La vraie liste d'instances arrivera en S6 (route /instances).
    instances = []
    return render_template("dashboard.html", user=current_user, instances=instances)
