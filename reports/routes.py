from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from db import db
from .models import ElectricalReport, ElectricalDistribution
from datetime import datetime, timedelta

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')
@login_required
def index():
    return render_template('reports/index.html')

@reports_bp.route('/electrical')
@login_required
def electrical_dashboard():
    # FEATURE 2: Check if a specific date was requested
    selected_date_str = request.args.get('date')
    
    if selected_date_str:
        try:
            target_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            latest_report = ElectricalReport.query.filter_by(reporting_date=target_date).first()
            if not latest_report:
                flash(f"No data found for {target_date.strftime('%d-%b-%Y')}. Showing latest instead.", "warning")
                latest_report = ElectricalReport.query.order_by(ElectricalReport.reporting_date.desc()).first()
        except ValueError:
            latest_report = ElectricalReport.query.order_by(ElectricalReport.reporting_date.desc()).first()
    else:
        latest_report = ElectricalReport.query.order_by(ElectricalReport.reporting_date.desc()).first()
    
    previous_report = None
    distributions = []
    prev_dist_map = {}
    
    if latest_report:
        distributions = ElectricalDistribution.query.filter_by(report_id=latest_report.id).order_by(ElectricalDistribution.consumption_mwh.desc()).all()
        
        previous_report = ElectricalReport.query.filter(
            ElectricalReport.reporting_date < latest_report.reporting_date
        ).order_by(ElectricalReport.reporting_date.desc()).first()
        
        if previous_report:
            prev_dists = ElectricalDistribution.query.filter_by(report_id=previous_report.id).all()
            prev_dist_map = {d.load_name: d.consumption_mwh for d in prev_dists}
            
    return render_template(
        'reports/electrical.html', 
        report=latest_report, 
        previous=previous_report, 
        distributions=distributions,
        prev_dist_map=prev_dist_map
    )

# FEATURE 3: API to fetch historical data for the Detailed Table modal
@reports_bp.route('/api/historical-load')
@login_required
def api_historical_load():
    load_name = request.args.get('name')
    days = int(request.args.get('days', 30))
    cutoff_date = datetime.utcnow().date() - timedelta(days=days)
    
    # Query database for this specific load over the requested timeframe
    results = db.session.query(
        ElectricalReport.reporting_date, ElectricalDistribution.consumption_mwh
    ).join(
        ElectricalDistribution, ElectricalReport.id == ElectricalDistribution.report_id
    ).filter(
        ElectricalDistribution.load_name == load_name,
        ElectricalReport.reporting_date >= cutoff_date
    ).order_by(ElectricalReport.reporting_date.asc()).all()
    
    return jsonify({
        'dates': [r.reporting_date.strftime('%d-%b') for r in results], 
        'values': [r.consumption_mwh for r in results], 
        'load_name': load_name
    })

# FEATURE 4: Custom Trend Analysis Tool Page
@reports_bp.route('/trends')
@login_required
def custom_trends():
    # Fetch all unique load names dynamically for the checkboxes
    unique_loads = db.session.query(ElectricalDistribution.load_name).distinct().all()
    load_names = [l[0] for l in unique_loads]
    return render_template('reports/trends.html', load_names=load_names)

# FEATURE 4: API to process the Custom Trend graph data
@reports_bp.route('/api/custom-trends', methods=['POST'])
@login_required
def api_custom_trends():
    data = request.json
    metrics = data.get('metrics', [])
    days = int(data.get('days', 30))
    cutoff_date = datetime.utcnow().date() - timedelta(days=days)
    
    reports = ElectricalReport.query.filter(
        ElectricalReport.reporting_date >= cutoff_date
    ).order_by(ElectricalReport.reporting_date.asc()).all()
    
    dates = [r.reporting_date.strftime('%d-%b') for r in reports]
    datasets, stats = [], []
    
    # Pre-define some colors for up to 5 lines
    colors = ['#0d6efd', '#dc3545', '#198754', '#ffc107', '#6f42c1']
    
    for idx, metric in enumerate(metrics):
        values = []
        if metric.startswith('dist_'):
            load_name = metric.replace('dist_', '')
            for r in reports:
                dist = next((d for d in r.distributions if d.load_name == load_name), None)
                values.append(dist.consumption_mwh if dist else 0)
        else:
            for r in reports:
                values.append(getattr(r, metric, 0))
                
        avg_val = sum(values) / len(values) if values else 0
        peak_val = max(values) if values else 0
        display_name = metric.replace('dist_', 'Load: ').replace('_', ' ').title()
        
        datasets.append({
            'label': display_name,
            'data': values,
            'borderColor': colors[idx % len(colors)],
            'backgroundColor': 'transparent',
            'borderWidth': 2,
            'tension': 0.3
        })
        stats.append({'metric': display_name, 'avg': round(avg_val, 2), 'peak': round(peak_val, 2)})
        
    return jsonify({'dates': dates, 'datasets': datasets, 'stats': stats})

@reports_bp.route('/electrical/entry', methods=['GET', 'POST'])
@login_required
def enter_data():
    if request.method == 'POST':
        try:
            date_str = request.form.get('reporting_date')
            rep_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            existing = ElectricalReport.query.filter_by(reporting_date=rep_date).first()
            if existing:
                flash(f"A report for {date_str} already exists.", "warning")
                return redirect(url_for('reports.enter_data'))

            report = ElectricalReport(
                reporting_date=rep_date,
                stg_1=float(request.form.get('stg_1') or 0),
                stg_2=float(request.form.get('stg_2') or 0),
                stg_3=float(request.form.get('stg_3') or 0),
                gt_1=float(request.form.get('gt_1') or 0),
                gt_2=float(request.form.get('gt_2') or 0),
                gt_3=float(request.form.get('gt_3') or 0),
                grid_import=float(request.form.get('grid_import') or 0),
                total_system_peak=float(request.form.get('total_system_peak') or 0),
                losses_mwh=float(request.form.get('losses_mwh') or 0),
                losses_percent=float(request.form.get('losses_percent') or 0)
            )
            report.total_generation = report.stg_1 + report.stg_2 + report.stg_3 + report.gt_1 + report.gt_2 + report.gt_3
            report.total_supply = report.total_generation + report.grid_import
            db.session.add(report)
            db.session.flush() 
            
            dist_names = request.form.getlist('dist_name[]')
            dist_vals = request.form.getlist('dist_val[]')
            for name, val in zip(dist_names, dist_vals):
                if name.strip() and val.strip():
                    dist = ElectricalDistribution(report_id=report.id, load_name=name.strip(), consumption_mwh=float(val))
                    db.session.add(dist)
                    
            db.session.commit()
            flash("Electrical Report saved!", "success")
            return redirect(url_for('reports.electrical_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f"System Error: {str(e)}", "danger")
            
    return render_template('reports/entry.html')