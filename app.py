from flask import Flask, abort, render_template, request

app = Flask(__name__)

# Simulated Plant Equipment Registry
EQUIPMENT_DATABASE = {
    "EQ-00001": {
        "name": "Main Step-Down Transformer 01",
        "tag": "220/33kV-TR-01",
        "area": "Switchyard Bay 1",
        "rating": "50 MVA",
        "voltage": "220 kV / 33 kV",
        "status": "In Service",
        "commission_date": "2021-04-10",
        "ppe_required": [
            "Safety Helmet",
            "Dielectric Safety Shoes (20kV)",
            "Safety Glasses",
            "Arc Flash Suit Class 4",
        ],
    },
    "EQ-00002": {
        "name": "Vacuum Circuit Breaker Incomer",
        "tag": "33kV-VCB-INC-01",
        "area": "33kV Switchgear Room",
        "rating": "1250 A",
        "voltage": "33 kV",
        "status": "Under Maintenance",
        "commission_date": "2022-01-18",
        "ppe_required": [
            "Safety Helmet",
            "Safety Shoes",
            "Insulated Gloves (33kV Rated)",
        ],
    },
    "EQ-00003": {
        "name": "Boiler Feed Pump Motor 01",
        "tag": "BFP-MTR-01",
        "area": "Boiler House Level 0",
        "rating": "630 kW",
        "voltage": "6.6 kV",
        "status": "Breakdown",
        "commission_date": "2019-11-05",
        "ppe_required": [
            "Safety Helmet",
            "Steel Toe Shoes",
            "Ear Protection (Ear Plugs/Muffs)",
        ],
    },
    "EQ-00004": {
        "name": "Emergency Diesel Generator",
        "tag": "DG-SET-01",
        "area": "DG Yard",
        "rating": "1500 kVA",
        "voltage": "415 V",
        "status": "Standby",
        "commission_date": "2023-08-20",
        "ppe_required": [
            "Safety Helmet",
            "Safety Shoes",
            "Ear Protection",
            "Heat Resistant Gloves",
        ],
    },
}


@app.route("/")
def home():
    # Read query parameters sent from the search form
    search_query = request.args.get("q", "").strip().lower()
    status_filter = request.args.get("status", "").strip()

    filtered_equipment = {}

    for eq_id, data in EQUIPMENT_DATABASE.items():
        # Match search text against ID, Name, Tag, or Area
        text_match = (
            not search_query
            or search_query in eq_id.lower()
            or search_query in data["name"].lower()
            or search_query in data["tag"].lower()
            or search_query in data["area"].lower()
        )

        # Match status filter if one is selected
        status_match = not status_filter or data["status"] == status_filter

        if text_match and status_match:
            filtered_equipment[eq_id] = data

    return render_template(
        "index.html",
        equipments=filtered_equipment,
        search_query=search_query,
        status_filter=status_filter,
    )


@app.route("/health")
def health_status():
    return "Status: OK | Database: Standby"


@app.route("/equipment/<equipment_id>")
def get_equipment(equipment_id):
    equipment = EQUIPMENT_DATABASE.get(equipment_id)

    if not equipment:
        abort(404, description=f"Equipment with ID '{equipment_id}' not found.")

    return render_template(
        "equipment.html", equipment_id=equipment_id, equipment=equipment
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)