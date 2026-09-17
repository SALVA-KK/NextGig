import os
import sys
import time
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.conf import settings
from django.db import connection
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.opportunities.models import Opportunity
from datetime import date, timedelta
from apps.opportunities.tasks import notify_poster_of_new_application

User = get_user_model()

print("==================================================================")
print("VERIFICATION 2: REDIS-DOWN SCENARIO (INVALID PORT 63799)")
print("==================================================================")

# Temporarily point Celery settings to unreachable broker port 63799
original_broker = settings.CELERY_BROKER_URL
original_backend = settings.CELERY_RESULT_BACKEND

settings.CELERY_BROKER_URL = "redis://localhost:63799/0"
settings.CELERY_RESULT_BACKEND = "redis://localhost:63799/0"

# Also update Celery app conf
from config.celery import app as celery_app
celery_app.conf.broker_url = "redis://localhost:63799/0"
celery_app.conf.result_backend = "redis://localhost:63799/0"
celery_app.conf.broker_connection_timeout = 2.0
celery_app.conf.broker_connection_max_retries = 2
celery_app.conf.broker_transport_options = {
    "socket_timeout": 2.0,
    "socket_connect_timeout": 2.0,
    "max_retries": 2,
}

# 1. Direct delay() call under Redis-down
print("--- Direct notify_poster_of_new_application.delay() under Redis-down ---")
t0 = time.perf_counter()
try:
    notify_poster_of_new_application.delay(99999)
except Exception as e:
    t1 = time.perf_counter()
    print(f"Direct delay() failed/fast-failed as expected in {(t1-t0)*1000:.2f}ms: {e}")
else:
    t1 = time.perf_counter()
    print(f"Direct delay() completed in {(t1-t0)*1000:.2f}ms")

# 2. HTTP View Request under Redis-down
poster, _ = User.objects.get_or_create(
    email="fastfail_poster@example.com",
    defaults={"full_name": "Fast Fail Poster", "role": "provider", "is_verified": True}
)
student, _ = User.objects.get_or_create(
    email="fastfail_student@example.com",
    defaults={"full_name": "Fast Fail Student", "role": "student", "is_verified": True}
)

opp = Opportunity.objects.create(
    poster=poster,
    title=f"Fast Fail Opp {time.time()}",
    description="Testing fast-fail under unreachable Redis",
    category=Opportunity.Category.INTERNSHIP,
    work_mode=Opportunity.WorkMode.REMOTE,
    pay_type=Opportunity.PayType.STIPEND,
    status=Opportunity.Status.OPEN,
    deadline=date.today() + timedelta(days=10)
)

client = APIClient()
client.force_authenticate(user=student)
apply_url = f"/api/opportunities/{opp.pk}/apply/"

print("\n--- Executing HTTP POST /api/opportunities/<id>/apply/ under Redis-down ---")
t_http0 = time.perf_counter()
response = client.post(apply_url, {"cover_note": "Fast fail test note"}, format="json")
t_http1 = time.perf_counter()

total_ms = (t_http1 - t_http0) * 1000
print(f"HTTP Response Status Code: {response.status_code}")
print(f"NEW Total Wall-Clock Time (Redis-down): {total_ms:.2f} ms ({total_ms/1000:.4f} seconds)")

# Restore original settings
settings.CELERY_BROKER_URL = original_broker
settings.CELERY_RESULT_BACKEND = original_backend
celery_app.conf.broker_url = original_broker
celery_app.conf.result_backend = original_backend
