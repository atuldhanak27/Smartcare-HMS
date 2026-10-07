# SmartCare — Hospital Management System

An academic mini-project implementing the complete daily clinical workflow of a
small hospital / clinic:

```
Patient Registration → Vitals Recording → Appointment Creation →
Doctor Consultation → Diagnosis & Medical Record → Prescription → Secure Storage
```

Built to improve on the limitations of the base paper **"Care Hive"** by adding
proper role-based access control, structured vitals capture, multi-medicine
prescriptions, and full patient history tracking.

This project has been **fully built and tested end-to-end against a real
MySQL 8.0 database** — patient registration, vitals, appointments,
consultations, multi-item prescriptions, and role-based access control were
all verified working before delivery.

---

## 1. Technology Stack

| Layer          | Technology                                   |
|-----------------|-----------------------------------------------|
| Backend         | Python 3.8+, Flask                            |
| Auth            | Flask-Login + Werkzeug password hashing       |
| Database        | MySQL 8.0+ (via PyMySQL, SQLAlchemy ORM)      |
| Frontend        | HTML5, CSS3, Bootstrap 5, vanilla JavaScript  |
| Structure       | Application Factory pattern + Blueprints      |
| Config          | python-dotenv                                 |

---

## 2. Project Structure

```
smartcare/
├── app/
│   ├── __init__.py              # Application factory
│   ├── extensions.py            # db, login_manager instances
│   ├── models.py                # SQLAlchemy models (8 tables)
│   ├── decorators.py            # @role_required RBAC decorator
│   ├── auth/                    # Login / logout blueprint
│   ├── admin/                   # Admin blueprint (users, doctors, stats)
│   ├── receptionist/            # Receptionist blueprint
│   ├── doctor/                  # Doctor blueprint
│   ├── templates/               # Jinja2 + Bootstrap 5 templates
│   │   ├── base.html
│   │   ├── auth/
│   │   ├── admin/
│   │   ├── receptionist/
│   │   ├── doctor/
│   │   └── errors/
│   └── static/
│       ├── css/style.css
│       └── js/main.js
├── scripts/
│   ├── schema.sql                # Raw MySQL DDL (reference / manual setup)
│   ├── seed_admin.py             # Creates tables + seeds first admin user
│   └── generate_password_hash.py # Standalone password-hash generator
├── config.py                     # App configuration (reads .env)
├── run.py                        # Entry point
├── requirements.txt
├── .env.example
└── README.md
```

---

## 3. Database Schema

8 tables, matching the spec exactly, with proper primary keys, foreign keys,
and indexes:

- **users** — id, username, password_hash, role (admin/receptionist/doctor), full_name, email, is_active, created_at, updated_at
- **doctors** — id, user_id (FK→users), specialization, phone, qualification, experience_years
- **patients** — id, patient_code (UNIQUE, format `SC-YYYY-XXXX`), full_name, age, gender, phone, email, address, blood_group, emergency_contact, created_by (FK→users), created_at, updated_at
- **vitals** — id, patient_id (FK), blood_pressure, blood_sugar, temperature, weight, height, pulse, symptoms, recorded_by (FK→users), recorded_at
- **appointments** — id, patient_id (FK), doctor_id (FK), appointment_date, appointment_time, status (Scheduled/Completed/Cancelled/No-Show), reason, notes, created_by (FK), created_at, updated_at
- **medical_records** — id, patient_id (FK), doctor_id (FK), appointment_id (FK), diagnosis, clinical_notes, follow_up_date, recorded_at
- **prescriptions** — id, medical_record_id (FK), patient_id (FK), doctor_id (FK), prescription_date, advice, created_at
- **prescription_items** — id, prescription_id (FK), medicine_name, dosage, frequency, duration, instructions

You can create these tables two ways:
1. **Automatically** — `scripts/seed_admin.py` calls `db.create_all()`, so it
   creates any missing tables from the SQLAlchemy models before seeding the
   admin user. This is the easiest path.
2. **Manually** — run `scripts/schema.sql` directly against MySQL if you want
   to inspect/customize the raw DDL first.

---

## 4. Roles & Permissions

| Role             | Capabilities |
|-------------------|--------------|
| **Admin**         | Create/manage users, register doctors, view system-wide stats, view all doctors |
| **Receptionist**  | Register patients (auto patient code), search patients, record vitals, create/view appointments |
| **Doctor**        | View today's appointments, run consultations, see patient history & latest vitals, enter diagnosis/notes/follow-up, generate multi-medicine prescriptions, view/print prescriptions |

Access control is enforced server-side via the `@role_required(...)` decorator
on every protected route — not just hidden in the UI.

