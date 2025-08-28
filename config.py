#!/usr/bin/env python3
"""
Configuration management for RAG Test Case Management System
"""

import os
from pathlib import Path
from typing import Dict, Any

class Config:
    """Base configuration class"""
    
    # Application settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'rag_test_case_management_2024'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # File paths
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / 'data'
    EXPORTS_DIR = BASE_DIR / 'exports'
    LOGS_DIR = BASE_DIR / 'logs'
    TEMPLATES_DIR = BASE_DIR / 'templates'
    STATIC_DIR = BASE_DIR / 'static'
    
    # Data files
    TEST_DATA_FILE = DATA_DIR / 'test_data.json'
    API_DOC_FILE = BASE_DIR / 'sample.md'
    
    # RAG settings
    RAG_TOP_K = 5
    RAG_CHUNK_SIZE = 500
    RAG_CHUNK_OVERLAP = 50
    
    # Validation settings
    MAX_TEST_CASES = 1000
    MAX_STEPS_PER_CASE = 20
    MAX_EXPECTED_PER_CASE = 20
    
    # UI settings
    ITEMS_PER_PAGE = 12
    SEARCH_MIN_LENGTH = 2
    
    @classmethod
    def init_directories(cls):
        """Create necessary directories"""
        for directory in [cls.DATA_DIR, cls.EXPORTS_DIR, cls.LOGS_DIR, 
                         cls.TEMPLATES_DIR, cls.STATIC_DIR]:
            directory.mkdir(exist_ok=True)
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get configuration as dictionary"""
        return {
            'debug': cls.DEBUG,
            'data_file': str(cls.TEST_DATA_FILE),
            'api_doc_file': str(cls.API_DOC_FILE),
            'rag_top_k': cls.RAG_TOP_K,
            'max_test_cases': cls.MAX_TEST_CASES,
            'items_per_page': cls.ITEMS_PER_PAGE
        }

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'production_secret_key_change_me'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    TEST_DATA_FILE = Config.BASE_DIR / 'test_data_test.json'

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}