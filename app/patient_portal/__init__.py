from flask import Blueprint

patient_portal_bp = Blueprint(
    "patient_portal", __name__, template_folder="../templates/patient_portal"
)

from app.patient_portal import routes  # noqa: E402,F401
