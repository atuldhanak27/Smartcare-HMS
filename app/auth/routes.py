from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from app.auth import auth_bp
from app.models import User


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash("Invalid username or password.", "danger")
            return render_template("auth/login.html", username=username)

        if not user.is_active:
            flash("Your account has been deactivated. Contact the administrator.", "danger")
            return render_template("auth/login.html", username=username)

        login_user(user)
        flash(f"Welcome back, {user.full_name}!", "success")

        next_page = request.args.get("next")
        if next_page:
            return redirect(next_page)

        if user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        elif user.role == "receptionist":
            return redirect(url_for("receptionist.dashboard"))
        elif user.role == "doctor":
            return redirect(url_for("doctor.dashboard"))
        return redirect(url_for("index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
