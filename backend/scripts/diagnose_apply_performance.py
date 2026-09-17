import os
import sys
import time
import socket
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.db import connection, reset_queries
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.opportunities.models import Opportunity, Application
from datetime import date, timedelta

User = get_user_model()

print("==================================================================")
print("1. CELERY & TASK DISPATCH CHECK")
print("==================================================================")
from apps.opportunities.tasks import notify_poster_of_new_application
print("Task function:", notify_poster_of_new_application)
print("Is Celery delay method present:", hasattr(notify_poster_of_new_application, "delay"))
print("Celery Broker URL:", getattr(settings, "CELERY_BROKER_URL", "Not set"))

print("\n==================================================================")
print("2. REDIS CONNECTIVITY CHECK (host: localhost, port: 6379)")
print("==================================================================")
redis_host = "localhost"
redis_port = 6379
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2.0)
t0 = time.perf_counter()
try:
    s.connect((redis_host, redis_port))
    t1 = time.perf_counter()
    print(f"SUCCESS: Connected to Redis at {redis_host}:{redis_port} in {(t1-t0)*1000:.2f}ms")
    s.close()
    redis_available = True
except Exception as e:
    t1 = time.perf_counter()
    print(f"FAILED: Connection to Redis failed in {(t1-t0)*1000:.2f}ms: {e}")
    redis_available = False

# Measure Redis delay() call timing specifically
print("\n--- Measuring notify_poster_of_new_application.delay() execution time ---")
t_delay_start = time.perf_counter()
try:
    # Use dummy ID 99999 for timing check
    res = notify_poster_of_new_application.delay(99999)
    t_delay_end = time.perf_counter()
    print(f"delay() call completed in {(t_delay_end - t_delay_start)*1000:.2f}ms. Result task_id: {getattr(res, 'id', None)}")
except Exception as e:
    t_delay_end = time.perf_counter()
    print(f"delay() call failed/timed out in {(t_delay_end - t_delay_start)*1000:.2f}ms: {e}")


print("\n==================================================================")
print("3. DETAILED STEP-BY-STEP MEASUREMENT OF POST /api/opportunities/<id>/apply/")
print("==================================================================")

# Setup test poster and student user
poster, _ = User.objects.get_or_create(
    email="perf_poster@example.com",
    defaults={"full_name": "Perf Poster", "role": "provider", "is_verified": True}
)
student, _ = User.objects.get_or_create(
    email="perf_student@example.com",
    defaults={"full_name": "Perf Student", "role": "student", "is_verified": True}
)

# Ensure fresh opportunity to apply to
opp = Opportunity.objects.create(
    poster=poster,
    title=f"Perf Test Opp {time.time()}",
    description="Testing application flow speed",
    category=Opportunity.Category.INTERNSHIP,
    work_mode=Opportunity.WorkMode.REMOTE,
    pay_type=Opportunity.PayType.STIPEND,
    status=Opportunity.Status.OPEN,
    deadline=date.today() + timedelta(days=10)
)

client = APIClient()
client.force_authenticate(user=student)

apply_url = f"/api/opportunities/{opp.pk}/apply/"

settings.DEBUG = True
reset_queries()

t_req_start = time.perf_counter()
response = client.post(apply_url, {"cover_note": "Timing measurement test note"}, format="json")
t_req_end = time.perf_counter()

total_wall_ms = (t_req_end - t_req_start) * 1000

print(f"HTTP Response Status Code: {response.status_code}")
print(f"Total Wall-Clock Time: {total_wall_ms:.2f} ms ({total_wall_ms/1000:.4f} seconds)")

print("\n==================================================================")
print("4. DATABASE QUERY ANALYSIS & N+1 CHECK")
print("==================================================================")
queries = connection.queries
print(f"Total SQL Queries Executed: {len(queries)}")
total_sql_time = sum(float(q.get("time", 0)) for q in queries) * 1000
print(f"Total SQL Time: {total_sql_time:.2f} ms")
for i, q in enumerate(queries, 1):
    print(f"  Query #{i} (time: {float(q['time'])*1000:.2f}ms): {q['sql']}")


print("\n==================================================================")
print("5. THROTTLE CLASS CHECK")
print("==================================================================")
from apps.opportunities.views import ApplicationCreateView
view_obj = ApplicationCreateView()
print("Throttle Scope:", view_obj.throttle_scope)
print("Permission Classes:", [p.__name__ for p in view_obj.permission_classes])
print("Cache backend in settings:", settings.CACHES.get("default", {}))
