import os
from celery import Celery
from django.conf import settings
from kombu import Queue


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "solstice.settings")

app = Celery("solstice")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.task_queues = (
    Queue('gpu_queue'),
    Queue('cpu_queue'),
)

app.conf.task_routes = {
    'video_processing.video_to_pose_data_task_gpu': {'queue': 'gpu_queue'},
    'video_processing.video_to_pose_data_task_cpu': {'queue': 'cpu_queue'},
}


# Optional: Define a debug task to test if Celery is working (can be removed later)
@app.task(bind=True, name="debug_task")
def debug_task(self):
    """A simple task that prints its own request info."""
    print(f"Request: {self.request!r}")
    return "Debug task executed successfully!"


# --- Notes on running Celery ---
#
# 1. Ensure you have a message broker (like Redis or RabbitMQ) running and configured
#    in your solstice/solstice/settings.py file. For example, for Redis:
#    CELERY_BROKER_URL = 'redis://localhost:6379/0'
#    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0' # Optional: if you want to store results
#
# 2. To start a Celery worker, open a new terminal, navigate to your project root
#    (the directory containing manage.py), activate your virtual environment, and run:
#    celery -A solstice worker -l info
#
#    (Replace 'solstice' with your project name if it's different in this context)
#
