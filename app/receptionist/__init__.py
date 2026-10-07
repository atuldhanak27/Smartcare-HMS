from flask import Blueprint

receptionist_bp = Blueprint(
    "receptionist", __name__, template_folder="../templates/receptionist"
)

from app.receptionist import routes  # noqa: E402,F401
