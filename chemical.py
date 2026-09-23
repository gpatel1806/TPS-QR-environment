from flask import Blueprint, request, jsonify, render_template, send_file, url_for, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from db import db
from datetime import datetime
import os
import smtplib
import threading
from email.message import EmailMessage
import qrcode
import io

chemical_bp = Blueprint('chemical', __name__)
#---db = SQLAlchemy()

# --- DATABASE MODELS ---
class Chemical(db.Model):
    __tablename__ = 'chemicals'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    min_stock = db.Column(db.Float, default=0.0)
    frequency = db.Column(db.String(20), default="daily")
    last_stock = db.Column(db.Float, default=0.0)

class StockLog(db.Model):
    __tablename__ = 'stock_logs'
    id = db.Column(db.Integer, primary_key=True)
    chemical_id = db.Column(db.Integer, db.ForeignKey('chemicals.id'))
    date_logged = db.Column(db.DateTime, default=datetime.utcnow)
    previous_stock = db.Column(db.Float)
    current_stock = db.Column(db.Float)
    consumption = db.Column(db.Float)

class AlertSettings(db.Model):
    __tablename__ = 'alert_settings'
    id = db.Column(db.Integer, primary_key=True)
    email_recipients = db.Column(db.String(255))

# --- CUSTOM MASTER AUTHENTICATION DECORATOR ---
def chemical_master_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('chemical_master_logged_in'):
            # Directly render the login page instead of redirecting to prevent 500 errors
            return render_template('chemical_login.html', login_prompt="Please log in to access the Master Portal.")
        return f(*args, **kwargs)
    return decorated_function

# --- MASTER LOGIN / LOGOUT ROUTES ---
@chemical_bp.route('/login', methods=['GET', 'POST'])
def chemical_login():
    error_msg = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Set your desired Master ID and Password here
        if username == 'chem_master' and password == 'admin123':
            session['chemical_master_logged_in'] = True
            return redirect(url_for('chemical.chemical_dashboard'))
        else:
            error_msg = "Invalid Master Credentials."
            
    return render_template('chemical_login.html', error_msg=error_msg)
@chemical_bp.route('/logout', methods=['GET'])
def chemical_logout():
    session.pop('chemical_master_logged_in', None)
    return redirect(url_for('chemical.render_operator_house'))


# --- ASYNC BACKGROUND WORKER ---
def send_email_async(msg, sender_email, sender_password):
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            print(f"Background email successfully sent to {msg['To']}")
    except Exception as e:
        print(f"Failed to send background email: {e}")

# --- ALERT LOGIC ---
def trigger_low_stock_alert(chem_name, current_stock, min_stock):
    settings = AlertSettings.query.first()
    if not settings or not settings.email_recipients:
        return 
        
    recipients = settings.email_recipients.split(',')
    msg = EmailMessage()
    msg.set_content(f"ALERT: Stock for {chem_name} has dropped below the minimum allowable limit.\n\n"
                    f"Current Stock: {current_stock}\n"
                    f"Minimum Allowable: {min_stock}\n"
                    f"Please arrange for replenishment.")
                    
    msg['Subject'] = f"Low Stock Alert: {chem_name}"
    
    sender_email = os.getenv('ALERT_EMAIL')
    sender_password = os.getenv('ALERT_EMAIL_PASSWORD')
    
    msg['From'] = sender_email
    msg['To'] = ", ".join(recipients)
    
    # Send the email in a background thread so the web page doesn't freeze
    thread = threading.Thread(target=send_email_async, args=(msg, sender_email, sender_password))
    thread.start()

# --- SECURED MASTER ROUTES (Requires separate login) ---

@chemical_bp.route('/dashboard', methods=['GET'])
@chemical_master_required
def chemical_dashboard():
    chemicals = Chemical.query.all()
    return render_template('chemical_dashboard.html', chemicals=chemicals)

@chemical_bp.route('/setup', methods=['GET'])
@chemical_master_required
def render_master_setup():
    return render_template('master_chemical.html')

@chemical_bp.route('/api/master/setup_chemical', methods=['POST'])
@chemical_master_required
def setup_chemical():
    data = request.json
    chemical = Chemical.query.filter_by(name=data['name']).first()
    
    if not chemical:
        chemical = Chemical(name=data['name'])
        db.session.add(chemical)
        
    chemical.min_stock = data.get('min_stock', chemical.min_stock)
    chemical.frequency = data.get('frequency', chemical.frequency)
    
    if 'emails' in data:
        settings = AlertSettings.query.first()
        if not settings:
            settings = AlertSettings(email_recipients=data['emails'])
            db.session.add(settings)
        else:
            settings.email_recipients = data['emails']
            
    db.session.commit()
    return jsonify({"message": f"{chemical.name} configured successfully."}), 200

@chemical_bp.route('/delete/<int:chemical_id>', methods=['POST'])
@chemical_master_required
def delete_chemical(chemical_id):
    chemical = Chemical.query.get_or_404(chemical_id)
    StockLog.query.filter_by(chemical_id=chemical.id).delete()
    db.session.delete(chemical)
    db.session.commit()
    flash(f"Chemical {chemical.name} and its history have been deleted.", "success")
    return redirect(url_for('chemical.chemical_dashboard'))