---

## 5. Setup Instructions

### macOS

```bash
# 1. Install prerequisites
brew install python@3.11 mysql
brew services start mysql

# 2. Secure MySQL and create the database
mysql_secure_installation
mysql -u root -p -e "CREATE DATABASE smartcare_db CHARACTER SET utf8mb4;"

# 3. Set up the project
cd smartcare
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# edit .env: set DB_USER, DB_PASSWORD, DB_NAME, SECRET_KEY

# 5. Create tables + seed admin
python scripts/seed_admin.py

# 6. Run
python run.py
```
Open **http://127.0.0.1:5000** and log in with the admin credentials from `.env`.

> Mac gotchas: if `pip install` fails building `cryptography`, run
> `xcode-select --install` first. On Apple Silicon, add
> `export PATH="/opt/homebrew/bin:$PATH"` to your shell profile if `mysql`
> isn't found after `brew install`.

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip mysql-server -y
sudo service mysql start

sudo mysql -e "CREATE DATABASE smartcare_db CHARACTER SET utf8mb4;"
sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'yourpassword';"

cd smartcare
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env with your DB credentials

python scripts/seed_admin.py
python run.py
```

### Windows

```powershell
# Install Python from python.org and MySQL from dev.mysql.com/downloads/installer/
cd smartcare
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env
:: edit .env with Notepad, set your DB credentials

:: In MySQL Workbench or mysql CLI:
:: CREATE DATABASE smartcare_db CHARACTER SET utf8mb4;

python scripts\seed_admin.py
python run.py
```

---

## 6. Default Login

After running `scripts/seed_admin.py`, log in with the credentials from your
`.env` file (defaults shown below — **change these in production**):

```
Username: admin
Password: Admin@123
```

From the Admin dashboard, use **Add User** or **Register Doctor** to create
receptionist and doctor accounts (doctor accounts require a specialization).

---

## 7. Generating a Password Hash Manually

If you ever need to insert a user directly via SQL (bypassing the app), use:

```bash
python scripts/generate_password_hash.py "SomePassword123"
```

This prints a Werkzeug-compatible salted hash you can paste into an
`INSERT INTO users (...) VALUES (...)` statement. Never store plaintext
passwords in the database — `User.set_password()` / `check_password()`
(Werkzeug's `generate_password_hash` / `check_password_hash`) are used
everywhere in the app itself.

---

## 8. Notable Design Decisions

- **Application Factory + Blueprints**: `create_app()` in `app/__init__.py`
  wires together four blueprints (`auth`, `admin`, `receptionist`, `doctor`),
  each with its own routes and templates folder, so the codebase scales
  cleanly and each role's logic is isolated.
- **Server-side RBAC**: the `@role_required()` decorator (in
  `app/decorators.py`) aborts with `403` if the logged-in user's role isn't
  permitted — enforced on every sensitive route, not just hidden nav links.
- **Auto-generated patient codes**: `Patient.generate_patient_code()` looks up
  the highest existing code for the current year and increments it, producing
  `SC-2026-0001`, `SC-2026-0002`, etc.
- **Vanilla JS, no build step**: the prescription form's "Add Medicine" rows,
  the patient search autocomplete (backed by a small JSON endpoint at
  `/reception/patients/lookup`), and the live BMI calculator on the vitals
  form are all plain JavaScript in `static/js/main.js` — no npm, no bundler.
- **One-appointment-one-consultation**: `medical_records.appointment_id` is
  `UNIQUE`, so an appointment can only be consulted once; the UI redirects to
  the existing prescription if a doctor revisits an already-completed
  appointment.
- **Printable prescriptions**: `doctor/prescription_view.html` includes
  print-specific CSS (`@media print` in `style.css`) that hides navigation
  chrome so the prescription prints cleanly.

---

## 9. Testing Notes

This project was verified against a live MySQL 8.0 instance covering:
- Admin creating a doctor and a receptionist
- Receptionist registering a patient (patient code auto-generation confirmed)
- Recording vitals and looking patients up via the autocomplete endpoint
- Booking an appointment
- Doctor logging in, seeing the appointment on their dashboard, opening the
  consultation, and submitting a diagnosis with a 2-item prescription
- Confirming the appointment status flips to `Completed` and the prescription
  renders correctly on the print view and in patient history
- Confirming role-based access control returns `403` when a receptionist
  tries to access admin routes, and vice versa for a doctor trying to access
  receptionist routes

---

## 10. License / Academic Use

This project is provided as an academic mini-project template. Feel free to
extend it (e.g. add lab/pharmacy modules, billing, SMS/email reminders) for
coursework or demonstration purposes.
