"""
Application factory for SmartCare Hospital Management System.
"""

import os
from datetime import datetime, date

from flask import Flask, render_template, redirect, url_for
from flask_login import current_user

from config import config_by_name
from app.extensions import db, login_manager


def create_app(config_name=None):
    app = Flask(__name__)

    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # --- init extensions ---
    db.init_app(app)
    login_manager.init_app(app)

    # --- user loader for Flask-Login ---
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # --- register blueprints ---
    from app.auth import auth_bp
    from app.admin import admin_bp
    from app.receptionist import receptionist_bp
    from app.doctor import doctor_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(receptionist_bp, url_prefix="/reception")
    app.register_blueprint(doctor_bp, url_prefix="/doctor")

    # --- root route: send user to their role's dashboard ---
    @app.route("/")
    def index():
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        if current_user.role == "receptionist":
            return redirect(url_for("receptionist.dashboard"))
        if current_user.role == "doctor":
            return redirect(url_for("doctor.dashboard"))
        return redirect(url_for("auth.login"))

    # --- error handlers ---
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    # --- template globals / filters ---
    @app.context_processor
    def inject_globals():
        return {"current_year": datetime.utcnow().year, "today": date.today()}

    @app.template_filter("time12")
    def time12_filter(t):
        """Format a datetime.time object as e.g. 09:30 AM."""
        if t is None:
            return ""
        return t.strftime("%I:%M %p")

    @app.template_filter("date_fmt")
    def date_fmt_filter(d, fmt="%d %b %Y"):
        if d is None:
            return ""
        return d.strftime(fmt)

    return app
