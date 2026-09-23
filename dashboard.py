from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from db import db

# Initialize the Blueprint
dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    # Local imports to prevent circular dependency errors with app.py and chemical.py
    from app import Equipment
    from chemical import Chemical
    from app import SystemAlert, ActivityLog

    # Query PostgreSQL for high-level plant health statistics
    total_equipment = Equipment.query.count()
    healthy_equipment = Equipment.query.filter_by(status='In Service').count()
    maintenance_equipment = Equipment.query.filter_by(status='Under Maintenance').count()
    critical_equipment = Equipment.query.filter_by(status='Breakdown').count()

    total_chemicals = Chemical.query.count()
    low_stock_chemicals = Chemical.query.filter(Chemical.last_stock < Chemical.min_stock).count()
    
    # Fetch the 5 most recent active alerts
    active_alerts = SystemAlert.query.filter_by(resolved=False).order_by(SystemAlert.created_at.desc()).limit(5).all()
    
    # Fetch the 5 most recent activity logs
    recent_activities = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(5).all()

    return render_template(
        'dashboard.html',
        total_equipment=total_equipment,
        healthy_equipment=healthy_equipment,
        maintenance_equipment=maintenance_equipment,
        critical_equipment=critical_equipment,
        total_chemicals=total_chemicals,
        low_stock_chemicals=low_stock_chemicals,
        active_alerts=active_alerts,
        recent_activities=recent_activities
    )

@dashboard_bp.route('/search')
def global_search():
    from app import Equipment
    
    # Grab the user's search query from the URL (e.g., ?q=EQ-00001)
    query = request.args.get('q', '').strip()
    
    if not query:
        return redirect(url_for('dashboard.index'))
    
    # SMART ROUTING: Check if the user typed an exact Equipment ID (case-insensitive)
    exact_match = Equipment.query.filter(Equipment.id.ilike(query)).first()
    
    if exact_match:
        # If it's an exact ID match, jump directly to the asset's telemetry page
        return redirect(url_for('get_equipment', equipment_id=exact_match.id))
    
    # If it's a general keyword (e.g., "Pump" or "Substation A"), send them to the directory filter
    return redirect(url_for('equipment_directory', q=query))

@dashboard_bp.route('/alert/<int:alert_id>/resolve', methods=['POST'])
@login_required
def resolve_alert(alert_id):
    from app import SystemAlert
    
    # Fetch the specific alert
    alert = db.session.get(SystemAlert, alert_id)
    if alert:
        # Mark it as resolved and save to PostgreSQL
        alert.resolved = True
        db.session.commit()
        flash("Plant alert acknowledged and resolved.", "success")
        
    return redirect(url_for('dashboard.index'))