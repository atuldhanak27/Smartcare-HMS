"""
Slot availability and race-safe booking for patient self-registration.

IMPORTANT - what "existing scheduling rules" means in this project:
  * The only scheduling rule that already exists is
    Config.APPOINTMENT_SLOT_MINUTES (15). It is reused here as the slot length.
  * Your project has NO working hours and NO double-booking check anywhere
    (the receptionist form accepts any time). So the opening hours below are
    NEW, configurable settings (see .env.example), not existing rules.

No schema changes: there is no unique constraint on (doctor, date, time) and
we are not allowed to add one, so double-booking is prevented with a database
transaction that takes row locks (SELECT ... FOR UPDATE) on the doctor rows
BEFORE reading availability. Concurrent self-bookings therefore queue up and
each one sees the previous one's committed booking.
"""

import os
import re
from dataclasses import dataclass
from datetime import datetime, date, time, timedelta

from flask import current_app
from sqlalchemy import func, or_, and_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Patient, Appointment, Doctor, User

# Appointments in these states occupy their slot. Cancelled / No-Show free it.
BLOCKING_STATUSES = ("Scheduled", "Completed")

SYSTEM_USERNAME = "online_self_registration"
SYSTEM_FULL_NAME = "Online Self-Registration"
BOOKING_REASON = "Booked online (self-registration)"
MAX_UPCOMING_PER_PATIENT = 2


# ---------------------------------------------------------------------------
# rules
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Rules:
    slot_minutes: int
    start: time
    end: time
    max_days_ahead: int
    min_lead_minutes: int
    open_weekdays: tuple          # Monday=0 ... Sunday=6


def _env_time(name, default):
    raw = os.environ.get(name, default).strip()
    try:
        return datetime.strptime(raw, "%H:%M").time()
    except ValueError:
        return datetime.strptime(default, "%H:%M").time()


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return int(default)


def get_rules():
    weekdays = []
    for part in os.environ.get("SELF_BOOKING_WEEKDAYS", "0,1,2,3,4,5,6").split(","):
        part = part.strip()
        if part.isdigit() and 0 <= int(part) <= 6:
            weekdays.append(int(part))
    return Rules(
        slot_minutes=int(current_app.config.get("APPOINTMENT_SLOT_MINUTES", 15)),  # existing rule
        start=_env_time("SELF_BOOKING_START", "09:00"),
        end=_env_time("SELF_BOOKING_END", "17:00"),
        max_days_ahead=_env_int("SELF_BOOKING_MAX_DAYS_AHEAD", "30"),
        min_lead_minutes=_env_int("SELF_BOOKING_MIN_LEAD_MINUTES", "30"),
        open_weekdays=tuple(weekdays) or (0, 1, 2, 3, 4, 5, 6),
    )


def date_is_bookable(day, rules, today=None):
    today = today or date.today()
    if day < today or day > today + timedelta(days=rules.max_days_ahead):
        return False
    return day.weekday() in rules.open_weekdays


def candidate_slots(day, rules, now=None):
    """Every slot the hospital offers on `day` (ignoring existing bookings)."""
    now = now or datetime.now()
    slots = []
    cur = datetime.combine(day, rules.start)
    close = datetime.combine(day, rules.end)
    step = timedelta(minutes=rules.slot_minutes)
    earliest = now + timedelta(minutes=rules.min_lead_minutes)
    while cur + step <= close:
        if cur >= earliest:
            slots.append(cur.time())
        cur += step
    return slots


def _minutes(t):
    return t.hour * 60 + t.minute


def _overlaps(appt_time, slot_time, slot_minutes):
    """True if an appointment starting at appt_time collides with the slot."""
    return abs(_minutes(appt_time) - _minutes(slot_time)) < slot_minutes


def _active_doctors():
    return [d for d in Doctor.query.order_by(Doctor.id).all() if d.user and d.user.is_active]


def _blocking_appointments(day, doctor_ids):
    if not doctor_ids:
        return []
    return Appointment.query.filter(
        Appointment.appointment_date == day,
        Appointment.doctor_id.in_(doctor_ids),
        Appointment.status.in_(BLOCKING_STATUSES),
    ).all()


def _free_doctors(slot, active, appts, slot_minutes):
    busy = {a.doctor_id for a in appts if _overlaps(a.appointment_time, slot, slot_minutes)}
    return [d for d in active if d.id not in busy]


