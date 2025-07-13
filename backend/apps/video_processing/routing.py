from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/jobs/$', consumers.JobListConsumer.as_asgi()),
    re_path(r'ws/jobs/(?P<job_id>[0-9a-f-]+)/$', consumers.JobStatusConsumer.as_asgi()),
    re_path(r'ws/latest/$', consumers.LatestDataConsumer.as_asgi()),
]
