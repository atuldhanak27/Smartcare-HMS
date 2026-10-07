-- =============================================================================
-- SmartCare Hospital Management System - MySQL 8.0+ Schema
-- =============================================================================
-- This file is provided for reference / manual setup and mirrors exactly what
-- SQLAlchemy (app/models.py) creates. You can either:
--   (a) run this file directly:  mysql -u root -p smartcare_db < scripts/schema.sql
--   (b) or let SQLAlchemy create tables automatically via scripts/seed_admin.py
--       (it calls db.create_all() before seeding the admin user).
-- =============================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- -----------------------------------------------------------------------------
-- users
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS `prescription_items`;
DROP TABLE IF EXISTS `prescriptions`;
DROP TABLE IF EXISTS `medical_records`;
DROP TABLE IF EXISTS `appointments`;
DROP TABLE IF EXISTS `vitals`;
DROP TABLE IF EXISTS `patients`;
DROP TABLE IF EXISTS `doctors`;
DROP TABLE IF EXISTS `users`;

CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(64) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `role` ENUM('admin','receptionist','doctor') NOT NULL,
    `full_name` VARCHAR(120) NOT NULL,
    `email` VARCHAR(120) UNIQUE,
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `ix_users_username` (`username`),
    INDEX `ix_users_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------------------------------
-- doctors
-- -----------------------------------------------------------------------------
CREATE TABLE `doctors` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `specialization` VARCHAR(120) NOT NULL,
    `phone` VARCHAR(20),
    `qualification` VARCHAR(150),
    `experience_years` INT DEFAULT 0,
    INDEX `ix_doctors_user_id` (`user_id`),
    CONSTRAINT `fk_doctors_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------------------------------
-- patients
-- -----------------------------------------------------------------------------
CREATE TABLE `patients` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `patient_code` VARCHAR(20) NOT NULL UNIQUE,
    `full_name` VARCHAR(120) NOT NULL,
    `age` INT NOT NULL,
    `gender` ENUM('Male','Female','Other') NOT NULL,
    `phone` VARCHAR(20) NOT NULL,
    `email` VARCHAR(120),
    `address` VARCHAR(255),
    `blood_group` VARCHAR(5),
    `emergency_contact` VARCHAR(20),
    `created_by` INT NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `ix_patients_patient_code` (`patient_code`),
    INDEX `ix_patients_full_name` (`full_name`),
    INDEX `ix_patients_phone` (`phone`),
    CONSTRAINT `fk_patients_creator` FOREIGN KEY (`created_by`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------------------------------
-- vitals
-- -----------------------------------------------------------------------------
CREATE TABLE `vitals` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `patient_id` INT NOT NULL,
    `blood_pressure` VARCHAR(20),
    `blood_sugar` VARCHAR(20),
    `temperature` VARCHAR(20),
    `weight` FLOAT,
    `height` FLOAT,
    `pulse` INT,
    `symptoms` TEXT,
    `recorded_by` INT NOT NULL,
    `recorded_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `ix_vitals_patient_id` (`patient_id`),
    INDEX `ix_vitals_recorded_at` (`recorded_at`),
    CONSTRAINT `fk_vitals_patient` FOREIGN KEY (`patient_id`) REFERENCES `patients`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_vitals_recorder` FOREIGN KEY (`recorded_by`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------------------------------
-- appointments
-- -----------------------------------------------------------------------------
CREATE TABLE `appointments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `patient_id` INT NOT NULL,
    `doctor_id` INT NOT NULL,
    `appointment_date` DATE NOT NULL,
    `appointment_time` TIME NOT NULL,
    `status` ENUM('Scheduled','Completed','Cancelled','No-Show') NOT NULL DEFAULT 'Scheduled',
    `reason` VARCHAR(255),
    `notes` TEXT,
    `created_by` INT NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `ix_appointments_patient_id` (`patient_id`),
    INDEX `ix_appointments_doctor_id` (`doctor_id`),
    INDEX `ix_appointments_appointment_date` (`appointment_date`),
    INDEX `ix_appointments_status` (`status`),
    INDEX `ix_appt_doctor_date` (`doctor_id`, `appointment_date`),
    CONSTRAINT `fk_appt_patient` FOREIGN KEY (`patient_id`) REFERENCES `patients`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_appt_doctor` FOREIGN KEY (`doctor_id`) REFERENCES `doctors`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_appt_creator` FOREIGN KEY (`created_by`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------------------------------
-- medical_records
-- -----------------------------------------------------------------------------
CREATE TABLE `medical_records` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `patient_id` INT NOT NULL,
    `doctor_id` INT NOT NULL,
    `appointment_id` INT UNIQUE,
    `diagnosis` TEXT NOT NULL,
    `clinical_notes` TEXT,
    `follow_up_date` DATE,
    `recorded_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `ix_medrec_patient_id` (`patient_id`),
    INDEX `ix_medrec_doctor_id` (`doctor_id`),
    INDEX `ix_medrec_recorded_at` (`recorded_at`),
    CONSTRAINT `fk_medrec_patient` FOREIGN KEY (`patient_id`) REFERENCES `patients`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_medrec_doctor` FOREIGN KEY (`doctor_id`) REFERENCES `doctors`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_medrec_appointment` FOREIGN KEY (`appointment_id`) REFERENCES `appointments`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------------------------------
-- prescriptions
-- -----------------------------------------------------------------------------
CREATE TABLE `prescriptions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `medical_record_id` INT NOT NULL UNIQUE,
    `patient_id` INT NOT NULL,
    `doctor_id` INT NOT NULL,
    `prescription_date` DATE NOT NULL DEFAULT (CURRENT_DATE),
    `advice` TEXT,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `ix_presc_patient_id` (`patient_id`),
    INDEX `ix_presc_doctor_id` (`doctor_id`),
    CONSTRAINT `fk_presc_medrec` FOREIGN KEY (`medical_record_id`) REFERENCES `medical_records`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_presc_patient` FOREIGN KEY (`patient_id`) REFERENCES `patients`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_presc_doctor` FOREIGN KEY (`doctor_id`) REFERENCES `doctors`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------------------------------
-- prescription_items
-- -----------------------------------------------------------------------------
CREATE TABLE `prescription_items` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `prescription_id` INT NOT NULL,
    `medicine_name` VARCHAR(150) NOT NULL,
    `dosage` VARCHAR(50) NOT NULL,
    `frequency` VARCHAR(50) NOT NULL,
    `duration` VARCHAR(50) NOT NULL,
    `instructions` VARCHAR(255),
    INDEX `ix_rxitem_prescription_id` (`prescription_id`),
    CONSTRAINT `fk_rxitem_prescription` FOREIGN KEY (`prescription_id`) REFERENCES `prescriptions`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================================
-- Seed admin user
-- -----------------------------------------------------------------------------
-- Passwords must be hashed with Werkzeug's generate_password_hash() - a raw SQL
-- INSERT cannot produce a valid salted hash, so the seed admin account is
-- created by the Python script instead. After running this schema file, seed
-- the admin account with:
--
--     python scripts/seed_admin.py
--
-- It reads ADMIN_USERNAME / ADMIN_PASSWORD / ADMIN_EMAIL from your .env file
-- (defaults: admin / Admin@123 / admin@smartcare.local) and inserts a
-- correctly-hashed admin user, safe to run multiple times (it skips creation
-- if the user already exists).
-- =============================================================================
