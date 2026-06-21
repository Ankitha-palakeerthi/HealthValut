import os
import random
import string
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Doctor, Patient, Appointment, Consultation, BlockedSlot
from sqlalchemy import inspect, text
from datetime import datetime, timedelta

app = Flask(__name__, 
            template_folder='../frontend/templates',
            static_folder='../frontend/static')
app.config['SECRET_KEY'] = 'healthvault-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def generate_booking_id():
    return 'HV' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            if user.role == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            return redirect(url_for('patient_dashboard'))
        flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        name = request.form.get('name')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
            
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw, role=role)
        db.session.add(new_user)
        db.session.commit()
        
        if role == 'doctor':
            doctor = Doctor(user_id=new_user.id, name=name, specialization="General Physician", fee=500, location="City Hospital", experience=5)
            db.session.add(doctor)
        else:
            patient = Patient(user_id=new_user.id, name=name)
            db.session.add(patient)
            
        db.session.commit()
        flash('Registration successful!', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Doctor Search
@app.route('/doctors')
def doctor_listing():
    specialization = request.args.get('specialization')
    location = request.args.get('location')
    
    query = Doctor.query
    if specialization:
        query = query.filter(Doctor.specialization.ilike(f'%{specialization}%'))
    if location:
        query = query.filter(Doctor.location.ilike(f'%{location}%'))
        
    doctors = query.all()
    return render_template('doctor_listing.html', doctors=doctors)

@app.route('/doctor/<int:doctor_id>')
def doctor_profile(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    # Generate slots for the next 7 days
    slots = []
    today = datetime.now()
    for i in range(1, 8):
        date_str = (today + timedelta(days=i)).strftime('%Y-%m-%d')
        # Filter out blocked slots
        blocked = [b.time_slot for b in BlockedSlot.query.filter_by(doctor_id=doctor_id, date=date_str).all()]
        booked = [a.time for a in Appointment.query.filter_by(doctor_id=doctor_id, date=date_str, status='Scheduled').all()]
        
        day_slots = []
        for hour in range(9, 17): # 9 AM to 5 PM
            time_str = f"{hour:02d}:00"
            if time_str not in blocked and time_str not in booked:
                day_slots.append(time_str)
        
        slots.append({'date': date_str, 'times': day_slots})
        
    return render_template('doctor_profile.html', doctor=doctor, slots=slots)

# Booking
@app.route('/book', methods=['POST'])
@login_required
def book_appointment():
    if current_user.role != 'patient':
        return jsonify({'error': 'Only patients can book appointments'}), 403
        
    doctor_id = request.form.get('doctor_id')
    date = request.form.get('date')
    time = request.form.get('time')
    
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    
    # Fill additional info
    patient.age = request.form.get('age')
    patient.phone = request.form.get('phone')
    patient.blood_group = request.form.get('blood_group')
    patient.medical_conditions = request.form.get('conditions')
    patient.medications = request.form.get('medications')
    
    try:
        new_appointment = Appointment(
            booking_id=generate_booking_id(),
            doctor_id=doctor_id,
            patient_id=patient.id,
            date=date,
            time=time,
            status='Scheduled'
        )
        db.session.add(new_appointment)
        db.session.commit()
        return render_template('booking_confirmation.html', appt=new_appointment)
    except Exception as e:
        db.session.rollback()
        return "Selected slot unavailable. Please choose another available slot.", 400

@app.route('/patient/dashboard')
@login_required
def patient_dashboard():
    if current_user.role != 'patient':
        return redirect(url_for('index'))
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    
    # Get appointments with doctor info
    appointments = db.session.query(Appointment, Doctor).join(Doctor, Appointment.doctor_id == Doctor.id).filter(Appointment.patient_id == patient.id).all()
    
    # History includes consultations joins
    history = db.session.query(Appointment, Consultation, Doctor).join(Consultation, Appointment.id == Consultation.appointment_id).join(Doctor, Appointment.doctor_id == Doctor.id).filter(Appointment.patient_id == patient.id).all()

    # Last consultation (most recent)
    last_consultation = db.session.query(Consultation, Appointment, Doctor).join(Appointment, Consultation.appointment_id == Appointment.id).join(Doctor, Appointment.doctor_id == Doctor.id).filter(Appointment.patient_id == patient.id).order_by(Consultation.created_at.desc()).first()
    
    return render_template('patient_dashboard.html', appointments=appointments, history=history, last_consultation=last_consultation)

@app.route('/patient/billing')
@login_required
def patient_billing():
    if current_user.role != 'patient':
        return redirect(url_for('index'))
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    appointments = db.session.query(Appointment, Doctor).join(Doctor, Appointment.doctor_id == Doctor.id)\
        .filter(Appointment.patient_id == patient.id).all()
    return render_template('patient_billing.html', appointments=appointments)

@app.route('/patient/settings', methods=['GET', 'POST'])
@login_required
def patient_settings():
    if current_user.role != 'patient':
        return redirect(url_for('index'))
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        patient.name = request.form.get('name')
        patient.age = int(request.form.get('age')) if request.form.get('age') else None
        patient.phone = request.form.get('phone')
        patient.blood_group = request.form.get('blood_group')
        patient.medical_conditions = request.form.get('conditions')
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('patient_settings'))
        
    return render_template('patient_settings.html', patient=patient)

@app.route('/appointment/slip/<int:appointment_id>')
@login_required
def download_slip(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)
    doctor = Doctor.query.get(appt.doctor_id)
    patient = Patient.query.get(appt.patient_id)
    # Check if authorized
    if current_user.id != doctor.user_id and current_user.id != patient.user_id:
        return "Unauthorized", 403
    return render_template('appointment_slip.html', appt=appt, doctor=doctor, patient=patient)

@app.route('/doctor/dashboard')
@login_required
def doctor_dashboard():
    if current_user.role != 'doctor':
        return redirect(url_for('index'))
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    today = datetime.now().strftime('%Y-%m-%d')
    # today's appointments
    todays = db.session.query(Appointment, Patient).join(Patient, Appointment.patient_id == Patient.id).filter(Appointment.doctor_id == doctor.id, Appointment.date == today).order_by(Appointment.time).all()
    # upcoming appointments (after today)
    upcoming = db.session.query(Appointment, Patient).join(Patient, Appointment.patient_id == Patient.id).filter(Appointment.doctor_id == doctor.id, Appointment.date > today).order_by(Appointment.date, Appointment.time).all()

    # Calculate revenue for today
    total_revenue = len(todays) * doctor.fee

    return render_template('doctor_dashboard.html', 
                           today_appts=todays, 
                           upcoming_appts=upcoming,
                           revenue=total_revenue,
                           appt_count=len(todays),
                           doctor=doctor)

@app.route('/doctor/patients')
@login_required
def doctor_patients():
    if current_user.role != 'doctor':
        return redirect(url_for('index'))
    
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    search = request.args.get('search')
    
    # Get unique patients who have appointments with this doctor
    query = Patient.query.join(Appointment).filter(Appointment.doctor_id == doctor.id)
    
    if search:
        query = query.filter(Patient.name.ilike(f'%{search}%'))
    
    patients = query.distinct().all()
    return render_template('doctor_patients.html', patients=patients, search=search)

@app.route('/doctor/analytics')
@login_required
def doctor_analytics():
    if current_user.role != 'doctor':
        return redirect(url_for('index'))
    
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    today = datetime.now().strftime('%Y-%m-%d')
    
    total_patients = Patient.query.join(Appointment).filter(Appointment.doctor_id == doctor.id).distinct().count()
    today_appts = Appointment.query.filter_by(doctor_id=doctor.id, date=today).count()
    total_consults = Appointment.query.filter_by(doctor_id=doctor.id, status='Completed').count()
    # Build 7-day trend (labels and counts)
    from datetime import timedelta
    labels = []
    appt_counts = []
    base = datetime.now()
    for i in range(6, -1, -1):
        d = (base - timedelta(days=i)).strftime('%Y-%m-%d')
        labels.append((base - timedelta(days=i)).strftime('%a'))
        appt_counts.append(Appointment.query.filter_by(doctor_id=doctor.id, date=d).count())

    # Status distribution for pie chart
    scheduled = Appointment.query.filter_by(doctor_id=doctor.id, status='Scheduled').count()
    completed = Appointment.query.filter_by(doctor_id=doctor.id, status='Completed').count()
    cancelled = Appointment.query.filter_by(doctor_id=doctor.id, status='Cancelled').count()

    status_counts = {'Scheduled': scheduled, 'Completed': completed, 'Cancelled': cancelled}

    return render_template('doctor_analytics.html', 
                           total_patients=total_patients,
                           today_appts=today_appts,
                           total_consults=total_consults,
                           rating=doctor.rating,
                           trend_labels=labels,
                           trend_counts=appt_counts,
                           status_counts=status_counts)

@app.route('/doctor/settings', methods=['GET', 'POST'])
@login_required
def doctor_settings():
    if current_user.role != 'doctor':
        return redirect(url_for('index'))
    
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        doctor.name = request.form.get('name')
        doctor.specialization = request.form.get('specialization')
        doctor.fee = float(request.form.get('fee'))
        doctor.location = request.form.get('location')
        doctor.experience = int(request.form.get('experience'))
        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('doctor_settings'))
        
    return render_template('doctor_settings.html', doctor=doctor)

