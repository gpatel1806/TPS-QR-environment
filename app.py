from flask import Flask, abort

app = Flask(__name__)

# Simulated Plant Equipment Registry (Lookup Table)
EQUIPMENT_DATABASE = {
    "EQ-00001": {
        "name": "Main Step-Down Transformer 01",
        "tag": "220/33kV-TR-01",
        "area": "Switchyard Bay 1",
        "rating": "50 MVA",
        "voltage": "220 kV / 33 kV",
        "status": "In Service",
    },
    "EQ-00002": {
        "name": "Vacuum Circuit Breaker Incomer",
        "tag": "33kV-VCB-INC-01",
        "area": "33kV Switchgear Room",
        "rating": "1250 A",
        "voltage": "33 kV",
        "status": "In Service",
    },
    "EQ-00003": {
        "name": "Boiler Feed Pump Motor 01",
        "tag": "BFP-MTR-01",
        "area": "Boiler House Level 0",
        "rating": "630 kW",
        "voltage": "6.6 kV",
        "status": "Under Maintenance",
   },
   "EQ-00004": {
        "name": "Emergency diesel generator",
        "tag": "dg-set-01",
        "area": "dg yard",
        "rating": "1500kva",
        "voltage": "415 v",
        "status": "standby",
   },
}


@app.route("/")
def home():
    return "Industrial Equipment Management System is Online."


@app.route("/health")
def health_status():
    return "Status: OK | Database: Standby"


# Dynamic Equipment Endpoint
@app.route("/equipment/<equipment_id>")
def get_equipment(equipment_id):
    # Search for the equipment in our database
    equipment = EQUIPMENT_DATABASE.get(equipment_id)

    # Safety interlock: if the asset does not exist, throw a clean 404
    if not equipment:
        abort(404, description=f"Equipment with ID '{equipment_id}' not found.")

    # Return structured plain text for now (Lesson 05 will replace this with HTML)
    return f"""
    --- EQUIPMENT SPECIFICATION SHEET ---
    Asset ID: {equipment_id}
    Name:     {equipment['name']}
    Tag:      {equipment['tag']}
    Area:     {equipment['area']}
    Rating:   {equipment['rating']}
    Voltage:  {equipment['voltage']}
    Status:   {equipment['status']}
    """


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)