from app.database import SessionLocal
from app.models import Role

ROLE_NAMES = [
    "Super Admin",
    "Admin",
    "Support Agent",
    "Customer",]

def seed_roles():
    db = SessionLocal()
    try:
        for role_name in ROLE_NAMES:
            exists = db.query(Role).filter(
                Role.name == role_name
            ).first()
            if not exists:
                db.add(Role(name=role_name))
        db.commit()
        print("Roles seeded successfully.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_roles()
