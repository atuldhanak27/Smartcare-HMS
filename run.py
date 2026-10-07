"""
SmartCare Hospital Management System - entry point.

Usage:
    python run.py
"""

import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402

app = create_app(os.environ.get("FLASK_ENV", "development"))

if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", True), host="0.0.0.0", port=5000)
    # app.run(host="0.0.0.0", port=5000, debug=True)