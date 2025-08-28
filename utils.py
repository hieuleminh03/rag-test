#!/usr/bin/env python3
"""
Utility functions for RAG Test Case Management System
"""

import logging
from typing import Dict, Any, List
from pathlib import Path
import json

from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    Config.LOGS_DIR.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Config.LOGS_DIR / 'app.log'),
            logging.StreamHandler()
        ]
    )

def validate_json_structure(data: Any, expected_structure: Dict[str, type]) -> List[str]:
    """Validate JSON data structure"""
    errors = []
    
    if not isinstance(data, dict):
        errors.append("Data must be a dictionary")
        return errors
    
    for field, expected_type in expected_structure.items():
        if field not in data:
            errors.append(f"Missing required field: {field}")
        elif not isinstance(data[field], expected_type):
            errors.append(f"Field '{field}' must be of type {expected_type.__name__}")
    
    return errors

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations"""
    import re
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    
    return filename

def safe_json_load(file_path: Path, default: Any = None) -> Any:
    """Safely load JSON file with error handling"""
    try:
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return default
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        return default
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return default

def safe_json_save(data: Any, file_path: Path) -> bool:
    """Safely save data to JSON file"""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Successfully saved data to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving to {file_path}: {e}")
        return False

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """Extract keywords from text"""
    import re
    
    # Simple keyword extraction
    words = re.findall(r'\b\w+\b', text.lower())
    keywords = [word for word in words if len(word) >= min_length]
    
    # Remove common stop words
    stop_words = {
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above',
        'below', 'between', 'among', 'this', 'that', 'these', 'those', 'is', 'are', 'was',
        'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'could', 'should', 'may', 'might', 'must', 'can', 'shall'
    }
    
    keywords = [word for word in keywords if word not in stop_words]
    
    # Return unique keywords
    return list(set(keywords))

def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate simple text similarity score"""
    keywords1 = set(extract_keywords(text1))
    keywords2 = set(extract_keywords(text2))
    
    if not keywords1 and not keywords2:
        return 1.0
    
    if not keywords1 or not keywords2:
        return 0.0
    
    intersection = keywords1.intersection(keywords2)
    union = keywords1.union(keywords2)
    
    return len(intersection) / len(union)

def paginate_list(items: List[Any], page: int = 1, per_page: int = None) -> Dict[str, Any]:
    """Paginate a list of items"""
    if per_page is None:
        per_page = Config.ITEMS_PER_PAGE
    
    total_items = len(items)
    total_pages = (total_items + per_page - 1) // per_page
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    return {
        'items': items[start_idx:end_idx],
        'page': page,
        'per_page': per_page,
        'total_items': total_items,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if page < total_pages else None
    }

class ErrorHandler:
    """Centralized error handling"""
    
    @staticmethod
    def handle_validation_error(errors: List[str]) -> Dict[str, Any]:
        """Handle validation errors"""
        return {
            'success': False,
            'error': 'Validation failed',
            'details': errors
        }
    
    @staticmethod
    def handle_not_found_error(resource: str, identifier: str) -> Dict[str, Any]:
        """Handle not found errors"""
        return {
            'success': False,
            'error': f"{resource} not found",
            'details': f"No {resource.lower()} found with identifier: {identifier}"
        }
    
    @staticmethod
    def handle_duplicate_error(resource: str, identifier: str) -> Dict[str, Any]:
        """Handle duplicate resource errors"""
        return {
            'success': False,
            'error': f"Duplicate {resource.lower()}",
            'details': f"{resource} with identifier '{identifier}' already exists"
        }
    
    @staticmethod
    def handle_generic_error(error: Exception) -> Dict[str, Any]:
        """Handle generic errors"""
        logger.error(f"Unexpected error: {error}")
        return {
            'success': False,
            'error': 'Internal server error',
            'details': str(error) if Config.DEBUG else 'An unexpected error occurred'
        }