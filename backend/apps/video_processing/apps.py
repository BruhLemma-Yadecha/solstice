from django.apps import AppConfig


class VideoProcessingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.video_processing"

    def ready(self):
        # Ensure signal handlers are connected
        import apps.video_processing.signals