@app.route('/consultation/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def consultation(appointment_id):
    if current_user.role != 'doctor':
        return redirect(url_for('index'))
        
    appointment = Appointment.query.get_or_404(appointment_id)
    if request.method == 'POST':
        diagnosis = request.form.get('diagnosis')
        prescription = request.form.get('prescription')
        follow_up = request.form.get('follow_up')

        # insert using ORM if DB has doctor_id column, else use raw SQL
        try:
            cols = [c['name'] for c in inspect(db.engine).get_columns('consultation')]
        except Exception:
            cols = []

        try:
            if 'doctor_id' in cols:
                cons = Consultation(appointment_id=appointment_id, doctor_id=appointment.doctor_id, diagnosis=diagnosis, prescription=prescription, follow_up_date=follow_up)
                db.session.add(cons)
                appointment.status = 'Completed'
                db.session.commit()
            else:
                # raw insert without doctor_id
                now = datetime.utcnow()
                stmt = text("INSERT INTO consultation (appointment_id, diagnosis, prescription, follow_up_date, created_at) VALUES (:appointment_id, :diagnosis, :prescription, :follow_up_date, :created_at)")
                db.session.execute(stmt, {'appointment_id': appointment_id, 'diagnosis': diagnosis, 'prescription': prescription, 'follow_up_date': follow_up, 'created_at': now})
                appointment.status = 'Completed'
                db.session.commit()
                cons = db.session.query(Consultation).filter_by(appointment_id=appointment_id).order_by(Consultation.created_at.desc()).first()
        except Exception as e:
            db.session.rollback()
            flash('Could not save consultation: ' + str(e), 'error')
            return redirect(url_for('doctor_dashboard'))

        patient = Patient.query.get(appointment.patient_id)
        return render_template('consultation_saved.html', cons=cons, appt=appointment, patient=patient)
        
    return render_template('consultation.html', appt=appointment)


@app.route('/save-consultation', methods=['POST'])
@login_required
def save_consultation():
    if current_user.role != 'doctor':
        return redirect(url_for('index'))

    appointment_id = request.form.get('appointment_id') or request.form.get('appt_id')
    if not appointment_id:
        flash('Missing appointment id', 'error')
        return redirect(url_for('doctor_dashboard'))

    appointment = Appointment.query.get(int(appointment_id))
    if not appointment:
        flash('Appointment not found', 'error')
        return redirect(url_for('doctor_dashboard'))

    diagnosis = request.form.get('diagnosis')
    prescription = request.form.get('prescription')
    follow_up = request.form.get('follow_up')
    # robust save with fallback for DB without doctor_id column
    try:
        cols = [c['name'] for c in inspect(db.engine).get_columns('consultation')]
    except Exception:
        cols = []

    try:
        if 'doctor_id' in cols:
            cons = Consultation(appointment_id=appointment.id, doctor_id=appointment.doctor_id, diagnosis=diagnosis, prescription=prescription, follow_up_date=follow_up)
            db.session.add(cons)
            appointment.status = 'Completed'
            db.session.commit()
        else:
            now = datetime.utcnow()
            stmt = text("INSERT INTO consultation (appointment_id, diagnosis, prescription, follow_up_date, created_at) VALUES (:appointment_id, :diagnosis, :prescription, :follow_up_date, :created_at)")
            db.session.execute(stmt, {'appointment_id': appointment.id, 'diagnosis': diagnosis, 'prescription': prescription, 'follow_up_date': follow_up, 'created_at': now})
            appointment.status = 'Completed'
            db.session.commit()
            cons = db.session.query(Consultation).filter_by(appointment_id=appointment.id).order_by(Consultation.created_at.desc()).first()
    except Exception as e:
        db.session.rollback()
        flash('Could not save consultation: ' + str(e), 'error')
        return redirect(url_for('doctor_dashboard'))

    patient = Patient.query.get(appointment.patient_id)
    return render_template('consultation_saved.html', cons=cons, appt=appointment, patient=patient)


# Full schedule view
@app.route('/doctor/full-schedule')
@login_required
def doctor_full_schedule():
    if current_user.role != 'doctor':
        return redirect(url_for('index'))
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    appointments = db.session.query(Appointment, Patient).join(Patient, Appointment.patient_id == Patient.id).filter(Appointment.doctor_id == doctor.id).order_by(Appointment.date, Appointment.time).all()
    return render_template('doctor_full_schedule.html', appointments=appointments)


@app.route('/doctor/patient/<int:patient_id>')
@login_required
def doctor_view_patient(patient_id):
    if current_user.role != 'doctor':
        return redirect(url_for('index'))
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    patient = Patient.query.get_or_404(patient_id)
    # ensure doctor has at least one appointment with this patient
    assoc = Appointment.query.filter_by(doctor_id=doctor.id, patient_id=patient.id).first()
    if not assoc:
        flash('You do not have permissions to view this patient dashboard', 'error')
        return redirect(url_for('doctor_dashboard'))

    appointments = db.session.query(Appointment, Doctor).join(Doctor, Appointment.doctor_id == Doctor.id).filter(Appointment.patient_id == patient.id, Appointment.doctor_id==doctor.id).all()
    history = db.session.query(Appointment, Consultation, Doctor).join(Consultation, Appointment.id == Consultation.appointment_id).join(Doctor, Appointment.doctor_id == Doctor.id).filter(Appointment.patient_id == patient.id, Appointment.doctor_id==doctor.id).all()
    last_consultation = db.session.query(Consultation, Appointment, Doctor).join(Appointment, Consultation.appointment_id == Appointment.id).join(Doctor, Appointment.doctor_id == Doctor.id).filter(Appointment.patient_id == patient.id, Appointment.doctor_id==doctor.id).order_by(Consultation.created_at.desc()).first()

    return render_template('patient_dashboard.html', appointments=appointments, history=history, last_consultation=last_consultation, patient=patient)


# New schedule (quick add appointment)
@app.route('/doctor/new-schedule', methods=['GET', 'POST'])
@login_required
def doctor_new_schedule():
    if current_user.role != 'doctor':
        return redirect(url_for('index'))
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    patients = Patient.query.all()
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        date = request.form.get('date')
        time = request.form.get('time')
        try:
            new_appt = Appointment(booking_id=generate_booking_id(), doctor_id=doctor.id, patient_id=patient_id, date=date, time=time, status='Scheduled')
            db.session.add(new_appt)
            db.session.commit()
            flash('Appointment added', 'success')
            return redirect(url_for('doctor_full_schedule'))
        except Exception as e:
            db.session.rollback()
            flash('Could not add appointment: ' + str(e), 'error')
    return render_template('doctor_new_schedule.html', patients=patients)


# Export data as CSV
@app.route('/doctor/export-data')
@login_required
def doctor_export_data():
    if current_user.role != 'doctor':
        return redirect(url_for('index'))
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    # Export appointments and consultations
    import csv
    from io import StringIO
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['appt_id','booking_id','date','time','patient_id','patient_name','status','diagnosis','prescription','consultation_created'])
    appts = Appointment.query.filter_by(doctor_id=doctor.id).all()
    for a in appts:
        patient = Patient.query.get(a.patient_id)
        cons = Consultation.query.filter_by(appointment_id=a.id).first()
        cw.writerow([a.id, a.booking_id, a.date, a.time, a.patient_id, patient.name if patient else '', a.status, cons.diagnosis if cons else '', cons.prescription if cons else '', cons.created_at if cons else ''])
    output = si.getvalue()
    return (output, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename="export_doctor_%s.csv"' % doctor.id
    })

