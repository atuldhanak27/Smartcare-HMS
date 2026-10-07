"""
SQLAlchemy ORM models for SmartCare.

Schema (MySQL 8.0+):
    users -> doctors (1:1)
    users -> patients (created_by)
    patients -> vitals (1:N)
    patients, doctors -> appointments (N:1 each)
    patients, doctors, appointments -> medical_records
    medical_records -> prescriptions (1:1)
    prescriptions -> prescription_items (1:N)
"""

from datetime import datetime, date, time

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


# ---------------------------------------------------------------------------
# USERS
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum("admin", "receptionist", "doctor", name="user_role"),
                      nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                            onupdate=datetime.utcnow, nullable=False)

    # relationships
    doctor_profile = db.relationship("Doctor", backref="user", uselist=False,
                                      cascade="all, delete-orphan")

    # -- password helpers --
    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(
    raw_password,
    method="pbkdf2:sha256:600000"
)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    # Flask-Login expects `is_active` to be a property/attribute it can read;
    # our column already satisfies that. We override get_id via UserMixin default.

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


# ---------------------------------------------------------------------------
# DOCTORS
# ---------------------------------------------------------------------------
class Doctor(db.Model):
    __tablename__ = "doctors"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                         nullable=False, unique=True, index=True)
    specialization = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    qualification = db.Column(db.String(150), nullable=True)
    experience_years = db.Column(db.Integer, default=0)

    appointments = db.relationship("Appointment", backref="doctor", lazy="dynamic")
    medical_records = db.relationship("MedicalRecord", backref="doctor", lazy="dynamic")
    prescriptions = db.relationship("Prescription", backref="doctor", lazy="dynamic")

    @property
    def full_name(self):
        return self.user.full_name if self.user else "Unknown"

    def __repr__(self):
        return f"<Doctor {self.full_name} - {self.specialization}>"


# ---------------------------------------------------------------------------
# PATIENTS
# ---------------------------------------------------------------------------
class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    patient_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False, index=True)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.Enum("Male", "Female", "Other", name="patient_gender"),
                        nullable=False)
    phone = db.Column(db.String(20), nullable=False, index=True)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    blood_group = db.Column(db.String(5), nullable=True)
    emergency_contact = db.Column(db.String(20), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                            onupdate=datetime.utcnow, nullable=False)

    creator = db.relationship("User", foreign_keys=[created_by])
    vitals = db.relationship("Vitals", backref="patient", lazy="dynamic",
                              cascade="all, delete-orphan", order_by="desc(Vitals.recorded_at)")
    appointments = db.relationship("Appointment", backref="patient", lazy="dynamic",
                                    cascade="all, delete-orphan")
    medical_records = db.relationship("MedicalRecord", backref="patient", lazy="dynamic",
                                       cascade="all, delete-orphan")
    prescriptions = db.relationship("Prescription", backref="patient", lazy="dynamic",
                                     cascade="all, delete-orphan")

    @staticmethod
    def generate_patient_code():
        """Generate a patient code in the form SC-YYYY-XXXX (sequential per year)."""
        year = date.today().year
        prefix = f"SC-{year}-"
        last = (
            Patient.query.filter(Patient.patient_code.like(f"{prefix}%"))
            .order_by(Patient.patient_code.desc())
            .first()
        )
        if last:
            last_seq = int(last.patient_code.split("-")[-1])
            new_seq = last_seq + 1
        else:
            new_seq = 1
        return f"{prefix}{new_seq:04d}"

    @property
    def latest_vitals(self):
        return self.vitals.first()  # already ordered desc by recorded_at

    def __repr__(self):
        return f"<Patient {self.patient_code} {self.full_name}>"


# ---------------------------------------------------------------------------
# VITALS
# ---------------------------------------------------------------------------
class Vitals(db.Model):
    __tablename__ = "vitals"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    blood_pressure = db.Column(db.String(20), nullable=True)   # e.g. "120/80"
    blood_sugar = db.Column(db.String(20), nullable=True)      # e.g. "95 mg/dL"
    temperature = db.Column(db.String(20), nullable=True)      # e.g. "98.6 F"
    weight = db.Column(db.Float, nullable=True)                # kg
    height = db.Column(db.Float, nullable=True)                # cm
    pulse = db.Column(db.Integer, nullable=True)                # bpm
    symptoms = db.Column(db.Text, nullable=True)
    recorded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    recorder = db.relationship("User", foreign_keys=[recorded_by])

    @property
    def bmi(self):
        if self.weight and self.height:
            h_m = self.height / 100.0
            if h_m > 0:
                return round(self.weight / (h_m * h_m), 1)
        return None

    def __repr__(self):
        return f"<Vitals patient={self.patient_id} at={self.recorded_at}>"


# ---------------------------------------------------------------------------
# APPOINTMENTS
# ---------------------------------------------------------------------------
class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    appointment_date = db.Column(db.Date, nullable=False, index=True)
    appointment_time = db.Column(db.Time, nullable=False)
    status = db.Column(
        db.Enum("Scheduled", "Completed", "Cancelled", "No-Show", name="appointment_status"),
        default="Scheduled", nullable=False, index=True,
    )
    reason = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                            onupdate=datetime.utcnow, nullable=False)

    creator = db.relationship("User", foreign_keys=[created_by])
    medical_record = db.relationship("MedicalRecord", backref="appointment",
                                      uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        db.Index("ix_appt_doctor_date", "doctor_id", "appointment_date"),
    )

    def __repr__(self):
        return f"<Appointment #{self.id} {self.appointment_date} {self.appointment_time}>"


# ---------------------------------------------------------------------------
# MEDICAL RECORDS
# ---------------------------------------------------------------------------
class MedicalRecord(db.Model):
    __tablename__ = "medical_records"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id", ondelete="SET NULL"),
                                nullable=True, unique=True)
    diagnosis = db.Column(db.Text, nullable=False)
    clinical_notes = db.Column(db.Text, nullable=True)
    follow_up_date = db.Column(db.Date, nullable=True)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    prescription = db.relationship("Prescription", backref="medical_record",
                                    uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MedicalRecord #{self.id} patient={self.patient_id}>"


# ---------------------------------------------------------------------------
# PRESCRIPTIONS
# ---------------------------------------------------------------------------
class Prescription(db.Model):
    __tablename__ = "prescriptions"

    id = db.Column(db.Integer, primary_key=True)
    medical_record_id = db.Column(db.Integer,
                                   db.ForeignKey("medical_records.id", ondelete="CASCADE"),
                                   nullable=False, unique=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    prescription_date = db.Column(db.Date, default=date.today, nullable=False)
    advice = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    items = db.relationship("PrescriptionItem", backref="prescription", lazy="joined",
                             cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Prescription #{self.id} patient={self.patient_id}>"


# ---------------------------------------------------------------------------
# PRESCRIPTION ITEMS
# ---------------------------------------------------------------------------
class PrescriptionItem(db.Model):
    __tablename__ = "prescription_items"

    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer,
                                 db.ForeignKey("prescriptions.id", ondelete="CASCADE"),
                                 nullable=False, index=True)
    medicine_name = db.Column(db.String(150), nullable=False)
    dosage = db.Column(db.String(50), nullable=False)          # e.g. "500mg"
    frequency = db.Column(db.String(50), nullable=False)       # e.g. "1-0-1"
    duration = db.Column(db.String(50), nullable=False)        # e.g. "5 days"
    instructions = db.Column(db.String(255), nullable=True)    # e.g. "After food"

    def __repr__(self):
        return f"<PrescriptionItem {self.medicine_name}>"
