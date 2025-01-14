from app import app
from extensions import db
from models import User
from sqlalchemy import text


def create_admin_user():
    with app.app_context():
        try:
            # Check if admin already exists
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    role='admin',
                    is_active=True
                )
                admin.set_password('admin123')  # Set default password
                db.session.add(admin)
                db.session.commit()
                print("Admin user created successfully")
            else:
                print("Admin user already exists")
        except Exception as e:
            print(f"Error creating admin user: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    # Create admin user
    create_admin_user() 