from datetime import date

from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user

from app.admin import admin_bp
from app.decorators import role_required
from app.extensions import db
from app.models import User, Doctor, Patient, Appointment


@admin_bp.route("/dashboard")
@login_required
@role_required("admin")
def dashboard():
    stats = {
        "total_patients": Patient.query.count(),
        "total_doctors": Doctor.query.count(),
        "total_appointments": Appointment.query.count(),
        "today_appointments": Appointment.query.filter(
            Appointment.appointment_date == date.today()
        ).count(),
        "total_receptionists": User.query.filter_by(role="receptionist").count(),
    }
    recent_patients = Patient.query.order_by(Patient.created_at.desc()).limit(5).all()
    todays_appts = (
        Appointment.query.filter(Appointment.appointment_date == date.today())
        .order_by(Appointment.appointment_time.asc())
        .all()
    )
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_patients=recent_patients,
        todays_appts=todays_appts,
    )


# ---------------------------------------------------------------------------
# USER MANAGEMENT
# ---------------------------------------------------------------------------
@admin_bp.route("/users")
@login_required
@role_required("admin")
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)


@admin_bp.route("/users/add", methods=["GET", "POST"])
@login_required
@role_required("admin")
def add_user():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip() or None
        role = request.form.get("role")
        password = request.form.get("password", "")
        specialization = request.form.get("specialization", "").strip()
        phone = request.form.get("phone", "").strip()
        qualification = request.form.get("qualification", "").strip()
        experience_years = request.form.get("experience_years", "0")

        errors = []
        if not username or not full_name or not password or not role:
            errors.append("Username, full name, password and role are required.")
        if role not in ("admin", "receptionist", "doctor"):
            errors.append("Invalid role selected.")
        if User.query.filter_by(username=username).first():
            errors.append(f"Username '{username}' is already taken.")
        if email and User.query.filter_by(email=email).first():
            errors.append(f"Email '{email}' is already registered.")
        if role == "doctor" and not specialization:
            errors.append("Specialization is required for doctors.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("admin/add_user.html", form=request.form)

        user = User(username=username, full_name=full_name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # get user.id before commit

        if role == "doctor":
            doctor = Doctor(
                user_id=user.id,
                specialization=specialization,
                phone=phone or None,
                qualification=qualification or None,
                experience_years=int(experience_years or 0),
            )
            db.session.add(doctor)

        db.session.commit()
        flash(f"User '{username}' ({role}) created successfully.", "success")
        return redirect(url_for("admin.users"))

    return render_template("admin/add_user.html", form={})


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@role_required("admin")
def toggle_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "warning")
        return redirect(url_for("admin.users"))
    user.is_active = not user.is_active
    db.session.commit()
    state = "activated" if user.is_active else "deactivated"
    flash(f"User '{user.username}' {state}.", "info")
    return redirect(url_for("admin.users"))


# ---------------------------------------------------------------------------
# DOCTOR MANAGEMENT (shortcut, in addition to generic add_user)
# ---------------------------------------------------------------------------
@admin_bp.route("/doctors")
@login_required
@role_required("admin")
def doctors():
    all_doctors = Doctor.query.join(User).order_by(User.full_name.asc()).all()
    return render_template("admin/doctors.html", doctors=all_doctors)


@admin_bp.route("/doctors/add", methods=["GET", "POST"])
@login_required
@role_required("admin")
def add_doctor():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip() or None
        password = request.form.get("password", "")
        specialization = request.form.get("specialization", "").strip()
        phone = request.form.get("phone", "").strip()
        qualification = request.form.get("qualification", "").strip()
        experience_years = request.form.get("experience_years", "0")

        errors = []
        if not username or not full_name or not password or not specialization:
            errors.append("Username, full name, password and specialization are required.")
        if User.query.filter_by(username=username).first():
            errors.append(f"Username '{username}' is already taken.")
        if email and User.query.filter_by(email=email).first():
            errors.append(f"Email '{email}' is already registered.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("admin/add_doctor.html", form=request.form)

        user = User(username=username, full_name=full_name, email=email, role="doctor")
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        doctor = Doctor(
            user_id=user.id,
            specialization=specialization,
            phone=phone or None,
            qualification=qualification or None,
            experience_years=int(experience_years or 0),
        )
        db.session.add(doctor)
        db.session.commit()

        flash(f"Dr. {full_name} registered successfully.", "success")
        return redirect(url_for("admin.doctors"))

    return render_template("admin/add_doctor.html", form={})
