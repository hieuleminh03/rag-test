#!/usr/bin/env python3
"""
JSON-based database alternative for test cases
Simple, reliable, no locking issues
"""

import json
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from models import TestCase
from config import Config

logger = logging.getLogger(__name__)

class JSONDatabaseManager:
    """JSON file-based database manager for test cases"""
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or Config.DATA_DIR / "test_cases.json"
        self._lock = threading.RLock()  # Thread-safe lock
        self.init_database()
    
    def init_database(self):
        """Initialize JSON file"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.db_path.exists():
            with self._lock:
                self._save_data([])
                logger.info("JSON database initialized successfully")
    
    def _load_data(self) -> List[Dict[str, Any]]:
        """Load data from JSON file"""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading data: {e}")
            return []
    
    def _save_data(self, data: List[Dict[str, Any]]):
        """Save data to JSON file"""
        try:
            # Create backup first
            if self.db_path.exists():
                backup_path = self.db_path.with_suffix('.json.backup')
                self.db_path.rename(backup_path)
            
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Remove backup if save was successful
            backup_path = self.db_path.with_suffix('.json.backup')
            if backup_path.exists():
                backup_path.unlink()
                
            logger.debug(f"Saved {len(data)} test cases to JSON")
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            # Restore backup if save failed
            backup_path = self.db_path.with_suffix('.json.backup')
            if backup_path.exists():
                backup_path.rename(self.db_path)
            raise
    
    def create_test_case(self, test_case: TestCase) -> bool:
        """Create a new test case"""
        with self._lock:
            try:
                data = self._load_data()
                
                # Check for duplicate
                for item in data:
                    if item.get('id') == test_case.id and item.get('purpose') == test_case.purpose:
                        logger.warning(f"Test case with ID '{test_case.id}' and purpose '{test_case.purpose}' already exists")
                        return False
                
                # Add new test case
                data.append(test_case.to_dict())
                self._save_data(data)
                logger.info(f"Created test case: {test_case.id}")
                return True
            except Exception as e:
                logger.error(f"Error creating test case: {e}")
                return False
    
    def update_test_case(self, test_case: TestCase) -> bool:
        """Update an existing test case (upsert based on id + purpose)"""
        with self._lock:
            try:
                data = self._load_data()
                test_case.updated_at = datetime.now().isoformat()
                
                # Find and update existing
                for i, item in enumerate(data):
                    if item.get('id') == test_case.id and item.get('purpose') == test_case.purpose:
                        data[i] = test_case.to_dict()
                        self._save_data(data)
                        logger.info(f"Updated test case: {test_case.id}")
                        return True
                
                # If not found, create new
                return self.create_test_case(test_case)
            except Exception as e:
                logger.error(f"Error updating test case: {e}")
                return False
    
    def upsert_test_case(self, test_case: TestCase) -> bool:
        """Insert or update test case based on id + purpose unique key"""
        return self.update_test_case(test_case)
    
    def get_test_case_by_id_and_purpose(self, case_id: str, purpose: str) -> Optional[TestCase]:
        """Get test case by ID and purpose"""
        try:
            data = self._load_data()
            for item in data:
                if item.get('id') == case_id and item.get('purpose') == purpose:
                    return TestCase.from_dict(item)
            return None
        except Exception as e:
            logger.error(f"Error getting test case: {e}")
            return None
    
    def get_test_case_by_id(self, case_id: str) -> Optional[TestCase]:
        """Get first test case by ID (for backward compatibility)"""
        try:
            data = self._load_data()
            for item in data:
                if item.get('id') == case_id:
                    return TestCase.from_dict(item)
            return None
        except Exception as e:
            logger.error(f"Error getting test case: {e}")
            return None
    
    def get_all_test_cases(self) -> List[TestCase]:
        """Get all test cases"""
        try:
            data = self._load_data()
            return [TestCase.from_dict(item) for item in data]
        except Exception as e:
            logger.error(f"Error getting all test cases: {e}")
            return []
    
    def get_test_cases_count(self) -> int:
        """Get total count of test cases (optimized - no object creation)"""
        try:
            data = self._load_data()
            return len(data)
        except Exception as e:
            logger.error(f"Error getting test cases count: {e}")
            return 0
    
    def search_test_cases(self, query: str) -> List[TestCase]:
        """Search test cases by text content"""
        try:
            test_cases = self.get_all_test_cases()
            query_lower = query.lower()
            results = []
            
            for tc in test_cases:
                searchable_text = " ".join([
                    tc.id, tc.purpose, tc.scenerio, tc.test_data,
                    " ".join(tc.steps), " ".join(tc.expected), tc.note
                ]).lower()
                
                if query_lower in searchable_text:
                    results.append(tc)
            
            return results
        except Exception as e:
            logger.error(f"Error searching test cases: {e}")
            return []
    
    def delete_test_case(self, case_id: str, purpose: str = None) -> bool:
        """Delete test case by ID and optionally purpose"""
        with self._lock:
            try:
                data = self._load_data()
                original_count = len(data)
                
                if purpose:
                    data = [item for item in data 
                           if not (item.get('id') == case_id and item.get('purpose') == purpose)]
                else:
                    data = [item for item in data if item.get('id') != case_id]
                
                if len(data) < original_count:
                    self._save_data(data)
                    logger.info(f"Deleted test case: {case_id}")
                    return True
                return False
            except Exception as e:
                logger.error(f"Error deleting test case: {e}")
                return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            test_cases = self.get_all_test_cases()
            
            purposes = {}
            test_data_sources = {}
            
            for tc in test_cases:
                purposes[tc.purpose] = purposes.get(tc.purpose, 0) + 1
                test_data_sources[tc.test_data] = test_data_sources.get(tc.test_data, 0) + 1
            
            return {
                'total_cases': len(test_cases),
                'purposes': purposes,
                'test_data_sources': test_data_sources
            }
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {'total_cases': 0, 'purposes': {}, 'test_data_sources': {}}
    
    def migrate_from_json(self, json_file_path: Path) -> int:
        """Migrate data from another JSON file"""
        try:
            if not json_file_path.exists():
                logger.warning(f"JSON file not found: {json_file_path}")
                return 0
            
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                logger.error("JSON file should contain a list of test cases")
                return 0
            
            migrated_count = 0
            for item in data:
                try:
                    test_case = TestCase.from_dict(item)
                    if self.upsert_test_case(test_case):
                        migrated_count += 1
                except Exception as e:
                    logger.error(f"Error migrating test case {item.get('id', 'unknown')}: {e}")
            
            logger.info(f"Migrated {migrated_count} test cases from JSON")
            return migrated_count
        except Exception as e:
            logger.error(f"Error migrating from JSON: {e}")
            return 0