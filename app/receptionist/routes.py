# OR send_appointment_email
from datetime import datetime, date
from app.utils.email_service import send_email
from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from sqlalchemy import or_
from app.receptionist import receptionist_bp
from app.decorators import role_required
from app.extensions import db
from app.models import Patient, Vitals, Appointment, Doctor, User




@receptionist_bp.route("/dashboard")
@login_required
@role_required("receptionist")
def dashboard():
    today_appts = (
        Appointment.query.filter(Appointment.appointment_date == date.today())
        .order_by(Appointment.appointment_time.asc())
        .all()
    )
    total_patients = Patient.query.count()
    recent_patients = Patient.query.order_by(Patient.created_at.desc()).limit(5).all()
    return render_template(
        "receptionist/dashboard.html",
        today_appts=today_appts,
        total_patients=total_patients,
        recent_patients=recent_patients,
    )


# ---------------------------------------------------------------------------
# PATIENT REGISTRATION
# ---------------------------------------------------------------------------
@receptionist_bp.route("/patients/register", methods=["GET", "POST"])
@login_required
@role_required("receptionist")
def register_patient():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender")
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip() or None
        address = request.form.get("address", "").strip() or None
        blood_group = request.form.get("blood_group", "").strip() or None
        emergency_contact = request.form.get("emergency_contact", "").strip() or None

        errors = []
        if not full_name or not age or not gender or not phone:
            errors.append("Full name, age, gender and phone are required.")
        try:
            age_val = int(age)
            if age_val < 0 or age_val > 130:
                errors.append("Please enter a valid age.")
        except ValueError:
            errors.append("Age must be a number.")
            age_val = None

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("receptionist/register_patient.html", form=request.form)

        patient_code = Patient.generate_patient_code()
        patient = Patient(
            patient_code=patient_code,
            full_name=full_name,
            age=age_val,
            gender=gender,
            phone=phone,
            email=email,
            address=address,
            blood_group=blood_group,
            emergency_contact=emergency_contact,
            created_by=current_user.id,
        )
        db.session.add(patient)
        db.session.commit()

        flash(f"Patient registered successfully. Patient code: {patient_code}", "success")
        return redirect(url_for("receptionist.patient_detail", patient_id=patient.id))

    return render_template("receptionist/register_patient.html", form={})


# ---------------------------------------------------------------------------
# SEARCH
# ---------------------------------------------------------------------------
@receptionist_bp.route("/patients/search")
@login_required
@role_required("receptionist")
def search_patients():
    query = request.args.get("q", "").strip()
    results = []
    if query:
        like = f"%{query}%"
        results = (
            Patient.query.filter(
                or_(
                    Patient.full_name.ilike(like),
                    Patient.phone.ilike(like),
                    Patient.patient_code.ilike(like),
                )
            )
            .order_by(Patient.created_at.desc())
            .all()
        )
    return render_template("receptionist/search_patients.html", query=query, results=results)


# ---------------------------------------------------------------------------
# PATIENT DETAIL
# ---------------------------------------------------------------------------
@receptionist_bp.route("/patients/<int:patient_id>")
@login_required
@role_required("receptionist")
def patient_detail(patient_id):
    patient = db.session.get(Patient, patient_id)
    if not patient:
        flash("Patient not found.", "danger")
        return redirect(url_for("receptionist.search_patients"))
    vitals_history = patient.vitals.limit(10).all()
    appointments = patient.appointments.order_by(
        Appointment.appointment_date.desc(), Appointment.appointment_time.desc()
    ).all()
    return render_template(
        "receptionist/patient_detail.html",
        patient=patient,
        vitals_history=vitals_history,
        appointments=appointments,
    )


# ---------------------------------------------------------------------------
# VITALS
# ---------------------------------------------------------------------------
@receptionist_bp.route("/patients/<int:patient_id>/vitals", methods=["GET", "POST"])
@login_required
@role_required("receptionist")
def record_vitals(patient_id):
    patient = db.session.get(Patient, patient_id)
    if not patient:
        flash("Patient not found.", "danger")
        return redirect(url_for("receptionist.search_patients"))

    if request.method == "POST":
        vitals = Vitals(
            patient_id=patient.id,
            blood_pressure=request.form.get("blood_pressure", "").strip() or None,
            blood_sugar=request.form.get("blood_sugar", "").strip() or None,
            temperature=request.form.get("temperature", "").strip() or None,
            weight=_to_float(request.form.get("weight")),
            height=_to_float(request.form.get("height")),
            pulse=_to_int(request.form.get("pulse")),
            symptoms=request.form.get("symptoms", "").strip() or None,
            recorded_by=current_user.id,
        )
        db.session.add(vitals)
        db.session.commit()
        flash("Vitals recorded successfully.", "success")
        return redirect(url_for("receptionist.patient_detail", patient_id=patient.id))

    return render_template("receptionist/record_vitals.html", patient=patient)


