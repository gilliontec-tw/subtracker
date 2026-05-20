import os

# Must be set before api modules are imported so Settings picks it up
# and cookies are not marked secure (TestClient uses http://testserver)
os.environ.setdefault("APP_ENV", "development")
