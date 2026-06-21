from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'patient' or 'doctor'

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    specialization = db.Column(db.String(100), nullable=False)
    fee = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    experience = db.Column(db.Integer, nullable=False)
    rating = db.Column(db.Float, default=4.5)
    
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    phone = db.Column(db.String(20))
    blood_group = db.Column(db.String(10))
    medical_conditions = db.Column(db.Text) # JSON or Comma separated
    medications = db.Column(db.Text)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.String(20), unique=True, nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False) # YYYY-MM-DD
    time = db.Column(db.String(10), nullable=False) # HH:MM
    status = db.Column(db.String(20), default='Scheduled') # Scheduled, Completed, Cancelled
    
    # Double booking prevention constraint
    __table_args__ = (db.UniqueConstraint('doctor_id', 'date', 'time', name='_doctor_slot_uc'),)

class Consultation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'))
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    follow_up_date = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BlockedSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    time_slot = db.Column(db.String(10), nullable=False)
    
    __table_args__ = (db.UniqueConstraint('doctor_id', 'date', 'time_slot', name='_doctor_blocked_uc'),)
