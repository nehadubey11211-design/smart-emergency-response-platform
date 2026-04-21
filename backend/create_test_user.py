#!/usr/bin/env python3
"""
Create a test user for development
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.db import SessionLocal, engine, Base
from app.models.user_model import User
from app.routes.auth import hash_password

def create_test_user():
    db = SessionLocal()
    try:
        # Check if user already exists
        existing = db.query(User).filter(User.email == "admin@test.com").first()
        if existing:
            print("Test user already exists!")
            return
        
        # Create test admin user
        user = User(
            name="Test Admin",
            email="admin@test.com",
            password=hash_password("password123"),
            role="admin",
            is_active=True
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print(f"Created test user: {user.email}")
        print("Login credentials:")
        print("  Email: admin@test.com")
        print("  Password: password123")
        
    except Exception as e:
        print(f"Error creating user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user()
