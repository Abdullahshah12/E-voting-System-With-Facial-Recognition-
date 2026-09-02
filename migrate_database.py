"""
Database Migration Script for CNIC Verification Feature
Adds new columns to existing database without losing data
"""

import sqlite3
import os
import sys
from datetime import datetime

# Add app directory to path
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(base_dir, 'app'))

def migrate_database():
    """Add new columns to voters table"""
    db_path = os.path.join(base_dir, 'instance', 'evoting.db')
    
    if not os.path.exists(db_path):
        print("❌ Database not found. Please run the application first to create the database.")
        return False
    
    print("="*60)
    print("DATABASE MIGRATION - CNIC Verification Feature")
    print("="*60)
    print()
    
    # Backup database
    backup_path = os.path.join(base_dir, 'instance', f'evoting_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
    print(f"📦 Creating backup: {backup_path}")
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print("✅ Backup created successfully")
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        return False
    
    print()
    print("🔄 Applying migrations...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(voters)")
        columns = [column[1] for column in cursor.fetchall()]
        
        migrations_applied = []
        
        # Add date_of_birth column
        if 'date_of_birth' not in columns:
            cursor.execute("ALTER TABLE voters ADD COLUMN date_of_birth DATE")
            migrations_applied.append("date_of_birth")
            print("✅ Added column: date_of_birth")
        else:
            print("⏭️  Column already exists: date_of_birth")
        
        # Add cnic_image_path column
        if 'cnic_image_path' not in columns:
            cursor.execute("ALTER TABLE voters ADD COLUMN cnic_image_path VARCHAR(255)")
            migrations_applied.append("cnic_image_path")
            print("✅ Added column: cnic_image_path")
        else:
            print("⏭️  Column already exists: cnic_image_path")
        
        # Check if mobile column has unique constraint
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='voters'")
        table_sql = cursor.fetchone()[0]
        
        if 'mobile' in columns and 'UNIQUE' not in table_sql.upper() or 'mobile VARCHAR(15),' in table_sql:
            print("⚠️  Note: mobile column should be unique. This requires recreating the table.")
            print("   For production, consider using a proper migration tool like Alembic.")
            print("   For now, the application will enforce uniqueness at the application level.")
        
        conn.commit()
        conn.close()
        
        print()
        print("="*60)
        if migrations_applied:
            print(f"✅ Migration completed successfully!")
            print(f"   Applied {len(migrations_applied)} migration(s): {', '.join(migrations_applied)}")
        else:
            print("✅ Database is already up to date!")
        print("="*60)
        print()
        print("📝 Next steps:")
        print("   1. Start the application: python app.py")
        print("   2. Test the new CNIC verification feature")
        print()
        print(f"💾 Backup saved at: {backup_path}")
        print("   You can restore from this backup if needed")
        print()
        
        return True
        
    except Exception as e:
        print()
        print("="*60)
        print(f"❌ Migration failed: {e}")
        print("="*60)
        print()
        print("🔄 Restoring from backup...")
        try:
            shutil.copy2(backup_path, db_path)
            print("✅ Database restored from backup")
        except Exception as restore_error:
            print(f"❌ Failed to restore backup: {restore_error}")
            print(f"   Please manually restore from: {backup_path}")
        
        return False

def check_database_status():
    """Check current database schema"""
    db_path = os.path.join(base_dir, 'instance', 'evoting.db')
    
    if not os.path.exists(db_path):
        print("❌ Database not found")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(voters)")
        columns = cursor.fetchall()
        
        print()
        print("="*60)
        print("CURRENT VOTERS TABLE SCHEMA")
        print("="*60)
        print()
        print(f"{'Column Name':<25} {'Type':<15} {'Nullable':<10}")
        print("-"*60)
        
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            nullable = "NULL" if col[3] == 0 else "NOT NULL"
            print(f"{col_name:<25} {col_type:<15} {nullable:<10}")
        
        print()
        
        # Check for new columns
        column_names = [col[1] for col in columns]
        required_columns = ['date_of_birth', 'cnic_image_path']
        missing_columns = [col for col in required_columns if col not in column_names]
        
        if missing_columns:
            print(f"⚠️  Missing columns: {', '.join(missing_columns)}")
            print("   Run migration to add these columns")
        else:
            print("✅ All required columns present")
        
        print()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Database migration for CNIC verification')
    parser.add_argument('--check', action='store_true', help='Check database status without migrating')
    parser.add_argument('--force', action='store_true', help='Force migration even if columns exist')
    
    args = parser.parse_args()
    
    if args.check:
        check_database_status()
    else:
        print()
        print("⚠️  WARNING: This will modify your database!")
        print("   A backup will be created automatically.")
        print()
        
        if not args.force:
            response = input("Continue with migration? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                print("Migration cancelled")
                sys.exit(0)
        
        print()
        success = migrate_database()
        
        if success:
            print("✅ You can now start the application with the new features!")
            sys.exit(0)
        else:
            print("❌ Migration failed. Please check the error messages above.")
            sys.exit(1)
