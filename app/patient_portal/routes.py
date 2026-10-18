"""
Patient self-registration + appointment booking (public, no login).

  GET  /patient/register   form
  GET  /patient/slots      JSON list of genuinely free times for ?date=YYYY-MM-DD
  POST /patient/register   validate -> re-check slot on server -> book atomically -> email
  GET  /patient/booked     confirmation page (shown once, after a successful booking)
"""

import hmac
import re
import secrets
import time as _time
import unicodedata
from collections import defaultdict, deque
from datetime import datetime, date, timedelta

from flask import (
    render_template, redirect, url_for, request, flash, session, abort, jsonify,
    make_response, current_app,
)
from markupsafe import escape

from app.extensions import db
from app.models import Patient, Appointment, Doctor
from app.patient_portal import patient_portal_bp
from app.patient_portal import scheduling
from app.utils.email_service import send_email

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-']+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\+?\d{10,15}$")

# Very small in-memory throttle (per server process) against form flooding.
_THROTTLE_MAX = 10
_THROTTLE_WINDOW = 600
_attempts = defaultdict(deque)


def _throttled():
    now = _time.time()
    q = _attempts[request.remote_addr or "?"]
    while q and now - q[0] > _THROTTLE_WINDOW:
        q.popleft()
    if len(q) >= _THROTTLE_MAX:
        return True
    q.append(now)
    return False


def _csrf_token():
    if "portal_csrf" not in session:
        session["portal_csrf"] = secrets.token_urlsafe(24)
    return session["portal_csrf"]


def _csrf_ok():
    sent = request.form.get("csrf_token", "")
    expected = session.get("portal_csrf", "")
    return bool(expected) and hmac.compare_digest(sent, expected)


def _valid_name(name):
    if not (2 <= len(name) <= 120) or not name[0].isalpha():
        return False
    for ch in name:
        cat = unicodedata.category(ch)
        if not (cat.startswith("L") or cat.startswith("M") or ch in " .'’-"):
            return False
    return True


def _clean_form(form, rules):
    """Return (clean_values, list_of_error_messages)."""
    errors = []
    name = re.sub(r"\s+", " ", form.get("full_name", "")).strip()
    phone_raw = form.get("phone", "").strip()
    phone = re.sub(r"[\s\-().]", "", phone_raw)
    email = (form.get("email") or "").strip().lower()
    date_raw = form.get("appointment_date", "").strip()
    time_raw = form.get("appointment_time", "").strip()
    doctor_raw = form.get("doctor_id", "").strip()

    if not name:
        errors.append("Patient name is required.")
    elif not _valid_name(name):
        errors.append("Please enter a valid name (letters, spaces, . ' - only).")

    if not phone_raw:
        errors.append("Mobile number is required.")
    elif not PHONE_RE.match(phone):
        errors.append("Please enter a valid mobile number (10 to 15 digits, optional + prefix).")

    # if not email:
    #     errors.append("Email address is required.")
    # elif len(email) > 120 or not EMAIL_RE.match(email):
    #     errors.append("Please enter a valid email address.")
    if not email or len(email) > 120 or not EMAIL_RE.match(email):
     errors.append("Please enter a valid email address.")

    day = slot = None
    if not date_raw:
        errors.append("Preferred appointment date is required.")
    else:
        try:
            day = datetime.strptime(date_raw, "%Y-%m-%d").date()
            if not scheduling.date_is_bookable(day, rules):
                errors.append("Online booking is not available for that date. "
                              "Please choose another date.")
                day = None
        except ValueError:
            errors.append("Please choose a valid appointment date.")

    if not time_raw:
        errors.append("Please select an available appointment time.")
    else:
        try:
            slot = datetime.strptime(time_raw, "%H:%M").time()
        except ValueError:
            errors.append("Please select a valid appointment time.")

    doctor_id = None
    if not doctor_raw:
        errors.append("Please select a doctor.")
    else:
        try:
            doctor_id = int(doctor_raw)
            doctor = db.session.get(Doctor, doctor_id)
            if not doctor or not doctor.user or not doctor.user.is_active:
                errors.append("Please select a currently available doctor.")
        except (TypeError, ValueError):
            errors.append("Please select a valid doctor.")

    clean = {"full_name": name, "phone": phone, "email": email,
             "day": day, "slot": slot, "doctor_id": doctor_id}
    return clean, errors


def _form_page(rules, form=None, status=200):
    today = date.today()
    resp = make_response(render_template(
        "patient_portal/register.html",
        form=form or {},
        csrf_token=_csrf_token(),
        min_date=today.isoformat(),
        max_date=(today + timedelta(days=rules.max_days_ahead)).isoformat(),
        doctors=[d for d in Doctor.query.order_by(Doctor.id).all()
                 if d.user and d.user.is_active],
    ), status)
    resp.headers["Cache-Control"] = "no-store"
    return resp


