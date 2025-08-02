#!/usr/bin/env python
"""
Script to test WebSocket functionality locally before Docker deployment
"""
import os
import sys
import django
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'solstice.settings')
django.setup()

# Now test WebSocket functionality
from apps.video_processing.websocket_utils import send_job_list_update
from apps.video_processing.models import VideoJob

print("Testing WebSocket functionality...")

# Test sending a job list update
try:
    send_job_list_update()
    print("✅ WebSocket job list update sent successfully")
except Exception as e:
    print(f"❌ Error sending WebSocket update: {e}")

# List current jobs
jobs = VideoJob.objects.all()
print(f"📊 Current jobs in database: {jobs.count()}")
for job in jobs:
    print(f"  - Job {job.id}: {job.status}")

print("\n🚀 To test WebSocket connection:")
print("1. Start the Django server: python manage.py runserver")
print("2. Open browser dev tools and run:")
print("   const ws = new WebSocket('ws://127.0.0.1:8000/ws/jobs/');")
print("   ws.onmessage = (e) => console.log('Received:', JSON.parse(e.data));")
print("3. Create a new job via the API and watch for real-time updates!")
