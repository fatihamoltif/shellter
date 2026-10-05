from flask import Blueprint

bp = Blueprint("workers", __name__, url_prefix="/workers")

from . import routes  # noqa: E402,F401
