from flask import Blueprint

workers_bp = Blueprint("workers", __name__)

from . import routes  # noqa: E402,F401
