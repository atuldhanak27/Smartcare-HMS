from flask import Blueprint

doctor_bp = Blueprint("doctor", __name__, template_folder="../templates/doctor")

from app.doctor import routes  # noqa: E402,F401
