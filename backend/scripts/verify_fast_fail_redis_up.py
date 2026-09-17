import os
import sys
import time
import json
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from apps.opportunities.models import Opportunity, Application
from apps.notifications.models import Notification
from datetime import date, timedelta

User = get_user_model()

print("==================================================================")
print("VERIFICATION 3 & 4: REDIS-UP NORMAL PATH & NOTIFICATION DISPATCH")
print("==================================================================")

poster = User.objects.filter(role="provider", is_verified=True).first()
student = User.objects.filter(role="student", is_verified=True).first()

if not poster or not student:
    poster, _ = User.objects.get_or_create(
        email="redisup_poster@example.com",
        defaults={"full_name": "Redis Up Poster", "role": "provider", "is_verified": True}
    )
    student, _ = User.objects.get_or_create(
        email="redisup_student@example.com",
        defaults={"full_name": "Redis Up Student", "role": "student", "is_verified": True}
    )

opp = Opportunity.objects.create(
    poster=poster,
    title=f"Redis UP Test Opp {time.time()}",
    description="Testing normal path timing and notification dispatch when Redis is up",
    category=Opportunity.Category.INTERNSHIP,
    work_mode=Opportunity.WorkMode.REMOTE,
    pay_type=Opportunity.PayType.STIPEND,
    status=Opportunity.Status.OPEN,
    deadline=date.today() + timedelta(days=10)
)

refresh = RefreshToken.for_user(student)
access_token = str(refresh.access_token)

url = f"http://127.0.0.1:8000/api/opportunities/{opp.pk}/apply/"
payload = json.dumps({"cover_note": "Redis UP normal path note"}).encode("utf-8")

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {access_token}"
}

print(f"Sending POST request to {url} ...")
t0 = time.perf_counter()
req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

try:
    with urllib.request.urlopen(req) as resp:
        t1 = time.perf_counter()
        body = resp.read().decode("utf-8")
        status_code = resp.status
        wire_ms = (t1 - t0) * 1000
        print(f"HTTP Response Code: {status_code}")
        print(f"VERIFICATION 3: Normal Path HTTP Wire Time: {wire_ms:.2f} ms ({wire_ms/1000:.4f} seconds)")

        # Verify application created
        app_obj = Application.objects.filter(applicant=student, opportunity=opp).first()
        print(f"Application created in DB: {app_obj is not None} (ID: {getattr(app_obj, 'id', None)})")

        # VERIFICATION 4: Check notification created in DB
        notif = Notification.objects.filter(recipient=poster, opportunity=opp, application=app_obj).first()
        print(f"VERIFICATION 4: In-app Notification created for poster: {notif is not None} (Title: '{getattr(notif, 'title', None)}')")

except Exception as e:
    print(f"Request failed: {e}")
