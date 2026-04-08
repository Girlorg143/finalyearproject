#!/usr/bin/env python3
"""
Migration script to add batch_id and shipment_id columns to blockchain_logs table
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'backend', 'food_logistics.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(blockchain_logs)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'batch_id' not in columns:
            cursor.execute("ALTER TABLE blockchain_logs ADD COLUMN batch_id INTEGER")
            print("Added batch_id column")
        
        if 'shipment_id' not in columns:
            cursor.execute("ALTER TABLE blockchain_logs ADD COLUMN shipment_id INTEGER")
            print("Added shipment_id column")
        
        conn.commit()
        print("Migration completed successfully")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