def free_slots(day, doctor_id=None):
    """Slots on `day` where a selected active doctor (or any active doctor) is free."""
    rules = get_rules()
    if not date_is_bookable(day, rules):
        return []
    active = _active_doctors()
    if doctor_id is not None:
        active = [d for d in active if d.id == doctor_id]
    if not active:
        return []
    appts = _blocking_appointments(day, [d.id for d in active])
    return [
        s for s in candidate_slots(day, rules)
        if _free_doctors(s, active, appts, rules.slot_minutes)
    ]


# ---------------------------------------------------------------------------
# identity
# ---------------------------------------------------------------------------
def phone_tail(phone):
    digits = re.sub(r"\D", "", phone or "")
    return digits[-10:] if len(digits) >= 10 else ""


def _normalised_phone_column():
    col = Patient.phone
    for ch in (" ", "-", "+", "(", ")", ".", "\t"):
        col = func.replace(col, ch, "")
    return col


# def resolve_patient(phone, email):
#     """
#     Returns (patient_or_None, verdict) where verdict is:
#       "reuse"      - an existing record matches BOTH mobile and email
#       "new"        - nothing matches either; safe to create a record
#       "unverified" - only ONE of mobile/email matches an existing record. We
#                      cannot prove it is the same person, and creating another
#                      record would duplicate them, so we do neither.
#     """
#     phone_match = _normalised_phone_column().like("%" + phone_tail(phone))
#     email_match = func.lower(Patient.email) == email.strip().lower()

#     both = Patient.query.filter(and_(phone_match, email_match)).order_by(Patient.id).first()
#     if both is not None:
#         return both, "reuse"
#     if Patient.query.filter(or_(phone_match, email_match)).first() is not None:
#         return None, "unverified"
#     return None, "new"
# def resolve_patient(phone, email):
#     """
#     Reuse an existing patient only when BOTH email and mobile match.
#     Never create a duplicate if either detail already belongs to a patient.
#     """
#     normal_email = (email or "").strip().lower()
#     normal_phone = phone_tail(phone or "")

#     if not normal_email or not normal_phone:
#         return None, "unverified"

#     phone_match = _normalised_phone_column().like("%" + normal_phone)
#     email_match = func.lower(func.trim(Patient.email)) == normal_email

#     # Both details must match the SAME existing patient.
#     patient = Patient.query.filter(
#         and_(phone_match, email_match)
#     ).order_by(Patient.id).first()

#     if patient is not None:
#         return patient, "reuse"

#     # If either detail already exists, do not create a duplicate.
#     existing = Patient.query.filter(
#         or_(phone_match, email_match)
#     ).first()

#     if existing is not None:
#         return None, "unverified"

#     return None, "new"
def normalize_email(email):
    return (email or "").strip().lower()


def normalize_phone(phone):
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    return digits[-10:]


def normalize_name(name):
    return " ".join((name or "").strip().lower().split())


def resolve_patient(full_name, phone, email):
    patients = Patient.query.all()

    name_key = normalize_name(full_name)
    phone_key = normalize_phone(phone)
    email_key = normalize_email(email)

    for patient in patients:
        same_name = normalize_name(patient.full_name) == name_key
        same_phone = normalize_phone(patient.phone) == phone_key
        same_email = normalize_email(patient.email) == email_key

        if same_name and same_phone and same_email:
            return patient, "existing"

    return None, "new"


def _get_system_user():
    """
    patients.created_by / appointments.created_by are NOT NULL foreign keys to
    users. Self-registered patients have no staff creator, so we use one
    dedicated, INACTIVE account (cannot log in; random unknown password).
    """
    import secrets
    user = User.query.filter_by(username=SYSTEM_USERNAME).first()
    if user is None:
        user = User(
            username=SYSTEM_USERNAME,
            role="receptionist",
            full_name=SYSTEM_FULL_NAME,
            email=None,
            is_active=False,
        )
        user.set_password(secrets.token_urlsafe(48))
        db.session.add(user)
        db.session.flush()
    return user


# ---------------------------------------------------------------------------
# booking
# ---------------------------------------------------------------------------
@dataclass
class BookingResult:
    status: str                    # ok | slot_unavailable | invalid_slot | unverified_identity
                                   # | too_many | no_doctors | error
    message: str = ""
    patient_id: int = None
    appointment_id: int = None
    new_patient: bool = False
    already_booked: bool = False   # idempotent repeat of the same booking

    @property
    def ok(self):
        return self.status == "ok"


def _fail(status, message):
    db.session.rollback()
    return BookingResult(status=status, message=message)


def _lock_doctors():
    """
    First statement of the booking transaction. Locking reads see the latest
    committed data, and the later plain SELECTs create their snapshot only
    AFTER the lock is held, so they include every booking committed by the
    transaction we just waited for.
    """
    return Doctor.query.order_by(Doctor.id).with_for_update().all()


