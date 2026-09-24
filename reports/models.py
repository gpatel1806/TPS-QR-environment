from db import db
from datetime import datetime

class ElectricalReport(db.Model):
    __tablename__ = "electrical_reports"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    reporting_date = db.Column(db.Date, unique=True, nullable=False, index=True)
    
    # Generation (MWh)
    stg_1 = db.Column(db.Float, default=0.0)
    stg_2 = db.Column(db.Float, default=0.0)
    stg_3 = db.Column(db.Float, default=0.0)
    gt_1 = db.Column(db.Float, default=0.0)
    gt_2 = db.Column(db.Float, default=0.0)
    gt_3 = db.Column(db.Float, default=0.0)
    grid_import = db.Column(db.Float, default=0.0)
    cumulative_grid_import = db.Column(db.Float, default=0.0)
    
    # Peak Loads (MW)
    peak_stg_1 = db.Column(db.Float, default=0.0)
    peak_stg_2 = db.Column(db.Float, default=0.0)
    peak_stg_3 = db.Column(db.Float, default=0.0)
    peak_gt_1 = db.Column(db.Float, default=0.0)
    peak_gt_2 = db.Column(db.Float, default=0.0)
    peak_gt_3 = db.Column(db.Float, default=0.0)
    peak_grid = db.Column(db.Float, default=0.0)
    total_system_peak = db.Column(db.Float, default=0.0)
    
    # Township Specific
    township_peak = db.Column(db.Float, default=0.0)
    township_peak_time = db.Column(db.String(10), nullable=True)
    
    # Calculated Totals
    total_generation = db.Column(db.Float, default=0.0)
    total_supply = db.Column(db.Float, default=0.0)
    losses_mwh = db.Column(db.Float, default=0.0)
    losses_percent = db.Column(db.Float, default=0.0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to distributions
    distributions = db.relationship('ElectricalDistribution', backref='report', cascade='all, delete-orphan', lazy=True)


class ElectricalDistribution(db.Model):
    __tablename__ = "electrical_distributions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    report_id = db.Column(db.Integer, db.ForeignKey("electrical_reports.id"), nullable=False, index=True)
    load_name = db.Column(db.String(100), nullable=False)
    consumption_mwh = db.Column(db.Float, default=0.0)