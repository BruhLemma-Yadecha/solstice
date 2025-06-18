from django.urls import path
from .views import (
    VideoUploadAPIView, JobStatusAPIView, LatestVideoAndCSVAPIView,
    VideoDeleteAPIView, VideoRegenerateCSVAPIView, VideoListAPIView,
    JobListAPIView,
)

app_name = "video_processing"

urlpatterns = [
    path('upload/', VideoUploadAPIView.as_view(), name='video_upload'),
    path('jobs/<uuid:job_id>/status/', JobStatusAPIView.as_view(), name='job_status'),
    path('latest/', LatestVideoAndCSVAPIView.as_view(), name='latest_video_and_csv'),
    path('videos/<uuid:video_id>/delete/', VideoDeleteAPIView.as_view(), name='video_delete'),
    path('videos/<uuid:video_id>/regenerate-csv/', VideoRegenerateCSVAPIView.as_view(), name='video_regenerate_csv'),
    path('videos/', VideoListAPIView.as_view(), name='video_list'),
    path('jobs/', JobListAPIView.as_view(), name='job_list'),
]
