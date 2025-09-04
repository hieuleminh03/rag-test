#!/usr/bin/env python3
"""
Data models for RAG Test Case Management System
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import re
from pathlib import Path

@dataclass
class TestCase:
    """Test case data model"""
    id: str
    purpose: str
    scenerio: str  # Keep original spelling for compatibility
    test_data: str
    steps: List[str]
    expected: List[str]
    note: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    @staticmethod
    def clean_id(raw_id: str) -> str:
        """Clean and normalize ID to make it valid for database storage"""
        if not raw_id or not str(raw_id).strip():
            return "cleaned_id"
        
        # Convert to string and strip whitespace
        clean_id = str(raw_id).strip()
        
        # Replace invalid characters with underscores
        # Keep only letters, numbers, hyphens, and underscores
        clean_id = re.sub(r'[^a-zA-Z0-9\-_]', '_', clean_id)
        
        # Remove multiple consecutive underscores
        clean_id = re.sub(r'_+', '_', clean_id)
        
        # Remove leading/trailing underscores
        clean_id = clean_id.strip('_')
        
        # Ensure it's not empty after cleaning
        if not clean_id:
            clean_id = "cleaned_id"
        
        return clean_id
    
    def __post_init__(self):
        """Set timestamps and clean ID if not provided"""
        # Clean the ID automatically
        self.id = self.clean_id(self.id)
        
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'purpose': self.purpose,
            'scenerio': self.scenerio,
            'test_data': self.test_data,
            'steps': self.steps,
            'expected': self.expected,
            'note': self.note,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestCase':
        """Create from dictionary with automatic ID cleaning"""
        # Clean the ID before creating the object
        raw_id = data.get('id', '')
        cleaned_id = cls.clean_id(raw_id)
        
        return cls(
            id=cleaned_id,
            purpose=data.get('purpose', ''),
            scenerio=data.get('scenerio', ''),
            test_data=data.get('test_data', ''),
            steps=data.get('steps', []),
            expected=data.get('expected', []),
            note=data.get('note', ''),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def validate(self) -> List[str]:
        """Validate test case data"""
        errors = []
        
        # Required fields
        if not self.id.strip():
            errors.append("ID is required")
        elif not self.id.replace('-', '').replace('_', '').replace(' ', '').isalnum():
            errors.append("ID can only contain letters, numbers, hyphens, and underscores")
        
        if not self.purpose.strip():
            errors.append("Purpose is required")
        
        if not self.scenerio.strip():
            errors.append("Scenario is required")
        
        # test_data is optional, no validation needed
        
        if not self.steps:
            errors.append("At least one test step is required")
        
        if not self.expected:
            errors.append("At least one expected result is required")
        
        # Length validations
        if len(self.steps) > 20:
            errors.append("Too many test steps (maximum 20)")
        
        if len(self.expected) > 20:
            errors.append("Too many expected results (maximum 20)")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if test case is valid"""
        return len(self.validate()) == 0

@dataclass
class ValidationReport:
    """Validation report data model"""
    total_cases: int = 0
    valid_cases: int = 0
    invalid_cases: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    duplicate_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'total_cases': self.total_cases,
            'valid_cases': self.valid_cases,
            'invalid_cases': self.invalid_cases,
            'errors': self.errors,
            'duplicate_ids': self.duplicate_ids
        }

@dataclass
class CoverageAnalysis:
    """Coverage analysis data model"""
    total_test_cases: int = 0
    coverage_areas: Dict[str, int] = field(default_factory=dict)
    missing_scenarios: List[Dict[str, str]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    covered_flow_steps: int = 0
    total_flow_steps: int = 0
    coverage_percentage: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'total_test_cases': self.total_test_cases,
            'coverage_areas': self.coverage_areas,
            'missing_scenarios': self.missing_scenarios,
            'recommendations': self.recommendations,
            'covered_flow_steps': self.covered_flow_steps,
            'total_flow_steps': self.total_flow_steps,
            'coverage_percentage': self.coverage_percentage
        }

@dataclass
class Statistics:
    """Statistics data model"""
    total_cases: int = 0
    purposes: Dict[str, int] = field(default_factory=dict)
    test_data_sources: Dict[str, int] = field(default_factory=dict)
    avg_steps: float = 0.0
    avg_expected: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'total_cases': self.total_cases,
            'purposes': self.purposes,
            'test_data_sources': self.test_data_sources,
            'avg_steps': self.avg_steps,
            'avg_expected': self.avg_expected
        }