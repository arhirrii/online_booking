from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'schimba_asta_cu_ceva_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///booking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# user/parola admin (de test – le poți schimba)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "parola123"

db = SQLAlchemy(app)

# -----------------------------
# DECORATOR login_required
# -----------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Trebuie să te loghezi ca să vezi această pagină.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# -----------------------------
# MODEL: Programare
# -----------------------------
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(100), nullable=False)
    client_phone = db.Column(db.String(30), nullable=False)
    service = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Appointment {self.client_name} {self.date} {self.time}>"

# Creăm DB dacă nu există
with app.app_context():
    if not os.path.exists('booking.db'):
        db.create_all()

# -----------------------------
# LOGIN / LOGOUT
# -----------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            flash("Te-ai logat cu succes.", "success")
            return redirect(url_for("admin"))
        else:
            flash("User sau parolă greșite.", "danger")
            return redirect(url_for("login"))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash("Te-ai delogat.", "info")
    return redirect(url_for('login'))

# -----------------------------
# RUTA: Pagina de rezervări (PUBLICĂ)
# -----------------------------
@app.route('/book', methods=['GET', 'POST'])
def book():
    if request.method == 'POST':
        client_name = request.form.get('client_name')
        client_phone = request.form.get('client_phone')
        service = request.form.get('service')
        date_str = request.form.get('date')
        time_str = request.form.get('time')

        # verificare câmpuri
        if not all([client_name, client_phone, service, date_str, time_str]):
            flash('Te rog completează toate câmpurile.', 'danger')
            return redirect(url_for('book'))

        # conversii date/time
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            time_obj = datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            flash('Dată sau oră invalidă.', 'danger')
            return redirect(url_for('book'))

        # prevenim dublarea slotului
        existing = Appointment.query.filter_by(date=date_obj, time=time_obj).first()
        if existing:
            flash('Acest interval orar este deja rezervat. Alege altă oră.', 'warning')
            return redirect(url_for('book'))

        # salvăm programarea
        appt = Appointment(
            client_name=client_name,
            client_phone=client_phone,
            service=service,
            date=date_obj,
            time=time_obj
        )
        db.session.add(appt)
        db.session.commit()

        flash('Programarea a fost creată cu succes!', 'success')
        return redirect(url_for('book'))

    # Pentru GET — afișăm lista de servicii și formularul
    services = ['Tuns', 'Coafat', 'Manichiură', 'Consultanță']
    return render_template('booking.html', services=services)

# -----------------------------
# DASHBOARD ADMIN (PROTEJAT)
# -----------------------------
@app.route('/admin')
@login_required
def admin():
    appointments = Appointment.query.order_by(Appointment.date, Appointment.time).all()
    return render_template('admin.html', appointments=appointments)

# -----------------------------
# ȘTERGERE PROGRAMARE (PROTEJAT)
# -----------------------------
@app.route('/delete/<int:id>')
@login_required
def delete(id):
    appt = Appointment.query.get_or_404(id)
    db.session.delete(appt)
    db.session.commit()
    flash('Programarea a fost ștearsă.', 'success')
    return redirect(url_for('admin'))

# -----------------------------
# EDITARE PROGRAMARE (PROTEJAT)
# -----------------------------
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    appt = Appointment.query.get_or_404(id)

    if request.method == 'POST':
        appt.client_name = request.form.get('client_name')
        appt.client_phone = request.form.get('client_phone')
        appt.service = request.form.get('service')

        try:
            appt.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
            appt.time = datetime.strptime(request.form.get('time'), '%H:%M').time()
        except ValueError:
            flash("Dată sau oră invalidă!", "danger")
            return redirect(url_for('edit', id=id))

        db.session.commit()
        flash("Programarea a fost actualizată!", "success")
        return redirect(url_for('admin'))

    return render_template('edit.html', appt=appt)

@app.route('/')
def home():
    return render_template('home.html')

# -----------------------------
# PORNIRE APLICAȚIE
# -----------------------------
if __name__ == '__main__':
    app.run(debug=True)
