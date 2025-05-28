from django.urls import path
from .views import VideoUploadAPIView, JobStatusAPIView, LatestVideoAndCSVAPIView

app_name = 'video_processing'

urlpatterns = [
    path('upload/', VideoUploadAPIView.as_view(), name='video_upload'),
    path('jobs/<uuid:job_id>/status/', JobStatusAPIView.as_view(), name='job_status'),
    path('latest/', LatestVideoAndCSVAPIView.as_view(), name='latest_video_and_csv'),
]