@app.route('/doctor/slots', methods=['POST'])
@login_required
def manage_slots():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    date = request.form.get('date')
    time = request.form.get('time')
    action = request.form.get('action') # block or unblock
    
    if action == 'block':
        blocked = BlockedSlot(doctor_id=doctor.id, date=date, time_slot=time)
        db.session.add(blocked)
    else:
        BlockedSlot.query.filter_by(doctor_id=doctor.id, date=date, time_slot=time).delete()
        
    db.session.commit()
    return redirect(url_for('doctor_dashboard'))

# Seed Data
def seed_data():
    if not User.query.first():
        # Create a doctor
        dr_user = User(username='doctor1', password=generate_password_hash('pass123'), role='doctor')
        db.session.add(dr_user)
        db.session.flush()
        doctor = Doctor(user_id=dr_user.id, name='Dr. Sarah Smith', specialization='Cardiologist', fee=1200, location='Central Clinic', experience=12)
        db.session.add(doctor)
        
        # Create more doctors
        dr_user2 = User(username='doctor2', password=generate_password_hash('pass123'), role='doctor')
        db.session.add(dr_user2)
        db.session.flush()
        doctor2 = Doctor(user_id=dr_user2.id, name='Dr. John Doe', specialization='Pediatrician', fee=800, location='Kids Health Center', experience=8)
        db.session.add(doctor2)
        
        # Create a patient
        pt_user = User(username='patient1', password=generate_password_hash('pass123'), role='patient')
        db.session.add(pt_user)
        db.session.flush()
        patient = Patient(user_id=pt_user.id, name='Mike Wason', age=29, phone='9876543210')
        db.session.add(patient)
        
        db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_data()
    app.run(debug=True, port=5000)
