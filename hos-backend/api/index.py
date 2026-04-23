import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]  # .../hos-backend
sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

app = get_wsgi_application()

