import os
import json
from firebase_admin import db
from datetime import datetime, timedelta
from UI.retry_utils import retry_with_backoff

class CacheManager:
    _instance = None
    _cache_file = os.path.join(os.path.dirname(__file__), 'cache.json')
    pass
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CacheManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self._cache = {}
        self._last_update = {}
        self._cache_duration = timedelta(minutes=5)  # Cache expires after 5 minutes
        self._load_cache_from_disk()
    
    def _is_cache_valid(self, key):
        if key not in self._last_update:
            return False
        return datetime.now() - self._last_update[key] < self._cache_duration
    
    def _save_cache_to_disk(self):
        try:
            serializable_last_update = {k: v.isoformat() for k, v in self._last_update.items()}
            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump({'cache': self._cache, 'last_update': serializable_last_update}, f)
        except Exception as e:
            print(f"Failed to save cache to disk: {e}")
    
    @retry_with_backoff
    def _load_cache_from_disk(self):
        if not os.path.exists(self._cache_file):
            return
        try:
            with open(self._cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._cache = data.get('cache', {})
                self._last_update = {k: datetime.fromisoformat(v) for k, v in data.get('last_update', {}).items()}
        except Exception as e:
            print(f"Failed to load cache from disk: {e}")
    
    def get_data(self, path, force_reload=False):
        """Get data from cache or Firebase"""
        if not force_reload and path in self._cache and self._is_cache_valid(path):
            return self._cache[path]
        
        # Fetch from Firebase
        ref = db.reference(path)
        data = ref.get()
        
        # Update cache
        self._cache[path] = data
        self._last_update[path] = datetime.now()
        self._save_cache_to_disk()
        
        return data
    
    def update_data(self, path, data):
        """Update data in both Firebase and cache"""
        ref = db.reference(path)
        ref.update(data)
        
        # Update cache if it exists
        if path in self._cache:
            if isinstance(self._cache[path], dict):
                self._cache[path].update(data)
            else:
                self._cache[path] = data
            self._last_update[path] = datetime.now()
        self._save_cache_to_disk()
    
    def set_data(self, path, data):
        """Set data in both Firebase and cache"""
        ref = db.reference(path)
        ref.set(data)
        
        # Update cache
        self._cache[path] = data
        self._last_update[path] = datetime.now()
        self._save_cache_to_disk()
    
    def delete_data(self, path):
        """Delete data from both Firebase and cache"""
        ref = db.reference(path)
        ref.delete()
        
        # Remove from cache
        if path in self._cache:
            del self._cache[path]
            del self._last_update[path]
        self._save_cache_to_disk()
    
    def clear_cache(self):
        """Clear all cached data"""
        self._cache.clear()
        self._last_update.clear()
        self._save_cache_to_disk()
    
    def invalidate_cache(self, path=None):
        """Invalidate cache for specific path or all paths"""
        if path:
            if path in self._last_update:
                del self._last_update[path]
        else:
            self._last_update.clear()
        self._save_cache_to_disk() 