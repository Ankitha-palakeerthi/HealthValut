# HealthVault Connect

## Overview

HealthVault Connect is a healthcare appointment and consultation management platform designed to simplify interactions between patients and doctors. The platform enables patients to discover doctors, book appointments, maintain personal health information, and receive consultation records digitally. Doctors can efficiently manage schedules, appointments, patient records, diagnoses, and prescriptions through a dedicated dashboard.

This project was developed as a solution for the Build for Ambula '26 Hackathon.

---

## Features

### Patient Features

* Browse and search doctors by specialization
* View doctor profiles and consultation fees
* Book appointments with available time slots
* Receive a unique Booking ID for every appointment
* Maintain a personal health summary including:

  * Blood Group
  * Medical Conditions
  * Current Medications
* Access appointment details and consultation records

### Doctor Features

* Secure doctor login
* View daily appointment dashboard
* Access patient health summaries before consultation
* Add diagnosis notes
* Generate prescriptions
* Manage appointment schedules
* Block unavailable dates and time slots
* View patient database
* Access analytics dashboard
* Manage practice settings

---

## Double Booking Prevention

The platform prevents double booking at the backend level using database validation and slot availability checks.

If two patients attempt to book the same appointment slot simultaneously, only one booking is accepted while the other patient is prompted to select another available slot.

This ensures reliable scheduling under concurrent booking requests.

---

## Technology Stack

### Frontend

* HTML5
* CSS3
* JavaScript
* Responsive Mobile-Friendly UI

### Backend

* Python
* Flask

### Database

* SQLite

### Version Control

* Git
* GitHub

---

## Project Structure

HealthVault Connect

backend/

* app.py
* models.py

frontend/

* templates/
* static/

instance/

* database.db

requirements.txt

---

## Core Modules

### Appointment Management

* Appointment booking
* Booking confirmation
* Booking ID generation

### Consultation Management

* Diagnosis recording
* Prescription generation
* Follow-up tracking

### Doctor Dashboard

* Appointment overview
* Patient management
* Analytics

### Patient Dashboard

* Health profile
* Appointment history
* Booking management

---

## Future Improvements

* Online video consultations
* Payment gateway integration
* Email and SMS notifications
* Electronic Medical Records (EMR)
* AI-powered health recommendations

---

## Author

P. Ankitha

Rajiv Gandhi University of Knowledge Technologies (RGUKT), Ongole

Build for Ambula '26 Hackathon Submission