@patient_portal_bp.route("/register", methods=["GET", "POST"])
def register():
    rules = scheduling.get_rules()

    if request.method == "GET":
        return _form_page(rules)

    if not _csrf_ok():
        flash("Your session expired. Please submit the form again.", "warning")
        return _form_page(rules, request.form, 400)

    if request.form.get("website"):            # honeypot: real users never fill this
        return redirect(url_for("patient_portal.register"))

    if _throttled():
        flash("Too many attempts from this device. Please wait a few minutes and try again.",
              "warning")
        return _form_page(rules, request.form, 429)

    clean, errors = _clean_form(request.form, rules)
    if errors:
        for e in errors:
            flash(e, "danger")
        return _form_page(rules, request.form)

    # Email mismatch is a warning only; booking continues.
    

    # Server-side availability re-check + atomic booking happen inside this call.
    result = scheduling.book_appointment(
        clean["day"], clean["slot"], clean["full_name"], clean["phone"], clean["email"],
        doctor_id=clean["doctor_id"]
    )

    if not result.ok:
        flash(result.message, "danger")
        return _form_page(rules, request.form, 409 if result.status == "slot_unavailable" else 200)

    email_sent = None
    if not result.already_booked:
        email_sent = _send_confirmation(result.appointment_id)

    session["portal_booking"] = {"appointment_id": result.appointment_id,
                                 "email_sent": email_sent,
                                 "already_booked": result.already_booked}
    return redirect(url_for("patient_portal.booked"))


def _send_confirmation(appointment_id):
    """Only called AFTER the booking is committed. Returns True/False."""
    appt = db.session.get(Appointment, appointment_id)
    patient = db.session.get(Patient, appt.patient_id)
    doctor = db.session.get(Doctor, appt.doctor_id)
    if not patient.email:
        return False
    html = f"""
    <h2>SmartCare Registration &amp; Appointment Confirmation</h2>
    <p>Hello {escape(patient.full_name)},</p>
    <p>Your appointment has been confirmed. Please keep your Patient ID for future visits.</p>
    <hr>
    <p><strong>Patient ID:</strong> {escape(patient.patient_code)}</p>
    <p><strong>Patient Name:</strong> {escape(patient.full_name)}</p>
    <p><strong>Appointment Date:</strong> {appt.appointment_date.strftime('%d %B %Y')}</p>
    <p><strong>Appointment Time:</strong> {appt.appointment_time.strftime('%I:%M %p')}</p>
    <p><strong>Doctor:</strong> Dr. {escape(doctor.full_name)}</p>
    <p><strong>Status:</strong> {escape(appt.status)}</p>
    <br>
    <p>Thank you for choosing SmartCare.</p>
    """
    try:
        return bool(send_email(patient.email, "SmartCare Registration & Appointment Confirmation", html))
    except Exception:                          # noqa: BLE001
        current_app.logger.exception("Confirmation email failed")
        return False


@patient_portal_bp.route("/slots")
def slots():
    raw = request.args.get("date", "")
    try:
        day = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date.", "slots": []}), 400

    rules = scheduling.get_rules()
    raw_doctor_id = request.args.get("doctor_id", "").strip()
    doctor_id = None
    if raw_doctor_id:
        try:
            doctor_id = int(raw_doctor_id)
        except ValueError:
            return jsonify({"error": "Invalid doctor.", "slots": []}), 400
    if not scheduling.date_is_bookable(day, rules):
        data = {"slots": [], "message": "Online booking is not available for this date. "
                                        "Please choose another date."}
    else:
        free = scheduling.free_slots(day, doctor_id=doctor_id)
        data = {"slots": [{"value": t.strftime("%H:%M"), "label": t.strftime("%I:%M %p")}
                          for t in free]}
        if not free:
            data["message"] = ("No appointment slots are available on this date. "
                               "Please select another date.")
    resp = jsonify(data)
    resp.headers["Cache-Control"] = "no-store"
    return resp


@patient_portal_bp.route("/booked")
def booked():
    info = session.pop("portal_booking", None)
    if not info:
        return redirect(url_for("patient_portal.register"))
    appt = db.session.get(Appointment, info["appointment_id"])
    if appt is None:
        abort(404)
    patient = db.session.get(Patient, appt.patient_id)
    doctor = db.session.get(Doctor, appt.doctor_id)
    resp = make_response(render_template(
        "patient_portal/booked.html", appt=appt, patient=patient, doctor=doctor,
        email_sent=info.get("email_sent"), already_booked=info.get("already_booked"),
    ))
    resp.headers["Cache-Control"] = "no-store"
    return resp