def book_appointment(day, slot, full_name, phone, email, doctor_id=None):
    """
    Atomically verify the slot and save patient + appointment.
    Nothing is saved unless the whole booking succeeds.
    """
    last_error = None
    for _attempt in (1, 2):
        try:
            return _book_once(day, slot, full_name, phone, email, doctor_id=doctor_id)
        except IntegrityError as exc:          # e.g. patient_code race - retry once
            db.session.rollback()
            last_error = exc
        except Exception as exc:               # noqa: BLE001
            db.session.rollback()
            current_app.logger.exception("Self-registration booking failed")
            last_error = exc
            break
    current_app.logger.error("Self-registration booking failed: %s", last_error)
    return BookingResult(
        status="error",
        message="We could not complete your booking because of a system problem. "
                "Nothing was booked and no confirmation was sent. Please try again "
                "or contact the reception desk.",
    )


def _book_once(day, slot, full_name, phone, email, doctor_id=None):
    db.session.rollback()                       # make sure we start a fresh transaction
    doctors = _lock_doctors()                   # <-- serialises concurrent bookings
    active = [d for d in doctors if d.user and d.user.is_active]
    rules = get_rules()

    if doctor_id is not None:
        active = [d for d in active if d.id == doctor_id]
    if not active:
        return _fail("no_doctors", "The selected doctor is not available for online booking. "
                                   "Please select another doctor or contact reception.")

    if not date_is_bookable(day, rules) or slot not in candidate_slots(day, rules):
        return _fail("invalid_slot", "That date or time cannot be booked online. "
                                     "Please choose another date.")

    patient, verdict = resolve_patient(full_name, phone, email)
    if verdict == "unverified":
        return _fail(
            "unverified_identity",
            "We found an existing patient record that matches some of these details, but "
            "we could not verify it is you. To protect patient records we cannot book "
            "online. Please contact the reception desk and they will help you.",
        )

    if patient is not None:
        # Same patient, same slot already booked (e.g. double-click / refresh): do not rebook.
        for a in Appointment.query.filter(
            Appointment.patient_id == patient.id,
            Appointment.appointment_date == day,
            Appointment.status == "Scheduled",
        ).all():
            if (doctor_id is None or a.doctor_id == doctor_id) and _overlaps(a.appointment_time, slot, rules.slot_minutes):
                result = BookingResult(status="ok", patient_id=patient.id,
                                       appointment_id=a.id, already_booked=True)
                db.session.rollback()
                return result

        upcoming = Appointment.query.filter(
            Appointment.patient_id == patient.id,
            Appointment.status == "Scheduled",
            Appointment.appointment_date >= date.today(),
        ).count()
        if upcoming >= MAX_UPCOMING_PER_PATIENT:
            return _fail(
                "too_many",
                f"You already have {upcoming} upcoming appointments. Please attend or "
                "cancel one, or contact the reception desk, before booking another.",
            )

    appts = _blocking_appointments(day, [d.id for d in active])
    free = _free_doctors(slot, active, appts, rules.slot_minutes)
    if not free:
        return _fail("slot_unavailable",
                     "Sorry, that time was just taken. Nothing has been booked. "
                     "Please choose another time or date.")

    if doctor_id is not None:
        if not any(d.id == doctor_id for d in free):
            return _fail("slot_unavailable", "That time is no longer available with the selected doctor. Please choose another time.")
        doctor = next(d for d in free if d.id == doctor_id)
    else:
        # Backward-compatible automatic assignment for existing internal callers.
        load = {d.id: 0 for d in free}
        for a in appts:
            if a.doctor_id in load:
                load[a.doctor_id] += 1
        doctor = min(free, key=lambda d: (load[d.id], d.id))

    system_user = _get_system_user()
    new_patient = patient is None
    if new_patient:
        patient = Patient(
            patient_code=Patient.generate_patient_code(),   # existing ID generator
            full_name=full_name,
            age=0,              # NOT NULL column that this form does not collect
            gender="Other",     # NOT NULL column that this form does not collect
            phone=phone,
            email=email,
            created_by=system_user.id,
        )
        db.session.add(patient)
        db.session.flush()

    appt = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=day,
        appointment_time=slot,
        status="Scheduled",
        reason=BOOKING_REASON,
        created_by=system_user.id,
    )
    db.session.add(appt)
    db.session.commit()                         # releases the doctor locks

    return BookingResult(status="ok", patient_id=patient.id, appointment_id=appt.id,
                         new_patient=new_patient)
