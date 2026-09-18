from datetime import datetime, timedelta
from app import Equipment, MaintenanceLog, User, app, db

# Initial Equipment Records using ONLY Excel columns
initial_equipment = [
    Equipment(
        id="EQ-00001",
        name="Main Step-Down Transformer 01",
        tag="220/33kV-TR-01",
        area="Switchyard Bay 1",
        equipment_type="transformer",
        category="Electrical",
        substation="Substation A",
        feeder="Incomer 1",
        status="In Service",
        specs="50 MVA, 220 kV / 33 kV"
    ),
    Equipment(
        id="EQ-00002",
        name="Vacuum Circuit Breaker Incomer",
        tag="33kV-VCB-INC-01",
        area="33kV Switchgear Room",
        equipment_type="ht breaker",
        category="Electrical",
        substation="Substation A",
        feeder="Incomer 1",
        status="Under Maintenance",
        specs="1250 A, 33 kV"
    ),
    Equipment(
        id="EQ-00003",
        name="Boiler Feed Pump Motor 01",
        tag="BFP-MTR-01",
        area="Boiler House Level 0",
        equipment_type="pump",
        category="Mechanical",
        substation="Substation B",
        feeder="MCC-01",
        status="Breakdown",
        specs="630 kW, 6.6 kV"
    ),
    Equipment(
        id="EQ-00004",
        name="Emergency Diesel Generator",
        tag="DG-SET-01",
        area="DG Yard",
        equipment_type="generator",
        category="Generation",
        substation=None,
        feeder=None,
        status="Standby",
        specs="1500 kVA, 415 V"
    ),
]

with app.app_context():
    print("Dropping and recreating database tables with Foreign Key schemas...")
    db.drop_all()
    db.create_all()

    print("Seeding administrative engineer accounts...")
    admin_user = User(
        username="lead_engineer",
        full_name="Chief Electrical Supervisor",
        role="Administrator"
    )
    admin_user.set_password("Substation@2026")
    db.session.add(admin_user)
    db.session.commit()

    print("Seeding industrial equipment...")
    db.session.add_all(initial_equipment)
    db.session.commit()

    print("Seeding relational maintenance logs...")
    sample_logs = [
        MaintenanceLog(
            equipment_id="EQ-00001",
            timestamp=datetime.utcnow() - timedelta(days=60),
            log_type="Quarterly PM",
            description="Transformer oil dielectric breakdown voltage test measured at 68 kV.",
            technician="R. Sharma (Senior Electrical Eng.)",
            status_after="In Service",
        ),
        MaintenanceLog(
            equipment_id="EQ-00003",
            timestamp=datetime.utcnow() - timedelta(hours=6),
            log_type="Emergency Breakdown",
            description="Motor bearing DE high vibration trip. Motor locked out.",
            technician="D. Patel (Mechanical & Drive Lead)",
            status_after="Breakdown",
        ),
    ]
    db.session.add_all(sample_logs)
    db.session.commit()

    print("Success: Database reset, admin account provisioned, and sample data injected.")