from django.apps import AppConfig
from django.contrib.auth import get_user_model


class SchedulerCoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scheduler'


def ready(self):
        # Auto create admin if not exists
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                password='1234',
                email='admin@example.com',
                role='ADMIN'
            )
