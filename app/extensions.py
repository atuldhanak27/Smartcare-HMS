"""
Extension instances live here, separate from app/__init__.py, so that
blueprints and models can import them (e.g. `from app.extensions import db`)
without causing circular-import problems.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"
