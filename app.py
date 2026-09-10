import os
from flask import Flask, abort, render_template, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configure SQLite Database File Path
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
    basedir, "equipment.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# Define the Equipment Model (Database Table Schema)
class Equipment(db.Model):
    __tablename__ = "equipments"

    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    tag = db.Column(db.String(50), nullable=False, unique=True)
    area = db.Column(db.String(50), nullable=False)
    rating = db.Column(db.String(50), nullable=False)
    voltage = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="In Service")
    commission_date = db.Column(db.String(20), nullable=False)
    ppe_required = db.Column(
        db.String(255), nullable=False
    )  # Stored as comma-separated values

    def get_ppe_list(self):
        """Helper to convert comma-separated string back to a clean list for templates."""
        if not self.ppe_required:
            return []
        return [item.strip() for item in self.ppe_required.split(",")]


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


@app.route("/equipment/<equipment_id>")
def get_equipment(equipment_id):
    # Query database using primary key; trips automatic 404 if record doesn't exist
    equipment = Equipment.query.get_or_404(equipment_id)
    return render_template(
        "equipment.html", equipment_id=equipment.id, equipment=equipment
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)