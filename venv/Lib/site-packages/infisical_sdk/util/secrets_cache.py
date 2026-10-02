from typing import Dict, Tuple, Any

import json
import time
import threading
import weakref
import atexit
from hashlib import sha256
import pickle

MAX_CACHE_SIZE = 1000

# Global registry to track active caches for cleanup at interpreter shutdown
_active_caches: weakref.WeakSet = weakref.WeakSet()
_atexit_registered = False


def _cleanup_all_caches():
    """Called at interpreter shutdown to stop all cache threads."""
    for cache in list(_active_caches):
        try:
            cache.close()
        except Exception:
            pass


class SecretsCache:
    def __init__(self, ttl_seconds: int = 60) -> None:
      if ttl_seconds is None or ttl_seconds <= 0:
          self.enabled = False
          self._closed = True
          return
    
      self.enabled = True
      self._closed = False
      self.ttl = ttl_seconds
      self.cleanup_interval = 60

      self.cache: Dict[str, Tuple[bytes, float]] = {}

      self.lock = threading.RLock()

      # use a event for cleaner thread signaling
      self._stop_event = threading.Event()
      
      # start cleanup thread with a ref to self
      # this prevents the thread from keeping the cache alive
      self.cleanup_thread = threading.Thread(
          target=self._cleanup_worker_static,
          args=(weakref.ref(self),),
          daemon=True,
          name=f"SecretsCache-cleanup-{id(self)}"
      )
      self.cleanup_thread.start()
      
      # register for cleanup tracking
      _active_caches.add(self)
      
      # register atexit handler once
      global _atexit_registered
      if not _atexit_registered:
          atexit.register(_cleanup_all_caches)
          _atexit_registered = True

    def compute_cache_key(self, operation_name: str, **kwargs) -> str:
      sorted_kwargs = sorted(kwargs.items())
      json_str = json.dumps(sorted_kwargs)

      return f"{operation_name}-{sha256(json_str.encode()).hexdigest()}"
  
    def get(self, cache_key: str) -> Any:
      if not self.enabled or self._closed:
        return None

      with self.lock:
          if cache_key in self.cache:
              serialized_value, timestamp = self.cache[cache_key]
              if time.time() - timestamp <= self.ttl:
                  return pickle.loads(serialized_value)
              else:
                  self.cache.pop(cache_key, None)
                  return None
          else:
              return None
            
            
    def set(self, cache_key: str, value: Any) -> None:
      if not self.enabled or self._closed:
        return

      with self.lock:
        serialized_value = pickle.dumps(value)
        self.cache[cache_key] = (serialized_value, time.time())

        if len(self.cache) > MAX_CACHE_SIZE:
          oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1]) # oldest key based on timestamp
          self.cache.pop(oldest_key)



    def unset(self, cache_key: str) -> None:
      if not self.enabled or self._closed:
        return

      with self.lock:
        self.cache.pop(cache_key, None)

    def invalidate_operation(self, operation_name: str) -> None:
      if not self.enabled or self._closed:
        return

      with self.lock:
        for key in list(self.cache.keys()):
          if key.startswith(operation_name):
            self.cache.pop(key, None)


    def _cleanup_expired_items(self) -> None:
      """Remove all expired items from the cache."""
      current_time = time.time()
      with self.lock:
          expired_keys = [
              key for key, (_, timestamp) in self.cache.items() 
              if current_time - timestamp > self.ttl
          ]
          for key in expired_keys:
              self.cache.pop(key, None)
  
    @staticmethod
    def _cleanup_worker_static(cache_ref: weakref.ref) -> None:
      """
      Background worker that periodically cleans up expired items.
      
      Uses a weak reference to the cache to avoid preventing garbage collection.
      The thread will exit automatically when the cache is garbage collected.
      """
      while True:
        cache = cache_ref()
        if cache is None:
            return  # cache has been garbage collected, exit thread
        
        # extract what we need, then release the reference so GC can work
        stop_event = cache._stop_event
        cleanup_interval = cache.cleanup_interval
        del cache  # release reference BEFORE waiting
        
        # now wait without holding a reference to the cache
        if stop_event.wait(timeout=cleanup_interval):
            return  # event was set, time to stop
        
        # re-acquire reference to do cleanup
        cache = cache_ref()
        if cache is None:
            return  # cache was garbage collected during wait
            
        cache._cleanup_expired_items()

    def close(self) -> None:
      """
      Explicitly stop the cleanup thread and release resources.
      
      This method should be called when the cache is no longer needed.
      It is safe to call multiple times.
      """
      if not self.enabled or self._closed:
          return
      
      self._closed = True
      self._stop_event.set()
      
      if self.cleanup_thread.is_alive():
          self.cleanup_thread.join(timeout=2.0)
      
      # clear the cache
      with self.lock:
          self.cache.clear()

    def __enter__(self) -> "SecretsCache":
      """Support for context manager protocol."""
      return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
      """Ensure cleanup when exiting context."""
      self.close()

    def __del__(self) -> None:
      """Fallback cleanup when object is garbage collected."""
      try:
          self.close()
      except Exception:
          # just pass to ignore errors on shutdown
          pass