@chemical_bp.route('/rename/<int:chemical_id>', methods=['POST'])
@chemical_master_required
def rename_chemical(chemical_id):
    chemical = Chemical.query.get_or_404(chemical_id)
    new_name = request.form.get('new_name')
    if new_name and new_name.strip():
        chemical.name = new_name.strip()
        db.session.commit()
    return redirect(url_for('chemical.chemical_dashboard'))

@chemical_bp.route('/report/<int:chemical_id>', methods=['GET'])
@chemical_master_required
def chemical_report(chemical_id):
    chemical = Chemical.query.get_or_404(chemical_id)
    logs = StockLog.query.filter_by(chemical_id=chemical.id).order_by(StockLog.date_logged.desc()).all()
    return render_template('chemical_report.html', chemical=chemical, logs=logs)

@chemical_bp.route('/house/qr/print', methods=['GET'])
@chemical_master_required
def print_house_qr():
    return render_template('print_house_qr.html')

# --- UNSECURED OPERATOR ROUTES (No Login Required) ---

@chemical_bp.route('/operator/<int:chemical_id>', methods=['GET'])
def render_operator_entry(chemical_id):
    return render_template('operator_chemical.html', chemical_id=chemical_id)

@chemical_bp.route('/operator/house', methods=['GET'])
def render_operator_house():
    chemicals = Chemical.query.order_by(Chemical.name).all()
    return render_template('operator_house.html', chemicals=chemicals)

@chemical_bp.route('/api/operator/scan/<int:chemical_id>', methods=['GET'])
def scan_chemical_qr(chemical_id):
    chemical = Chemical.query.get(chemical_id)
    if not chemical:
        return jsonify({"error": "Chemical not found"}), 404
    recent_logs = StockLog.query.filter_by(chemical_id=chemical.id).order_by(StockLog.date_logged.desc()).limit(5).all()
    consumption_pattern = [{"date": log.date_logged.strftime("%Y-%m-%d"), "consumption": log.consumption} for log in recent_logs]
    return jsonify({"chemical_id": chemical.id, "chemical_name": chemical.name, "previous_stock": chemical.last_stock, "recent_consumption_pattern": consumption_pattern}), 200

@chemical_bp.route('/api/operator/log_stock', methods=['POST'])
def log_stock():
    data = request.json
    chemical = Chemical.query.filter_by(name=data['name']).first()
    if not chemical: return jsonify({"error": "Chemical not found"}), 404
    
    current_stock = float(data['current_stock'])
    previous_stock = chemical.last_stock
    consumption = previous_stock - current_stock if previous_stock > 0 else 0
    
    # Update Stock
    new_log = StockLog(chemical_id=chemical.id, previous_stock=previous_stock, current_stock=current_stock, consumption=consumption)
    db.session.add(new_log)
    chemical.last_stock = current_stock
    
    # Log Activity to Dashboard
    from app import ActivityLog, SystemAlert
    activity = ActivityLog(module="Chemical Stock", action=f"Stock updated for {chemical.name} ({current_stock} units)")
    db.session.add(activity)

    # Handle Alerts
    alert_triggered = False
    if current_stock < chemical.min_stock:
        alert_triggered = True
        trigger_low_stock_alert(chemical.name, current_stock, chemical.min_stock)
        
        sys_alert = SystemAlert(module="Chemical Stock", severity="WARNING", message=f"Low Stock: {chemical.name} dropped to {current_stock}")
        db.session.add(sys_alert)

    db.session.commit()
    return jsonify({"chemical": chemical.name, "consumption": consumption, "alert_triggered": alert_triggered}), 200

@chemical_bp.route('/api/operator/log_stock_bulk', methods=['POST'])
def log_stock_bulk():
    data = request.json
    alerts_triggered = []
    from app import ActivityLog, SystemAlert
    
    for item in data.get('entries', []):
        if item['current_stock'] == "": continue
        chemical = Chemical.query.filter_by(name=item['name']).first()
        if chemical:
            current_stock = float(item['current_stock'])
            previous_stock = chemical.last_stock
            consumption = previous_stock - current_stock if previous_stock > 0 else 0
            
            new_log = StockLog(chemical_id=chemical.id, previous_stock=previous_stock, current_stock=current_stock, consumption=consumption)
            db.session.add(new_log)
            
            activity = ActivityLog(module="Chemical Stock", action=f"Bulk stock updated for {chemical.name}")
            db.session.add(activity)
            
            chemical.last_stock = current_stock
            if current_stock < chemical.min_stock:
                alerts_triggered.append(chemical.name)
                trigger_low_stock_alert(chemical.name, current_stock, chemical.min_stock)
                
                sys_alert = SystemAlert(module="Chemical Stock", severity="WARNING", message=f"Low Stock: {chemical.name} dropped to {current_stock}")
                db.session.add(sys_alert)
                
    db.session.commit()
    return jsonify({"message": "Stock logged successfully.", "alerts": alerts_triggered}), 200

@chemical_bp.route('/house/qr/image', methods=['GET'])
def house_qr_image():
    target_url = url_for("chemical.render_operator_house", _external=True)
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=2)
    qr.add_data(target_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png")