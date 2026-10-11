import os
import tempfile

os.environ.setdefault("DB_PATH", os.path.join(tempfile.gettempdir(), "helpdesk_test_tickets.db"))
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "3")
os.environ.setdefault("PROXYAPI_KEY", "test-key")
