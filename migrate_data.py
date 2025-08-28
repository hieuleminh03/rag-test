#!/usr/bin/env python3
"""
Data migration script for RAG Test Case Management System
Migrates existing data to new structure and validates integrity
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from config import Config
from models import TestCase
from services import TestCaseService
from utils import safe_json_load, safe_json_save, setup_logging

setup_logging()

def backup_existing_data():
    """Create backup of existing data"""
    backup_dir = Config.BASE_DIR / 'backup'
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Backup test_data.json
    if Path('test_data.json').exists():
        backup_file = backup_dir / f'test_data_backup_{timestamp}.json'
        shutil.copy2('test_data.json', backup_file)
        print(f"✅ Backed up test_data.json to {backup_file}")
        return backup_file
    
    return None

def migrate_test_cases():
    """Migrate test cases to new structure"""
    # Load existing data
    old_data = safe_json_load(Path('test_data.json'), [])
    
    if not old_data:
        print("⚠️  No existing test data found")
        return
    
    print(f"📊 Found {len(old_data)} test cases to migrate")
    
    # Initialize new data directory
    Config.init_directories()
    
    # Migrate each test case
    migrated_cases = []
    errors = []
    
    for i, case_data in enumerate(old_data):
        try:
            # Create TestCase object (this will add timestamps if missing)
            test_case = TestCase.from_dict(case_data)
            
            # Validate
            validation_errors = test_case.validate()
            if validation_errors:
                errors.append(f"Case {i+1} ({test_case.id}): {', '.join(validation_errors)}")
            
            migrated_cases.append(test_case.to_dict())
            
        except Exception as e:
            errors.append(f"Case {i+1}: Failed to migrate - {str(e)}")
    
    # Save migrated data
    if migrated_cases:
        safe_json_save(migrated_cases, Config.TEST_DATA_FILE)
        print(f"✅ Migrated {len(migrated_cases)} test cases to {Config.TEST_DATA_FILE}")
    
    # Report errors
    if errors:
        print(f"⚠️  Migration errors:")
        for error in errors:
            print(f"   - {error}")
    
    return len(migrated_cases), len(errors)

def validate_migration():
    """Validate migrated data"""
    print("\n🔍 Validating migrated data...")
    
    try:
        service = TestCaseService()
        test_cases = service.get_all_test_cases()
        validation_report = service.validate_all_test_cases()
        
        print(f"📊 Validation Results:")
        print(f"   Total cases: {validation_report.total_cases}")
        print(f"   Valid cases: {validation_report.valid_cases}")
        print(f"   Invalid cases: {validation_report.invalid_cases}")
        
        if validation_report.duplicate_ids:
            print(f"   Duplicate IDs: {', '.join(validation_report.duplicate_ids)}")
        
        if validation_report.errors:
            print(f"   Validation errors:")
            for error in validation_report.errors:
                print(f"      - {error['id']}: {', '.join(error['errors'])}")
        
        return validation_report.invalid_cases == 0
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

def cleanup_old_files():
    """Clean up old files after successful migration"""
    old_files = [
        'data_manager.py',
        'rag_utils.py',
        'setup_rag.py'
    ]
    
    cleanup_dir = Config.BASE_DIR / 'old_files'
    cleanup_dir.mkdir(exist_ok=True)
    
    for file_name in old_files:
        file_path = Path(file_name)
        if file_path.exists():
            new_path = cleanup_dir / file_name
            shutil.move(str(file_path), str(new_path))
            print(f"📦 Moved {file_name} to {new_path}")

def main():
    """Main migration process"""
    print("🚀 Starting data migration...")
    print("=" * 50)
    
    # Step 1: Backup existing data
    backup_file = backup_existing_data()
    
    # Step 2: Migrate test cases
    migrated_count, error_count = migrate_test_cases()
    
    # Step 3: Validate migration
    if migrated_count > 0:
        validation_success = validate_migration()
        
        if validation_success:
            print("\n✅ Migration completed successfully!")
            
            # Step 4: Cleanup (optional)
            response = input("\n🗂️  Move old utility files to 'old_files' directory? (y/N): ")
            if response.lower() == 'y':
                cleanup_old_files()
            
        else:
            print("\n⚠️  Migration completed with validation errors")
            if backup_file:
                print(f"💡 Original data backed up to: {backup_file}")
    
    else:
        print("\n❌ Migration failed - no test cases migrated")
    
    print("\n📋 Migration Summary:")
    print(f"   Migrated: {migrated_count} test cases")
    print(f"   Errors: {error_count}")
    print(f"   Backup: {backup_file if backup_file else 'None created'}")
    
    print("\n🎯 Next Steps:")
    print("   1. Test the web application: python app.py")
    print("   2. Verify all functionality works correctly")
    print("   3. Update any custom scripts to use new services")

if __name__ == "__main__":
    main()