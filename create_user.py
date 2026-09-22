from app import app, db, User

with app.app_context():
    # Ensure tables exist
    db.create_all()

    # Check if the user already exists
    username = "lead_engineer"
    existing_user = User.query.filter_by(username=username).first()

    if not existing_user:
        user = User(
            username=username,
            full_name="Chief Electrical Supervisor",
            role="Administrator"
        )
        user.set_password("Substation@2026")
        db.session.add(user)
        db.session.commit()
        print(f"User '{username}' created successfully!")
    else:
        # Reset password in case the hash was corrupted
        existing_user.set_password("Substation@2026")
        db.session.commit()
        print(f"User '{username}' already exists. Password has been reset.")