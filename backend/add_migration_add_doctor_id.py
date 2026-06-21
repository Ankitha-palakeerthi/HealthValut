from sqlalchemy import inspect, text
from app import app
from models import db, Appointment

def migrate():
    with app.app_context():
        engine = db.engine
        inspector = inspect(engine)
        cols = [c['name'] for c in inspector.get_columns('consultation')]
        if 'doctor_id' in cols:
            print('doctor_id already present on consultation table; nothing to do')
            return

        print('Adding doctor_id column to consultation...')
        # SQLite supports ADD COLUMN
        conn = engine.connect()
        conn.execute(text('ALTER TABLE consultation ADD COLUMN doctor_id INTEGER'))
        print('Column added. Backfilling doctor_id from appointment data...')

        rows = conn.execute(text('SELECT id, appointment_id FROM consultation')).fetchall()
        updated = 0
        for r in rows:
            cid = r[0]
            appt_id = r[1]
            if appt_id is None:
                continue
            appt = Appointment.query.get(appt_id)
            if appt and appt.doctor_id:
                conn.execute(text('UPDATE consultation SET doctor_id = :d WHERE id = :cid'), {'d': appt.doctor_id, 'cid': cid})
                updated += 1

        conn.close()
        print(f'Backfill complete. Updated {updated} rows.')

if __name__ == '__main__':
    migrate()
