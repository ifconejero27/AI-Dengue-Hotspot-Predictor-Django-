from django.apps import AppConfig
from django.db.utils import OperationalError
from django.db.models.signals import post_migrate

class BackendConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend'

    def ready(self):
        from backend.tasks import start_scheduler

        try:
            print("⚙️ Starting APScheduler immediately (dev mode)...")
            start_scheduler()
        except OperationalError:
            print("⚠️ Database not ready, skipping scheduler start for now.")