def _to_float(val):
    try:
        return float(val) if val not in (None, "") else None
    except ValueError:
        return None


def _to_int(val):
    try:
        return int(val) if val not in (None, "") else None
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# APPOINTMENTS
# ---------------------------------------------------------------------------
@receptionist_bp.route("/appointments")
@login_required
@role_required("receptionist")
def appointments():
    filter_date = request.args.get("date", "")
    q = Appointment.query
    if filter_date:
        try:
            d = datetime.strptime(filter_date, "%Y-%m-%d").date()
            q = q.filter(Appointment.appointment_date == d)
        except ValueError:
            pass
    all_appts = q.order_by(
        Appointment.appointment_date.desc(), Appointment.appointment_time.asc()
    ).all()
    return render_template(
        "receptionist/appointments.html", appointments=all_appts, filter_date=filter_date
    )


@receptionist_bp.route("/appointments/create", methods=["GET", "POST"])
@login_required
@role_required("receptionist")
def create_appointment():
    preselected_patient_id = request.args.get("patient_id", type=int)
    doctors = Doctor.query.join(User).filter(User.is_active == True).order_by(  # noqa: E712
        User.full_name.asc()
    ).all()

    if request.method == "POST":
        patient_id = request.form.get("patient_id", type=int)
        doctor_id = request.form.get("doctor_id", type=int)
        appt_date = request.form.get("appointment_date", "")
        appt_time = request.form.get("appointment_time", "")
        reason = request.form.get("reason", "").strip() or None

        errors = []
        patient = db.session.get(Patient, patient_id) if patient_id else None
        doctor = db.session.get(Doctor, doctor_id) if doctor_id else None

        if not patient:
            errors.append("Please select a valid patient (search by code/name/phone).")
        if not doctor:
            errors.append("Please select a doctor.")

        parsed_date = parsed_time = None
        try:
            parsed_date = datetime.strptime(appt_date, "%Y-%m-%d").date()
        except ValueError:
            errors.append("Please provide a valid appointment date.")
        try:
            parsed_time = datetime.strptime(appt_time, "%H:%M").time()
        except ValueError:
            errors.append("Please provide a valid appointment time.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "receptionist/create_appointment.html",
                doctors=doctors,
                form=request.form,
                preselected_patient=patient,
            )

        appt = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_date=parsed_date,
            appointment_time=parsed_time,
            reason=reason,
            created_by=current_user.id,
        )
        db.session.add(appt)
        db.session.commit()

        print("DEBUG: Patient email =", patient.email)
        
        if patient.email:
         send_email(
        patient.email,
        "SmartCare Appointment Confirmation",
        f"""
        <h2>SmartCare Appointment Confirmation</h2>

        <p>Hello {patient.full_name},</p>

        <p>Your appointment has been successfully scheduled.</p>

        <hr>

        <p><strong>Doctor:</strong> Dr. {doctor.full_name}</p>
        <p><strong>Date:</strong> {parsed_date.strftime('%d %B %Y')}</p>
        <p><strong>Time:</strong> {parsed_time.strftime('%I:%M %p')}</p>
        <p><strong>Status:</strong> Scheduled</p>

        <br>

        <p>Thank you for using SmartCare.</p>
        """
    )

         flash(
    f"Appointment created for {patient.full_name} with Dr. {doctor.full_name} "
    f"on {parsed_date.strftime('%d %b %Y')} at {parsed_time.strftime('%I:%M %p')}.",
    "success",
)
         return redirect(url_for("receptionist.appointments"))

    preselected_patient = (
        db.session.get(Patient, preselected_patient_id) if preselected_patient_id else None
    )
    return render_template(
        "receptionist/create_appointment.html",
        doctors=doctors,
        form={},
        preselected_patient=preselected_patient,
    )


@receptionist_bp.route("/patients/lookup")
@login_required
@role_required("receptionist")
def patient_lookup():
    """Small JSON endpoint used by vanilla JS for the appointment-creation
    patient auto-complete search box."""
    from flask import jsonify

    q = request.args.get("q", "").strip()
    results = []
    if len(q) >= 2:
        like = f"%{q}%"
        patients = (
            Patient.query.filter(
                or_(
                    Patient.full_name.ilike(like),
                    Patient.phone.ilike(like),
                    Patient.patient_code.ilike(like),
                )
            )
            .limit(8)
            .all()
        )
        results = [
            {
                "id": p.id,
                "code": p.patient_code,
                "name": p.full_name,
                "phone": p.phone,
                "label": f"{p.patient_code} - {p.full_name} ({p.phone})",
            }
            for p in patients
        ]
    return jsonify(results)
