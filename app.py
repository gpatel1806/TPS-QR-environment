from datetime import datetime
from functools import wraps
import io
import os
import zipfile

from dotenv import load_dotenv
import pandas as pd  # <--- ADD THIS
import qrcode
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

# Load environment variables from .env
load_dotenv()
app = Flask(__name__)

# Dynamic Production / Staging Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY", "industrial-plant-secret-key-change-in-prod-9982"
)
database_url = os.getenv("DATABASE_URL", "sqlite:///" + os.path.join(basedir, "equipment.db"))
# Fix SQLAlchemy dialect URI for PostgreSQL
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
with app.app_context():
    db.create_all()
# Authentication Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please authenticate with Engineering credentials to perform this action."
login_manager.login_message_category = "warning"

# Define the Equipment Model (Parent Table)
# Define the Equipment Model (Parent Table)
class Equipment(db.Model):
    __tablename__ = 'equipments'

    id = db.Column(db.String(50), primary_key=True)
    tag = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(150), nullable=False)
    area = db.Column(db.String(100), nullable=False)
    equipment_type = db.Column(db.String(50), nullable=False) 
    category = db.Column(db.String(50), nullable=True)        
    substation = db.Column(db.String(100), nullable=True)     
    feeder = db.Column(db.String(100), nullable=True)         
    rating = db.Column(db.String(50), nullable=True)          
    status = db.Column(db.String(50), default='In Service')
    specs = db.Column(db.Text, nullable=True)                 

    # Relationships
    logs = db.relationship('MaintenanceLog', backref='equipment', cascade='all, delete-orphan', lazy=True)
    
    def get_ppe_list(self):
        """Safe helper to convert optional PPE field or fallback to empty list."""
        ppe = getattr(self, 'ppe_required', None)
        if not ppe:
            return []
        return [item.strip() for item in ppe.split(",") if item.strip()]

# Define the MaintenanceLog Model (Child Table)
class MaintenanceLog(db.Model):
    __tablename__ = "maintenance_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    equipment_id = db.Column(db.String(20), db.ForeignKey("equipments.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    log_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    technician = db.Column(db.String(100), nullable=False)
    status_after = db.Column(db.String(30), nullable=False)

