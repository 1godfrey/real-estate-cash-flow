import os
import json
import time
import logging
from typing import Any, Optional
from datetime import datetime, timedelta

# Default cache location is the current directory
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
CACHE_EXPIRY_DAYS = 30  # Cache data for 30 days

def ensure_cache_dir():
    """Ensures the cache directory exists."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def get_cache_path(key: str) -> str:
    """Returns the full file path for a cache key."""
    # Convert key to a valid filename by replacing non-alphanumeric chars
    safe_key = "".join(c if c.isalnum() else "_" for c in key)
    return os.path.join(CACHE_DIR, f"{safe_key}.json")

def get_cached_data(key: str) -> Optional[Any]:
    """
    Retrieves data from cache if it exists and is not expired.
    
    Args:
        key: The cache key to retrieve.
        
    Returns:
        The cached data if available and not expired, otherwise None.
    """
    ensure_cache_dir()
    cache_path = get_cache_path(key)
    
    if not os.path.exists(cache_path):
        logging.debug(f"No cache found for {key}")
        return None
    
    try:
        with open(cache_path, 'r') as f:
            cache_data = json.load(f)
        
        # Check if cache is expired
        timestamp = cache_data.get('timestamp', 0)
        expiry_time = datetime.fromtimestamp(timestamp) + timedelta(days=CACHE_EXPIRY_DAYS)
        
        if datetime.now() > expiry_time:
            logging.debug(f"Cache for {key} has expired")
            os.remove(cache_path)  # Clean up expired cache
            return None
            
        return cache_data.get('data')
        
    except (IOError, json.JSONDecodeError) as e:
        logging.warning(f"Error reading cache for {key}: {str(e)}")
        return None

def cache_data(key: str, data: Any) -> bool:
    """
    Stores data in the cache.
    
    Args:
        key: The cache key.
        data: The data to cache.
        
    Returns:
        True if caching was successful, False otherwise.
    """
    ensure_cache_dir()
    cache_path = get_cache_path(key)
    
    try:
        cache_entry = {
            'timestamp': datetime.now().timestamp(),
            'data': data
        }
        
        with open(cache_path, 'w') as f:
            json.dump(cache_entry, f)
            
        return True
        
    except (IOError, TypeError) as e:
        logging.error(f"Error caching data for {key}: {str(e)}")
        return False
