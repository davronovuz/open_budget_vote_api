from threading import Lock
from typing import Dict

_registry: Dict[int, object] = {}
_lock = Lock()

def set_driver(vote_id: int, driver) -> None:
    with _lock:
        _registry[vote_id] = driver

def get_driver(vote_id: int):
    with _lock:
        return _registry.get(vote_id)

def pop_driver(vote_id: int):
    with _lock:
        return _registry.pop(vote_id, None)
