import time
from typing import Dict, List

# dict mapping client IP to list of timestamps
_login_attempts: Dict[str, List[float]] = {}
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 60

class RateLimitExceeded(Exception):
    pass

def check_login_rate_limit(client_ip: str | None):
    """
    Limits the number of login attempts per IP address using a fixed window algorithm.
    """
    if not client_ip:
        client_ip = "unknown"
        
    now = time.time()
    
    if client_ip not in _login_attempts:
        _login_attempts[client_ip] = []
        
    # Remove old attempts outside the window
    _login_attempts[client_ip] = [ts for ts in _login_attempts[client_ip] if now - ts < WINDOW_SECONDS]
    
    if len(_login_attempts[client_ip]) >= MAX_ATTEMPTS:
        raise RateLimitExceeded()
        
    _login_attempts[client_ip].append(now)