# Define User Model for Role-Based Plant Operations
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="Engineer")
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f"Access granted. Welcome, {user.full_name}.", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("home"))
        else:
            flash("Invalid credentials. Access rejected by substation security.", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Session terminated safely.", "info")
    return redirect(url_for("home"))

@app.route("/")
def home():
    search_query = request.args.get("q", "").strip().lower()
    status_filter = request.args.get("status", "").strip()

    # Query all assets from the persistent database table
    query = Equipment.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    if search_query:
        query = query.filter(
            (Equipment.id.ilike(f"%{search_query}%"))
            | (Equipment.name.ilike(f"%{search_query}%"))
            | (Equipment.tag.ilike(f"%{search_query}%"))
            | (Equipment.area.ilike(f"%{search_query}%"))
        )

    equipments = query.all()

    print(f"[SQL TELEMETRY] Loaded {len(equipments)} assets from SQLite.")
    
    return render_template(
        "index.html",
        equipments=equipments,
        search_query=search_query,
        status_filter=status_filter,
    )


@app.route("/health")
def health_status():
    return "Status: OK | Database: SQLite Connected"


def derive_category(eq_type):
    """Categorizes assets into the 4 plant dashboard groups."""
    eq_type = str(eq_type).lower().strip()
    if any(k in eq_type for k in ['breaker', 'ht breaker', 'lt module', 'transformer', 'battery', 'ups']):
        return 'Electrical'
    elif any(k in eq_type for k in ['pump', 'fan']):
        return 'Mechanical'
    elif any(k in eq_type for k in ['vessel', 'tank']):
        return 'Process'
    elif 'generator' in eq_type:
        return 'Generation'
    return 'Other'


@app.route('/equipment/import-excel', methods=['GET', 'POST'])
@login_required
def import_excel():
    if request.method == 'POST':
        if 'excel_file' not in request.files:
            flash('No file selected.', 'danger')
            return redirect(request.url)
            
        file = request.files['excel_file']
        if not file.filename.endswith(('.xlsx', '.xls')):
            flash('Please upload a valid Excel spreadsheet (.xlsx or .xls).', 'danger')
            return redirect(request.url)

        try:
            df = pd.read_excel(file)
            df.columns = [str(c).strip().lower() for c in df.columns]

            required_cols = {'equipment id', 'tag no', 'equipment type', 'name', 'area'}
            if not required_cols.issubset(set(df.columns)):
                flash(f"Missing required columns! File must include: {', '.join(required_cols)}", 'danger')
                return redirect(request.url)

            success_count = 0
            updated_count = 0

            for _, row in df.iterrows():
                asset_id = str(row['equipment id']).strip()
                if not asset_id or asset_id.lower() == 'nan':
                    continue

                eq_type = str(row.get('equipment type', '')).strip().lower()

                eq = Equipment.query.get(asset_id)
                if not eq:
                    eq = Equipment(id=asset_id)
                    db.session.add(eq)
                    success_count += 1
                else:
                    updated_count += 1

                eq.tag = str(row.get('tag no', '')).strip()
                eq.name = str(row.get('name', '')).strip()
                eq.area = str(row.get('area', '')).strip()
                eq.equipment_type = eq_type
                eq.category = derive_category(eq_type)

                # Substation & Feeder mapping
                if any(k in eq_type for k in ELECTRICAL_FED_TYPES):
                    eq.substation = str(row['substation']).strip() if 'substation' in df.columns and pd.notna(row['substation']) else None
                    eq.feeder = str(row['feeder']).strip() if 'feeder' in df.columns and pd.notna(row['feeder']) else None
                else:
                    eq.substation = None
                    eq.feeder = None

                # Rating and Additional Information mapping
                eq.rating = str(row['rating']).strip() if 'rating' in df.columns and pd.notna(row['rating']) else None
                
                additional_info = None
                if 'additional information' in df.columns and pd.notna(row['additional information']):
                    additional_info = str(row['additional information']).strip()
                elif 'specs' in df.columns and pd.notna(row['specs']):
                    additional_info = str(row['specs']).strip()
                eq.specs = additional_info

            db.session.commit()
            flash(f'Import complete: {success_count} assets created, {updated_count} updated.', 'success')
            return redirect(url_for('index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error importing file: {str(e)}', 'danger')
            return redirect(request.url)

    return render_template('import_excel.html')
     
@app.route("/equipment/new", methods=["GET", "POST"])
@login_required
def create_equipment():
    error_message = None

    if request.method == "POST":
        eq_id = request.form.get("id", "").strip().upper()
        tag = request.form.get("tag", "").strip().upper()
        equipment_type = request.form.get("equipment_type", "").strip().lower()
        name = request.form.get("name", "").strip()
        area = request.form.get("area", "").strip()
        substation = request.form.get("substation", "").strip()
        feeder = request.form.get("feeder", "").strip()
        rating = request.form.get("rating", "").strip()
        specs = request.form.get("specs", "").strip()
        status = request.form.get("status", "In Service").strip()

        category = derive_category(equipment_type)

        existing_id = Equipment.query.get(eq_id)
        existing_tag = Equipment.query.filter_by(tag=tag).first()

        if existing_id:
            error_message = f"Asset ID '{eq_id}' is already registered in the system."
        elif existing_tag:
            error_message = f"Plant Tag '{tag}' is already assigned to another unit."
        else:
            new_asset = Equipment(
                id=eq_id,
                tag=tag,
                name=name,
                area=area,
                equipment_type=equipment_type,
                category=category,
                substation=substation if substation else None,
                feeder=feeder if feeder else None,
                rating=rating,
                specs=specs,
                status=status
            )
            db.session.add(new_asset)
            db.session.commit()
            flash(f"Asset {eq_id} commissioned successfully.", "success")
            return redirect(url_for("home"))

    return render_template("new_equipment.html", error_message=error_message)
    


@app.route("/equipment/<equipment_id>/edit", methods=["GET", "POST"])
@login_required
def edit_equipment(equipment_id):
    equipment = Equipment.query.get_or_404(equipment_id)

    if request.method == "POST":
        # Mutate existing record fields with incoming form inputs
        equipment.name = request.form.get("name", "").strip()
        equipment.tag = request.form.get("tag", "").strip().upper()
        equipment.area = request.form.get("area", "").strip()
        equipment.rating = request.form.get("rating", "").strip()
        equipment.voltage = request.form.get("voltage", "").strip()
        equipment.status = request.form.get("status", "").strip()
        equipment.commission_date = request.form.get("commission_date", "").strip()
        equipment.ppe_required = request.form.get("ppe_required", "").strip()

        # Commit update transaction
        db.session.commit()
        return redirect(url_for("get_equipment", equipment_id=equipment.id))

    return render_template("edit_equipment.html", equipment=equipment)



@app.route("/equipment/<equipment_id>/delete", methods=["POST"])
@login_required
def delete_equipment(equipment_id):
    # Fetch equipment or trigger a 404 trip if not present
    equipment = Equipment.query.get_or_404(equipment_id)

    # Delete the record from SQLite
    db.session.delete(equipment)
    db.session.commit()

    return redirect(url_for("home"))



@app.route("/equipment/<equipment_id>/log", methods=["POST"])
@login_required
def add_maintenance_log(equipment_id):
    equipment = Equipment.query.get_or_404(equipment_id)

    log_type = request.form.get("log_type", "").strip()
    technician = request.form.get("technician", "").strip()
    status_after = request.form.get("status_after", "").strip()
    description = request.form.get("description", "").strip()

    if log_type and technician and status_after and description:
        # Create child relational log entry
        new_log = MaintenanceLog(
            equipment_id=equipment.id,
            log_type=log_type,
            technician=technician,
            status_after=status_after,
            description=description,
            timestamp=datetime.utcnow()
        )
        db.session.add(new_log)

        # Synchronize parent asset operational status
        equipment.status = status_after
        db.session.commit()

    return redirect(url_for("get_equipment", equipment_id=equipment.id))



@app.route("/equipment/<equipment_id>")
def get_equipment(equipment_id):
    # Query database using primary key; trips automatic 404 if record doesn't exist
    equipment = Equipment.query.get_or_404(equipment_id)
    return render_template(
        "equipment.html", equipment_id=equipment.id, equipment=equipment
    )

@app.route("/equipment/print-tags")
def print_tags():
    # Fetch all equipment assets ordered by Asset ID
    equipments = Equipment.query.order_by(Equipment.id).all()
    return render_template("print_tags.html", equipments=equipments)

@app.route("/equipment/export-qr-zip")
def export_qr_zip():
    equipments = Equipment.query.order_by(Equipment.id).all()

    # Create an in-memory byte buffer for the zip file
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for eq in equipments:
            target_url = url_for("get_equipment", equipment_id=eq.id, _external=True)

            # Generate individual QR
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=2,
            )
            qr.add_data(target_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            # Save QR to a temporary image buffer
            img_buffer = io.BytesIO()
            img.save(img_buffer, format="PNG")
            img_buffer.seek(0)

            # Write file into zip archive with a clean naming convention
            file_name = f"{eq.id}_{eq.tag.replace('/', '-')}.png"
            zip_file.writestr(file_name, img_buffer.getvalue())

    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="plant_equipment_qr_bundle.zip"
    )

@app.route("/scanner")
def scan_equipment():
    return render_template("scanner.html")

@app.route("/equipment/<equipment_id>/qr")
def equipment_qr(equipment_id):
    # Verify equipment exists in database first
    equipment = Equipment.query.get_or_404(equipment_id)

    # Construct the absolute URL to the equipment detail page
    # _external=True generates 'http://127.0.0.1:5000/equipment/EQ-00001' instead of a relative path
    target_url = url_for("get_equipment", equipment_id=equipment.id, _external=True)

    # Generate QR Code Matrix
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,  # Standard 15% error recovery for plant tags
        box_size=10,
        border=2,
    )
    qr.add_data(target_url)
    qr.make(fit=True)

    # Render image using Pillow
    img = qr.make_image(fill_color="black", back_color="white")

    # Write image to an in-memory byte stream (no disk write)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return send_file(buffer, mimetype="image/png")

@app.errorhandler(403)
def forbidden_error(error):
    return render_template("errors/403.html"), 403


@app.errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template("errors/500.html"), 500

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)