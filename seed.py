from app import Equipment, app, db

# Standard initial dataset
initial_equipment = [
    Equipment(
        id="EQ-00001",
        name="Main Step-Down Transformer 01",
        tag="220/33kV-TR-01",
        area="Switchyard Bay 1",
        rating="50 MVA",
        voltage="220 kV / 33 kV",
        status="In Service",
        commission_date="2021-04-10",
        ppe_required="Safety Helmet, Dielectric Safety Shoes (20kV), Safety Glasses, Arc Flash Suit Class 4",
    ),
    Equipment(
        id="EQ-00002",
        name="Vacuum Circuit Breaker Incomer",
        tag="33kV-VCB-INC-01",
        area="33kV Switchgear Room",
        rating="1250 A",
        voltage="33 kV",
        status="Under Maintenance",
        commission_date="2022-01-18",
        ppe_required="Safety Helmet, Safety Shoes, Insulated Gloves (33kV Rated)",
    ),
    Equipment(
        id="EQ-00003",
        name="Boiler Feed Pump Motor 01",
        tag="BFP-MTR-01",
        area="Boiler House Level 0",
        rating="630 kW",
        voltage="6.6 kV",
        status="Breakdown",
        commission_date="2019-11-05",
        ppe_required="Safety Helmet, Steel Toe Shoes, Ear Protection (Ear Plugs/Muffs)",
    ),
    Equipment(
        id="EQ-00004",
        name="Emergency Diesel Generator",
        tag="DG-SET-01",
        area="DG Yard",
        rating="1500 kVA",
        voltage="415 V",
        status="Standby",
        commission_date="2023-08-20",
        ppe_required="Safety Helmet, Safety Shoes, Ear Protection, Heat Resistant Gloves",
    ),
]

with app.app_context():
    print("Dropping existing tables and creating fresh database...")
    db.drop_all()
    db.create_all()

    print("Seeding industrial equipment data...")
    db.session.add_all(initial_equipment)
    db.session.commit()

    print("Success: equipment.db generated and populated.")